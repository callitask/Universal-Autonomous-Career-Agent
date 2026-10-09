import unittest
from unittest.mock import MagicMock
from CompanySiteApply.anatomy import (
    PageBone,
    SectionSurface,
    FormMatrix,
    FieldCell,
    CellAuditResult,
    SectionAuditResult,
    SurgicalAuditor,
    OracleEducationSectionSurface,
    OracleExperienceSectionSurface,
    OraclePage3TimelineBone,
)


class DummyEducationSection(SectionSurface):
    @property
    def section_name(self) -> str:
        return "Education"

    def audit(self, page, ground_truth):
        has_school = ground_truth.get("school_filled", False)
        return SectionAuditResult(
            section_name=self.section_name,
            is_valid=has_school,
            missing_fields=[] if has_school else ["school"]
        )

    def heal_isolated(self, page, ground_truth):
        ground_truth["school_filled"] = True
        return True


class DummyExperienceSection(SectionSurface):
    @property
    def section_name(self) -> str:
        return "Experience"

    def audit(self, page, ground_truth):
        # Experience is already compliant
        return SectionAuditResult(
            section_name=self.section_name,
            is_valid=True
        )

    def heal_isolated(self, page, ground_truth):
        raise AssertionError("Flawless Experience section must NEVER be touched when healing Education!")


class DummyPage3TimelineBone(PageBone):
    @property
    def page_index(self) -> int:
        return 3

    @property
    def page_title(self) -> str:
        return "Experience & Education Timeline"

    def is_current_page(self, page):
        return True

    def get_sections(self):
        return [DummyEducationSection(), DummyExperienceSection()]


class TestAnatomyHierarchy(unittest.TestCase):
    def test_surgical_auditor_isolates_healing(self):
        page = MagicMock()
        ground_truth = {"school_filled": False}

        auditor = SurgicalAuditor([DummyPage3TimelineBone()])
        active_bone = auditor.find_active_bone(page)
        self.assertIsNotNone(active_bone)
        self.assertEqual(active_bone.page_index, 3)

        report = auditor.diagnose_and_heal_page(page, ground_truth)
        self.assertTrue(report["success"])
        self.assertIn("Education", report["healed_sections"])
        self.assertNotIn("Experience", report["healed_sections"])
        self.assertTrue(ground_truth["school_filled"])

    def test_oracle_page3_bone_and_sections(self):
        page = MagicMock()
        page.url = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210796584/apply/section/3"

        bone = OraclePage3TimelineBone()
        self.assertTrue(bone.is_current_page(page))
        self.assertEqual(bone.page_index, 3)

        sections = bone.get_sections()
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].section_name, "Education")
        self.assertEqual(sections[1].section_name, "WorkExperience")


if __name__ == "__main__":
    unittest.main()
