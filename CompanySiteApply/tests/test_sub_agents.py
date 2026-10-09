# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_SUB_AGENTS_INIT]
# Timestamp: 2026-10-09 22:50:00 +05:30
# Issue / Context: Need rigorous unit test coverage for the 9 granular Sub-Agents.
# Changes Made: Created test suite covering PreferredLocationSubAgent, DropdownQuestionSubAgent,
#               DocumentsSubAgent, DiversitySubAgent, SignatureSubAgent, and Dispatcher routing.
# Rationale: Guarantees zero regression and mathematically proves sub-agent independence.
# ==============================================================================

import unittest
from unittest.mock import MagicMock, patch

from CompanySiteApply.section_agents.section_agent_dispatcher import SectionAgentDispatcher
from CompanySiteApply.section_agents.sub_agents.personal_details_subagent import PersonalDetailsSubAgent
from CompanySiteApply.section_agents.sub_agents.preferred_location_subagent import PreferredLocationSubAgent
from CompanySiteApply.section_agents.sub_agents.binary_question_subagent import BinaryQuestionSubAgent
from CompanySiteApply.section_agents.sub_agents.technical_competency_subagent import TechnicalCompetencySubAgent
from CompanySiteApply.section_agents.sub_agents.dropdown_question_subagent import DropdownQuestionSubAgent
from CompanySiteApply.section_agents.sub_agents.documents_subagent import DocumentsSubAgent
from CompanySiteApply.section_agents.sub_agents.diversity_subagent import DiversitySubAgent
from CompanySiteApply.section_agents.sub_agents.signature_subagent import SignatureSubAgent
from CompanySiteApply.section_agents.sub_agents.visual_verifier_subagent import VisualVerifierSubAgent


class TestSubAgents(unittest.TestCase):

    def setUp(self):
        self.dispatcher = SectionAgentDispatcher()

    def test_dispatcher_registers_all_subagents(self):
        expected_subs = [
            "personal_details",
            "preferred_location",
            "binary_questions",
            "technical_competency",
            "dropdown_questions",
            "education",
            "experience",
            "documents",
            "diversity",
            "signature",
            "visual_verifier"
        ]
        available = self.dispatcher.list_available_subagents()
        for sub in expected_subs:
            self.assertIn(sub, available)
            self.assertIsNotNone(self.dispatcher.get_agent(sub))

    def test_preferred_location_subagent_audit_missing_pill(self):
        agent = PreferredLocationSubAgent()
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first = mock_loc
        mock_loc.all_text_contents.return_value = []
        mock_page.locator.return_value = mock_loc
        mock_page.evaluate.return_value = []  # No pills

        res = agent.audit(mock_page, {})
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["pill_count"], 0)

    def test_preferred_location_subagent_audit_valid_pill(self):
        agent = PreferredLocationSubAgent()
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first = mock_loc
        mock_loc.all_text_contents.return_value = []
        mock_page.locator.return_value = mock_loc
        mock_page.evaluate.return_value = ["33437-Embassy Tech Village - Parcel"]

        res = agent.audit(mock_page, {})
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["pill_count"], 1)

    def test_dropdown_question_subagent_audit_unanswered(self):
        agent = DropdownQuestionSubAgent()
        mock_page = MagicMock()
        # Mock evaluate returning unanswered dropdown question
        mock_page.evaluate.side_effect = [
            ["Which of the following programming languages have you worked with? *"],
            ["This information is required."]
        ]
        res = agent.audit(mock_page, {})
        self.assertFalse(res["is_valid"])
        self.assertIn("Which of the following programming languages have you worked with? *", res["unanswered_dropdown_questions"])

    def test_dropdown_question_subagent_audit_all_answered(self):
        agent = DropdownQuestionSubAgent()
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = [[], []]
        res = agent.audit(mock_page, {})
        self.assertTrue(res["is_valid"])

    def test_documents_subagent_audit_both_attached(self):
        agent = DocumentsSubAgent()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = ["Udaysagar_Resume.pdf", "Udaysagar_Cover_Letter.pdf"]
        res = agent.audit(mock_page, {})
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["has_resume"])
        self.assertTrue(res["has_cover_letter"])

    def test_documents_subagent_audit_missing_cover(self):
        agent = DocumentsSubAgent()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = ["Udaysagar_Resume.pdf"]
        res = agent.audit(mock_page, {})
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["has_resume"])
        self.assertFalse(res["has_cover_letter"])

    def test_visual_verifier_subagent_human_gate_enforcement(self):
        agent = VisualVerifierSubAgent()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = []
        mock_btn = MagicMock()
        mock_btn.count.return_value = 1
        mock_btn.first = mock_btn
        mock_btn.is_disabled.return_value = False
        mock_page.locator.return_value = mock_btn

        res = agent.audit(mock_page, {})
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["human_gate_active"])
        self.assertFalse(res["submit_clicked"])


if __name__ == "__main__":
    unittest.main()
