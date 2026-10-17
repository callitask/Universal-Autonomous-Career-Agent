import os
import unittest
import json
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from CompanySiteApply.autonomous_job_agent import AutonomousJobAgent
from CompanySiteApply.cognitive_job_matcher import CognitiveJobMatcher


class TestAutonomousJobAgent(unittest.TestCase):

    def setUp(self):
        # [CATCH-NEW-1] Sandbox isolation for requisition "3001" /
        # "Staff Software Engineer - Distributed Systems": stage_1 derives
        # slug "alex_rivera" from full_name "Alex Rivera" and stage_4 calls
        # resolve_recipient_header which persists screening_answers.json.
        # Without an isolated Operations root, resolve_profile_dir() falls
        # back to the repo tree and writes
        # F:\\JOB AI AGENT\\profiles\\alex_rivera\\screening_answers.json.
        self._tmp_ops = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_ops.cleanup)
        for _slug in ("alex_rivera", "alice_smith", "test_structured_profile_xyz", "candidate"):
            (Path(self._tmp_ops.name) / "profiles" / _slug).mkdir(parents=True, exist_ok=True)
        _patcher = unittest.mock.patch.dict(os.environ, {"JOB_AGENT_OPERATIONS": self._tmp_ops.name})
        _patcher.start()
        self.addCleanup(_patcher.stop)
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver as _R
        _R._instance = None
        self.tech_candidate = {
            "candidate": {
                "full_name": "Alex Rivera",
                "current_title": "Lead Software Engineer",
                "total_experience_years": 10.5,
                "location": "Bengaluru",
                "country": "India"
            },
            "target_jobs": {
                "keywords": ["Lead Software Engineer", "Principal Software Engineer", "Java Architect"],
                "locations": ["Bengaluru", "Bangalore"],
                "negative_keywords": ["Sales", "Marketing", "BPO"]
            },
            "taxonomy_skills": {
                "Technical Skills": ["Java", "Spring Boot", "Microservices", "Kafka", "AWS"]
            }
        }

        self.finance_candidate = {
            "candidate": {
                "full_name": "Alice Smith",
                "current_title": "Internal Audit Associate",
                "total_experience_years": 0.5,
                "location": "Delhi",
                "country": "India"
            },
            "target_jobs": {
                "keywords": ["Internal Audit Associate", "Financial Analyst", "Risk Advisory"],
                "locations": ["Delhi", "NCR"],
                "negative_keywords": ["Developer", "Coding", "Java"]
            },
            "taxonomy_skills": {
                "Domain Skills": ["Internal Controls", "Risk Assessment", "Statutory Audit"]
            }
        }

    def test_stage_1_comprehend_profile_zero_hardcoding(self):
        agent = AutonomousJobAgent()
        summary_tech = agent.stage_1_comprehend_profile(candidate_config=self.tech_candidate)
        self.assertEqual(summary_tech["candidate_name"], "Alex Rivera")
        self.assertEqual(summary_tech["experience_years"], 10.5)
        self.assertIn("Java", agent.matcher.candidate_skills)

        summary_fin = agent.stage_1_comprehend_profile(candidate_config=self.finance_candidate)
        self.assertEqual(summary_fin["candidate_name"], "Alice Smith")
        self.assertEqual(summary_fin["experience_years"], 0.5)
        self.assertIn("Internal Controls", agent.matcher.candidate_skills)
        self.assertNotIn("Java", agent.matcher.candidate_skills)

    def test_cognitive_job_matcher_scoring(self):
        matcher = CognitiveJobMatcher(self.tech_candidate)
        
        # High match job
        job_good = {
            "job_id": "1001",
            "title": "Lead Software Engineer - Java / Cloud",
            "location": "Bengaluru, India",
            "full_text": "We need a Lead Software Engineer with deep Java, Spring Boot, Microservices, and Kafka expertise."
        }
        res_good = matcher.evaluate_job(job_good)
        self.assertTrue(res_good["is_eligible"])
        self.assertGreaterEqual(res_good["score"], 70)
        self.assertIn("Java", res_good["matched_skills"])

        # Disqualified job by negative keyword
        job_neg = {
            "job_id": "1002",
            "title": "Sales Executive - Enterprise Software",
            "location": "Bengaluru, India",
            "full_text": "Looking for a Sales Executive to drive B2B customer acquisition."
        }
        res_neg = matcher.evaluate_job(job_neg)
        self.assertFalse(res_neg["is_eligible"])
        self.assertEqual(res_neg["status"], "NEGATIVE_KEYWORD_GATED")
        self.assertEqual(res_neg["score"], 0)

    def test_cognitive_job_matcher_country_gate(self):
        # 1. Candidate with allowed_countries: ["India"]
        cand_with_gate = dict(self.tech_candidate)
        cand_with_gate["target_jobs"] = dict(self.tech_candidate["target_jobs"])
        cand_with_gate["target_jobs"]["allowed_countries"] = ["India"]
        matcher_with_gate = CognitiveJobMatcher(cand_with_gate)

        # US req rejected at 0 with reason "out-of-country"
        job_us = {
            "job_id": "9001",
            "title": "Lead Software Engineer - Java",
            "location": "Jersey City, NJ, United States",
            "full_text": "Lead Software Engineer role with Java and AWS in Jersey City."
        }
        res_us = matcher_with_gate.evaluate_job(job_us)
        self.assertEqual(res_us["score"], 0)
        self.assertFalse(res_us["is_eligible"])
        self.assertEqual(res_us["status"], "DISQUALIFIED")
        self.assertIn("out-of-country", res_us["reasons"])

        # Indian req unaffected
        job_in = {
            "job_id": "9002",
            "title": "Lead Software Engineer - Java",
            "location": "Bengaluru, Karnataka, India",
            "full_text": "Lead Software Engineer role with Java, Spring Boot, Microservices, and Kafka in Bengaluru."
        }
        res_in = matcher_with_gate.evaluate_job(job_in)
        self.assertTrue(res_in["is_eligible"])
        self.assertGreaterEqual(res_in["score"], 70)
        self.assertNotIn("out-of-country", res_in["reasons"])

        # Absent-key neutral (backward compatible)
        cand_no_gate = dict(self.tech_candidate)
        matcher_no_gate = CognitiveJobMatcher(cand_no_gate)
        res_neutral = matcher_no_gate.evaluate_job(job_us)
        self.assertGreater(res_neutral["score"], 0)
        self.assertNotIn("out-of-country", res_neutral["reasons"])

    @patch("CompanySiteApply.autonomous_job_agent.JPMorganScraper.search_jobs", new_callable=AsyncMock)
    def test_stage_2_filter_already_applied(self, mock_search):
        agent = AutonomousJobAgent()
        agent.stage_1_comprehend_profile(candidate_config=self.tech_candidate)

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "processed_ledger.json"
            ledger_file.write_text(json.dumps({
                "jpmc:2002": {"title": "Prior Applied Job", "status": "applied"}
            }), encoding="utf-8")
            agent.ledger_path = ledger_file

            # Mock scraper returning 3 jobs: one clean, one DOM applied, one ledger applied
            mock_search.return_value = [
                {"job_id": "2001", "title": "Fresh Unapplied Role", "is_already_applied": False},
                {"job_id": "2002", "title": "Ledger Applied Role", "is_already_applied": False},
                {"job_id": "2003", "title": "DOM Applied Role", "is_already_applied": True}
            ]

            import asyncio
            mock_page = MagicMock()
            eligible = asyncio.run(agent.stage_2_search_jobs(mock_page))
            
            # Only 2001 should be eligible
            self.assertEqual(len(eligible), 1)
            self.assertEqual(eligible[0]["job_id"], "2001")

    @patch("core.generate_professional_cover_letter.sync_playwright")
    def test_stage_4_tailor_documents(self, mock_pw):
        agent = AutonomousJobAgent()
        agent.stage_1_comprehend_profile(candidate_config=self.tech_candidate)
        # Isolate from the live Operations profile.
        agent.candidate_data["profile"] = "test_structured_profile_xyz"
        agent.profile_slug = "test_structured_profile_xyz"

        target_job = {
            "job_id": "3001",
            "title": "Staff Software Engineer - Distributed Systems",
            "location": "Bengaluru, India",
            "details": {
                "company": "JPMorgan Chase & Co.",
                "full_text": "Staff Software Engineer needed for high-throughput distributed systems in Java."
            }
        }
        
        with patch("CompanySiteApply.autonomous_job_agent.generate_tailored_cover_letter") as mock_gen:
            import tempfile as _tf
            _tmpd = _tf.mkdtemp()
            _mock_pdf = Path(_tmpd, "Alice_Smith_Cover_Letter.pdf")
            _mock_pdf.write_bytes(b"%PDF-mock")
            mock_gen.side_effect = lambda cd, jd, td, pdf_filename=None: (
                Path(td, pdf_filename or "x.pdf").write_bytes(b"%PDF-mock"),
                str(Path(td) / (pdf_filename or "x.pdf")))[1]
            res = agent.stage_4_tailor_documents(target_job)
            self.assertTrue(res["success"])
            # Structured layout: FIXED name inside role folder, never mock path.
            self.assertIn("3001", res["cover_letter_pdf"])
            self.assertTrue(res["cover_letter_pdf"].endswith("Test_Structured_Profile_Xyz_Cover_Letter.pdf") or res["cover_letter_pdf"].endswith("Alice_Smith_Cover_Letter.pdf"))
            self.assertIn("JPMorgan_Chase_Co", res["applied_dir"])
            self.assertEqual(res["job_id"], "3001")
            # [CATCH-NEW-1] Sandbox proof: screening_answers.json must live
            # inside temp Operations under the ACTIVE profile folder
            # ("test_structured_profile_xyz" — Stage 1 now derives the slug
            # from the profile key, not full_name), never in the repo.
            _sandbox_answers = (Path(self._tmp_ops.name) / "profiles"
                                / "test_structured_profile_xyz" / "screening_answers.json")
            self.assertTrue(_sandbox_answers.is_file(),
                            f"sandbox screening_answers missing: {_sandbox_answers}")
            self.assertFalse((Path("profiles") / "alex_rivera").exists(),
                             "repo profiles/alex_rivera must never be created")
            # Cleanup isolated test profile (repo fallback, gitignored but keep tree clean).
            import shutil as _sh
            for _base in (Path("profiles") / "test_structured_profile_xyz",
                          Path("F:/Operations JOB AI AGENT/profiles/test_structured_profile_xyz")):
                try:
                    if _base.exists():
                        _sh.rmtree(_base, ignore_errors=True)
                except Exception:
                    pass

    def test_stage_6_human_gate_enforcement_and_ledger(self):
        agent = AutonomousJobAgent()
        agent.stage_1_comprehend_profile(candidate_config=self.tech_candidate)

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "processed_ledger.json"
            agent.ledger_path = ledger_file

            target_job = {
                "job_id": "4001",
                "title": "Principal Java Architect",
                "score": 88,
                "details": {"company": "JPMorgan Chase & Co."}
            }
            app_result = {"status": "SUCCESS", "current_section": 4}

            mock_page = AsyncMock()
            import asyncio
            report = asyncio.run(agent.stage_6_verify_and_gate(
                page=mock_page,
                target_job=target_job,
                app_result=app_result,
                screenshot_dir=Path(tmpdir)
            ))

            self.assertEqual(report["status"], "HALTED_AT_HUMAN_GATE")
            self.assertTrue(report["submit_ready"])
            self.assertIn("strictly before SUBMIT", report["message"])

            # Verify recorded in ledger
            self.assertTrue(ledger_file.exists())
            ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
            self.assertIn("jpmc:4001", ledger_data)
            self.assertEqual(ledger_data["jpmc:4001"]["status"], "READY_FOR_HUMAN_SUBMISSION")


if __name__ == "__main__":
    unittest.main()
