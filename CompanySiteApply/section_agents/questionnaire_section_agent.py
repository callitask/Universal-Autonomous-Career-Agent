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
# [ENTRY #002]
# Term: [PHASE3_CONDITIONAL_QUESTION_RESCAN]
# Timestamp: 2026-10-12 21:15:00 +05:30
# Issue / Context: Dynamic conditional questions (such as years of work experience radio chip group)
#                  appeared after binary questions were filled and were left unanswered.
# Changes Made: Integrated s2_conditional_questions into audit() and heal() multi-pass loop.
# Rationale: Guarantees zero unanswered questions by performing continuous dynamic DOM rescanning.
# Preventative Notes: Always run conditional rescan after primary subagents.
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

    def __init__(
        self,
        binary_subagent: Optional[BinaryQuestionSubAgent] = None,
        competency_subagent: Optional[TechnicalCompetencySubAgent] = None,
        dropdown_subagent: Optional[DropdownQuestionSubAgent] = None
    ):
        self.binary_subagent = binary_subagent or BinaryQuestionSubAgent()
        self.competency_subagent = competency_subagent or TechnicalCompetencySubAgent()
        self.dropdown_subagent = dropdown_subagent or DropdownQuestionSubAgent()

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

            # Oracle required-field tripwire: empty mandatory questions render this
            # text even when control-type scans miss the widget (e.g. JET radios).
            try:
                required_flags = page.evaluate("""() => {
                    const body = (document.body && document.body.innerText) || '';
                    const m = body.match(/This information is required\\.?/gi);
                    return m ? m.length : 0;
                }""") or 0
            except Exception:
                required_flags = 0
            if required_flags:
                err_list.append(f"{required_flags} required question(s) unanswered (Oracle flag)")

            # Red-asterisk tripwire (Rank 4, 2026-10-13): Oracle marks empty
            # required questions with a red asterisk BEFORE any validation
            # attempt, when "This information is required." does not exist yet
            # (incident 210765001: tier pills sat unselected under a red *).
            try:
                asterisk_flags = page.evaluate("""() => {
                    // asterisk-required-scan
                    const isVisible = el => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
                    };
                    const rows = Array.from(document.querySelectorAll(
                        '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset'
                    )).filter(isVisible);
                    let flagged = 0;
                    for (const r of rows) {
                        const txt = (r.innerText || '');
                        if (!txt.includes('*')) continue;
                        const pills = Array.from(r.querySelectorAll(
                            'button.cx-select-pill-section, button[role="radio"], oj-option, [role="radio"], input[type="radio"], input[type="checkbox"]'
                        )).filter(isVisible);
                        const inputs = Array.from(r.querySelectorAll(
                            'input[type="text"], input:not([type]):not([role="combobox"]), textarea, select, input[role="combobox"]'
                        )).filter(isVisible);
                        const anyPill = pills.some(p =>
                            (p.className || '').includes('selected') ||
                            p.getAttribute('aria-checked') === 'true' ||
                            p.getAttribute('aria-pressed') === 'true' ||
                            p.getAttribute('aria-selected') === 'true' ||
                            p.checked === true
                        );
                        const anyVal = inputs.some(i => ((i.value || '').trim().length > 0)) ||
                            r.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill').length > 0;
                        const requiredMark = r.querySelector('.input-row__label--required-star, .input-row__label--required, .text-color-red, .required, [aria-required="true"]') !== null ||
                            /\\*\\s*$/.test(txt.split('\\n')[0] || '');
                        if (requiredMark && !anyPill && !anyVal) flagged += 1;
                    }
                    return flagged;
                }""") or 0
            except Exception:
                asterisk_flags = 0
            if asterisk_flags:
                err_list.append(f"{asterisk_flags} required question(s) unanswered (red-asterisk flag)")

            # Check for newly revealed or unanswered conditional questions
            cond_unanswered = []
            try:
                from CompanySiteApply.section_agents.scripts.s2_conditional_questions import scan_unanswered_questions
                cond_unanswered = scan_unanswered_questions(page)
            except Exception as ce:
                logger.debug(f"[QuestionnaireSectionAgent] Conditional scan note: {ce}")

            is_valid = (
                bin_audit.get("is_valid", False) and
                comp_audit.get("is_valid", False) and
                drop_audit.get("is_valid", False) and
                len(err_list) == 0 and
                len(cond_unanswered) == 0
            )

            return {
                "is_valid": is_valid,
                "errors": err_list,
                "binary": bin_audit,
                "competency": comp_audit,
                "dropdowns": drop_audit,
                "conditional": cond_unanswered
            }
        except Exception as e:
            logger.error(f"[QuestionnaireSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes multi-pass cascading healing across binary, competency, dropdown, and conditional sub-agents.
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

                # 4. Conditional Questions (Newly revealed questions e.g. experience tiers, skills)
                try:
                    from CompanySiteApply.section_agents.scripts.s2_conditional_questions import heal_conditional_questions
                    from CompanySiteApply.ipc.ipc_manager import get_effective_session_id
                    _sess = get_effective_session_id(candidate_data, None) or None
                    heal_conditional_questions(page, candidate_data, session_id=_sess)
                    time.sleep(0.5)
                except Exception as ce:
                    logger.debug(f"[QuestionnaireSectionAgent] Conditional heal note: {ce}")

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

