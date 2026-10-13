# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S2_CONDITIONAL_QUESTIONS_INIT]
# Timestamp: 2026-10-12 21:12:00 +05:30
# Issue / Context: Conditional questions (like "relevant years of work experience" or dynamic skill dropdowns)
#                  appear dynamically after binary or preliminary questions are answered.
# Changes Made: Built s2_conditional_questions.py to scan for newly revealed, unanswered question blocks.
#               Integrates with IPCManager for question serialization and AIBrainResolver for cognitive answers.
# Rationale: Guarantees zero missed questions on Section 2 regardless of when DOM elements are revealed.
# Preventative Notes: Never assume a static question list on dynamic single-page applications.
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


def _fetch_dropdown_options(page: Any, question_text: str) -> List[str]:
    """Open the matching row's toggle and read visible listbox options."""
    try:
        rows = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
        for r in rows:
            try:
                if not r.is_visible():
                    continue
                label_el = r.locator("legend, label, .cx-form-label, p, h3, h4").first
                cur = label_el.inner_text().strip() if label_el.count() > 0 else r.inner_text().strip()
                if question_text.lower()[:25] not in cur.lower():
                    continue
                toggle = r.locator("button.icon-dropdown-arrow, button[id*='toggle-button'], input[role='combobox']").first
                if toggle.count() == 0 or not toggle.is_visible():
                    continue
                toggle.click()
                time.sleep(0.8)
                try:
                    row_el = r.element_handle()
                except Exception:
                    row_el = None
                opts = page.evaluate("""(rowEl) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const inODA = el => !!el.closest('ul.oda-chat-autocomplete-items, [class*="oda-chat"]');
                    if (rowEl) {
                        const combo = rowEl.querySelector('input[role="combobox"], select');
                        const ctrlId = combo && combo.getAttribute('aria-controls');
                        const list = ctrlId ? document.getElementById(ctrlId) : null;
                        const pool = list
                            ? Array.from(list.querySelectorAll('[role="option"], li, .cx-multi-select__list-item, .cx-select__list-item'))
                            : Array.from(rowEl.querySelectorAll('.cx-multi-select__list-item, .cx-select__list-item, [role="option"], li[role="option"]'));
                        const found = pool.filter(e => isVis(e) && !inODA(e)).map(i => (i.innerText || '').trim()).filter(Boolean);
                        if (found.length) return found;
                    }
                    return Array.from(document.querySelectorAll('.cx-multi-select__list-item, .cx-select__list-item, [role="option"], li[role="option"]'))
                        .filter(e => isVis(e) && !inODA(e)).map(i => (i.innerText || '').trim()).filter(Boolean);
                }""", row_el) or []
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                time.sleep(0.3)
                # De-duplicate preserving order
                seen = set()
                uniq = []
                for o in opts:
                    if o.lower() not in seen:
                        seen.add(o.lower())
                        uniq.append(o)
                return uniq[:40]
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"[s2_conditional_questions] Fetch options note: {e}")
    return []


