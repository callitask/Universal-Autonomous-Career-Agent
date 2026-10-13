# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_REPO_STRUCTURE_GUARD]
# Timestamp: 2026-10-13 01:00:00 +05:30
# Issue / Context: One-off session scripts used to accumulate in the repo
#                  root (4 archived to scripts/legacy_company_apply/ on
#                  2026-10-12). The 2 remaining root launchers are
#                  workspace-level by design (they resolve profiles/,
#                  artifacts/, and per-profile output dirs from the repo root).
# Changes Made: Allowlist guard failing on any new root .py or stray proof
#               artifacts at root, so recurrence breaks the suite, not review.
# Preventative Notes: New entry points belong in CompanySiteApply/ or
#                     scripts/ — never the root.
# ==============================================================================

import unittest
from pathlib import Path

# Repo root derived from this file's location (CompanySiteApply/tests/ is two levels down).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The only workspace-level launchers. They must stay at root because they
# resolve profiles/, artifacts/, and per-profile output dirs relative to it.
ALLOWED_ROOT_PY = {
    "run_universal_apply.py",
    "search_and_evaluate_jpmc_jobs.py",
}

# Global secrets live at root by design (gitignored, never in profiles/).
# Every other runtime JSON belongs in profiles/<slug>/output/.
ALLOWED_ROOT_JSON = {
    "colab_credentials.json",
    "gemini_credentials.json",
}


class TestRepoStructure(unittest.TestCase):
    def test_root_py_allowlist(self):
        root_py = {p.name for p in REPO_ROOT.glob("*.py")}
        stray = root_py - ALLOWED_ROOT_PY
        self.assertEqual(
            stray,
            set(),
            f"Non-canonical .py at repo root (move to CompanySiteApply/ or scripts/): {sorted(stray)}",
        )

    def test_no_proof_artifacts_at_root(self):
        stray = [
            p.name
            for p in REPO_ROOT.iterdir()
            if p.is_file() and p.suffix.lower() in (".png", ".log", ".tmp")
        ]
        self.assertEqual(
            stray, [], f"Proof/log artifacts belong in artifacts/, not root: {stray}"
        )

    def test_no_runtime_json_at_root(self):
        stray = [
            p.name
            for p in REPO_ROOT.iterdir()
            if p.is_file() and p.suffix.lower() == ".json" and p.name not in ALLOWED_ROOT_JSON
        ]
        self.assertEqual(
            stray,
            [],
            f"Runtime JSON belongs in profiles/<slug>/output/, not root: {stray}",
        )


if __name__ == "__main__":
    unittest.main()
