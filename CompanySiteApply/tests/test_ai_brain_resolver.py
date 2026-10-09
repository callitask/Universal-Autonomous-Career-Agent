import unittest
import json
import tempfile
from pathlib import Path
from CompanySiteApply.ai_brain_resolver import AIBrainResolver


class TestAIBrainResolver(unittest.TestCase):

    def setUp(self):
        # Sample candidate profile similar to Udaysagar Kandpal
        self.candidate_data = {
            "candidate": {
                "full_name": "Udaysagar Kandpal",
                "current_title": "Lead Software Engineer - Java Full Stack",
                "total_experience_years": 10.8,
                "country": "India",
                "location": "Bengaluru",
                "requires_sponsorship": False
            },
            "taxonomy_skills": {
                "Technical Skills": [
                    "Java", "Spring Boot", "Microservices", "SQL", "Oracle",
                    "Apache Kafka", "Hibernate", "RESTful APIs", "AWS"
                ],
                "Domain Skills": [
                    "Principal Technical Architecture", "Distributed Systems"
                ]
            },
            "ats_answers": {
                "programming languages": "JAVA, SQL",
                "proficiency with AWS": "Advanced / Expert",
                "Which primary technical area best describes your experience?": "Software Engineering"
            },
            "auto_learned_truths": {},
            "profile_content": {
                "key_skills": ["Java", "Spring Boot", "SQL", "Microservices"]
            }
        }
        self.brain = AIBrainResolver(self.candidate_data)

    def test_knowledge_index_extraction(self):
        idx = self.brain.knowledge_index
        self.assertEqual(idx["candidate_name"], "Udaysagar Kandpal")
        self.assertAlmostEqual(idx["total_experience_years"], 10.8)
        self.assertIn("Java", idx["programming_languages"])
        self.assertIn("SQL", idx["programming_languages"])
        self.assertEqual(idx["primary_domain"], "Software Engineering")
        self.assertEqual(idx["aws_proficiency"], "Advanced / Expert")
        self.assertEqual(idx["is_adult"], "Yes")
        self.assertEqual(idx["needs_sponsorship"], "No")
        self.assertEqual(idx["has_indian_passport"], "Yes")

    def test_resolve_programming_languages_multi_select(self):
        question = "Which of the following programming languages have you worked with?( Choose two that apply)"
        options = [
            "C++", "Cobol", "Metlab", ".NET", "PL/SQL", "R", "SAS", "Scala",
            "SQL", "Visual Basic", "Java", "Python",
            "My job does not require coding/I am not hands-on with coding",
            "Others/not listed above"
        ]
        res = self.brain.resolve_question(question, control_type="DROPDOWN_MULTI", options=options, req_count=2)
        ans = res["answer"]
        self.assertIsInstance(ans, list)
        self.assertEqual(len(ans), 2)
        self.assertIn("Java", ans)
        self.assertIn("SQL", ans)
        # Strict rule: Never select non-coding options
        self.assertNotIn("My job does not require coding/I am not hands-on with coding", ans)

    def test_resolve_experience_tier(self):
        question = "Please select the relevant years of work experience you have for this role:"
        options = [
            "Less than 2 years", "At Least 2 Years", "At Least 3 Years",
            "At Least 5 Years", "At Least 10 Years"
        ]
        res = self.brain.resolve_question(question, control_type="RADIO_PILL", options=options)
        self.assertEqual(res["answer"], "At Least 10 Years")

    def test_resolve_primary_domain(self):
        question = "Please select your primary area of expertise:"
        options = [
            "Software Engineering", "Applications Support/SRE/DevOps", "Business Analysis",
            "Cybersecurity", "Product Management", "Others/not listed above"
        ]
        res = self.brain.resolve_question(question, control_type="RADIO_PILL", options=options)
        self.assertEqual(res["answer"], "Software Engineering")

    def test_resolve_specialization(self):
        question = "If Software Engineering is your primary area of expertise, please choose your specific field of specialization?"
        options = [
            "UI/Frontend development (React, Angular, ReactNATIVE)",
            "C#/.NET",
            "Python (Django, Flask, Pandas, Numpy, FastAPI)",
            "Java Fullstack (Springboot, Hibernate, Microservices, React/Angular, Cloud)",
            "Java Backend (Springboot, Hibernate, Microservices)",
            "Others/not listed above"
        ]
        res = self.brain.resolve_question(question, control_type="RADIO_PILL", options=options)
        self.assertEqual(res["answer"], "Java Fullstack (Springboot, Hibernate, Microservices, React/Angular, Cloud)")

    def test_resolve_proficiency_aws(self):
        question = "How would you rate your proficiency with AWS?"
        options = ["Fundamental", "Intermediate", "Advanced / Expert"]
        res = self.brain.resolve_question(question, control_type="RADIO_PILL", options=options)
        self.assertEqual(res["answer"], "Advanced / Expert")

    def test_resolve_binary_questions(self):
        q1 = "Are you at least 18 years of age?"
        res1 = self.brain.resolve_question(q1, control_type="BINARY_PILL", options=["Yes", "No"])
        self.assertEqual(res1["answer"], "Yes")

        q2 = "Will you now or in the future require sponsorship for an employment-based visa status?"
        res2 = self.brain.resolve_question(q2, control_type="BINARY_PILL", options=["Yes", "No"])
        self.assertEqual(res2["answer"], "No")

        q3 = "Do you hold an Indian Passport?"
        res3 = self.brain.resolve_question(q3, control_type="BINARY_PILL", options=["Yes", "No"])
        self.assertEqual(res3["answer"], "Yes")

    def test_atomic_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "test_screening_answers.json"
            self.brain.output_json_path = custom_path
            res = self.brain.resolve_question("Are you at least 18 years of age?", "BINARY_PILL", ["Yes", "No"])
            self.assertTrue(custom_path.exists())
            loaded = json.loads(custom_path.read_text("utf-8"))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["answer"], "Yes")


if __name__ == "__main__":
    unittest.main()
