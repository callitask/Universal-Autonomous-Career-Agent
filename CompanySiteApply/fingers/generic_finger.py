# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:58:00 +05:30
# Issue / Context: Generic adaptive ATS finger for bespoke and uncatalogued corporate career forms.
# Changes Made: Implemented GenericAdaptiveFinger to safely inspect, fill, and advance bespoke portals.
# Rationale: Ensures the system gracefully handles unknown custom React/Vue/Angular career forms.
# Preventative Notes: Respects HoneypotGuard and skips decoy inputs; prompts for ambiguous fields.
# ==============================================================================

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.parser_doctor.review_verifier import ReviewVerifier
from CompanySiteApply.utils.dom_helpers import DOMHelpers
from CompanySiteApply.utils.honeypot_guard import HoneypotGuard


class GenericAdaptiveFinger(BaseATSFinger):
    """
    Fallback adaptive finger for unknown, custom, or bespoke company career portals.
    """

    @property
    def platform_name(self) -> str:
        return "generic_adaptive"

    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        # Always can handle as a fallback with low baseline confidence
        return True, 0.1, "Generic Adaptive Career Portal"

    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        raw_schema = DOMHelpers.extract_form_schema(page)
        for inp in raw_schema.get("inputs", []):
            inp["is_honeypot"] = HoneypotGuard.is_honeypot(inp)
        raw_schema["detected_step"] = "adaptive_form_step"
        raw_schema["platform"] = self.platform_name
        return raw_schema

    def fill_step(self,
                  page: Any,
                  candidate_data: Dict[str, Any],
                  prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        schema = self.inspect_current_step(page)
        filled_count = 0

        # Also run parser doctor on any existing filled textareas
        ReviewVerifier.audit_and_heal_experience_descriptions(page)

        for inp in schema.get("inputs", []):
            if inp.get("is_honeypot") or inp.get("disabled") or inp.get("readOnly"):
                continue

            name = inp.get("name") or inp.get("id") or inp.get("labelText") or ""
            name_lower = name.lower()
            val = None

            if "first" in name_lower and "name" in name_lower:
                val = candidate_data.get("first_name")
            elif "last" in name_lower and "name" in name_lower:
                val = candidate_data.get("last_name")
            elif "email" in name_lower:
                val = candidate_data.get("email")
            elif "phone" in name_lower or "mobile" in name_lower:
                val = candidate_data.get("phone")
            elif "city" in name_lower or "location" in name_lower:
                val = candidate_data.get("location") or candidate_data.get("city")

            if not val and inp.get("required") and prompt_user_callback:
                val = prompt_user_callback(f"Enter value for required field '{name}':", None)

            if val:
                sel = f"#{inp['id']}" if inp.get("id") else f"[name='{inp.get('name')}']"
                if DOMHelpers.set_input_value_native(page, sel, val):
                    filled_count += 1

        return {"success": True, "filled_count": filled_count}

    def advance_step(self, page: Any) -> Tuple[bool, str]:
        buttons = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Submit')",
            "button:has-text('Apply')"
        ]
        for sel in buttons:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible() and not loc.first.is_disabled():
                loc.first.click()
                time.sleep(2.0)
                return True, f"Clicked button: {sel}"
        return False, "Could not identify visible submit or next button"

    def is_complete(self, page: Any) -> Tuple[bool, str]:
        text_loc = page.locator(":has-text('Application Submitted'), :has-text('Thank you for applying')")
        if text_loc.count() > 0 and text_loc.first.is_visible():
            return True, "Confirmation text detected"
        return False, "Not confirmed"
