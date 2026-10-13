# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S3_EDUCATION_TILE_INIT]
# Timestamp: 2026-10-12 21:45:00 +05:30
# Issue / Context: Education section needed isolated sub-section execution and IPC serialization.
# Changes Made: Built s3_education_tile.py supporting isolated education audit and healing,
#               JET degree combobox selection, Area of Study, Country mapping, and modal saving.
# Rationale: Guarantees modular sub-section isolation and prevents side effects on Work Experience.
# Preventative Notes: Never interact with experience tiles when operating in this script.
# ==============================================================================

import logging
import time
from typing import Any, Dict, List, Optional
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    build_question,
    get_effective_session_id,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
)

logger = logging.getLogger(__name__)


def heal_education_tile(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Surgically audits and heals the Education tile.
    Populates Degree, Area of Study / Major, and Country from candidate ground truth.
    """
    try:
        cand = candidate_data.get("candidate", candidate_data)
        edu_list = cand.get("education") or candidate_data.get("education") or []
        edu_info = edu_list[0] if edu_list else {}

        # Strictly profile-grounded — never invent degree/major/country.
        # Missing education data defers to operator instead of filling fake credentials.
        target_degree = str(edu_info.get("degree") or "").strip()
        target_major = str(edu_info.get("major") or edu_info.get("field_of_study") or "").strip()
        target_country = str(edu_info.get("country") or "").strip()
        if not target_degree or not target_major:
            logger.warning("[s3_education_tile] Education ground truth missing — deferring (no invented degree).")
            return {"success": False, "error": "ACTION_REQUIRED: education degree/major absent from candidate profile", "deferred": True}

        # Check if modal is already open or tile has errors
        modal_open = page.locator("input[name='educationalEstablishment']:visible, input[id^='contentItemId']:visible, input[name='areaOfStudy']:visible").count() > 0

        if not modal_open:
            # Check for invalid education tile or edit button
            tiles = page.locator(".apply-flow-profile-item-tile").all()
            target_tile = None
            for t in tiles:
                txt = t.inner_text().strip().lower()
                if any(k in txt for k in ["bachelor", "master", "degree", "education"]):
                    target_tile = t
                    break
            if not target_tile and tiles:
                target_tile = tiles[0]

            if target_tile:
                edit_btn = target_tile.locator(".apply-flow-profile-item-tile__edit-item-icon, button.icon-edit, [class*='edit-item-icon']").first
                if edit_btn.count() > 0:
                    edit_btn.click()
                    time.sleep(1.2)

        # IPC Serialization
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_edu_tile"
        ipc = IPCManager(sess_id, job_id, profile, "section_3", "education_tile")

        ipc_q = build_question(
            q_id="edu_degree_major",
            question_text="Education Details",
            field_type="COMBOBOX",
            available_choices=[target_degree, target_major, target_country],
            current_value=None,
            is_conditional=False,
            is_required=True
        )
        ipc_q["answer"] = {
            "degree": target_degree,
            "major": target_major,
            "country": target_country
        }
        ipc.write_questions([ipc_q])
        ipc.write_answers([ipc_q])

        # 1. Degree Combobox
        deg_toggle = page.locator("button[id^='contentItemId'][id$='-toggle-button']:visible").first
        if deg_toggle.count() > 0:
            deg_toggle.click()
            time.sleep(0.8)
            page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                const match = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                if (match) match.click();
            }''', target_degree)
            time.sleep(0.5)

        # 2. Area of Study / Major
        study_inp = page.locator("input[name='areaOfStudy']:visible, input[id^='areaOfStudy']:visible").first
        if study_inp.count() > 0 and (not study_inp.input_value().strip() or "unnamed" in study_inp.input_value().strip().lower()):
            study_inp.fill(target_major)
            study_inp.dispatch_event("input")
            study_inp.dispatch_event("change")

        # 3. Country Combobox
        c_toggle = page.locator("button[id^='countryCode'][id$='-toggle-button']:visible").first
        if c_toggle.count() > 0:
            c_toggle.click()
            time.sleep(0.8)
            page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                const match = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                if (match) match.click();
            }''', target_country)
            time.sleep(0.5)

        # 4. Click SAVE
        save_btn = page.locator("button.save-btn:visible, button:has-text('SAVE'):visible").first
        if save_btn.count() > 0 and not save_btn.is_disabled():
            save_btn.click()
            time.sleep(1.5)

        try:
            page.wait_for_selector("button.save-btn:visible", state="detached", timeout=3000)
        except Exception:
            pass

        ipc.mark_done()
        return {
            "success": True,
            "degree": target_degree,
            "major": target_major,
            "country": target_country
        }
    except Exception as e:
        logger.error(f"[s3_education_tile] Error healing education tile: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    import sys
    from CompanySiteApply.ats_arm import ATSArm
    from CompanySiteApply.utils.config_resolver import ConfigResolver

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Heal Education tile.")
    parser.add_argument("--profile", default="default_user", help="Candidate profile name")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP URL")
    args = parser.parse_args()

    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        candidate_data = ConfigResolver.load_candidate_config(args.profile)
        res = heal_education_tile(page, candidate_data)
        print(f"Education Tile Heal Result: {res}")
        sys.exit(0 if res.get("success") else 1)
    finally:
        arm.disconnect()
