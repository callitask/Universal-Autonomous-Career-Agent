# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_COMPANY_WORKSPACE_INIT]
# Timestamp: 2026-10-13 20:00:00 +05:30
# Issue / Context: Per-company workspaces must self-provision (slug, dirs,
#                  master seeding without PII leaks) and Stage 4 must archive
#                  per-application docs where operators look for them.
# ==============================================================================

import os
import tempfile
import unittest
from pathlib import Path

from CompanySiteApply.utils.company_workspace import (
    company_cover_tone,
    company_kind,
    company_slug,
    company_workspace_dir,
    ensure_company_workspace,
    resolve_base_cover_letter_md,
    resolve_base_resume_md,
    resolve_company_roots,
)
from CompanySiteApply.autonomous_job_agent import _archive_application_docs


class TestCompanySlug(unittest.TestCase):
    def test_normalizes(self):
        self.assertEqual(company_slug("JPMorgan Chase & Co."), "JPMorganChase")
        self.assertEqual(company_slug("Goldman Sachs"), "GoldmanSachs")
        self.assertEqual(company_slug("JPMorgan&Chasae"), "JPMorganChasae")
        self.assertEqual(company_slug(""), "GenericCompany")


class TestEnsureWorkspace(unittest.TestCase):
    def test_creates_and_seeds_from_master(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "someone"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            (prof / "resume.md").write_text("# MASTER", encoding="utf-8")
            cand = {"profile": "someone", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            self.assertEqual(work, csa / "JPMorganChase")
            self.assertTrue((work / "cover_letters").is_dir())
            self.assertTrue((work / "resumes").is_dir())
            self.assertEqual((work / "resumes" / "BASE.md").read_text(encoding="utf-8"), "# MASTER")
            self.assertFalse((work / "resume.md").exists())
            self.assertTrue((work / "README.md").exists())

    def test_migrates_legacy_root_files(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "someone"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            (prof / "resume.md").write_text("# MASTER", encoding="utf-8")
            cand = {"profile": "someone", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            # Legacy waste: root resume + company.json + cover_letter_base.md
            (work / "resume.md").write_text("# MASTER", encoding="utf-8")
            (work / "company.json").write_text("{}", encoding="utf-8")
            (work / "cover_letter_base.md").write_text("legacy", encoding="utf-8")
            ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            self.assertFalse((work / "company.json").exists())
            self.assertFalse((work / "cover_letter_base.md").exists())
            self.assertTrue((work / "resumes" / "BASE.md").is_file())
            # Root holds README only.
            names = sorted(p.name for p in work.iterdir() if p.name != "__pycache__")
            self.assertEqual(names, ["README.md", "cover_letters", "resumes"])

    def test_no_pii_without_master(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "ghost"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            cand = {"profile": "ghost", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "Amex")
            self.assertTrue(work.is_dir())
            self.assertFalse((work / "resume.md").exists())

    def test_base_letter_seeded_from_profile_letter(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "someone"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            (prof / "cover_letter.md").write_text("# Base letter", encoding="utf-8")
            cand = {"profile": "someone", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "Barclays")
            seeded = work / "cover_letters" / "BASE.md"
            self.assertTrue(seeded.exists())
            self.assertIn("Base letter", seeded.read_text(encoding="utf-8"))

    def test_base_letter_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "someone"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            (prof / "cover_letter.md").write_text("# New base", encoding="utf-8")
            cand = {"profile": "someone", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "Barclays")
            custom = work / "cover_letters" / "BASE.md"
            custom.write_text("# Hand-tuned", encoding="utf-8")
            ensure_company_workspace(cand, "Barclays")
            self.assertEqual(custom.read_text(encoding="utf-8"), "# Hand-tuned")

    def test_company_roots_first(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "someone"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            cand = {"profile": "someone", "profile_dir": str(prof)}
            ensure_company_workspace(cand, "Barclays")
            roots = resolve_company_roots(cand, "Barclays")
            self.assertTrue(roots[0].endswith("Barclays"))


class TestCompanyKind(unittest.TestCase):
    def test_service_uses_generic(self):
        self.assertEqual(company_kind("Tata Consultancy Services"), "service")
        self.assertEqual(company_kind("Infosys"), "service")

    def test_product_uses_company(self):
        self.assertEqual(company_kind("JPMorgan Chase & Co."), "company")
        self.assertEqual(company_kind("Some Unknown Startup XYZ"), "company")

    def test_cover_tone(self):
        tone = company_cover_tone("JPMorgan Chase & Co.")
        self.assertIn("banking", tone)
        self.assertEqual(company_cover_tone("No Such Company ABC"), "")


class TestArchiveDocs(unittest.TestCase):
    def setUp(self):
        # Isolate profile resolution to a temp Operations root so the suite
        # never recreates profiles/someone/ (or any profile dir) in the repo.
        # NOTE: resolve_profile_dir() falls back to the repo tree when the
        # Operations profile dir is absent, so the temp profile must exist.
        import os as _os
        from pathlib import Path as _P
        self._tmp_ops = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_ops.cleanup)
        (_P(self._tmp_ops.name) / "profiles" / "someone").mkdir(parents=True)
        self._old_ops = _os.environ.get("JOB_AGENT_OPERATIONS")
        _os.environ["JOB_AGENT_OPERATIONS"] = self._tmp_ops.name
        self.addCleanup(self._restore_ops)

    def _restore_ops(self):
        import os as _os
        if self._old_ops is None:
            _os.environ.pop("JOB_AGENT_OPERATIONS", None)
        else:
            _os.environ["JOB_AGENT_OPERATIONS"] = self._old_ops

    def test_copies_into_applied_tree(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "csa"
            src.mkdir()
            (src / "Name_Cover_Letter.pdf").write_text("pdf", encoding="utf-8")
            (src / "Cover_Letter.txt").write_text("txt", encoding="utf-8")
            dest = _archive_application_docs(
                Path(d), {"profile": "someone"}, "JPMorgan Chase & Co.",
                "Lead Software Engineer", "123",
                str(src / "Name_Cover_Letter.pdf"), str(src),
            )
            self.assertIn("123", dest)
            # Fixed-stem contract (Decision 2/3): the source basename is NOT
            # preserved; the role folder carries <Stem>_Cover_Letter.pdf where
            # Stem derives from the profile (no full_name here -> "Someone").
            self.assertTrue(Path(dest, "Someone_Cover_Letter.pdf").exists())
            self.assertFalse(Path(dest, "Name_Cover_Letter.pdf").exists())
            self.assertTrue(Path(dest, "Cover_Letter.txt").exists())


class TestThreeTierBaseResolvers(unittest.TestCase):
    """Phase 3A: canonical (profile_dir, company) resolver priority.

    Synthetic fixture profile "alex_rivera" only — never real candidate PII.
    """

    def _profile(self, d):
        # Synthetic profile tree with all three resume tiers populated.
        prof = Path(d) / "alex_rivera"
        (prof / "company_site_apply" / "JPMorganChase" / "resumes").mkdir(parents=True)
        (prof / "company_site_apply" / "JPMorganChase" / "cover_letters").mkdir(parents=True)
        (prof / "company_site_apply" / "JPMorgan Chase" / "resumes").mkdir(parents=True)
        (prof / "company_site_apply" / "JPMorgan Chase" / "cover_letters").mkdir(parents=True)
        (prof / "company_site_apply" / "JPMorganChase" / "resumes" / "BASE.md").write_text(
            "## SLUG BASE\nreal", encoding="utf-8")
        (prof / "company_site_apply" / "JPMorganChase" / "cover_letters" / "BASE.md").write_text(
            "## SLUG LETTER\nreal", encoding="utf-8")
        (prof / "company_site_apply" / "JPMorgan Chase" / "resumes" / "BASE.md").write_text(
            "## LEGACY BASE\nreal", encoding="utf-8")
        (prof / "company_site_apply" / "JPMorgan Chase" / "cover_letters" / "BASE.md").write_text(
            "## LEGACY LETTER\nreal", encoding="utf-8")
        (prof / "company_site_apply" / "resume.md").write_text("## CSA MASTER\nreal", encoding="utf-8")
        (prof / "company_site_apply" / "cover_letter.md").write_text("## CSA LETTER\nreal", encoding="utf-8")
        (prof / "resume.md").write_text("## ROOT MASTER\nreal", encoding="utf-8")
        (prof / "cover_letter_template.md").write_text("## TEMPLATE\nreal", encoding="utf-8")
        return prof

    def test_resume_priority_slug_over_legacy_over_masters(self):
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            got = resolve_base_resume_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "JPMorganChase" / "resumes" / "BASE.md")
            (prof / "company_site_apply" / "JPMorganChase" / "resumes" / "BASE.md").unlink()
            got = resolve_base_resume_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "JPMorgan Chase" / "resumes" / "BASE.md")
            (prof / "company_site_apply" / "JPMorgan Chase" / "resumes" / "BASE.md").unlink()
            got = resolve_base_resume_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "resume.md")
            (prof / "company_site_apply" / "resume.md").unlink()
            got = resolve_base_resume_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "resume.md")

    def test_resume_placeholders_fall_through_to_none(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "alex_rivera"
            (prof / "company_site_apply").mkdir(parents=True)
            (prof / "resume.md").write_text("# [FIRSTNAME LASTNAME]\ntemplate", encoding="utf-8")
            self.assertIsNone(resolve_base_resume_md(prof, "JPMorgan Chase & Co."))
            self.assertIsNone(resolve_base_resume_md(prof, ""))
            self.assertIsNone(resolve_base_resume_md(None, "Acme"))

    def test_cover_priority_and_template_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            prof = self._profile(d)
            got = resolve_base_cover_letter_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "JPMorganChase" / "cover_letters" / "BASE.md")
            (prof / "company_site_apply" / "JPMorganChase" / "cover_letters" / "BASE.md").unlink()
            got = resolve_base_cover_letter_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "JPMorgan Chase" / "cover_letters" / "BASE.md")
            (prof / "company_site_apply" / "JPMorgan Chase" / "cover_letters" / "BASE.md").unlink()
            got = resolve_base_cover_letter_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "company_site_apply" / "cover_letter.md")
            (prof / "company_site_apply" / "cover_letter.md").unlink()
            got = resolve_base_cover_letter_md(prof, "JPMorgan Chase & Co.")
            self.assertEqual(got, prof / "cover_letter_template.md")

    def test_cover_placeholders_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "alex_rivera"
            (prof / "company_site_apply").mkdir(parents=True)
            (prof / "cover_letter_template.md").write_text(
                "Dear {{FULL_NAME}},\ntemplate", encoding="utf-8")
            self.assertIsNone(resolve_base_cover_letter_md(prof, "Acme"))

    def test_ensure_never_overwrites_real_base(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "alex_rivera"
            csa = prof / "company_site_apply"
            csa.mkdir(parents=True)
            (prof / "resume.md").write_text("## MASTER\nreal", encoding="utf-8")
            cand = {"profile": "alex_rivera", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            target = work / "resumes" / "BASE.md"
            target.write_text("## SACRED USER CONTENT\nreal", encoding="utf-8")
            before = target.read_bytes()
            ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            self.assertEqual(target.read_bytes(), before)

    def test_ensure_seeds_from_legacy_tier_first(self):
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "alex_rivera"
            csa = prof / "company_site_apply"
            (csa / "JPMorgan Chase" / "resumes").mkdir(parents=True)
            (csa / "JPMorgan Chase" / "resumes" / "BASE.md").write_text(
                "## LEGACY\nreal", encoding="utf-8")
            (prof / "resume.md").write_text("## ROOT\nreal", encoding="utf-8")
            cand = {"profile": "alex_rivera", "profile_dir": str(prof)}
            work = ensure_company_workspace(cand, "JPMorgan Chase & Co.")
            seeded = (work / "resumes" / "BASE.md").read_text(encoding="utf-8")
            self.assertIn("LEGACY", seeded)

    def test_application_docs_reexports_resolvers(self):
        import CompanySiteApply.utils.application_docs as ad
        import CompanySiteApply.utils.company_workspace as cw
        self.assertIs(ad.resolve_base_resume_md, cw.resolve_base_resume_md)
        self.assertIs(ad.resolve_base_cover_letter_md, cw.resolve_base_cover_letter_md)


if __name__ == "__main__":
    unittest.main()
