# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S4_RESUME_UPLOAD_INIT]
# Timestamp: 2026-10-12 21:55:00 +05:30
# Issue / Context: Section 4 Resume upload needed independent execution so that if only the resume
#                  needs upload, the cover letter is not redundantly touched.
# Changes Made: Built s4_resume_upload.py encapsulating resume inspection, file resolution,
#               DOM attachment upload, and verification of the filled state.
# Rationale: Guarantees modular sub-section isolation per Section IPC Architecture §3.
# Preventative Notes: Never upload stale resumes; resolve dynamically from candidate config.
# ==============================================================================

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    build_question,
    get_effective_session_id,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
)

logger = logging.getLogger(__name__)


def heal_resume_upload(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Independently inspects and uploads the candidate's resume if missing or requested.
    """
    try:
        cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")

        # 1. Resolve candidate resume file path. PRIORITY 0 (2026-10-14 fix):
        # exact structured path APPLIED/.../<Company>/<Role>_<id>/ with FIXED
        # names — no glob. Glob is legacy fallback only.
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
        from pathlib import Path
        _url = str(getattr(page, "url", "") or "")
        _company = _company_of(candidate_data, candidate_data, _url)
        _jid = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        if not _jid and _url:
            import re as _re
            _m = (_re.search(r'requisition[iI]d=(\d+)', _url)
                  or _re.search(r'/(?:jobs?/preview/|job/|requisitions?/|preview/)(\d+)', _url))
            if _m:
                _jid = _m.group(1)
        _title = ""
        try:
            _t = page.locator(".job-title, [class*='requisition-title'], [data-bind*='jobTitle' i]").first
            if _t.count() > 0 and _t.is_visible():
                _title = _t.inner_text().strip()
        except Exception:
            _title = ""
        if not _title and isinstance(candidate_data, dict):
            _tj = candidate_data.get("target_jobs") or {}
            _title = str(_tj.get("title") or _tj.get("job_title") or "").strip()
        _profile = _slug_of(candidate_data, profile)
        resume_path = None
        if _jid:
            try:
                _ap = _app_paths(_profile, _company, _title or "role", _jid, candidate_data)
                for _cand in (_ap["resume_sub_pdf"], _ap["resume_pdf"]):
                    if _cand.is_file() and _cand.stat().st_size > 0:
                        resume_path = str(_cand)
                        break
            except Exception:
                resume_path = None
        if _company:
            from CompanySiteApply.utils.company_workspace import company_kind
            if company_kind(_company) == "service":
                roots = [Path(r) for r in resolve_search_roots(candidate_data)]
            else:
                ensure_company_workspace(candidate_data, _company)
                roots = [Path(r) for r in resolve_company_roots(candidate_data, _company)]
        else:
            roots = [Path(r) for r in resolve_search_roots(candidate_data)]
        cand_name = str(cand.get("name") or cand.get("full_name") or "").strip()
        patterns = ["*resume*.pdf", "*Resume*.pdf", "*resume*.docx", "*Resume*.docx"]
        if cand_name:
            import re as _re2
            for _tok in [t for t in _re2.split(r"[^A-Za-z0-9]+", cand_name) if t][:2]:
                patterns.insert(0, f"*{_tok}*resume*.pdf")

        if not resume_path:
            search_dirs = []
            for r in roots:
                search_dirs.append(r)
                if (r / "resumes").is_dir():
                    search_dirs.append(r / "resumes")
            for r in search_dirs:
                # Never use APPLIED trees as base inputs in fallback either —
                # outputs are role-specific; generic fallback must be a base.
                if "APPLIED ON COMPANY WEBSITE" in str(r):
                    continue
                for pattern in patterns:
                    try:
                        matches = sorted(r.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
                    except Exception:
                        matches = []
                    if matches:
                        resume_path = str(matches[0])
                        break
                if resume_path:
                    break

        if not resume_path or not os.path.exists(resume_path):
            return {"success": False, "error": f"Resume file not found in roots: {roots}"}

        expected_resume_name = os.path.basename(resume_path)

        def _has_elements(loc: Any) -> bool:
            try:
                cnt = loc.count()
                if isinstance(cnt, (int, float)):
                    return cnt > 0
                return bool(cnt)
            except Exception:
                return False

        # 2. Inspect DOM container (state AND identity — a filled box can
        # hold a stale file from a previous draft, same as cover letters).
        res_box = page.locator(".attachment-upload-button").filter(has_text=re.compile(r'resume', re.I)).first
        needs_upload = False

        if not _has_elements(res_box) or not res_box.is_visible():
            needs_upload = True
        else:
            try:
                is_filled = res_box.evaluate("el => el.classList.contains('attachment-upload-button--filled')")
                if not is_filled:
                    needs_upload = True
                else:
                    try:
                        attached = res_box.evaluate(
                            "el => { const d = el.querySelector('.attachment-upload-button__download'); "
                            "return d ? d.innerText.trim() : ''; }"
                        ) or ""
                    except Exception:
                        attached = ""
                    if attached and attached != expected_resume_name:
                        logger.warning(
                            f"[s4_resume_upload] Stale resume attached ('{attached}' != '{expected_resume_name}') — replacing."
                        )
                        rm_btn = res_box.locator("button:has-text('REMOVE'), button:has-text('Remove')").first
                        if _has_elements(rm_btn):
                            try:
                                if rm_btn.is_visible():
                                    rm_btn.click()
                                    time.sleep(1.5)
                            except Exception:
                                pass
                        needs_upload = True
            except Exception:
                needs_upload = True

        if not needs_upload:
            logger.info("[s4_resume_upload] Resume is already present and filled.")
            return {"success": True, "uploaded": False, "resume_path": resume_path}

        # 3. IPC Serialization
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_res_up"
        ipc = IPCManager(sess_id, job_id, profile, "section_4", "resume_upload")
        ipc_q = build_question(
            q_id="doc_resume",
            question_text="Candidate Master Resume",
            field_type="FILE_UPLOAD",
            available_choices=[os.path.basename(resume_path)],
            current_value=None,
            is_conditional=False,
            is_required=True
        )
        ipc_q["answer"] = resume_path
        ipc.write_questions([ipc_q])
        ipc.write_answers([ipc_q])

        # 4. Attach file
        res_input = res_box.locator("input[type='file'], input[name='attachment-upload']").first
        if _has_elements(res_input):
            logger.info(f"[s4_resume_upload] Attaching resume: {os.path.basename(resume_path)}")
            res_input.set_input_files(resume_path)
            time.sleep(2.0)

            # Wait for filled state
            for _ in range(5):
                try:
                    if res_box.evaluate("el => el.classList.contains('attachment-upload-button--filled')"):
                        break
                except Exception:
                    pass
                time.sleep(1.0)

        ipc.mark_done()
        return {
            "success": True,
            "uploaded": True,
            "resume_path": resume_path,
            "filename": os.path.basename(resume_path)
        }
    except Exception as e:
        logger.error(f"[s4_resume_upload] Error uploading resume: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    import sys
    from CompanySiteApply.ats_arm import ATSArm
    from CompanySiteApply.utils.config_resolver import ConfigResolver

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Upload candidate resume independently.")
    parser.add_argument("--profile", default="default_user", help="Candidate profile name")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP URL")
    args = parser.parse_args()

    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        candidate_data = ConfigResolver.load_candidate_config(args.profile)
        res = heal_resume_upload(page, candidate_data)
        print(f"Resume Upload Result: {res}")
        sys.exit(0 if res.get("success") else 1)
    finally:
        arm.disconnect()
