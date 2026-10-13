# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [MATCH_REPORT_WRITER_INIT]
# Timestamp: 2026-10-13 15:00:00 +05:30
# Issue / Context: Both root launchers hand-rolled the match-report write;
#                  the run_universal_apply.py copy referenced cfg_path outside
#                  its scope (NameError in --autonomous mode, found live
#                  2026-10-13). Duplicated untested I/O drifts.
# Changes Made: Single tested save_match_report(output_dir, ranked_jobs)
#               helper; both launchers delegate to it.
# Rationale: One profile-sandboxed writer, pinned by unit test — the NameError
#            class cannot recur.
# Preventative Notes: Never inline match-report writes in launchers again.
# ==============================================================================

"""Profile-sandboxed match-report writer shared by all launchers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def save_match_report(output_dir: str | Path, ranked_jobs: List[Dict[str, Any]]) -> Path:
    """Write ranked matches to <output_dir>/jpmc_job_matches.json.

    Creates the directory when missing. Returns the written file path.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "jpmc_job_matches.json"
    out_file.write_text(json.dumps(ranked_jobs, indent=2), encoding="utf-8")
    return out_file
