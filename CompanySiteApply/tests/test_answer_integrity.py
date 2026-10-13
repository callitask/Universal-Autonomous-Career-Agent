# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_ANSWER_INTEGRITY_INIT]
# Timestamp: 2026-10-13 15:30:00 +05:30
# Issue / Context: Req 210788242 shipped "No Prior Experience" for a 10-year
#                  candidate: a scanner emitted an option pill's own text as
#                  the question, the brain echoed it back, and the click
#                  flipped the single-select group (screening_answers proof).
# Changes Made: Tests for option-title dropping, brain self-echo refusal,
#               deferral fallback, threadsafe generation wrapper, and honest
#               review-branch status.
# Preventative Notes: Never answer a question that is one of its own options.
# ==============================================================================

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from CompanySiteApply.utils.question_hygiene import drop_option_titled_questions


class TestQuestionHygiene(unittest.TestCase):
    def test_drops_option_titled_question(self):
        qs = [
            {
                "q_id": "x",
                "question_text": "No Prior Experience",
                "field_type": "RADIO_CHIP",
                "available_choices": ["No Prior Experience", "At least 1 year"],
            },
            {
                "q_id": "y",
                "question_text": "Real question?",
                "field_type": "BINARY_PILL",
                "available_choices": ["Yes", "No"],
            },
        ]
        out = drop_option_titled_questions(qs)
        self.assertEqual([q["q_id"] for q in out], ["y"])

    def test_drops_unknown_titled_question(self):
        qs = [{"q_id": "z", "question_text": "Unknown Binary Question", "available_choices": ["Yes", "No"]}]
        self.assertEqual(drop_option_titled_questions(qs), [])


class TestBrainAnswerIntegrity(unittest.TestCase):
    def _brain(self):
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        AIBrainResolver._instance = None
        return AIBrainResolver.get_instance({
            "candidate": {
                "full_name": "Test User",
                "country": "India",
                "total_experience_years": 10,
            },
            "ats_answers": {},
            "taxonomy_skills": {},
        })

    def test_self_echo_refused(self):
        brain = self._brain()
        rec = brain.resolve_question(
            question_text="No Prior Experience",
            control_type="RADIO_CHIP",
            options=["No Prior Experience", "At least 1 year", "At least 5 years of experience"],
        )
        self.assertIsNone(rec.get("answer"))
        self.assertEqual(rec.get("source"), "REFUSED_SELF_ECHO")

    def test_unrecognized_question_defers(self):
        brain = self._brain()
        rec = brain.resolve_question(
            question_text="Zqx jumbled wobble?",
            control_type="RADIO_CHIP",
            options=["Alpha", "Beta"],
        )
        self.assertEqual(rec.get("answer"), "")

    def test_tier_still_resolves(self):
        brain = self._brain()
        rec = brain.resolve_question(
            question_text="Please select the relevant years of work experience you have for this role:",
            control_type="RADIO_PILL",
            options=["No Prior Experience", "At least 1 year", "At least 5 years of experience"],
        )
        self.assertEqual(rec.get("answer"), "At least 5 years of experience")


class TestThreadsafeGeneration(unittest.TestCase):
    def test_offload_inside_running_loop(self):
        from CompanySiteApply.section_agents.scripts.s4_cover_letter_upload import (
            _generate_cover_letter_threadsafe,
        )

        async def _run():
            with patch(
                "core.generate_professional_cover_letter.generate_tailored_cover_letter",
                return_value="letter.pdf",
            ):
                return _generate_cover_letter_threadsafe({}, {"job_id": "1"}, "/tmp")

        self.assertEqual(asyncio.run(_run()), "letter.pdf")


class TestReviewBranchHonesty(unittest.TestCase):
    def test_failed_audit_returns_review_blocked(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        orch.arm = MagicMock()
        orch.dispatcher = MagicMock()
        orch.dispatcher.evaluate_and_heal_section.return_value = {"success": True}
        orch.dispatcher.dispatch_audit.return_value = {
            "is_valid": False,
            "errors": ["ORDER_UNVERIFIED: review-screen tiles not newest-first"],
        }
        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210788242/apply/section/4"
        page.locator.return_value.count.return_value = 0
        orch.arm.connect.return_value = page

        res = orch.run({}, max_steps=2, screenshot_dir=None)
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("status"), "REVIEW_BLOCKED")
        self.assertIn("transcript_path", res)
        if res.get("transcript_path"):
            import os
            self.addCleanup(os.unlink, res["transcript_path"])


