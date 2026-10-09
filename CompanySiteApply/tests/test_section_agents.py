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


class MockPill:
    def __init__(self, text: str, selected: bool = False):
        self._text = text
        self._selected = selected
        self.clicked = False

    def inner_text(self):
        return self._text

    def get_attribute(self, attr: str):
        if attr == "class":
            return "selected" if self._selected else ""
        if attr == "aria-pressed":
            return "true" if self._selected else "false"
        return None

    def click(self):
        self.clicked = True


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
                "total_experience_years": 10,
                "resume_headline": "Lead Java Architect | High-Performance Systems",
                "profile_summary": "Expert in backend distributed systems, enterprise integration, microservices.",
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
            },
            "taxonomy_skills": {
                "Domain Skills": ["Backend Architecture", "Microservices"],
                "Technical Skills": ["Java", "Kafka", "AWS"]
            },
            "demographics": {
                "gender": "Male",
                "ethnicity": "Asian",
                "military_status": "No"
            },
            "ats_answers": {
                "skill_years_experience": {
                    "aws": 5,
                    "java": 10
                }
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

        agent.audit(mock_page, self.candidate_data)
        call_args = [str(call) for call in mock_page.locator.call_args_list]
        for arg in call_args:
            self.assertNotIn("employerName", arg)
            self.assertNotIn("achievements", arg)

    # =========================================================================
    # UNIVERSAL DYNAMIC MATCHING TESTS (ZERO HARDCODING VALIDATION)
    # =========================================================================

    def test_dynamic_experience_tier_senior_candidate(self):
        agent = QuestionnaireSectionAgent()
        pills = [
            MockPill("Less than 1 year"),
            MockPill("1 to 3 years"),
            MockPill("3 to 5 years"),
            MockPill("At least 5 years")
        ]
        # Candidate with 10 years experience must pick "At least 5 years"
        best = agent._resolve_experience_tier(10.0, pills)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "At least 5 years")

    def test_dynamic_experience_tier_mid_candidate(self):
        agent = QuestionnaireSectionAgent()
        pills = [
            MockPill("Less than 1 year"),
            MockPill("1 to 3 years"),
            MockPill("3 to 5 years"),
            MockPill("5+ years")
        ]
        # Candidate with 3.5 years experience must pick "3 to 5 years"
        best = agent._resolve_experience_tier(3.5, pills)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "3 to 5 years")

    def test_dynamic_experience_tier_junior_candidate(self):
        agent = QuestionnaireSectionAgent()
        pills = [
            MockPill("Less than 1 year"),
            MockPill("1 to 3 years"),
            MockPill("3 to 5 years"),
            MockPill("5+ years")
        ]
        # Candidate with 1.5 years experience must pick "1 to 3 years"
        best = agent._resolve_experience_tier(1.5, pills)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "1 to 3 years")

    def test_dynamic_experience_tier_fresher_candidate(self):
        agent = QuestionnaireSectionAgent()
        pills = [
            MockPill("No prior experience"),
            MockPill("1 to 3 years"),
            MockPill("3 to 5 years"),
            MockPill("5+ years")
        ]
        # Fresher with 0 years experience must pick "No prior experience"
        best = agent._resolve_experience_tier(0.0, pills)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "No prior experience")

    def test_dynamic_domain_resolution_marketing_profile(self):
        agent = QuestionnaireSectionAgent()
        marketing_profile = {
            "candidate": {
                "total_experience_years": 4,
                "resume_headline": "Senior Growth Marketing Manager | B2B Demand Gen | SEO & Content",
                "profile_summary": "Performance marketing expert leading digital acquisition and campaigns."
            },
            "taxonomy_skills": {
                "Domain Skills": ["Growth Marketing", "Demand Generation", "Digital Advertising"],
                "Technical Skills": ["Google Analytics", "HubSpot", "Marketo"]
            }
        }
        pills = [
            MockPill("Software Engineering"),
            MockPill("Marketing & Communications"),
            MockPill("Human Resources"),
            MockPill("Finance & Accounting")
        ]
        best = agent._resolve_expertise_or_domain_pill("primary area of expertise", pills, marketing_profile)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "Marketing & Communications")

    def test_dynamic_domain_resolution_sales_profile(self):
        agent = QuestionnaireSectionAgent()
        sales_profile = {
            "candidate": {
                "total_experience_years": 7,
                "resume_headline": "Enterprise Sales Director | Account Executive | SaaS B2B",
                "profile_summary": "Exceeded quota closing high-value enterprise software deals."
            },
            "taxonomy_skills": {
                "Domain Skills": ["Enterprise Sales", "Strategic Negotiations", "Account Management"],
                "Technical Skills": ["Salesforce CRM", "Outreach", "Gong"]
            }
        }
        pills = [
            MockPill("Software Engineering"),
            MockPill("Product Design"),
            MockPill("Sales & Business Development"),
            MockPill("Operations")
        ]
        best = agent._resolve_expertise_or_domain_pill("primary area of expertise", pills, sales_profile)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "Sales & Business Development")

    def test_dynamic_tool_proficiency_salesforce(self):
        agent = QuestionnaireSectionAgent()
        profile = {
            "candidate": {"total_experience_years": 6},
            "ats_answers": {
                "skill_years_experience": {
                    "salesforce": 5.0
                }
            }
        }
        pills = [
            MockPill("Beginner"),
            MockPill("Intermediate"),
            MockPill("Advanced / Expert")
        ]
        best = agent._resolve_tool_proficiency_pill("What is your proficiency level in Salesforce?", pills, profile)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "Advanced / Expert")

    def test_dynamic_tool_proficiency_absent_skill(self):
        agent = QuestionnaireSectionAgent()
        profile = {
            "candidate": {"total_experience_years": 3},
            "taxonomy_skills": {"Domain Skills": ["Sales"]},
            "ats_answers": {"skill_years_experience": {}}
        }
        pills = [
            MockPill("Beginner"),
            MockPill("Intermediate"),
            MockPill("Advanced / Expert")
        ]
        best = agent._resolve_tool_proficiency_pill("What is your proficiency level in Kubernetes?", pills, profile)
        self.assertIsNotNone(best)
        self.assertEqual(best.inner_text(), "Beginner")

    def test_review_agent_demographics_dynamic_female_candidate(self):
        agent = ReviewSectionAgent()
        mock_page = MagicMock()
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first = mock_loc
        mock_loc.input_value.return_value = ""
        mock_loc.is_disabled.return_value = False
        mock_loc.all_text_contents.return_value = []
        mock_page.locator.return_value = mock_loc

        female_profile = {
            "candidate": {
                "full_name": "Sarah Connor",
                "linkedin_profile_url": "https://www.linkedin.com/in/sarahconnor"
            },
            "demographics": {
                "gender": "Female",
                "ethnicity": "Black or African American",
                "military_status": "Yes"
            }
        }

        with patch.object(agent, "_select_exact_dropdown") as mock_select:
            agent.heal(mock_page, female_profile)
            # Must call dropdown with candidate's actual values, NOT Asian / Male!
            calls = mock_select.call_args_list
            selected_items = [(call[0][1], call[0][2]) for call in calls]
            self.assertIn(("ETHNICITY", "Black or African American"), selected_items)
            self.assertIn(("GENDER", "Female"), selected_items)
            self.assertIn(("ATTRIBUTE16", "Yes"), selected_items)


if __name__ == "__main__":
    unittest.main()
