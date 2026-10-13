# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [BINARY_QUESTION_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:43:00 +05:30
# Issue / Context: Isolating binary Yes/No screening questions from technical dropdowns to prevent cross-contamination.
# Changes Made: Built BinaryQuestionSubAgent handling regulatory, background, age 18+, and employment authorization pills.
# Rationale: Guarantees grounded-truth resolution for binary decisions with zero hardcoding.
# Preventative Notes: Never default to guessing without profile/ground-truth fallback.
# ==============================================================================
# [ENTRY #002]
# Term: [PHASE4_BINARY_QUESTIONS_IPC_DELEGATION]
# Timestamp: 2026-10-12 21:32:00 +05:30
# Issue / Context: Section 2 Binary questions needed IPCManager serialization for auditability.
# Changes Made: Delegated heal() to s2_binary_questions.heal_binary_questions().
# Rationale: Enables subagent independence and IPC integration.
# Preventative Notes: Never bypass IPC serialization for active questions.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class BinaryQuestionSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Page 2 Binary (Yes/No) Regulatory & Screening Questions.
    Handles Age 18+, Work Authorization, Non-Compete, Former Employee, and Disciplinary history.
    """

    @property
    def section_name(self) -> str:
        return "binary_questions"

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
                for (const r of rows) {
                    if (r.offsetWidth === 0 && r.offsetHeight === 0) continue;
                    const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section'));
                    const isYesNo = btns.length === 2 && btns.some(b => b.innerText.trim().toLowerCase() === 'yes') && btns.some(b => b.innerText.trim().toLowerCase() === 'no');
                    if (!isYesNo) continue;
                    const hasSelected = btns.some(b => b.className.includes('selected') || b.getAttribute('aria-checked') === 'true' || b.getAttribute('aria-pressed') === 'true');
                    if (!hasSelected) {
                        const title = r.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || "Unknown Question";
                        missing.push(title);
                    }
                }
                return missing;
            }''')

            return {
                "is_valid": len(unanswered) == 0,
                "unanswered_binary_questions": unanswered
            }
        except Exception as e:
            logger.error(f"[BinaryQuestionSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from CompanySiteApply.section_agents.scripts.s2_binary_questions import heal_binary_questions
            from CompanySiteApply.ipc.ipc_manager import get_effective_session_id
            _sess = get_effective_session_id(candidate_data, None) or None
            res = heal_binary_questions(page, candidate_data, session_id=_sess)
            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "healed_count": res.get("healed_count", 0),
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[BinaryQuestionSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
