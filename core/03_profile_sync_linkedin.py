"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT
File: core/03_profile_sync_linkedin.py
================================================================================
Dynamic LinkedIn Profile Sync
- Uses centralized AIClient for all text generation (removes hanging inputs).
- Deep text extraction for strict modal matching to prevent wrong-employer overwrites (Fix H5).
- Zero hardcoding. 100% Config-driven.
================================================================================
"""
import sys
import os
import json
import argparse
import logging
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] 03_linkedin_sync - %(message)s")
logger = logging.getLogger("03_linkedin_sync")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.utils.profile_context import ProfileContext
from core.ai_client import AIClient

def log(msg: str):
    print(f"  {msg}", flush=True)

def generate_robust_about_section(resume_text: str, ai_client: AIClient) -> str:
    if not resume_text:
        return ""
    log("[Brain] Analyzing resume to generate a robust About section...")
    prompt = f"""
You are an expert Executive Resume Writer. Analyze the following candidate resume and write a robust, highly professional, and engaging LinkedIn 'About' summary.
Do NOT use first-person pronouns like "I" excessively. Keep it under 2000 characters. Focus on their core achievements, domains of expertise, and overall value proposition.

RESUME:
{resume_text}

Output ONLY the final summary text. No introductions or explanations.
"""
    return ai_client.generate_text(prompt)

def enhance_description_with_ai(raw_desc: str, designation: str, company: str, ai_client: AIClient) -> str:
    if not raw_desc:
        return raw_desc
        
    log(f"    [Brain] Formatting ATS bullets for {designation} at {company}...")
    prompt = f"""
You are an expert ATS Resume Writer. Format the following work experience into a highly professional, grammatically correct bulleted list.

Role: {designation} at {company}
Raw Description: {raw_desc}

