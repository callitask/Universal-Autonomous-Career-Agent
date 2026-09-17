# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:57:00 +05:30
# Issue / Context: Pluggable ATS finger for Greenhouse job boards.
# Changes Made: Implemented GreenhouseFinger for boards.greenhouse.io / embedded Greenhouse forms.
# Rationale: Greenhouse is widely used by high-growth tech companies and enterprise startups.
# Preventative Notes: Scopes to #application_form to prevent header navigation interference.
# ==============================================================================

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.utils.dom_helpers import DOMHelpers


class GreenhouseFinger(BaseATSFinger):
    """
    ATS Finger for Greenhouse application boards (boards.greenhouse.io, embedded forms).
    """

    @property
    def platform_name(self) -> str:
        return "greenhouse"

    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        score = 0.0
        variant = "Unknown Greenhouse"

        if "greenhouse.io" in url or "gh_jid" in url:
            score += 0.8
            variant = "Native Greenhouse Board"

        try:
            if page.locator("#application_form, form#application_form, #embedded_application").count() > 0:
                score += 0.5
                variant = "Greenhouse Embedded Form"
        except Exception:
            pass

        return score >= 0.6, min(score, 1.0), variant

    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        raw_schema = DOMHelpers.extract_form_schema(page)
        raw_schema["detected_step"] = "single_page_application"
        raw_schema["platform"] = self.platform_name
        return raw_schema

    def fill_step(self,
                  page: Any,
                  candidate_data: Dict[str, Any],
                  prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Fills standard Greenhouse fields: first_name, last_name, email, phone, linkedin.
        """
        mappings = {
            "#first_name, input[name*='first_name']": candidate_data.get("first_name"),
            "#last_name, input[name*='last_name']": candidate_data.get("last_name"),
            "#email, input[name*='email']": candidate_data.get("email"),
            "#phone, input[name*='phone']": candidate_data.get("phone"),
            "input[autocomplete='custom-question-linkedin']": candidate_data.get("linkedin_url"),
        }

        filled = 0
        for sel, val in mappings.items():
            if val and DOMHelpers.set_input_value_native(page, sel, val):
                filled += 1

        return {"success": True, "filled_count": filled}

    def advance_step(self, page: Any) -> Tuple[bool, str]:
        submit_btn = page.locator("#submit_app, input[type='submit'][value*='Submit'], button:has-text('Submit Application')")
        if submit_btn.count() > 0 and submit_btn.first.is_visible():
            submit_btn.first.click()
            time.sleep(2.0)
            return True, "Clicked Greenhouse submit button"
        return False, "Submit button not found"

    def is_complete(self, page: Any) -> Tuple[bool, str]:
        if "confirmation" in page.url:
            return True, "Confirmation URL reached"
        success_loc = page.locator("#application_confirmation, :has-text('Thank you for applying')")
        if success_loc.count() > 0 and success_loc.first.is_visible():
            return True, "Confirmation text detected"
        return False, "Application pending"
