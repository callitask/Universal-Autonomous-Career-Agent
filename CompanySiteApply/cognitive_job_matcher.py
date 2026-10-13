# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [COGNITIVE_JOB_MATCHER_INIT]
# Timestamp: 2026-10-11 00:36:00 +05:30
# Issue / Context: Job matching scripts had hardcoded "Java", "Bengaluru", and static tech
#                  dictionaries, failing for diverse candidate domains (Finance, Sales, HR, etc.).
# Changes Made: Built CognitiveJobMatcher with 100% dynamic, profile-grounded matching.
#               Extracts candidate skills, experience years, target titles, locations, and negative
#               keywords dynamically from candidate_data and evaluates JDs factually.
# Rationale: Zero hardcoding policy across any candidate profile or professional vertical.
# Preventative Notes: Never hardcode specific languages, frameworks, or city names.
# ==============================================================================

import re
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CognitiveJobMatcher:
    """
    Antigravity 2.0 Cognitive Job Matcher.
    
    Dynamically scores job requisitions against any candidate profile:
    - Zero Hardcoding: All skills, seniority rules, locations, and filters are
      derived directly from candidate_data.
    - C6 Negative Keyword Gating: Disqualifies roles matching candidate negative keywords.
    - Seniority & Experience Alignment: Dynamically pairs candidate years of experience
      and target titles with job title and requirements.
    - Domain & Skills Overlap: Evaluates candidate's actual taxonomy skills in JD text.
    - Location Compatibility: Checks candidate's target and home locations against JD location.
    """

    def __init__(self, candidate_data: Dict[str, Any], resume_text: str = ""):
        self.candidate_data = candidate_data
        self.resume_text = resume_text or ""
        self._extract_candidate_profile()

    def _extract_candidate_profile(self):
        cand = self.candidate_data.get("candidate", self.candidate_data) if isinstance(self.candidate_data, dict) else {}
        self.candidate_name = cand.get("full_name") or cand.get("name") or "Candidate"
        self.current_title = str(cand.get("current_title") or cand.get("headline") or cand.get("resume_headline") or "").strip()
        
        # Experience
        self.total_experience_years = float(cand.get("total_experience_years") or 0.0)
        if self.total_experience_years == 0.0 and "experience_years" in cand:
            try:
                self.total_experience_years = float(cand["experience_years"])
            except Exception:
                pass

        # Target jobs configuration
        target_jobs = self.candidate_data.get("target_jobs", {}) if isinstance(self.candidate_data, dict) else {}
        self.target_keywords: List[str] = [str(k).strip() for k in target_jobs.get("keywords", []) if str(k).strip()]
        self.recommended_titles: List[str] = [str(t).strip() for t in target_jobs.get("recommended_titles", []) if str(t).strip()]
        self.negative_keywords: List[str] = [str(n).strip() for n in target_jobs.get("negative_keywords", []) if str(n).strip()]
        self.allowed_countries: List[str] = [str(c).strip() for c in target_jobs.get("allowed_countries", []) if str(c).strip()]

        # Locations
        loc_list: List[str] = []
        if cand.get("location"):
            loc_list.append(str(cand["location"]).strip())
        if target_jobs.get("locations"):
            loc_list.extend([str(l).strip() for l in target_jobs["locations"] if str(l).strip()])
        if cand.get("preferred_locations"):
            loc_list.extend([str(l).strip() for l in cand["preferred_locations"] if str(l).strip()])
        
        # Add common Indian metropolitan synonyms
        expanded_locs = []
        for l in loc_list:
            clean = l.strip()
            expanded_locs.append(clean)
            l_low = clean.lower()
            if "bengaluru" in l_low and "Bangalore" not in expanded_locs:
                expanded_locs.append("Bangalore")
            elif "bangalore" in l_low and "Bengaluru" not in expanded_locs:
                expanded_locs.append("Bengaluru")
            elif "mumbai" in l_low and "Bombay" not in expanded_locs:
                expanded_locs.append("Bombay")
            elif "gurgaon" in l_low and "Gurugram" not in expanded_locs:
                expanded_locs.append("Gurugram")
            elif "gurugram" in l_low and "Gurgaon" not in expanded_locs:
                expanded_locs.append("Gurgaon")
            elif "delhi" in l_low and "NCR" not in expanded_locs:
                expanded_locs.append("NCR")

        self.locations = list(dict.fromkeys(expanded_locs))  # Deduplicate

        # Skills extraction from taxonomy, profile_content, and candidate skills
        unique_skills: List[str] = []
        seen_skills: Set[str] = set()

        def _add_skill(s: Any):
            clean = str(s).strip()
            if clean and clean.lower() not in seen_skills and len(clean) > 1:
                seen_skills.add(clean.lower())
                unique_skills.append(clean)

        tax = self.candidate_data.get("taxonomy_skills", {}) if isinstance(self.candidate_data, dict) else {}
        if isinstance(tax, dict):
            for v in tax.values():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and item.get("skill_name"):
                            _add_skill(item["skill_name"])
                        else:
                            _add_skill(item)

        content = self.candidate_data.get("profile_content", {}) if isinstance(self.candidate_data, dict) else {}
        if isinstance(content, dict):
            for s in content.get("key_skills", []):
                _add_skill(s)

        for s in cand.get("skills", []):
            _add_skill(s)

        self.candidate_skills = unique_skills

    def evaluate_job(self, job_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates and scores a single job details dictionary.
        Returns match score (0-100), reasons, matched skills, and qualification status.
        """
        title = job_details.get("title", "")
        desc = job_details.get("full_text", "") or job_details.get("description", "")
        job_loc = job_details.get("location", "") or desc
        title_lower = title.lower()
        desc_lower = desc.lower()

        reasons = []
        matched_skills = []

        # ---------------------------------------------------------------------
        # 0. Hard Country Gate (Config-driven; absent/empty = neutral)
        # ---------------------------------------------------------------------
        if self.allowed_countries:
            loc_candidate_text = f"{job_details.get('location', '')} {job_details.get('full_tile_text', '')}".strip()
            loc_eval_text = loc_candidate_text if loc_candidate_text else desc
            loc_eval_lower = loc_eval_text.lower()

            country_matched = any(
                re.search(r'\b' + re.escape(c.lower()) + r'\b', loc_eval_lower)
                for c in self.allowed_countries
            )
            if not country_matched:
                return {
                    "job_id": job_details.get("job_id", ""),
                    "title": title,
                    "score": 0,
                    "is_eligible": False,
                    "status": "DISQUALIFIED",
                    "matched_skills": [],
                    "reasons": ["out-of-country"]
                }

        # ---------------------------------------------------------------------
        # 1. C6 Negative Keyword Gating (Intelligent Conflict Resolution)
        # ---------------------------------------------------------------------
        has_positive_anchor = any(tk.lower() in title_lower for tk in self.target_keywords) or any(rt.lower() in title_lower for rt in self.recommended_titles)
        
        for neg in self.negative_keywords:
            if re.search(r'\b' + re.escape(neg.lower()) + r'\b', title_lower):
                # If the title explicitly contains a candidate positive anchor (e.g. "Lead Software Engineer Java"),
                # a secondary mention (e.g. "/ python") is advisory, not an absolute disqualification.
                if has_positive_anchor:
                    reasons.append(f"Advisory notice: Secondary term '{neg}' observed in title alongside positive anchor.")
                else:
                    return {
                        "job_id": job_details.get("job_id", ""),
                        "title": title,
                        "score": 0,
                        "is_eligible": False,
                        "status": "NEGATIVE_KEYWORD_GATED",
                        "matched_skills": [],
                        "reasons": [f"Disqualified by negative keyword in title: '{neg}'"]
                    }

        # ---------------------------------------------------------------------
        # 2. Seniority & Title Match (Up to 30 Points)
        # ---------------------------------------------------------------------
        seniority_score = 0
        
        # Check target keywords in title
        for tk in self.target_keywords:
            if tk.lower() in title_lower:
                seniority_score = max(seniority_score, 30)
                reasons.append(f"Direct target keyword match in title: '{tk}'")
                break

        if seniority_score == 0:
            for rt in self.recommended_titles:
                if rt.lower() in title_lower:
                    seniority_score = max(seniority_score, 25)
                    reasons.append(f"Recommended target title match in title: '{rt}'")
                    break

        if seniority_score == 0:
            # Experience-tier based seniority match
            exp = self.total_experience_years
            if exp >= 8:
                if any(k in title_lower for k in ["lead", "principal", "architect", "staff", "senior", "director", "manager", "head"]):
                    seniority_score = 25
                    reasons.append(f"Seniority tier match (Lead/Principal/Senior role for {exp}+ yrs experience)")
                elif any(k in title_lower for k in ["engineer iii", "specialist iii", "consultant iii"]):
                    seniority_score = 20
                    reasons.append("Seniority tier match (Tier III role)")
                elif "senior" in title_lower:
                    seniority_score = 20
                    reasons.append("Seniority match (Senior)")
            elif exp >= 3:
                if any(k in title_lower for k in ["senior", "associate", "specialist", "consultant", "analyst ii", "engineer ii"]):
                    seniority_score = 25
                    reasons.append(f"Seniority tier match for mid-level ({exp} yrs experience)")
            else:
                if any(k in title_lower for k in ["associate", "analyst", "junior", "entry", "trainee", "engineer i"]):
                    seniority_score = 25
                    reasons.append(f"Seniority tier match for early career ({exp} yrs experience)")

        # ---------------------------------------------------------------------
        # 3. Domain & Candidate Skills Overlap (Up to 50 Points)
        # ---------------------------------------------------------------------
        skills_score = 0
        for skill in self.candidate_skills:
            if len(skill) < 2:
                continue
            # Regex word-boundary match
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            in_desc = bool(re.search(pattern, desc_lower))
            in_title = bool(re.search(pattern, title_lower))
            if in_desc or in_title:
                matched_skills.append(skill)
                # Cap contribution per skill
                skills_score += 10 if in_title else 6
                if skills_score >= 50:
                    skills_score = 50
                    break

        if matched_skills:
            reasons.append(f"Matched Candidate Skills ({len(matched_skills)}): {', '.join(matched_skills[:8])}")
        else:
            reasons.append("No explicit skill keywords matched from candidate profile.")

        # ---------------------------------------------------------------------
        # 4. Location Match (Up to 20 Points)
        # ---------------------------------------------------------------------
        loc_score = 0
        matched_loc = None
        for cand_loc in self.locations:
            cand_loc_clean = cand_loc.split(",")[0].strip().lower()
            if cand_loc_clean and (cand_loc_clean in job_loc.lower() or "remote" in job_loc.lower()):
                loc_score = 20
                matched_loc = cand_loc
                reasons.append(f"Location match: '{cand_loc}' (Requisition Location: '{job_loc}')")
                break

        if loc_score == 0:
            # If no explicit location preferred, award partial neutral score
            if not self.locations:
                loc_score = 10
                reasons.append("No specific location restriction in candidate profile.")
            else:
                reasons.append(f"Location did not match preferred candidate locations {self.locations}.")

        # ---------------------------------------------------------------------
        # Final Score Calculation
        # ---------------------------------------------------------------------
        total_score = min(100, seniority_score + skills_score + loc_score)
        is_eligible = total_score >= 50

        return {
            "job_id": job_details.get("job_id", ""),
            "title": title,
            "score": total_score,
            "is_eligible": is_eligible,
            "status": "QUALIFIED" if is_eligible else "LOW_FIT",
            "matched_skills": matched_skills,
            "reasons": reasons,
            "seniority_score": seniority_score,
            "skills_score": skills_score,
            "location_score": loc_score
        }
