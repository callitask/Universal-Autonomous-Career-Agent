# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_RUNTIME_PATHS_INIT]
# Timestamp: 2026-10-14 00:00:00 +05:30
# Issue / Context: Runtime data must live outside the git-tracked codebase
#                  (Operations sibling), with repo fallback for transition.
# ==============================================================================

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from CompanySiteApply.utils import runtime_paths
from CompanySiteApply.utils.runtime_paths import (
    artifacts_dir,
    ensure_operations_layout,
    operations_root,
    resolve_profile_dir,
)


class TestRuntimePaths(unittest.TestCase):
    def test_operations_root_default_and_env(self):
        self.assertEqual(operations_root(Path("F:/JOB AI AGENT")), Path("F:/Operations JOB AI AGENT"))
        with patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": "F:/Custom Ops"}):
            self.assertEqual(operations_root(), Path("F:/Custom Ops"))

    def test_resolve_profile_prefers_operations(self):
        with tempfile.TemporaryDirectory() as d:
            ops = Path(d) / "ops"
            (ops / "profiles" / "someone").mkdir(parents=True)
            repo = Path(d) / "repo"
            (repo / "profiles" / "someone").mkdir(parents=True)
            with patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": str(ops)}):
                got = resolve_profile_dir("someone", repo)
                self.assertEqual(got, ops / "profiles" / "someone")

    def test_resolve_profile_falls_back_to_repo(self):
        with tempfile.TemporaryDirectory() as d:
            ops = Path(d) / "ops"
            ops.mkdir()
            repo = Path(d) / "repo"
            (repo / "profiles" / "blue").mkdir(parents=True)
            with patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": str(ops)}):
                got = resolve_profile_dir("blue", repo)
                self.assertEqual(got, repo / "profiles" / "blue")

    def test_ensure_layout_creates_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": str(Path(d) / "ops2")}):
                paths = ensure_operations_layout(Path(d) / "repo")
                for key in ("root", "profiles", "artifacts", "inspections", "ipc", "logs"):
                    self.assertTrue(paths[key].is_dir(), key)
                self.assertTrue((paths["root"] / "README.md").exists())

    def test_artifacts_under_operations(self):
        with patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": "F:/Ops X"}):
            self.assertEqual(artifacts_dir(), Path("F:/Ops X/artifacts"))


if __name__ == "__main__":
    unittest.main()
