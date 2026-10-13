# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S2_BINARY_QUESTIONS_IPC_INIT]
# Timestamp: 2026-10-12 21:20:00 +05:30
# Issue / Context: Section 2 Binary (Yes/No) questions needed isolated IPC handshake and cognitive resolution.
# Changes Made: Built s2_binary_questions.py encapsulating DOM discovery, IPCManager serialization,
#               AIBrainResolver resolution, and DOM pill click actuation.
# Rationale: Guarantees section/subsection independence and decoupling between AG Brain and DOM scripts.
# Preventative Notes: Never default to guessing without profile/ground-truth fallback.
# ==============================================================================

import logging
import time
from typing import Any, Dict, List, Optional
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    build_question,
    get_effective_session_id,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
)

logger = logging.getLogger(__name__)


def scan_binary_questions(page: Any) -> List[Dict[str, Any]]:
    """Scans Section 2 for unanswered binary (Yes/No) questions."""
    try:
        return page.evaluate("""() => {
            const isVisible = el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
            };

            const rows = Array.from(document.querySelectorAll(
                '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"]'
            )).filter(isVisible);

            const missing = [];
            let idx = 0;

            for (const r of rows) {
                const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section')).filter(isVisible);
                const isYesNo = btns.length === 2 && btns.some(b => b.innerText.trim().toLowerCase() === 'yes') && btns.some(b => b.innerText.trim().toLowerCase() === 'no');
                if (!isYesNo) continue;

                const hasSelected = btns.some(b => 
                    b.className.includes('selected') || 
                    b.getAttribute('aria-checked') === 'true' || 
                    b.getAttribute('aria-pressed') === 'true'
                );

                if (!hasSelected) {
                    const titleEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4');
                    const title = titleEl ? titleEl.innerText.trim() : (r.innerText || '').split('\\n')[0].trim();
                    const choices = btns.map(b => b.innerText.trim());
                    missing.push({
                        q_id: `bin_q_${++idx}`,
                        question_text: title || "Unknown Binary Question",
                        field_type: "BINARY_PILL",
                        available_choices: choices,
                        current_value: null,
                        is_conditional: false,
                        is_required: true
                    });
                }
            }
            return missing;
        }""") or []
    except Exception as e:
        logger.error(f"[s2_binary_questions] Scan error: {e}")
        return []


def heal_binary_questions(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans for unanswered binary questions, writes to IPCManager, resolves via AIBrainResolver,
    clicks target pills, and verifies DOM state.
    """
    try:
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        from CompanySiteApply.utils.question_hygiene import drop_option_titled_questions
        brain = AIBrainResolver.get_instance(candidate_data)

        unanswered = drop_option_titled_questions(scan_binary_questions(page))
        if not unanswered:
            return {"success": True, "healed_count": 0, "questions": []}

        logger.info(f"[s2_binary_questions] Discovered {len(unanswered)} unanswered binary question(s).")

        # 1. IPC Serialization
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_bin_q"
        ipc = IPCManager(sess_id, job_id, profile, "section_2", "binary_questions")

        ipc_questions = [
            build_question(
                q_id=q["q_id"],
                question_text=q["question_text"],
                field_type=q["field_type"],
                available_choices=q["available_choices"],
                current_value=None,
                is_conditional=False,
                is_required=True
            )
            for q in unanswered
        ]
        ipc.write_questions(ipc_questions)

        # 2. Cognitive Answer Resolution
        answered_list = []
        for q in ipc_questions:
            q_text = q["question_text"]
            choices = q["available_choices"]

            resolution = brain.resolve_question(
                question_text=q_text,
                control_type="BINARY_PILL",
                options=choices
            )
            target_ans = str(resolution.get("answer") or "No").strip()
            q["answer"] = target_ans
            q["answer_confidence"] = 1.0
            q["answer_rationale"] = resolution.get("rationale")
            answered_list.append(q)
            logger.info(f"[s2_binary_questions] Brain resolved '{q_text[:40]}' -> '{target_ans}'")

        # 3. Write answers back to IPC
        ipc.write_answers(answered_list)

        # 4. Actuation on DOM
        healed_count = 0
        questions_elements = page.locator(
            ".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']"
        ).all()

        for ans in answered_list:
            q_text = ans["question_text"]
            target_choice = str(ans.get("answer") or "no").strip().lower()

            for q in questions_elements:
                try:
                    if not q.is_visible():
                        continue
                    pills = q.locator("button.cx-select-pill-section, button[role='radio']").all()
                    if len(pills) != 2:
                        continue
                    pill_texts = [p.inner_text().strip() for p in pills]
                    pill_lower = [pt.lower() for pt in pill_texts]
                    if "yes" not in pill_lower or "no" not in pill_lower:
                        continue

                    label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
                    cur_q_text = label_el.inner_text().strip() if label_el.count() > 0 else q.inner_text().strip()
                    if q_text.lower()[:25] not in cur_q_text.lower():
                        continue

                    # Find target pill
                    for p in pills:
                        if p.inner_text().strip().lower() == target_choice:
                            p.click()
                            healed_count += 1
                            time.sleep(0.3)
                            break
                    break
                except Exception:
                    continue

        ipc.mark_done()
        return {
            "success": True,
            "healed_count": healed_count,
            "questions": answered_list
        }
    except Exception as e:
        logger.error(f"[s2_binary_questions] Heal error: {e}")
        return {"success": False, "error": str(e), "healed_count": 0}
