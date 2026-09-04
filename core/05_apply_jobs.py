"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT: APPLICATION ENGINE
File: core/05_apply_jobs.py
Description: Full-lifecycle autonomous job application executor supporting:
             1. 1-Click apply verification (Naukri & LinkedIn)
             2. External redirect gating (saved_external_jobs.json)
             3. Reverse-engineered Naukri chatbot drawer solver (C9 & H5 compliant)
             4. Native LinkedIn Easy Apply multi-step modal solver
             5. Zero-API Antigravity 2.0 Cognitive IPC integration for Q&A
             6. Per-job audit logging (ques_ans_chatbot.json) and canonical tracker CSV.
================================================================================
"""

import sys
import os
import json
import csv
import time
import random
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.profile_context import ProfileContext
from core.utils.browser_manager import BrowserManager
from core.ai_client import AIClient


def human_jitter(min_ms: int = 150, max_ms: int = 400):
    time.sleep(random.randint(min_ms, max_ms) / 1000.0)


def log_section(title: str) -> None:
    print(f"\n{'=' * 80}", flush=True)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {title}", flush=True)
    print(f"{'=' * 80}", flush=True)


def log_step(category: str, message: str) -> None:
    print(f"[{category.upper():<14}] {message}", flush=True)


def log_substep(category: str, message: str) -> None:
    print(f"    [{category}] {message}", flush=True)


class ChatbotResolver:
    """
    DOM Chatbot Reverse-Engineering Engine for Naukri and platform modals.
    Implements Guardrails C7, C8, C9, H1, H2, H3, H5, H6.
    """
    CHIP_SELECTORS = (
        "div.radioItem, div.choiceChip, div.clickableChip, div.optionItem, "
        "div[class*='radioItem'], label[class*='radio'], ul.ChoiceList li, "
        "div[class*='chipItem'], button[class*='chip'], span[class*='chip'], "
        "button[class*='option'], li[class*='option'], div.customRadio, "
        ".chatbot_Choice, button.radio-button, span.radio-button, label.ssrc__label"
    )

    def __init__(self, page, ctx: ProfileContext, ai_client: AIClient):
        self.page = page
        self.ctx = ctx
        self.ai = ai_client
        self.config = getattr(ctx, "config", {})
        cand = self.config.get("candidate", {})
        
        self.candidate_name = getattr(ctx, "candidate_name", None) or cand.get("full_name") or cand.get("name") or ""
        self.first_name = getattr(ctx, "first_name", None) or (self.candidate_name.split()[0] if self.candidate_name else "")
        self.resume_text = getattr(ctx, "resume_text", "")

    def is_drawer_open(self) -> bool:
        drawer_selectors = [
            ".chatbot_DrawerContentWrapper",
            "div[class*='chatbot_Drawer']",
            "div[class*='_chatbotContainer']",
            "div[class*='chatbot_MessageContainer']",
            "div[id*='Messages']"
        ]
        for sel in drawer_selectors:
            loc = self.page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return True
        return False

    def scroll_drawer_to_bottom(self) -> None:
        scroll_script = """
        () => {
            const container = document.querySelector(
                '.chatbot_MessageContainer, .chatbot_DrawerContentWrapper, div[class*="MessageContainer"], div[id*="Messages"]'
            );
            if (container) {
                container.scrollTop = container.scrollHeight;
                return true;
            }
            return false;
        }
        """
        try:
            self.page.evaluate(scroll_script)
            self.page.wait_for_timeout(300)
        except Exception:
            pass

    def extract_active_question(self) -> Tuple[Optional[str], Optional[str]]:
        self.scroll_drawer_to_bottom()
        
        bot_items = self.page.locator(
            "div[class*='chatbot_MessageContainer'] li.botItem, "
            "div[id*='Messages'] li.botItem, "
            ".chatbot_DrawerContentWrapper li.botItem, "
            "li.botItem.chatbot_ListItem, "
            "li.botItem"
        )
        count = bot_items.count()
        if count == 0:
            return None, None

        raw_messages = []
        for i in range(count):
            item = bot_items.nth(i)
            msg_div = item.locator(".botMsg, div[class*='botMsg']").first
            if msg_div.count() > 0:
                txt = msg_div.inner_text().strip()
                if txt:
                    raw_messages.append(txt)

        if not raw_messages:
            return None, None

        cand_name_clean = self.candidate_name.lower().strip()
        first_name_clean = self.first_name.lower().strip()
        
        greeting_markers = [
            "thank you for showing interest",
            "kindly answer all",
            "answer all the recruiter",
            "welcome to",
            "to successfully apply",
            "hi ",
            "hello "
        ]

        active_question = None
        filtered_greeting = None

        for msg in reversed(raw_messages):
            msg_lower = msg.lower()
            is_greeting = False
            
            if (first_name_clean and first_name_clean in msg_lower) or (cand_name_clean and cand_name_clean in msg_lower):
                if any(marker in msg_lower for marker in greeting_markers):
                    is_greeting = True
                    filtered_greeting = msg
            elif any(marker in msg_lower for marker in ["thank you for showing interest", "kindly answer all the recruiter"]):
                is_greeting = True
                filtered_greeting = msg

            if not is_greeting and len(msg.strip()) > 3:
                active_question = msg.strip()
                break

        if not active_question and raw_messages:
            active_question = raw_messages[-1].strip()

        return active_question, filtered_greeting

    def detect_ui_control(self) -> str:
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first

        # 1. File Upload
        file_input = drawer.locator("input[type='file'], input.chatbot_Uploader, input[id*='Uploader']")
        if file_input.count() > 0 and file_input.first.is_visible():
            return "FILE_UPLOAD"

        # 2. Date Input
        date_input = drawer.locator("input[type='date'], input.datePicker, input[class*='datePicker'], input[class*='date-picker']")
        if date_input.count() > 0 and date_input.first.is_visible():
            return "DATE_INPUT"

        # 3. Radio / Choice Chips / Custom Radios (Strictly ignoring .chipMsg)
        is_radio = self.page.evaluate("""() => {
            const drawer = document.querySelector('.chatbot_DrawerContentWrapper, div[class*="_chatbotContainer"]') || document;
            if (drawer.querySelector('input[type="radio"], input[type="checkbox"]')) return true;
            
            const chips = Array.from(drawer.querySelectorAll(
                '.choiceChip, .clickableChip, .radioItem, .optionItem, [class*="chipItem"], ' +
                'label.ssrc__label, div.customRadio, div.radioItem, div.togglePill, button.toggle, ' +
                'div[class*="toggle"], div.yesNoToggle, label[class*="radio"], ul.ChoiceList li'
            )).filter(el => !el.closest('.chipMsg') && !el.classList.contains('chipMsg') && el.offsetParent !== null);
            
            return chips.length > 0;
        }""")
        if is_radio:
            return "RADIO_CHIP"

        # 4. Dropdowns
        select_dropdown = drawer.locator("select, div.custom-select, div[class*='dropdown'], div[class*='select-dropdown']")
        if select_dropdown.count() > 0 and select_dropdown.first.is_visible():
            return "DROPDOWN"

        # 5. Contenteditable Text Inputs
        textarea = drawer.locator(
            "div.textArea[contenteditable='true'], "
            "div[id^='userInput_'], "
            "div[id*='userInput'], "
            ".textAreaWrapper div[contenteditable='true'], "
            "div.chatbot_userInput, "
            "input[type='text'], "
            "textarea"
        )
        if textarea.count() > 0 and textarea.first.is_visible():
            return "CONTENTEDITABLE"

        body_textarea = self.page.locator("div.textArea[contenteditable='true'], div[id^='userInput_']").first
        if body_textarea.count() > 0 and body_textarea.is_visible():
            return "CONTENTEDITABLE"

        return "UNKNOWN"

    def get_radio_options(self) -> List[str]:
        try:
            options = self.page.evaluate(r"""() => {
                const drawer = document.querySelector('.chatbot_DrawerContentWrapper, div[class*="_chatbotContainer"]') || document;
                const opts = new Set();
                
                // Strategy A: Explicit Radio Inputs
                const radios = drawer.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                if (radios.length > 0) {
                    radios.forEach(r => {
                        if (r.closest('.chipMsg')) return;
                        if (r.id) {
                            const label = drawer.querySelector(`label[for="${r.id}"]`);
                            if (label && label.innerText) {
                                opts.add(label.innerText.trim());
                                return;
                            }
                        }
                        if (r.nextElementSibling && (r.nextElementSibling.tagName === 'LABEL' || r.nextElementSibling.tagName === 'SPAN')) {
                            opts.add(r.nextElementSibling.innerText.trim());
                            return;
                        }
                        if (r.value && r.value.length > 0 && r.value !== 'on') {
                            opts.add(r.value.trim());
                        }
                    });
                }
                
                // Strategy B: Choice Chips and Custom Radio Wrappers
                const chips = drawer.querySelectorAll(
                    '.choiceChip, .clickableChip, .radioItem, .optionItem, [class*="chipItem"], ' +
                    'label.ssrc__label, div.customRadio, div.togglePill, button.toggle, div.yesNoToggle, ' +
                    'label[class*="radio"], ul.ChoiceList li'
                );
                chips.forEach(c => {
                    if (c.closest('.chipMsg') || c.classList.contains('chipMsg')) return;
                    const txt = c.innerText.trim();
                    if (txt && txt.length < 150 && !/[\r\n]/.test(txt)) {
                        opts.add(txt);
                    }
                });
                
                return Array.from(opts).filter(Boolean);
            }""")
            return options or []
        except Exception as e:
            log_step("WARNING", f"Error evaluating radio options: {e}")
            return []

    def resolve_answer(self, question: str, options: Optional[List[str]] = None, control_type: str = "CONTENTEDITABLE") -> str:
        q_clean = question.strip()
        log_step("AI BRAIN", f"Grounded Resume Analysis -> Resolving screening question...")
        ai_response = self.ai.answer_screening_question(
            question=q_clean,
            candidate_profile=self.config,
            options=options,
            control_type=control_type,
            resume_text=self.resume_text
        )
        cleaned_ans = ai_response.strip().strip('"').strip("'")
        log_step("AI BRAIN", f"Resolved Factual Answer: '{cleaned_ans}'")
        return cleaned_ans

    def _get_input_field(self):
        selectors = [
            "div.textArea[contenteditable='true']",
            "div[id*='userInput']",
            "div.chatbot_SendMessageContainer div.textArea",
            "div[id*='InputBox'] div.textArea",
            "div.textAreaWrapper div[contenteditable='true']",
            "div.chatbot_InputContainer div.textArea",
            "textarea.chatbot_Input",
            "input.chatbot_Input"
        ]
        for sel in selectors:
            loc = self.page.locator(sel).first
            try:
                if loc.is_visible(timeout=400):
                    return loc
            except Exception:
                continue
        return None

    def execute_contenteditable_input(self, answer: str) -> bool:
        input_loc = self._get_input_field()
        if not input_loc:
            log_step("WARNING", "Could not locate contenteditable textarea in chatbot drawer.")
            return False

        log_step("CHATBOT", f"Targeting input container with answer: '{answer}'")
        self.scroll_drawer_to_bottom()

        try:
            input_loc.click(force=True)
            human_jitter(100, 250)
            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            self.page.keyboard.press(mod_key)
            self.page.keyboard.press("Backspace")
            human_jitter(50, 150)

            self.page.keyboard.insert_text(str(answer))
            human_jitter(100, 200)

            js_dispatch = """
            (ans) => {
                const el = document.querySelector(
                    'div.textArea[contenteditable="true"], div[id*="userInput"], .textAreaWrapper div[contenteditable="true"]'
                );
                if (el) {
                    el.focus();
                    if (!el.innerText || el.innerText.trim() === '') {
                        document.execCommand('insertText', false, ans);
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter' }));
                    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter' }));
                }
                
                const drawer = document.querySelector('.chatbot_DrawerContentWrapper, div[class*="_chatbotContainer"]');
                const btn = drawer ? drawer.querySelector('.sendMsgbtn_container .sendMsg, div[id*="sendMsg"] .sendMsg, .sendMsg') : document.querySelector('.sendMsgbtn_container .sendMsg, div[id*="sendMsg"] .sendMsg, .sendMsg');
                if (btn) {
                    btn.classList.remove('disabled');
                    btn.removeAttribute('disabled');
                } else if (drawer) {
                    const btns = drawer.querySelectorAll('button');
                    for (let b of btns) {
                        if ((b.innerText || '').toLowerCase().includes('save') || (b.innerText || '').toLowerCase().includes('send')) {
                            b.classList.remove('disabled');
                            b.removeAttribute('disabled');
                            break;
                        }
                    }
                }
                return true;
            }
            """
            self.page.evaluate(js_dispatch, str(answer))
            human_jitter(150, 300)

            drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='_chatbotContainer'], div[class*='chatbot_Drawer']").first
            send_btn_selectors = [
                ".sendMsgbtn_container .sendMsg",
                "div[id*='sendMsg'] .sendMsg",
                ".sendMsgbtn_container div.send .sendMsg",
                "span.chatBot-send",
                "span[class*='send']",
                ".chatbot_SendMessageContainer button"
            ]
            
            clicked = False
            for btn_sel in send_btn_selectors:
                btn_loc = drawer.locator(btn_sel).first
                if btn_loc.count() > 0 and btn_loc.is_visible():
                    btn_loc.click(force=True)
                    clicked = True
                    break

            if not clicked:
                for btn_sel in [".sendMsgbtn_container .sendMsg", "div[id*='sendMsg'] .sendMsg"]:
                    btn_loc = drawer.locator(btn_sel).first
                    if btn_loc.count() > 0 and btn_loc.is_visible():
                        btn_loc.click(force=True)
                        clicked = True
                        break

            if not clicked:
                self.page.keyboard.press("Enter")

            self.page.wait_for_timeout(1500)
            return True
        except Exception as e:
            log_step("WARNING", f"Failed typing into input container: {e}")
            return False

    def execute_chip_selection(self, matched_option: str) -> bool:
        self.scroll_drawer_to_bottom()
        clean_target = str(matched_option).strip()
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first

        # Priority 1: Native Playwright locator click (dispatches real OS mouse events)
        clicked = False
        try:
            escaped_text = clean_target.replace("'", "\\'")
            chip_loc = drawer.locator(
                f"button:has-text('{escaped_text}'), label:has-text('{escaped_text}'), "
                f"div.clickableChip:has-text('{escaped_text}'), div.choiceChip:has-text('{escaped_text}'), "
                f"div.radioItem:has-text('{escaped_text}'), span:has-text('{escaped_text}')"
            ).first
            if chip_loc.count() > 0 and chip_loc.is_visible():
                chip_loc.click(force=True)
                clicked = True
        except Exception:
            pass

        # Priority 2: Scoped DOM evaluate click if Playwright native locator didn't resolve
        if not clicked:
            clicked = self.page.evaluate(r"""(targetText) => {
                const cleanTarget = targetText.toLowerCase().trim();
                const drawer = document.querySelector('.chatbot_DrawerContentWrapper, div[class*="_chatbotContainer"]');
                if (!drawer) return false;

                const labels = drawer.querySelectorAll('label');
                for (let lbl of labels) {
                    if (lbl.closest('.chipMsg') || lbl.classList.contains('chipMsg')) continue;
                    if (lbl.innerText.toLowerCase().trim() === cleanTarget) {
                        lbl.click();
                        return true;
                    }
                }

                const elements = drawer.querySelectorAll('span, div, button, label, a');
                for (let el of elements) {
                    if (el.closest('.chipMsg') || el.classList.contains('chipMsg')) continue;
                    if (el.children.length > 2) continue;
                    let text = (el.innerText || '').toLowerCase().trim();

                    if (text === cleanTarget) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }""", clean_target)

        if clicked:
            # Radio chips are self-submitting upon click. Never trigger empty text area send buttons.
            self.page.wait_for_timeout(1200)
            return True

        log_step("WARNING", f"Could not click element for option: '{matched_option}'")
        return False

    def execute_file_upload(self, tailored_pdf_path: Optional[str] = None) -> bool:
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer'], div.jobs-easy-apply-modal").first
        file_input = drawer.locator("input[type='file'], input.chatbot_Uploader, input[id*='Uploader']").first
        
        if file_input.count() == 0:
            return False

        target_pdf = tailored_pdf_path
        if not target_pdf or not os.path.exists(target_pdf):
            profile_pdf = self.ctx.profile_dir / f"{self.candidate_name.replace(' ', '_')}_Resume.pdf"
            if profile_pdf.exists():
                target_pdf = str(profile_pdf)

        if not target_pdf or not os.path.exists(target_pdf):
            log_step("CHATBOT", "No valid PDF resume file found on disk for upload.")
            return False

        log_step("CHATBOT", f"Uploading resume PDF: {target_pdf}")
        file_input.set_input_files(target_pdf)
        self.page.wait_for_timeout(2000)
        return True

    def check_completion_status(self) -> Tuple[bool, str]:
        success_markers = [
            "applied successfully",
            "application has been submitted",
            "your application has reached",
            "successfully applied",
            "application submitted",
            "application sent to recruiter",
            "responses recorded",
            "responses have been recorded",
            "profile shared with recruiter",
            "has reached the recruiter",
            "application sent",
            "your application was sent"
        ]
        
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
        if drawer.count() > 0 and drawer.is_visible():
            drawer_text = drawer.inner_text().lower()
            for marker in success_markers:
                if marker in drawer_text:
                    return True, f"Detected success marker in drawer: '{marker}'"
            return False, ""

        page_text = self.page.locator("body").inner_text().lower()
        for marker in success_markers:
            if marker in page_text:
                return True, f"Detected success marker on page: '{marker}'"

        return False, ""


# ==============================================================================
# LINKEDIN EASY APPLY AUTOMATION ENGINE
# ==============================================================================

class LinkedInApplyHandler:
    """
    Dedicated handler for LinkedIn Easy Apply multi-step modal dialogs.
    Executes form filling, radio button selection, file attachment, and step progression.
    Guarantees Guardrail H1 compliance: strictly eliminates blind options[0] fallbacks,
    routes unmatched queries to Antigravity IPC, and performs clean modal dismissal/discard.
    """
    def __init__(self, page, ctx: ProfileContext, ai_client: AIClient):
        self.page = page
        self.ctx = ctx
        self.ai = ai_client
        self.config = getattr(ctx, "config", {})
        self.cand = self.config.get("candidate", {})

    def is_modal_open(self) -> bool:
        if not self.page:
            return False
        modal = self.page.locator("div.jobs-easy-apply-modal, div[data-view-name='job-apply-modal'], div.artdeco-modal").first
        return modal.count() > 0 and modal.is_visible()

    def discard_and_close_modal(self) -> bool:
        """
        Safely dismisses and discards an active LinkedIn Easy Apply modal dialog.
        Prevents dangling modal states that could block subsequent operations or scans.
        """
        if not self.page:
            return True
        log_step("LINKEDIN", "Executing clean modal dismissal and application discard...")
        try:
            # 1. Locate and click modal dismiss / close button
            dismiss_selectors = [
                "button[aria-label='Dismiss']",
                "button[data-test-modal-close-btn]",
                "button.artdeco-modal__dismiss",
                ".artdeco-modal__dismiss",
                "button[data-control-name='overlay.close_padding']",
                "button:has(svg[data-test-icon='close-small'])",
                "button:has(svg[data-test-icon='close-medium'])"
            ]
            dismissed = False
            for sel in dismiss_selectors:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click()
                    dismissed = True
                    break

            if not dismissed:
                self.page.keyboard.press("Escape")

            self.page.wait_for_timeout(1000)

            # 2. Confirm the 'Discard application' prompt if presented
            discard_selectors = [
                "button[data-control-name='discard_application_confirm_btn']",
                "button[data-test-dialog-secondary-action]",
                "button:has-text('Discard')",
                "button.artdeco-button--primary:has-text('Discard')",
                "button:has-text('Save as draft')"
            ]
            for d_sel in discard_selectors:
                d_loc = self.page.locator(d_sel).first
                if d_loc.count() > 0 and d_loc.is_visible():
                    log_step("LINKEDIN", "Confirming 'Discard application' dialog...")
                    d_loc.click()
                    self.page.wait_for_timeout(1000)
                    break

            return not self.is_modal_open()
        except Exception as e:
            log_step("WARNING", f"Modal discard notice: {e}")
            return False

    def handle_easy_apply(self, job: Dict[str, Any]) -> str:
        log_step("LINKEDIN", "Engaging LinkedIn Easy Apply Engine...")
        tailored_pdf = job.get("pdf_path") or job.get("tailored_pdf", "")
        max_steps = 15
        step = 0

        try:
            while step < max_steps:
                step += 1
                self.page.wait_for_timeout(1500)

                # 1. Check for application submission success
                body_text = self.page.locator("body").inner_text().lower()
                if any(m in body_text for m in ["application sent", "your application was sent", "application submitted"]):
                    log_step("SUCCESS", "LinkedIn Easy Apply confirmed submitted!")
                    # Dismiss post-apply modal if present
                    try:
                        dismiss_btn = self.page.locator("button[aria-label='Dismiss'], button:has-text('Done')").first
                        if dismiss_btn.is_visible():
                            dismiss_btn.click()
                    except Exception:
                        pass
                    return "APPLIED_LINKEDIN_EASY_APPLY"

                if not self.is_modal_open():
                    # Re-verify if completed
                    if any(m in body_text for m in ["application sent", "your application was sent"]):
                        return "APPLIED_LINKEDIN_EASY_APPLY"
                    log_step("WARNING", "LinkedIn Easy Apply modal closed prematurely.")
                    return "DRAWER_CLOSED"

                modal = self.page.locator("div.jobs-easy-apply-modal, div.artdeco-modal").first

                # 2. Handle File Upload if requested on this step
                file_input = modal.locator("input[type='file']").first
                if file_input.count() > 0 and file_input.is_visible():
                    if tailored_pdf and os.path.exists(tailored_pdf):
                        log_step("LINKEDIN", f"Attaching Tailored PDF: {os.path.basename(tailored_pdf)}")
                        file_input.set_input_files(tailored_pdf)
                        self.page.wait_for_timeout(1500)

                # 3. Handle Form Text Inputs
                text_inputs = modal.locator("input[type='text'], input:not([type]), textarea").all()
                for inp in text_inputs:
                    try:
                        if inp.is_visible() and not inp.input_value():
                            inp_id = inp.get_attribute("id") or ""
                            label_el = modal.locator(f"label[for='{inp_id}']").first if inp_id else None
                            q_text = label_el.inner_text().strip() if (label_el and label_el.count()) else "Input field"
                            
                            ans = ""
                            q_lower = q_text.lower()
                            if "phone" in q_lower or "mobile" in q_lower:
                                ans = str(self.cand.get("phone", ""))
                            elif "email" in q_lower:
                                ans = str(self.cand.get("email", ""))
                            else:
                                ans = self.ai.answer_screening_question(
                                    question=q_text,
                                    candidate_profile=self.config,
                                    control_type="TEXT"
                                )
                            if ans:
                                inp.fill(ans)
                                human_jitter(100, 250)
                    except Exception:
                        pass

                # 4. Handle Radio / Checkbox Fieldsets (H1 Strict Compliance)
                fieldsets = modal.locator("fieldset").all()
                for fs in fieldsets:
                    try:
                        if fs.is_visible():
                            legend = fs.locator("legend").first
                            q_text = legend.inner_text().strip() if legend.count() else ""
                            radios = fs.locator("input[type='radio']").all()
                            if radios:
                                options = []
                                for r in radios:
                                    r_id = r.get_attribute("id") or ""
                                    lbl = fs.locator(f"label[for='{r_id}']").first
                                    if lbl.count():
                                        options.append(lbl.inner_text().strip())
                                if options and q_text:
                                    ans = self.ai.answer_screening_question(
                                        question=q_text,
                                        candidate_profile=self.config,
                                        options=options,
                                        control_type="RADIO"
                                    )
                                    best_opt = self.ai._best_option_match(ans, options)
                                    
                                    # H1 Remediation: No blind options[0] fallback; route to Antigravity IPC
                                    if not best_opt:
                                        log_step("LINKEDIN", f"No exact match for '{ans}'. Engaging Antigravity IPC fallback for radio options: {options}")
                                        ipc_ans = self.ai._fallback_antigravity_ipc(
                                            prompt=(
                                                f"LinkedIn Easy Apply Screening Question:\n"
                                                f"Question: {q_text}\n"
                                                f"Available Options:\n" + "\n".join(f"- {o}" for o in options) + "\n\n"
                                                f"Candidate Profile: {self.config.get('candidate', {})}\n"
                                                f"Select the exact matching option string from the available options above."
                                            ),
                                            question=q_text,
                                            options=options,
                                            control_type="RADIO",
                                            task_type="SCREENING_QUESTION"
                                        )
                                        best_opt = self.ai._best_option_match(ipc_ans, options)

                                    if best_opt:
                                        safe_opt = best_opt.replace("'", "\\'")
                                        matched_lbl = fs.locator(f"label:has-text('{safe_opt}')").first
                                        if matched_lbl.count():
                                            matched_lbl.click()
                                            human_jitter(100, 250)
                                    else:
                                        log_step("WARNING", f"Guardrail H1: Zero option match for radio question '{q_text}'. Refusing blind fallback. Aborting.")
                                        self.discard_and_close_modal()
                                        return "FAILED"
                    except Exception as ex:
                        log_step("WARNING", f"Radio fieldset handling notice: {ex}")

                # 5. Handle Select Dropdowns (H1 Strict Compliance)
                selects = modal.locator("select").all()
                for sel_el in selects:
                    try:
                        if sel_el.is_visible() and not sel_el.input_value():
                            sel_id = sel_el.get_attribute("id") or ""
                            lbl = modal.locator(f"label[for='{sel_id}']").first
                            q_text = lbl.inner_text().strip() if lbl.count() else "Select option"
                            opts = sel_el.locator("option").all_inner_texts()
                            valid_opts = [o.strip() for o in opts if o.strip() and "select" not in o.lower()]
                            if valid_opts:
                                ans = self.ai.answer_screening_question(
                                    question=q_text,
                                    candidate_profile=self.config,
                                    options=valid_opts,
                                    control_type="DROPDOWN"
                                )
                                best = self.ai._best_option_match(ans, valid_opts)

                                # H1 Remediation: No blind valid_opts[0] fallback; route to Antigravity IPC
                                if not best:
                                    log_step("LINKEDIN", f"No exact match for '{ans}'. Engaging Antigravity IPC fallback for dropdown options: {valid_opts}")
                                    ipc_ans = self.ai._fallback_antigravity_ipc(
                                        prompt=(
                                            f"LinkedIn Easy Apply Dropdown Question:\n"
                                            f"Question: {q_text}\n"
                                            f"Available Options:\n" + "\n".join(f"- {o}" for o in valid_opts) + "\n\n"
                                            f"Candidate Profile: {self.config.get('candidate', {})}\n"
                                            f"Select the exact matching option string from the available options above."
                                        ),
                                        question=q_text,
                                        options=valid_opts,
                                        control_type="DROPDOWN",
                                        task_type="SCREENING_QUESTION"
                                    )
                                    best = self.ai._best_option_match(ipc_ans, valid_opts)

                                if best:
                                    sel_el.select_option(label=best)
                                    human_jitter(100, 250)
                                else:
                                    log_step("WARNING", f"Guardrail H1: Zero option match for dropdown question '{q_text}'. Refusing blind fallback. Aborting.")
                                    self.discard_and_close_modal()
                                    return "FAILED"
                    except Exception as ex:
                        log_step("WARNING", f"Dropdown handling notice: {ex}")

                # 6. Step Progression: Check buttons in order of priority
                submit_btn = modal.locator("button:has-text('Submit application'), button:has-text('Submit')").first
                if submit_btn.count() > 0 and submit_btn.is_visible():
                    log_step("LINKEDIN", "Clicking 'Submit application'...")
                    submit_btn.click()
                    self.page.wait_for_timeout(3000)
                    continue

                review_btn = modal.locator("button:has-text('Review')").first
                if review_btn.count() > 0 and review_btn.is_visible():
                    log_step("LINKEDIN", "Clicking 'Review' button...")
                    review_btn.click()
                    self.page.wait_for_timeout(1500)
                    continue

                next_btn = modal.locator("button:has-text('Next')").first
                if next_btn.count() > 0 and next_btn.is_visible():
                    log_step("LINKEDIN", "Clicking 'Next' button...")
                    next_btn.click()
                    self.page.wait_for_timeout(1500)
                    continue

                # If no progression button could be identified or clicked:
                error_loc = modal.locator(".artdeco-inline-feedback--error, div[data-test-form-builder-error]").first
                if error_loc.count() > 0 and error_loc.is_visible():
                    err_text = error_loc.inner_text().strip()
                    log_step("WARNING", f"LinkedIn form validation error detected: {err_text}")
                else:
                    log_step("WARNING", "No progression button (Submit/Review/Next) located in modal.")
                self.discard_and_close_modal()
                return "FAILED"

            log_step("FAILED", "Exceeded max steps in LinkedIn Easy Apply modal.")
            self.discard_and_close_modal()
            return "FAILED"

        except Exception as e:
            log_step("WARNING", f"Unhandled exception in LinkedIn Easy Apply handler: {e}")
            self.discard_and_close_modal()
            return "FAILED"


# ==============================================================================
# MASTER APPLICATION CONTROLLER
# ==============================================================================

class ApplicationEngine:
    def __init__(self, profile_path: str):
        self.ctx = ProfileContext(profile_path)
        self.browser_mgr = BrowserManager()
        self.ai = AIClient(self.ctx)
        self.stats = {
            "total": 0,
            "applied_1click": 0,
            "applied_chatbot": 0,
            "applied_linkedin": 0,
            "redirect_external": 0,
            "failed": 0,
            "skipped": 0
        }

    def load_application_manifest(self) -> List[Dict[str, Any]]:
        manifest_file = self.ctx.manifest_path
        if not manifest_file.exists():
            log_step("MANIFEST", f"No search_manifest.json located at {manifest_file}")
            return []
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("jobs", [])
        except Exception as e:
            log_step("ERROR", f"Failed to parse manifest: {e}")
            return []

    def record_tracker_entry(self, entry: Dict[str, Any]) -> None:
        tracker_file = self.ctx.tracker_path
        file_exists = tracker_file.exists()
        headers = [
            "Date", "Company", "Job Title", "Platform", "Job URL", 
            "Match Score", "Status", "Tailored Resume PDF", "Notes"
        ]
        try:
            with open(tracker_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "Date": entry.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "Company": entry.get("company", "Unknown"),
                    "Job Title": entry.get("job_title", "Unknown"),
                    "Platform": entry.get("platform", "Naukri"),
                    "Job URL": entry.get("url", ""),
                    "Match Score": entry.get("score", "N/A"),
                    "Status": entry.get("status", "APPLIED"),
                    "Tailored Resume PDF": entry.get("pdf_path", ""),
                    "Notes": entry.get("notes", "")
                })
            log_substep("TRACKER", f"Recorded entry in {tracker_file.name} -> Status: {entry.get('status')}")
        except Exception as e:
            log_step("ERROR", f"Failed writing to tracker: {e}")

    def record_external_redirect(self, job: Dict[str, Any], redirect_url: str) -> None:
        ext_file = self.ctx.saved_external_path
        records = []
        if ext_file.exists():
            try:
                with open(ext_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []
        
        exists = any(r.get("original_url") == job.get("url") or r.get("url") == job.get("url") for r in records)
        if not exists:
            records.append({
                "job_title": job.get("job_title") or job.get("title"),
                "company": job.get("company"),
                "platform": job.get("platform", "Naukri"),
                "original_url": job.get("url"),
                "redirect_url": redirect_url,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(ext_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            log_substep("EXTERNAL", f"Saved redirect posting to {ext_file.name}")

    def apply_single_job(self, page, job: Dict[str, Any], already_at_url: bool = False) -> str:
        url = job.get("url", "")
        title = job.get("job_title") or job.get("title", "Job Role")
        company = job.get("company", "Employer")
        platform = job.get("platform", "naukri").lower()
        
        log_section(f"Processing Application: [{platform.upper()}] {company} | {title}")
        
        try:
            page.bring_to_front()
            if not already_at_url or not page.url or page.url == "about:blank":
                log_step("NAVIGATE", f"Opening Job URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            else:
                log_step("NAVIGATE", f"Reusing already open job tab: {page.url}")
            
            # Resilient wait for React hydration and main action buttons
            try:
                page.wait_for_selector(
                    "button#apply-button, button.apply-button, button:has-text('Apply'), "
                    "button:has-text('Already Applied'), span:has-text('Already Applied'), "
                    "button:has-text('Apply on company website'), a:has-text('Apply on company website'), "
                    "#company-site-button",
                    timeout=8000
                )
            except Exception:
                page.wait_for_timeout(1500)
        except Exception as e:
            log_step("ERROR", f"Navigation timeout or failure: {e}")
            return "FAILED"

        # Check for external employer website redirects
        ext_btn_selectors = [
            "button:has-text('Apply on company website')",
            "a:has-text('Apply on company website')",
            "button:has-text('Apply on Company Site')",
            "a:has-text('Apply on Company Site')",
            "#company-site-button"
        ]
        for sel in ext_btn_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                log_step("GATE", "Listing requires external site redirect. Gating and saving...")
                self.record_external_redirect(job, url)
                return "REDIRECT_EXTERNAL"

        # Check if already applied
        already_applied_selectors = [
            "button:has-text('Already Applied')",
            "span:has-text('Already Applied')",
            "div:has-text('You have already applied')",
            "button:has-text('Applied')",
            ".jobs-s-apply__applied-date"
        ]
        for sel in already_applied_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                log_step("STATUS", "Already applied previously. Skipping.")
                return "SKIPPED_ALREADY_APPLIED"

        # Platform Specific Branching
        if platform == "linkedin":
            li_handler = LinkedInApplyHandler(page, self.ctx, self.ai)
            easy_apply_btn = page.locator("button.jobs-apply-button, button:has-text('Easy Apply')").first
            if easy_apply_btn.count() > 0 and easy_apply_btn.is_visible():
                log_step("CLICK", "Clicking LinkedIn 'Easy Apply' button...")
                easy_apply_btn.click()
                page.wait_for_timeout(2000)
                return li_handler.handle_easy_apply(job)
            else:
                log_step("WARNING", "LinkedIn Easy Apply button not found on page.")
                return "APPLY_BUTTON_NOT_FOUND"

        # Naukri Native Apply Handling
        apply_btn_selectors = [
            "button#apply-button",
            "button.apply-button",
            "button.styles_apply-button__uJI3A",
            "button:has-text('Apply on Naukri')",
            "button:has-text('Apply')",
            "div.apply-button-container button",
            ".styles_jds-apply-button__WbS2i button",
            ".styles_jds-apply-button__WbS2i"
        ]
        
        # Attach popup listener to capture application questionnaires opening in new tabs
        popup_tabs = []
        def handle_popup(new_page):
            popup_tabs.append(new_page)
        
        try:
            page.context.on("page", handle_popup)
        except Exception:
            pass

        apply_clicked = False
        for sel in apply_btn_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                txt = loc.inner_text().strip()
                log_step("CLICK", f"Clicking native apply trigger: '{txt}' ({sel})")
                try:
                    loc.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                loc.click()
                apply_clicked = True
                break

        if not apply_clicked:
            log_step("WARNING", "No visible native apply trigger found on page.")
            try:
                page.context.remove_listener("page", handle_popup)
            except Exception:
                pass
            return "APPLY_BUTTON_NOT_FOUND"

        target_page = page
        resolver = ChatbotResolver(target_page, self.ctx, self.ai)
        drawer_opened = False
        applied_1click = False
        success_msg = ""

        # Await drawer or 1-click confirmation across primary page and any opened popups
        for _ in range(20):
            page.wait_for_timeout(500)
            
            # Check if popup was opened and contains questionnaire or redirect
            if popup_tabs:
                for p_tab in list(popup_tabs):
                    try:
                        if not p_tab.is_closed():
                            p_tab.bring_to_front()
                            target_page = p_tab
                            resolver = ChatbotResolver(target_page, self.ctx, self.ai)
                            if resolver.is_drawer_open():
                                drawer_opened = True
                                break
                    except Exception:
                        pass
                if drawer_opened:
                    break

            if resolver.is_drawer_open():
                drawer_opened = True
                break
            
            if "/myapply/saveApply" in target_page.url or "myapply/historypage" in target_page.url:
                applied_1click = True
                success_msg = "Redirected to Naukri success page"
                break
                
            success_selectors = [
                "div.apply-message:has-text('successfully applied')",
                "div[class*='success-message']:has-text('applied')",
                "div.apply-message:has-text('applied')",
                ".applied-txt:has-text('Applied')",
                "span:has-text('Applied to')",
                "div:has-text('Applied to')"
            ]
            for s_sel in success_selectors:
                try:
                    loc = target_page.locator(s_sel).first
                    if loc.count() > 0 and loc.is_visible():
                        applied_1click = True
                        success_msg = loc.inner_text().strip()[:50]
                        break
                except Exception:
                    pass
            
            if applied_1click:
                break

        try:
            page.context.remove_listener("page", handle_popup)
        except Exception:
            pass

        if drawer_opened:
            log_step("CHATBOT", "Interactive Chatbot Drawer opened! Entering screening loop...")
            return self._handle_chatbot_loop(target_page, resolver, job)

        if applied_1click:
            log_step("SUCCESS", f"1-Click Apply confirmed via DOM or URL redirect: {success_msg}")
            return "APPLIED_1CLICK"

        log_step("FAILED", "Apply button clicked but no confirmation or drawer appeared.")
        return "FAILED"

    def _handle_chatbot_loop(self, page, resolver: ChatbotResolver, job: Dict[str, Any]) -> str:
        max_iterations = 25
        iteration = 0
        tailored_pdf = job.get("pdf_path") or job.get("tailored_pdf", "")
        
        company = job.get("company", "Company")
        job_title = job.get("job_title") or job.get("title", "Role")
        clean_c = re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_")[:50]
        clean_t = re.sub(r"[^\w\s-]", "", job_title).strip().replace(" ", "_")[:50]
        
        output_dir = getattr(self.ctx, "output_dir", Path("."))
        job_app_dir = output_dir / "applications" / f"{clean_c}_{clean_t}"
        job_app_dir.mkdir(parents=True, exist_ok=True)
        qa_log_path = job_app_dir / "ques_ans_chatbot.json"
        
        qa_history = []
        if qa_log_path.exists():
            try:
                with open(qa_log_path, "r", encoding="utf-8") as f:
                    qa_history = json.load(f)
            except Exception:
                qa_history = []

        last_processed_q = ""
        stuck_count = 0

        while iteration < max_iterations:
            iteration += 1
            page.wait_for_timeout(1500)
            
            # 1. Platform rejection banner detection (Guardrail C9)
            rejection_markers = [
                "not accepted due to incomplete information",
                "application was not accepted",
                "application not accepted",
                "unable to apply",
                "please answer all mandatory questions",
                "could not be submitted"
            ]
            page_content = ""
            try:
                page_content = page.locator("body").inner_text().lower()
            except Exception:
                pass

            rejected_msg = next((rm for rm in rejection_markers if rm in page_content), None)
            if rejected_msg:
                log_step("REJECTED_PLATFORM", f"Naukri rejected application: '{rejected_msg}'. Terminating screening loop.")
                qa_history.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "question": "[PLATFORM_REJECTION_BANNER]",
                    "answer": f"Platform rejected: {rejected_msg}",
                    "control_type": "REJECTED_BANNER"
                })
                try:
                    with open(qa_log_path, "w", encoding="utf-8") as f:
                        json.dump(qa_history, f, indent=2)
                except Exception:
                    pass
                return "FAILED_PLATFORM_REJECTED"

            # 2. Completion confirmation detection
            is_done, done_msg = resolver.check_completion_status()
            if is_done:
                log_step("SUCCESS", f"Application Completed! {done_msg}")
                return "APPLIED_CHATBOT"

            # 3. Premature drawer closure detection (Guardrail C9)
            if not resolver.is_drawer_open():
                page.wait_for_timeout(1000)
                if not resolver.is_drawer_open():
                    is_done, done_msg = resolver.check_completion_status()
                    if is_done:
                        log_step("SUCCESS", f"Application Completed! {done_msg}")
                        return "APPLIED_CHATBOT"
                    log_step("DRAWER_CLOSED", "Chatbot drawer closed prematurely. Aborting.")
                    return "DRAWER_CLOSED"

            active_q, filtered_greeting = resolver.extract_active_question()
            
            if not active_q:
                log_step("CHATBOT", f"Iteration {iteration}: Awaiting recruiter question or completion confirmation...")
                page.wait_for_timeout(2000)
                continue

            if active_q == last_processed_q:
                stuck_count += 1
                log_step("WARNING", f"Chatbot question repeated ({stuck_count}/3): '{active_q}'")
                if stuck_count >= 2:
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)
                if stuck_count >= 3:
                    log_step("FAILED", f"Chatbot permanently stuck on same question: '{active_q}'. Aborting loop.")
                    qa_history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "question": active_q,
                        "answer": "[ABORTED_STUCK_3X]",
                        "control_type": "STUCK",
                        "status": "REQUIRES_MANUAL_INTERVENTION"
                    })
                    try:
                        with open(qa_log_path, "w", encoding="utf-8") as f:
                            json.dump(qa_history, f, indent=2)
                    except Exception:
                        pass
                    return "FAILED"
            else:
                stuck_count = 0

            last_processed_q = active_q

            if filtered_greeting and stuck_count == 0:
                log_step("CHATBOT", f"Filtered Preamble: \"{filtered_greeting}\"")

            print(f"\n{'-' * 60}", flush=True)
            log_step("CHATBOT QUESTION", f"\"{active_q}\"")
            print(f"{'-' * 60}", flush=True)

            control_type = resolver.detect_ui_control()
            log_step("CONTROL TYPE", f"{control_type}")

            ans = ""
            if control_type == "RADIO_CHIP":
                options = resolver.get_radio_options()
                if not options:
                    log_step("WARNING", "RADIO_CHIP detected but no options found. Falling back to text.")
                    control_type = "CONTENTEDITABLE"
                else:
                    log_step("CHOICES", f"{options}")
                    ans = resolver.resolve_answer(active_q, options=options, control_type="RADIO_CHIP")
                    log_step("ACTION", f"Selecting Option: \"{ans}\"")
                    selection_ok = resolver.execute_chip_selection(ans)
                    if not selection_ok:
                        log_step("WARNING", "Native click failed. Attempting contenteditable fallback...")
                        resolver.execute_contenteditable_input(ans)

            if control_type == "CONTENTEDITABLE":
                ans = resolver.resolve_answer(active_q, control_type="CONTENTEDITABLE")
                log_step("ACTION", f"Submitting text response: \"{ans}\"")
                resolver.execute_contenteditable_input(ans)

            elif control_type == "FILE_UPLOAD":
                log_step("ACTION", "Resume File Upload requested by screening drawer.")
                resolver.execute_file_upload(tailored_pdf)
                ans = "[UPLOADED_RESUME_PDF]"

            elif control_type == "DROPDOWN":
                drawer = page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
                select_el = drawer.locator("select").first
                if select_el.count() > 0:
                    options = select_el.locator("option").all_inner_texts()
                    ans = resolver.resolve_answer(active_q, options=options, control_type="DROPDOWN")
                    select_el.select_option(label=ans)
                    log_step("ACTION", f"Selected Dropdown Value: \"{ans}\"")
                else:
                    ans = resolver.resolve_answer(active_q, control_type="CONTENTEDITABLE")
                    resolver.execute_contenteditable_input(ans)

            elif control_type == "DATE_INPUT":
                drawer = page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
                date_el = drawer.locator("input[type='date'], input.datePicker, input[class*='datePicker'], input[class*='date-picker']").first
                ans = resolver.resolve_answer(active_q, control_type="DATE_INPUT")
                log_step("ACTION", f"Submitting date value: '{ans}'")
                if date_el.count() > 0 and date_el.is_visible():
                    try:
                        date_el.fill(ans)
                        date_el.press("Enter")
                    except Exception:
                        resolver.execute_contenteditable_input(ans)
                else:
                    resolver.execute_contenteditable_input(ans)

            elif control_type not in ["RADIO_CHIP", "CONTENTEDITABLE", "FILE_UPLOAD", "DROPDOWN", "DATE_INPUT"]:
                input_field = resolver._get_input_field()
                if input_field and input_field.is_visible():
                    ans = resolver.resolve_answer(active_q, control_type="CONTENTEDITABLE")
                    resolver.execute_contenteditable_input(ans)
                else:
                    visible_interactive = page.evaluate("""() => {
                        const drawer = document.querySelector('.chatbot_DrawerContentWrapper, div[class*="_chatbotContainer"]') || document;
                        const elements = drawer.querySelectorAll('button, label, [class*="chip"], [class*="radio"], [class*="toggle"], div.choiceChip, div.clickableChip');
                        const items = [];
                        for (let el of elements) {
                            if (el.offsetParent !== null && !el.closest('.chipMsg') && !el.classList.contains('chipMsg')) {
                                const t = (el.innerText || '').trim();
                                if (t && t.length < 100 && !items.includes(t)) {
                                    items.push(t);
                                }
                            }
                        }
                        return items;
                    }""")
                    if visible_interactive:
                        ans = resolver.resolve_answer(active_q, options=visible_interactive, control_type="RADIO_CHIP")
                        resolver.execute_chip_selection(ans)

            qa_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question": active_q,
                "answer": ans,
                "control_type": control_type
            })
            try:
                with open(qa_log_path, "w", encoding="utf-8") as f:
                    json.dump(qa_history, f, indent=2)
            except Exception:
                pass

            page.wait_for_timeout(2500)

        is_done, _ = resolver.check_completion_status()
        return "APPLIED_CHATBOT" if is_done else "FAILED"

    def run(self, max_applications: int = 10) -> None:
        log_section("UNIVERSAL CAREER AGENT: APPLICATION BATCH START")
        log_step("PROFILE", f"Candidate: {self.ctx.candidate_name}")
        log_step("SANDBOX", f"Profile Directory: {self.ctx.profile_dir}")
        
        jobs_queue = self.load_application_manifest()
        if not jobs_queue:
            log_step("INFO", "No evaluated jobs found in search_manifest.json to apply for.")
            return

        # Dynamically resolve tab per job or fallback to transient page
        page = None
        applied_count = 0
        
        try:
            for job in jobs_queue:
                if applied_count >= max_applications:
                    log_step("LIMIT", f"Reached target application batch limit of {max_applications}.")
                    break
                
                url = job.get("url", "")
                page, already_at_url = self.browser_mgr.get_or_create_page_for_url(url)
                if not page:
                    page = self.browser_mgr.new_transient_page()
                status = self.apply_single_job(page, job, already_at_url=already_at_url)
                self.stats["total"] += 1
                
                company = job.get("company", "Unknown")
                job_title = job.get("job_title") or job.get("title", "Unknown")
                pdf_path = job.get("pdf_path") or job.get("tailored_pdf", "")
                platform = job.get("platform", "Naukri")
                
                if status in ["APPLIED_1CLICK", "APPLIED_CHATBOT", "APPLIED_LINKEDIN_EASY_APPLY"]:
                    applied_count += 1
                    if status == "APPLIED_1CLICK":
                        self.stats["applied_1click"] += 1
                    elif status == "APPLIED_LINKEDIN_EASY_APPLY":
                        self.stats["applied_linkedin"] += 1
                    else:
                        self.stats["applied_chatbot"] += 1

                    self.record_tracker_entry({
                        "company": company,
                        "job_title": job_title,
                        "platform": platform,
                        "url": job.get("url"),
                        "score": job.get("score") or job.get("match_score", "N/A"),
                        "status": status,
                        "pdf_path": pdf_path,
                        "notes": f"Applied autonomously via {status}"
                    })
                elif status == "REDIRECT_EXTERNAL":
                    self.stats["redirect_external"] += 1
                    self.record_tracker_entry({
                        "company": company,
                        "job_title": job_title,
                        "platform": platform,
                        "url": job.get("url"),
                        "score": job.get("score") or job.get("match_score", "N/A"),
                        "status": "REDIRECT_EXTERNAL",
                        "pdf_path": pdf_path,
                        "notes": "External employer site redirect saved to saved_external_jobs.json"
                    })
                elif status == "SKIPPED_ALREADY_APPLIED":
                    self.stats["skipped"] += 1
                else:
                    self.stats["failed"] += 1
                    failure_reason = "Application could not be committed or drawer failed"
                    if status == "FAILED_PLATFORM_REJECTED":
                        failure_reason = "Platform rejected application banner (incomplete screening responses)"
                    elif status == "DRAWER_CLOSED":
                        failure_reason = "Chatbot drawer closed prematurely"
                    self.record_tracker_entry({
                        "company": company,
                        "job_title": job_title,
                        "platform": platform,
                        "url": job.get("url"),
                        "score": job.get("score") or job.get("match_score", "N/A"),
                        "status": "FAILED",
                        "notes": failure_reason
                    })
                
                time.sleep(2.0)
        finally:
            if page and not page.is_closed():
                self.browser_mgr.close_page(page)
            self.browser_mgr.close_orphaned_blank_pages()
            self.browser_mgr.close()

        log_section("APPLICATION BATCH EXECUTION SUMMARY")
        print(f"    Total Jobs Evaluated:      {self.stats['total']}", flush=True)
        print(f"    Applied (1-Click):         {self.stats['applied_1click']}", flush=True)
        print(f"    Applied (Chatbot Solved):  {self.stats['applied_chatbot']}", flush=True)
        print(f"    Applied (LinkedIn Apply):  {self.stats['applied_linkedin']}", flush=True)
        print(f"    External Redirects Saved:  {self.stats['redirect_external']}", flush=True)
        print(f"    Skipped / Already Applied: {self.stats['skipped']}", flush=True)
        print(f"    Failed:                    {self.stats['failed']}", flush=True)
        print(f"{'=' * 80}\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Job Application Engine")
    parser.add_argument("--profile", type=str, default=None, help="Path to candidate profile directory")
    parser.add_argument("--max", type=int, default=10, help="Maximum number of applications to submit in this run")
    args = parser.parse_args()

    resolved_profile = args.profile
    if not resolved_profile:
        profiles_dir = PROJECT_ROOT / "profiles"
        available_profiles = [p for p in profiles_dir.iterdir() if p.is_dir()]
        if available_profiles:
            resolved_profile = str(available_profiles[0])
        else:
            print("[ERROR] No profile directory found in profiles/.", flush=True)
            sys.exit(1)

    engine = ApplicationEngine(resolved_profile)
    engine.run(max_applications=args.max)


if __name__ == "__main__":
    main()
