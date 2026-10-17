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
#
# [ENTRY #003]
# Term: [THREE_TIER_SEEDING + CANONICAL_RESOLVERS]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: ensure_company_workspace() seeded only from profile_dir
#                  resume.md/cover_letter.md with no placeholder guard and no
#                  legacy space-separated folder tier; resolvers had no
#                  cover-letter counterpart and no profile_dir convention.
# Changes Made: Non-overwrite seeding (_needs_seed/_seed_base_md) with 3-tier
#               sources (legacy <company_name>/ -> company_site_apply master ->
#               profile-root fallback, all placeholder-guarded, skeleton for
#               letters); new resolve_base_resume_md(profile_dir, company_name)
#               and resolve_base_cover_letter_md() (-> Optional[Path]); legacy
#               dict-convention preserved verbatim via type dispatch.
# Rationale: Existing BASE.md is sacred ground truth; missing BASE.md must
#            prefer the closest company-framed source over the generic master.
# Preventative Notes: Never write into a real BASE.md from seeding logic;
#                     never add a fourth tier without auditor approval.
#
# [ENTRY #004]
# Term: [F_CSA_02_BARE_SLUG_PROFILE_DIR]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: [F-CSA-02] ensure_company_workspace() and
#                  _profile_dir_of() only accepted cwd-relative profile dirs;
#                  candidate_data["profile"]="<slug>" (production shape) fell
#                  through to cwd, so workspaces were seeded outside the
#                  Operations sandbox and then never found again.
# Changes Made: Single-segment slugs resolve through resolve_profile_dir().
# Rationale: Workspace provisioning must target the same sandbox every other
#            resolver uses.
# Preventative Notes: Never treat a profile slug as a relative filesystem path.
#
# [ENTRY #005]
# Term: [F_DOC_01_BLUEPRINT_PLACEHOLDER_GUARD]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: [F-DOC-01] default_user's cover_letters/BASE.md used the
#                  token "[FULL NAME]", which _is_real_base_md() did not reject,
#                  so the unedited blueprint resolved as a real cover letter.
# Changes Made: Guard rejects BOTH "[FIRSTNAME LASTNAME]" and "[FULL NAME]";
#               blueprint template tokens normalized to the documented set
#               ([Job Title], [Company Name], [City, State, Country], "- **" bullets).
# Rationale: A template must never synthesize a letter.
# Preventative Notes: When adding a token variant, add it to the guard too.
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
                if cand_dir is None and not p.is_absolute() and len(p.parts) == 1:
                    # [F-CSA-02] Bare slug ("<profile>") -> Operations root;
                    # a workspace created under cwd was never found again.
                    try:
                        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
                        ops_p = resolve_profile_dir(str(val))
                        if ops_p.is_dir():
                            cand_dir = ops_p
                    except Exception:
                        cand_dir = None
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
        # 3-tier seeding (never overwrite real content — see _needs_seed):
        # P1 legacy space-separated folder -> P2 company_site_apply master ->
        # P3 profile-root fallback. Placeholder sources never seed.
        _seed_base_md(
            workdir / "resumes" / "BASE.md",
            _resume_seed_sources(profile_dir, company),
            _log,
        )
        _seed_base_md(
            workdir / "cover_letters" / "BASE.md",
            _cover_seed_sources(profile_dir, company),
            _log,
            extra_tokens=("{{FULL_NAME}}",),
            skeleton=_COVER_SKELETON,
        )
    return workdir


_COVER_SKELETON = (
    "# Company base letter\n\n"
    "Tone reference for per-requisition synthesis. "
    "Per-req PDFs are generated beside this file at runtime.\n"
)


def _legacy_company_dirnames(company: str) -> List[str]:
    """Space-separated legacy folder candidates for a company name.

    The full stripped name first (literal contract), then the corporate-
    suffix-stripped form (e.g. "JPMorgan Chase & Co." -> "JPMorgan Chase"),
    which is how legacy snapshot folders were actually named on disk.
    """
    full = str(company or "").strip()
    if not full:
        return []
    tokens = re.findall(r"[A-Za-z0-9]+", full)
    kept = [t for t in tokens if t.lower() not in _CORP_SUFFIXES] or tokens
    short = " ".join(kept)
    names = [full]
    if short and short not in names:
        names.append(short)
    return names


def _resume_seed_sources(profile_dir: Path, company: str) -> List[Path]:
    """Ordered seed candidates for <Slug>/resumes/BASE.md (P1 -> P3)."""
    csa = Path(profile_dir) / "company_site_apply"
    sources: List[Path] = []
    for legacy in _legacy_company_dirnames(company):
        sources.append(csa / legacy / "resumes" / "BASE.md")
    sources.append(csa / "resume.md")
    sources.append(Path(profile_dir) / "resume.md")
    return sources


def _cover_seed_sources(profile_dir: Path, company: str) -> List[Path]:
    """Ordered seed candidates for <Slug>/cover_letters/BASE.md.

    P1 legacy -> P2 company_site_apply master -> P3 profile template, plus a
    backward-compat fallback to profile-root cover_letter.md (pre-3A seeding
    behavior relied on it) before the default skeleton.
    """
    csa = Path(profile_dir) / "company_site_apply"
    sources: List[Path] = []
    for legacy in _legacy_company_dirnames(company):
        sources.append(csa / legacy / "cover_letters" / "BASE.md")
    sources.append(csa / "cover_letter.md")
    sources.append(Path(profile_dir) / "cover_letter_template.md")
    sources.append(Path(profile_dir) / "cover_letter.md")
    return sources


