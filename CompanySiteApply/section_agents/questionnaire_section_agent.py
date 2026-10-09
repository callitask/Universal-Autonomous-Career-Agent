# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [QUESTIONNAIRE_SECTION_AGENT_MODULAR_REFACTOR]
# Timestamp: 2026-10-09 22:44:30 +05:30
# Issue / Context: Monolithic questionnaire agent failed on multi-select dropdown questions and caused false-positives.
# Changes Made: Refactored QuestionnaireSectionAgent to act as Master Coordinator orchestrating
#               BinaryQuestionSubAgent, TechnicalCompetencySubAgent, and DropdownQuestionSubAgent.
# Rationale: Guarantees complete resolution of pills, dropdowns, and cascading trees with zero hardcoding.
# Preventative Notes: Never skip non-pill combobox inputs in audit or heal.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.section_agents.sub_agents.binary_question_subagent import BinaryQuestionSubAgent
from CompanySiteApply.section_agents.sub_agents.technical_competency_subagent import TechnicalCompetencySubAgent
from CompanySiteApply.section_agents.sub_agents.dropdown_question_subagent import DropdownQuestionSubAgent

logger = logging.getLogger(__name__)


class QuestionnaireSectionAgent(BaseSectionAgent):
    """
    Master Coordinator for Section 2 Application & Screening Questionnaires.
    Orchestrates BinaryQuestionSubAgent, TechnicalCompetencySubAgent, and DropdownQuestionSubAgent.
    """

    def __init__(self):
        self.binary_subagent = BinaryQuestionSubAgent()
        self.competency_subagent = TechnicalCompetencySubAgent()
        self.dropdown_subagent = DropdownQuestionSubAgent()

    @property
    def section_name(self) -> str:
        return "questionnaire"

    @property
    def target_stage(self) -> str:
        return "section_2"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("section") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/2" in url or "/apply/questions" in url or "questions" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits active questions across binary, competency, and dropdown sub-agents.
        """
        try:
            bin_audit = self.binary_subagent.audit(page, candidate_data)
            comp_audit = self.competency_subagent.audit(page, candidate_data)
            drop_audit = self.dropdown_subagent.audit(page, candidate_data)

            # Check for any active error banners or red labels
            errors = page.locator(".cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message, [aria-invalid='true']").all_text_contents()
            err_list = [e.strip() for e in errors if e.strip() and "saved" not in e.lower() and "all set" not in e.lower() and "successfully" not in e.lower()]

            is_valid = (
                bin_audit.get("is_valid", False) and
                comp_audit.get("is_valid", False) and
                drop_audit.get("is_valid", False) and
                len(err_list) == 0
            )

            return {
                "is_valid": is_valid,
                "errors": err_list,
                "binary": bin_audit,
                "competency": comp_audit,
                "dropdowns": drop_audit
            }
        except Exception as e:
            logger.error(f"[QuestionnaireSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes multi-pass cascading healing across binary, competency, and dropdown sub-agents.
        """
        try:
            max_passes = 4
            pass_num = 0

            while pass_num < max_passes:
                pass_num += 1
                logger.info(f"[QuestionnaireSectionAgent] Executing pass {pass_num}/{max_passes}...")

                # 1. Binary Yes/No
                self.binary_subagent.heal(page, candidate_data)
                time.sleep(0.5)

                # 2. Competency Pills (Experience tiers, primary area, specialization, cloud ratings)
                self.competency_subagent.heal(page, candidate_data)
                time.sleep(0.5)

                # 3. Dropdowns & Multi-select Comboboxes (Languages, skills)
                self.dropdown_subagent.heal(page, candidate_data)
                time.sleep(0.5)

                # Check if all satisfied
                audit_res = self.audit(page, candidate_data)
                if audit_res.get("is_valid", False):
                    logger.info(f"[QuestionnaireSectionAgent] All questions satisfied on pass {pass_num}.")
                    break

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "section": self.section_name,
                "passes_run": pass_num,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[QuestionnaireSectionAgent] Heal error: {e}")
            return {"success": False, "section": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False

    def _resolve_experience_tier(self, total_exp: float, pill_elements: List[Any]) -> Optional[Any]:
        return self.competency_subagent._resolve_experience_tier(total_exp, pill_elements)

    def _resolve_expertise_or_domain_pill(self, q_text: str, pill_elements: List[Any], candidate_data: Dict[str, Any]) -> Optional[Any]:
        return self.competency_subagent._resolve_domain_or_specialization(q_text, pill_elements, candidate_data)

    def _resolve_tool_proficiency_pill(self, q_text: str, pill_elements: List[Any], candidate_data: Dict[str, Any]) -> Optional[Any]:
        return self.competency_subagent._resolve_proficiency(q_text, pill_elements, candidate_data)

