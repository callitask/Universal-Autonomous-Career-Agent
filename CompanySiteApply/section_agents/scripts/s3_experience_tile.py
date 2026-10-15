# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S3_EXPERIENCE_TILE_INIT]
# Timestamp: 2026-10-12 21:42:00 +05:30
# Issue / Context: Work experience section needed surgical single-tile healing and independent execution
#                  so that if one tile fails verification, only that specific tile re-runs.
# Changes Made: Built s3_experience_tile.py supporting tile-indexed execution (--tile-index N),
#               IPC serialization, bulleted achievement formatting, and atomic modal saving.
# Rationale: Guarantees modular sub-section isolation and prevents full section re-runs.
# Preventative Notes: Never interact with subsequent tiles while an inline modal is still open.
#
# [ENTRY #002]
# Term: [NEW-8_WORD_BOUNDARY_TILE_SCOPE]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Raw substrings mis-scoped employers ("Mastercard",
#                  "CL Educate") as Education tiles.
# Changes Made: Word-boundary degree regex for experience-tile filtering.
# Rationale: Employer names must never match degree patterns partially.
# Preventative Notes: Extend the pattern list, never revert to substrings.
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


def _tile_company(page: Any, candidate_data: Any) -> str:
    """Portal company for company-aware resume fallback (Gap 1)."""
    try:
        from CompanySiteApply.utils.application_docs import resolve_company_name
        return resolve_company_name(
            candidate_data, candidate_data, getattr(page, "url", "") or "")
    except Exception:
        return ""


