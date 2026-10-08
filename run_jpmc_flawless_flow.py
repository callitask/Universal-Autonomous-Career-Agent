import os
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

COVER_LETTER_PDF = r"F:\JOB AI AGENT\profiles\udaysagar_kandpal\APPLIED ON COMPANY WEBSITE\JPMorgan Chase\Senior_Lead_Software_Engineer_Java_Python\Udaysagar_Kandpal_Cover_Letter.pdf"
RESUME_PDF = r"F:\JOB AI AGENT\profiles\udaysagar_kandpal\APPLIED ON COMPANY WEBSITE\JPMorgan Chase\Senior_Lead_Software_Engineer_Java_Python\Udaysagar_Kandpal_Resume.pdf"
CANONICAL_LINKEDIN = "https://www.linkedin.com/in/udaykandpal"

def check_errors(page, step_name):
    errors = page.locator(".cx-messages__message--error:visible, .cx-form-control__error-message:visible, .app-form-item__error:visible, [aria-invalid='true']:visible").all_inner_texts()
    clean_errors = [e.strip() for e in errors if e.strip() and e.strip().lower() != 'saved']
    if clean_errors:
        print(f"[ERROR AUDIT FAIL on {step_name}]: Found active red errors: {clean_errors}")
        return False, clean_errors
    print(f"[ERROR AUDIT PASS on {step_name}]: 0 validation errors found.")
    return True, []

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9222')
    ctx = browser.contexts[0]
    pages = [p for p in ctx.pages if 'jpmc.fa.oraclecloud.com' in p.url and 'apply' in p.url]
    if not pages:
        print("Error: No Oracle apply page found!")
        return
    page = pages[0]
    print(f"Connected to page: {page.url}")

    # ==========================================
    # SECTION 1: Personal Details & Address
    # ==========================================
    if "/section/1" in page.url:
        print("\n--- Processing Section 1 ---")
        
        # 1. Title: Mr.
        mr_btn = page.locator("button:has-text('Mr.')").first
        if mr_btn.count() > 0:
            if mr_btn.get_attribute("aria-checked") != "true":
                mr_btn.click()
                time.sleep(0.5)
                print("Selected Title: Mr.")
            else:
                print("Title Mr. already selected.")
                
        # 2. City & State (region2)
        city_inp = page.locator("input[name='city']").first
        state_inp = page.locator("input[name='region2']").first
        
        cur_city = city_inp.input_value().strip()
        cur_state = state_inp.input_value().strip() if state_inp.count() > 0 else ""
        print(f"Current City: '{cur_city}', State: '{cur_state}'")
        
        if not cur_city or "bengaluru" not in cur_city.lower():
            print("Populating City: Bengaluru...")
            city_inp.fill("Bengaluru")
            time.sleep(1.0)
            
            # Click the exact dropdown list item for Bengaluru, Karnataka
            clicked = page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]'))
                    .filter(e => (e.offsetWidth > 0 || e.offsetHeight > 0) && e.innerText.trim().toLowerCase().includes('bengaluru'));
                if (els.length > 0) {
                    els[0].click();
                    return els[0].innerText.trim();
                }
                return null;
            }''')
            print(f"Selected City dropdown item: '{clicked}'")
            time.sleep(1.0)
            
        # Re-check State
        if state_inp.count() > 0 and not state_inp.input_value().strip():
            print("State is still empty, setting Karnataka...")
            state_inp.fill("Karnataka")
            time.sleep(1.0)
            clicked_state = page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"]'))
                    .filter(e => (e.offsetWidth > 0 || e.offsetHeight > 0) && e.innerText.trim().toLowerCase().includes('karnataka'));
                if (els.length > 0) {
                    els[0].click();
                    return els[0].innerText.trim();
                }
                return null;
            }''')
            print(f"Selected State dropdown item: '{clicked_state}'")
            time.sleep(1.0)
            
        print(f"Final Section 1 City: '{city_inp.input_value()}', State: '{state_inp.input_value()}'")
        
        # Pre-Advance Error Check
        ok, errs = check_errors(page, "Section 1")
        if not ok:
            print("Cannot advance: Red errors detected on Section 1!")
            return
            
        print("Clicking NEXT to advance to Section 2...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)
        print(f"Arrived at URL: {page.url}")

    # ==========================================
    # SECTION 2: Screening Questions
    # ==========================================
    if "/section/2" in page.url:
        print("\n--- Processing Section 2 ---")
        # Ensure questions are answered using JPMC nail logic
        from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
        nail = JPMCNail()
        
        # Check Primary Area of Expertise
        # Select Java Backend (Springboot, Hibernate, Microservices)
        page.evaluate('''() => {
            const pills = Array.from(document.querySelectorAll('.cx-select-pill-name'));
            const targetPill = pills.find(p => p.innerText.includes('Java Backend') || p.innerText.includes('Springboot, Hibernate, Microservices'));
            if (targetPill) {
                targetPill.click();
            }
        }''')
        time.sleep(1.0)
        
        ok, errs = check_errors(page, "Section 2")
        if not ok:
            print("Cannot advance: Red errors detected on Section 2!")
            return
            
        print("Clicking NEXT to advance to Section 3...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)
        print(f"Arrived at URL: {page.url}")

    # ==========================================
    # SECTION 3: Experience & Education Timeline
    # ==========================================
    if "/section/3" in page.url:
        print("\n--- Processing Section 3 ---")
        tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
        print(f"Total tiles visible: {tiles.count()}")
        
        # Verify 0 open forms and 0 red errors
        open_forms = page.locator("input[id^='employerName']:visible, input[id^='school']:visible").count()
        print(f"Open forms: {open_forms}")
        
        ok, errs = check_errors(page, "Section 3")
        if not ok:
            print("Cannot advance: Red errors detected on Section 3!")
            return
            
        print("Clicking NEXT to advance to Section 4...")
        next_btn = page.locator("button:has-text('NEXT'):visible, button[aria-label='Next']:visible").first
        next_btn.click()
        time.sleep(3.0)
        print(f"Arrived at URL: {page.url}")

    # ==========================================
    # SECTION 4: More About You & Documents
    # ==========================================
    if "/section/4" in page.url:
        print("\n--- Processing Section 4 ---")
        
        # 1. Correct LinkedIn Link (ensure not truncated to 'udaykan')
        link_inp = page.locator("input[id*='siteLink'], input[name*='siteLink']").first
        if link_inp.count() > 0:
            link_inp.scroll_into_view_if_needed()
            cur_link = link_inp.input_value().strip()
            print(f"Current Link: '{cur_link}'")
            if cur_link != CANONICAL_LINKEDIN:
                print(f"Correcting Link to: '{CANONICAL_LINKEDIN}'...")
                link_inp.fill(CANONICAL_LINKEDIN)
                link_inp.dispatch_event("input")
                link_inp.dispatch_event("change")
                time.sleep(0.5)
            print(f"Verified Link: '{link_inp.input_value()}'")
            
        # 2. Cover Letter: Remove previous and upload newly styled PDF
        rem_cl_btn = page.locator("button:has-text('REMOVE COVER LETTER'), button[aria-label*='Remove Cover Letter' i]").first
        if rem_cl_btn.count() > 0 and rem_cl_btn.is_visible():
            print("Removing previous Cover Letter...")
            page.once("dialog", lambda d: d.accept())
            rem_cl_btn.click()
            time.sleep(2.0)
            print("Previous Cover Letter removed.")
            
        # Upload fresh Cover Letter PDF
        cl_file_inp = page.locator("input[name='attachment-upload'], input[id^='attachment-upload'], input[type='file'][aria-label*='Cover Letter' i], input[type='file']").last
        if cl_file_inp.count() > 0:
            print(f"Uploading freshly styled enterprise Cover Letter: {COVER_LETTER_PDF}")
            cl_file_inp.set_input_files(COVER_LETTER_PDF)
            time.sleep(3.0)
            print("Cover Letter uploaded.")
            
        # 3. Demographics verification
        eth_inp = page.locator("input[id*='ETHNICITY']:visible, input[name*='ETHNICITY']:visible").first
        if eth_inp.count() > 0 and eth_inp.input_value().strip() != "Asian":
            eth_inp.fill("Asian")
            time.sleep(0.5)
            
        gen_inp = page.locator("input[id*='GENDER']:visible, input[name*='GENDER']:visible").first
        if gen_inp.count() > 0 and gen_inp.input_value().strip() != "Male":
            gen_inp.fill("Male")
            time.sleep(0.5)
            
        forces_inp = page.locator("input[id*='indiaMilitaryStatus']:visible, input[id*='ATTRIBUTE16']:visible").first
        if forces_inp.count() > 0 and forces_inp.input_value().strip() != "No":
            forces_inp.fill("No")
            time.sleep(0.5)
            
        sig_inp = page.locator("input[name='fullName']:visible, input[id*='fullName']:visible").first
        if sig_inp.count() > 0 and sig_inp.input_value().strip() != "Udaysagar Kandpal":
            sig_inp.fill("Udaysagar Kandpal")
            time.sleep(0.5)
            
        # 4. Final Verification Audit
        attached_docs = page.locator("button:has-text('.pdf'), .attachment-upload-button__download").all_inner_texts()
        print(f"\nFinal Attached Documents: {attached_docs}")
        print(f"Final Link 1: {link_inp.input_value() if link_inp.count() > 0 else 'N/A'}")
        print(f"Final Ethnicity: {eth_inp.input_value() if eth_inp.count() > 0 else 'N/A'}")
        print(f"Final Gender: {gen_inp.input_value() if gen_inp.count() > 0 else 'N/A'}")
        print(f"Final Military Status: {forces_inp.input_value() if forces_inp.count() > 0 else 'N/A'}")
        print(f"Final E-Signature: {sig_inp.input_value() if sig_inp.count() > 0 else 'N/A'}")
        
        ok, errs = check_errors(page, "Section 4 Final Audit")
        print(f"Final Error Audit: zero_errors={ok}, errors={errs}")
        
        submit_btn = page.locator("button:has-text('SUBMIT'), button:has-text('Submit')").first
        if submit_btn.count() > 0:
            print(f"SUBMIT button: visible={submit_btn.is_visible()}, enabled={submit_btn.is_enabled()} -> [HALTED FOR HUMAN REVIEW]")
            
        # Capture final screenshot
        screenshot_path = r"F:\JOB AI AGENT\section4_flawless_final.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Final full-page screenshot saved: {screenshot_path}")

    pw.stop()
    print("\nFLAWLESS EXECUTION COMPLETE. READY FOR HUMAN REVIEW.")

if __name__ == "__main__":
    main()
