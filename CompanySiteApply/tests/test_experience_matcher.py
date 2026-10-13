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
# ==============================================================================

import os
import tempfile
import unittest

from CompanySiteApply.utils.experience_matcher import (
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


if __name__ == "__main__":
    unittest.main()
