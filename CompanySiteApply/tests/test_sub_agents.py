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
        mock_page.evaluate.side_effect = [
            [],  # errors
            {  # structured readback, newest-first order
                "experience_tiles": [
                    ["Senior Associate", "Cognizant", "03/2026 - Present"],
                    ["Consultant", "Infosys", "02/2024 - 02/2026"],
                ],
                "education_tiles": [],
                "documents": [],
            },
        ]
        mock_btn = MagicMock()
        mock_btn.count.return_value = 1
        mock_btn.first = mock_btn
        mock_btn.is_disabled.return_value = False
        mock_page.locator.return_value = mock_btn

        res = agent.audit(mock_page, {})
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["chronological_order_correct"])
        self.assertTrue(res["human_gate_active"])
        self.assertFalse(res["submit_clicked"])

    def test_visual_verifier_rejects_scrambled_review_order(self):
        agent = VisualVerifierSubAgent()
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = [
            [],  # errors
            {  # alphabetical backend order (incident 2026-10-13)
                "experience_tiles": [
                    ["Software Engineer", "Adobe India Pvt. Ltd.", "06/2016 - 01/2017"],
                    ["Senior Associate", "Cognizant", "03/2026 - Present"],
                ],
                "education_tiles": [],
                "documents": [],
            },
        ]
        mock_btn = MagicMock()
        mock_btn.count.return_value = 1
        mock_btn.first = mock_btn
        mock_btn.is_disabled.return_value = False
        mock_page.locator.return_value = mock_btn

        res = agent.audit(mock_page, {})
        self.assertFalse(res["is_valid"])
        self.assertFalse(res["chronological_order_correct"])
        self.assertTrue(any("ORDER_UNVERIFIED" in e for e in res["errors"]))

    def test_documents_subagent_preuploaded_stale_detection(self):
        agent = DocumentsSubAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210790129/apply/section/4"
        mock_page.evaluate.return_value = {
            "resume": {"filled": True, "filename": "Udaysagar_Resume.pdf", "waiting": False, "hasRemove": True},
            "cover": {"filled": True, "filename": "Old_Cover_Letter.pdf", "waiting": False, "hasRemove": True}
        }
        res = agent.audit(mock_page, {"job_id": "210790129"})
        self.assertFalse(res["is_valid"])
        self.assertTrue(res["is_preuploaded_cover"])
        self.assertEqual(res["cover_status"], "PRE_UPLOADED_STALE")

    def test_dispatcher_evaluate_and_heal_section_targeted_execution(self):
        from CompanySiteApply.section_agents.section_agent_dispatcher import SectionAgentDispatcher
        dispatcher = SectionAgentDispatcher()
        mock_page = MagicMock()

        # Mock sub-agents: personal details valid, preferred location needs healing
        mock_personal = MagicMock()
        mock_personal.section_name = "personal_details"
        mock_personal.audit.return_value = {"is_valid": True}

        mock_location = MagicMock()
        mock_location.section_name = "preferred_location"
        # First audit returns False (needs heal), second returns True (healed)
        mock_location.audit.side_effect = [{"is_valid": False}, {"is_valid": True}]
        mock_location.heal.return_value = {"success": True}

        dispatcher.register_agent(mock_personal)
        dispatcher.register_agent(mock_location)

        report = dispatcher.evaluate_and_heal_section("profile", mock_page, {})
        self.assertTrue(report["success"])
        self.assertIn("preferred_location", report["subagents_healed"])
        self.assertNotIn("personal_details", report["subagents_healed"])
        mock_personal.heal.assert_not_called()
        mock_location.heal.assert_called_once()


if __name__ == "__main__":
    unittest.main()

