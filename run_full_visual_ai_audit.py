# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# [ENTRY #001]
# Term: [FULL_VISUAL_AI_MULTIMODAL_AUDIT_RUNNER]
# Timestamp: 2026-10-09 09:15:00 +05:30
# Issue / Context:
#   User directive to automate visual verification across all application sections
#   using Gemini Vision API and enforce reverse-chronological experience ordering
#   in Section 3 and Section 4 review screen.
# Changes Made:
#   - Iterates through Section 1, 2, 3, 4 with full screenshot capture.
#   - Calls VisualAIAuditor (gemini-3.8-flash) on each section screenshot.
#   - Applies Knockout VM experience reordering on Section 3.
#   - Cross-checks ground-truth DOM validation errors.
#   - Enforces strict human review gate on Section 4 (never clicks SUBMIT).
# ================================================================================

import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
from core.visual_ai_auditor import VisualAIAuditor

REPO_ROOT = Path(__file__).resolve().parent

def load_candidate_context(profile_name: str = "udaysagar_kandpal"):
    cfg_path = REPO_ROOT / "profiles" / profile_name / "candidate_config.json"
    if not cfg_path.exists():
        cfg_path = REPO_ROOT / "profiles" / "default_user" / "candidate_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def navigate_to_section(page, target_section: int):
    """
    Navigates to the given section number using the train pagination bar.
    """
    if f"/section/{target_section}" in page.url:
        return True
        
    print(f"[NAV] Navigating to Section {target_section}...")
    link = page.locator(f"a.apply-flow-navigation-pages__link[aria-label*='{target_section}' i]").first
    if link.count() > 0 and link.is_visible():
        link.click()
        time.sleep(3.0)
    else:
        # Fallback to general link
        train_step = page.locator(f"a:has-text('{target_section}'), button:has-text('{target_section}')").first
        if train_step.count() > 0 and train_step.is_visible():
            train_step.click()
            time.sleep(3.0)
            
    print(f"[NAV] Now on URL: {page.url}")
    return f"/section/{target_section}" in page.url

