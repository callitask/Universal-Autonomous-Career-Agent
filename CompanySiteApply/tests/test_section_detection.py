# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_SECTION_DETECTION_PREVIEW_COLLISION]
# Timestamp: 2026-10-12 23:00:00 +05:30
# Issue / Context: Oracle HCM apply URLs contain /jobs/preview/<id>/ which
#                  collided with naked "review" substring checks, misrouting
#                  Section 1 → Section 4 Review (live incident 2026-10-12,
#                  requisition 210780039). Dispatcher + review/diversity/
#                  signature can_handle() had the same flaw.
# Changes Made: Regression tests pinning detect_current_section() and
#               DocumentsSubAgent job-id extraction against preview URLs.
# Rationale: URL routing must be proven by test, never by inspection —
#            this class slipped through a 75-green suite.
# Preventative Notes: Any new URL keyword check must add a preview-URL
#                     negative case here first.
# ==============================================================================

import unittest
from unittest.mock import MagicMock

from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
from CompanySiteApply.section_agents.sub_agents.documents_subagent import (
    DocumentsSubAgent,
)


def _orchestrator():
    orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
    return orch


def _page(url):
    p = MagicMock()
    p.url = url
    return p


_PREVIEW_S1 = (
    "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/"
    "CX_1002/jobs/preview/210780039/apply/section/1"
)


class TestSectionDetection(unittest.TestCase):
    def setUp(self):
        self.orch = _orchestrator()

    def test_preview_section_1_is_profile_not_review(self):
        sec = self.orch.detect_current_section(_page(_PREVIEW_S1))
        self.assertEqual(sec, "profile")

    def test_preview_sections_2_to_4(self):
        for n, expected in (
            ("2", "questionnaire"),
            ("3", "section_3"),
            ("4", "review"),
        ):
            url = _PREVIEW_S1.replace("/section/1", f"/section/{n}")
            self.assertEqual(
                self.orch.detect_current_section(_page(url)),
                expected,
                f"section/{n} misrouted",
            )

    def test_naked_preview_never_routes_to_review(self):
        # No /section/N and no /review boundary — must not be review.
        url = (
            "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/"
            "CX_1002/jobs/preview/210780039"
        )
        self.assertNotEqual(self.orch.detect_current_section(_page(url)), "review")

    def test_documents_job_id_from_preview_url(self):
        sub = DocumentsSubAgent()
        page = _page(_PREVIEW_S1)
        page.evaluate.return_value = ""
        ctx = sub._extract_job_context(page, {})
        self.assertEqual(ctx["job_id"], "210780039")


class TestCompetencyJetRadios(unittest.TestCase):
    """Incident 2026-10-12: primary-area + AWS proficiency render as JET radio
    groups. Pill-only scans missed them while Oracle flagged required."""

    def test_scan_detects_jet_radio_group(self):
        from CompanySiteApply.section_agents.scripts.s2_competency_questions import (
            scan_competency_questions,
        )
        page = MagicMock()
        page.evaluate.return_value = [
            {
                "q_id": "comp_q_1",
                "question_text": "Please select your primary area of expertise",
                "field_type": "RADIO_BUTTON",
                "available_choices": ["Business Analysis", "Software Engineering"],
                "current_value": None,
                "is_conditional": False,
                "is_required": True,
            }
        ]
        found = scan_competency_questions(page)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["field_type"], "RADIO_BUTTON")

    def test_read_back_empty_on_evaluate_failure(self):
        from CompanySiteApply.section_agents.scripts.s2_competency_questions import (
            _read_selected_value,
        )
        page = MagicMock()
        page.evaluate.side_effect = Exception("detached")
        self.assertEqual(_read_selected_value(page, "anything"), "")

    def test_apply_returns_false_when_row_missing(self):
        from CompanySiteApply.section_agents.scripts.s2_competency_questions import (
            _apply_competency_answer,
        )
        page = MagicMock()
        self.assertFalse(_apply_competency_answer(page, [], "no such question", "Yes", "RADIO_PILL"))


class TestRequiredFieldTripwire(unittest.TestCase):
    """Questionnaire audit must fail when Oracle renders its required flag."""

    def _questionnaire_page(self, required_text_hits, asterisk_hits):
        from CompanySiteApply.section_agents.questionnaire_section_agent import (
            QuestionnaireSectionAgent,
        )
        agent = QuestionnaireSectionAgent()
        page = MagicMock()
        page.locator.return_value.all_text_contents.return_value = []

        def _eval(script, *args):
            if "This information is required" in script:
                return required_text_hits
            if "asterisk-required-scan" in script:
                return asterisk_hits
            return []

        page.evaluate.side_effect = _eval
        return agent, page

    def test_audit_fails_on_required_text(self):
        agent, page = self._questionnaire_page(2, 0)
        res = agent.audit(page, {})
        self.assertFalse(res.get("is_valid", True))
        self.assertTrue(any("required question" in e for e in res.get("errors", [])))

    def test_audit_fails_on_red_asterisk(self):
        agent, page = self._questionnaire_page(0, 1)
        res = agent.audit(page, {})
        self.assertFalse(res.get("is_valid", True))
        self.assertTrue(any("red-asterisk" in e for e in res.get("errors", [])))

    def test_audit_passes_when_clean(self):
        agent, page = self._questionnaire_page(0, 0)
        res = agent.audit(page, {})
        self.assertTrue(res.get("is_valid", False))


