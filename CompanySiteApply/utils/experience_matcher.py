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
#
# [ENTRY #002]
# Term: [ROLE_RESUME_BULLET_PRIORITY]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Healers used structured-config bullets even when the
#                  operator hand-tuned BASE.md or Stage 4 tailored a role
#                  resume.md; role resume had no discovery path (title is
#                  unavailable at heal time).
# Changes Made: load_role_bullets_for_employer() — explicit path keys, then
#               job_id-anchored APPLIED-tree discovery, then BASE hierarchy.
#               Structured city/country/dates stay with the caller.
# Rationale: Markdown edits must reach tiles without config copy-paste;
#            job_id is unique per requisition so title is unnecessary.
# Preventative Notes: Never invent bullets; return [] when nothing parses.
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
    company: str = "",
) -> Dict[str, Dict[str, Any]]:
    """Locate resume markdown via search roots and parse it. Returns {} if absent.

    Gap 1: company workspace resumes/BASE.md is tried first (via
    resolve_base_resume_md); legacy root resume.md loop stays as fallback.
    """
    try:
        from CompanySiteApply.utils.company_workspace import resolve_base_resume_md
        base_md = resolve_base_resume_md(candidate_data, company or "")
        if base_md:
            parsed = parse_resume_experiences(base_md)
            if parsed:
                return parsed
    except Exception:
        pass
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


def _candidate_profile_dir(candidate_data: Optional[Dict[str, Any]]) -> Optional[Path]:
    """Profile dir from explicit keys only — never guessed, never created."""
    if isinstance(candidate_data, dict):
        for key in ("profile_dir", "profile"):
            val = candidate_data.get(key)
            if val:
                p = Path(str(val))
                if p.is_dir():
                    return p
                if (p.parent / "candidate_config.json").exists():
                    return p.parent
    return None


def _discover_role_resume_md(
    candidate_data: Optional[Dict[str, Any]], job_id: str = ""
) -> Optional[Path]:
    """Locate <APPLIED>/<Company>/<Role>_<jobid>/resume.md without a title.

    job_id values are unique per requisition, so the first
    */*_<jobid>/resume.md match under the profile APPLIED root wins.
    Returns None when anything is missing — never raises, never creates.
    """
    jid = re.sub(r"[^A-Za-z0-9_]", "_", str(job_id or "").strip()).strip("_")
    if not jid:
        return None
    prof = _candidate_profile_dir(candidate_data)
    if prof is None:
        return None
    root = prof / "APPLIED ON COMPANY WEBSITE"
    if not root.is_dir():
        return None
    try:
        hits = sorted(root.glob(f"*/*_{jid}/resume.md"))
    except Exception:
        return None
    for hit in hits:
        try:
            if hit.is_file() and hit.stat().st_size > 0:
                return hit
        except OSError:
            continue
    return None


def load_role_bullets_for_employer(
    candidate_data: Optional[Dict[str, Any]] = None,
    company: str = "",
    employer_text: str = "",
) -> list:
    """Role-tailored resume.md -> BASE hierarchy bullet lookup.

    Priority: explicit tailored-resume path keys on candidate_data, then
    job_id-anchored APPLIED-tree discovery, then the canonical 4-tier
    resolve_base_resume_md(profile_dir, company). Returns the matched
    employer's bullets or [] — structured city/country/dates stay with the
    caller and are never sourced here.
    """
    if not str(employer_text or "").strip():
        return []
    if isinstance(candidate_data, dict):
        for key in ("role_resume_md", "tailored_resume_md", "active_role_resume"):
            val = candidate_data.get(key)
            if val:
                matched = match_experience_entry(
                    employer_text, parse_resume_experiences(val))
                if matched and matched.get("bullets"):
                    return list(matched["bullets"])
        try:
            jid = str(candidate_data.get("job_id")
                      or candidate_data.get("_ipc_job_id") or "")
            role_md = _discover_role_resume_md(candidate_data, jid)
            if role_md is not None:
                matched = match_experience_entry(
                    employer_text, parse_resume_experiences(str(role_md)))
                if matched and matched.get("bullets"):
                    return list(matched["bullets"])
        except Exception:
            pass
    try:
        from CompanySiteApply.utils.company_workspace import resolve_base_resume_md
        prof = _candidate_profile_dir(candidate_data)
        if prof is not None:
            base = resolve_base_resume_md(prof, company or "")
            if base is not None:
                matched = match_experience_entry(
                    employer_text, parse_resume_experiences(str(base)))
                if matched and matched.get("bullets"):
                    return list(matched["bullets"])
    except Exception:
        pass
    return []