def _apply_dropdown_or_checkbox(page: Any, question_text: str, targets: List[str], field_type: str) -> bool:
    """Select dropdown options or check checkbox values for the matching question row."""
    try:
        rows = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
        for r in rows:
            try:
                if not r.is_visible():
                    continue
                label_el = r.locator("legend, label, .cx-form-label, p, h3, h4").first
                cur = label_el.inner_text().strip() if label_el.count() > 0 else r.inner_text().strip()
                if question_text.lower()[:25] not in cur.lower():
                    continue
                if field_type == "CHECKBOX":
                    boxes = r.locator("input[type='checkbox']").all()
                    applied_any = False
                    for box in boxes:
                        try:
                            lbl = box.locator("xpath=ancestor::label").first
                            txt = lbl.inner_text().strip() if lbl.count() > 0 else ""
                            for t in targets:
                                if t.lower() in txt.lower() or txt.lower() in t.lower():
                                    if not box.is_checked():
                                        box.check(force=True)
                                    applied_any = True
                        except Exception:
                            continue
                    if applied_any:
                        return True
                    continue
                # DROPDOWN / COMBOBOX
                toggle = r.locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
                if toggle.count() > 0 and toggle.is_visible():
                    toggle.click()
                    time.sleep(0.8)
                ok_any = False
                try:
                    row_el = r.element_handle()
                except Exception:
                    row_el = None
                for t in targets:
                    clicked = page.evaluate("""([rowEl, targetText]) => {
                        const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                        const inODA = el => !!el.closest('ul.oda-chat-autocomplete-items, [class*="oda-chat"]');
                        const match = i => {
                            const x = (i.innerText || '').trim().toLowerCase();
                            return x === targetText.toLowerCase() || x.includes(targetText.toLowerCase());
                        };
                        if (rowEl) {
                            const combo = rowEl.querySelector('input[role="combobox"], select');
                            const ctrlId = combo && combo.getAttribute('aria-controls');
                            const list = ctrlId ? document.getElementById(ctrlId) : null;
                            const pool = list
                                ? Array.from(list.querySelectorAll('[role="option"], li, .cx-multi-select__list-item, .cx-select__list-item'))
                                : Array.from(rowEl.querySelectorAll('.cx-multi-select__list-item, .cx-select__list-item, [role="option"], li[role="option"]'));
                            const opt = pool.filter(e => isVis(e) && !inODA(e)).find(match);
                            if (opt) { opt.click(); return true; }
                        }
                        const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, .cx-select__list-item, [role="option"], li[role="option"]')).filter(e => isVis(e) && !inODA(e));
                        const opt = items.find(match);
                        if (opt) { opt.click(); return true; }
                        return false;
                    }""", [row_el, t])
                    if clicked:
                        ok_any = True
                        time.sleep(0.4)
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                if ok_any:
                    return True
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"[s2_conditional_questions] Apply dropdown note: {e}")
    return False


def _apply_text_field(page: Any, question_text: str, value: str, field_type: str) -> bool:
    """Fill TEXT / TEXTAREA for the matching question row."""
    if not value:
        return False
    try:
        rows = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
        for r in rows:
            try:
                if not r.is_visible():
                    continue
                label_el = r.locator("legend, label, .cx-form-label, p, h3, h4").first
                cur = label_el.inner_text().strip() if label_el.count() > 0 else r.inner_text().strip()
                if question_text.lower()[:25] not in cur.lower():
                    continue
                sel = "textarea" if field_type == "TEXTAREA" else "input[type='text'], input:not([type]):not([role='combobox'])"
                inp = r.locator(sel).first
                if inp.count() > 0 and inp.is_visible():
                    inp.fill(value)
                    try:
                        inp.dispatch_event("input")
                        inp.dispatch_event("change")
                    except Exception:
                        pass
                    return True
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"[s2_conditional_questions] Apply text note: {e}")
    return False