class TestCompetencyWrongPickCorrection(unittest.TestCase):
    """Incident 210788242: tier group showed 'No Prior Experience' selected."""

    def test_wrong_pick_is_reclicked_to_truth(self):
        from CompanySiteApply.section_agents.scripts.s2_competency_questions import (
            heal_competency_questions,
        )
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        AIBrainResolver._instance = None
        candidate_data = {
            "candidate": {
                "full_name": "Test User",
                "country": "India",
                "total_experience_years": 10,
            },
            "ats_answers": {},
            "taxonomy_skills": {},
        }
        tier_q = "Please select the relevant years of work experience you have for this role:"
        tier_opts = [
            "No Prior Experience",
            "At least 1 year",
            "At least 2 years of experience",
            "At least 3 years of experience",
            "At least 5 years of experience",
        ]

        page = MagicMock()

        def _eval(script, *args):
            if '|| "Competency Question"' in script:
                return []
            if "current_value" in script:
                return [{
                    "question_text": tier_q,
                    "available_choices": tier_opts,
                    "current_value": "No Prior Experience",
                }]
            if "aria-checked" in script and "targetQ" in script:
                return "At least 5 years of experience"
            return []

        page.evaluate.side_effect = _eval

        clicked = []

        def _pill(text):
            p = MagicMock()
            p.inner_text.return_value = text
            p.click.side_effect = lambda: clicked.append(text)
            return p

        pills = [_pill(t) for t in tier_opts]
        label = MagicMock()
        label.count.return_value = 1
        label.inner_text.return_value = tier_q
        row = MagicMock()
        row.is_visible.return_value = True
        row.locator.side_effect = lambda sel: (
            MagicMock(first=label, count=MagicMock(return_value=1))
            if "legend" in sel else MagicMock(all=MagicMock(return_value=pills))
        )

        def _locator(selector, *args):
            if "legend" in selector or "label" in selector or ".cx-form-label" in selector:
                return MagicMock(first=label, count=MagicMock(return_value=1))
            m = MagicMock()
            m.all.return_value = [row]
            return m

        page.locator.side_effect = _locator

        res = heal_competency_questions(page, candidate_data)
        self.assertTrue(res.get("success", False))
        self.assertIn("At least 5 years of experience", clicked)
        self.assertNotIn("No Prior Experience", clicked)


