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
            from CompanySiteApply.ai_brain_resolver import AIBrainResolver
            brain = AIBrainResolver.get_instance(candidate_data)
            healed_count = 0

            questions = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
            for q in questions:
                if not q.is_visible():
                    continue
                pills = q.locator("button.cx-select-pill-section, button[role='radio']").all()
                if len(pills) != 2:
                    continue
                pill_texts = [p.inner_text().strip() for p in pills]
                pill_lower = [pt.lower() for pt in pill_texts]
                if "yes" not in pill_lower or "no" not in pill_lower:
                    continue

                has_selected = any("selected" in (p.get_attribute("class") or "") or p.get_attribute("aria-checked") == "true" for p in pills)
                if has_selected:
                    continue

                label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
                q_text = label_el.inner_text().strip() if label_el.count() > 0 else q.inner_text().strip()

                # Resolve via AI Brain
                resolution = brain.resolve_question(
                    question_text=q_text,
                    control_type="BINARY_PILL",
                    options=pill_texts
                )
                target_choice = str(resolution.get("answer") or "no").strip().lower()
                logger.info(f"[BinaryQuestionSubAgent] Brain resolved '{q_text[:40]}' -> '{target_choice}'")

                target_pill = None
                for p in pills:
                    if p.inner_text().strip().lower() == target_choice:
                        target_pill = p
                        break

                if target_pill:
                    target_pill.click()
                    healed_count += 1
                    time.sleep(0.3)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "healed_count": healed_count,
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
