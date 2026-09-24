# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-23 14:00:00 +05:30
# Issue / Context: cli_scraper.py and oracle_cloud_finger.py hardcoded a live
#   profile folder name in DEFAULT_CONFIG_PATH / search_roots (PII + purity fail).
# Changes Made: Created config_resolver.py — dynamic resolution via --config /
#   --profile args, candidate_data profile_dir hint, and default_user blueprint
#   fallback only. No live profile name literals.
# Rationale: Zero-hardcoding; CompanySiteApply stays on-demand/human-gated.
# Preventative Notes: Never add a live profile name here. Blueprint fallback is
#   profiles/default_user only.
# ==============================================================================
"""Dynamic candidate-config resolution for CompanySiteApply. No PII literals."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_BLUEPRINT = Path("profiles") / "default_user" / "candidate_config.json"


def _repo_root(start: Optional[Path] = None) -> Path:
    base = Path(start) if start else Path.cwd()
    # CompanySiteApply/utils -> repo root is two levels up
    here = Path(__file__).resolve()
    root = here.parent.parent.parent
    return root if root.exists() else base


def resolve_candidate_config(
    explicit_path: Optional[str] = None,
    candidate_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load candidate config dict without hardcoded profile names."""
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    if isinstance(candidate_data, dict):
        for key in ("config_path", "candidate_config_path", "profile_dir"):
            val = candidate_data.get(key)
            if val:
                p = Path(str(val))
                candidates.append(p / "candidate_config.json" if p.is_dir() else p)
        prof = candidate_data.get("profile")
        if prof:
            candidates.append(Path(str(prof)) / "candidate_config.json")
    root = _repo_root()
    candidates.append(root / _BLUEPRINT)
    candidates.append(Path.cwd() / _BLUEPRINT)
    for path in candidates:
        try:
            if path and path.exists() and path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def resolve_search_roots(candidate_data: Optional[Dict[str, Any]] = None) -> list[str]:
    """Directories to search for relative resume files. No live names."""
    roots: list[str] = []
    if isinstance(candidate_data, dict):
        for key in ("profile_dir", "profile", "config_path"):
            val = candidate_data.get(key)
            if val:
                p = Path(str(val))
                roots.append(str(p if p.is_dir() else p.parent))
    root = str(_repo_root())
    roots.extend([str(Path(root) / "profiles" / "default_user"), root, os.getcwd()])
    # de-duplicate, keep order
    seen, out = set(), []
    for r in roots:
        if r and r not in seen:
            seen.add(r)
            out.append(r)
    return out
