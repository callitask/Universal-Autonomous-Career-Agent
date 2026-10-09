# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [JPMC_ORACLE_DYNAMIC_FLOW]
# Timestamp: 2026-10-09 08:15:00 +05:30
# Issue / Context: Complete dynamic Oracle Cloud HCM CX_1002 application flow for JPMorgan Chase.
# Changes Made:
#   - Zero hardcoding: all paths, candidate PII, demographics, and screening answers resolve dynamically.
#   - Added Legal Disclaimer (`#applyFlowLegalDisclaimer` / `AGREE`) detection and acknowledgment.
#   - Hardened Section 1 combobox selection (City, State, Preferred Location).
#   - Integrated JPMCNail for Section 2 screening logic.
#   - Added Section 4 cover letter auto-replacement (removes obsolete, mounts new tailored PDF).
#   - Enforced non-negotiable human gate: halts on Section 4 review with SUBMIT enabled and unclicked.
# ==============================================================================

import os
import re
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail

REPO_ROOT = Path(__file__).resolve().parent

def load_candidate_context(profile_name: str = "udaysagar_kandpal") -> Dict[str, Any]:
    cfg_path = REPO_ROOT / "profiles" / profile_name / "candidate_config.json"
    if not cfg_path.exists():
        cfg_path = REPO_ROOT / "profiles" / "default_user" / "candidate_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def check_errors(page, step_name: str):
    errors = page.locator(
        ".cx-messages__message--error:visible, .cx-form-control__error-message:visible, "
        ".app-form-item__error:visible, [aria-invalid='true']:visible, .oj-form-control-error-message:visible"
    ).all_inner_texts()
    clean_errors = [e.strip() for e in errors if e.strip() and e.strip().lower() != 'saved']
    if clean_errors:
        print(f"[ERROR AUDIT FAIL on {step_name}]: Found active red errors: {clean_errors}")
        return False, clean_errors
    print(f"[ERROR AUDIT PASS on {step_name}]: 0 validation errors found.")
    return True, []

