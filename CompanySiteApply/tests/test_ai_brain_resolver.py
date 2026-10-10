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
            fresh_brain = AIBrainResolver(self.candidate_data)
            fresh_brain.output_json_path = custom_path
            fresh_brain.history = []
            res = fresh_brain.resolve_question("Are you at least 18 years of age?", "BINARY_PILL", ["Yes", "No"])
            self.assertTrue(custom_path.exists())
            loaded = json.loads(custom_path.read_text("utf-8"))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["answer"], "Yes")

    def test_non_technical_candidate_resolution(self):
        # Sample non-tech profile: Anshika Garg (Internal Audit)
        audit_data = {
            "candidate": {
                "full_name": "Anshika Garg",
                "current_title": "Internal Audit Associate",
                "total_experience_years": 0.5,
                "country": "India",
                "location": "Delhi",
                "requires_sponsorship": False
            },
            "target_jobs": {
                "keywords": ["Internal Audit Associate", "Financial Analyst", "Risk Advisory"],
                "department": "Internal Audit & Risk"
            },
            "taxonomy_skills": {
                "Domain Skills": ["Internal Controls", "Risk Assessment", "Statutory Audit", "Financial Analysis"]
            },
            "ats_answers": {},
            "auto_learned_truths": {},
            "profile_content": {
                "key_skills": ["Internal Controls", "Risk Assessment", "Financial Modelling"]
            }
        }
        audit_brain = AIBrainResolver(audit_data)
        idx = audit_brain.knowledge_index
        self.assertEqual(idx["candidate_name"], "Anshika Garg")
        self.assertEqual(idx["primary_domain"], "Internal Audit & Risk")
        self.assertFalse(idx["is_tech_candidate"])
        self.assertEqual(idx["aws_proficiency"], "None")

        # Non-tech candidate answering programming languages question
        q = "Which of the following programming languages have you worked with?( Choose two that apply)"
        options = [
            "C++", ".NET", "Java", "Python",
            "My job does not require coding/I am not hands-on with coding",
            "Others/not listed above"
        ]
        res = audit_brain.resolve_question(q, control_type="DROPDOWN_MULTI", options=options, req_count=2)
        ans = res["answer"]
        self.assertIn("My job does not require coding/I am not hands-on with coding", ans)


if __name__ == "__main__":
    unittest.main()
