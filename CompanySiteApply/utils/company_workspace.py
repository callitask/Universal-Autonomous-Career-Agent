# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [COMPANY_WORKSPACE_INIT]
# Timestamp: 2026-10-13 20:00:00 +05:30
# Issue / Context: Section scripts resolved resumes/cover letters from a flat
#                  company_site_apply/ namespace. Service-background candidates
#                  need per-company product-framed base documents, and future
#                  company agents must self-provision their workspace instead of
#                  rediscovering layout (incident: APPLIED-folder writes skipped
#                  because only cli_scraper.py knew that path).
# Changes Made: company_slug(), ensure_company_workspace() (auto-create +
#               seed from master), resolve_company_roots() (company-first
#               search order).
# Rationale: One workspace contract for every current and future company
#            agent; profile truth stays in the sandbox.
# Preventative Notes: Slugs are alphanumeric only (no spaces/&/punctuation)
#                     so shell globs and OCR-style matchers never break.
#                     Never seed live PII into the default_user blueprint.
#
# [ENTRY #002]
# Term: [BASE_RESUME_MD_READER]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: resumes/BASE.md was seeded but never read — matching/Q&A
#                  only read profile resume.md (write-only decoration).
# Changes Made: resolve_base_resume_md() — company workspace BASE.md first
#               (placeholder-guarded), profile resume.md fallback. Readers in
#               experience_matcher + oracle_cloud_finger use it.
# Rationale: Company-framed bases must actually ground matching.
# Preventative Notes: Never read a BASE.md containing blueprint placeholders.
# ==============================================================================

"""Per-company workspace contract for CompanySiteApply document resolution."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


_CORP_SUFFIXES = {"co", "inc", "ltd", "llc", "corp", "llp", "pvt", "plc", "gmbh", "sa", "ag"}


_PROFILE_CACHE: Dict[str, Any] = {}


def _load_company_profiles() -> Dict[str, Any]:
    """Load the company framing map (cached; tiny file)."""
    global _PROFILE_CACHE
    if not _PROFILE_CACHE:
        try:
            here = Path(__file__).resolve().parent.parent / "company_profiles.json"
            _PROFILE_CACHE = json.loads(here.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _PROFILE_CACHE = {"companies": {}}
    return _PROFILE_CACHE


def company_slug(company: str) -> str:
    """Normalize a company name to a filesystem-safe slug.

    Examples: "JPMorgan Chase & Co." -> "JPMorganChase",
              "Goldman Sachs" -> "GoldmanSachs".
    """
    tokens = re.findall(r"[A-Za-z0-9]+", str(company or ""))
    tokens = [t for t in tokens if t.lower() not in _CORP_SUFFIXES] or tokens
    slug = "".join(t[:1].upper() + t[1:] for t in tokens)
    return slug or "GenericCompany"


def company_workspace_dir(profile_dir: str | Path, company: str) -> Path:
    """Path of the per-company workspace inside a profile's company_site_apply/."""
    return Path(profile_dir) / "company_site_apply" / company_slug(company)


def ensure_company_workspace(
    candidate_data: Optional[Dict[str, Any]],
    company: str,
    seed_from_master: bool = True,
) -> Path:
    """Create company_site_apply/<Slug>/ (plus cover_letters/ + resumes/)
    and seed the base resume from the master resume.md when absent.

    For the default_user blueprint (or when no master exists) only the
    directory skeleton + README are created — never PII.
    Returns the workspace directory.
    """
    profile_dir: Optional[Path] = None
    if isinstance(candidate_data, dict):
        for key in ("profile_dir", "profile"):
            val = candidate_data.get(key)
            if val:
                p = Path(str(val))
                cand_dir = p if p.is_dir() else None
                if cand_dir is None and (p.parent / "candidate_config.json").exists():
                    cand_dir = p.parent
                if cand_dir is not None:
                    profile_dir = cand_dir
                    break
    if profile_dir is None:
        try:
            roots = [str(r) for r in resolve_search_roots(candidate_data)]
        except Exception:
            roots = [os.getcwd()]
        profile_dir = next(
            (Path(r).parent if Path(r).name == "company_site_apply" else Path(r)
             for r in roots if Path(r).exists()),
            Path(os.getcwd()),
        )

    workdir = company_workspace_dir(profile_dir, company)
    (workdir / "cover_letters").mkdir(parents=True, exist_ok=True)
    (workdir / "resumes").mkdir(parents=True, exist_ok=True)

    # Legacy layout migration (2026-10-14): base files lived at the
    # workspace root (resume.md, cover_letter_base.md, company.json).
    # Contract: root holds README.md ONLY; bases live in resumes/BASE.md
    # and cover_letters/BASE.md. Nothing in code reads the legacy files.
    import logging as _logging
    _log = _logging.getLogger(__name__)
    for _legacy in ("company.json", "cover_letter_base.md"):
        try:
            _lp = workdir / _legacy
            if _lp.is_file():
                _lp.unlink()
                _log.info(f"[workspace] Removed legacy {_legacy} from {workdir}")
        except OSError:
            pass
    try:
        _root_resume = workdir / "resume.md"
        _base_resume = workdir / "resumes" / "BASE.md"
        if _root_resume.is_file() and not _base_resume.is_file():
            _base_resume.write_bytes(_root_resume.read_bytes())
            _root_resume.unlink()
            _log.info(f"[workspace] Moved resume.md -> resumes/BASE.md in {workdir}")
        elif _root_resume.is_file() and _base_resume.is_file():
            try:
                _same = (_root_resume.read_bytes() == _base_resume.read_bytes())
            except OSError:
                _same = False
            if _same:
                _root_resume.unlink()
                _log.info(f"[workspace] Removed duplicate root resume.md in {workdir}")
            else:
                _log.warning(f"[workspace] Root resume.md differs from "
                             f"resumes/BASE.md in {workdir} — kept both; "
                             f"resumes/BASE.md is authoritative.")
    except OSError:
        pass

    readme = workdir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {company_slug(company)} workspace\n\n"
            "Base documents the agent refactors per requisition at runtime:\n"
            "- `resumes/BASE.md` — company-framed base resume (product-oriented, same stack)\n"
            "- `cover_letters/BASE.md` — company base letter (tone reference + token template; per-req PDFs are synthesized beside it)\n"
            "- `cover_letters/` — generated per-requisition letters (Job ID verified)\n"
            "- `resumes/` — per-requisition resume variants\n"
            "Workspace root holds this README only.\n",
            encoding="utf-8",
        )

    if seed_from_master:
        target = workdir / "resumes" / "BASE.md"
        if not target.exists():
            master = profile_dir / "resume.md"
            if master.exists():
                try:
                    target.write_text(master.read_text(encoding="utf-8"), encoding="utf-8")
                except OSError:
                    pass
        base_letter = workdir / "cover_letters" / "BASE.md"
        if not base_letter.exists():
            master_letter = profile_dir / "cover_letter.md"
            if master_letter.exists():
                try:
                    base_letter.write_text(master_letter.read_text(encoding="utf-8"), encoding="utf-8")
                except OSError:
                    pass
    return workdir


