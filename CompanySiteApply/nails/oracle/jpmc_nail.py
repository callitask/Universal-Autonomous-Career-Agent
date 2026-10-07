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
#
# [ENTRY #002]
# Term: [SCREENING_AND_DEMOGRAPHIC_TRUTH_GATING]
# Timestamp: 2026-10-07 16:10:00 +05:30
# Issue / Context: Demographic selects defaulted (No/Asian/Male); screening returned fixed Yes/No and assumed domain stack (software engineering/AWS/fullstack); _match_choice fell back to options[0].
# Changes Made: Demographics skip when config missing; screening answers gated on candidate truth (age/auth/sponsorship/passport/diploma) with None deferral; expertise/AWS/focus match taxonomy or skill map; _match_choice returns None (H1).
# Rationale: No assumed identity or stack; unknowns defer to the operator, never fiction.

# Preventative Notes: Never restore fixed answers or options[0] here.
#
# [ENTRY #003]
# Term: [TIERED_FIELD_RESOLUTION]
# Timestamp: 2026-10-07 17:10:00 +05:30
# Issue / Context: Demographic fields keyed on versioned flexfield IDs that rev per requisition schema.
# Changes Made: _resolve_field tier (exact ID -> name attribute -> shared semantic label proximity); all three demographic fields use it.
# Rationale: Survives ATTRIBUTE suffix revs; future nails reuse the shared helper.
# Preventative Notes: Never depend on a single versioned ID without name/label fallbacks.
# ==============================================================================

