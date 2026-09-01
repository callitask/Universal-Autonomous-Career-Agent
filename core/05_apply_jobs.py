"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT: APPLICATION ENGINE
File: core/05_apply_jobs.py
Description: Full-lifecycle autonomous job application executor supporting
             1-click apply, external redirect gating, reverse-engineered
             Naukri chatbot drawer automation, and AG 2.0 job-specific logging.
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


def human_type(page, text: str):
    for char in text:
        page.keyboard.insert_text(char)
        time.sleep(random.randint(30, 85) / 1000.0)


def log_section(title: str) -> None:
    print(f"\n{'=' * 80}", flush=True)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {title}", flush=True)
    print(f"{'=' * 80}", flush=True)


def log_step(category: str, message: str) -> None:
    print(f"[{category.upper():<14}] {message}", flush=True)


def log_substep(category: str, message: str) -> None:
    print(f"    [{category}] {message}", flush=True)


class ChatbotResolver:
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
        
        file_input = drawer.locator("input[type='file'], input.chatbot_Uploader, input[id*='Uploader']")
        if file_input.count() > 0 and file_input.first.is_visible():
            return "FILE_UPLOAD"

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

        chips = drawer.locator(
            "div.radioItem, "
            "div.choiceChip, "
            "div.clickableChip, "
            "div[class*='radioItem'], "
            "label[class*='radio'], "
            "ul.ChoiceList li, "
            "div.optionItem"
        )
        if chips.count() > 0 and chips.first.is_visible():
            return "RADIO_CHIP"

        select_dropdown = drawer.locator("select, div.custom-select, div[class*='dropdown']")
        if select_dropdown.count() > 0 and select_dropdown.first.is_visible():
            return "DROPDOWN"

        body_textarea = self.page.locator("div.textArea[contenteditable='true'], div[id^='userInput_']").first
        if body_textarea.count() > 0 and body_textarea.is_visible():
            return "CONTENTEDITABLE"

        return "UNKNOWN"

    def resolve_answer(self, question: str, options: Optional[List[str]] = None, control_type: str = "CONTENTEDITABLE") -> str:
        q_clean = question.strip()
        log_step("AI BRAIN", f"Grounded Resume Analysis -> Evaluating question against candidate resume...")
        ai_response = self.ai.answer_screening_question(
            question=q_clean,
            candidate_profile=self.config,
            options=options,
            control_type=control_type,
            resume_text=self.resume_text
        )
        cleaned_ans = ai_response.strip().strip('"').strip("'")
        log_step("AI BRAIN", f"AG 2.0 Resolved Factual Answer: '{cleaned_ans}'")
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

        log_step("CHATBOT", f"Targeting interactive input container with answer: '{answer}'")
        
        self.scroll_drawer_to_bottom()
        try:
            input_loc.click(force=True)
            human_jitter(100, 250)

            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            self.page.keyboard.press(mod_key)
            self.page.keyboard.press("Backspace")
            human_jitter(50, 150)

            human_type(self.page, str(answer))
            human_jitter(150, 300)

            self.page.keyboard.press("Enter")
            human_jitter(200, 400)

            send_btn_selectors = [
                ".sendMsgbtn_container .sendMsg",
                "div[id*='sendMsg'] .sendMsg",
                ".sendMsgbtn_container div.send .sendMsg",
                "span.chatBot-send",
                "span[class*='send']",
                "button:has-text('Save')",
                "button:has-text('Submit')"
            ]
            
            clicked = False
            for btn_sel in send_btn_selectors:
                btn_loc = self.page.locator(btn_sel).first
                if btn_loc.count() > 0 and btn_loc.is_visible():
                    btn_loc.click(force=True)
                    clicked = True
                    break

            if not clicked:
                self.page.evaluate("""() => {
                    const btn = document.querySelector('.sendMsgbtn_container .sendMsg, div[id*="sendMsg"] .sendMsg');
                    if (btn) btn.click();
                }""")

            self.page.wait_for_timeout(1500)
            return True
        except Exception as e:
            log_step("WARNING", f"Failed typing into input container: {e}")
            return False

    def execute_chip_selection(self, matched_option: str) -> bool:
        self.scroll_drawer_to_bottom()
        
        safe_opt = matched_option.replace("'", "\\'")
        chip_selectors = [
            f"div.radioItem:has-text('{safe_opt}')",
            f"div.choiceChip:has-text('{safe_opt}')",
            f"div.clickableChip:has-text('{safe_opt}')",
            f"div[class*='radioItem']:has-text('{safe_opt}')",
            f"label:has-text('{safe_opt}')",
            f"ul.ChoiceList li:has-text('{safe_opt}')",
            f"div.optionItem:has-text('{safe_opt}')"
        ]

        chip = None
        for sel in chip_selectors:
            loc = self.page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                chip = loc
                break

        if chip:
            log_step("CHATBOT", f"Clicking choice chip: '{matched_option}'")
            chip.click(force=True)
            self.page.wait_for_timeout(500)
            
            save_btn = self.page.locator(
                ".sendMsgbtn_container .sendMsg, "
                "div[id*='sendMsg'] .sendMsg, "
                ".footerWrapper button:has-text('Save'), "
                "button:has-text('Save'), "
                "button:has-text('Next')"
            ).first
            if save_btn.count() > 0 and save_btn.is_visible():
                save_btn.click(force=True)
                self.page.wait_for_timeout(800)
            return True

        return False

    def execute_file_upload(self, tailored_pdf_path: Optional[str] = None) -> bool:
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
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
        self.page.wait_for_timeout(1000)
        return True

    def check_completion_status(self) -> Tuple[bool, str]:
        success_markers = [
            "applied successfully",
            "application has been submitted",
            "thank you for applying",
            "your application has reached",
            "successfully applied",
            "application submitted"
        ]
        
        drawer = self.page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
        if drawer.count() == 0 or not drawer.is_visible():
            return True, "Chatbot drawer dismissed; application confirmed."

        drawer_text = drawer.inner_text().lower()
        for marker in success_markers:
            if marker in drawer_text:
                return True, f"Detected success marker in drawer: '{marker}'"

        page_text = self.page.locator("body").inner_text().lower()
        for marker in success_markers:
            if marker in page_text:
                return True, f"Detected success marker on page: '{marker}'"

        return False, ""


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

        exists = any(r.get("url") == job.get("url") for r in records)
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

    def apply_single_job(self, page, job: Dict[str, Any]) -> str:
        url = job.get("url", "")
        title = job.get("job_title") or job.get("title", "Job Role")
        company = job.get("company", "Employer")
        
        log_section(f"Processing Application: {company} | {title}")
        log_step("NAVIGATE", f"Opening Job URL: {url}")
        
        try:
            page.bring_to_front()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log_step("ERROR", f"Navigation timeout or failure: {e}")
            return "FAILED"

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

        already_applied_selectors = [
            "button:has-text('Already Applied')",
            "span:has-text('Already Applied')",
            "div:has-text('You have already applied')"
        ]
        for sel in already_applied_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                log_step("STATUS", "Already applied previously. Skipping.")
                return "SKIPPED_ALREADY_APPLIED"

        apply_btn_selectors = [
            "button#apply-button",
            "button.apply-button",
            "button:has-text('Apply on Naukri')",
            "button:has-text('Apply')",
            "div.apply-button-container button",
            ".styles_jds-apply-button__WbS2i button"
        ]

        apply_clicked = False
        for sel in apply_btn_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.first.is_visible():
                txt = loc.inner_text().strip()
                log_step("CLICK", f"Clicking native apply trigger: '{txt}' ({sel})")
                loc.click(force=True)
                apply_clicked = True
                break

        if not apply_clicked:
            log_step("WARNING", "No visible native apply trigger found on page.")
            return "APPLY_BUTTON_NOT_FOUND"

        resolver = ChatbotResolver(page, self.ctx, self.ai)
        drawer_opened = False
        for _ in range(16):
            page.wait_for_timeout(500)
            if resolver.is_drawer_open():
                drawer_opened = True
                break

        if drawer_opened:
            log_step("CHATBOT", "Interactive Chatbot Drawer opened! Entering screening loop...")
            return self._handle_chatbot_loop(page, resolver, job)

        success_selectors = [
            "div.apply-message:has-text('successfully applied')",
            "div[class*='success-message']:has-text('applied')",
            "div.apply-message:has-text('applied')",
            ".applied-txt:has-text('Applied')"
        ]
        for s_sel in success_selectors:
            loc = page.locator(s_sel).first
            if loc.count() > 0 and loc.first.is_visible():
                log_step("SUCCESS", f"1-Click Apply confirmed via '{loc.inner_text().strip()}'")
                return "APPLIED_1CLICK"

        log_step("FAILED", "Apply button clicked but no confirmation or drawer appeared.")
        return "FAILED"

    def _handle_chatbot_loop(self, page, resolver: ChatbotResolver, job: Dict[str, Any]) -> str:
        max_iterations = 25
        iteration = 0
        tailored_pdf = job.get("pdf_path") or job.get("tailored_pdf", "")
        
        # AG 2.0 Feature: Per-Job QA Audit Directory next to resumes
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
            
            is_done, done_msg = resolver.check_completion_status()
            if is_done:
                log_step("SUCCESS", f"Application Completed! {done_msg}")
                return "APPLIED_CHATBOT"

            active_q, filtered_greeting = resolver.extract_active_question()
            
            if not active_q:
                log_step("CHATBOT", f"Iteration {iteration}: Awaiting recruiter question or completion confirmation...")
                page.wait_for_timeout(2000)
                continue

            if active_q == last_processed_q:
                stuck_count += 1
                if stuck_count >= 2:
                    log_step("WARNING", f"Chatbot waiting on: '{active_q}'. Retrying Enter commit...")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)
                if stuck_count >= 5:
                    log_step("FAILED", "Chatbot permanently stuck on the same question. Aborting loop.")
                    break
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
            if control_type == "CONTENTEDITABLE":
                ans = resolver.resolve_answer(active_q, control_type="CONTENTEDITABLE")
                log_step("ACTION", f"Submitting text response: \"{ans}\"")
                success = resolver.execute_contenteditable_input(ans)
                if not success:
                    log_step("WARNING", "Failed typing into input container.")

            elif control_type == "RADIO_CHIP":
                drawer = page.locator(".chatbot_DrawerContentWrapper, div[class*='chatbot_Drawer'], div[class*='_chatbotContainer']").first
                chip_locs = drawer.locator(
                    "div.radioItem, "
                    "div.choiceChip, "
                    "div.clickableChip, "
                    "div[class*='radioItem'], "
                    "label[class*='radio'], "
                    "ul.ChoiceList li, "
                    "div.optionItem"
                )
                options = []
                for idx in range(chip_locs.count()):
                    opt_t = chip_locs.nth(idx).inner_text().strip()
                    if opt_t and opt_t not in options:
                        options.append(opt_t)
                        
                log_step("CHOICES", f"{options}")
                ans = resolver.resolve_answer(active_q, options=options, control_type="RADIO_CHIP")
                log_step("ACTION", f"Selecting Option: \"{ans}\"")
                resolver.execute_chip_selection(ans)

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
                log_step("WARNING", "Unknown control type. Attempting generic input fallback...")
                ans = resolver.resolve_answer(active_q, control_type="CONTENTEDITABLE")
                resolver.execute_contenteditable_input(ans)

            # Persist Q&A to job's ques_ans_chatbot.json audit file
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

        log_step("QUEUE", f"Loaded {len(jobs_queue)} job postings from manifest.")
        
        context = self.browser_mgr.get_context()
        page = self.browser_mgr.new_page()
        applied_count = 0

        for job in jobs_queue:
            if applied_count >= max_applications:
                log_step("LIMIT", f"Reached target application batch limit of {max_applications}.")
                break

            status = self.apply_single_job(page, job)
            self.stats["total"] += 1
            
            company = job.get("company", "Unknown")
            job_title = job.get("job_title") or job.get("title", "Unknown")
            pdf_path = job.get("pdf_path") or job.get("tailored_pdf", "")

            if status in ["APPLIED_1CLICK", "APPLIED_CHATBOT"]:
                applied_count += 1
                if status == "APPLIED_1CLICK":
                    self.stats["applied_1click"] += 1
                else:
                    self.stats["applied_chatbot"] += 1

                self.record_tracker_entry({
                    "company": company,
                    "job_title": job_title,
                    "platform": job.get("platform", "Naukri"),
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
                    "platform": job.get("platform", "Naukri"),
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
                self.record_tracker_entry({
                    "company": company,
                    "job_title": job_title,
                    "platform": job.get("platform", "Naukri"),
                    "url": job.get("url"),
                    "score": job.get("score") or job.get("match_score", "N/A"),
                    "status": "FAILED",
                    "notes": "Application could not be committed or drawer failed"
                })

            time.sleep(2.0)

        log_section("APPLICATION BATCH EXECUTION SUMMARY")
        print(f"    Total Jobs Evaluated:      {self.stats['total']}", flush=True)
        print(f"    Applied (1-Click):         {self.stats['applied_1click']}", flush=True)
        print(f"    Applied (Chatbot Solved):  {self.stats['applied_chatbot']}", flush=True)
        print(f"    External Redirects Saved:  {self.stats['redirect_external']}", flush=True)
        print(f"    Skipped / Already Applied: {self.stats['skipped']}", flush=True)
        print(f"    Failed:                    {self.stats['failed']}", flush=True)
        print(f"{'=' * 80}\n", flush=True)


# ==============================================================================
# ENTRYPOINT
# ==============================================================================

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