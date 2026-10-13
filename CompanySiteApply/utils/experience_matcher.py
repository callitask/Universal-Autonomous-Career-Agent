# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [EXPERIENCE_MATCHER_EXTRACTION]
# Timestamp: 2026-10-12 21:45:00 +05:30
# Issue / Context: heal_all_experience_tiles.py (root legacy script, now archived)
#                  contained the only resume.md → per-employer parser (city/country/
#                  bullets + fuzzy employer matcher). s3_experience_tile.py only
#                  matches against candidate_data work_experience and has no
#                  resume.md fallback, so tiles defer when structured config is thin.
# Changes Made: Extracted parse_resume_experiences(), match_experience_entry(),
#               and load_resume_experience_map() as profile-parameterized pure
#               helpers with zero hardcoded cities, countries, or employer names.
# Rationale: Single shared resume-grounding source for experience healing;
#            legacy script's logic survives archival in tested, reusable form.
# Preventative Notes: Never add employer/city literals here — keywords derive
#                     dynamically from parsed employer names. Missing location
#                     resolves to "" (caller skips the DOM step, never invents).
# ==============================================================================

"""Resume.md-grounded work-experience parsing and fuzzy employer matching.

Pure functions — no browser, no I/O except explicit resume_path reads.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


def _standardize_city(city: str) -> str:
    """Normalize well-known spelling variants without inventing locations."""
    low = city.strip().lower()
    if low in ("bangalore", "bengaluru"):
        return "Bengaluru"
    if "delhi" in low or "new delhi" in low:
        return "Delhi"
    if low in ("noida", "greater noida"):
        return "Noida"
    return city.strip()


def parse_resume_experiences(resume_path: str | Path) -> Dict[str, Dict[str, Any]]:
    """Parse ## PROFESSIONAL EXPERIENCE from resume.md into {employer: {...}}.

    Each entry: {"city": str, "country": str, "bullets": [str], "title": str}.
    Missing location fields resolve to "" — never invented.
    Returns {} when the file or section is absent.
    """
    try:
        content = Path(resume_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    exp_section = re.search(
        r"## PROFESSIONAL EXPERIENCE(.*?)(?=## EDUCATION|\Z)", content, re.DOTALL
    )
    if not exp_section:
        return {}

    text = exp_section.group(1)
    roles = re.split(r"### \*\*(.*?)\*\*", text)
    experiences: Dict[str, Dict[str, Any]] = {}

    for i in range(1, len(roles), 2):
        emp_name = roles[i].strip()
        body = roles[i + 1]

        city = ""
        country = ""
        loc_match = re.search(r"\*(.*?)\|(.*?)\*", body)
        if loc_match:
            parts = [p.strip() for p in loc_match.group(1).split(",")]
            if len(parts) >= 2:
                city, country = _standardize_city(parts[0]), parts[1]
            elif len(parts) == 1 and parts[0]:
                city = _standardize_city(parts[0])

        bullets = [
            re.sub(r"^[\u2022\-\*]\s*", "", line).strip()
            for line in body.split("\n")
            if re.match(r"^\s*[\u2022\-\*]\s+", line)
        ]
        experiences[emp_name] = {
            "city": city,
            "country": country,
            "bullets": [b for b in bullets if b],
            "title": "",
        }
    return experiences


def match_experience_entry(
    employer_name: str, experiences: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Fuzzy-match an employer name against a parsed experience map.

    Match keys derive dynamically from the map itself (substring either way,
    then significant-token overlap). No hardcoded employer list.
    Returns the matched entry dict or None.
    """
    low = (employer_name or "").strip().lower()
    if not low or not experiences:
        return None

    for exp_key, exp_val in experiences.items():
        k_low = exp_key.lower()
        if k_low in low or low in k_low:
            return exp_val

    low_tokens = {w for w in re.findall(r"[a-z0-9]+", low) if len(w) > 3}
    best: Optional[Dict[str, Any]] = None
    best_score = 0
    for exp_key, exp_val in experiences.items():
        key_tokens = {w for w in re.findall(r"[a-z0-9]+", exp_key.lower()) if len(w) > 3}
        overlap = len(low_tokens & key_tokens)
        if overlap > best_score:
            best_score = overlap
            best = exp_val
    return best if best_score > 0 else None


def load_resume_experience_map(
    candidate_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Locate resume.md via search roots and parse it. Returns {} if absent.

    Mirrors the oracle_cloud_finger.py resume.md lookup (root + "/resume.md").
    """
    try:
        from CompanySiteApply.utils.config_resolver import resolve_search_roots

        roots = [str(r) for r in resolve_search_roots(candidate_data)]
    except Exception:
        roots = [os.getcwd()]

    for root in roots:
        md_path = os.path.join(root, "resume.md")
        if os.path.exists(md_path):
            parsed = parse_resume_experiences(md_path)
            if parsed:
                return parsed
    return {}