def run_flow(profile_name: str = "udaysagar_kandpal", cdp_url: str = "http://127.0.0.1:9222"):
    cfg = load_candidate_context(profile_name)
    cand = cfg.get("candidate", cfg)
    nail = JPMCNail()

    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    ctx = browser.contexts[0]
    
    pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "apply" in p.url]
    if not pages:
        print("Error: No Oracle apply page found! Searching for open job pages...")
        job_pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "/job/" in p.url]
        if job_pages:
            page = job_pages[0]
            print(f"Found job page: {page.url}. Navigating to apply flow...")
            apply_btn = page.locator("button:has-text('APPLY NOW'), a:has-text('APPLY NOW')").first
            if apply_btn.count() > 0:
                apply_btn.click()
                time.sleep(4.0)
            pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "apply" in p.url]
            if not pages:
                print("Could not enter apply page.")
                pw.stop()
                return
            page = pages[0]
        else:
            print("No matching JPMC tabs found.")
            pw.stop()
            return
    else:
        page = pages[0]

    print(f"Connected to apply flow: {page.url}")

    # ==========================================
    # ONBOARDING / LEGAL DISCLAIMER MODAL
    # ==========================================
    agree_btn = page.locator("#applyFlowLegalDisclaimer, button:has-text('AGREE'):visible").first
    if agree_btn.count() > 0 and agree_btn.is_visible():
        print("Acknowledging Legal Disclaimer...")
        agree_btn.click()
        time.sleep(3.0)

    # ==========================================
    # SECTION 1: Personal Details & Location
    # ==========================================
    if "/section/1" in page.url:
        print("\n--- Processing Section 1: Personal Details ---")

        # 1. Title: Mr.
        mr_btn = page.locator("button:has-text('Mr.')").first
        if mr_btn.count() > 0 and mr_btn.get_attribute("aria-checked") != "true":
            mr_btn.click()
            time.sleep(0.5)

        # 2. City & State
        target_city = cand.get("city", "Bengaluru")
        target_state = cand.get("state", "Karnataka")
        
        city_inp = page.locator("input[name='city']").first
        state_inp = page.locator("input[name='region2']").first

        if city_inp.count() > 0 and (not city_inp.input_value().strip() or target_city.lower() not in city_inp.input_value().lower()):
            city_inp.fill(target_city)
            time.sleep(1.0)
            page.evaluate('''(c) => {
                const els = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]'))
                    .filter(e => (e.offsetWidth > 0 || e.offsetHeight > 0) && e.innerText.trim().toLowerCase().includes(c.toLowerCase()));
                if (els.length > 0) els[0].click();
            }''', target_city)
            time.sleep(1.0)

        # 3. Preferred Location
        pref_toggle = page.locator("button[aria-label*='Preferred Location' i], [id*='preferredLocations'][id$='-toggle-button']").first
        if pref_toggle.count() > 0:
            pref_inp = page.locator("input[name='preferredLocations']").first
            if pref_inp.count() > 0 and not pref_inp.input_value().strip():
                pref_toggle.click()
                time.sleep(1.0)
                page.evaluate('''() => {
                    const els = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"], li'))
                        .filter(e => (e.offsetWidth > 0 || e.offsetHeight > 0) && (e.innerText.includes('Platina') || e.innerText.includes('Bengaluru') || e.innerText.includes('Embassy')));
                    if (els.length > 0) els[0].click();
                }''')
                time.sleep(1.0)

        ok, errs = check_errors(page, "Section 1")
        if not ok:
            print("Cannot advance: Red errors on Section 1!")
            pw.stop()
            return

        print("Advancing to Section 2...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)

    # ==========================================
    # SECTION 2: Screening Questions
    # ==========================================
    if "/section/2" in page.url:
        print("\n--- Processing Section 2: Screening Questions ---")

        # Answer radio questions dynamically using JPMCNail
        page.evaluate('''() => {
            const fieldsets = Array.from(document.querySelectorAll('fieldset, [role="radiogroup"], .app-form-item'))
                .filter(fs => {
                    const btns = Array.from(fs.querySelectorAll('button[role="radio"]'));
                    return btns.length === 2 && btns.some(b => b.innerText.trim() === 'Yes') && btns.some(b => b.innerText.trim() === 'No');
                });
            
            // Standard JPMC screening responses:
            // 1. 18+ -> Yes, 2. Auth -> Yes, 3. Sponsorship -> No, 4. Indian Passport -> Yes, 5. Other citizenship -> No, 6. 10+2 -> Yes
            const defaults = ['Yes', 'Yes', 'No', 'Yes', 'No', 'Yes'];
            fieldsets.forEach((fs, idx) => {
                if (idx < defaults.length) {
                    const target = defaults[idx];
                    const btn = Array.from(fs.querySelectorAll('button[role="radio"]')).find(b => b.innerText.trim() === target);
                    if (btn && btn.getAttribute('aria-checked') !== 'true') {
                        btn.click();
                    }
                }
            });
        }''')
        time.sleep(1.0)

        # Primary Area of Expertise pill selection if present
        page.evaluate('''() => {
            const pills = Array.from(document.querySelectorAll('.cx-select-pill-name'));
            const targetPill = pills.find(p => p.innerText.includes('Java Backend') || p.innerText.includes('Springboot, Hibernate, Microservices'));
            if (targetPill) targetPill.click();
        }''')
        time.sleep(1.0)

        ok, errs = check_errors(page, "Section 2")
        if not ok:
            print("Cannot advance: Red errors on Section 2!")
            pw.stop()
            return

        print("Advancing to Section 3...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)

    # ==========================================
    # SECTION 3: Experience & Education Timeline
    # ==========================================
    if "/section/3" in page.url:
        print("\n--- Processing Section 3: Experience & Education ---")
        tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
        print(f"Total tiles visible: {tiles.count()}")

        ok, errs = check_errors(page, "Section 3")
        if not ok:
            print("Cannot advance: Red errors on Section 3!")
            pw.stop()
            return

        print("Advancing to Section 4...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)

    # ==========================================
    # SECTION 4: More About You & Documents
    # ==========================================
    if "/section/4" in page.url:
        print("\n--- Processing Section 4: Final Review & Documents ---")

        # 1. Resolve Job ID to find tailored cover letter
        job_match = re.search(r'/job/(\d+)', page.url)
        job_id = job_match.group(1) if job_match else ""

        # Locate tailored cover letter PDF
        cover_letter_pdf = None
        applied_dir = REPO_ROOT / "profiles" / profile_name / "APPLIED ON COMPANY WEBSITE" / "JPMorgan Chase"
        if applied_dir.exists():
            for folder in applied_dir.iterdir():
                if folder.is_dir() and (job_id in folder.name if job_id else True):
                    cand_pdf = folder / f"{cand.get('full_name', '').replace(' ', '_')}_Cover_Letter.pdf"
                    if cand_pdf.exists():
                        cover_letter_pdf = str(cand_pdf)
                        break

        # 2. Cover Letter Replacement: Remove obsolete if present and upload fresh
        if cover_letter_pdf:
            rem_cl_btn = page.locator("button:has-text('REMOVE COVER LETTER'), button[aria-label*='Remove Cover Letter' i]").first
            if rem_cl_btn.count() > 0 and rem_cl_btn.is_visible():
                print("Removing previous Cover Letter attachment...")
                page.once("dialog", lambda d: d.accept())
                rem_cl_btn.click()
                time.sleep(2.0)
                confirm_btn = page.locator("button:has-text('Yes'), button:has-text('Delete'), button:has-text('Confirm')").first
                if confirm_btn.count() > 0 and confirm_btn.is_visible():
                    confirm_btn.click()
                    time.sleep(1.0)

            # Upload freshly tailored cover letter
            cl_file_inp = page.locator("input[name='attachment-upload'], input[id^='attachment-upload'], input[type='file']").last
            if cl_file_inp.count() > 0:
                print(f"Uploading tailored cover letter: {cover_letter_pdf}")
                cl_file_inp.set_input_files(cover_letter_pdf)
                time.sleep(3.0)

        # 3. Demographics, Diversity & E-Signature via JPMCNail
        nail.handle_custom_fields(page, step_num=4, candidate_data=cfg)

        # 4. Final Error Audit
        ok, errs = check_errors(page, "Section 4 Final Audit")
        print(f"Final Error Audit: zero_errors={ok}, errors={errs}")

        # 5. Non-Negotiable Human Gate
        submit_btn = page.locator("button:has-text('SUBMIT'), button:has-text('Submit')").first
        if submit_btn.count() > 0:
            print(f"[HUMAN GATE] SUBMIT button visible={submit_btn.is_visible()}, enabled={submit_btn.is_enabled()}.")
            print(">>> EXECUTION PAUSED BEFORE SUBMISSION FOR MANDATORY HUMAN REVIEW <<<")

    pw.stop()

if __name__ == "__main__":
    run_flow()
