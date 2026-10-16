import os
import unittest
import json
import tempfile
import unittest.mock
from pathlib import Path
from CompanySiteApply.ai_brain_resolver import AIBrainResolver


class TestAIBrainResolver(unittest.TestCase):

    def setUp(self):
        # [CATCH-NEW-1] Sandbox isolation: AIBrainResolver derives slug
        # "alex_rivera" from full_name "Alex Rivera" (and "alice_smith"
        # from the audit fixture). Without an isolated Operations root,
        # resolve_profile_dir()/profiles_root() fall back to the repo tree
        # and persist screening_answers.json into profiles/alex_rivera/.
        self._tmp_ops = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_ops.cleanup)
        for _slug in ("alex_rivera", "alice_smith", "candidate"):
            (Path(self._tmp_ops.name) / "profiles" / _slug).mkdir(parents=True, exist_ok=True)
        _patcher = unittest.mock.patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": self._tmp_ops.name})
        _patcher.start()
        self.addCleanup(_patcher.stop)
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver as _R
        _R._instance = None
        # Sample synthetic tech candidate profile
        self.candidate_data = {
            "candidate": {
                "full_name": "Alex Rivera",
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
        # Enforce sandbox: brain must resolve inside temp ops, never repo.
        _expected = Path(self._tmp_ops.name) / "profiles" / "alex_rivera" / "screening_answers.json"
        if Path(str(self.brain.output_json_path)) != _expected:
            # If resolver picked inspections fallback (no company_site_apply
            # subdir), redirect into the pre-created sandbox profile.
            if "alex_rivera" not in str(self.brain.output_json_path):
                self.brain.output_json_path = _expected

    def test_knowledge_index_extraction(self):
        idx = self.brain.knowledge_index
        self.assertEqual(idx["candidate_name"], "Alex Rivera")
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
        # Sample non-tech profile: Alice Smith (Internal Audit)
        audit_data = {
            "candidate": {
                "full_name": "Alice Smith",
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
        self.assertEqual(idx["candidate_name"], "Alice Smith")
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


class TestRecipientHeaderArbitration(unittest.TestCase):
    """AG Brain owns the cover-letter recipient block (incident 210791831)."""

    def setUp(self):
        # [CATCH-NEW-1] Isolate Operations so resolve_recipient_header for
        # requisition "3001"/"Staff Software Engineer - Distributed Systems"
        # (and these 210791831 fixtures) persists inside temp ops, never
        # into F:\\JOB AI AGENT\\profiles\\alex_rivera\\screening_answers.json.
        self._tmp_ops = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_ops.cleanup)
        (Path(self._tmp_ops.name) / "profiles" / "alex_rivera").mkdir(parents=True, exist_ok=True)
        (Path(self._tmp_ops.name) / "profiles" / "candidate").mkdir(parents=True, exist_ok=True)
        _patcher = unittest.mock.patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": self._tmp_ops.name})
        _patcher.start()
        self.addCleanup(_patcher.stop)
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver as _R
        _R._instance = None

    def _brain(self):
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        AIBrainResolver._instance = None
        b = AIBrainResolver.get_instance(
            {"candidate": {"full_name": "Alex Rivera"}})
        # Sandbox proof: force output inside temp Operations profile dir.
        _sandbox = Path(self._tmp_ops.name) / "profiles" / "alex_rivera" / "screening_answers.json"
        b.output_json_path = _sandbox
        b.history = []
        try:
            if _sandbox.exists():
                _sandbox.unlink()
        except Exception:
            pass
        return b

    def test_stamped_company_wins_with_location(self):
        v = self._brain().resolve_recipient_header({
            "job_id": "210791831",
            "job_title": "Sr Manager of Software Engineering - Java, AWS, React",
            "stamped_company": "JPMorgan Chase",
            "page_url": "https://jpmc.fa.oraclecloud.com/.../job/210791831",
            "portal_default_company": "JPMorgan Chase",
            "candidate_company_hints": [],
            "dom_location": "",
            "requisition_location": "Mumbai, Maharashtra, India",
            "explicit_team": "",
            "workspace_provisioned": True,
        })
        self.assertTrue(v["success"])
        self.assertEqual(v["company"], "JPMorgan Chase & Co.")
        self.assertEqual(v["location"], "Mumbai, Maharashtra, India")
        self.assertEqual(v["hiring_team"], "JPMorgan Chase & Co. Engineering Team")

    def test_unknown_company_refuses(self):
        v = self._brain().resolve_recipient_header({
            "job_id": "1", "job_title": "X", "stamped_company": "",
            "page_url": "", "portal_default_company": "",
            "candidate_company_hints": [], "dom_location": "",
            "requisition_location": "", "explicit_team": "",
            "workspace_provisioned": False,
        })
        self.assertFalse(v["success"])
        self.assertEqual(v["company"], "")

    def test_conflicting_evidence_refuses(self):
        v = self._brain().resolve_recipient_header({
            "job_id": "1", "job_title": "X",
            "stamped_company": "Acme Corp",
            "page_url": "https://jpmc.fa.oraclecloud.com/...",
            "portal_default_company": "", "candidate_company_hints": [],
            "dom_location": "", "requisition_location": "",
            "explicit_team": "", "workspace_provisioned": False,
        })
        self.assertFalse(v["success"])
        self.assertIn("conflict", v["error"])

    def test_never_invents_person_name(self):
        v = self._brain().resolve_recipient_header({
            "job_id": "1", "job_title": "Engineer",
            "stamped_company": "Acme Corp", "page_url": "",
            "portal_default_company": "", "candidate_company_hints": [],
            "dom_location": "Bengaluru", "requisition_location": "",
            "explicit_team": "", "workspace_provisioned": False,
        })
        self.assertTrue(v["success"])
        self.assertNotIn("Hiring Organization", v["hiring_team"])
        self.assertIn("Acme Corp", v["hiring_team"])


class TestScreeningLedgerDedup(unittest.TestCase):
    """Phase 4: noise filtering, in-place dedup, role answers.json mirror."""

    def setUp(self):
        self._tmp_ops = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_ops.cleanup)
        (Path(self._tmp_ops.name) / "profiles" / "synth_qa").mkdir(parents=True, exist_ok=True)
        _patcher = unittest.mock.patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": self._tmp_ops.name})
        _patcher.start()
        self.addCleanup(_patcher.stop)
        AIBrainResolver._instance = None
        self.candidate_data = {
            "profile": "synth_qa",
            "job_id": "3001",
            "candidate": {"full_name": "Synth Qa", "country": "India",
                          "total_experience_years": 10},
            "ats_answers": {}, "taxonomy_skills": {},
        }
        self.job_context = {"job_id": "3001", "job_title": "Engineer",
                            "company": "Acme Corp"}
        self.brain = AIBrainResolver(self.candidate_data, dict(self.job_context))
        self.brain.output_json_path = (
            Path(self._tmp_ops.name) / "profiles" / "synth_qa" / "screening_answers.json")
        self.brain.history = []

    def _rows(self):
        return json.loads(self.brain.output_json_path.read_text(encoding="utf-8"))

    def test_noise_rows_not_persisted_but_returned(self):
        rec = self.brain.resolve_question(
            "No Prior Experience", "RADIO_CHIP",
            ["No Prior Experience", "At least 1 year"])
        self.assertEqual(rec.get("source"), "REFUSED_SELF_ECHO")
        self.assertIsNone(rec.get("answer"))
        rec2 = self.brain.resolve_question(
            "Zqx jumbled wobble?", "RADIO_CHIP", ["Alpha", "Beta"])
        self.assertEqual(rec2.get("answer"), "")
        self.assertFalse(self.brain.output_json_path.exists())

    def test_repeat_updates_in_place(self):
        self.brain.resolve_question(
            "Are you authorized to work?", "BINARY_PILL", ["Yes", "No"])
        self.brain.resolve_question(
            "  are   you AUTHORIZED to work?  ", "BINARY_PILL", ["Yes", "No"])
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["job_id"], "3001")
        self.assertEqual(rows[0]["company"], "Acme Corp")

    def test_load_compacts_legacy_noise_and_dupes(self):
        legacy = [
            {"question": "No Prior Experience", "control_type": "RADIO_CHIP",
             "options": ["No Prior Experience", "At least 1 year"],
             "source": "REFUSED_SELF_ECHO", "answer": None},
            {"question": "Are you authorized?", "answer": "Yes",
             "job_id": "3001", "source": "OLD", "control_type": "BINARY_PILL",
             "options": ["Yes", "No"]},
            {"questionorig": 0, "question": "are you authorized?", "answer": "Yes",
             "job_id": "3001", "source": "OLD2", "control_type": "BINARY_PILL",
             "options": ["Yes", "No"]},
        ]
        self.brain.output_json_path.write_text(json.dumps(legacy), encoding="utf-8")
        AIBrainResolver._instance = None
        fresh = AIBrainResolver(self.candidate_data, dict(self.job_context))
        fresh.output_json_path = self.brain.output_json_path
        fresh.history = fresh._load_existing_answers()
        self.assertEqual(len(fresh.history), 1)
        self.assertEqual(fresh.history[0]["source"], "OLD2")

    def test_role_answers_json_mirror(self):
        from CompanySiteApply.utils.application_docs import application_dir
        role_dir = application_dir("synth_qa", "Acme Corp", "Engineer", "3001")
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "answers.json").write_text(
            json.dumps({"status": "OPEN", "screening_qa": []}), encoding="utf-8")
        self.brain.resolve_question(
            "Are you authorized to work?", "BINARY_PILL", ["Yes", "No"])
        data = json.loads((role_dir / "answers.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "OPEN")
        self.assertEqual(data["job_id"], "3001")
        self.assertEqual(len(data["screening_qa"]), 1)
        self.assertEqual(data["screening_qa"][0]["answer"], "Yes")
        # Repeat dedups the role list too.
        self.brain.resolve_question(
            "Are you authorized to work?", "BINARY_PILL", ["Yes", "No"])
        data = json.loads((role_dir / "answers.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["screening_qa"]), 1)

    def test_recipient_records_skip_mirror(self):
        from CompanySiteApply.utils.application_docs import application_dir
        role_dir = application_dir("synth_qa", "Acme Corp", "Engineer", "3001")
        role_dir.mkdir(parents=True, exist_ok=True)
        v = self.brain.resolve_recipient_header({
            "job_id": "3001", "job_title": "Engineer",
            "stamped_company": "Acme Corp", "page_url": "",
            "portal_default_company": "", "candidate_company_hints": [],
            "dom_location": "Bengaluru", "requisition_location": "",
            "explicit_team": "", "workspace_provisioned": False})
        self.assertTrue(v["success"])
        self.assertFalse((role_dir / "answers.json").exists())

    def test_auto_learned_truths_never_written(self):
        before = json.dumps(self.candidate_data, sort_keys=True)
        self.brain.resolve_question(
            "Are you authorized to work?", "BINARY_PILL", ["Yes", "No"])
        self.brain.resolve_recipient_header({
            "job_id": "3001", "job_title": "Engineer",
            "stamped_company": "Acme Corp", "page_url": "",
            "portal_default_company": "", "candidate_company_hints": [],
            "dom_location": "", "requisition_location": "",
            "explicit_team": "", "workspace_provisioned": False})
        self.assertEqual(json.dumps(self.candidate_data, sort_keys=True), before)
        self.assertEqual(self.candidate_data.get("auto_learned_truths", "absent"), "absent")


if __name__ == "__main__":
    unittest.main()
