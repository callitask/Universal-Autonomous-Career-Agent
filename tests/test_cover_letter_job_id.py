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
#
# [ENTRY #002]
# Term: [TEST_FIXTURE_DEPII]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Test fixtures used the live candidate's real full_name,
#                  which Guardrail P1 flags when purity runs against the live
#                  profile (tests/*.py are now in scan scope).
# Changes Made: Synthetic fixture identity ("Alex Rivera") everywhere.
# Rationale: Tests must pass purity against default_user AND live profiles.
# Preventative Notes: Never use real candidate names in test fixtures.
#
# [ENTRY #003]
# Term: [BASE_MD_PARSER_TESTS]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Phase 3B added _parse_base_cover_letter_md(); parser
#                  token/paragraph/bullet behavior needed regression pins.
# Changes Made: TestBaseCoverLetterParser (tokens, empty-ID strip, ".."
#               dedup, paragraph/bullet extraction, missing-file guard).
# Rationale: Parser output feeds PDF kwargs; pin it with synthetic data.
# Preventative Notes: Never use real candidate names in test fixtures.
#
# [ENTRY #004]
# Term: [F_CL_01_FALLBACK_OVERWRITE_REGRESSION]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: The generic fallback block in generate_tailored_cover_letter()
#                  sat at function scope, so it overwrote company BASE.md
#                  prose and bullets with hardcoded boilerplate.
# Changes Made: Two pins — BASE.md prose+bullets survive end-to-end (no
#               boilerplate in kwargs), and the no-BASE fallback still emits
#               4 generic bullets.
# Rationale: Both branches must be independently verifiable.
# Preventative Notes: Never assert only one branch; never let fallback run at
#                     function scope.
# ==============================================================================

import json
import os
import tempfile
import unittest

