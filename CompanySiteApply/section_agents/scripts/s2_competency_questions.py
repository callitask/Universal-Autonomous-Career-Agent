# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S2_COMPETENCY_QUESTIONS_IPC_INIT]
# Timestamp: 2026-10-12 21:23:00 +05:30
# Issue / Context: Section 2 Competency pills (experience tiers, domain, specialization, proficiency)
#                  needed isolated IPC handshake and cognitive resolution.
# Changes Made: Built s2_competency_questions.py encapsulating DOM discovery, IPCManager serialization,
#               AIBrainResolver resolution, and DOM pill click actuation.
# Rationale: Guarantees section/subsection independence and decoupling between AG Brain and DOM scripts.
# Preventative Notes: Never hardcode years of experience, skill names, or proficiency levels.
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


def scan_competency_questions(page: Any) -> List[Dict[str, Any]]:
    """Scans Section 2 for unanswered technical competency questions.

    Covers pill buttons (3-15 options) AND Oracle JET / native radio groups
    (oj-radiogroup, role=radiogroup, input[type=radio]) — the latter render as
    plain option lists (e.g. primary-area-of-expertise, AWS proficiency) that
    pill-only scans miss while Oracle flags "This information is required."
    """
    try:
        return page.evaluate("""() => {
            const isVisible = el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
            };
            const optText = el => (el.innerText || el.textContent || el.value || '').trim();

            const rows = Array.from(document.querySelectorAll(
                '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset, [role="radiogroup"], oj-radiogroup'
            )).filter(isVisible);

            const missing = [];
            let idx = 0;
            const seen = new Set();

            const pushOnce = (title, fieldType, choices) => {
                const key = (title || '').toLowerCase();
                if (!title || title.length < 3 || seen.has(key)) return;
                seen.add(key);
                missing.push({
                    q_id: `comp_q_${++idx}`,
                    question_text: title,
                    field_type: fieldType,
                    available_choices: choices,
                    current_value: null,
                    is_conditional: false,
                    is_required: true
                });
            };

            const rowTitle = r => {
                const titleEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4');
                return titleEl ? titleEl.innerText.trim() : (r.innerText || '').split('\\n')[0].trim();
            };

            for (const r of rows) {
                // 1. Pill buttons (3-15 options, single select)
                const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section')).filter(isVisible);
                if (btns.length > 2 && btns.length <= 15) {
                    const hasSelected = btns.some(b =>
                        b.className.includes('selected') ||
                        b.getAttribute('aria-checked') === 'true' ||
                        b.getAttribute('aria-pressed') === 'true'
                    );
                    if (!hasSelected) {
                        pushOnce(rowTitle(r) || "Competency Question", 'RADIO_PILL', btns.map(optText).filter(Boolean));
                    }
                    continue;
                }

                // 2. Oracle JET / native radio groups (oj-option, role=radio, input[type=radio])
                const jetOpts = Array.from(r.querySelectorAll('oj-option, [role="radio"], input[type="radio"]')).filter(isVisible);
                if (jetOpts.length >= 2) {
                    const hasSelected = jetOpts.some(o =>
                        (o.getAttribute && (o.getAttribute('aria-checked') === 'true' || o.getAttribute('aria-selected') === 'true')) ||
                        (o.checked === true) ||
                        (o.className && o.className.includes('selected'))
                    );
                    if (!hasSelected) {
                        pushOnce(rowTitle(r) || "Competency Question", 'RADIO_BUTTON', jetOpts.map(optText).filter(Boolean));
                    }
                }
            }
            return missing;
        }""") or []
    except Exception as e:
        logger.error(f"[s2_competency_questions] Scan error: {e}")
        return []


def scan_competency_rows(page: Any) -> List[Dict[str, Any]]:
    """Scan ALL competency pill/radio rows with their current selections.

    Incident 210788242: the tier group showed a selection ("No Prior
    Experience") that contradicted profile truth. Unanswered-only scans never
    revisit answered rows, so a wrong pick survives forever. Audits must
    compare read-back against brain truth, not just emptiness.
    """
    try:
        return page.evaluate("""() => {
            const isVisible = el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
            };
            const optText = el => (el.innerText || el.textContent || el.value || '').trim();
            const rows = Array.from(document.querySelectorAll(
                '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset, [role="radiogroup"], oj-radiogroup'
            )).filter(isVisible);
            const out = [];
            const rowTitle = r => {
                const titleEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4');
                return titleEl ? titleEl.innerText.trim() : (r.innerText || '').split('\\n')[0].trim();
            };
            for (const r of rows) {
                const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section')).filter(isVisible);
                const jet = Array.from(r.querySelectorAll('oj-option, [role="radio"], input[type="radio"]')).filter(isVisible);
                const opts = (btns.length > 2 && btns.length <= 15) ? btns : (jet.length >= 2 ? jet : []);
                if (!opts.length) continue;
                const sel = opts.find(o =>
                    (o.getAttribute && (o.getAttribute('aria-checked') === 'true' || o.getAttribute('aria-selected') === 'true' || o.getAttribute('aria-pressed') === 'true')) ||
                    (o.checked === true) ||
                    ((o.className || '').includes('selected'))
                );
                const title = rowTitle(r);
                if (!title || title.length < 3) continue;
                out.push({
                    question_text: title,
                    available_choices: opts.map(optText).filter(Boolean),
                    current_value: sel ? optText(sel) : null,
                });
            }
            return out;
        }""") or []
    except Exception as e:
        logger.error(f"[s2_competency_questions] Row scan error: {e}")
        return []