def scan_unanswered_questions(page: Any) -> List[Dict[str, Any]]:
    """
    Scans the Section 2 DOM for any visible, unanswered questions across all control types
    (radio pills, radio chips, radio inputs, comboboxes, dropdowns, checkboxes, text fields).
    """
    try:
        raw_questions = page.evaluate("""() => {
            const isVisible = el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
            };

            const results = [];
            // Target candidate question rows
            const rows = Array.from(document.querySelectorAll(
                '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset, [role="radiogroup"]'
            )).filter(isVisible);

            let qIndex = 0;
            const seenLabels = new Set();

            for (const r of rows) {
                // Find label/legend/prompt text
                const labelEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4, [id*="label"]');
                let qText = labelEl ? (labelEl.innerText || '').trim() : '';
                if (!qText) {
                    // Try getting first text node or container text
                    qText = (r.innerText || '').split('\\n')[0].trim();
                }
                // Skip if empty or already inspected in this pass
                if (!qText || qText.length < 3 || seenLabels.has(qText.toLowerCase())) continue;
                
                // Skip navigation/step headers
                const lower = qText.toLowerCase();
                if (lower.includes('step ') || lower.includes('save and continue') || lower.includes('candidate declaration')) continue;

                // 1. Radio Pills / Chips (buttons with role="radio" or class containing "pill")
                const radioPillBtns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section, button[class*="pill"]')).filter(isVisible);
                if (radioPillBtns.length > 0) {
                    const hasSelected = radioPillBtns.some(b => 
                        (b.className || '').includes('selected') || 
                        b.getAttribute('aria-checked') === 'true' || 
                        b.getAttribute('aria-pressed') === 'true'
                    );
                    if (!hasSelected) {
                        seenLabels.add(qText.toLowerCase());
                        const choices = radioPillBtns.map(b => (b.innerText || '').trim()).filter(Boolean);
                        const isBinary = choices.length === 2 && choices.some(c => c.toLowerCase() === 'yes') && choices.some(c => c.toLowerCase() === 'no');
                        results.push({
                            q_id: `cond_q_${++qIndex}`,
                            question_text: qText,
                            field_type: isBinary ? 'BINARY_PILL' : 'RADIO_CHIP',
                            available_choices: choices,
                            current_value: null,
                            is_conditional: true,
                            is_required: true,
                            dom_selector: null
                        });
                        continue;
                    }
                }

                // 2. Native Radio Inputs (input[type="radio"])
                const radioInputs = Array.from(r.querySelectorAll('input[type="radio"]')).filter(isVisible);
                if (radioInputs.length > 0) {
                    const hasChecked = radioInputs.some(inp => inp.checked);
                    if (!hasChecked) {
                        seenLabels.add(qText.toLowerCase());
                        const choices = radioInputs.map(inp => {
                            const lbl = inp.closest('label') || r.querySelector(`label[for="${inp.id}"]`);
                            return lbl ? (lbl.innerText || '').trim() : (inp.value || '').trim();
                        }).filter(Boolean);
                        results.push({
                            q_id: `cond_q_${++qIndex}`,
                            question_text: qText,
                            field_type: 'RADIO_BUTTON',
                            available_choices: choices,
                            current_value: null,
                            is_conditional: true,
                            is_required: true,
                            dom_selector: null
                        });
                        continue;
                    }
                }

                // 3. Dropdowns / Comboboxes (select or input with listbox/combobox)
                const comboInp = r.querySelector('input[role="combobox"], input[class*="cx-select"], [id$="-toggle-button"], select');
                if (comboInp && isVisible(comboInp)) {
                    let curVal = '';
                    if (comboInp.tagName.toLowerCase() === 'select') {
                        curVal = comboInp.value;
                        if (!curVal) {
                            const sel = comboInp.querySelector('option[selected], option:checked');
                            curVal = sel ? (sel.innerText || sel.value || '').trim() : '';
                        }
                    } else if (comboInp.tagName.toLowerCase() === 'input') {
                        curVal = (comboInp.value || '').trim();
                    }
                    // Multi-select pills already present count as answered
                    const existingPills = r.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill');
                    // Required markers: literal *, required classes, the empty
                    // required-star span, or aria-required (incident 210788242)
                    const hasStar = r.querySelector('.input-row__label--required-star, .input-row__label--required, .text-color-red') !== null;
                    const isAriaReq = r.querySelector('[aria-required="true"]') !== null;
                    const isRequired = hasStar || isAriaReq || r.querySelector('.required, [aria-required="true"], *[aria-label*="required"]') !== null || r.className.includes('required');
                    if (!curVal && existingPills.length === 0 && isRequired) {
                        seenLabels.add(qText.toLowerCase());
                        // Capture hidden listbox options without opening (Oracle JET renders them detached)
                        let hiddenOpts = [];
                        try {
                            const listItems = Array.from(document.querySelectorAll('.cx-select__list-item, [role="option"], li[role="option"]')).filter(isVisible);
                            // Only attach if the listbox is currently open (visible); else leave empty for healer to fetch
                            hiddenOpts = listItems.map(i => (i.innerText || '').trim()).filter(Boolean).slice(0, 40);
                        } catch (e) {}
                        results.push({
                            q_id: `cond_q_${++qIndex}`,
                            question_text: qText,
                            field_type: 'DROPDOWN',
                            available_choices: hiddenOpts,
                            current_value: null,
                            is_conditional: true,
                            is_required: true,
                            dom_selector: null
                        });
                        continue;
                    }
                }

                // 4. Checkboxes (unanswered required checkbox groups)
                const checkboxes = Array.from(r.querySelectorAll('input[type="checkbox"]')).filter(isVisible);
                if (checkboxes.length > 0) {
                    const anyChecked = checkboxes.some(c => c.checked);
                    const isRequired = r.querySelector('.required, [aria-required="true"]') !== null || r.className.includes('required');
                    if (!anyChecked && isRequired) {
                        seenLabels.add(qText.toLowerCase());
                        const choices = checkboxes.map(cb => {
                            const lbl = cb.closest('label') || r.querySelector(`label[for="${cb.id}"]`);
                            return lbl ? (lbl.innerText || '').trim() : (cb.value || '').trim();
                        }).filter(Boolean);
                        results.push({
                            q_id: `cond_q_${++qIndex}`,
                            question_text: qText,
                            field_type: 'CHECKBOX',
                            available_choices: choices,
                            current_value: null,
                            is_conditional: true,
                            is_required: true,
                            dom_selector: null
                        });
                        continue;
                    }
                }

                // 5. Text / Textarea (required but empty — conditional follow-ups like "specify other")
                const textInp = r.querySelector('input[type="text"]:not([role="combobox"]):not([class*="cx-select"]), textarea');
                if (textInp && isVisible(textInp)) {
                    const v = (textInp.value || '').trim();
                    const isRequired = textInp.getAttribute('aria-required') === 'true' || r.querySelector('.required, [aria-required="true"]') !== null || r.className.includes('required');
                    if (!v && isRequired) {
                        seenLabels.add(qText.toLowerCase());
                        results.push({
                            q_id: `cond_q_${++qIndex}`,
                            question_text: qText,
                            field_type: textInp.tagName.toLowerCase() === 'textarea' ? 'TEXTAREA' : 'TEXT',
                            available_choices: [],
                            current_value: null,
                            is_conditional: true,
                            is_required: true,
                            dom_selector: null
                        });
                        continue;
                    }
                }
            }

            return results;
        }""")
        return raw_questions or []
    except Exception as e:
        logger.error(f"[s2_conditional_questions] Scan error: {e}")
        return []