from core.generate_professional_cover_letter import (
    build_contact_parts,
    clean_empty_job_id_refs,
    verify_cover_letter_job_id,
    verify_cover_letter_job_title,
    _md_bold_to_html,
    _strip_md_bold,
)
from core.generate_factual_tailored import ResumeTailorEngine


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
        cand = {"candidate": {"full_name": "Alex Rivera"}}
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
        cand = {"candidate": {"full_name": "Alex Rivera",
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

class TestBaseCoverLetterParser(unittest.TestCase):
    """Phase 3B: BASE.md token substitution, parsing, and hygiene."""

    def _base_md(self, d, body):
        p = os.path.join(d, "BASE.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        return p

    def _ctx(self, job_id="210791831"):
        return {"date_str": "October 17, 2026", "organization": "JPMorgan Chase & Co.",
                "org_location": "Mumbai, Maharashtra, India",
                "hiring_team": "JPMorgan Chase & Co. Engineering Team",
                "job_title": "Sr Manager of Software Engineering",
                "job_id": job_id, "candidate_name": "Alex Rivera"}

    def _fixture(self):
        return (
            "Dear Hiring Team,\n"
            "\n"
            "I am Alex Rivera applying for [Job Title] (Job ID: [JOB_ID]) at "
            "[Company Name] in [City, State, Country] on [Date].\n"
            "\n"
            "My transition to product engineering drives me.\n"
            "\n"
            "- **Distributed Systems:** Led high-throughput services.\n"
            "- **Cloud Platforms:** Shipped Kubernetes workloads.\n"
            "\n"
            "I welcome the chance to contribute to [Company Name]. Thank you.\n"
            "\n"
            "Sincerely,\n"
            "Alex Rivera\n"
        )

    def test_substitutes_all_tokens(self):
        from core.generate_professional_cover_letter import _parse_base_cover_letter_md
        with tempfile.TemporaryDirectory() as d:
            p = self._base_md(d, self._fixture())
            out = _parse_base_cover_letter_md(p, self._ctx())
            self.assertIn("Sr Manager of Software Engineering", out["opening"][0])
            self.assertIn("JPMorgan Chase & Co.", out["opening"][0])
            self.assertIn("Mumbai, Maharashtra, India", out["opening"][0])
            self.assertIn("October 17, 2026", out["opening"][0])
            self.assertIn("(Job ID: 210791831)", out["opening"][0])
            for token in ("[Job Title]", "[JOB_ID]", "[Company Name]",
                          "[City, State, Country]", "[Date]"):
                self.assertNotIn(token, out["rendered_md"])

    def test_strips_empty_job_id_parens(self):
        from core.generate_professional_cover_letter import _parse_base_cover_letter_md
        with tempfile.TemporaryDirectory() as d:
            p = self._base_md(d, self._fixture())
            out = _parse_base_cover_letter_md(p, self._ctx(job_id=""))
            self.assertNotIn("(Job ID: )", out["rendered_md"])
            self.assertNotIn("(Job ID:)", out["opening"][0])

    def test_dedupes_double_periods(self):
        from core.generate_professional_cover_letter import _parse_base_cover_letter_md
        with tempfile.TemporaryDirectory() as d:
            p = self._base_md(d, "Dear Hiring Team,\n\nWelcome to [Company Name].\n\nSincerely,\nAlex Rivera\n")
            out = _parse_base_cover_letter_md(p, self._ctx())
            self.assertNotIn("..", out["rendered_md"])
            self.assertIn("JPMorgan Chase & Co.", out["rendered_md"])

    def test_extracts_paragraphs_and_bullets(self):
        from core.generate_professional_cover_letter import _parse_base_cover_letter_md
        with tempfile.TemporaryDirectory() as d:
            p = self._base_md(d, self._fixture())
            out = _parse_base_cover_letter_md(p, self._ctx())
            self.assertEqual(len(out["opening"]), 2)
            self.assertEqual(len(out["bullets"]), 2)
            self.assertEqual(out["bullets"][0][0], "Distributed Systems")
            self.assertIn("high-throughput", out["bullets"][0][1])
            self.assertEqual(len(out["closing"]), 1)
            for title, body in out["bullets"]:
                self.assertNotIn("**", title + body)

    def test_missing_file_returns_empty(self):
        from core.generate_professional_cover_letter import _parse_base_cover_letter_md
        out = _parse_base_cover_letter_md("/nonexistent_dir_xyz/BASE.md", self._ctx())
        self.assertEqual(out, {"opening": [], "bullets": [], "closing": [], "rendered_md": ""})

    def test_base_letter_survives_no_fallback_interference(self):
        # [F-CL-01] regression: the generic fallback block once ran at
        # function scope and overwrote BASE.md prose + bullets, shipping
        # boilerplate ("Distributed Event-Driven Architecture") instead of
        # the company-framed letter.
        from pathlib import Path as _P
        from unittest.mock import patch
        from core.generate_professional_cover_letter import generate_tailored_cover_letter
        with tempfile.TemporaryDirectory() as d:
            prof = _P(d) / "synth_cov"
            (prof / "company_site_apply" / "JPMorganChase" / "cover_letters").mkdir(parents=True)
            (prof / "company_site_apply" / "JPMorganChase" / "cover_letters" / "BASE.md").write_text(
                "Dear Hiring Team,\n\n"
                "First BASE paragraph.\n\n"
                "Second BASE paragraph.\n\n"
                "- **BASE Bullet One:** Real tailored content.\n"
                "- **BASE Bullet Two:** More real tailored content.\n\n"
                "Closing BASE paragraph.\n\n"
                "Sincerely,\nAlex Rivera\n", encoding="utf-8")
            cand = {"profile_dir": str(prof),
                    "candidate": {"full_name": "Alex Rivera", "total_experience_years": 10}}
            jd = {"title": "Staff Engineer", "job_id": "3001",
                  "company": "JPMorgan Chase & Co.", "location": "Bengaluru, India"}
            with patch("core.generate_professional_cover_letter.generate_cover_letter_pdf") as mock_pdf:
                mock_pdf.return_value = _P(d) / "x.pdf"
                generate_tailored_cover_letter(cand, jd, d)
                kwargs = mock_pdf.call_args.kwargs
            self.assertEqual([b["title"] for b in kwargs["bullets"]],
                             ["BASE Bullet One", "BASE Bullet Two"])
            self.assertIn("First BASE paragraph", kwargs["opening_p"])
            self.assertIn("Second BASE paragraph", kwargs["transition_p"])
            self.assertIn("Closing BASE paragraph", kwargs["synthesis_p"])
            blob = json.dumps(kwargs)
            self.assertNotIn("Distributed Event-Driven Architecture", blob)
            self.assertNotIn("Cloud-Native Resilience", blob)

    def test_no_base_letter_still_falls_back_to_generic(self):
        # Guard both ways: no BASE.md must keep the deterministic fallback.
        from unittest.mock import patch
        from core.generate_professional_cover_letter import generate_tailored_cover_letter
        with tempfile.TemporaryDirectory() as d:
            cand = {"candidate": {"full_name": "Alex Rivera", "total_experience_years": 10}}
            jd = {"title": "Staff Engineer", "job_id": "3001",
                  "company": "JPMorgan Chase & Co.", "location": "Bengaluru, India"}
            with patch("core.generate_professional_cover_letter.generate_cover_letter_pdf") as mock_pdf:
                mock_pdf.return_value = os.path.join(d, "x.pdf")
                generate_tailored_cover_letter(cand, jd, d)
                kwargs = mock_pdf.call_args.kwargs
            self.assertEqual(len(kwargs["bullets"]), 4)
            self.assertIn("Distributed Event-Driven Architecture",
                          kwargs["bullets"][0]["title"])

    def test_multiparagraph_transition_splits_html_paragraphs(self):
        # Phase 4 Stage 1: \n\n-separated prose must render as separate <p>
        # tags in HTML/PDF while staying \n\n-separated in Cover_Letter.txt.
        from unittest.mock import MagicMock, patch
        from core.generate_professional_cover_letter import generate_cover_letter_pdf
        with tempfile.TemporaryDirectory() as d:
            mock_page = MagicMock()
            mock_browser = MagicMock()
            mock_browser.new_page.return_value = mock_page
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_browser
            with patch("core.generate_professional_cover_letter.sync_playwright",
                       return_value=mock_ctx):
                generate_cover_letter_pdf(
                    target_dir=d, candidate_name="Alex Rivera",
                    location="Bengaluru", phone="+91-1", email="a@b.c",
                    linkedin="link", date_str="October 17, 2026",
                    hiring_team="Team", organization="Acme Corp",
                    org_location="Mumbai", job_title="Engineer", job_id="3001",
                    opening_p="Opening paragraph.",
                    transition_p="Transition rationale.\n\nLead-in to bullets.",
                    bullets=[{"title": "T", "body": "B"}],
                    synthesis_p="Synthesis.", closing_p="Closing.")
            html = open(os.path.join(d, "Cover_Letter.html"), encoding="utf-8").read()
            self.assertIn("<p>Transition rationale.</p>", html)
            self.assertIn("<p>Lead-in to bullets.</p>", html)
            txt = open(os.path.join(d, "Cover_Letter.txt"), encoding="utf-8").read()
            self.assertIn("Transition rationale.\n\nLead-in to bullets.", txt)


class TestMarkdownBoldRendering(unittest.TestCase):
    """[F-CL-02] Markdown "**bold**" must never reach the employer PDF."""

    def test_balanced_pairs_become_strong(self):
        self.assertEqual(
            _md_bold_to_html("Apply for **Lead Software Engineer** at **Acme**."),
            "Apply for <strong>Lead Software Engineer</strong> at <strong>Acme</strong>.")

    def test_adjacent_pairs_each_converted(self):
        self.assertEqual(_md_bold_to_html("**a** and **b**"),
                         "<strong>a</strong> and <strong>b</strong>")

    def test_unbalanced_marker_left_intact(self):
        """An odd trailing ** must not swallow the rest of the letter."""
        src = "dangling ** marker then more text"
        self.assertEqual(_md_bold_to_html(src), src)
        self.assertEqual(_strip_md_bold(src), src)

    def test_plain_text_unchanged(self):
        self.assertEqual(_md_bold_to_html("no bold here"), "no bold here")
        self.assertEqual(_strip_md_bold("no bold here"), "no bold here")

    def test_txt_strips_markers_but_keeps_text(self):
        self.assertEqual(_strip_md_bold("**JPMorgan Chase & Co.** team"),
                         "JPMorgan Chase & Co. team")


class TestZeroOmissionSectionRestore(unittest.TestCase):
    """[F-RES-01/02] Bullets restore into their SOURCE section, not the tail."""

    TEMPLATE = (
        "# NAME\n\n## SKILLS\n\n**Alpha Domain:** thing one\n\n"
        "## EXPERIENCE\n\n- Alpha role bullet\n- Beta role bullet\n\n"
        "## HONORS & AWARDS\n\n- Award one\n"
    )
    TAILORED = (
        "# NAME\n\n## SKILLS\n\n**Alpha Domain:** thing one\n\n"
        "## EXPERIENCE\n\n- Alpha role bullet\n\n"
        "## HONORS & AWARDS\n\n- Award one\n"
    )

    def setUp(self):
        self.engine = ResumeTailorEngine.__new__(ResumeTailorEngine)
        self.engine._reframed_any = False

    def test_bold_prose_is_not_a_bullet(self):
        """Regression: '**Label:** ...' skill blocks were counted as bullets."""
        self.assertNotIn("**Alpha Domain:** thing one",
                         ResumeTailorEngine._bullets_of(self.TEMPLATE))
        self.assertIn("- Beta role bullet",
                      ResumeTailorEngine._bullets_of(self.TEMPLATE))

    def test_asterisk_bullet_still_counts(self):
        self.assertIn("* star bullet", ResumeTailorEngine._bullets_of("* star bullet"))
        self.assertIn("- dash bullet", ResumeTailorEngine._bullets_of("- dash bullet"))

    def test_missing_bullet_returns_to_its_own_section(self):
        out = self.engine._enforce_content_preservation(self.TEMPLATE, self.TAILORED)
        self.assertIn("- Beta role bullet", out)
        # Restored BEFORE the last section, not appended after it.
        self.assertLess(out.index("- Beta role bullet"), out.index("## HONORS & AWARDS"))

    def test_restore_does_not_leak_html_marker(self):
        out = self.engine._enforce_content_preservation(self.TEMPLATE, self.TAILORED)
        self.assertNotIn("zero-omission", out)

    def test_no_missing_bullets_leaves_document_untouched(self):
        out = self.engine._enforce_content_preservation(self.TEMPLATE, self.TEMPLATE)
        self.assertEqual(out, self.TEMPLATE)


if __name__ == "__main__":
    unittest.main()