def _matching_row(questions_elements: List[Any], q_text: str) -> Optional[Any]:
    """Find the visible row whose label matches the question text."""
    for q in questions_elements:
        try:
            if not q.is_visible():
                continue
            label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
            cur = label_el.inner_text().strip() if label_el.count() > 0 else q.inner_text().strip()
            if q_text.lower()[:25] in cur.lower():
                return q
        except Exception:
            continue
    return None


def _apply_competency_answer(
    page: Any, questions_elements: List[Any], q_text: str, target_ans: str, f_type: str
) -> bool:
    """Click the matching option across pill buttons and JET/native radios."""
    row = _matching_row(questions_elements, q_text)
    if row is None:
        return False
    try:
        # 1. Pill buttons
        pills = row.locator("button.cx-select-pill-section, button[role='radio']").all()
        if 2 < len(pills) <= 15:
            for p in pills:
                try:
                    pt = p.inner_text().strip()
                except Exception:
                    continue
                if pt.lower() == target_ans.lower() or target_ans.lower() in pt.lower() or pt.lower() in target_ans.lower():
                    p.click()
                    time.sleep(0.4)
                    return True
        # 2. Oracle JET options / role=radios
        jet_opts = row.locator("oj-option, [role='radio']").all()
        for o in jet_opts:
            try:
                ot = (o.inner_text() or "").strip()
            except Exception:
                continue
            if ot.lower() == target_ans.lower() or target_ans.lower() in ot.lower():
                try:
                    o.click()
                except Exception:
                    try:
                        page.evaluate("(el) => el.click()", o.element_handle())
                    except Exception:
                        continue
                time.sleep(0.4)
                return True
        # 3. Native radio inputs (click associated label for JET state sync)
        radios = row.locator("input[type='radio']").all()
        for r in radios:
            try:
                lbl = r.locator("xpath=ancestor::label").first
                txt = lbl.inner_text().strip() if lbl.count() > 0 else str(r.get_attribute("value") or "")
            except Exception:
                continue
            if txt.lower() == target_ans.lower() or target_ans.lower() in txt.lower():
                try:
                    if lbl.count() > 0:
                        lbl.click()
                    else:
                        r.check(force=True)
                except Exception:
                    continue
                time.sleep(0.4)
                return True
    except Exception as e:
        logger.debug(f"[s2_competency_questions] Apply note for '{q_text[:35]}': {e}")
    return False


def _read_selected_value(page: Any, q_text: str) -> str:
    """Read back the currently selected option text for the question row.

    Returns "" when nothing is selected. This is the verification gate —
    a click Oracle JET ignored reads back empty.
    """
    try:
        return page.evaluate("""(targetQ) => {
            const isVisible = el => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && (el.offsetWidth > 0 || el.offsetHeight > 0);
            };
            const rows = Array.from(document.querySelectorAll(
                '.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset, [role="radiogroup"], oj-radiogroup'
            )).filter(isVisible);
            for (const r of rows) {
                const labelEl = r.querySelector('legend, label, .cx-form-label, p, h3, h4');
                const text = labelEl ? (labelEl.innerText || '').trim() : (r.innerText || '').trim();
                if (!text.toLowerCase().includes(targetQ.toLowerCase().slice(0, 25))) continue;
                const sel = r.querySelector('button.selected, button[aria-checked="true"], button[aria-pressed="true"], oj-option[selected], oj-option[aria-selected="true"], [role="radio"][aria-checked="true"], input[type="radio"]:checked');
                if (!sel) return '';
                if (sel.tagName.toLowerCase() === 'input') {
                    const lbl = sel.closest('label');
                    const forLbl = sel.id ? r.querySelector(`label[for="${sel.id}"]`) : null;
                    return ((lbl && lbl.innerText) || (forLbl && forLbl.innerText) || sel.value || '').trim();
                }
                return (sel.innerText || sel.textContent || '').trim();
            }
            return '';
        }""", q_text) or ""
    except Exception:
        return ""


