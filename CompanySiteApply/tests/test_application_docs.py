# AI CONTEXT & CHANGE LOG
# [ENTRY #001] Structured layout contract tests — fixed names, role folders.

import unittest
from pathlib import Path
import tempfile

from CompanySiteApply.utils.application_docs import (
    application_doc_paths,
    copy_into_role,
    profile_stem,
    resolve_company_name,
    resolve_job_location,
)


class TestStructuredLayout(unittest.TestCase):
    def test_stem_title_case(self):
        self.assertEqual(profile_stem({"candidate": {"full_name": "Alex Rivera"}}, "udaysagar_kandpal"),
                         "Udaysagar_Kandpal")
        self.assertEqual(profile_stem({}, "udaysagar_kandpal"), "Udaysagar_Kandpal")
        self.assertEqual(profile_stem({"profile": "new_user_test"}, "new_user_test"),
                         "New_User_Test")

    def test_slug_wins_over_full_name(self):
        # Gap 2: folder identity is canonical — a differing full_name must
        # not fork a second stem inside one role folder.
        self.assertEqual(
            profile_stem({"profile": "someone",
                          "candidate": {"full_name": "Name Nobody"}},
                         "someone"),
            "Someone")

    def test_company_never_literal(self):
        self.assertNotEqual(resolve_company_name({"details": {"company": ""}}, {}, ""), "company")
        self.assertEqual(resolve_company_name({"details": {"company": ""}}, {}, "https://jpmc.fa.oraclecloud.com/x"),
                         "JPMorgan Chase & Co.")
        self.assertEqual(resolve_company_name({"details": {"company": "JPMorgan Chase & Co."}}, {}, ""),
                         "JPMorgan Chase & Co.")

    def test_unknown_company_returns_empty_never_jpmorgan(self):
        # Follow-up: no blind JPMorgan default — unknown portals must
        # defer loudly instead of shipping a wrong-company letter.
        self.assertEqual(
            resolve_company_name({"details": {"company": ""}}, {}, ""), "")
        self.assertEqual(
            resolve_company_name({"details": {"company": "company"}}, {}, ""), "")

    def test_scraper_short_name_canonicalized(self):
        # config holds "JPMorgan Chase"; letter + folder use formal "& Co.".
        self.assertEqual(
            resolve_company_name({"details": {"company": "JPMorgan Chase"}}, {}, ""),
            "JPMorgan Chase & Co.")
        self.assertEqual(
            resolve_company_name({}, {}, "", default_company="JPMorgan Chase"),
            "JPMorgan Chase & Co.")

    def test_job_location_prefers_dom_over_candidate(self):
        from unittest.mock import MagicMock
        page = MagicMock()
        page.evaluate.return_value = "Mumbai, Maharashtra, India"
        cand = {"candidate": {"location": "Bengaluru, Karnataka, India"}}
        self.assertEqual(resolve_job_location(page, cand),
                         "Mumbai, Maharashtra, India")
        page2 = MagicMock()
        page2.evaluate.return_value = ""
        self.assertEqual(resolve_job_location(page2, cand), "")

    def test_role_paths_fixed_names(self):
        with tempfile.TemporaryDirectory() as d:
            import os
            os.environ["JOB_AGENT_OPERATIONS"] = d
            try:
                from importlib import reload
                import CompanySiteApply.utils.runtime_paths as rp
                reload(rp)
                import CompanySiteApply.utils.application_docs as ad
                reload(ad)
                paths = ad.application_doc_paths("udaysagar_kandpal", "JPMorgan Chase & Co.",
                                                 "Sr Manager of Software Engineering - Java, AWS, React",
                                                 "210791831",
                                                 {"candidate": {"full_name": "Alex Rivera"}})
                self.assertIn("210791831", str(paths["role_dir"]))
                self.assertTrue(paths["cover_pdf"].name == "Udaysagar_Kandpal_Cover_Letter.pdf")
                self.assertTrue(paths["resume_pdf"].name == "Udaysagar_Kandpal_Resume.pdf")
                self.assertIn("JPMorgan_Chase_Co", str(paths["role_dir"]))
            finally:
                os.environ.pop("JOB_AGENT_OPERATIONS", None)
                reload(rp)

    def test_mirror_flat_and_subfolders(self):
        with tempfile.TemporaryDirectory() as d:
            role = Path(d) / "role_123"
            src_r = Path(d) / "master_resume.pdf"
            src_c = Path(d) / "gen_cover.pdf"
            src_r.write_bytes(b"R")
            src_c.write_bytes(b"C")
            out = copy_into_role(role, "Udaysagar_Kandpal", str(src_r), str(src_c))
            self.assertTrue(Path(out["resume_pdf"]).is_file())
            self.assertTrue(Path(out["cover_pdf"]).is_file())
            self.assertTrue((role / "resume" / "Udaysagar_Kandpal_Resume.pdf").is_file())
            self.assertTrue((role / "cover_letters" / "Udaysagar_Kandpal_Cover_Letter.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
