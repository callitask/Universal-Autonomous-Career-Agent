# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_DECISIONS_1_AND_4]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Decisions 1 (tailoring gate) and 4 (CLI auto-discovery)
#                  plus the Greenhouse human gate had zero regression pins.
# Changes Made: Pure-unit tests (mocked pages, temp dirs/env) for profile
#               resolution, tailoring-block stamping/propagation, Section 4
#               document skip, Stage 6 blocked ledger, and submit refusal.
# Rationale: Gates that halt applications must fail loudly in tests first.
# Preventative Notes: Never touch live profiles, CDP, or the network here.
# ==============================================================================

"""Regression tests for approved Decisions 1 & 4 + NEW-3 human gate."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch


class TestResolveCandidateProfile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._old_env = os.environ.get("JOB_AGENT_OPERATIONS")
        os.environ["JOB_AGENT_OPERATIONS"] = str(Path(self._tmp.name) / "Ops")
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop("JOB_AGENT_OPERATIONS", None)
        else:
            os.environ["JOB_AGENT_OPERATIONS"] = self._old_env

    def _mk(self, slug):
        d = Path(self._tmp.name) / "Ops" / "profiles" / slug
        d.mkdir(parents=True)
        (d / "candidate_config.json").write_text(json.dumps({"candidate": {}}))
        return d

    def _resolve(self):
        import run_universal_apply as rua
        return rua._resolve_candidate_profile

    def test_single_profile_autodiscovered(self):
        self._mk("alice_smith")
        slug, cfg = self._resolve()(None, None)
        self.assertEqual(slug, "alice_smith")
        self.assertTrue(cfg.name == "candidate_config.json")

    def test_zero_profiles_raise(self):
        (Path(self._tmp.name) / "Ops" / "profiles").mkdir(parents=True)
        with self.assertRaises(RuntimeError):
            self._resolve()(None, None)

    def test_multiple_profiles_raise_listing_names(self):
        self._mk("alice_smith")
        self._mk("bob_jones")
        with self.assertRaises(RuntimeError) as cm:
            self._resolve()(None, None)
        self.assertIn("alice_smith", str(cm.exception))
        self.assertIn("bob_jones", str(cm.exception))

    def test_default_user_refused(self):
        self._mk("alice_smith")
        with self.assertRaises(ValueError):
            self._resolve()("default_user", None)

    def test_missing_config_raises_filenotfound(self):
        with self.assertRaises((FileNotFoundError, RuntimeError)):
            self._resolve()("ghost_profile_xyz", None)


class TestTailoringBlockedPropagation(unittest.TestCase):
    def _agent(self):
        from CompanySiteApply.autonomous_job_agent import AutonomousJobAgent
        agent = AutonomousJobAgent.__new__(AutonomousJobAgent)
        agent.candidate_data = {"profile": "alice_smith"}
        agent.profile_slug = "alice_smith"
        import tempfile as _tf
        agent.ledger_path = Path(_tf.mkdtemp()) / "processed_ledger.json"
        return agent

    def test_tailoring_blocked_stamps_both_carriers(self):
        agent = self._agent()
        best_job = {"job_id": "123", "title": "Engineer"}
        res = agent._tailoring_blocked(best_job, "123", "boom")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "TAILORING_BLOCKED")
        for carrier in (best_job, agent.candidate_data):
            self.assertTrue(carrier["_tailoring_failed"])
            self.assertTrue(carrier["_skip_document_upload"])
            self.assertEqual(carrier["_missing_document"], "cover_letter")
            self.assertIn("--job-id", carrier["_fix_command"])

    def test_stage6_records_blocked_never_ready(self):
        import asyncio
        agent = self._agent()
        page = AsyncMock()
        page.screenshot = AsyncMock()
        target = {"job_id": "123", "title": "Engineer",
                  "details": {"company": "Acme"}, "_tailoring_failed": True}
        app_res = {"status": "REVIEW_BLOCKED", "blocked_reason": "TAILORING_BLOCKED",
                   "missing_document": "cover_letter", "fix_command": "cmd"}
        report = asyncio.run(agent.stage_6_verify_and_gate(
            page, target, app_res, screenshot_dir=Path(agent.ledger_path.parent)))
        self.assertEqual(report["status"], "REVIEW_BLOCKED")
        self.assertFalse(report["ready_for_submission"])
        self.assertFalse(report["submit_ready"])
        ledger = json.loads(agent.ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(ledger["jpmc:123"]["status"], "REVIEW_BLOCKED")

    def test_documents_heal_skips_upload_when_tailoring_failed(self):
        from CompanySiteApply.section_agents.sub_agents.documents_subagent import DocumentsSubAgent
        page = MagicMock()
        box = MagicMock()
        box.evaluate.return_value = True
        rm = MagicMock()
        rm.count.return_value = 1
        rm.is_visible.return_value = True
        box.locator.return_value.first = rm
        loc = MagicMock()
        loc.filter.return_value.first = box
        page.locator.return_value = loc
        cand = {"profile": "alice_smith", "_tailoring_failed": True,
                "_skip_document_upload": True, "_tailoring_error": "nope",
                "_fix_command": "fixme", "_missing_document": "cover_letter"}
        res = DocumentsSubAgent().heal(page, cand)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("status"), "REVIEW_BLOCKED")
        self.assertTrue(res.get("skip_retry"))
        self.assertFalse(res.get("cover_updated", False))
        rm.click.assert_called_once()

    def test_greenhouse_advance_refuses_submit_by_default(self):
        from CompanySiteApply.fingers.greenhouse_finger import GreenhouseFinger
        page = MagicMock()
        ok, msg = GreenhouseFinger().advance_step(page)
        self.assertFalse(ok)
        self.assertIn("Human gate", msg)
        page.locator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
