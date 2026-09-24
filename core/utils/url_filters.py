# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-23 14:00:00 +05:30
# Issue / Context: 04_job_discovery.py had ~60 lines of identical CTC/WFH
#   if/elif branches producing the same output (config illusion) plus inline
#   companyJobs logic. Needed one config-driven library.
# Changes Made: Created url_filters.py (build_ctc_param, build_wfh_param,
#   build_company_jobs_param). All values come from candidate_config; no literals.
# Rationale: Short code, single source of truth, discovery just calls 3 helpers.
# Preventative Notes: Never hardcode bracket ids or wfh ids here. Read them from
#   target_jobs (ctc_bracket_id / ctc_filters / wfh_type_id). Empty string = skip.
# ================================================================================
"""URL filter builders for Naukri discovery. Pure functions, no PII, no I/O."""
from __future__ import annotations
import re
from typing import Dict


def build_ctc_param(target: Dict, cand: Dict) -> str:
    """Return '&ctcFilter=...' or '' using only config values."""
    if not isinstance(target, dict):
        return ""
    configured = target.get("ctc_filters")
    if isinstance(configured, list) and configured:
        parts = "".join(
            f"&ctcFilter={str(c).strip()}"
            for c in configured
            if c and str(c).strip()
        )
        if parts:
            return parts
    bracket_id = str(target.get("ctc_bracket_id", "") or "").strip()
    if not bracket_id:
        return ""
    # Only emit when a floor is actually configured (bracket or numeric).
    has_floor = bool(str(target.get("salary_filter_bracket", "") or "").strip())
    has_floor = has_floor or bool(str((cand or {}).get("target_salary_min_lpa", "") or "").strip())
    has_floor = has_floor or any(
        re.search(r"\d", str(v or "")) for v in [target.get("salary_filter_bracket")]
    )
    return f"&ctcFilter={bracket_id}" if has_floor else ""


def build_wfh_param(target: Dict) -> str:
    """Return '&wfhType=...' or '' using only config wfh_type_id."""
    if not isinstance(target, dict):
        return ""
    wfh_id = str(target.get("wfh_type_id", "") or "").strip()
    if not wfh_id:
        return ""
    pref = str(target.get("work_mode") or target.get("wfh_type") or "").lower().strip()
    if any(k in pref for k in ("remote", "wfh", "hybrid", "office", "onsite", "on-site")):
        return f"&wfhType={wfh_id}"
    # Unknown/empty preference: still honor explicit id? No — require explicit pref.
    return ""


def build_company_jobs_param(target: Dict) -> str:
    """Return '&companyJobs=true' or '' from config flags only."""
    if not isinstance(target, dict):
        return ""
    direct = target.get("direct_employers_only", False) or target.get("company_jobs_only", False)
    return "&companyJobs=true" if direct else ""
