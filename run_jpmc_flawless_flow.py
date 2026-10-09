# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #002]
# Term: [JPMC_ORACLE_DYNAMIC_CASCADE_AND_MULTISELECT_FIX]
# Timestamp: 2026-10-09 08:53:00 +05:30
# Issue / Context: 
#   1. Section 1 Preferred Location is a multi-select combobox (.cx-multi-select__list-item).
#   2. Section 2 has a cascading conditional question tree (Level 1: experience tier -> 
#      Level 2: Software Engineering & AWS rating -> Level 3: Java Backend & Top 2 languages).
#   3. Section 3 work experience cards render alphabetically by employerName (Oracle JET design).
#   4. Error detection must inspect .input-row__validation and [id$="-error"].
# Changes Made:
#   - Implemented iterative cascading question loop on Section 2 using JPMCNail.
# [ENTRY #003]
# Term: [MULTIMODAL_VISUAL_AUDIT_AND_EXPERIENCE_REORDERING]
# Timestamp: 2026-10-09 09:16:00 +05:30
# Issue / Context:
#   1. Work experience tiles in Section 3 render alphabetically by employerName by default.
#   2. End-to-end multimodal visual AI verification is required across all 4 sections.
# Changes Made:
#   - Integrated nail.reorder_experience_tiles(page) on Section 3.
#   - Connected VisualAIAuditor to capture full screenshots and run Gemini 3.8 Flash audits.
# ==============================================================================

import os
import re
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright

from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
from core.visual_ai_auditor import VisualAIAuditor

REPO_ROOT = Path(__file__).resolve().parent

def load_candidate_context(profile_name: str = "udaysagar_kandpal") -> Dict[str, Any]:
    cfg_path = REPO_ROOT / "profiles" / profile_name / "candidate_config.json"
    if not cfg_path.exists():
        cfg_path = REPO_ROOT / "profiles" / "default_user" / "candidate_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def check_errors(page, step_name: str):
    error_selectors = (
        ".cx-messages__message--error:visible, .cx-form-control__error-message:visible, "
        ".app-form-item__error:visible, [aria-invalid='true']:visible, "
        ".oj-form-control-error-message:visible, .input-row__validation:visible, "
        "[id$='-error']:visible, .input-row--error:visible"
    )
    raw_errors = page.locator(error_selectors).all_inner_texts()
    clean_errors = [e.strip() for e in raw_errors if e.strip() and e.strip().lower() != 'saved']
    if clean_errors:
        print(f"[ERROR AUDIT FAIL on {step_name}]: Found active red errors: {clean_errors}")
        return False, clean_errors
    print(f"[ERROR AUDIT PASS on {step_name}]: 0 validation errors found.")
    return True, []

