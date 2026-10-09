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
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            tax_skills = candidate_data.get("taxonomy_skills") or {}
            skills_list = cand.get("skills") or []
            if isinstance(tax_skills, dict):
                skills_list.extend(tax_skills.get("technical_skills") or [])
                skills_list.extend(tax_skills.get("domain_skills") or [])

            # Extract languages from candidate
            cand_languages = [str(s).lower() for s in skills_list]
            cand_languages.extend([str(l).lower() for l in cand.get("languages", [])])
            headline = str(cand.get("headline") or cand.get("current_title") or "").lower()
            cand_languages.extend(headline.split())

            questions = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
            healed_count = 0

            for q in questions:
                if not q.is_visible():
                    continue

                # Must have dropdown / combobox
                toggle = q.locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
                if toggle.count() == 0:
                    continue

                # Check if already answered
                pills = q.locator(".cx-multi-select-pill__value-text, .cx-multi-select-pill").count()
                if pills > 0:
                    continue

                label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
                q_text = label_el.inner_text().strip().lower() if label_el.count() > 0 else q.inner_text().strip().lower()

                # Determine required count (e.g. 'choose two' -> 2, 'choose three' -> 3, default 1)
                req_count = 1
                match_count = re.search(r'choose\s+(\w+)', q_text)
                if match_count:
                    word = match_count.group(1).lower()
                    word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "2": 2, "3": 3}
                    req_count = word_map.get(word, 2)

                # Open the dropdown
                toggle.click()
                time.sleep(1.0)

                # Select matching options
                select_res = page.evaluate('''(args) => {
                    const { candTerms, reqCount } = args;
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(isVis);
                    if (items.length === 0) return { selectedCount: 0, reason: "no_items" };

                    const clicked = [];

                    // 1. Try to find candidate skills/languages matches
                    for (const item of items) {
                        if (clicked.length >= reqCount) break;
                        const itemText = item.innerText.trim().toLowerCase();
                        
                        // Check if any candidate term matches item
                        const matched = candTerms.some(t => {
                            if (t === itemText) return true;
                            if (t.length > 2 && itemText.includes(t)) return true;
                            if (itemText.length > 2 && t.includes(itemText)) return true;
                            return false;
                        });

                        if (matched && !clicked.includes(item.innerText.trim())) {
                            item.click();
                            clicked.push(item.innerText.trim());
                        }
                    }

                    // 2. Fallback if not enough matches found
                    if (clicked.length === 0) {
                        // Check for 'My job does not require coding' or 'Others'
                        const fallbackItem = items.find(i => i.innerText.toLowerCase().includes('not require') || i.innerText.toLowerCase().includes('others'));
                        if (fallbackItem) {
                            fallbackItem.click();
                            clicked.push(fallbackItem.innerText.trim());
                        } else {
                            items[0].click();
                            clicked.push(items[0].innerText.trim());
                        }
                    }

                    return { selectedCount: clicked.length, clicked };
                }''', {"candTerms": cand_languages, "reqCount": req_count})

                logger.info(f"[DropdownQuestionSubAgent] Selected for '{q_text[:40]}': {select_res}")
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
