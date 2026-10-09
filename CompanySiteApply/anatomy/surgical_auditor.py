# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [SURGICAL_AUDITOR_INIT]
# Timestamp: 2026-10-09 18:52:00 +05:30
# Issue / Context: Needed an isolated micro-healer coordinator operating at PageBone -> SectionSurface -> FormMatrix level.
# Changes Made: Implemented SurgicalAuditor to run pin-point diagnosis and execute micro-repairs without full-page reloads.
# Rationale: Guarantees that fixing one section (e.g. Education School) leaves all other sections completely untouched.
# Preventative Notes: Always verify section boundary before invoking heal_isolated.
# ==============================================================================

import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.anatomy.base_anatomy import PageBone, SectionSurface, SectionAuditResult

logger = logging.getLogger(__name__)


class SurgicalAuditor:
    """
    Coordinates isolated micro-audits and targeted healing across the Anatomical ATS hierarchy.
    """

    def __init__(self, registered_bones: List[PageBone]):
        self.bones = registered_bones

    def find_active_bone(self, page: Any) -> Optional[PageBone]:
        """Identifies the active PageBone matching the current browser URL / state."""
        for bone in self.bones:
            try:
                if bone.is_current_page(page):
                    return bone
            except Exception as e:
                logger.warning(f"Error checking bone {bone.page_title}: {e}")
        return None

    def diagnose_and_heal_page(self, page: Any, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """
        Diagnoses each section on the current page. If a section is defective,
        surgically heals ONLY that defective section without touching compliant sections.
        """
        bone = self.find_active_bone(page)
        if not bone:
            return {
                "success": False,
                "error": "No matching PageBone found for current browser state"
            }

        report = {
            "page_title": bone.page_title,
            "page_index": bone.page_index,
            "audits": [],
            "healed_sections": []
        }

        for sec in bone.get_sections():
            audit_res = sec.audit(page, ground_truth)
            report["audits"].append(audit_res)

            if not audit_res.is_valid:
                logger.info(f"[SurgicalAuditor] Section '{sec.section_name}' failed audit. Commencing isolated micro-healing...")
                healed = sec.heal_isolated(page, ground_truth)
                if healed:
                    report["healed_sections"].append(sec.section_name)
                    logger.info(f"[SurgicalAuditor] Successfully healed section '{sec.section_name}'.")
                else:
                    logger.error(f"[SurgicalAuditor] Failed to heal section '{sec.section_name}'.")

        report["success"] = True
        return report