class TestOrchestratorHardGate(unittest.TestCase):
    """Rank 2: a failing section must block advance (incident 210765001)."""

    def test_blocked_section_never_advances(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        orch.arm = MagicMock()
        orch.dispatcher = MagicMock()
        orch.dispatcher.evaluate_and_heal_section.return_value = {
            "success": False,
            "post_audits": {"technical_competency": {"is_valid": False}},
        }
        orch.advance = MagicMock(return_value=True)

        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210765001/apply/section/2"
        page.locator.return_value.count.return_value = 0
        orch.arm.connect.return_value = page

        res = orch.run({}, max_steps=2, screenshot_dir=None)
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("status"), "SECTION_BLOCKED")
        self.assertEqual(orch.dispatcher.evaluate_and_heal_section.call_count, 3)
        orch.advance.assert_not_called()


class TestDispatcherCascade(unittest.TestCase):
    """Rank 1: post-audit invalidation triggers a second heal pass."""

    def test_newly_invalid_agent_rehealed(self):
        from CompanySiteApply.section_agents.section_agent_dispatcher import (
            SectionAgentDispatcher,
        )
        binary = MagicMock()
        binary.section_name = "binary_questions"
        binary.audit.return_value = {"is_valid": True}
        binary.heal.return_value = {"success": True}
        comp = MagicMock()
        comp.section_name = "technical_competency"
        # pre-audit valid (hidden) -> post invalid (revealed) -> valid after cascade heal
        comp.audit.side_effect = [
            {"is_valid": True},
            {"is_valid": False},
            {"is_valid": True},
        ]
        comp.heal.return_value = {"success": True}
        dropdown = MagicMock()
        dropdown.section_name = "dropdown_questions"
        dropdown.audit.return_value = {"is_valid": True}
        dropdown.heal.return_value = {"success": True}

        dispatcher = SectionAgentDispatcher(agents=[binary, comp, dropdown])
        res = dispatcher.evaluate_and_heal_section("questionnaire", MagicMock(), {})
        self.assertTrue(res.get("success", False))
        self.assertEqual(res.get("cascade_passes"), 2)
        self.assertTrue(comp.heal.called)
        self.assertIn("technical_competency_cascade_2", res.get("healed_results", {}))


class TestPreferredLocationJetVariant(unittest.TestCase):
    """Rank 3: JET input markup without legacy block class must not pass empty."""

    def test_jet_input_without_pills_is_invalid(self):
        from CompanySiteApply.section_agents.sub_agents.preferred_location_subagent import (
            PreferredLocationSubAgent,
        )
        agent = PreferredLocationSubAgent()
        page = MagicMock()

        def _locator(selector, *args):
            m = MagicMock()
            if "preferredLocations" in selector and "preferred-location" not in selector:
                m.count.return_value = 1
            else:
                m.count.return_value = 0
            m.first = m
            m.locator.return_value = m
            m.all_text_contents.return_value = []
            return m

        page.locator.side_effect = _locator
        page.evaluate.return_value = []
        res = agent.audit(page, {})
        self.assertFalse(res.get("is_valid", True))

    def test_absent_block_stays_valid(self):
        from CompanySiteApply.section_agents.sub_agents.preferred_location_subagent import (
            PreferredLocationSubAgent,
        )
        agent = PreferredLocationSubAgent()
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        loc.first = loc
        page.locator.return_value = loc
        res = agent.audit(page, {})
        self.assertTrue(res.get("is_valid", False))


class TestStepperPriority(unittest.TestCase):
    """Rank 5: on-page stepper beats a stale /apply/email URL."""

    def test_stepper_step1_overrides_email_url(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210765001/apply/email"
        page.evaluate.return_value = "Step 1 of 4"
        self.assertEqual(orch.detect_current_section(page), "profile")

    def test_non_string_probe_falls_back_to_url(self):
        from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
        orch = ApplyOrchestrator.__new__(ApplyOrchestrator)
        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/jobs/preview/210780039/apply/section/1"
        page.evaluate.return_value = MagicMock()
        self.assertEqual(orch.detect_current_section(page), "profile")


if __name__ == "__main__":
    unittest.main()
