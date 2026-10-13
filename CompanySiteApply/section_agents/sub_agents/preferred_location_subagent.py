# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [PREFERRED_LOCATION_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:42:30 +05:30
# Issue / Context: Preferred Location combobox was frequently skipped or unverified during onboarding.
# Changes Made: Built PreferredLocationSubAgent encapsulating dropdown toggle, option scoring,
#               pill attachment verification, and multi-location support.
# Rationale: Isolates facility selection into an independent mini-agent that can be audited and healed surgically.
# Preventative Notes: Never hardcode facility or city strings; dynamically resolve from candidate profile and job data.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class PreferredLocationSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Page 1 Preferred Locations.
    Interacts with the Oracle HCM multi-select combobox to select up to 3 work locations in order of preference.
    """

    @property
    def section_name(self) -> str:
        return "preferred_location"

    @property
    def target_stage(self) -> str:
        return "section_1"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            if "/apply/section/1" not in url and "profile" not in url.lower() and "personal" not in url.lower():
                return False
            return page.locator(".apply-flow-block--preferred-locations, [class*='preferred-location']").count() > 0
        except Exception:
            return False

    def _find_location_block(self, page: Any) -> Any:
        """Locate the preferred-location container across Oracle HCM variants.

        Incident 210765001: CX_1002 renders the JET combobox as
        input[name='preferredLocations'] inside generic layout containers —
        the legacy .apply-flow-block--preferred-locations class is absent.
        """
        for selector in (
            ".apply-flow-block--preferred-locations",
            "[class*='preferred-location']",
            "input[name='preferredLocations']",
            "[id^='preferredLocations-']",
        ):
            try:
                loc = page.locator(selector).first
                if loc.count() > 0:
                    return loc
            except Exception:
                continue
        return None

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            anchor = self._find_location_block(page)
            if anchor is None:
                # No preferred locations control on this page/job
                return {"is_valid": True, "present": False, "pill_count": 0}

            pref_block = page.locator(".apply-flow-block--preferred-locations, [class*='preferred-location']").first
            if pref_block.count() == 0:
                # JET input variant: scope pill search to the input's container
                pills = page.evaluate('''() => {
                    const inp = document.querySelector("input[name='preferredLocations'], [id^='preferredLocations-']");
                    if (!inp) return [];
                    const scope = inp.closest('.cx-form-item, .standard-apply-flow-profile-block, .input-row, .app-form-item') || document;
                    const pillEls = Array.from(scope.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill'));
                    return pillEls.map(p => p.innerText.trim()).filter(Boolean);
                }''')
            else:
                # Check selected pills
                pills = page.evaluate('''() => {
                    const block = document.querySelector('.apply-flow-block--preferred-locations, [class*="preferred-location"]');
                    if (!block) return [];
                    const pillEls = Array.from(block.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill'));
                    return pillEls.map(p => p.innerText.trim()).filter(Boolean);
                }''')

            # Check error messages
            errors = pref_block.locator(".cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message").all_text_contents()
            err_list = [e.strip() for e in errors if e.strip()]

            is_valid = len(pills) > 0 and len(err_list) == 0
            return {
                "is_valid": is_valid,
                "present": True,
                "pill_count": len(pills),
                "selected_locations": pills,
                "errors": err_list
            }
        except Exception as e:
            logger.error(f"[PreferredLocationSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            anchor = self._find_location_block(page)
            if anchor is None:
                return {"success": True, "subagent": self.section_name, "message": "No preferred location block present"}

            # Check existing pills
            audit_res = self.audit(page, candidate_data)
            if audit_res.get("is_valid") and audit_res.get("pill_count", 0) > 0:
                logger.info("[PreferredLocationSubAgent] Preferred location already populated.")
                return {"success": True, "subagent": self.section_name, "already_valid": True}

            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            target_jobs = candidate_data.get("target_jobs") or {} if isinstance(candidate_data, dict) else {}
            job_locations = target_jobs.get("locations") or []

            # Priority order for preferred location:
            # 1. candidate['preferred_locations']
            # 2. candidate['location'] / candidate['city']
            # 3. target_jobs['locations']
            pref_candidates = []
            if isinstance(cand.get("preferred_locations"), list):
                pref_candidates.extend(cand["preferred_locations"])
            elif cand.get("preferred_locations"):
                pref_candidates.append(str(cand["preferred_locations"]))

            if cand.get("city"):
                pref_candidates.append(str(cand["city"]))
            if cand.get("location"):
                pref_candidates.append(str(cand["location"]))
            if job_locations:
                pref_candidates.extend(job_locations)

            # Open the dropdown: focus/click the JET input first (scar 2026-10-08 —
            # the collapsed toggle button has zero width and swallows clicks),
            # falling back to the toggle button on legacy markup.
            opened = False
            for opener in (
                "input[name='preferredLocations']:visible",
                "[id^='preferredLocations-']:visible",
            ):
                try:
                    inp = page.locator(opener).first
                    if inp.count() > 0 and inp.is_visible():
                        inp.click()
                        time.sleep(0.6)
                        opened = True
                        break
                except Exception:
                    continue
            if not opened:
                pref_block = page.locator(".apply-flow-block--preferred-locations, [class*='preferred-location']").first
                toggle = pref_block.locator("button[id*='preferredLocations'][id$='-toggle-button'], button.icon-dropdown-arrow, button").first
                if toggle.count() > 0:
                    toggle.click()
                    time.sleep(1.0)

            # Select matching option in dropdown
            selected_info = page.evaluate('''(searchTerms) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(isVis);
                if (items.length === 0) return { selected: false, reason: "no_items_found" };

                // 1. Try to find match from search terms
                for (const term of searchTerms) {
                    if (!term) continue;
                    const cleanTerm = term.toLowerCase().trim();
                    const match = items.find(i => i.innerText.toLowerCase().includes(cleanTerm));
                    if (match) {
                        const txt = match.innerText.trim();
                        match.click();
                        return { selected: true, text: txt, matchedTerm: term };
                    }
                }

                // 2. Fallback to first available option
                const firstTxt = items[0].innerText.trim();
                items[0].click();
                return { selected: true, text: firstTxt, matchedTerm: "first_fallback" };
            }''', pref_candidates)

            logger.info(f"[PreferredLocationSubAgent] Selection result: {selected_info}")
            time.sleep(1.0)

            # Commit the selection (blur + Escape) so Oracle JET persists the
            # pill to the draft model before any NEXT navigation re-renders.
            try:
                page.keyboard.press("Escape")
                time.sleep(0.4)
            except Exception:
                pass

            # Verify pill creation
            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "selection_info": selected_info,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[PreferredLocationSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
