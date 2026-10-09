# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [EDUCATION_SECTION_AGENT_INIT]
# Timestamp: 2026-10-09 20:36:00 +05:30
# Issue / Context: Needed a dedicated mini-agent for Education section diagnosis and surgical healing.
# Changes Made: Implemented EducationSectionAgent encapsulating modal opening, JET combobox
#               autocomplete selection for school, date/country mapping, and modal saving.
# Rationale: Eliminates ad-hoc scripting for education anomalies and guarantees zero side effects on Work Experience.
# Preventative Notes: Never interact with experience tiles when operating in this agent.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class EducationSectionAgent(BaseSectionAgent):
    """
    Specialist Mini-Agent for the Education section across ATS platforms (Oracle Cloud HCM, Workday, etc.).
    Operates with surgical precision on Degree, School autocomplete, Dates, Country, and Major fields.
    """

    @property
    def section_name(self) -> str:
        return "education"

    @property
    def target_stage(self) -> str:
        return "section_3"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("section") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/3" in url or "/apply/education" in url or "timeline" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits the Education section to identify missing or unmapped values.
        """
        try:
            cand = candidate_data.get("candidate", candidate_data)
            edu_list = cand.get("education") or candidate_data.get("education") or []
            target = edu_list[0] if edu_list else {}
            target_school = target.get("institution") or target.get("school") or ""
            target_degree = target.get("degree") or ""

            # Check if modal is currently open
            modal_open = page.locator("input[name='educationalEstablishment']:visible, input[id^='contentItemId']:visible").count() > 0

            if modal_open:
                school_val = page.locator("input[name='educationalEstablishment']:visible").first.input_value().strip()
                deg_val = page.locator("input[name='contentItemId']:visible, input[id^='contentItemId']:visible").first.input_value().strip()
                missing = []
                if not school_val or (target_school and target_school.lower() not in school_val.lower() and school_val.lower() not in target_school.lower()):
                    missing.append("school")
                if not deg_val or (target_degree and target_degree.lower() not in deg_val.lower()):
                    missing.append("degree")

                return {
                    "is_valid": len(missing) == 0,
                    "modal_open": True,
                    "missing_fields": missing,
                    "current_school": school_val,
                    "current_degree": deg_val
                }

            # Check summary tile on page
            tiles = page.locator(".apply-flow-profile-item-tile, .cx-tile").all_text_contents()
            edu_tiles = [t for t in tiles if ("degree" in t.lower() or "bachelor" in t.lower() or "master" in t.lower() or target_school.lower() in t.lower())]

            missing = []
            if not edu_tiles:
                missing.append("education_tile")
            else:
                combined = " ".join(edu_tiles).lower()
                if target_degree and target_degree.lower() not in combined:
                    missing.append("degree")
                if target_school:
                    tokens = [w for w in target_school.lower().split() if len(w) > 3]
                    if not any(t in combined for t in tokens):
                        missing.append("school")

            return {
                "is_valid": len(missing) == 0,
                "modal_open": False,
                "missing_fields": missing,
                "tiles_found": len(edu_tiles)
            }
        except Exception as e:
            logger.error(f"[EducationSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e), "missing_fields": ["audit_exception"]}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically heals the Education section.
        Opens modal if needed, fills missing fields with autocomplete handling, and clicks SAVE.
        """
        try:
            cand = candidate_data.get("candidate", candidate_data)
            edu_list = cand.get("education") or candidate_data.get("education") or []
            target = edu_list[0] if edu_list else {}

            target_school = str(target.get("institution") or target.get("school") or "").strip()
            target_degree = str(target.get("degree") or "").strip()
            target_country = str(target.get("country") or "India").strip()
            target_major = str(target.get("major") or target.get("field_of_study") or "").strip()
            target_month = str(target.get("end_month") or target.get("graduated_month") or "").strip()
            target_year = str(target.get("end_year") or target.get("graduated_year") or "").strip()

            # 1. Open modal if not open
            modal_open = page.locator("input[name='educationalEstablishment']:visible, input[id^='contentItemId']:visible").count() > 0
            if not modal_open:
                edu_tile = page.locator(".apply-flow-profile-item-tile:has-text('Degree'), .apply-flow-profile-item-tile:has-text('Education')").first
                if edu_tile.count() > 0:
                    edit_btn = edu_tile.locator(".apply-flow-profile-item-tile__edit-item-icon, button.icon-edit, [class*='edit-item-icon']").first
                    if edit_btn.count() > 0:
                        edit_btn.click(force=True)
                        time.sleep(1.0)
                else:
                    add_btn = page.locator("button:has-text('ADD EDUCATION'), button:has-text('Add Education')").first
                    if add_btn.count() > 0:
                        add_btn.click(force=True)
                        time.sleep(1.0)

            # 2. Heal Degree
            deg_input = page.locator("[id^='contentItemId']:visible, input[name='contentItemId']:visible").first
            if deg_input.count() > 0 and target_degree and not deg_input.input_value().strip():
                deg_input.fill(target_degree[:6])
                time.sleep(0.5)
                deg_input.press("ArrowDown")
                time.sleep(0.2)
                deg_input.press("Enter")
                time.sleep(0.3)

            # 3. Heal School Autocomplete
            school_input = page.locator("input[name='educationalEstablishment']:visible, [id^='educationalEstablishment']:visible").first
            if school_input.count() > 0 and target_school:
                current_school = school_input.input_value().strip()
                if not current_school or target_school.lower() not in current_school.lower():
                    school_input.click()
                    school_input.fill(target_school)
                    time.sleep(1.2)
                    clicked = page.evaluate('''(wantSchool) => {
                        const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                        const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="option"], [role="gridcell"]')).filter(isVis);
                        const wantLower = wantSchool.toLowerCase();
                        const opt = items.find(i => {
                            const t = i.innerText.trim().toLowerCase();
                            return t === wantLower || t.includes(wantLower) || wantLower.includes(t);
                        });
                        if (opt) { opt.click(); return true; }
                        return false;
                    }''', target_school)
                    if not clicked:
                        school_input.press("ArrowDown")
                        time.sleep(0.3)
                        school_input.press("Enter")
                    time.sleep(0.5)

            # 4. Heal Dates
            month_input = page.locator("[id^='month-endDate']:visible, input[name*='month-endDate']:visible").first
            if month_input.count() > 0 and target_month and month_input.input_value().strip().lower() != target_month.lower():
                month_input.click()
                time.sleep(0.3)
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="option"], li')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) opt.click();
                }''', target_month)
                time.sleep(0.3)

            year_input = page.locator("[id^='year-endDate']:visible, input[name*='year-endDate']:visible").first
            if year_input.count() > 0 and target_year and year_input.input_value().strip() != target_year:
                year_input.fill(target_year)

            # 5. Heal Country & Major
            country_input = page.locator("input[id^='countryCode']:visible, input[name='countryCode']:visible").first
            if country_input.count() > 0 and target_country and country_input.input_value().strip() != target_country:
                country_input.fill(target_country)
                time.sleep(0.3)
                country_input.press("ArrowDown")
                time.sleep(0.2)
                country_input.press("Enter")

            major_input = page.locator("[id^='areaOfStudy']:visible, input[name='areaOfStudy']:visible").first
            if major_input.count() > 0 and not major_input.input_value().strip() and target_major:
                major_input.fill(target_major)

            # 6. Click SAVE
            save_btn = page.locator(".save-btn:visible, button:has-text('SAVE'):visible, button:has-text('Save'):visible").first
            saved = False
            if save_btn.count() > 0 and not save_btn.is_disabled():
                save_btn.click(force=True)
                time.sleep(1.5)
                saved = True

            verified = self.verify(page, candidate_data)
            return {
                "success": saved and verified,
                "section": self.section_name,
                "saved": saved,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[EducationSectionAgent] Heal error: {e}")
            return {"success": False, "section": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        """
        Verifies that education modal is closed and summary tile renders correctly.
        """
        try:
            cand = candidate_data.get("candidate", candidate_data)
            edu_list = cand.get("education") or candidate_data.get("education") or []
            target = edu_list[0] if edu_list else {}
            target_school = target.get("institution") or target.get("school") or ""

            # Check modal is closed
            modal_visible = page.locator("input[name='educationalEstablishment']:visible").count() > 0
            if modal_visible:
                return False

            tiles = page.locator(".apply-flow-profile-item-tile, .cx-tile").all_text_contents()
            tokens = [w for w in target_school.lower().split() if len(w) > 3]
            for t in tiles:
                if any(tok in t.lower() for tok in tokens) or "bachelor" in t.lower() or "degree" in t.lower():
                    return True
            return False
        except Exception:
            return False
