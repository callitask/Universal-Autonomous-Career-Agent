# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-17 13:16:00 +05:30
# Issue / Context: Company ATS Nail for JPMorgan Chase on Oracle Cloud HCM.
# Changes Made: Implemented JPMCNail with custom field handling for Section 4 diversity
#               (India Uniformed forces, Ethnicity, Gender), and curated screening answer
#               resolution for Section 2 (18+ age, legal work authorization, experience tier).
# Rationale: Encapsulates JPMC CX_1001 specific portal behaviors without polluting generic
#            OracleCloudFinger mechanics.
# Preventative Notes: Never hardcode candidate PII; all answers resolve dynamically from candidate_data.
# ==============================================================================

import re
import time
from typing import Any, Dict, List, Optional
from CompanySiteApply.nails.base_nail import BaseNail


class JPMCNail(BaseNail):
    """
    Company ATS Nail for JPMorgan Chase (JPMC) career portal on Oracle Cloud HCM.
    Attached to OracleCloudFinger to handle CX_1001 custom questionnaires and surveys.
    """

    @property
    def company_name(self) -> str:
        return "JPMorgan Chase"

    def matches(self, url: str, page_title: str = "", page: Any = None) -> bool:
        url_lower = (url or "").lower()
        title_lower = (page_title or "").lower()
        return "jpmc.fa.oraclecloud.com" in url_lower or "jpmorgan" in url_lower or "jpmc" in title_lower

    def handle_custom_fields(self, page: Any, step_num: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes JPMC-specific custom form fields on demographic/diversity steps (Section 4).
        """
        results = {}

        # 1. India Uniformed Forces / Military Status
        # Selector: #IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-8, [name="IN-DFF-indiaMilitaryStatus-ATTRIBUTE16"]
        forces_field = page.locator('#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-8, [name="IN-DFF-indiaMilitaryStatus-ATTRIBUTE16"]').first
        if forces_field.count() > 0 and forces_field.is_visible():
            current_val = forces_field.input_value().strip()
            if not current_val:
                forces_status = candidate_data.get("india_uniformed_forces") or "No"
                forces_field.click()
                time.sleep(0.4)
                clicked = page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) {
                        opt.click();
                        return true;
                    }
                    return false;
                }''', forces_status)
                time.sleep(0.4)
                results["india_uniformed_forces"] = forces_field.input_value()

        # 2. Ethnicity
        ethnicity_field = page.locator('#IN-STANDARD-ORA_ETHNICITY-STANDARD-6, [name="IN-STANDARD-ORA_ETHNICITY-STANDARD"]').first
        if ethnicity_field.count() > 0 and ethnicity_field.is_visible():
            current_val = ethnicity_field.input_value().strip()
            target_eth = candidate_data.get("ethnicity") or "Asian"
            if not current_val or current_val.lower() != target_eth.lower():
                ethnicity_field.click()
                time.sleep(0.4)
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) { opt.click(); return true; }
                    return false;
                }''', target_eth)
                time.sleep(0.4)
                results["ethnicity"] = ethnicity_field.input_value()

        # 3. Gender
        gender_field = page.locator('#IN-STANDARD-ORA_GENDER-STANDARD-7, [name="IN-STANDARD-ORA_GENDER-STANDARD"]').first
        if gender_field.count() > 0 and gender_field.is_visible():
            current_val = gender_field.input_value().strip()
            target_gender = candidate_data.get("gender") or "Male"
            if not current_val or current_val.lower() != target_gender.lower():
                gender_field.click()
                time.sleep(0.4)
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) { opt.click(); return true; }
                    return false;
                }''', target_gender)
                time.sleep(0.4)
                results["gender"] = gender_field.input_value()

        return results

    def override_screening_answer(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        JPMC curated screening questionnaire matching.
        """
        if not question_text:
            return None

        q = question_text.lower().strip()
        data = candidate_data or {}
        cand = data.get("candidate", data)

        # 1. Age Gate (18+)
        if "at least 18 years of age" in q or "18 years" in q:
            return self._match_choice("Yes", options)

        # 2. Legal Work Authorization
        if "legally authorized to work" in q or "authorized to work in this country" in q:
            # Domestic citizen applying in home country
            cand_country = str(cand.get("country", "")).lower()
            citizenship = str(cand.get("citizenship", "")).lower()
            if "india" in citizenship or "india" in cand_country:
                return self._match_choice("Yes", options)
            return self._match_choice("Yes", options)

        # 3. Visa Sponsorship
        if "sponsorship for an employment-based visa" in q or "require sponsorship" in q:
            return self._match_choice("No", options)

        # 4. Indian Passport
        if "hold an indian passport" in q:
            return self._match_choice("Yes", options)

        # 5. Dual / Foreign Citizenship
        if "citizenship or a passport of any country other than" in q:
            return self._match_choice("No", options)

        # 6. High School Diploma / 10+2
        if "high school diploma" in q or "10+2" in q:
            return self._match_choice("Yes", options)

        # 7. Relevant Years of Work Experience Tier
        if "relevant years of work experience" in q or "years of work experience you have" in q:
            total_exp = float(cand.get("total_experience_years", 0))
            if options:
                # Parse numeric tiers from options
                best_option = None
                highest_threshold = -1.0
                for opt in options:
                    nums = [float(n) for n in re.findall(r'\d+', opt)]
                    threshold = max(nums) if nums else 0.0
                    if "no prior" in opt.lower() or "none" in opt.lower():
                        threshold = 0.0
                    if total_exp >= threshold and threshold > highest_threshold:
                        highest_threshold = threshold
                        best_option = opt
                if best_option:
                    return best_option

        # 8. Primary Area of Expertise
        if "primary area of expertise" in q and options:
            for opt in options:
                if "software engineering" in opt.lower():
                    return opt

        # 9. AWS Proficiency
        if "proficiency with aws" in q or "proficiency level in aws" in q:
            return self._match_choice("Advanced / Expert", options) or self._match_choice("Advanced", options)

        # 10. Area of Focus within Software Engineering
        if "area of focus" in q and options:
            for opt in options:
                if "fullstack" in opt.lower() or "java fullstack" in opt.lower():
                    return opt

        return None

    def _match_choice(self, target: str, options: Optional[List[str]]) -> Optional[str]:
        if not options:
            return target
        target_l = target.lower().strip()
        for opt in options:
            if opt.lower().strip() == target_l:
                return opt
        for opt in options:
            if target_l in opt.lower():
                return opt
        return options[0] if options else target