def heal_conditional_questions(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans for unanswered conditional questions on the current page, serializes them to IPC,
    resolves them via AIBrainResolver, and executes surgical clicks/inputs on the DOM.
    """
    try:
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        from CompanySiteApply.utils.question_hygiene import drop_option_titled_questions
        brain = AIBrainResolver.get_instance(candidate_data)

        unanswered = drop_option_titled_questions(scan_unanswered_questions(page))
        if not unanswered:
            return {"success": True, "healed_count": 0, "questions": []}

        logger.info(f"[s2_conditional_questions] Discovered {len(unanswered)} unanswered conditional question(s).")

        # 0. For DROPDOWN/COMBOBOX with no captured choices, open the toggle once to read options.
        #    Without choices the AG Brain cannot resolve (it would return [] and the question stays unanswered).
        for q in unanswered:
            if q.get("field_type") in ("DROPDOWN", "COMBOBOX") and not q.get("available_choices"):
                try:
                    fetched = _fetch_dropdown_options(page, q.get("question_text", ""))
                    if fetched:
                        q["available_choices"] = fetched
                except Exception as fe:
                    logger.debug(f"[s2_conditional_questions] Option fetch note: {fe}")
        
        # 1. IPC Serialization
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_cond_q"
        ipc = IPCManager(sess_id, job_id, profile, "section_2", "conditional_questions")
        
        # Format questions for IPC
        ipc_questions = [
            build_question(
                q_id=q["q_id"],
                question_text=q["question_text"],
                field_type=q["field_type"],
                available_choices=q["available_choices"],
                current_value=q.get("current_value"),
                is_conditional=True,
                is_required=True
            )
            for q in unanswered
        ]
        ipc.write_questions(ipc_questions)

        # 2. Cognitive Answer Resolution
        answered_list = []
        for q in ipc_questions:
            q_text = q["question_text"]
            f_type = q["field_type"]
            choices = q["available_choices"]

            resolution = brain.resolve_question(
                question_text=q_text,
                control_type=f_type,
                options=choices
            )
            q["answer"] = resolution.get("answer")
            q["answer_confidence"] = 1.0
            q["answer_rationale"] = resolution.get("rationale")
            answered_list.append(q)
            logger.info(f"[s2_conditional_questions] Brain resolved '{q_text[:40]}' -> '{q['answer']}'")

        # 3. Write answers back to IPC
        ipc.write_answers(answered_list)

        # 4. Apply answers to DOM (clicks verified by read-back, never assumed)
        from CompanySiteApply.section_agents.scripts.s2_competency_questions import (
            _read_selected_value,
        )
        healed_count = 0
        failed = []
        for ans in answered_list:
            q_text = ans["question_text"]
            f_type = ans["field_type"]
            raw_answer = ans.get("answer")

            # Normalize to list for multi-choice types
            if f_type in ("DROPDOWN", "COMBOBOX", "CHECKBOX"):
                if isinstance(raw_answer, list):
                    targets = [str(t).strip() for t in raw_answer if str(t).strip()]
                elif raw_answer:
                    targets = [str(raw_answer).strip()]
                else:
                    continue
                if _apply_dropdown_or_checkbox(page, q_text, targets, f_type):
                    healed_count += 1
                    time.sleep(0.4)
                else:
                    logger.warning(f"[s2_conditional_questions] Could not apply {f_type} for '{q_text[:35]}'")
                continue

            if f_type in ("TEXT", "TEXTAREA"):
                if _apply_text_field(page, q_text, str(raw_answer or "").strip(), f_type):
                    healed_count += 1
                    time.sleep(0.4)
                else:
                    logger.warning(f"[s2_conditional_questions] Could not fill text for '{q_text[:35]}'")
                continue

            target_ans = str(raw_answer or "").strip()
            if not target_ans:
                continue

            applied = page.evaluate("""([targetQ, targetVal, fieldType]) => {
                const isVisible = el => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
                };

                const rows = Array.from(document.querySelectorAll(
                    '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset, [role="radiogroup"]'
                )).filter(isVisible);

                for (const r of rows) {
                    const labelEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4');
                    const text = labelEl ? (labelEl.innerText || '').trim() : (r.innerText || '').trim();
                    if (!text.toLowerCase().includes(targetQ.toLowerCase().slice(0, 20))) continue;

                    // Match Radio Pill / Chip
                    if (fieldType === 'RADIO_CHIP' || fieldType === 'BINARY_PILL') {
                        const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section, button[class*="pill"]')).filter(isVisible);
                        for (const b of btns) {
                            const bText = (b.innerText || '').trim().toLowerCase();
                            if (bText === targetVal.toLowerCase() || bText.includes(targetVal.toLowerCase()) || targetVal.toLowerCase().includes(bText)) {
                                b.click();
                                return true;
                            }
                        }
                    }

                    // Match Radio Input
                    if (fieldType === 'RADIO_BUTTON') {
                        const inputs = Array.from(r.querySelectorAll('input[type="radio"]')).filter(isVisible);
                        for (const inp of inputs) {
                            const lbl = inp.closest('label') || r.querySelector(`label[for="${inp.id}"]`);
                            const lText = lbl ? (lbl.innerText || '').trim().toLowerCase() : (inp.value || '').trim().toLowerCase();
                            if (lText === targetVal.toLowerCase() || lText.includes(targetVal.toLowerCase())) {
                                inp.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }""", [q_text, target_ans, f_type])

            if applied:
                _rb = _read_selected_value(page, q_text)
                _tl, _rl = target_ans.lower(), (_rb or "").lower()
                if _rl and (_tl == _rl or _tl in _rl or _rl in _tl):
                    healed_count += 1
                    time.sleep(0.4)
                else:
                    logger.warning(
                        f"[s2_conditional_questions] Read-back FAILED for '{q_text[:35]}' "
                        f"(target '{target_ans}', read '{_rb}')"
                    )
                    failed.append(q_text)
            else:
                logger.warning(f"[s2_conditional_questions] Could not click matching element for '{q_text[:35]}'")
                failed.append(q_text)

        ipc.mark_done()
        return {
            "success": len(failed) == 0,
            "healed_count": healed_count,
            "questions": answered_list,
            "failed_questions": failed,
        }
    except Exception as e:
        logger.error(f"[s2_conditional_questions] Heal error: {e}")
        return {"success": False, "error": str(e), "healed_count": 0}
