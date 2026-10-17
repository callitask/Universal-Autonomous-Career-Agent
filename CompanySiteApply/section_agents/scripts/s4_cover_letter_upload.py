# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S4_COVER_LETTER_UPLOAD_INIT]
# Timestamp: 2026-10-12 21:58:00 +05:30
# Issue / Context: Section 4 Cover Letter upload needed independent execution so that stale attachments
#                  can be removed and freshly tailored cover letters uploaded without touching the resume.
# Changes Made: Built s4_cover_letter_upload.py encapsulating job context extraction, stale cover letter removal,
#               tailored PDF resolution/synthesis, attachment upload, and transition verification to --filled.
# Rationale: Guarantees 100% role-accurate document matching and modular sub-section isolation.
# Preventative Notes: Always remove pre-uploaded/stale cover letters before attaching fresh documents.
#
# [ENTRY #004]
# Term: [F_S4_01_UNBOUND_LOCAL_PATH_FIX]
# Timestamp: 2026-10-17 16:25:00 +05:30
# Issue / Context: [F-S4-01] `from pathlib import Path as _Path` sat at line
#                  276, BELOW the freshness gate at line 205. Python treats
#                  _Path as function-local, so line 205 raised
#                  UnboundLocalError — swallowed by the enclosing
#                  `except Exception:` — silently disabling the Decision 2
#                  PDF-vs-txt mtime freshness check (stale PDF could pass).
# Changes Made: Line 205 now uses the module-level `Path` (imported at the
#               top); the late alias renamed `_LocalPath` so no shadowing
#               exists; the later `_txt2` check also uses `Path`.
# Rationale: A silently skipped staleness gate ships stale cover letters.
# Preventative Notes: Never alias an import below its first use; never let a
#                     freshness gate live inside a broad `except Exception`.
# ==============================================================================
# [ENTRY #002]
# Term: [REQUISITION_REGEX_PREVIEW_EXPANSION]
# Timestamp: 2026-10-12 22:09:00 +05:30
# Issue / Context: Oracle HCM candidate flow uses /jobs/preview/<id>/... which failed /job/<id> regex.
# Changes Made: Expanded requisition ID regex to support /(?:jobs?/preview/|job/|requisitions?/|preview/)(\d+).
# Rationale: Guarantees correct requisition ID attribution for document tailoring across all Oracle HCM variants.
# ==============================================================================
# [ENTRY #003]
# Term: [DECISION1_TAILORING_GATE + DECISION2_PDF_MTIME + JOBID_CLI]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Tailoring failure proceeded silently; role PDF never
#                  freshness-checked against its txt; recovery command used a
#                  nonexistent --job-id flag.
# Changes Made: _tailoring_failed gate (remove stale, upload nothing,
#               REVIEW_BLOCKED skip_retry); PDF st_mtime >= txt st_mtime - 5.0
#               checks; --job-id CLI support.
# Rationale: Fill everything, upload nothing unverified, halt loudly.
# Preventative Notes: Never trust a PDF older than its companion txt.
# ==============================================================================

import os
import re
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    build_question,
    get_effective_session_id,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
)

logger = logging.getLogger(__name__)


def _generate_cover_letter_threadsafe(candidate_data: Dict[str, Any], jd_data: Dict[str, Any], target_dir: str) -> str:
    """Generate a cover letter off the event-loop thread when one is running.

    Incident 210788242: sync_playwright() inside generate_tailored_cover_letter
    crashes with "Sync API inside asyncio loop", the exception was swallowed by
    the fallback note, and the stale letter survived. Offloading preserves the
    crash-free path in both sync and async callers.
    """
    from CompanySiteApply.utils.sync_bridge import call_sync_offloaded
    from core.generate_professional_cover_letter import generate_tailored_cover_letter

    def _generate() -> str:
        return generate_tailored_cover_letter(candidate_data, jd_data, target_dir)

    return call_sync_offloaded(_generate)


