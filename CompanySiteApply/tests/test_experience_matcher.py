# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_EXPERIENCE_MATCHER_INIT]
# Timestamp: 2026-10-12 21:50:00 +05:30
# Issue / Context: experience_matcher.py (extracted from archived
#                  heal_all_experience_tiles.py) needed regression coverage for
#                  resume.md parsing and fuzzy employer matching.
# Changes Made: Pure-function unit tests with zero browser dependency,
#               zero PII, zero hardcoded employer literals outside fixtures.
#
# [ENTRY #002]
# Term: [ROLE_BULLET_PRIORITY_TESTS]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Phase 4 added load_role_bullets_for_employer() and
#                  markdown-bullet priority in heal_single_experience_tile.
# Changes Made: TestRoleBulletPriority (role>BASE>none, heal prefers
#               markdown bullets while keeping structured city/country).
# Preventative Notes: Fixture employers stay synthetic (Acme/Globex).
# ==============================================================================

import os
import tempfile
import unittest

from CompanySiteApply.utils.experience_matcher import (
    load_role_bullets_for_employer,
    match_experience_entry,
    parse_resume_experiences,
)

_RESUME_FIXTURE = """# Candidate

## PROFESSIONAL EXPERIENCE

### **Acme Technologies**
*Bangalore, India | March 2022 - Present*
• Shipped event pipeline handling 1M msgs/day
• Cut p99 latency by 40%

### **Globex Corp**
*Delhi, India | June 2020 - Feb 2022*
• Maintained billing service

## EDUCATION

### **Some University**
"""


class TestExperienceMatcher(unittest.TestCase):
    def _write_fixture(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(_RESUME_FIXTURE)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_parse_resume_experiences(self):
        parsed = parse_resume_experiences(self._write_fixture())
        self.assertEqual(len(parsed), 2)
        acme = parsed["Acme Technologies"]
        self.assertEqual(acme["city"], "Bengaluru")  # bangalore standardized
        self.assertEqual(acme["country"], "India")
        self.assertEqual(len(acme["bullets"]), 2)
        self.assertTrue(acme["bullets"][0].startswith("Shipped event"))

    def test_parse_missing_file_returns_empty(self):
        self.assertEqual(parse_resume_experiences("/nonexistent/resume.md"), {})

    def test_match_exact_and_fuzzy(self):
        parsed = parse_resume_experiences(self._write_fixture())
        # Substring either direction
        self.assertIsNotNone(match_experience_entry("Acme Technologies Pvt Ltd", parsed))
        # Token overlap without substring
        m = match_experience_entry("Engineer @ Globex", parsed)
        self.assertIsNotNone(m)
        self.assertEqual(len(m["bullets"]), 1)

    def test_match_no_hit_returns_none(self):
        parsed = parse_resume_experiences(self._write_fixture())
        self.assertIsNone(match_experience_entry("Unknown Employer XYZ", parsed))
        self.assertIsNone(match_experience_entry("", parsed))
        self.assertIsNone(match_experience_entry("Acme", {}))


class TestRoleBulletPriority(unittest.TestCase):
    """Phase 4: role resume.md -> BASE hierarchy bullet priority."""

    def _profile(self, d):
        from pathlib import Path as _P
        prof = _P(d) / "synth_exp"
        (prof / "company_site_apply" / "JPMorganChase" / "resumes").mkdir(parents=True)
        (prof / "company_site_apply" / "JPMorganChase" / "resumes" / "BASE.md").write_text(
            "## PROFESSIONAL EXPERIENCE\n\n"
            "### **Acme Technologies**\n*Bangalore, India | 2022 - Present*\n"
            "• Base bullet one\n",
            encoding="utf-8")
        role_dir = (prof / "APPLIED ON COMPANY WEBSITE" / "Acme_Corp" / "Engineer_3001")
        role_dir.mkdir(parents=True)
        (role_dir / "resume.md").write_text(
            "## PROFESSIONAL EXPERIENCE\n\n"
            "### **Acme Technologies**\n*Bangalore, India | 2022 - Present*\n"
            "• Role bullet one\n",
            encoding="utf-8")
        return prof

    def _cand(self, prof):
        return {"profile_dir": str(prof), "job_id": "3001",
                "candidate": {"full_name": "Synth Exp"}}

    def test_role_resume_beats_base(self):
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            got = load_role_bullets_for_employer(
                self._cand(prof), "Acme Corp", "Acme Technologies")
            self.assertEqual(got, ["Role bullet one"])

    def test_base_beats_nothing_when_role_missing(self):
        import shutil as _shutil
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            _shutil.rmtree(prof / "APPLIED ON COMPANY WEBSITE")
            got = load_role_bullets_for_employer(
                self._cand(prof), "JPMorgan Chase & Co.", "Acme Technologies")
            self.assertEqual(got, ["Base bullet one"])

    def test_empty_when_no_match(self):
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            self.assertEqual(load_role_bullets_for_employer(
                self._cand(prof), "Acme Corp", "Unknown Employer XYZ"), [])
            self.assertEqual(load_role_bullets_for_employer(
                self._cand(prof), "Acme Corp", ""), [])

    def test_heal_prefers_markdown_bullets_keeps_structured_city(self):
        from unittest.mock import MagicMock
        from CompanySiteApply.section_agents.scripts.s3_experience_tile import (
            heal_single_experience_tile,
        )
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            cand = self._cand(prof)
            cand["candidate"] = {
                "full_name": "Synth Exp", "city": "FallbackCity",
                "country": "FallbackCountry",
                "work_experience": [{
                    "employer": "Acme Technologies", "city": "StructCity",
                    "country": "StructCountry",
                    "bullets": ["Structured bullet one"],
                }],
            }
            tile = MagicMock()
            tile.inner_text.return_value = "Acme Technologies\n03/2026"
            edit_btn = MagicMock()
            edit_btn.count.return_value = 1
            tile.locator.return_value.first = edit_btn
            filled = {}

            def _locator(selector, *args):
                m = MagicMock()
                m.first = m
                if "achievements" in selector:
                    m.count.return_value = 1
                    m.fill.side_effect = lambda v: filled.update(text=v)
                else:
                    m.count.return_value = 0
                return m

            page = MagicMock()
            page.url = ""
            page.locator.side_effect = lambda sel, *a: (
                MagicMock(all=MagicMock(return_value=[tile]))
                if sel == ".apply-flow-profile-item-tile"
                else _locator(sel))
            res = heal_single_experience_tile(page, cand, tile_index=0)
            self.assertTrue(res.get("success", False))
            self.assertIn("Role bullet one", filled.get("text", ""))
            self.assertNotIn("Structured bullet one", filled.get("text", ""))
            self.assertEqual(res.get("city"), "StructCity")
            self.assertEqual(res.get("country"), "StructCountry")


if __name__ == "__main__":
    unittest.main()