def _is_real_base_md(path: Path) -> bool:
    """Non-empty BASE.md without unedited blueprint placeholders."""
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return False
        return "[FIRSTNAME LASTNAME]" not in text
    except OSError:
        return False


def resolve_base_resume_md(
    candidate_data: Optional[Dict[str, Any]] = None,
    company: str = "",
) -> str:
    """Company-first markdown resume lookup (Gap 1 closure).

    Order: company_site_apply/<Slug>/resumes/BASE.md (real content only)
    -> profiles/<slug>/resume.md. Returns "" when neither is usable.
    """
    if company and str(company).strip().lower() not in ("company", "unknown", ""):
        try:
            for root in resolve_company_roots(candidate_data, str(company)):
                base = Path(root) / "resumes" / "BASE.md"
                if _is_real_base_md(base):
                    return str(base)
        except Exception:
            pass
    try:
        from CompanySiteApply.utils.config_resolver import resolve_search_roots
        roots = [str(r) for r in resolve_search_roots(candidate_data)]
    except Exception:
        roots = [os.getcwd()]
    for root in roots:
        md_path = Path(root) / "resume.md"
        if _is_real_base_md(md_path):
            return str(md_path)
        csa = Path(root) / "company_site_apply" / "resume.md"
        if _is_real_base_md(csa):
            return str(csa)
    return ""


def resolve_company_roots(
    candidate_data: Optional[Dict[str, Any]], company: str
) -> List[str]:
    """Search roots with the company workspace first, then standard roots."""
    from CompanySiteApply.utils.config_resolver import resolve_search_roots

    try:
        roots = [str(r) for r in resolve_search_roots(candidate_data)]
    except Exception:
        roots = [os.getcwd()]
    workdir = company_workspace_dir(_profile_dir_of(candidate_data, roots), company)
    ordered = [str(workdir)] + [r for r in roots if r != str(workdir)]
    return ordered


def company_kind(company: str) -> str:
    """Framing kind for a company: "service" or "company" (default).

    service → flat generic base (consulting tone fits the relationship).
    anything else (product/tech/finance/unlisted) → per-company workspace.
    """
    slug = company_slug(company)
    entry = _load_company_profiles().get("companies", {}).get(slug, {})
    return "service" if entry.get("type") == "service" else "company"


def company_cover_tone(company: str) -> str:
    """Short framing tone for cover synthesis ("" when unmapped)."""
    slug = company_slug(company)
    entry = _load_company_profiles().get("companies", {}).get(slug, {})
    return str(entry.get("cover_tone") or "").strip()


def _profile_dir_of(candidate_data: Optional[Dict[str, Any]], roots: List[str]) -> Path:
    if isinstance(candidate_data, dict):
        for key in ("profile_dir", "profile"):
            val = candidate_data.get(key)
            if val:
                p = Path(str(val))
                if p.is_dir():
                    return p
                if (p.parent / "candidate_config.json").exists():
                    return p.parent
    return next(
        (Path(r).parent if Path(r).name == "company_site_apply" else Path(r)
         for r in roots if Path(r).exists()),
        Path(os.getcwd()),
    )