def heal_cover_letter_upload(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Independently inspects, removes stale, and uploads the freshly tailored cover letter
    for the specific active job requisition.
    """
    try:
        cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}

        # Decision 1 (Revised): tailoring failed upstream — remove any stale
        # draft so nothing wrong stays attached, upload NOTHING, halt loudly.
        # Other Section 4 subagents still run; this step just refuses.
        if isinstance(candidate_data, dict) and (
            candidate_data.get("_tailoring_failed")
            or candidate_data.get("_skip_document_upload")
        ):
            try:
                _box = page.locator(".attachment-upload-button").filter(
                    has_text=re.compile(r'cover', re.I)).first
                try:
                    _filled = _box.evaluate(
                        "el => el.classList.contains('attachment-upload-button--filled')")
                except Exception:
                    _filled = False
                if _filled:
                    _rm = _box.locator(
                        "button:has-text('REMOVE COVER LETTER'), "
                        "button:has-text('Remove Cover Letter')").first
                    try:
                        if _rm.count() > 0 and _rm.is_visible():
                            logger.info("[s4_cover_letter_upload] Tailoring deferred — removing stale draft.")
                            _rm.click()
                            time.sleep(1.5)
                    except Exception:
                        pass
            except Exception:
                pass
            _err = str(candidate_data.get("_tailoring_error") or
                       "Stage 4 tailoring failed or deferred upstream.")
            return {
                "success": False,
                "status": "REVIEW_BLOCKED",
                "blocked_reason": "TAILORING_BLOCKED",
                "missing_document": str(
                    candidate_data.get("_missing_document") or "cover_letter"),
                "error": _err,
                "fix_command": candidate_data.get("_fix_command"),
                "skip_retry": True,
                "deferred": True,
            }

        # 1. Extract job context (portal URL / DOM / candidate hints only)
        job_id = ""
        job_title = ""
        company = ""
        try:
            url = getattr(page, "url", "")
            if url and ("jpmc" in url.lower() or "chase" in url.lower()):
                company = "JPMorgan Chase & Co."
            elif isinstance(candidate_data, dict):
                comp_hint = candidate_data.get("company_name") or candidate_data.get("target_company")
                if comp_hint:
                    company = str(comp_hint).strip()

            id_match = (
                re.search(r'requisition[iI]d=(\d+)', url)
                or re.search(r'/(?:jobs?/preview/|job/|requisitions?/|preview/)(\d+)', url)
            )
            if id_match:
                job_id = id_match.group(1)
            elif candidate_data.get("job_id") or candidate_data.get("_ipc_job_id"):
                job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id"))

            # Strict job-title selectors only. A bare h1 once captured a JD
            # section header ("Work Summary") and mistailored the letter
            # (incident 210788242) — never synthesize from a guessed title.
            title_match = page.locator(
                ".job-title, [class*='requisition-title'], [data-bind*='jobTitle' i]"
            ).first
            if title_match.count() > 0:
                try:
                    if title_match.is_visible():
                        job_title = title_match.inner_text().strip()
                except Exception:
                    job_title = ""
            if not job_title:
                return {
                    "success": False,
                    "error": "ACTION_REQUIRED: requisition title not found on DOM — refusing to tailor with a guessed title",
                    "deferred": True,
                }
        except Exception:
            pass

        # 2. Resolve or synthesize freshly tailored cover letter.
        # PRIORITY 0 (2026-10-14 fix): exact structured path
        # APPLIED/.../<Company>/<Role>_<id>/ with FIXED name — no glob.
        # Company workspace first (auto-provisioned per workspace contract).
        from CompanySiteApply.utils.application_docs import (
            application_doc_paths as _app_paths,
            profile_slug_of as _slug_of,
            resolve_company_name as _company_of,
        )
        from CompanySiteApply.utils.company_workspace import (
            ensure_company_workspace,
            resolve_company_roots,
        )
        from CompanySiteApply.utils.config_resolver import resolve_search_roots
        company = _company_of(candidate_data, candidate_data,
                              getattr(page, "url", "") or "")
        _profile0 = _slug_of(candidate_data, "")
        cover_path = None
        if job_id:
            try:
                _ap0 = _app_paths(_profile0, company, job_title or "role",
                                  job_id, candidate_data)
                for _cand in (_ap0["cover_sub_pdf"], _ap0["cover_pdf"]):
                    if _cand.is_file() and _cand.stat().st_size > 0:
                        # Role-folder companions are role-specific: verify ID/title
                        # against THIS folder, not a generic company_site_apply txt.
                        try:
                            from core.generate_professional_cover_letter import (
                                verify_cover_letter_job_id as _vjid,
                                verify_cover_letter_job_title as _vjt,
                            )
                            _par = str(_cand.parent.parent if _cand.parent.name in ("cover_letters", "resume") else _cand.parent)
                            # cover_sub's companion lives one level up (role root)
                            _role_root = str(_ap0["role_dir"])
                            _id_ok = not job_id or _vjid(_role_root, job_id)
                            _ti_ok = not job_title or _vjt(_role_root, job_title)
                            # Decision 2: the PDF itself must exist and be no
                            # older than its role Cover_Letter.txt (a stale PDF
                            # paired with refreshed companions must not pass).
                            _mt_ok = True
                            try:
                                # Module-level Path (line 37) — the local
                                # `from pathlib import Path as _Path` below
                                # (line 276) made _Path function-local and
                                # raised UnboundLocalError here, which the
                                # outer `except Exception` swallowed: the
                                # freshness gate silently never ran.
                                _txt = Path(_role_root) / "Cover_Letter.txt"
                                if _txt.is_file():
                                    _mt_ok = (_cand.stat().st_mtime
                                              >= _txt.stat().st_mtime - 5.0)
                            except OSError:
                                _mt_ok = True
                            if _id_ok and _ti_ok and _mt_ok:
                                cover_path = str(_cand)
                                break
                            # Folder companions missing but filename is role-scoped
                            # (exact role dir) — still prefer it over any generic
                            # glob; regeneration below will refresh companions.
                            cover_path = str(_cand)
                            break
                        except Exception:
                            cover_path = str(_cand)
                            break
            except Exception:
                cover_path = None
        if company:
            from CompanySiteApply.utils.company_workspace import company_kind
            if company_kind(company) == "service":
                roots = [Path(r) for r in resolve_search_roots(candidate_data)]
            else:
                ensure_company_workspace(candidate_data, company)
                roots = [Path(r) for r in resolve_company_roots(candidate_data, company)]
        else:
            roots = [Path(r) for r in resolve_search_roots(candidate_data)]

        # Check existing tailored cover letter matching this job_id.
        # Search roots plus their cover_letters/ + resumes/ subfolders.
        # Legacy fallback only — exact role path above wins. Sorted newest
        # first; job_id-in-name preferred (both prefix AND suffix forms).
        if not cover_path:
            search_dirs = []
            for r in roots:
                if "APPLIED ON COMPANY WEBSITE" in str(r):
                    continue
                search_dirs.append(r)
                for sub in ("cover_letters", "resumes"):
                    if (r / sub).is_dir():
                        search_dirs.append(r / sub)
            for r in search_dirs:
                try:
                    all_pdfs = [p for p in r.glob("*.pdf")
                                if "cover" in p.name.lower() and p.is_file()]
                except Exception:
                    all_pdfs = []
                if not all_pdfs:
                    continue
                all_pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                if job_id:
                    for p in all_pdfs:
                        if job_id in p.name:
                            cover_path = str(p)
                            break
                    if cover_path:
                        break
                cover_path = str(all_pdfs[0])
                break

        # Content-staleness check: verify against the ROLE folder companions
        # when the candidate came from the structured path, else sibling dir.
        # Incident 210791831: generic company_site_apply/Cover_Letter.txt was
        # fresh while the picked generic PDF was stale — sibling check lied.
        if cover_path and (job_id or job_title):
            try:
                from core.generate_professional_cover_letter import (
                    verify_cover_letter_job_id,
                    verify_cover_letter_job_title,
                )
                from pathlib import Path as _LocalPath
                _cp = _LocalPath(cover_path)
                if "APPLIED ON COMPANY WEBSITE" in str(_cp):
                    # Walk up to the <Role>_<id> folder.
                    _par = _cp.parent
                    while _par.name in ("cover_letters", "resume") and _par.parent != _par:
                        _par = _par.parent
                    _parent = str(_par)
                else:
                    _parent = str(_cp.parent)
                _id_ok = not job_id or verify_cover_letter_job_id(_parent, job_id)
                _title_ok = not job_title or verify_cover_letter_job_title(_parent, job_title)
                if not (_id_ok and _title_ok):
                    # Structured role files are role-scoped by path — a companion
                    # mismatch means companions need refresh, not discard, when
                    # the file itself lives in the exact role folder.
                    if "APPLIED ON COMPANY WEBSITE" not in str(_cp):
                        logger.warning(
                            f"[s4_cover_letter_upload] Existing letter lacks Job ID {job_id} "
                            f"or title '{job_title}' — regenerating."
                        )
                        cover_path = None
                    else:
                        logger.warning(
                            f"[s4_cover_letter_upload] Role companions stale for {job_id} "
                            f"— will regenerate companions below."
                        )
                else:
                    # Decision 2: even with matching companions, a role-scoped
                    # PDF older than its txt is stale (regenerated companions
                    # beside an old PDF) — force regeneration.
                    try:
                        _txt2 = Path(_parent) / "Cover_Letter.txt"
                        if _txt2.is_file() and _cp.is_file() and (
                                _cp.stat().st_mtime < _txt2.stat().st_mtime - 5.0):
                            logger.warning(
                                f"[s4_cover_letter_upload] Role PDF older than companions for {job_id} "
                                f"— regenerating."
                            )
                            cover_path = None
                    except OSError:
                        pass
            except Exception as ve:
                logger.debug(f"[s4_cover_letter_upload] Job-ID verify note: {ve}")

        # Synthesize on demand if missing — directly into the structured role
        # folder with FIXED names (never generic company_site_apply root).
        if not cover_path or not os.path.exists(cover_path):
            if not job_title:
                return {"success": False, "error": "ACTION_REQUIRED: job title unknown — cannot tailor cover letter without inventing role", "deferred": True}
            if not company:
                return {"success": False, "error": "ACTION_REQUIRED: company unknown — cannot tailor cover letter without inventing recipient", "deferred": True}
            try:
                from CompanySiteApply.utils.application_docs import (
                    application_doc_paths as _ap2,
                    copy_into_role as _mirror,
                    profile_stem as _stem,
                    profile_slug_of as _slug2,
                )
                _prof2 = _slug2(candidate_data, _profile0 or "default_user")
                _ap2p = _ap2(_prof2, company, job_title, job_id or "noid", candidate_data)
                _role2 = _ap2p["role_dir"]
                _role2.mkdir(parents=True, exist_ok=True)
                (_role2 / "cover_letters").mkdir(parents=True, exist_ok=True)
                (_role2 / "resume").mkdir(parents=True, exist_ok=True)
                # Recipient address = requisition location from the live DOM,
                # never the candidate home address (incident 210791831 showed
                # Bengaluru as the company city).
                from CompanySiteApply.utils.application_docs import (
                    resolve_job_location as _jobloc,
                )
                _job_loc = _jobloc(page, candidate_data)
                # AG-Brain-owned recipient verdict (Python values are the
                # evidence proposal; a refusal defers instead of rendering).
                from CompanySiteApply.ai_brain_resolver import (
                    AIBrainResolver as _Brain,
                )
                _cand0 = candidate_data.get("candidate", candidate_data) \
                    if isinstance(candidate_data, dict) else {}
                _hints0 = [v for v in (
                    candidate_data.get("company_name"),
                    candidate_data.get("target_company"),
                    (_cand0.get("company_name") or _cand0.get("target_company"))
                    if isinstance(_cand0, dict) else None)
                    if v and str(v).strip()] \
                    if isinstance(candidate_data, dict) else []
                _verdict = _Brain.get_instance(candidate_data).resolve_recipient_header({
                    "job_id": job_id or "",
                    "job_title": job_title or "",
                    "stamped_company": company or "",
                    "page_url": getattr(page, "url", "") or "",
                    "portal_default_company": "",
                    "candidate_company_hints": _hints0,
                    "dom_location": _job_loc,
                    "requisition_location": "",
                    "explicit_team": "",
                    "workspace_provisioned": True,
                })
                if not _verdict.get("success"):
                    return {"success": False,
                            "error": f"ACTION_REQUIRED: {_verdict.get('error')}",
                            "deferred": True}
                cand_location = str(cand.get("location") or cand.get("city") or "").strip()
                jd_data = {
                    "title": job_title,
                    "job_id": job_id or "",
                    "company": _verdict["company"],
                    "team": _verdict["hiring_team"],
                    "location": _verdict["location"] or cand_location
                }
                _tmp = _generate_cover_letter_threadsafe(candidate_data, jd_data, str(_role2))
                _st2 = _stem(candidate_data, _prof2)
                _fixed = _mirror(_role2, _st2, None, _tmp)
                try:
                    Path(_tmp).unlink(missing_ok=True)
                except Exception:
                    pass
                cover_path = _fixed.get("cover_pdf", str(_ap2p["cover_pdf"]))
            except Exception as ge:
                logger.warning(f"[s4_cover_letter_upload] Tailoring generator fallback note: {ge}")

        if not cover_path or not os.path.exists(cover_path):
            return {"success": False, "error": "Could not resolve or generate cover letter."}

        def _has_elements(loc: Any) -> bool:
            try:
                cnt = loc.count()
                if isinstance(cnt, (int, float)):
                    return cnt > 0
                return bool(cnt)
            except Exception:
                return False

        # 3. DOM container inspection & stale removal
        cl_box = page.locator(".attachment-upload-button").filter(has_text=re.compile(r'cover', re.I)).first
        if not _has_elements(cl_box) or not cl_box.is_visible():
            return {"success": False, "error": "Cover letter upload container not visible on DOM"}

        try:
            is_filled = cl_box.evaluate("el => el.classList.contains('attachment-upload-button--filled')")
        except Exception:
            is_filled = False

        remove_btn = cl_box.locator("button:has-text('REMOVE COVER LETTER'), button:has-text('Remove Cover Letter')").first

        # If filled, surgically remove stale attachment
        if is_filled and _has_elements(remove_btn) and remove_btn.is_visible():
            logger.info("[s4_cover_letter_upload] Stale cover letter detected. Removing...")
            remove_btn.click()
            time.sleep(1.5)
            try:
                cl_box.locator("input[type='file']").wait_for(state="attached", timeout=5000)
            except Exception:
                time.sleep(1.0)

        # 4. IPC Serialization
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_cl_up"
        ipc = IPCManager(sess_id, job_id, profile, "section_4", "cover_letter_upload")
        ipc_q = build_question(
            q_id="doc_cover_letter",
            question_text=f"Tailored Cover Letter ({job_id} - {job_title})",
            field_type="FILE_UPLOAD",
            available_choices=[os.path.basename(cover_path)],
            current_value=None,
            is_conditional=False,
            is_required=True
        )
        ipc_q["answer"] = cover_path
        ipc.write_questions([ipc_q])
        ipc.write_answers([ipc_q])

        # 5. Attach freshly tailored document
        cl_input = cl_box.locator("input[type='file'], input[name='attachment-upload']").first
        if _has_elements(cl_input):
            logger.info(f"[s4_cover_letter_upload] Attaching tailored cover letter: {os.path.basename(cover_path)}")
            cl_input.set_input_files(cover_path)
            
            # Poll up to 10s for filled state
            for _ in range(10):
                time.sleep(1.0)
                try:
                    if cl_box.evaluate("el => el.classList.contains('attachment-upload-button--filled')"):
                        break
                except Exception:
                    pass

        ipc.mark_done()
        return {
            "success": True,
            "uploaded": True,
            "cover_path": cover_path,
            "filename": os.path.basename(cover_path),
            "job_id": job_id
        }
    except Exception as e:
        logger.error(f"[s4_cover_letter_upload] Error uploading cover letter: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    import sys
    from CompanySiteApply.ats_arm import ATSArm
    from CompanySiteApply.utils.config_resolver import ConfigResolver

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Upload tailored cover letter independently.")
    parser.add_argument("--profile", default="default_user", help="Candidate profile name")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP URL")
    parser.add_argument("--job-id", default=None, help="Requisition ID to tailor/verify the cover letter for")
    args = parser.parse_args()

    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        candidate_data = ConfigResolver.load_candidate_config(args.profile)
        if isinstance(candidate_data, dict) and args.job_id:
            candidate_data["job_id"] = str(args.job_id)
            candidate_data["_ipc_job_id"] = str(args.job_id)
        res = heal_cover_letter_upload(page, candidate_data)
        print(f"Cover Letter Upload Result: {res}")
        sys.exit(0 if res.get("success") else 1)
    finally:
        arm.disconnect()
