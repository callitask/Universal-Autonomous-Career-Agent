# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [PROFILE_SECTION_AGENT_INIT]
# Timestamp: 2026-10-09 20:39:00 +05:30
# Issue / Context: Needed a dedicated mini-agent for Section 1 personal details and facility selection.
# Changes Made: Implemented ProfileSectionAgent encapsulating contact fields, address verification,
#               Country combobox healing, and interactive Preferred Location facility pill selection.
# Rationale: Guarantees zero unmapped contact fields on requisition onboarding.
# Preventative Notes: Never advance without verifying Preferred Location combobox commitment.
#
# [ENTRY #002]
# Term: [ZERO_HARDCODING_CITY_LOCATION_RESOLUTION]
# Timestamp: 2026-10-09 21:31:00 +05:30
# Issue / Context: Hardcoded city literals ('Bengaluru', 'Tower D', 'Platina') broke compatibility for any other city/facility.
# Changes Made: Dynamically resolved city and preferred location from candidate['city'], candidate['location'], and target_jobs['locations'].
# Rationale: Seamlessly supports any city, state, or country across global requisitions.
# Preventative Notes: Never hardcode city names or building names in this agent.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.section_agents.sub_agents.personal_details_subagent import PersonalDetailsSubAgent
from CompanySiteApply.section_agents.sub_agents.preferred_location_subagent import PreferredLocationSubAgent

logger = logging.getLogger(__name__)


class ProfileSectionAgent(BaseSectionAgent):
    """
    Master Coordinator for Section 1: Personal Details & Preferred Location.
    Composes PersonalDetailsSubAgent and PreferredLocationSubAgent.
    """

    def __init__(self):
        self.personal_subagent = PersonalDetailsSubAgent()
        self.location_subagent = PreferredLocationSubAgent()

    @property
    def section_name(self) -> str:
        return "profile"

    @property
    def target_stage(self) -> str:
        return "section_1"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("section") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/1" in url or "personal" in url.lower() or "profile" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits Section 1 personal details and preferred location sub-agents.
        """
        personal_audit = self.personal_subagent.audit(page, candidate_data)
        location_audit = self.location_subagent.audit(page, candidate_data)

        errors = page.locator(".cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message").all_text_contents()
        err_list = [e.strip() for e in errors if e.strip() and "saved" not in e.lower() and "all set" not in e.lower() and "successfully" not in e.lower()]

        is_valid = personal_audit.get("is_valid", False) and location_audit.get("is_valid", False) and len(err_list) == 0

        return {
            "is_valid": is_valid,
            "errors": err_list,
            "personal_details": personal_audit,
            "preferred_location": location_audit
        }

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes surgical healing across personal details and preferred location.
        """
        try:
            # 1. Heal personal details
            personal_res = self.personal_subagent.heal(page, candidate_data)

            # 2. Heal preferred location
            location_res = self.location_subagent.heal(page, candidate_data)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "section": self.section_name,
                "personal_details": personal_res,
                "preferred_location": location_res,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[ProfileSectionAgent] Heal error: {e}")
            return {"success": False, "section": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
        except Exception:
            return False