class TestEmailBranchGate(unittest.TestCase):
    def test_unaccepted_terms_blocks_advance(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        orch.arm = MagicMock()
        orch.dispatcher = MagicMock()
        orch.advance = MagicMock(return_value=True)

        email_box = MagicMock()
        email_box.count.return_value = 1
        email_box.input_value.return_value = ""
        email_box.first = email_box
        cb = MagicMock()
        cb.count.return_value = 1
        cb.is_checked.return_value = False
        cb.first = cb
        modal = MagicMock()
        modal.count.return_value = 0
        modal.first = modal

        def _locator(selector, *args):
            if "primary-email" in selector:
                return email_box
            if "checkbox" in selector:
                return cb
            return modal

        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210788242/apply/email"
        page.evaluate.return_value = MagicMock()
        page.locator.side_effect = _locator
        orch.arm.connect.return_value = page

        res = orch.run({"email": "a@b.c"}, max_steps=2, screenshot_dir=None)
        self.assertEqual(res.get("status"), "SECTION_BLOCKED")
        orch.advance.assert_not_called()


class TestCompetencyAuditTruthCheck(unittest.TestCase):
    """Audit must flag answered-but-wrong picks, not just empties."""

    def test_wrong_pick_fails_audit(self):
        from CompanySiteApply.section_agents.sub_agents.technical_competency_subagent import (
            TechnicalCompetencySubAgent,
        )
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        AIBrainResolver._instance = None
        agent = TechnicalCompetencySubAgent()
        page = MagicMock()
        tier_q = "Please select the relevant years of work experience you have for this role:"
        tier_opts = ["No Prior Experience", "At least 1 year", "At least 5 years of experience"]

        def _eval(script, *args):
            if "Competency Question" in script and "current_value" not in script:
                return []  # unanswered scan: nothing empty
            if "current_value" in script:
                return [{
                    "question_text": tier_q,
                    "available_choices": tier_opts,
                    "current_value": "No Prior Experience",
                }]
            return []

        page.evaluate.side_effect = _eval
        res = agent.audit(page, {
            "candidate": {"full_name": "T", "country": "India", "total_experience_years": 10},
            "ats_answers": {},
            "taxonomy_skills": {},
        })
        self.assertFalse(res.get("is_valid", True))
        self.assertTrue(res.get("mismatched_answers"))

    def test_correct_pick_passes_audit(self):
        from CompanySiteApply.section_agents.sub_agents.technical_competency_subagent import (
            TechnicalCompetencySubAgent,
        )
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        AIBrainResolver._instance = None
        agent = TechnicalCompetencySubAgent()
        page = MagicMock()
        tier_q = "Please select the relevant years of work experience you have for this role:"
        tier_opts = ["No Prior Experience", "At least 1 year", "At least 5 years of experience"]

        def _eval(script, *args):
            if "Competency Question" in script and "current_value" not in script:
                return []
            if "current_value" in script:
                return [{
                    "question_text": tier_q,
                    "available_choices": tier_opts,
                    "current_value": "At least 5 years of experience",
                }]
            return []

        page.evaluate.side_effect = _eval
        res = agent.audit(page, {
            "candidate": {"full_name": "T", "country": "India", "total_experience_years": 10},
            "ats_answers": {},
            "taxonomy_skills": {},
        })
        self.assertTrue(res.get("is_valid", False))


class TestReviewReorderRetry(unittest.TestCase):
    def test_retry_until_verified(self):
        from CompanySiteApply.section_agents.review_section_agent import ReviewSectionAgent
        agent = ReviewSectionAgent()
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        page.evaluate.return_value = []
        cand = {"candidate": {}, "job_id": "1"}

        calls = {"n": 0}

        import CompanySiteApply.section_agents.scripts.s3_experience_ordering as ordering

        def _fake_reorder(p):
            calls["n"] += 1
            if calls["n"] < 2:
                return {"success": False, "order_verified": False}
            return {"success": True, "order_verified": True, "ko_sorted_count": 1, "dom_sorted_count": 1}

        ordering.reorder_experience_tiles = _fake_reorder
        try:
            with patch.object(
                type(agent.docs_subagent), "heal", return_value={"success": True}
            ), patch.object(
                type(agent.diversity_subagent), "heal", return_value={"success": True}
            ), patch.object(
                type(agent.signature_subagent), "heal", return_value={"success": True}
            ), patch.object(
                type(agent.visual_subagent), "heal",
                return_value={"success": True, "audit": {"is_valid": True}},
            ), patch.object(
                type(agent), "verify", return_value=True,
            ):
                res = agent.heal(page, cand)
        finally:
            import importlib
            importlib.reload(ordering)
        self.assertTrue(res.get("order_verified", False))
        self.assertEqual(calls["n"], 2)


class TestVisualHealReordersLivePath(unittest.TestCase):
    """Reorder must live where the dispatcher executes (visual heal)."""

    def test_heal_invokes_reorder_before_audit(self):
        from CompanySiteApply.section_agents.sub_agents.visual_verifier_subagent import (
            VisualVerifierSubAgent,
        )
        import CompanySiteApply.section_agents.scripts.s3_experience_ordering as ordering

        agent = VisualVerifierSubAgent()
        page = MagicMock()
        page.evaluate.side_effect = [
            [],  # errors
            {"experience_tiles": [], "education_tiles": [], "documents": []},
        ]
        btn = MagicMock()
        btn.count.return_value = 1
        btn.first = btn
        btn.is_disabled.return_value = False
        page.locator.return_value = btn

        calls = {"n": 0}

        def _fake_reorder(p):
            calls["n"] += 1
            return {"success": True, "order_verified": True}

        ordering.reorder_experience_tiles = _fake_reorder
        try:
            res = agent.heal(page, {})
        finally:
            import importlib
            importlib.reload(ordering)
        self.assertEqual(calls["n"], 1)
        self.assertTrue(res.get("order_detail", {}).get("order_verified", False))


class TestGateErrorSweep(unittest.TestCase):
    def test_visible_error_text_blocks_advance(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        orch.arm = MagicMock()
        orch.dispatcher = MagicMock()
        orch.dispatcher.evaluate_and_heal_section.return_value = {
            "success": True,
            "post_audits": {},
        }
        orch.advance = MagicMock(return_value=True)

        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210788242/apply/section/2"
        page.evaluate.return_value = ["This information is required."]
        page.locator.return_value.count.return_value = 0
        orch.arm.connect.return_value = page

        res = orch.run({}, max_steps=2, screenshot_dir=None)
        self.assertEqual(res.get("status"), "SECTION_BLOCKED")
        self.assertIn("gate_errors", res.get("eval_result", {}))
        orch.advance.assert_not_called()


class TestDropdownOrphanSweep(unittest.TestCase):
    def test_orphan_required_combobox_flagged(self):
        from CompanySiteApply.section_agents.sub_agents.dropdown_question_subagent import (
            DropdownQuestionSubAgent,
        )
        agent = DropdownQuestionSubAgent()
        page = MagicMock()
        page.evaluate.side_effect = [
            ["Do you have experience with programming languages? Choose your top 2."],
            [],
        ]
        res = agent.audit(page, {})
        self.assertFalse(res.get("is_valid", True))
        self.assertTrue(res.get("unanswered_dropdown_questions"))


class TestResumeFreshness(unittest.TestCase):
    def test_stale_attached_resume_replaced(self):
        import tempfile
        from pathlib import Path as _Path
        from unittest.mock import patch
        from CompanySiteApply.section_agents.scripts.s4_resume_upload import (
            heal_resume_upload,
        )

        with tempfile.TemporaryDirectory() as d:
            new_resume = _Path(d) / "Test_User_Resume.pdf"
            new_resume.write_text("pdf-bytes", encoding="utf-8")

            set_files = {}

            file_input = MagicMock()
            file_input.count.return_value = 1
            file_input.first = file_input
            file_input.set_input_files.side_effect = lambda p: set_files.update(path=p)
            rm_btn = MagicMock()
            rm_btn.count.return_value = 1
            rm_btn.first = rm_btn
            rm_btn.is_visible.return_value = True

            res_box = MagicMock()
            res_box.count.return_value = 1
            res_box.is_visible.return_value = True

            def _eval(script, *args):
                if "--filled" in script:
                    return True
                if "download" in script:
                    return "Old_Stale_Resume.pdf"
                return False

            res_box.evaluate.side_effect = _eval

            def _box_locator(selector, *args):
                if "file" in selector:
                    return file_input
                return rm_btn

            res_box.locator.side_effect = _box_locator

            filtered = MagicMock()
            filtered.first = res_box
            container = MagicMock()
            container.filter.return_value = filtered
            page = MagicMock()
            page.locator.return_value = container

            cand = {"candidate": {"full_name": "Test User"}, "job_id": "1"}
            with patch(
                "CompanySiteApply.utils.config_resolver.resolve_search_roots",
                return_value=[d],
            ):
                res = heal_resume_upload(page, cand)

            self.assertTrue(res.get("success", False))
            self.assertTrue(res.get("uploaded", False))
            self.assertEqual(set_files.get("path"), str(new_resume))

    def test_matching_resume_skipped(self):
        import tempfile
        from pathlib import Path as _Path
        from unittest.mock import patch
        from CompanySiteApply.section_agents.scripts.s4_resume_upload import (
            heal_resume_upload,
        )

        with tempfile.TemporaryDirectory() as d:
            resume = _Path(d) / "Test_User_Resume.pdf"
            resume.write_text("pdf-bytes", encoding="utf-8")

            res_box = MagicMock()
            res_box.count.return_value = 1
            res_box.is_visible.return_value = True

            def _eval(script, *args):
                if "--filled" in script:
                    return True
                if "download" in script:
                    return "Test_User_Resume.pdf"
                return False

            res_box.evaluate.side_effect = _eval
            res_box.locator.side_effect = Exception("must not touch DOM when fresh")

            filtered = MagicMock()
            filtered.first = res_box
            container = MagicMock()
            container.filter.return_value = filtered
            page = MagicMock()
            page.locator.return_value = container

            cand = {"candidate": {"full_name": "Test User"}, "job_id": "1"}
            with patch(
                "CompanySiteApply.utils.config_resolver.resolve_search_roots",
                return_value=[d],
            ):
                res = heal_resume_upload(page, cand)

            self.assertTrue(res.get("success", False))
            self.assertFalse(res.get("uploaded", True))


if __name__ == "__main__":
    unittest.main()