def _needs_seed(target: Path, extra_tokens: tuple = ()) -> bool:
    """True only when the target is missing, empty, or still a blueprint
    placeholder — real user content is sacred and never reseeded."""
    if not target.exists():
        return True
    return not _is_real_base_md(target, extra_tokens)


def _seed_base_md(
    target: Path,
    sources: List[Path],
    log: Any,
    extra_tokens: tuple = (),
    skeleton: str = "",
) -> bool:
    """Copy the first real source into target. Never touches real content."""
    if not _needs_seed(target, extra_tokens):
        return False
    for src in sources:
        if _is_real_base_md(src, extra_tokens):
            try:
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                log.info(f"[workspace] Seeded {target} from {src}")
                return True
            except OSError:
                return False
    if skeleton:
        try:
            target.write_text(skeleton, encoding="utf-8")
            log.info(f"[workspace] Wrote default skeleton {target}")
            return True
        except OSError:
            pass
    return False


def _is_real_base_md(path: Path, extra_tokens: tuple = ()) -> bool:
    """Non-empty BASE.md without unedited blueprint placeholders."""
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return False
        # [F-DOC-01] Both blueprint placeholder spellings must be rejected:
        # the cover_letters template shipped "[FULL NAME]" while resumes used
        # "[FIRSTNAME LASTNAME]", so the unedited blueprint passed as real.
        if "[FIRSTNAME LASTNAME]" in text or "[FULL NAME]" in text:
            return False
        return not any(tok in text for tok in extra_tokens)
    except OSError:
        return False


def resolve_base_resume_md(
    profile_dir: Optional[Path] = None,
    company_name: str = "",
    candidate_data: Optional[Dict[str, Any]] = None,
    company: str = "",
) -> Optional[Path]:
    """Canonical base-resume lookup (3-tier hierarchy).

    Canonical convention — resolve_base_resume_md(profile_dir, company_name):
    1. company_site_apply/<Slug>/resumes/BASE.md (Slug = company_slug)
    2. company_site_apply/<legacy>/resumes/BASE.md for each legacy
       space-separated dirname (full strip, then suffix-stripped short form)
    3. company_site_apply/resume.md
    4. profile_dir/resume.md
    Returns the first path that exists, is non-empty, and is free of the
    [FIRSTNAME LASTNAME] blueprint token; None when nothing usable exists.

    Legacy engine convention — resolve_base_resume_md(candidate_data,
    company) — is preserved verbatim (returns str, "" when missing) for the
    existing callers in experience_matcher / oracle_cloud_finger / tests.
    """
    if isinstance(profile_dir, dict) or candidate_data is not None:
        cand = profile_dir if isinstance(profile_dir, dict) else candidate_data
        comp = company_name if isinstance(profile_dir, dict) else company
        return _legacy_candidate_resume_md(cand, comp)
    if profile_dir is None:
        return None
    base = Path(profile_dir)
    cname = str(company_name or "").strip()
    candidates: List[Path] = []
    if cname and cname.lower() not in ("company", "unknown"):
        candidates.append(base / "company_site_apply" / company_slug(cname) / "resumes" / "BASE.md")
        for legacy in _legacy_company_dirnames(cname):
            candidates.append(base / "company_site_apply" / legacy / "resumes" / "BASE.md")
    candidates.append(base / "company_site_apply" / "resume.md")
    candidates.append(base / "resume.md")
    for path in candidates:
        if _is_real_base_md(path):
            return path
    return None


def resolve_base_cover_letter_md(
    profile_dir: Optional[Path] = None,
    company_name: str = "",
) -> Optional[Path]:
    """Canonical base-letter lookup (3-tier hierarchy).

    1. company_site_apply/<Slug>/cover_letters/BASE.md
    2. company_site_apply/<legacy>/cover_letters/BASE.md (full strip, then
       suffix-stripped short form)
    3. company_site_apply/cover_letter.md
    4. profile_dir/cover_letter_template.md
    Returns the first path that exists, is non-empty, and is free of both
    [FIRSTNAME LASTNAME] and {{FULL_NAME}}; None when nothing usable exists.
    """
    if profile_dir is None:
        return None
    base = Path(profile_dir)
    cname = str(company_name or "").strip()
    candidates: List[Path] = []
    if cname and cname.lower() not in ("company", "unknown"):
        candidates.append(base / "company_site_apply" / company_slug(cname) / "cover_letters" / "BASE.md")
        for legacy in _legacy_company_dirnames(cname):
            candidates.append(base / "company_site_apply" / legacy / "cover_letters" / "BASE.md")
    candidates.append(base / "company_site_apply" / "cover_letter.md")
    candidates.append(base / "cover_letter_template.md")
    for path in candidates:
        if _is_real_base_md(path, ("{{FULL_NAME}}",)):
            return path
    return None


def _legacy_candidate_resume_md(
    candidate_data: Optional[Dict[str, Any]] = None,
    company: str = "",
) -> str:
    """Pre-3A engine lookup, preserved verbatim for existing callers.

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
                if not p.is_absolute() and len(p.parts) == 1:
                    # [F-CSA-02] Bare slug -> Operations profile root.
                    try:
                        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
                        ops_p = resolve_profile_dir(str(val))
                        if ops_p.is_dir():
                            return ops_p
                    except Exception:
                        pass
    return next(
        (Path(r).parent if Path(r).name == "company_site_apply" else Path(r)
         for r in roots if Path(r).exists()),
        Path(os.getcwd()),
    )
