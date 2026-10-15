# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_TASK1_REMAINING_GAPS]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Four leftover gaps (company BASE.md reader, Stem contract,
#                  tile re-sort drift, active-tab/PIN parity) had no pins.
# Changes Made: Unit tests for BASE.md company-first resolution (+placeholder
#               guard) and key-tracked multi-tile healing under JET re-sort.
# Rationale: Every gap fix must fail loudly in tests before it can regress.
# Preventative Notes: Temp dirs/env only; never live profiles, CDP, network.
# ==============================================================================

"""Regression tests for Phase-2 Task 1 remaining engineering gaps."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestBaseResumeMdResolution(unittest.TestCase):
    def _profile(self, d):
        prof = Path(d) / "prof"
        (prof / "company_site_apply" / "Acme" / "resumes").mkdir(parents=True)
        (prof / "company_site_apply" / "Acme" / "cover_letters").mkdir(parents=True)
        (prof / "resume.md").write_text("## PROFESSIONAL EXPERIENCE\nmaster", encoding="utf-8")
        return prof

    def test_company_base_wins_over_master(self):
        from CompanySiteApply.utils.company_workspace import resolve_base_resume_md
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            (prof / "company_site_apply" / "Acme" / "resumes" / "BASE.md").write_text(
                "## PROFESSIONAL EXPERIENCE\ncompany-framed", encoding="utf-8")
            cand = {"profile_dir": str(prof)}
            got = resolve_base_resume_md(cand, "Acme Corp")
            self.assertTrue(got.endswith("BASE.md"))
            self.assertIn("Acme", got)

    def test_placeholder_base_ignored_falls_back_to_master(self):
        from CompanySiteApply.utils.company_workspace import resolve_base_resume_md
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            (prof / "company_site_apply" / "Acme" / "resumes" / "BASE.md").write_text(
                "# [FIRSTNAME LASTNAME]\ntemplate", encoding="utf-8")
            cand = {"profile_dir": str(prof)}
            got = resolve_base_resume_md(cand, "Acme Corp")
            self.assertTrue(got.endswith("resume.md"))

    def test_experience_map_prefers_company_base(self):
        from CompanySiteApply.utils.experience_matcher import load_resume_experience_map
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            (prof / "company_site_apply" / "Acme" / "resumes" / "BASE.md").write_text(
                "## PROFESSIONAL EXPERIENCE\n### **Acme Corp** | Engineer\n*2020*\n- did x\n",
                encoding="utf-8")
            cand = {"profile_dir": str(prof),
                    "candidate": {"full_name": "Test User"}}
            m = load_resume_experience_map(cand, "Acme Corp")
            self.assertIn("Acme Corp", m)


class TestTileResortDriftGuard(unittest.TestCase):
    def test_each_employer_healed_once_despite_resort(self):
        from CompanySiteApply.section_agents.experience_section_agent import (
            ExperienceSectionAgent,
        )
        order = [["Cognizant\n03/2026"], ["Infosys\n02/2024"]]

        def make_tile(text):
            t = MagicMock()
            t.inner_text.return_value = text
            return t

        page = MagicMock()
        state = {"order": [make_tile("Cognizant\n03/2026"), make_tile("Infosys\n02/2024")]}

        def _locator(sel):
            m = MagicMock()
            if sel == ".apply-flow-profile-item-tile":
                m.all.return_value = list(state["order"])
            m.count.return_value = 0
            return m

        page.locator.side_effect = _locator
        healed = []

        def _fake_heal(pg, cand, tile_index=0, session_id=None):
            current = [t.inner_text() for t in state["order"]]
            employer = current[tile_index].split("\n")[0]
            healed.append(employer)
            # Simulate Oracle JET re-sorting after SAVE: reverse the tiles.
            state["order"] = list(reversed(state["order"]))
            return {"success": True, "employer": employer}

        cand = {"candidate": {"full_name": "T U", "work_experience": [
            {"employer": "Cognizant"}, {"employer": "Infosys"}]}}
        agent = ExperienceSectionAgent()
        with patch("CompanySiteApply.section_agents.scripts.s3_experience_tile.heal_single_experience_tile",
                   side_effect=_fake_heal):
            with patch.object(ExperienceSectionAgent, "_reorder_tiles_reverse_chronological",
                              return_value=True):
                with patch.object(ExperienceSectionAgent, "verify", return_value=True):
                    with patch.object(ExperienceSectionAgent, "_get_candidate_experiences",
                                      return_value=[{"employer": "Cognizant"},
                                                    {"employer": "Infosys"}]):
                        res = agent.heal(page, cand)
        self.assertTrue(res.get("success"))
        self.assertEqual(sorted(healed), ["Cognizant", "Infosys"])


if __name__ == "__main__":
    unittest.main()
