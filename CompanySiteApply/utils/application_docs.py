# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [APPLICATION_DOCS_STRUCTURED_LAYOUT]
# Timestamp: 2026-10-14
# Issue / Context: Stage 4 generated per-req files (Name_Cover_Letter_<jobid>.pdf)
#   into flat company_site_apply/ while Section 4 upload globbed
#   `*{jobid}*cover*letter*.pdf` (job_id prefix) which never matches the
#   suffix naming. Fallback candidates[0] picked the stale generic letter
#   (incident 210791831 uploaded 210765001 content). Archive also fell back
#   to literal folder "company" when details.company was empty.
# Changes Made: Single contract for input/output locations:
#   input  = profiles/<slug>/company_site_apply/<Slug>/resumes|cover_letters
#   output = profiles/<slug>/APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/
#            with FIXED names <Stem>_Resume.pdf / <Stem>_Cover_Letter.pdf
#            (Stem = Title-Cased profile, e.g. udaysagar_kandpal -> Udaysagar_Kandpal)
#   plus resume/ + cover_letters/ subfolders holding the same fixed files so
#   uploaders can refer to either layout. Uploaders try this exact path FIRST.
# Rationale: Multiple jobs per company and same-title different-IDs coexist;
#   no glob, no candidates[0], no renamed files.
# Preventative Notes: Never reintroduce job_id-prefixed globs or per-req
#   filename suffixes for upload. Fixed names only inside the role folder.
#
# [ENTRY #002]
# Term: [BASE_MD_RESOLVER_REEXPORT]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Base-markdown lookups lived only in company_workspace;
#                  application_docs had no 3-tier entry point for Phase 3B.
# Changes Made: Re-export resolve_base_resume_md / resolve_base_cover_letter_md
#               from company_workspace (single contract, no logic duplicated).
# Rationale: Stage 4 (Phase 3B) resolves base .md through application_docs;
#            one import path prevents contract drift.
# Preventative Notes: Never duplicate tier order here — import, don't copy.
# ==============================================================================

