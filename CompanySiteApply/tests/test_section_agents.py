import unittest
from unittest.mock import MagicMock, patch
from CompanySiteApply.section_agents import (
    BaseSectionAgent,
    ProfileSectionAgent,
    QuestionnaireSectionAgent,
    EducationSectionAgent,
    ExperienceSectionAgent,
    ReviewSectionAgent,
    SectionAgentDispatcher,
)


class TestSectionAgents(unittest.TestCase):
    def setUp(self):
        self.candidate_data = {
            "candidate": {
                "first_name": "Udaysagar",
                "last_name": "Kandpal",
                "full_name": "Udaysagar Kandpal",
                "email": "ukandpal2@gmail.com",
                "phone": "+91 9654258060",
                "city": "Bengaluru",
                "country": "India",
                "linkedin_url": "https://www.linkedin.com/in/udaykandpal",
                "education": [{
                    "institution": "Jaypee Institute of Information Technology",
                    "degree": "Bachelor's Degree",
                    "major": "Computer Science & Engineering",
                    "end_month": "December",
                    "end_year": "2015",
                    "country": "India"
                }],
                "work_experience": [
                    {"employer": "Cognizant", "bullets": ["Built backend"]},
                    {"employer": "Infosys", "bullets": ["Engineered APIs"]}
                ]
            }
        }

    def test_dispatcher_registry_and_lookup(self):
        dispatcher = SectionAgentDispatcher()
        sections = dispatcher.list_available_sections()
        self.assertIn("education", sections)
        self.assertIn("experience", sections)
        self.assertIn("questionnaire", sections)
        self.assertIn("profile", sections)
        self.assertIn("review", sections)

        edu_agent = dispatcher.get_agent("education")
        self.assertIsInstance(edu_agent, EducationSectionAgent)
        self.assertEqual(edu_agent.section_name, "education")
        self.assertEqual(edu_agent.target_stage, "section_3")

    def test_education_agent_can_handle(self):
        agent = EducationSectionAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/3"
        self.assertTrue(agent.can_handle(mock_page))
        self.assertTrue(agent.can_handle(mock_page, {"section": "education"}))

        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/1"
        self.assertFalse(agent.can_handle(mock_page))

    def test_experience_agent_can_handle(self):
        agent = ExperienceSectionAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/3"
        self.assertTrue(agent.can_handle(mock_page))
        self.assertTrue(agent.can_handle(mock_page, {"section": "experience"}))

    def test_questionnaire_agent_can_handle(self):
        agent = QuestionnaireSectionAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/2"
        self.assertTrue(agent.can_handle(mock_page))

    def test_profile_agent_can_handle(self):
        agent = ProfileSectionAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/1"
        self.assertTrue(agent.can_handle(mock_page))

    def test_review_agent_can_handle(self):
        agent = ReviewSectionAgent()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/4"
        self.assertTrue(agent.can_handle(mock_page))

    def test_review_agent_enforces_human_gate(self):
        agent = ReviewSectionAgent()
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first = mock_loc
        mock_loc.is_disabled.return_value = False
        mock_loc.all_text_contents.return_value = []
        mock_loc.input_value.return_value = "Existing Value"
        mock_page.locator.return_value = mock_loc

        res = agent.heal(mock_page, self.candidate_data)
        self.assertTrue(res.get("human_gate_active"))
        self.assertFalse(res.get("submit_clicked"))

    def test_dispatcher_dispatch_heal_unknown_section(self):
        dispatcher = SectionAgentDispatcher()
        res = dispatcher.dispatch_heal("unknown_sec", MagicMock(), self.candidate_data)
        self.assertFalse(res["success"])
        self.assertIn("Unknown section agent", res["error"])

    def test_dispatcher_resolve_agents_for_section3(self):
        dispatcher = SectionAgentDispatcher()
        mock_page = MagicMock()
        mock_page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/3"
        agents = dispatcher.resolve_agents_for_page(mock_page)
        agent_names = [a.section_name for a in agents]
        self.assertIn("education", agent_names)
        self.assertIn("experience", agent_names)
        self.assertNotIn("profile", agent_names)
        self.assertNotIn("questionnaire", agent_names)
    def test_education_isolation_from_experience(self):
        """Verifies EducationSectionAgent never interacts with Work Experience locators."""
        agent = EducationSectionAgent()
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.count.return_value = 0
        mock_loc.first = mock_loc
        mock_loc.all_text_contents.return_value = ["Bachelor's Degree", "Jaypee Institute of Information Technology"]
        mock_page.locator.return_value = mock_loc

        # Audit should not search for employerName or achievements
        agent.audit(mock_page, self.candidate_data)
        call_args = [str(call) for call in mock_page.locator.call_args_list]
        for arg in call_args:
            self.assertNotIn("employerName", arg)
            self.assertNotIn("achievements", arg)


if __name__ == "__main__":
    unittest.main()
