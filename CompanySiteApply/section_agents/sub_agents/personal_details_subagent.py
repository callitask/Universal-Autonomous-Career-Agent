# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [PERSONAL_DETAILS_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:42:00 +05:30
# Issue / Context: Decomposing Section 1 into dedicated, isolated sub-agents to avoid ripple effects.
# Changes Made: Built PersonalDetailsSubAgent handling Name, Email, Phone, Address, City, Country, and Postal code.
# Rationale: Provides surgical repair for contact fields without touching Preferred Locations or other sections.
# Preventative Notes: Never hardcode candidate PII or location values.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class PersonalDetailsSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Page 1 Personal Details: Name, Email, Phone, Address, City, Country, Zip.
    """

    @property
    def section_name(self) -> str:
        return "personal_details"

    @property
    def target_stage(self) -> str:
        return "section_1"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/1" in url or "personal" in url.lower() or "profile" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            missing = []

            # Check core inputs
            fn = page.locator("input[name*='firstName']:visible, input[id*='firstName']:visible").first
            if fn.count() > 0 and not fn.input_value().strip():
                missing.append("first_name")

            ln = page.locator("input[name*='lastName']:visible, input[id*='lastName']:visible").first
            if ln.count() > 0 and not ln.input_value().strip():
                missing.append("last_name")

            city = page.locator("input[id^='city']:visible, input[name='city']:visible").first
            if city.count() > 0 and not city.input_value().strip():
                missing.append("city")

            # Check any inline error banners
            errors = page.locator(".cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message").all_text_contents()
            err_list = [e.strip() for e in errors if e.strip() and "saved" not in e.lower() and "all set" not in e.lower() and "successfully" not in e.lower()]

            return {
                "is_valid": len(missing) == 0 and len(err_list) == 0,
                "missing_fields": missing,
                "errors": err_list
            }
        except Exception as e:
            logger.error(f"[PersonalDetailsSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            target_jobs = candidate_data.get("target_jobs") or {} if isinstance(candidate_data, dict) else {}
            locations_list = target_jobs.get("locations") or []

            city_val = str(cand.get("city") or cand.get("location") or (locations_list[0] if locations_list else "")).strip()
            country_val = str(cand.get("country") or "").strip()
            if not country_val and "+91" in str(cand.get("phone", "")):
                country_val = "India"

            # 1. Address Country combobox
            country_input = page.locator("input[name='country']:visible, input[id^='country-']:not([id*='phoneNumber']):visible").first
            if country_input.count() > 0 and not country_input.input_value().strip() and country_val:
                country_input.fill(country_val)
                time.sleep(0.3)
                country_input.press("ArrowDown")
                time.sleep(0.2)
                country_input.press("Enter")

            # 2. City
            city_input = page.locator("input[id^='city']:visible, input[name='city']:visible").first
            if city_input.count() > 0 and not city_input.input_value().strip() and city_val:
                city_input.fill(city_val)
                city_input.dispatch_event("input")
                city_input.dispatch_event("change")

            # 3. Address Line 1
            addr1 = str(cand.get("address_line_1") or cand.get("address") or "").strip()
            addr_input = page.locator("input[name='addressLine1']:visible, input[id^='addressLine1']:visible").first
            if addr_input.count() > 0 and not addr_input.input_value().strip() and addr1:
                addr_input.fill(addr1)
                addr_input.dispatch_event("input")
                addr_input.dispatch_event("change")

            # 4. Postal Code
            zip_val = str(cand.get("postal_code") or cand.get("zip") or cand.get("zip_code") or "").strip()
            zip_input = page.locator("input[name='postalCode']:visible, input[id^='postalCode']:visible").first
            if zip_input.count() > 0 and not zip_input.input_value().strip() and zip_val:
                zip_input.fill(zip_val)
                zip_input.dispatch_event("input")
                zip_input.dispatch_event("change")

            # 5. Title / Salutation pill if available
            salutation = str(cand.get("salutation") or cand.get("title") or "").strip()
            if salutation:
                sal_pill = page.locator(f"button.cx-select-pill-section:has-text('{salutation}')").first
                if sal_pill.count() > 0 and "selected" not in (sal_pill.get_attribute("class") or ""):
                    sal_pill.click()

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[PersonalDetailsSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
