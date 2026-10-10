# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [DIVERSITY_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:45:30 +05:30
# Issue / Context: Isolating demographic and diversity fields into a dedicated sub-agent.
# Changes Made: Built DiversitySubAgent dynamically mapping Ethnicity, Gender, and Military status.
# Rationale: Guarantees zero hardcoded demographic values and modular error handling.
# Preventative Notes: Never hardcode race, gender, or veteran status; strictly profile-driven.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class DiversitySubAgent(BaseSectionAgent):
    """
    Sub-Agent for Section 4 Diversity & Demographics: Ethnicity, Gender, Veteran Status.
    """

    @property
    def section_name(self) -> str:
        return "diversity"

    @property
    def target_stage(self) -> str:
        return "section_4"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/4" in url or "more-about-you" in url.lower() or "review" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            demographics = candidate_data.get("demographics") or {} if isinstance(candidate_data, dict) else {}

            # Check for red errors or missing dropdown selections
            errors = page.locator(".input-row:has-text('ETHNICITY') [class*='error'], .input-row:has-text('GENDER') [class*='error']").all_text_contents()
            err_list = [e.strip() for e in errors if e.strip()]

            # Inspect actual values of visible inputs
            eth_val = page.locator("input[id*='ETHNICITY']:visible").first.input_value() if page.locator("input[id*='ETHNICITY']:visible").count() > 0 else ""
            gen_val = page.locator("input[id*='GENDER']:visible").first.input_value() if page.locator("input[id*='GENDER']:visible").count() > 0 else ""
            mil_val = page.locator("input[id*='ATTRIBUTE16']:visible").first.input_value() if page.locator("input[id*='ATTRIBUTE16']:visible").count() > 0 else ""

            missing = []
            if demographics.get("ethnicity") and not eth_val.strip():
                missing.append("ethnicity")
            if demographics.get("gender") and not gen_val.strip():
                missing.append("gender")
            if demographics.get("military_status") and not mil_val.strip():
                missing.append("military_status")

            is_valid = len(err_list) == 0 and len(missing) == 0

            return {
                "is_valid": is_valid,
                "errors": err_list,
                "missing": missing,
                "ethnicity": eth_val,
                "gender": gen_val,
                "military_status": mil_val
            }
        except Exception as e:
            logger.error(f"[DiversitySubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            demographics = candidate_data.get("demographics") or {} if isinstance(candidate_data, dict) else {}

            ethnicity_val = str(demographics.get("ethnicity") or demographics.get("race") or cand.get("ethnicity") or cand.get("race") or "").strip()
            gender_val = str(demographics.get("gender") or cand.get("gender") or "").strip()
            military_val = str(demographics.get("military_status") or demographics.get("veteran") or cand.get("military_status") or "").strip()

            if ethnicity_val and "decline" not in ethnicity_val.lower():
                self._select_exact_dropdown(page, "ETHNICITY", ethnicity_val)
            if gender_val and "decline" not in gender_val.lower():
                self._select_exact_dropdown(page, "GENDER", gender_val)
            if military_val:
                self._select_exact_dropdown(page, "ATTRIBUTE16", military_val)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[DiversitySubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False

    def _select_exact_dropdown(self, page: Any, partial_id: str, exact_text: str):
        try:
            toggle = page.locator(f"button[id*='{partial_id}'][id$='-toggle-button']:visible").first
            if toggle.count() > 0:
                toggle.click()
            else:
                inp = page.locator(f"input[id*='{partial_id}']:visible").first
                if inp.count() > 0:
                    inp.click()
            time.sleep(0.5)

            clicked = page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-option, li[role="option"], [role="option"], [role="gridcell"]')).filter(isVis);
                const match = items.find(i => {
                    const t = i.innerText.trim().toLowerCase();
                    const w = targetText.trim().toLowerCase();
                    return t === w || t.startsWith(w) || t.includes(w) || (w === 'no' && (t.includes('no') || t.includes('not')));
                });
                if (match) {
                    match.click();
                    return true;
                }
                return false;
            }''', exact_text)

            if not clicked:
                inp = page.locator(f"input[id*='{partial_id}']:visible").first
                if inp.count() > 0:
                    inp.fill(exact_text)
                    time.sleep(0.3)
                    inp.press("Enter")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"[DiversitySubAgent] Failed selecting {partial_id}: {e}")
