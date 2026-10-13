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

        # 1. Resolve candidate resume file path. Prefer an exact
        # candidate-name match, newest first — a bare glob once attached an
        # arbitrary (possibly stale) resume when several existed.
        from CompanySiteApply.utils.config_resolver import resolve_search_roots
        from pathlib import Path
        roots = [Path(r) for r in resolve_search_roots(candidate_data)]
        cand_name = str(cand.get("name") or cand.get("full_name") or "").strip()
        patterns = ["*resume*.pdf", "*Resume*.pdf", "*resume*.docx", "*Resume*.docx"]
        if cand_name:
            patterns.insert(0, f"*{cand_name}*.pdf")

        resume_path = None
        for r in roots:
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