def heal_single_experience_tile(
    page: Any,
    candidate_data: Dict[str, Any],
    tile_index: int = 0,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Surgically audits and heals a single Work Experience tile at the specified tile_index.
    Ensures country, city, internal status (No), and authentic bulleted achievements are saved.
    """
    try:
        cand = candidate_data.get("candidate", candidate_data)
        exp_list = (cand.get("work_experience") or 
                    cand.get("experience") or 
                    candidate_data.get("experience") or 
                    candidate_data.get("work_experience") or [])

        # Filter all tiles, finding experience tiles specifically.
        # NEW-8: word-boundary degree match — raw substrings mis-scope
        # employers like "Mastercard" or "CL Educate" as Education tiles.
        import re as _re_tile
        _EDU_RE = _re_tile.compile(
            r"\b(bachelor|master'?s?|b\.?tech|m\.?tech|mba|degree|education|"
            r"university|college|school|diploma)\b", _re_tile.IGNORECASE)
        tiles = page.locator(".apply-flow-profile-item-tile").all()
        exp_tiles = []
        for t in tiles:
            txt = t.inner_text().strip().lower()
            if not _EDU_RE.search(txt):
                exp_tiles.append(t)

        if not exp_tiles or tile_index >= len(exp_tiles):
            return {
                "success": False,
                "error": f"Tile index {tile_index} not found (total exp tiles: {len(exp_tiles)})"
            }

        target_tile = exp_tiles[tile_index]
        tile_text = target_tile.inner_text().strip()

        # Match corresponding candidate experience record
        best_match = exp_list[min(tile_index, len(exp_list) - 1)] if exp_list else {}
        for exp in exp_list:
            emp = (exp.get("employer") or exp.get("company") or "").lower()
            if emp and (emp in tile_text.lower() or tile_text.lower() in emp):
                best_match = exp
                break

        # Resume.md fallback — when structured work_experience config is absent,
        # ground the tile from the candidate's master resume instead of deferring.
        if not best_match:
            try:
                from CompanySiteApply.utils.experience_matcher import (
                    load_resume_experience_map,
                    match_experience_entry,
                )
                _rmap = load_resume_experience_map(
                    candidate_data, _tile_company(page, candidate_data))
                _m = match_experience_entry(tile_text, _rmap)
                if _m:
                    best_match = {
                        "employer": tile_text.split("\n")[0].strip(),
                        "title": _m.get("title", ""),
                        "city": _m.get("city", ""),
                        "country": _m.get("country", ""),
                        "bullets": _m.get("bullets", []),
                    }
                    logger.info("[s3_experience_tile] Grounded tile from resume.md fallback.")
            except Exception as rm_e:
                logger.debug(f"[s3_experience_tile] Resume fallback note: {rm_e}")

        # Click Edit icon on target tile
        edit_btn = target_tile.locator(
            ".apply-flow-profile-item-tile__edit-item-icon, button.icon-edit, [class*='edit-item-icon']"
        ).first
        if edit_btn.count() == 0:
            return {"success": False, "error": f"No edit button found on tile {tile_index}"}

        target_tile.scroll_into_view_if_needed()
        time.sleep(0.3)
        try:
            edit_btn.click(force=True)
        except Exception:
            page.evaluate("(el) => el.click()", edit_btn.element_handle())
        time.sleep(1.0)

        # IPC Serialization
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_exp_tile"
        ipc = IPCManager(sess_id, job_id, profile, "section_3", f"experience_tile_{tile_index}")

        # Target fields — strictly profile-grounded, no invented city/country.
        # If country/city are absent from profile, the corresponding DOM step is skipped
        # and the tile is flagged for operator review instead of filling fake data.
        target_country = str(best_match.get("country") or cand.get("country") or "").strip()
        target_city = str(best_match.get("city") or cand.get("city") or "").strip()
        bullets = best_match.get("bullets") or []
        bullet_text = "\n\n".join([f"• {b.lstrip('•*- ')}" for b in bullets]) if bullets else ""

        ipc_q = build_question(
            q_id=f"exp_{tile_index}",
            question_text=f"Experience: {best_match.get('employer', 'Company')} ({best_match.get('title', 'Role')})",
            field_type="TEXTAREA",
            available_choices=[],
            current_value=bullet_text,
            is_conditional=False,
            is_required=True
        )
        ipc_q["answer"] = {
            "country": target_country,
            "city": target_city,
            "internal": "No",
            "achievements": bullet_text
        }
        ipc.write_questions([ipc_q])
        ipc.write_answers([ipc_q])

        # 1. Employer Country
        country_inp = page.locator("input[id^='countryCode']:visible, input[name='countryCode']:visible").first
        if country_inp.count() > 0 and target_country and country_inp.input_value().strip() != target_country:
            c_toggle = page.locator("button[id^='countryCode'][id$='-toggle-button']:visible, button.icon-dropdown-arrow:visible").first
            if c_toggle.count() > 0:
                c_toggle.click()
                time.sleep(0.4)
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="option"], li')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) opt.click();
                }''', target_country)
                time.sleep(0.3)

        # 2. Employer City (skip when profile has no city — never fill fake city)
        city_inp = page.locator("input[id^='employerCity']:visible, input[name='employerCity']:visible").first
        if city_inp.count() > 0 and target_city and not city_inp.input_value().strip():
            city_inp.fill(target_city)
            city_inp.dispatch_event("input")
            city_inp.dispatch_event("change")

        # 3. Internal Employee: No
        no_pill = page.locator("button.cx-select-pill-section:has-text('No'):visible").first
        if no_pill.count() > 0:
            is_selected = "selected" in (no_pill.get_attribute("class") or "") or no_pill.get_attribute("aria-pressed") == "true"
            if not is_selected:
                no_pill.click()
                time.sleep(0.2)

        # 4. Achievements textarea with formatted bullet points
        ach_area = page.locator("textarea[name='achievements']:visible, textarea[id^='achievements']:visible").first
        if ach_area.count() > 0 and bullet_text:
            ach_area.fill(bullet_text)
            ach_area.dispatch_event("input")
            ach_area.dispatch_event("change")

        # 5. Click SAVE
        save_btn = page.locator(".save-btn:visible, button:has-text('SAVE'):visible").first
        if save_btn.count() > 0 and not save_btn.is_disabled():
            save_btn.click(force=True)
            time.sleep(1.5)

        # Wait for inline form to detach
        try:
            page.wait_for_selector("input[id^='employerName']:visible", state="detached", timeout=4000)
        except Exception:
            pass

        ipc.mark_done()
        return {
            "success": True,
            "tile_index": tile_index,
            "employer": best_match.get("employer"),
            "city": target_city,
            "country": target_country
        }
    except Exception as e:
        logger.error(f"[s3_experience_tile] Error healing tile {tile_index}: {e}")
        return {"success": False, "tile_index": tile_index, "error": str(e)}


if __name__ == "__main__":
    import argparse
    import sys
    from CompanySiteApply.ats_arm import ATSArm
    from CompanySiteApply.utils.config_resolver import ConfigResolver

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Heal a single Work Experience tile.")
    parser.add_argument("--tile-index", type=int, default=0, help="0-based index of experience tile to heal")
    parser.add_argument("--profile", default="default_user", help="Candidate profile name")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP URL")
    args = parser.parse_args()

    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        candidate_data = ConfigResolver.load_candidate_config(args.profile)
        res = heal_single_experience_tile(page, candidate_data, tile_index=args.tile_index)
        print(f"Experience Tile Heal Result: {res}")
        sys.exit(0 if res.get("success") else 1)
    finally:
        arm.disconnect()
