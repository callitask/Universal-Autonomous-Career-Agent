# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [DROPDOWN_QUESTION_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:44:00 +05:30
# Issue / Context: Screening questions rendered as multi-select comboboxes (e.g. programming languages)
#                  were skipped by pill-only loops, resulting in red validation failures.
# Changes Made: Built DropdownQuestionSubAgent encapsulating combobox detection, dynamic option ranking,
#               multi-option selection, and error label clearance.
# Rationale: Guarantees 100% resolution for all non-pill dropdown questionnaire inputs with zero hardcoding.
# Preventative Notes: Never hardcode programming languages or skills; dynamically match candidate profile.
# ==============================================================================
# [ENTRY #002]
# Term: [PHASE4_DROPDOWN_QUESTIONS_IPC_DELEGATION]
# Timestamp: 2026-10-12 21:38:00 +05:30
# Issue / Context: Section 2 Dropdown questions needed IPCManager serialization for auditability.
# Changes Made: Delegated heal() to s2_dropdown_questions.heal_dropdown_questions().
# Rationale: Enables subagent independence and IPC integration.
# Preventative Notes: Never bypass IPC serialization for active questions.
# ==============================================================================

import re
import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class DropdownQuestionSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Page 2 Dropdown & Multi-Select Combobox Questions.
    Handles fields like 'Which of the following programming languages have you worked with?( Choose two that apply) *'.
    """

    @property
    def section_name(self) -> str:
        return "dropdown_questions"

    @property
    def target_stage(self) -> str:
        return "section_2"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/2" in url or "questions" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            unanswered = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"]'));
                const missing = [];
                const seenRow = new Set();
                const rowLabel = r => {
                    const label = r.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || "";
                    return label;
                };
                for (const r of rows) {
                    if (r.offsetWidth === 0 && r.offsetHeight === 0) continue;
                    // Has combobox or dropdown
                    const cb = r.querySelector('input[role="combobox"], [class*="multi-select"], button.icon-dropdown-arrow, select');
                    if (!cb) continue;
                    seenRow.add(r);

                    // Does it already have pills or input value?
                    const pills = r.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill');
                    const hasPills = pills.length > 0;
                    const valInput = r.querySelector('input[role="combobox"], select');
                    const hasVal = valInput && valInput.value && valInput.value.trim().length > 0;

                    // Check if required: Oracle renders the red asterisk as an
                    // EMPTY span (no literal '*' in text) + required label
                    // class + aria-required on the input (incident 210788242).
                    const label = rowLabel(r);
                    const hasStar = r.querySelector('.input-row__label--required-star, .input-row__label--required, .text-color-red') !== null;
                    const isAriaReq = r.querySelector('[aria-required="true"]') !== null;
                    const isRequired = label.includes('*') || r.className.includes('required') || hasStar || isAriaReq;
                    const hasError = r.querySelector('.cx-message--error, .error, .alert-danger, [class*="error"], [aria-invalid="true"]') !== null;

                    if ((isRequired || hasError) && !hasPills && !hasVal) {
                        missing.push(label);
                    }
                }
                // Orphan sweep (incident 210788242): required comboboxes living
                // outside the standard row containers (late-revealed rows).
                const orphans = Array.from(document.querySelectorAll('input[role="combobox"], select')).filter(el => {
                    if (el.offsetWidth === 0 && el.offsetHeight === 0) return false;
                    const scope = el.closest('.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset');
                    if (scope && seenRow.has(scope)) return false;
                    const holder = scope || el.parentElement;
                    if (!holder) return false;
                    const pills = holder.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill');
                    if (pills.length > 0) return false;
                    if ((el.value || '').trim().length > 0) return false;
                    const text = (holder.innerText || '');
                    return text.includes('*') || /required/i.test(text);
                });
                orphans.forEach(el => {
                    const holder = el.closest('.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset') || el.parentElement;
                    const label = holder ? (holder.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || holder.innerText.split('\\n')[0].trim()) : 'Unlabeled required combobox';
                    missing.push(label || 'Unlabeled required combobox');
                });
                return missing;
            }''')

            # Red error labels anywhere in questionnaire dropdowns
            errors = page.evaluate('''() => {
                const errs = Array.from(document.querySelectorAll('.input-row--multiselect ~ [class*="error"], .cx-form-control__error-message, .error, [aria-invalid="true"]'));
                return errs.filter(e => e.offsetWidth > 0 || e.offsetHeight > 0).map(e => e.innerText.trim()).filter(Boolean);
            }''')

            return {
                "is_valid": len(unanswered) == 0 and len(errors) == 0,
                "unanswered_dropdown_questions": unanswered,
                "errors": errors
            }
        except Exception as e:
            logger.error(f"[DropdownQuestionSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from CompanySiteApply.section_agents.scripts.s2_dropdown_questions import heal_dropdown_questions
            from CompanySiteApply.ipc.ipc_manager import get_effective_session_id
            _sess = get_effective_session_id(candidate_data, None) or None
            res = heal_dropdown_questions(page, candidate_data, session_id=_sess)
            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "healed_count": res.get("healed_count", 0),
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[DropdownQuestionSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
