# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:56:00 +05:30
# Issue / Context: Pluggable ATS finger for Workday application portals.
# Changes Made: Implemented WorkdayFinger supporting multi-step wizard, [data-automation-id] selectors,
#               and integrated Parser Doctor (LineWrapHealer + EducationHealer).
# Rationale: Workday is the primary platform where line-wrap sentence truncation and college
#            inversions occur during resume parsing.
# Preventative Notes: Always check data-automation-id attributes for reliable DOM targeting.
# ==============================================================================

import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.parser_doctor.review_verifier import ReviewVerifier
from CompanySiteApply.utils.dom_helpers import DOMHelpers


class WorkdayFinger(BaseATSFinger):
    """
    ATS Finger for Workday application portals (*.myworkdayjobs.com, custom Workday domains).
    """

    @property
    def platform_name(self) -> str:
        return "workday"

    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        """
        Detects Workday through domain patterns and [data-automation-id] attributes.
        """
        score = 0.0
        variant = "Unknown Workday"

        if "myworkdayjobs.com" in url or "myworkday.com" in url:
            score += 0.8
            variant = "Native Workday Jobs Portal"
        elif "/job/" in url or "/en-US/job/" in url:
            score += 0.2

        try:
            wd_elements = page.locator("[data-automation-id]").count()
            if wd_elements > 3:
                score += 0.5
                variant = "Workday Custom Domain Flow"
        except Exception:
            pass

        is_match = score >= 0.6
        return is_match, min(score, 1.0), variant

    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        """
        Catalogs current Workday form step.
        """
        raw_schema = DOMHelpers.extract_form_schema(page)
        url = page.url

        # Detect active Workday section
        active_step = "unknown"
        try:
            header_text = page.locator("[data-automation-id='pageHeader'], h2, h1").first.inner_text().lower()
            if "my information" in header_text or "contact" in header_text:
                active_step = "contact_information"
            elif "my experience" in header_text or "work experience" in header_text:
                active_step = "experience_and_education"
            elif "question" in header_text or "voluntary" in header_text:
                active_step = "screening_questions"
            elif "review" in header_text:
                active_step = "review_and_submit"
        except Exception:
            pass

        raw_schema["detected_step"] = active_step
        raw_schema["platform"] = self.platform_name
        return raw_schema

    def fill_step(self,
                  page: Any,
                  candidate_data: Dict[str, Any],
                  prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Fills fields on the active Workday step and executes Parser Doctor on Experience step.
        """
        schema = self.inspect_current_step(page)
        step = schema.get("detected_step")

        if step == "experience_and_education":
            # CRITICAL WORKDAY FIX: Heal line wraps in experience textareas and education entries
            exp_healed = ReviewVerifier.audit_and_heal_experience_descriptions(page)
            gt_edu = candidate_data.get("education") or []
            edu_healed = ReviewVerifier.audit_and_heal_education_fields(page, ground_truth_education=gt_edu)
            return {
                "success": True,
                "step": step,
                "healed_experience_descriptions": exp_healed,
                "healed_education_fields": edu_healed
            }
        else:
            # Standard field filling via [data-automation-id]
            return self._fill_workday_fields(page, candidate_data, prompt_user_callback)

    def _fill_workday_fields(self,
                             page: Any,
                             candidate_data: Dict[str, Any],
                             prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Fills common Workday inputs.
        """
        field_mappings = {
            "legalNameSection_firstName": candidate_data.get("first_name"),
            "legalNameSection_lastName": candidate_data.get("last_name"),
            "addressSection_addressLine1": candidate_data.get("address"),
            "addressSection_city": candidate_data.get("city") or candidate_data.get("location"),
            "addressSection_postalCode": candidate_data.get("pincode"),
            "phone-number": candidate_data.get("phone"),
        }

        filled = 0
        for auto_id, val in field_mappings.items():
            if not val:
                continue
            selector = f"[data-automation-id='{auto_id}'] input, input[data-automation-id='{auto_id}']"
            if page.locator(selector).count() > 0:
                if DOMHelpers.set_input_value_native(page, selector, val):
                    filled += 1

        return {"success": True, "filled_count": filled}

    def advance_step(self, page: Any) -> Tuple[bool, str]:
        """
        Advances to the next Workday step via bottom navigation buttons.
        """
        next_button_selectors = [
            "[data-automation-id='bottom-navigation-next-button']",
            "button:has-text('Save and Continue')",
            "button:has-text('Next')",
            "button:has-text('Submit')"
        ]

        for sel in next_button_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible() and not loc.first.is_disabled():
                loc.first.click()
                time.sleep(2.5)
                return True, "Clicked Workday next button"

        return False, "Could not locate visible Workday next button"

    def is_complete(self, page: Any) -> Tuple[bool, str]:
        """
        Detects Workday submission confirmation.
        """
        success_loc = page.locator("[data-automation-id='congratulationsPage'], :has-text('Application Submitted')")
        if success_loc.count() > 0 and success_loc.first.is_visible():
            return True, "Workday submission confirmed"
        return False, "Workday application in progress"
