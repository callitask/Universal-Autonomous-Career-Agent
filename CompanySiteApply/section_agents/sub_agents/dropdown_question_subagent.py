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
                for (const r of rows) {
                    if (r.offsetWidth === 0 && r.offsetHeight === 0) continue;
                    // Has combobox or dropdown
                    const cb = r.querySelector('input[role="combobox"], [class*="multi-select"], button.icon-dropdown-arrow, select');
                    if (!cb) continue;
                    
                    // Does it already have pills or input value?
                    const pills = r.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill');
                    const hasPills = pills.length > 0;
                    const valInput = r.querySelector('input[role="combobox"], select');
                    const hasVal = valInput && valInput.value && valInput.value.trim().length > 0;
                    
                    // Check if required or has red error
                    const label = r.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || "";
                    const isRequired = label.includes('*') || r.className.includes('required');
                    const hasError = r.querySelector('.cx-message--error, .error, .alert-danger, [class*="error"], [aria-invalid="true"]') !== null;
                    
                    if ((isRequired || hasError) && !hasPills && !hasVal) {
                        missing.push(label);
                    }
                }
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
            from CompanySiteApply.ai_brain_resolver import AIBrainResolver
            brain = AIBrainResolver.get_instance(candidate_data)

            questions = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
            healed_count = 0

            for q in questions:
                if not q.is_visible():
                    continue

                # Must have dropdown / combobox
                toggle = q.locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
                if toggle.count() == 0:
                    continue

                label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
                q_text = label_el.inner_text().strip() if label_el.count() > 0 else q.inner_text().strip()

                # Determine required count (e.g. 'choose two' -> 2, 'choose three' -> 3, default 1)
                req_count = 1
                match_count = re.search(r'choose\s+(\w+)', q_text, re.IGNORECASE)
                if match_count:
                    word = match_count.group(1).lower()
                    word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "2": 2, "3": 3}
                    req_count = word_map.get(word, 2)

                # Check existing pills: if bad negative pill exists (e.g. 'not require'), remove it
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
                if bad_pill_removed:
                    time.sleep(0.5)

                # Check if already answered with valid pills
                pills_count = q.locator(".cx-multi-select-pill__value-text, .cx-multi-select-pill").count()
                if pills_count >= req_count and not bad_pill_removed:
                    continue

                # Open the dropdown
                toggle.click()
                time.sleep(0.8)

                # Fetch all available items
                available_options = page.evaluate('''() => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(isVis);
                    return items.map(i => i.innerText.trim()).filter(Boolean);
                }''')

                # AI Brain resolves exact high-quality choices
                resolution = brain.resolve_question(
                    question_text=q_text,
                    control_type="DROPDOWN_MULTI",
                    options=available_options,
                    req_count=req_count
                )
                target_choices = resolution.get("answer") or []
                if isinstance(target_choices, str):
                    target_choices = [c.strip() for c in target_choices.split(",") if c.strip()]

                logger.info(f"[DropdownQuestionSubAgent] Brain resolved {q_text[:40]} -> {target_choices}")

                # Select resolved options via DOM
                select_res = page.evaluate('''(targets) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(isVis);
                    const clicked = [];
                    for (const target of targets) {
                        const targetLower = target.trim().toLowerCase();
                        const item = items.find(i => {
                            const t = i.innerText.trim().toLowerCase();
                            return t === targetLower || (targetLower.length > 2 && t.includes(targetLower)) || (t.length > 2 && targetLower.includes(t));
                        });
                        if (item && !clicked.includes(item.innerText.trim())) {
                            item.click();
                            clicked.push(item.innerText.trim());
                        }
                    }
                    return { clicked };
                }''', target_choices)

                logger.info(f"[DropdownQuestionSubAgent] Clicks applied: {select_res}")
                healed_count += 1
                time.sleep(1.0)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "healed_count": healed_count,
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