import re
import time
from typing import Any, Dict, List, Optional
from CompanySiteApply.nails.base_nail import BaseNail
from CompanySiteApply.utils.dom_helpers import DOMHelpers


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

    def _resolve_field(self, page: Any, exact_css: str, name_css: str,
                       label_pattern: str) -> Any:
        """
        Tiered field resolution surviving requisition schema revs:
        exact ID -> name attribute -> semantic label proximity. Returns a
        visible locator or None. Shared-helper backed so future nails reuse it.
        """
        for css in (exact_css, name_css):
            try:
                loc = page.locator(css).first
                if loc.count() > 0 and loc.is_visible():
                    return loc
            except Exception:
                continue
        try:
            found = DOMHelpers.find_field_by_label(page, label_pattern)
            if found is not None:
                return found
        except Exception:
            pass
        return None

    def handle_custom_fields(self, page: Any, step_num: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes JPMC-specific custom form fields on demographic/diversity steps (Section 4).
        """
        results = {}

        # 1. India Uniformed Forces / Military Status
        # Primary: versioned flexfield ID; fallback: name attribute; last: label proximity.
        forces_field = self._resolve_field(
            page,
            '#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-8, [name="IN-DFF-indiaMilitaryStatus-ATTRIBUTE16"]',
            '[name="IN-DFF-indiaMilitaryStatus-ATTRIBUTE16"], [name*="indiaMilitaryStatus"]',
            'military status')
        if forces_field is not None:
            current_val = forces_field.input_value().strip()
            if not current_val:
                forces_status = str(candidate_data.get("india_uniformed_forces", "") or "").strip()
                if not forces_status:
                    return results
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
        ethnicity_field = self._resolve_field(
            page,
            '#IN-STANDARD-ORA_ETHNICITY-STANDARD-6, [name="IN-STANDARD-ORA_ETHNICITY-STANDARD"]',
            '[name="IN-STANDARD-ORA_ETHNICITY-STANDARD"], [name*="ORA_ETHNICITY"]',
            'ethnicity')
        if ethnicity_field is not None:
            current_val = ethnicity_field.input_value().strip()
            target_eth = str(candidate_data.get("ethnicity", "") or "").strip()
            if not target_eth:
                return results
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
        gender_field = self._resolve_field(
            page,
            '#IN-STANDARD-ORA_GENDER-STANDARD-7, [name="IN-STANDARD-ORA_GENDER-STANDARD"]',
            '[name="IN-STANDARD-ORA_GENDER-STANDARD"], [name*="ORA_GENDER"]',
            'gender')
        if gender_field is not None:
            current_val = gender_field.input_value().strip()
            target_gender = str(candidate_data.get("gender", "") or "").strip()
            if not target_gender:
                return results
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

        # 1. Age Gate (18+): answerable only when date_of_birth or explicit
        # majority flag is present; otherwise defer to the operator.
        if "at least 18 years of age" in q or "18 years" in q:
            if cand.get("date_of_birth") or cand.get("age_verified") or cand.get("majority_confirmed"):
                return self._match_choice("Yes", options)
            return None

        # 2. Legal Work Authorization (resolve from citizenship/country only)
        if "legally authorized to work" in q or "authorized to work in this country" in q:
            # Domestic citizen applying in home country
            cand_country = str(cand.get("country", "")).lower()
            citizenship = str(cand.get("citizenship", "")).lower()
            if ("india" in citizenship or "india" in cand_country
                    or str(cand.get("legally_authorized", "")).lower() in ("yes", "true", "1")):
                return self._match_choice("Yes", options)
            return None

        # 3. Visa Sponsorship (resolve from explicit flag; default unknown -> operator)
        if "sponsorship for an employment-based visa" in q or "require sponsorship" in q:
            req = str(cand.get("requires_sponsorship", "")).lower()
            if req in ("yes", "true", "1"):
                return self._match_choice("Yes", options)
            if req in ("no", "false", "0"):
                return self._match_choice("No", options)
            return None

        # 4. Indian Passport (resolve from citizenship only)
        if "hold an indian passport" in q:
            citizenship = str(cand.get("citizenship", "")).lower()
            if "india" in citizenship:
                return self._match_choice("Yes", options)
            return None

        # 5. Dual / Foreign Citizenship (resolve from citizenship/country only)
        if "citizenship or a passport of any country other than" in q:
            if cand.get("citizenship") or cand.get("country"):
                return self._match_choice("No", options)
            return None

        # 6. High School Diploma / 10+2 (resolve from education presence only)
        if "high school diploma" in q or "10+2" in q:
            if cand.get("education") or cand.get("degree") or (data.get("ats_answers", {}) if isinstance(data, dict) else {}):
                return self._match_choice("Yes", options)
            return None

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

        # 8. Primary Area of Expertise (match options against candidate taxonomy,
        # never an assumed domain)
        if "primary area of expertise" in q and options:
            _tax = data.get("taxonomy_skills", {}) if isinstance(data, dict) else {}
            _terms = set()
            for _v in (_tax.values() if isinstance(_tax, dict) else []):
                for _s in (_v if isinstance(_v, list) else []):
                    _terms.add(str(_s).lower())
            for opt in options:
                if opt and opt.lower() in _terms:
                    return opt
            return None

        # 9. AWS Proficiency (resolve from skill map only; never assume level)
        if "proficiency with aws" in q or "proficiency level in aws" in q:
            _skills = ((data.get("ats_answers", {}) or {}).get("skill_years_experience", {}) or {}) if isinstance(data, dict) else {}
            _aws_years = None
            for _k, _v in _skills.items():
                if "aws" in str(_k).lower():
                    try:
                        _aws_years = float(_v)
                    except Exception:
                        _aws_years = None
                    break
            if _aws_years is None:
                return None
            if _aws_years >= 4:
                return self._match_choice("Advanced / Expert", options) or self._match_choice("Advanced", options)
            if _aws_years >= 2:
                return self._match_choice("Intermediate", options)
            return self._match_choice("Beginner", options)

        # 10. Area of Focus within candidate domain (match taxonomy, never assume stack)
        if "area of focus" in q and options:
            _tax = data.get("taxonomy_skills", {}) if isinstance(data, dict) else {}
            _terms = set()
            for _v in (_tax.values() if isinstance(_tax, dict) else []):
                for _s in (_v if isinstance(_v, list) else []):
                    _terms.add(str(_s).lower())
            for opt in options:
                if opt and any(t and t in opt.lower() for t in _terms):
                    return opt
            return None

        return None

    def _match_choice(self, target: str, options: Optional[List[str]]) -> Optional[str]:
        # H1: never blind-pick options[0]; return None so the operator/AI resolves.
        if not options:
            return None
        target_l = target.lower().strip()
        for opt in options:
            if opt.lower().strip() == target_l:
                return opt
        for opt in options:
            if target_l in opt.lower():
                return opt
        return None