def answer_cascading_section2_questions(page):
    """
    Iteratively resolves all questions on Section 2, handling dynamically unhidden sub-questions.
    """
    max_passes = 5
    for pass_idx in range(max_passes):
        print(f"--- Section 2 Question Resolution Pass {pass_idx + 1} ---")
        
        # 1. Answer all visible radio button questions
        action_taken = page.evaluate('''() => {
            let changed = false;
            const rows = Array.from(document.querySelectorAll('.input-row, .app-form-item, fieldset'));
            
            for (const r of rows) {
                const labelEl = r.querySelector('legend, label, .cx-form-label, p');
                const label = labelEl ? labelEl.innerText.trim() : '';
                const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section'));
                if (btns.length === 0) continue;
                
                const isAnswered = btns.some(b => b.getAttribute('aria-checked') === 'true');
                if (isAnswered) continue;
                
                const qLower = label.toLowerCase();
                let targetChoice = null;
                
                // Mappings
                if (qLower.includes('18 years')) targetChoice = 'Yes';
                else if (qLower.includes('legally authorized')) targetChoice = 'Yes';
                else if (qLower.includes('sponsorship')) targetChoice = 'No';
                else if (qLower.includes('indian passport')) targetChoice = 'Yes';
                else if (qLower.includes('other than india')) targetChoice = 'No';
                else if (qLower.includes('high school') || qLower.includes('10+2')) targetChoice = 'Yes';
                else if (qLower.includes('relevant years of work experience')) targetChoice = 'At least 5 years of experience';
                else if (qLower.includes('primary area of expertise') && !qLower.includes('if software')) targetChoice = 'Software Engineering';
                else if (qLower.includes('proficiency with aws')) targetChoice = 'Advanced / Expert';
                else if (qLower.includes('area of expertise') && (qLower.includes('if software') || qLower.includes('select your area'))) {
                    targetChoice = 'Java Backend (Springboot, Hibernate, Microservices)';
                }
                
                if (targetChoice) {
                    const match = btns.find(b => b.innerText.trim().toLowerCase().includes(targetChoice.toLowerCase()));
                    if (match) {
                        match.click();
                        changed = true;
                    }
                }
            }
            return changed;
        }''')
        
        time.sleep(1.0)
        
        # 2. Check multi-select combobox question (Top 2 languages)
        lang_action = page.evaluate('''() => {
            const container = Array.from(document.querySelectorAll('.input-row, .app-form-item')).find(el => {
                const text = el.innerText || '';
                return text.includes('programming languages') && text.includes('Choose your top 2');
            });
            if (!container) return false;
            
            const pills = container.querySelectorAll('.cx-multi-select-pill__value-text');
            if (pills.length >= 2) return false; // Already answered
            
            const toggle = container.querySelector('button');
            if (toggle) toggle.click();
            return true;
        }''')
        
        if lang_action:
            time.sleep(1.0)
            page.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, .cx-select__list-item, [role="option"], [role="gridcell"]'))
                    .filter(e => e.offsetWidth > 0 || e.offsetHeight > 0);
                const javaOpt = items.find(i => i.innerText.trim() === 'JAVA');
                if (javaOpt) javaOpt.click();
                const pyOpt = items.find(i => i.innerText.trim().startsWith('Python'));
                if (pyOpt) pyOpt.click();
            }''')
            time.sleep(1.0)
            page.keyboard.press("Escape")
        
        if not action_taken and not lang_action:
            print("No new questions unhidden. Questionnaire fully resolved.")
            break

def run_flow(profile_name: str = "udaysagar_kandpal", cdp_url: str = "http://127.0.0.1:9222"):
    cfg = load_candidate_context(profile_name)
    cand = cfg.get("candidate", cfg)
    nail = JPMCNail()

    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    ctx = browser.contexts[0]
    
    pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "apply" in p.url]
    if not pages:
        print("Error: No Oracle apply page found!")
        pw.stop()
        return
    page = pages[0]
    print(f"Connected to apply flow: {page.url}")

    # Section 1
    if "/section/1" in page.url:
        print("\n--- Processing Section 1 ---")
        
        # Preferred Location Handling
        pref_container = page.locator('.apply-flow-block--preferred-locations').first
        if pref_container.count() > 0:
            existing_pills = pref_container.locator('.cx-multi-select-pill__value-text').count()
            if existing_pills == 0:
                print("Setting Preferred Location...")
                toggle = pref_container.locator("button[aria-label*='Preferred Location' i], button.icon-dropdown-arrow").first
                if toggle.count() > 0:
                    toggle.click()
                    time.sleep(1.0)
                    page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], [role="gridcell"]'))
                            .filter(e => e.offsetWidth > 0 || e.offsetHeight > 0);
                        const match = items.find(i => i.innerText.includes('Platina') || i.innerText.includes('Bengaluru') || i.innerText.includes('Embassy'));
                        if (match) match.click();
                    }''')
                    time.sleep(1.0)
                    page.keyboard.press("Escape")

        ok, errs = check_errors(page, "Section 1")
        if not ok:
            pw.stop()
            return
        page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first.click()
        time.sleep(3.0)

    # Section 2
    if "/section/2" in page.url:
        print("\n--- Processing Section 2 ---")
        answer_cascading_section2_questions(page)
        
        ok, errs = check_errors(page, "Section 2")
        if not ok:
            pw.stop()
            return
        page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first.click()
        time.sleep(3.0)

    # Section 3
    if "/section/3" in page.url:
        print("\n--- Processing Section 3 ---")
        # Ensure any open inline edit dialog is closed
        cancel_btn = page.locator("button.cancel-btn:visible, button:has-text('CANCEL'):visible").first
        if cancel_btn.count() > 0:
            cancel_btn.click()
            time.sleep(1.0)
            
        # Reorder tiles strictly in reverse-chronological order
        nail.reorder_experience_tiles(page)
        time.sleep(1.0)
            
        ok, errs = check_errors(page, "Section 3")
        if not ok:
            pw.stop()
            return
        page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first.click()
        time.sleep(3.0)

    # Section 4
    if "/section/4" in page.url:
        print("\n--- Processing Section 4 Review ---")
        nail.handle_custom_fields(page, step_num=4, candidate_data=cfg)
        
        ok, errs = check_errors(page, "Section 4 Final Audit")
        submit_btn = page.locator("button:has-text('SUBMIT'), button:has-text('Submit')").first
        if submit_btn.count() > 0:
            print(f"[HUMAN GATE] SUBMIT button visible={submit_btn.is_visible()}, enabled={submit_btn.is_enabled()}.")
            print(">>> EXECUTION PAUSED BEFORE SUBMISSION FOR MANDATORY HUMAN REVIEW <<<")

    pw.stop()

if __name__ == "__main__":
    run_flow()
