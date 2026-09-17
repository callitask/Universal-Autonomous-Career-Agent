# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:53:00 +05:30
# Issue / Context: ATS review step verifier & comprehensive parser doctor.
# Changes Made: Implemented ReviewVerifier to audit and heal populated form fields in DOM.
# Rationale: Scans all textareas (experience descriptions) and education inputs on active ATS page,
#            heals formatting anomalies, and injects corrected text back into DOM.
# Preventative Notes: Safely dispatches native events via DOMHelpers.
# ==============================================================================

from typing import Any, Dict, List, Optional
from CompanySiteApply.parser_doctor.line_wrap_healer import LineWrapHealer
from CompanySiteApply.parser_doctor.education_healer import EducationHealer
from CompanySiteApply.utils.dom_helpers import DOMHelpers


class ReviewVerifier:
    """
    Coordinates post-upload verification and healing of ATS form fields.
    """

    @classmethod
    def audit_and_heal_experience_descriptions(cls, page: Any) -> List[Dict[str, Any]]:
        """
        Scans all visible textareas on page (typically role descriptions), checks for
        broken margin line wraps, heals them, and updates the DOM.
        """
        healed_reports = []
        try:
            textareas = page.locator("textarea:visible").all()
            for idx, ta in enumerate(textareas):
                raw_text = ta.input_value()
                if not raw_text or len(raw_text.strip()) < 20:
                    continue

                healed_text = LineWrapHealer.heal_text(raw_text)
                if healed_text != raw_text:
                    # Update DOM
                    ta_id = ta.get_attribute("id")
                    if ta_id:
                        selector = f"textarea#{ta_id}"
                    else:
                        selector = f"textarea:nth-of-type({idx + 1})"

                    success = DOMHelpers.set_input_value_native(page, selector, healed_text)
                    healed_reports.append({
                        "field_index": idx,
                        "selector": selector,
                        "original_length": len(raw_text),
                        "healed_length": len(healed_text),
                        "success": success
                    })
        except Exception as e:
            healed_reports.append({"error": str(e)})

        return healed_reports

    @classmethod
    def audit_and_heal_education_fields(cls, page: Any, ground_truth_education: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Scans education section fields on page, validates against ground truth,
        and corrects inverted school/degree inputs.
        """
        reports = []
        # Target common education input identifiers across Workday, Oracle, and Greenhouse
        school_selectors = [
            "input[id*='school']", "input[name*='school']",
            "input[id*='institution']", "input[name*='institution']",
            "input[data-automation-id*='school']"
        ]
        degree_selectors = [
            "input[id*='degree']", "input[name*='degree']",
            "input[data-automation-id*='degree']"
        ]

        try:
            school_el = None
            school_sel = ""
            for s in school_selectors:
                if page.locator(s).count() > 0 and page.locator(s).first.is_visible():
                    school_el = page.locator(s).first
                    school_sel = s
                    break

            degree_el = None
            degree_sel = ""
            for d in degree_selectors:
                if page.locator(d).count() > 0 and page.locator(d).first.is_visible():
                    degree_el = page.locator(d).first
                    degree_sel = d
                    break

            if school_el and degree_el:
                parsed_school = school_el.input_value()
                parsed_degree = degree_el.input_value()

                diagnosis = EducationHealer.diagnose_and_heal_entry(
                    parsed_school, parsed_degree, ground_truth_education=ground_truth_education
                )

                if diagnosis.get("was_modified"):
                    DOMHelpers.set_input_value_native(page, school_sel, diagnosis["school"])
                    DOMHelpers.set_input_value_native(page, degree_sel, diagnosis["degree"])
                    reports.append({
                        "school_selector": school_sel,
                        "degree_selector": degree_sel,
                        "diagnosis": diagnosis
                    })
        except Exception as e:
            reports.append({"error": str(e)})

        return reports