def heal_competency_questions(
    page: Any,
    candidate_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans for unanswered competency questions, writes to IPCManager, resolves via AIBrainResolver,
    clicks target pills, and verifies DOM state.
    """
    try:
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        from CompanySiteApply.utils.question_hygiene import drop_option_titled_questions
        brain = AIBrainResolver.get_instance(candidate_data)

        unanswered = drop_option_titled_questions(scan_competency_questions(page))

        # 0b. Truth verification on answered rows (incident 210788242:
        # "No Prior Experience" sat selected for a 10-year candidate while the
        # unanswered-scan saw nothing to heal). A wrong pick is corrected,
        # not skipped.
        try:
            _rows = scan_competency_rows(page)
        except Exception:
            _rows = []
        for _row in _rows:
            _cur = (_row.get("current_value") or "").strip()
            if not _cur:
                continue
            _rtext = _row.get("question_text", "")
            if any(
                q.get("question_text", "").lower()[:25] in _rtext.lower()
                or _rtext.lower()[:25] in q.get("question_text", "").lower()
                for q in unanswered
            ):
                continue
            try:
                _res = brain.resolve_question(
                    question_text=_rtext,
                    control_type="RADIO_PILL",
                    options=_row.get("available_choices") or [],
                )
                _ans = str(_res.get("answer") or "").strip()
                _tl, _cl = _ans.lower(), _cur.lower()
                if _ans and not (_tl == _cl or _tl in _cl or _cl in _tl):
                    logger.warning(
                        f"[s2_competency_questions] Wrong pick detected: '{_rtext[:40]}' "
                        f"shows '{_cur}' but truth is '{_ans}' — re-healing."
                    )
                    unanswered.append({
                        "q_id": f"correction_{len(unanswered) + 1}",
                        "question_text": _rtext,
                        "field_type": "RADIO_PILL",
                        "available_choices": _row.get("available_choices") or [],
                        "current_value": _cur,
                        "is_conditional": False,
                        "is_required": True,
                    })
            except Exception as _ve:
                logger.debug(f"[s2_competency_questions] Truth-verify note: {_ve}")

        if not unanswered:
            return {"success": True, "healed_count": 0, "questions": []}

        logger.info(f"[s2_competency_questions] Discovered {len(unanswered)} unanswered competency question(s).")

        # 1. IPC Serialization
        job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
        profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
        sess_id = get_effective_session_id(candidate_data, session_id) or "sess_comp_q"
        ipc = IPCManager(sess_id, job_id, profile, "section_2", "competency_questions")

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
                control_type="RADIO_PILL",
                options=choices
            )
            target_ans = str(resolution.get("answer") or "").strip()
            q["answer"] = target_ans
            q["answer_confidence"] = 1.0
            q["answer_rationale"] = resolution.get("rationale")
            answered_list.append(q)
            logger.info(f"[s2_competency_questions] Brain resolved '{q_text[:40]}' -> '{target_ans}'")

        # 3. Write answers back to IPC
        ipc.write_answers(answered_list)

        # 4. Actuation on DOM with selected-value read-back.
        # A click that Oracle JET ignores must NOT count as healed.
        healed_count = 0
        failed = []
        questions_elements = page.locator(
            ".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block'], fieldset, [role='radiogroup'], oj-radiogroup"
        ).all()

        for ans in answered_list:
            q_text = ans["question_text"]
            f_type = ans.get("field_type", "RADIO_PILL")
            target_ans = str(ans.get("answer") or "").strip()
            if not target_ans:
                failed.append(q_text)
                continue

            applied = _apply_competency_answer(page, questions_elements, q_text, target_ans, f_type)
            readback = _read_selected_value(page, q_text)
            tl, rl = target_ans.lower(), (readback or "").lower()
            if applied and rl and (tl == rl or tl in rl or rl in tl):
                healed_count += 1
                time.sleep(0.3)
            else:
                logger.warning(f"[s2_competency_questions] Read-back FAILED for '{q_text[:40]}' (target '{target_ans}', read '{readback}')")
                failed.append(q_text)

        ipc.mark_done()
        return {
            "success": len(failed) == 0,
            "healed_count": healed_count,
            "questions": answered_list,
            "failed_questions": failed,
        }
    except Exception as e:
        logger.error(f"[s2_competency_questions] Heal error: {e}")
        return {"success": False, "error": str(e), "healed_count": 0}
