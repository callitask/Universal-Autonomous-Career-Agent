# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [COMPANY_SCRAPER_BASE]
# Timestamp: 2026-09-16 12:40:00 +05:30
# Issue / Context: Abstract base class for company-specific career site scrapers.
# Changes Made: Defined BaseCompanyScraper with standard interfaces for searching,
#               filtering, scraping job cards/details, and scoring candidate matches.
# Rationale: Decouples company scraping and job discovery from ATS form filling fingers.
#
# [ENTRY #002]
# Term: [CDP_LITERAL_PURGE]
# Timestamp: 2026-09-26 12:00:00 +05:30
# Issue / Context: Default literal "http://localhost:9222" bypassed env/config.
# Changes Made: cdp_url defaults to None, resolves via CDP_URL env.
# Rationale: Zero hardcoding; custom ports need no code edits.

# Preventative Notes: Never restore a literal CDP default here.
#
# [ENTRY #003]
# Term: [CONFIG_DRIVEN_SCORING]
# Timestamp: 2026-10-07 16:10:00 +05:30
# Issue / Context: score_job assumed a tech stack fallback and a default city.
# Changes Made: Empty skills matrix scores 0 skill component; location bonus is token-based from candidate location only (skip when unknown).
# Rationale: No assumed identity; unknown data contributes nothing, never fiction.
# Preventative Notes: Never restore stack or city literals here.
# ==============================================================================

import abc
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class BaseCompanyScraper(abc.ABC):
    """
    Abstract Base Class for enterprise career site scrapers.
    Defines universal contract for discovery, search filtering, extraction, and matching.
    """

    def __init__(self, cdp_url: str = None):
        # Resolve via explicit arg → CDP_URL env. No literals (zero-hardcoding).
        self.cdp_url = cdp_url or os.environ.get("CDP_URL")
        self.scraped_jobs: List[Dict[str, Any]] = []

    @property
    @abc.abstractmethod
    def company_name(self) -> str:
        """Returns canonical company name (e.g. 'JPMorgan Chase')."""
        pass

    @property
    @abc.abstractmethod
    def portal_type(self) -> str:
        """Returns ATS portal type (e.g. 'oracle_cloud_hcm', 'workday', 'greenhouse')."""
        pass

    @abc.abstractmethod
    async def search_jobs(self,
                          page: Any,
                          keyword: str,
                          location: str,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Navigates to career portal and executes search query with filters.
        Returns list of extracted job cards.
        """
        pass

    @abc.abstractmethod
    async def scrape_job_details(self, page: Any, job_id_or_url: str) -> Dict[str, Any]:
        """
        Navigates to an individual job description page and extracts full metadata:
        title, description, required skills, responsibilities, business unit, posting date.
        """
        pass

    def score_job_match(self, job_details: Dict[str, Any], candidate_profile: Dict[str, Any]) -> float:
        """
        Calculates match score [0.0 - 1.0] between candidate profile and job requirements.
        Considers title keywords, core skills, and negative keyword exclusions.
        """
        score = 0.0
        candidate = candidate_profile.get("candidate", {})
        target_jobs = candidate_profile.get("target_jobs", {})
        
        job_text = (job_details.get("title", "") + " " + 
                    job_details.get("description", "")).lower()
        
        # 1. Negative keyword penalty
        negative_keywords = target_jobs.get("negative_keywords", [])
        for neg in negative_keywords:
            if neg.lower() in job_text:
                score -= 0.3
                
        # 2. Recommended title bonus
        recommended_titles = target_jobs.get("recommended_titles", [])
        job_title_lower = job_details.get("title", "").lower()
        for rec in recommended_titles:
            if rec.lower() in job_title_lower:
                score += 0.4
                break
                
        # 3. Core skills overlap (config-driven only; no assumed stack)
        core_skills = candidate.get("skills_matrix", []) or []
        if not core_skills:
            # No assumed tech stack: without candidate skills there is nothing
            # truthful to score, so the skill component contributes 0.
            core_skills = []
            
        matched_skills = 0
        for skill in core_skills:
            if skill.lower() in job_text:
                matched_skills += 1
                
        if core_skills:
            skill_ratio = matched_skills / min(len(core_skills), 15)
            score += skill_ratio * 0.4
            
        # 4. Location match bonus (config-driven only; no assumed city)
        preferred_loc = str(candidate.get("location", "") or "").lower().strip()
        job_loc = str(job_details.get("location", "") or "").lower()
        if preferred_loc and job_loc:
            pref_tokens = [t for t in re.split(r"[^a-z0-9]+", preferred_loc) if t]
            if any(t and t in job_loc for t in pref_tokens):
                score += 0.2
            
        return max(0.0, min(1.0, round(score, 2)))

    def export_scraped_jobs(self, output_path: str):
        """Saves scraped jobs to JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "company": self.company_name,
                "portal_type": self.portal_type,
                "total_jobs": len(self.scraped_jobs),
                "jobs": self.scraped_jobs
            }, f, indent=2)
        print(f"[{self.company_name}] Exported {len(self.scraped_jobs)} jobs to {output_path}")
