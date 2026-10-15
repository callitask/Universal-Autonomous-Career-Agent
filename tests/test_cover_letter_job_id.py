# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_COVER_LETTER_JOB_ID]
# Timestamp: 2026-10-13 00:00:00 +05:30
# Issue / Context: Requisition-tailored letter shipped "Re: Application for
#                  Lead Software Engineer (Job ID: )" — empty ID rendered
#                  because generation predated the preview-URL job_id fix and
#                  the template prints the slot unconditionally.
# Changes Made: Pure-helper tests (no browser/PDF): empty parens are
#               stripped; companion-txt verification gates regeneration.
# Preventative Notes: Never render "(Job ID: )" with a blank ID again.
# ==============================================================================

import os
import tempfile
import unittest

from core.generate_professional_cover_letter import (
    build_contact_parts,
    clean_empty_job_id_refs,
    verify_cover_letter_job_id,
    verify_cover_letter_job_title,
)


class TestCoverLetterJobId(unittest.TestCase):
    def test_empty_parens_stripped(self):
        self.assertEqual(
            clean_empty_job_id_refs("Re: Application for X (Job ID: )"),
            "Re: Application for X",
        )
        self.assertEqual(
            clean_empty_job_id_refs("Subject: Application for X (Requisition ID: )"),
            "Subject: Application for X",
        )
        self.assertEqual(
            clean_empty_job_id_refs("Re: Application for X (Job ID: 210780039)"),
            "Re: Application for X (Job ID: 210780039)",
        )

    def test_verify_companion_txt(self):
        with tempfile.TemporaryDirectory() as d:
            txt = os.path.join(d, "Cover_Letter.txt")
            with open(txt, "w", encoding="utf-8") as f:
                f.write("Re: Application for Lead Software Engineer (Job ID: 210780039)")
            self.assertTrue(verify_cover_letter_job_id(d, "210780039"))
            self.assertFalse(verify_cover_letter_job_id(d, "999999999"))

    def test_verify_missing_or_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(verify_cover_letter_job_id(d, "210780039"))
            self.assertFalse(verify_cover_letter_job_id(d, ""))

    def test_contact_parts_drop_blanks(self):
        self.assertEqual(
            build_contact_parts("", "+91-1", "", "link"),
            ["+91-1", "link"],
        )
        self.assertEqual(build_contact_parts("", "", ""), [])

    def test_verify_job_title(self):
        with tempfile.TemporaryDirectory() as d:
            txt = os.path.join(d, "Cover_Letter.txt")
            with open(txt, "w", encoding="utf-8") as f:
                f.write("Re: Application for Lead Software Engineer (Job ID: 210788242)")
            self.assertTrue(verify_cover_letter_job_title(d, "Lead Software Engineer"))
            self.assertFalse(verify_cover_letter_job_title(d, "Work Summary"))
            self.assertFalse(verify_cover_letter_job_title(d, ""))

    def test_rejects_placeholder_company(self):
        # Incident 210791831: "Hiring Organization" rendered as recipient
        # block and shipped. Missing/placeholder company must refuse loudly.
        from core.generate_professional_cover_letter import generate_tailored_cover_letter
        cand = {"candidate": {"full_name": "Udaysagar Kandpal"}}
        with tempfile.TemporaryDirectory() as d:
            for bad in ("", "Hiring Organization", "company", "Unknown"):
                with self.assertRaises(ValueError, msg=f"company={bad!r} must refuse"):
                    generate_tailored_cover_letter(
                        cand,
                        {"title": "Sr Manager of Software Engineering",
                         "job_id": "210791831", "company": bad},
                        d)

    def test_recipient_uses_job_location_not_candidate(self):
        # Recipient address block must carry the requisition location
        # (Mumbai), never the candidate home address (Bengaluru).
        from unittest.mock import patch
        from core.generate_professional_cover_letter import generate_tailored_cover_letter
        cand = {"candidate": {"full_name": "Udaysagar Kandpal",
                              "location": "Bengaluru, Karnataka, India"}}
        jd = {"title": "Sr Manager of Software Engineering - Java, AWS, React",
              "job_id": "210791831",
              "company": "JPMorgan Chase & Co.",
              "location": "Mumbai, Maharashtra, India"}
        with tempfile.TemporaryDirectory() as d:
            with patch("core.generate_professional_cover_letter.generate_cover_letter_pdf") as mock_pdf:
                mock_pdf.return_value = os.path.join(d, "x.pdf")
                generate_tailored_cover_letter(cand, jd, d)
                kwargs = mock_pdf.call_args.kwargs
                self.assertEqual(kwargs["organization"], "JPMorgan Chase & Co.")
                self.assertEqual(kwargs["org_location"], "Mumbai, Maharashtra, India")
                self.assertIn("JPMorgan Chase & Co. Engineering Team",
                              kwargs["hiring_team"])

if __name__ == "__main__":
    unittest.main()