"""Structured per-application document locations (profile-agnostic)."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Canonical 3-tier base-markdown resolvers (single contract lives in
# company_workspace; re-exported here for Stage 4 / Phase 3B consumers).
from CompanySiteApply.utils.company_workspace import (
    resolve_base_cover_letter_md,
    resolve_base_resume_md,
)

__all__ = [
    "profile_stem",
    "profile_slug_of",
    "resolve_company_name",
    "resolve_job_location",
    "application_dir",
    "application_doc_paths",
    "ensure_role_layout",
    "mirror_fixed_files",
    "resolve_master_resume",
    "copy_into_role",
    "resolve_base_resume_md",
    "resolve_base_cover_letter_md",
]


def profile_stem(candidate_data: Optional[Dict[str, Any]] = None,
                 profile_slug: str = "") -> str:
    """Fixed filename stem: Title-Cased profile slug.

    udaysagar_kandpal -> Udaysagar_Kandpal (first letter capital, rest kept).
    Gap 2: the slug is canonical (stable folder identity); candidate
    full_name is fallback only. A rename-proof stem must follow the folder,
    never display metadata — otherwise two identities collide in one role
    folder (incident: Name_ vs Someone_ stubs in profiles/someone/).
    """
    slug = ""
    if isinstance(candidate_data, dict):
        for key in ("profile", "_ipc_profile"):
            val = candidate_data.get(key)
            if val and isinstance(val, str) and val.strip():
                slug = val.strip()
                break
        if not slug:
            cand = candidate_data.get("candidate", {})
            if isinstance(cand, dict):
                for key in ("profile_name", "profile"):
                    val = cand.get(key)
                    if val and isinstance(val, str) and val.strip():
                        slug = val.strip()
                        break
    if not slug:
        slug = str(profile_slug or "").strip()
    name = slug.replace("_", " ")
    if not name.strip():
        cand = candidate_data.get("candidate", candidate_data) \
            if isinstance(candidate_data, dict) else {}
        name = ""
        if isinstance(cand, dict):
            name = str(cand.get("full_name") or cand.get("name") or "").strip()
        if not name and isinstance(candidate_data, dict):
            name = str(candidate_data.get("full_name") or "").strip()
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", name or "") if t]
    if not tokens:
        tokens = [str(profile_slug or "candidate").strip() or "candidate"]
        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", tokens[0]) if t] or ["candidate"]
    titled = [(t[:1].upper() + t[1:]) for t in tokens]
    return "_".join(titled)


def profile_slug_of(candidate_data: Optional[Dict[str, Any]],
                    fallback: str = "") -> str:
    """Resolve profile slug without hardcoding live names."""
    if isinstance(candidate_data, dict):
        for key in ("profile", "_ipc_profile"):
            val = candidate_data.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        cand = candidate_data.get("candidate", {})
        if isinstance(cand, dict):
            for key in ("profile_name", "profile"):
                val = cand.get(key)
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
            full = cand.get("full_name") or ""
            if full:
                return re.sub(r"[^a-zA-Z0-9_]", "_", str(full).strip().lower()).strip("_")
    return fallback.strip() or "default_user"


def _canonical_company(name: str) -> str:
    """Single formal form per company (letter + folder stable).

    "JPMorgan Chase" (scraper config) and "JPMorgan Chase & Co." (portal
    formal) must not produce two identities — canonicalize to the formal.
    """
    s = str(name or "").strip()
    if "jpmorgan" in s.lower() and "chase" in s.lower():
        return "JPMorgan Chase & Co."
    return s


def resolve_company_name(target_job: Optional[Dict[str, Any]] = None,
                         candidate_data: Optional[Dict[str, Any]] = None,
                         page_url: str = "",
                         default_company: str = "") -> str:
    """Resolve company without ever returning the literal 'company'.

    Priority: explicit details.company (meaningful) -> page URL hint
    (jpmc/chase) -> candidate hints -> explicit default_company (portal
    context, e.g. scraper.company_name) -> "" (unknown: callers must
    defer/raise, never ship a placeholder).
    Incident 210791831 follow-up: the old blind "JPMorgan Chase & Co."
    default would mislabel every non-JPMC portal — no silent default.
    """
    url = str(page_url or "")
    if not url and isinstance(target_job, dict):
        url = str(target_job.get("url") or target_job.get("details", {}).get("url") or "")
    if isinstance(target_job, dict):
        det = target_job.get("details", {}) if isinstance(target_job.get("details"), dict) else {}
        for key in ("company", "company_name", "organization"):
            val = target_job.get(key) or det.get(key)
            if val and isinstance(val, str):
                s = val.strip()
                if s and s.lower() not in ("company", "hiring organization", "hiring organisation", "unknown"):
                    return _canonical_company(s)
    if url and ("jpmc" in url.lower() or "chase" in url.lower()):
        return "JPMorgan Chase & Co."
    if isinstance(candidate_data, dict):
        for key in ("company_name", "target_company"):
            val = candidate_data.get(key)
            if val and str(val).strip():
                return _canonical_company(str(val).strip())
        cand = candidate_data.get("candidate", {})
        if isinstance(cand, dict):
            for key in ("company_name", "target_company"):
                val = cand.get(key)
                if val and str(val).strip():
                    return _canonical_company(str(val).strip())
    if default_company and str(default_company).strip():
        return _canonical_company(str(default_company).strip())
    return ""


def _strip_multi_location_suffix(loc: str) -> str:
    """Drop Oracle HCM "and N more" location suffixes (F-04 cosmetic fix)."""
    return re.sub(r"\.?\s+and\s+\d+\s+more\b.*$", "", loc,
                  flags=re.IGNORECASE).strip()[:120]


def resolve_job_location(page: Any = None,
                         candidate_data: Optional[Dict[str, Any]] = None) -> str:
    """Requisition location for the recipient block (never candidate address).

    Priority: live Section 4 DOM (Location label/panel) -> candidate_data
    target-jobs/details location keys -> "" (generator falls back to
    candidate address only as a last resort). Multi-location suffixes
    ("and 2 more") are stripped.
    """
    if page is not None:
        try:
            loc = page.evaluate("""() => {
                const q = (sel) => { const el = document.querySelector(sel); return el ? (el.innerText || '').trim() : ''; };
                let v = q('.job-location') || q('[class*="job-location"]') || q('.job-details__subtitle') || q('[class*="requisition"] [class*="location"]');
                if (v) return v;
                const body = (document.body && document.body.innerText) || '';
                const m = body.match(/Location\\s*[:\\n]\\s*([^\\n]+)/i);
                return m ? m[1].trim().slice(0, 120) : '';
            }""")
            if isinstance(loc, str) and loc.strip():
                return _strip_multi_location_suffix(loc.strip())
        except Exception:
            pass
    if isinstance(candidate_data, dict):
        tj = candidate_data.get("target_jobs")
        if isinstance(tj, dict):
            for key in ("location", "job_location", "title_location"):
                val = tj.get(key)
                if val and str(val).strip():
                    return _strip_multi_location_suffix(str(val).strip())
        for key in ("job_location", "location"):
            val = candidate_data.get(key)
            if val and str(val).strip():
                return _strip_multi_location_suffix(str(val).strip())
        det = candidate_data.get("details")
        if isinstance(det, dict):
            for key in ("location", "job_location"):
                val = det.get(key)
                if val and str(val).strip():
                    return _strip_multi_location_suffix(str(val).strip())
    return ""


def application_dir(profile: str, company: str, job_title: str,
                    job_id: str, repo_root: Optional[Path] = None) -> Path:
    """profiles/<slug>/APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/"""
    from core.utils.sanitize import safe_filename
    from CompanySiteApply.utils.runtime_paths import resolve_profile_dir

    company_clean = resolve_company_name(
        {"details": {"company": company}}, None, "")
    if not company_clean or company_clean.lower() in ("company", "unknown"):
        company_clean = "UnknownCompany"
    company_part = safe_filename(company_clean, max_len=60)
    role_part = safe_filename(job_title or "role", max_len=80)
    jid = re.sub(r"[^A-Za-z0-9_]", "_", str(job_id or "").strip()).strip("_") or "noid"
    return (resolve_profile_dir(profile, repo_root)
            / "APPLIED ON COMPANY WEBSITE" / company_part / f"{role_part}_{jid}")


def application_doc_paths(profile: str, company: str, job_title: str,
                          job_id: str,
                          candidate_data: Optional[Dict[str, Any]] = None,
                          repo_root: Optional[Path] = None) -> Dict[str, Path]:
    """Canonical fixed-name paths for one requisition (profile-agnostic)."""
    role_dir = application_dir(profile, company, job_title, job_id, repo_root)
    stem = profile_stem(candidate_data, profile)
    resume_name = f"{stem}_Resume.pdf"
    cover_name = f"{stem}_Cover_Letter.pdf"
    resume_sub = role_dir / "resume" / resume_name
    cover_sub = role_dir / "cover_letters" / cover_name
    return {
        "role_dir": role_dir,
        "resume_pdf": role_dir / resume_name,
        "cover_pdf": role_dir / cover_name,
        "resume_sub_pdf": resume_sub,
        "cover_sub_pdf": cover_sub,
        "cover_txt": role_dir / "Cover_Letter.txt",
        "cover_html": role_dir / "Cover_Letter.html",
    }


def ensure_role_layout(role_dir: Path) -> Dict[str, Path]:
    """Create role folder plus resume/ + cover_letters/ subfolders."""
    role_dir.mkdir(parents=True, exist_ok=True)
    resume_d = role_dir / "resume"
    cover_d = role_dir / "cover_letters"
    resume_d.mkdir(parents=True, exist_ok=True)
    cover_d.mkdir(parents=True, exist_ok=True)
    return {"role_dir": role_dir, "resume_dir": resume_d, "cover_dir": cover_d}


def mirror_fixed_files(role_dir: Path, resume_src: Optional[Path],
                       cover_src: Optional[Path],
                       stem: str) -> Dict[str, str]:
    """Place FIXED-name files flat + inside resume//cover_letters/ subfolders.

    Returns {resume_pdf, cover_pdf} as strings (flat canonical paths).
    """
    layout = ensure_role_layout(role_dir)
    out: Dict[str, str] = {}
    if resume_src and Path(resume_src).is_file():
        flat = role_dir / f"{stem}_Resume.pdf"
        sub = layout["resume_dir"] / f"{stem}_Resume.pdf"
        try:
            flat.write_bytes(Path(resume_src).read_bytes())
            sub.write_bytes(Path(resume_src).read_bytes())
            out["resume_pdf"] = str(flat)
        except OSError:
            pass
    if cover_src and Path(cover_src).is_file():
        flat = role_dir / f"{stem}_Cover_Letter.pdf"
        sub = layout["cover_dir"] / f"{stem}_Cover_Letter.pdf"
        try:
            flat.write_bytes(Path(cover_src).read_bytes())
            sub.write_bytes(Path(cover_src).read_bytes())
            out["cover_pdf"] = str(flat)
        except OSError:
            pass
    return out


def resolve_master_resume(candidate_data: Optional[Dict[str, Any]],
                          company: str = "") -> Optional[str]:
    """Newest master resume PDF: company resumes/ first, then profile fallbacks."""
    from CompanySiteApply.utils.company_workspace import ensure_company_workspace
    from CompanySiteApply.utils.config_resolver import resolve_search_roots
    from pathlib import Path as _P

    roots: list[_P] = []
    if company and company.lower() not in ("company", "", "unknown"):
        try:
            from CompanySiteApply.utils.company_workspace import (
                company_kind, resolve_company_roots)
            if company_kind(company) == "service":
                roots = [_P(r) for r in resolve_search_roots(candidate_data)]
            else:
                try:
                    ensure_company_workspace(candidate_data, company)
                except Exception:
                    pass
                roots = [_P(r) for r in resolve_company_roots(candidate_data, company)]
        except Exception:
            roots = [_P(r) for r in resolve_search_roots(candidate_data)]
    else:
        try:
            roots = [_P(r) for r in resolve_search_roots(candidate_data)]
        except Exception:
            roots = [_P(os.getcwd())]

    cand: Dict[str, Any] = {}
    if isinstance(candidate_data, dict):
        c = candidate_data.get("candidate", candidate_data)
        cand = c if isinstance(c, dict) else {}
    cand_name = str(cand.get("name") or cand.get("full_name") or "").strip()

    search_dirs: list[_P] = []
    for r in roots:
        search_dirs.append(r)
        for sub in ("resumes", "cover_letters", "company_site_apply"):
            try:
                if (r / sub).is_dir():
                    search_dirs.append(r / sub)
            except Exception:
                continue
    patterns = ["*resume*.pdf", "*Resume*.pdf"]
    if cand_name:
        # Name-qualified but still resume-constrained — a bare *FirstName*.pdf
        # once picked the cover letter (incident 210791831 backfill).
        for token in [t for t in re.split(r"[^A-Za-z0-9]+", cand_name) if t][:2]:
            patterns.insert(0, f"*{token}*resume*.pdf")
        patterns.insert(0, f"*{re.sub(r'[^A-Za-z0-9*? ]', '', cand_name).strip()}*resume*.pdf")
    best: Optional[_P] = None
    best_mtime = -1.0
    for d in search_dirs:
        # Skip APPLIED trees — those are outputs, never base inputs.
        if "APPLIED ON COMPANY WEBSITE" in str(d):
            continue
        for pat in patterns:
            try:
                for p in d.glob(pat):
                    try:
                        if p.is_file() and p.stat().st_size > 0:
                            mt = p.stat().st_mtime
                            if mt > best_mtime:
                                best_mtime = mt
                                best = p
                    except OSError:
                        continue
            except Exception:
                continue
    return str(best) if best else None


def copy_into_role(role_dir: Path, stem: str,
                   resume_master: Optional[str] = None,
                   cover_generated: Optional[str] = None) -> Dict[str, str]:
    """Copy master resume + freshly generated cover into the role folder."""
    return mirror_fixed_files(role_dir,
                              Path(resume_master) if resume_master else None,
                              Path(cover_generated) if cover_generated else None,
                              stem)