def answer_cascading_section2_questions(page):
    """
    Iteratively resolves all questions on Section 2, handling dynamically unhidden sub-questions.
    """
    for pass_idx in range(4):
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
        
        # Languages combobox
        page.evaluate('''() => {
            const container = Array.from(document.querySelectorAll('.input-row, .app-form-item')).find(el => {
                const text = el.innerText || '';
                return text.includes('programming languages') && text.includes('Choose your top 2');
            });
            if (!container) return;
            const pills = container.querySelectorAll('.cx-multi-select-pill__value-text');
            if (pills.length >= 2) return;
            const toggle = container.querySelector('button');
            if (toggle) toggle.click();
        }''')
        time.sleep(0.5)
        page.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"]'))
                .filter(e => e.offsetWidth > 0 || e.offsetHeight > 0);
            const javaOpt = items.find(i => i.innerText.trim() === 'JAVA');
            if (javaOpt) javaOpt.click();
            const pyOpt = items.find(i => i.innerText.trim().startsWith('Python'));
            if (pyOpt) pyOpt.click();
        }''')
        time.sleep(0.5)
        page.keyboard.press("Escape")
        time.sleep(0.5)

def run_end_to_end_audit(profile_name: str = "udaysagar_kandpal", cdp_url: str = "http://127.0.0.1:9222"):
    cfg = load_candidate_context(profile_name)
    nail = JPMCNail()
    auditor = VisualAIAuditor()
    
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    ctx = browser.contexts[0]
    
    pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "apply" in p.url]
    if not pages:
        print("[ERROR] No Oracle apply page found!")
        pw.stop()
        return False
        
    page = pages[0]
    print(f"[CONNECTED] Active page: {page.url}")
    
    screenshot_dir = REPO_ROOT / "screenshots" / "visual_audit"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    audit_results = {}
    
    # -------------------------------------------------------------
    # SECTION 1 AUDIT
    # -------------------------------------------------------------
    print("\n==================================================")
    print(">>> AUDITING SECTION 1 (Personal Info & Location)")
    print("==================================================")
    navigate_to_section(page, 1)
    
    # Ensure Preferred Location is set
    pref_container = page.locator('.apply-flow-block--preferred-locations').first
    if pref_container.count() > 0:
        existing_pills = pref_container.locator('.cx-multi-select-pill__value-text').count()
        if existing_pills == 0:
            print("[SECTION 1] Mounting Preferred Location pill...")
            toggle = pref_container.locator("button[aria-label*='Preferred Location' i], button.icon-dropdown-arrow").first
            if toggle.count() > 0:
                toggle.click()
                time.sleep(1.0)
                page.evaluate('''() => {
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"]'))
                        .filter(e => e.offsetWidth > 0 || e.offsetHeight > 0);
                    const match = items.find(i => i.innerText.includes('Platina') || i.innerText.includes('Bengaluru'));
                    if (match) match.click();
                }''')
                time.sleep(1.0)
                page.keyboard.press("Escape")
    
    dom_ok_1, dom_errs_1 = auditor.verify_dom_errors(page)
    s1_img = auditor.capture_screenshot(page, screenshot_dir / "section_1_audited.png")
    s1_ai_audit = auditor.audit_screenshot(s1_img, 1)
    audit_results["section_1"] = {
        "dom_clean": dom_ok_1,
        "dom_errors": dom_errs_1,
        "ai_audit": s1_ai_audit
    }
    print(f"[SECTION 1 RESULT] DOM Clean: {dom_ok_1} | AI Verdict: {s1_ai_audit.get('overall_verdict')} | Notes: {s1_ai_audit.get('audit_notes')}")
    
    # -------------------------------------------------------------
    # SECTION 2 AUDIT
    # -------------------------------------------------------------
    print("\n==================================================")
    print(">>> AUDITING SECTION 2 (Curated Screening Questions)")
    print("==================================================")
    navigate_to_section(page, 2)
    answer_cascading_section2_questions(page)
    
    dom_ok_2, dom_errs_2 = auditor.verify_dom_errors(page)
    s2_img = auditor.capture_screenshot(page, screenshot_dir / "section_2_audited.png")
    s2_ai_audit = auditor.audit_screenshot(s2_img, 2)
    audit_results["section_2"] = {
        "dom_clean": dom_ok_2,
        "dom_errors": dom_errs_2,
        "ai_audit": s2_ai_audit
    }
    print(f"[SECTION 2 RESULT] DOM Clean: {dom_ok_2} | AI Verdict: {s2_ai_audit.get('overall_verdict')} | Notes: {s2_ai_audit.get('audit_notes')}")
    
    # -------------------------------------------------------------
    # SECTION 3 AUDIT (REORDERING & CHRONOLOGY VERIFICATION)
    # -------------------------------------------------------------
    print("\n==================================================")
    print(">>> AUDITING SECTION 3 (Experience Reordering & Bullets)")
    print("==================================================")
    navigate_to_section(page, 3)
    
    # Reorder tiles strictly in reverse-chronological order
    nail.reorder_experience_tiles(page)
    time.sleep(1.5)
    
    # Check tile sequence in DOM
    tiles = page.locator('.apply-flow-profile-item-tile')
    print(f"[SECTION 3] Rendered Tiles Count: {tiles.count()}")
    for idx in range(tiles.count()):
        print(f"  Tile {idx}: {tiles.nth(idx).inner_text().replace(chr(10), ' | ')[:80]}")
        
    dom_ok_3, dom_errs_3 = auditor.verify_dom_errors(page)
    s3_img = auditor.capture_screenshot(page, screenshot_dir / "section_3_audited.png")
    s3_ai_audit = auditor.audit_screenshot(s3_img, 3)
    audit_results["section_3"] = {
        "dom_clean": dom_ok_3,
        "dom_errors": dom_errs_3,
        "ai_audit": s3_ai_audit
    }
    print(f"[SECTION 3 RESULT] DOM Clean: {dom_ok_3} | AI Verdict: {s3_ai_audit.get('overall_verdict')} | Chronology: {s3_ai_audit.get('section_specific_checks', {}).get('chronological_order_correct')} | Notes: {s3_ai_audit.get('audit_notes')}")
    
    # -------------------------------------------------------------
    # SECTION 4 AUDIT (REVIEW, ATTACHMENTS & HUMAN GATE)
    # -------------------------------------------------------------
    print("\n==================================================")
    print(">>> AUDITING SECTION 4 (Final Review & Human Gate)")
    print("==================================================")
    navigate_to_section(page, 4)
    
    # Verify/set Section 4 fields
    nail.handle_custom_fields(page, step_num=4, candidate_data=cfg)
    time.sleep(1.5)
    
    dom_ok_4, dom_errs_4 = auditor.verify_dom_errors(page)
    s4_img = auditor.capture_screenshot(page, screenshot_dir / "section_4_audited.png")
    s4_ai_audit = auditor.audit_screenshot(s4_img, 4)
    
    # SUBMIT button check (STRICT HUMAN GATE)
    submit_btn = page.locator("button:has-text('SUBMIT'), button:has-text('Submit')").first
    submit_visible = submit_btn.count() > 0 and submit_btn.is_visible()
    submit_enabled = submit_btn.count() > 0 and submit_btn.is_enabled()
    
    audit_results["section_4"] = {
        "dom_clean": dom_ok_4,
        "dom_errors": dom_errs_4,
        "submit_button": {
            "visible": submit_visible,
            "enabled": submit_enabled,
            "clicked": False
        },
        "ai_audit": s4_ai_audit
    }
    print(f"[SECTION 4 RESULT] DOM Clean: {dom_ok_4} | AI Verdict: {s4_ai_audit.get('overall_verdict')} | Submit Enabled: {submit_enabled} (UNCLICKED) | Notes: {s4_ai_audit.get('audit_notes')}")
    
    # Save structured audit report
    report_file = REPO_ROOT / "screenshots" / "visual_audit" / "audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\n[REPORT SAVED] Full audit report written to: {report_file}")
    
    print("\n==================================================")
    print(">>> FINAL MULTIMODAL AUDIT VERDICT <<<")
    print("==================================================")
    all_passed = (
        dom_ok_1 and dom_ok_2 and dom_ok_3 and dom_ok_4
        and s1_ai_audit.get("passed", False)
        and s2_ai_audit.get("passed", False)
        and s3_ai_audit.get("passed", False)
        and s4_ai_audit.get("passed", False)
    )
    print(f"Overall Application State: {'PERFECT / READY FOR OPERATOR REVIEW' if all_passed else 'ATTENTION NEEDED'}")
    print(f"SUBMIT Button State: VISIBLE={submit_visible}, ENABLED={submit_enabled}, CLICKED=FALSE (MANDATORY HUMAN GATE HELD)")
    
    pw.stop()
    return all_passed

if __name__ == "__main__":
    run_end_to_end_audit()
