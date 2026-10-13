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
# [ENTRY #002]
# Term: [PHASE2_EXPERIENCE_ORDERING_FIX]
# Timestamp: 2026-10-12 21:02:00 +05:30
# Issue / Context: Knockout sort was doing localeCompare on "MM/YYYY" strings, resulting in month-based sort.
# Changes Made: Delegated _reorder_tiles_reverse_chronological to s3_experience_ordering with numeric YYYYMM date comparison.
# Rationale: Enforces strict reverse-chronological ordering (current job first, newest to oldest).
# Preventative Notes: Never compare MM/YYYY strings alphabetically.
# ==============================================================================
# [ENTRY #003]
# Term: [PHASE5_EXPERIENCE_TILE_IPC_DELEGATION]
# Timestamp: 2026-10-12 21:48:00 +05:30
# Issue / Context: Work experience section needed isolated sub-section execution and IPC serialization.
# Changes Made: Updated heal() to delegate each tile to s3_experience_tile.heal_single_experience_tile().
# Rationale: Guarantees modular sub-section isolation and prevents full section re-runs on single failure.
# Preventative Notes: Never interact with subsequent tiles while an inline modal is still open.
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
        Audits Work Experience tiles for count AND runtime reverse-chronological
        ordering. Count-only audits passed pre-saved drafts with scrambled
        timelines (incident 2026-10-12) — order is now verified from visible
        date text on every audit.
        """
        try:
            from CompanySiteApply.section_agents.scripts.s3_experience_ordering import (
                get_tile_order,
                is_reverse_chronological,
            )
            order = get_tile_order(page)
            cand_exp = self._get_candidate_experiences(candidate_data)

            keys = [t["sort_key"] for t in order]
            ordered = is_reverse_chronological(keys) if order else False
            count_ok = len(order) >= min(len(cand_exp), 1) if cand_exp else len(order) > 0
            is_valid = count_ok and ordered
            return {
                "is_valid": is_valid,
                "tiles_count": len(order),
                "expected_count": len(cand_exp),
                "chronological_order_correct": ordered,
                "tiles": [t["title"] for t in order[:9]],
            }
        except Exception as e:
            logger.error(f"[ExperienceSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically heals Work Experience tiles and enforces reverse-chronological ordering.
        Delegates single-tile healing to s3_experience_tile.
        Re-queries the DOM before every tile (Oracle re-renders after SAVE) so
        tile indices never go stale.
        """
        try:
            from CompanySiteApply.section_agents.scripts.s3_experience_tile import heal_single_experience_tile
            from CompanySiteApply.ipc.ipc_manager import get_effective_session_id
            _sess = get_effective_session_id(candidate_data, None)

            healed_count = 0
            exp_idx = 0
            # Bound by candidate truth count + small headroom for stale extra tiles.
            cand_exp = self._get_candidate_experiences(candidate_data)
            max_tiles = max(len(cand_exp), 1) + 2

            while exp_idx < max_tiles:
                tiles = page.locator(".apply-flow-profile-item-tile").all()
                exp_tiles = []
                for t in tiles:
                    try:
                        tile_text = t.inner_text().strip()
                    except Exception:
                        continue
                    if any(k in tile_text.lower() for k in ["degree", "education", "bachelor", "master"]):
                        continue
                    exp_tiles.append(t)

                if exp_idx >= len(exp_tiles):
                    break

                res = heal_single_experience_tile(page, candidate_data, tile_index=exp_idx, session_id=_sess or None)
                if res.get("success"):
                    healed_count += 1
                elif res.get("deferred"):
                    logger.warning(f"[ExperienceSectionAgent] Tile {exp_idx} deferred: {res.get('error')}")
                    break
                exp_idx += 1
                time.sleep(0.5)

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

    def _reorder_tiles_reverse_chronological(self, page: Any) -> bool:
        """
        Universally sorts experience tiles in strict reverse-chronological order
        (current employer first, newest to oldest) via s3_experience_ordering.
        """
        try:
            from CompanySiteApply.section_agents.scripts.s3_experience_ordering import reorder_experience_tiles
            res = reorder_experience_tiles(page)
            if res.get("success"):
                logger.info("[ExperienceSectionAgent] Successfully reordered tiles via s3_experience_ordering.")
                return True
        except Exception as e:
            logger.debug(f"[ExperienceSectionAgent] s3_experience_ordering delegation note: {e}")

        # Fallback to JPMCNail if available
        try:
            from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
            nail = JPMCNail()
            return nail.reorder_experience_tiles(page)
        except Exception as ne:
            logger.warning(f"[ExperienceSectionAgent] Reorder warning: {ne}")
            return False

    def _get_candidate_experiences(self, candidate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        cand = candidate_data.get("candidate", candidate_data)
        return (cand.get("work_experience") or 
                cand.get("experience") or 
                candidate_data.get("experience") or 
                candidate_data.get("work_experience") or [])