CRITICAL RULES:
1. PRESERVE EVERY SINGLE DETAIL AND METRIC from the raw description. Do NOT summarize or truncate.
2. DO NOT invent, hallucinate, or add any new software, tools, or technologies.
3. Format as a clean bulleted list using the '-' character. 
4. Output ONLY the formatted text.
"""
    enhanced = ai_client.generate_text(prompt, default_fallback=raw_desc)
    return enhanced if enhanced else raw_desc

def update_headline_and_about(page, profile_content: dict, li_profile_url: str, resume_text: str, ai_client: AIClient):
    log("\n[A] Syncing LinkedIn Headline...")
    intro_edit_url = f"{li_profile_url.rstrip('/')}/edit/intro/"
    try:
        page.goto(intro_edit_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3500)
        
        headline_input = page.locator("input[name='headline'], input[id*='headline'], textarea[name='headline']").first
        if headline_input.is_visible(timeout=5000):
            headline_input.click()
            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            page.keyboard.press(mod_key)
            page.keyboard.press("Backspace")
            
            headline = profile_content.get("naukri_headline", profile_content.get("headline", ""))
            headline_input.fill(headline)
            
            save_btn = page.locator("button:has-text('Save')").first
            if save_btn.is_visible():
                save_btn.click()
                page.wait_for_timeout(2500)
                log("    [OK] Headline updated successfully.")
    except Exception as e:
        log(f"    [!] Failed to update headline: {e}")

    log("\n[B] Syncing LinkedIn About (Summary)...")
    about_edit_url = f"{li_profile_url.rstrip('/')}/edit/forms/summary/new/"
    try:
        page.goto(about_edit_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3500)
        
        about_box = page.locator("div.tiptap.ProseMirror, div[role='textbox'], textarea#summary, textarea").first
        if about_box.is_visible(timeout=5000):
            smart_summary = generate_robust_about_section(resume_text, ai_client)
            if not smart_summary:
                smart_summary = profile_content.get("profile_summary", "")
                
            about_box.click()
            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            page.keyboard.press(mod_key)
            page.keyboard.press("Backspace")
            page.wait_for_timeout(500)
            
            page.keyboard.insert_text(smart_summary)
            page.wait_for_timeout(500)
            
            save_btn = page.locator("button:has-text('Save')").first
            if save_btn.is_visible():
                save_btn.click()
                page.wait_for_timeout(2500)
                log("    [OK] Robust About section injected successfully.")
    except Exception as e:
        log(f"    [!] Failed to update About section: {e}")

def update_experiences(page, cfg_employments: dict, li_profile_url: str, ai_client: AIClient):
    log("\n[C] Scanning and Updating Experience Descriptions...")
    exp_url = f"{li_profile_url.rstrip('/')}/details/experience/"
    
    try:
        page.goto(exp_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        
        edit_buttons = page.locator("a[href*='/edit/']").all()
        urls_to_edit = []
        for btn in edit_buttons:
            href = btn.get_attribute("href")
            if href and ("position" in href or "experience" in href or "forms" in href):
                if href not in urls_to_edit:
                    urls_to_edit.append(href)
                    
        if not urls_to_edit:
            log("    [!] No experience edit buttons found. Profile may have no experiences listed.")
            return

        for edit_url in urls_to_edit:
            full_url = edit_url if edit_url.startswith("http") else f"https://www.linkedin.com{edit_url}"
            try:
                page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)
                
                modal_header = page.locator("h2:has-text('Edit role'), h2:has-text('Edit experience'), h1:has-text('Edit experience')").first
                if not modal_header.is_visible(timeout=6000):
                    log(f"    [!] Edit role modal did not appear in time for {full_url}")
                    continue
                
                # H5 Fix: Deep multi-attribute extraction from the active form
                page_text_blocks = []
                
                title_input = page.locator("input[name='title'], input[id*='title'], input[placeholder*='Title'], input[aria-label*='Title']").first
                if title_input.count() > 0 and title_input.is_visible():
                    val = title_input.input_value() or title_input.get_attribute("value") or ""
                    if val: page_text_blocks.append(val.lower())
                    
                org_input = page.locator("input[name='company'], input[id*='company'], input[placeholder*='Company'], input[placeholder*='Organization'], input[aria-label*='Company']").first
                if org_input.count() > 0 and org_input.is_visible():
                    val = org_input.input_value() or org_input.get_attribute("value") or ""
                    if val: page_text_blocks.append(val.lower())
                
                modal_dialog = page.locator("div[role='dialog'], .artdeco-modal").first
                if modal_dialog.count() > 0 and modal_dialog.is_visible():
                    page_text_blocks.append(modal_dialog.inner_text().lower())
                
                desc_box = page.locator("div.tiptap.ProseMirror, div[contenteditable='true'][role='textbox'], div[contenteditable='true'], textarea#profilePosition-description, textarea").first
                if desc_box.count() > 0 and desc_box.is_visible():
                    page_text_blocks.append(desc_box.inner_text().lower())
                    
                combined_page_text = " || ".join(page_text_blocks)
                
                # Strict H5 word-boundary matching against config roles
                matched_emp_key = None
                for key, emp_data in cfg_employments.items():
                    comp_keyword = emp_data.get("naukri_card_keyword", "").strip().lower()
                    comp_name = emp_data.get("company", "").strip().lower()
                    designation = emp_data.get("designation", "").strip().lower()
                    
                    has_comp_match = False
                    if comp_name and re.search(rf'\b{re.escape(comp_name)}\b', combined_page_text):
                        has_comp_match = True
                    elif comp_keyword and re.search(rf'\b{re.escape(comp_keyword)}\b', combined_page_text):
                        has_comp_match = True
                        
                    has_desig_match = False
                    if designation:
                        # Allow matching primary tokens of designation (e.g. "Manager", "Analyst", "Lead")
                        desig_tokens = [t for t in re.split(r'\W+', designation) if len(t) > 2]
                        if any(re.search(rf'\b{re.escape(tok)}\b', combined_page_text) for tok in desig_tokens):
                            has_desig_match = True
                            
                    if has_comp_match and has_desig_match:
                        matched_emp_key = key
                        break
                        
                if matched_emp_key:
                    target_company = cfg_employments[matched_emp_key].get("company", matched_emp_key)
                    raw_desc = cfg_employments[matched_emp_key].get("description", "")
                    title = cfg_employments[matched_emp_key].get("designation", "")
                    
                    log(f"    -> Matched form to config role: {title} @ {target_company}")
                    polished_desc = enhance_description_with_ai(raw_desc, title, target_company, ai_client)
                    
                    if desc_box.is_visible():
                        desc_box.click(force=True)
                        mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
                        page.keyboard.press(mod_key)
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(300)
                        
                        page.keyboard.insert_text(polished_desc)
                        page.wait_for_timeout(1000)
                        
                        save_btn = page.locator("button:has-text('Save')").first
                        if save_btn.is_visible():
                            save_btn.click()
                            page.wait_for_timeout(3500)
                            log(f"    [OK] Experience updated for {target_company}")
                        else:
                            log(f"    [!] Save button not visible after typing for {target_company}.")
                    else:
                        log(f"    [!] Description input box not found for {target_company}.")
                else:
                    log("    [!] Could not strictly match form contents to any role in candidate_config.json. Skipping modal.")
            except Exception as e:
                log(f"    [!] Failed to update experience at {full_url}: {e}")
    except Exception as e:
        log(f"    [!] Error accessing experience page: {e}")

def update_skills(page, key_skills: list, li_profile_url: str):
    log("\n[D] Syncing Skills Directory...")
    skills_url = f"{li_profile_url.rstrip('/')}/details/skills/"
    
    for skill in key_skills:
        log(f"    Injecting skill: {skill}...")
        try:
            new_skill_url = f"{li_profile_url.rstrip('/')}/details/skills/new/"
            page.goto(new_skill_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            
            inp = page.locator("input[role='combobox'], input[placeholder*='Skill'], input[id*='skill']").first
            
            if not inp.is_visible(timeout=3000):
                page.goto(skills_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)
                add_btn = page.locator("a[href*='new'], button[aria-label*='Add skill'], button:has-text('Add skill')").first
                if add_btn.is_visible():
                    add_btn.click()
                    page.wait_for_timeout(2000)
            
            if inp.is_visible(timeout=4000):
                inp.fill(skill)
                page.wait_for_timeout(2500)
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                
                save_btn = page.locator("button:has-text('Save')").first
                if save_btn.is_visible():
                    save_btn.click()
                    page.wait_for_timeout(2500)
                    log(f"      [OK] Saved '{skill}'.")
                else:
                    log("      [!] Save button not found. Backing out.")
                    page.keyboard.press("Escape")
            else:
                log("      [!] Could not locate skill input box on the form.")
        except Exception as e:
            log(f"      [!] Error updating skill '{skill}': {e}")

def run_sync(profile_path: str):
    print("\n" + "=" * 60, flush=True)
    print("  STEP 3: DYNAMIC LINKEDIN PROFILE SYNC WITH AI ANALYSIS", flush=True)
    print("=" * 60 + "\n", flush=True)
    
    ctx = ProfileContext(profile_path, BASE_DIR)
    config = ctx.config
    ai_client = AIClient(ctx)
    
    cand = config.get("candidate", {})
    profile_content = config.get("profile_content", {})
    employments = profile_content.get("employment", {})
    key_skills = profile_content.get("key_skills", [])
    
    cdp_url = cand.get("cdp_url", "http://127.0.0.1:9222")
    li_profile_url = cand.get("linkedin_profile_url", "")
    resume_text = ctx.resume_text
    
    if not li_profile_url:
        log("[!] Missing 'linkedin_profile_url' in candidate_config.json. Aborting.")
        return

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            log(f"[!] CDP Connection Failed. Ensure Chrome is running on port 9222. Error: {e}")
            return
            
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        
        log("[1/3] Navigating to LinkedIn profile...")
        page.bring_to_front()
        page.goto(li_profile_url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(3000)
        
        update_headline_and_about(page, profile_content, li_profile_url, resume_text, ai_client)
        update_experiences(page, employments, li_profile_url, ai_client)
        if key_skills:
            update_skills(page, key_skills, li_profile_url)
            
        log("\n[2/3] Returning to main profile view...")
        page.goto(li_profile_url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(4000)
        
        log("[3/3] Capturing verification screenshot...")
        screenshot_path = ctx.output_dir / "linkedin_corrected_proof.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        log(f"  Saved screenshot: {screenshot_path.name}")
        
        print("\n" + "=" * 60, flush=True)
        print("  LINKEDIN SYNC COMPLETE", flush=True)
        print("=" * 60, flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None, help="Path to profile directory")
    args, _ = parser.parse_known_args()
    
    run_sync(args.profile)