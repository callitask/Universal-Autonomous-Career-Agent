# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:52:00 +05:30
# Issue / Context: ATS parser education/college field misalignment healing.
# Changes Made: Implemented EducationHealer to detect and repair swapped school/degree/major fields.
# Rationale: Workday and Oracle parsers frequently invert School Name with Degree (e.g. placing
#            'Bachelor of Technology' into School Name, or University into Degree).
# Preventative Notes: Compares against candidate ground truth; zero hardcoded candidate PII in code.
# ==============================================================================

import re
from typing import Any, Dict, List, Optional


class EducationHealer:
    """
    Validates and rectifies education entries populated by ATS resume parsers.
    """

    # Generic degree patterns to identify when a degree string landed in an institution field
    DEGREE_PATTERNS = [
        re.compile(r"\b(bachelor|master|doctorate|phd|diploma|associate|b\.?tech|m\.?tech|b\.?e|m\.?e|m\.?s|b\.?s|bba|mba|bca|mca|b\.?sc|m\.?sc|b\.?com|m\.?com)\b", re.IGNORECASE),
        re.compile(r"\b(undergraduate|postgraduate|graduate)\b", re.IGNORECASE),
    ]

    # Generic institution patterns to identify when an institution string landed in a degree field
    INSTITUTION_PATTERNS = [
        re.compile(r"\b(university|college|institute|school|academy|polytechnic|vidyapith|campus)\b", re.IGNORECASE),
        re.compile(r"\b(iit|nit|iiit|bits|mit|stanford|oxford|harvard)\b", re.IGNORECASE),
    ]

    @classmethod
    def diagnose_and_heal_entry(cls,
                                parsed_school: str,
                                parsed_degree: str,
                                parsed_field: str = "",
                                ground_truth_education: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Diagnoses whether parsed_school and parsed_degree are inverted or corrupted,
        and returns corrected field values.
        """
        school = parsed_school.strip()
        degree = parsed_degree.strip()
        field = parsed_field.strip()
        was_swapped = False
        reasons = []

        # Check 1: Inversion detection via keyword heuristics
        school_looks_like_degree = any(p.search(school) for p in cls.DEGREE_PATTERNS)
        school_looks_like_institution = any(p.search(school) for p in cls.INSTITUTION_PATTERNS)

        degree_looks_like_institution = any(p.search(degree) for p in cls.INSTITUTION_PATTERNS)
        degree_looks_like_degree = any(p.search(degree) for p in cls.DEGREE_PATTERNS)

        if (school_looks_like_degree and not school_looks_like_institution) and \
           (degree_looks_like_institution and not degree_looks_like_degree):
            # Obvious swap!
            school, degree = degree, school
            was_swapped = True
            reasons.append("Swapped inverted School and Degree based on structural keywords")

        # Check 2: Match against ground truth education if provided
        if ground_truth_education:
            best_match = cls._find_matching_ground_truth(school, degree, ground_truth_education)
            if best_match:
                gt_school = best_match.get("institution") or best_match.get("school") or ""
                gt_degree = best_match.get("degree") or ""
                gt_field = best_match.get("field_of_study") or best_match.get("major") or ""

                if gt_school and school != gt_school:
                    # Ground truth has exact school
                    if gt_school.lower() in degree.lower():
                        school = gt_school
                        was_swapped = True
                        reasons.append("Aligned institution to candidate ground truth")
                    elif not school:
                        school = gt_school
                        reasons.append("Filled missing institution from ground truth")

                if gt_degree and degree != gt_degree:
                    if not degree:
                        degree = gt_degree
                        reasons.append("Filled missing degree from ground truth")

                if gt_field and not field:
                    field = gt_field
                    reasons.append("Filled missing field of study from ground truth")

        return {
            "school": school,
            "degree": degree,
            "field_of_study": field,
            "was_modified": was_swapped or bool(reasons),
            "reasons": reasons
        }

    @staticmethod
    def _find_matching_ground_truth(school: str, degree: str,
                                    gt_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Finds the closest matching education item from ground truth.
        """
        for item in gt_list:
            gt_school = (item.get("institution") or item.get("school") or "").lower()
            gt_degree = (item.get("degree") or "").lower()
            if gt_school and (gt_school in school.lower() or gt_school in degree.lower()):
                return item
            if gt_degree and (gt_degree in degree.lower() or gt_degree in school.lower()):
                return item
        return gt_list[0] if gt_list else None
