# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S2_DROPDOWN_QUESTIONS_IPC_INIT]
# Timestamp: 2026-10-12 21:28:00 +05:30
# Issue / Context: Section 2 Dropdown & multi-select combobox questions (e.g. programming languages, tools)
#                  needed isolated IPC handshake and cognitive resolution.
# Changes Made: Built s2_dropdown_questions.py encapsulating DOM discovery, IPCManager serialization,
#               AIBrainResolver resolution, and list-item click actuation.
# Rationale: Guarantees section/subsection independence and decoupling between AG Brain and DOM scripts.
# Preventative Notes: Never hardcode skills or programming languages; match dynamically from profile.
# ==============================================================================

import re
import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    build_question,
    get_effective_session_id,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
)

logger = logging.getLogger(__name__)


def heal_dropdown_questions(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans for unanswered dropdown and multi-select combobox questions, writes to IPCManager,
    resolves choices via AIBrainResolver, and selects them on the DOM.
    """
    try:
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        brain = AIBrainResolver.get_instance(candidate_data)

        questions = page.locator(
            ".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block'], fieldset"
        ).all()
        healed_count = 0
        resolved_records = []

        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_drop_q"
        ipc = IPCManager(sess_id, job_id, profile, "section_2", "dropdown_questions")

        # Phase 1 — discovery + option fetch (open → read → close per row).
        pending: list = []
        for q in questions:
            if not q.is_visible():
                continue

            # Must have dropdown / combobox toggle
            toggle = q.locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
            if toggle.count() == 0:
                continue

            label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
            q_text = label_el.inner_text().strip() if label_el.count() > 0 else q.inner_text().strip()

            # Determine required count (e.g. 'choose two' -> 2)
            req_count = 1
            match_count = re.search(r'choose\s+(\w+)', q_text, re.IGNORECASE)
            if match_count:
                word = match_count.group(1).lower()
                word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "2": 2, "3": 3}
                req_count = word_map.get(word, 2)

            # Check if negative non-coding pill exists for tech candidate and remove it
            is_tech = brain.knowledge_index.get("is_tech_candidate", True)
            bad_pill_removed = False
            if is_tech:
                try:
                    bad_pill_removed = page.evaluate('''(el) => {
                        const pills = Array.from(el.querySelectorAll('.cx-multi-select-pill, .cx-multi-select-pill__value-text'));
                        let removed = false;
                        for (const p of pills) {
                            const txt = p.innerText.toLowerCase();
                            if (txt.includes('not require') || txt.includes('not hands-on')) {
                                const btn = p.querySelector('button, [aria-label*="Remove"]') || p.parentElement.querySelector('button, [aria-label*="Remove"]');
                                if (btn) { btn.click(); removed = true; }
                            }
                        }
                        return removed;
                    }''', q.element_handle())
                except Exception:
                    bad_pill_removed = False
                if bad_pill_removed:
                    time.sleep(0.5)

            # Check if already answered with valid pills
            pills_count = q.locator(".cx-multi-select-pill__value-text, .cx-multi-select-pill").count()
            if pills_count >= req_count and not bad_pill_removed:
                continue

            # Open the dropdown to inspect options (listbox scoped to this row
            # via aria-controls; global queries collide with Section 1/4
            # toggles and the ODA chatbot listbox — incident 210788242)
            toggle.click()
            time.sleep(0.8)

            available_options = q.evaluate("""(rowEl) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const inODA = el => !!el.closest('ul.oda-chat-autocomplete-items, [class*="oda-chat"]');
                const combo = rowEl.querySelector('input[role="combobox"], select');
                const ctrlId = combo && combo.getAttribute('aria-controls');
                let list = ctrlId ? document.getElementById(ctrlId) : null;
                let items = [];
                if (list) {
                    items = Array.from(list.querySelectorAll('[role="option"], li, .cx-multi-select__list-item')).filter(e => isVis(e) && !inODA(e));
                }
                if (!items.length) {
                    items = Array.from(rowEl.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(e => isVis(e) && !inODA(e));
                }
                if (!items.length) {
                    items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(e => isVis(e) && !inODA(e));
                }
                return items.map(i => i.innerText.trim()).filter(Boolean);
            }""") or []
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            time.sleep(0.3)

            pending.append({"q_text": q_text, "req_count": req_count, "options": available_options})

        if not pending:
            ipc.mark_done()
            return {"success": True, "healed_count": 0, "questions": []}

        # Phase 2 — single IPC batch (no per-question overwrite; full audit trail in one file).
        ipc_questions = [
            build_question(
                q_id=f"drop_q_{i + 1}",
                question_text=p["q_text"],
                field_type="DROPDOWN_MULTI",
                available_choices=p["options"],
                current_value=None,
                is_conditional=False,
                is_required=True
            )
            for i, p in enumerate(pending)
        ]
        ipc.write_questions(ipc_questions)

        resolved_records = []
        for ipc_q, p in zip(ipc_questions, pending):
            # 2. Cognitive Answer Resolution
            resolution = brain.resolve_question(
                question_text=p["q_text"],
                control_type="DROPDOWN_MULTI",
                options=p["options"],
                req_count=p["req_count"]
            )
            target_choices = resolution.get("answer") or []
            if isinstance(target_choices, str):
                target_choices = [target_choices]

            ipc_q["answer"] = target_choices
            ipc_q["answer_confidence"] = 1.0
            ipc_q["answer_rationale"] = resolution.get("rationale")
            resolved_records.append(ipc_q)

            logger.info(f"[s2_dropdown_questions] Brain resolved '{p['q_text'][:35]}' -> {target_choices}")

        ipc.write_answers(resolved_records)

        # Phase 3 — actuation (re-open each row, click choices, close).
        healed_count = 0
        for rec in resolved_records:
            q_text = rec["question_text"]
            target_choices = rec.get("answer") or []
            # Re-locate the row and re-open before clicking (listbox was closed after fetch).
            rows = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
            target_row = None
            for r in rows:
                try:
                    if not r.is_visible():
                        continue
                    lbl = r.locator("legend, label, .cx-form-label, p, h3, h4").first
                    cur = lbl.inner_text().strip() if lbl.count() > 0 else r.inner_text().strip()
                    if q_text.lower()[:25] in cur.lower():
                        target_row = r
                        break
                except Exception:
                    continue
            if target_row is None:
                continue
            try:
                tgl = target_row.locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
                if tgl.count() > 0 and tgl.is_visible():
                    tgl.click()
                    time.sleep(0.8)
            except Exception:
                pass
            for choice in target_choices:
                try:
                    row_el = target_row.element_handle()
                except Exception:
                    row_el = None
                clicked = page.evaluate('''([rowEl, targetText]) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const inODA = el => !!el.closest('ul.oda-chat-autocomplete-items, [class*="oda-chat"]');
                    const match = i => {
                        const t = (i.innerText || '').trim().toLowerCase();
                        return t === targetText.toLowerCase() || t.includes(targetText.toLowerCase());
                    };
                    // 1. Row-scoped listbox via aria-controls (bypasses SPA + ODA collisions)
                    if (rowEl) {
                        const combo = rowEl.querySelector('input[role="combobox"], select');
                        const ctrlId = combo && combo.getAttribute('aria-controls');
                        const list = ctrlId ? document.getElementById(ctrlId) : null;
                        const pool = list
                            ? Array.from(list.querySelectorAll('[role="option"], li, .cx-multi-select__list-item'))
                            : Array.from(rowEl.querySelectorAll('.cx-multi-select__list-item, [role="option"]'));
                        const opt = pool.filter(e => isVis(e) && !inODA(e)).find(match);
                        if (opt) { opt.click(); return true; }
                    }
                    // 2. Global fallback excluding the chatbot overlay
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(e => isVis(e) && !inODA(e));
                    const opt = items.find(match);
                    if (opt) {
                        opt.click();
                        return true;
                    }
                    return false;
                }''', [row_el, choice])
                if clicked:
                    time.sleep(0.4)

            # Close dropdown if open
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            time.sleep(0.5)
            healed_count += 1

        ipc.mark_done()
        return {
            "success": True,
            "healed_count": healed_count,
            "questions": resolved_records
        }
    except Exception as e:
        logger.error(f"[s2_dropdown_questions] Heal error: {e}")
        return {"success": False, "error": str(e), "healed_count": 0}
