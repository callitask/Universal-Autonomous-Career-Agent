# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [RUNTIME_PATHS_INIT]
# Timestamp: 2026-10-14 00:00:00 +05:30
# Issue / Context: Runtime input/output (live profiles, artifacts, inspections,
#                  IPC bus) lived inside the git-tracked codebase. Enterprise
#                  layout keeps code in the repo and ALL runtime data in the
#                  sibling operations root.
# Changes Made: operations_root(), profiles_root(), artifacts_dir(),
#               inspections_dir(), ipc_dir() with env override + repo fallback.
# Rationale: Single choke point — every present and future path resolution
#            flows through here; no caller hardcodes a data location again.
# Preventative Notes: Env var JOB_AGENT_OPERATIONS renames/moves the data
#                     root without code edits. Never point these at profiles/
#                     inside the repo for live data (blueprint only).
# ==============================================================================

"""Enterprise runtime-data locations (outside the git-tracked codebase)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


def _repo_root(start: Optional[Path] = None) -> Path:
    here = Path(__file__).resolve()
    # CompanySiteApply/utils -> repo root is two levels up
    root = here.parent.parent.parent
    return root if root.exists() else Path(start) if start else Path.cwd()


def operations_root(repo_root: Optional[Path] = None) -> Path:
    """Sibling data root: `<repo> Operations` (env JOB_AGENT_OPERATIONS wins)."""
    base = Path(repo_root) if repo_root else _repo_root()
    env = os.environ.get("JOB_AGENT_OPERATIONS")
    if env:
        return Path(env)
    return base.parent / f"Operations {base.name}"


def profiles_root(repo_root: Optional[Path] = None) -> Path:
    """Live candidate sandboxes. Blueprint (default_user) stays in the repo."""
    return operations_root(repo_root) / "profiles"


def artifacts_dir(repo_root: Optional[Path] = None) -> Path:
    """Screenshots, transcripts, proofs."""
    return operations_root(repo_root) / "artifacts"


def inspections_dir(repo_root: Optional[Path] = None) -> Path:
    """Company-site DOM snapshots (runtime captures)."""
    return operations_root(repo_root) / "inspections" / "company_site_apply"


def ipc_dir(repo_root: Optional[Path] = None) -> Path:
    """Section IPC bus files (runtime state)."""
    return operations_root(repo_root) / "ipc"


def logs_dir(repo_root: Optional[Path] = None) -> Path:
    """Run logs (reserved)."""
    return operations_root(repo_root) / "logs"


def resolve_profile_dir(
    profile: str, repo_root: Optional[Path] = None
) -> Path:
    """Live profile dir in Operations, falling back to the repo (blueprint)."""
    slug = str(profile or "").strip()
    ops = profiles_root(repo_root) / slug
    if slug and ops.is_dir():
        return ops
    base = Path(repo_root) if repo_root else _repo_root()
    return base / "profiles" / slug


def ensure_operations_layout(repo_root: Optional[Path] = None) -> Dict[str, Path]:
    """Create the operations tree. Returns {key: path} mapping."""
    paths = {
        "root": operations_root(repo_root),
        "profiles": profiles_root(repo_root),
        "artifacts": artifacts_dir(repo_root),
        "inspections": inspections_dir(repo_root),
        "ipc": ipc_dir(repo_root),
        "logs": logs_dir(repo_root),
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    (paths["root"] / "README.md").write_text(
        "# Operations data root (NOT in git)\n\n"
        "profiles/ — live candidate sandboxes (config, resume, output, "
        "company_site_apply, APPLIED ON COMPANY WEBSITE).\n"
        "artifacts/ — screenshots, run transcripts, proofs.\n"
        "inspections/ — company-site DOM snapshots.\n"
        "ipc/ — section IPC bus runtime files.\n"
        "logs/ — run logs.\n"
        "The repo keeps code + default_user blueprint only. "
        "Move this tree via JOB_AGENT_OPERATIONS env var.\n",
        encoding="utf-8",
    )
    return paths
