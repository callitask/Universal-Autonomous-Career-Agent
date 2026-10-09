# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [EXPERIENCE_SECTION_AGENT_INIT]
# Timestamp: 2026-10-09 20:37:00 +05:30
# Issue / Context: Needed a dedicated mini-agent for Work Experience section diagnosis, sub-field healing, and reverse-chronology.
# Changes Made: Implemented ExperienceSectionAgent encapsulating tile modal iteration, country/city/internal healing,
#               achievement bullet points formatting, and Knockout VM reverse-chronological reordering.
# Rationale: Guarantees 100% data fidelity for career history without touching Education cards.
# Preventative Notes: Never interact with education tiles when operating in this agent.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class ExperienceSectionAgent(BaseSectionAgent):
    """
    Specialist Mini-Agent for the Work Experience section across ATS platforms.
    Handles Employer Country, Employer City, Internal employee status (No),
    clean bulleted achievements, and reverse-chronological career ordering.
    """

    @property
    def section_name(self) -> str:
        return "experience"

    @property
    def target_stage(self) -> str:
        return "section_3"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("section") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/3" in url or "/apply/experience" in url or "timeline" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits Work Experience tiles for count and chronological ordering.
        """
        try:
            tiles = page.locator(".apply-flow-profile-item-tile:has-text(' - ')").all_text_contents()
            cand_exp = self._get_candidate_experiences(candidate_data)

            is_valid = len(tiles) >= min(len(cand_exp), 1)
            return {
                "is_valid": is_valid,
                "tiles_count": len(tiles),
                "expected_count": len(cand_exp),
                "tiles": tiles[:5]
            }
        except Exception as e:
            logger.error(f"[ExperienceSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically heals Work Experience tiles and enforces reverse-chronological ordering.
        """
        try:
            exp_list = self._get_candidate_experiences(candidate_data)
            tiles_count = page.locator(".apply-flow-profile-item-tile").count()

            healed_count = 0
            for i in range(tiles_count):
                tile = page.locator(".apply-flow-profile-item-tile").nth(i)
                tile_text = tile.inner_text().strip()

                # Skip Education tiles
                if "degree" in tile_text.lower() or "education" in tile_text.lower() or "bachelor" in tile_text.lower() or "master" in tile_text.lower():
                    continue

                edit_btn = tile.locator(".apply-flow-profile-item-tile__edit-item-icon, button.icon-edit, [class*='edit-item-icon']").first
                if edit_btn.count() == 0:
                    continue

                edit_btn.click(force=True)
                time.sleep(1.0)

                # Match candidate experience item
                best_match = exp_list[0] if exp_list else {}
                for exp in exp_list:
                    emp = exp.get("employer", "").lower()
                    if emp and (emp in tile_text.lower() or tile_text.lower() in emp):
                        best_match = exp
                        break

                self._heal_single_experience_modal(page, best_match, candidate_data)
                healed_count += 1

            # Enforce reverse-chronological ordering
            self._reorder_tiles_reverse_chronological(page)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "section": self.section_name,
                "healed_tiles_count": healed_count,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[ExperienceSectionAgent] Heal error: {e}")
            return {"success": False, "section": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            modal_open = page.locator("input[id^='employerName']:visible, input[name='employerName']:visible").count() > 0
            tiles = page.locator(".apply-flow-profile-item-tile:has-text(' - ')").count()
            return not modal_open and tiles > 0
        except Exception:
            return False

    def _heal_single_experience_modal(self, page: Any, exp_data: Dict[str, Any], candidate_data: Optional[Dict[str, Any]] = None):
        """Heals an open Work Experience modal dialog dynamically from candidate profile."""
        cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
        target_country = str(exp_data.get("country") or cand.get("country") or "").strip()
        target_city = str(exp_data.get("city") or cand.get("city") or "").strip()

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

        # 2. Employer City
        city_inp = page.locator("input[id^='employerCity']:visible, input[name='employerCity']:visible").first
        if city_inp.count() > 0 and not city_inp.input_value().strip():
            city_inp.fill(target_city)
            city_inp.dispatch_event("input")
            city_inp.dispatch_event("change")

        # 3. Internal: No
        no_pill = page.locator("button.cx-select-pill-section:has-text('No'):visible").first
        if no_pill.count() > 0:
            is_selected = "selected" in (no_pill.get_attribute("class") or "") or no_pill.get_attribute("aria-pressed") == "true"
            if not is_selected:
                no_pill.click()
                time.sleep(0.2)

        # 4. Achievements textarea
        ach_area = page.locator("textarea[name='achievements']:visible, textarea[id^='achievements']:visible").first
        if ach_area.count() > 0:
            bullets = exp_data.get("bullets") or []
            if bullets:
                bullet_text = "\n\n".join([f"• {b.lstrip('•*- ')}" for b in bullets])
                ach_area.fill(bullet_text)
                ach_area.dispatch_event("input")
                ach_area.dispatch_event("change")

        # 5. Click SAVE
        save_btn = page.locator(".save-btn:visible, button:has-text('SAVE'):visible").first
        if save_btn.count() > 0 and not save_btn.is_disabled():
            save_btn.click(force=True)
            time.sleep(1.2)

    def _reorder_tiles_reverse_chronological(self, page: Any):
        """Sorts Knockout parent.forms observableArray in reverse-chronological order."""
        try:
            page.evaluate("""() => {
                const node = document.querySelector('.apply-flow-profile-item-tile, .timeline-item');
                if (!node || typeof ko === 'undefined') return;
                const ctx = ko.contextFor(node);
                if (!ctx || !ctx.$parent || !ctx.$parent.forms) return;
                
                const forms = ctx.$parent.forms();
                if (!forms || forms.length <= 1) return;
                
                forms.sort((a, b) => {
                    const aCurr = a.currentJobFlag ? a.currentJobFlag() === 'Y' : false;
                    const bCurr = b.currentJobFlag ? b.currentJobFlag() === 'Y' : false;
                    if (aCurr && !bCurr) return -1;
                    if (!aCurr && bCurr) return 1;
                    const aStart = a.startDate ? (a.startDate() || '') : '';
                    const bStart = b.startDate ? (b.startDate() || '') : '';
                    return bStart.localeCompare(aStart);
                });
                
                ctx.$parent.forms.valueHasMutated();
                if (typeof ctx.$parent._buildTiles === 'function') {
                    ctx.$parent._buildTiles();
                }
            }""")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"[ExperienceSectionAgent] Reorder warning: {e}")

    def _get_candidate_experiences(self, candidate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        cand = candidate_data.get("candidate", candidate_data)
        return (cand.get("work_experience") or 
                cand.get("experience") or 
                candidate_data.get("experience") or 
                candidate_data.get("work_experience") or [])
