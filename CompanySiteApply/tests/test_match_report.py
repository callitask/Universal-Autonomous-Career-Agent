# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_MATCH_REPORT_INIT]
# Timestamp: 2026-10-13 15:00:00 +05:30
# Issue / Context: run_universal_apply.py referenced out-of-scope cfg_path
#                  (NameError in --autonomous mode). Both launchers now share
#                  save_match_report(); this pins its contract.
# ==============================================================================

import json
import tempfile
import unittest
from pathlib import Path

from CompanySiteApply.utils.match_report import save_match_report


class TestMatchReport(unittest.TestCase):
    def test_writes_to_given_output_dir(self):
        with tempfile.TemporaryDirectory() as d:
            out = save_match_report(Path(d) / "output", [{"job_id": "1"}])
            self.assertEqual(out, Path(d) / "output" / "jpmc_job_matches.json")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), [{"job_id": "1"}])

    def test_creates_missing_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            out = save_match_report(Path(d) / "a" / "b", [])
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
