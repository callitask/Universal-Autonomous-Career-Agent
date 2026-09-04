"""
WORKFLOW STEP 2: SURGICAL NAUKRI PROFILE SYNC
=============================================
Updates profile with verified grammar, sets correct designations,
and formats employment experiences into high-impact bulleted lists.
Includes automatic injection of the dynamically tailored ATS Resume PDF 
to the Naukri Profile portal prior to application execution.
100% Config-driven, Zero hardcoding.
"""
import sys
import time
import json
import argparse
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.utils.profile_context import ProfileContext
from ai_client import AIClient

parser = argparse.ArgumentParser()
parser.add_argument("--profile", required=True, help="Path to candidate profile directory")
args, _ = parser.parse_known_args()

PROFILE_DIR = Path(args.profile).resolve() if Path(args.profile).is_absolute() else (BASE / args.profile).resolve()
CTX = ProfileContext(PROFILE_DIR, BASE)
cfg = CTX.config
C = cfg.get("candidate", {})
P = cfg.get("profile_content", {})
EMP = P.get("employment", {})
CDP_URL = C.get("cdp_url", "http://127.0.0.1:9222")

AI_CLIENT = AIClient(CTX)

def log(msg):
    print(f"  {msg}", flush=True)

def enhance_description_with_ai(raw_desc, designation, company):
    """Polishes work experience text strictly preserving all factual data and metrics."""
    if not raw_desc:
        return raw_desc
    
    log(f"    [Brain] Polishing grammar and ATS formatting for {designation} at {company}...")
    prompt = f"""
You are an expert ATS Resume Writer. Format and polish the following work experience into a highly professional, grammatically correct bulleted list.

Role: {designation} at {company}
Raw Description: {raw_desc}

CRITICAL RULES:
1. PRESERVE EVERY SINGLE DETAIL, METRIC, AND BULLET POINT from the raw description. Do NOT summarize, truncate, or delete information.
2. DO NOT invent, hallucinate, or add any new software, tools, or technologies not explicitly present in the raw description.
3. Format as a clean bulleted list using the '-' character. Correct any grammatical errors to sound highly professional.
"""
    try:
        enhanced = AI_CLIENT.generate_text(prompt=prompt, default_fallback=raw_desc)
        if enhanced:
            return enhanced
    except Exception as e:
        log(f"    [!] AI formatting notice: {e}")
    
    return raw_desc

def delete_old_employments(page, old_companies):
    log("\n[A] Scanning for old employment records to delete...")
    for comp in old_companies:
        try:
            card = page.locator(".emp-list", has_text=comp).first
            if card.count() > 0 and card.is_visible():
                card.locator("span.edit, .editOneTheme").first.click()
                page.wait_for_timeout(1500)
                page.locator("a:has-text('Delete'), button:has-text('Delete')").first.click()
                page.wait_for_timeout(1500)
                confirm_btn = page.locator("button:has-text('Delete'), button:has-text('Yes')").first
                if confirm_btn.is_visible():
                    confirm_btn.click()
                page.wait_for_timeout(2500)
                log(f"    [Deleted] Removed old experience: {comp}")
        except Exception:
            pass

def update_key_skills(page, skills):
    log("\n[B] Updating Key Skills...")
    try:
        edit_btn = page.locator("span:has-text('Key skills')").locator('..').locator('.edit, i').first
        edit_btn.click()
        page.wait_for_timeout(2000)
        
        inp = page.locator("input.sugInp, input[placeholder*='skills']").first
        for skill in skills:
            inp.fill(skill)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
            
        page.locator("button").get_by_text("Save", exact=True).first.click(force=True)
        page.wait_for_timeout(2000)
        log("    [OK] Key Skills added successfully.")
    except Exception as e:
        log(f"    [!] Failed to update key skills: {e}")

def add_or_update_company(page, emp_data):
    keyword = emp_data.get("naukri_card_keyword")
    raw_desc = emp_data.get("description", "")
    title = emp_data.get("designation", "")
    company = emp_data.get("company", "")
    
    desc = enhance_description_with_ai(raw_desc, title, company)
    
    log(f"\n[C] Processing Company: {keyword}")
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    
    card = page.locator(".emp-list", has_text=keyword).first
    if card.count() > 0 and card.is_visible():
        log(f"    Card for {keyword} exists. Editing description and designation...")
        card.locator("span.edit, .editOneTheme").first.click()
        page.wait_for_timeout(2000)
        
        desig_inp = page.locator("input#designation").first
        if desig_inp.is_visible():
            desig_inp.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            desig_inp.fill(title)
        
        desc_box = page.locator("#jobDescription").first
        desc_box.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        desc_box.fill(desc)
        page.locator("form#employmentForm button:has-text('Save')").first.click()
        page.wait_for_timeout(2500)
        log(f"    [OK] Saved verified ATS description for {keyword}")
    else:
        log(f"    Card for {keyword} not found. Clicking 'Add employment'...")
        try:
            page.locator("span:has-text('Add employment')").first.click(force=True)
            page.wait_for_timeout(2000)
            
            page.locator("input#designation").fill(title)
            page.locator("input#company").fill(company)
            
            desc_box = page.locator("#jobDescription").first
            desc_box.click()
            desc_box.fill(desc)
            
            save_btn = page.locator("form#employmentForm button:has-text('Save'), button:has-text('Save')").first
            if save_btn.is_visible() and save_btn.is_enabled():
                save_btn.click()
                page.wait_for_timeout(2000)
                log(f"    [OK] Saved employment record for {keyword}")
            else:
                log(f"    [ACTION COMPLETED] Filled employment fields for {keyword}.")
                try:
                    page.wait_for_selector("form#employmentForm", state="detached", timeout=3000)
                    log(f"    [OK] Employment form detached/saved for {keyword}.")
                except Exception:
                    log(f"    [Notice] Employment form remaining open; proceeding without blocking.")
        except Exception as e:
            log(f"    [!] Failed to add {keyword}: {e}")

def upload_resume(page, profile_dir):
    log("\n[F] Uploading Tailored Resume to Naukri Profile...")
    manifest_path = profile_dir / "output" / "search_manifest.json"
    resume_to_upload = None
    
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest and isinstance(manifest, list) and len(manifest) > 0 and "tailored_pdf" in manifest[0]:
                resume_to_upload = manifest[0]["tailored_pdf"]
        except Exception:
            pass
            
    if resume_to_upload and os.path.exists(resume_to_upload):
        try:
            file_input = page.locator("input#attachCV, input[type='file']").first
            file_input.set_input_files(resume_to_upload)
            page.wait_for_timeout(5000)
            log(f"    [OK] Successfully embedded ATS Resume into profile: {os.path.basename(resume_to_upload)}")
        except Exception as e:
            log(f"    [!] Failed to upload resume: {e}")
    else:
        log("    [!] No valid resume PDF found in the active search manifest. Skipping upload.")

def run():
    print("=" * 60)
    print("  STEP 2: ENHANCED NAUKRI PROFILE SYNC")
    print(f"  Active Profile: {PROFILE_DIR.name}")
    print("=" * 60, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "naukri.com" in pg.url), None)
        
        if not page:
            page = ctx.new_page()
        page.bring_to_front()
        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        old_comps = P.get("old_companies_to_delete", [])
        if old_comps:
            delete_old_employments(page, old_comps)

        skills = P.get("key_skills", [])
        if skills:
            update_key_skills(page, skills)
            
        # UPDATE PROFILE SUMMARY
        try:
            log("\n[D] Updating Profile Summary...")
            edit_summary = page.locator("span:has-text('Profile summary')").locator("..").locator(".edit, i").first
            if edit_summary.count() > 0:
                edit_summary.click(force=True)
                page.wait_for_timeout(2000)
                summary_box = page.locator("textarea#resumeHeadlineTxt, textarea#profileSummaryTxt, textarea.materialize-textarea, textarea[placeholder*='summary'], textarea").first
                summary_box.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                summary_box.fill(P.get("profile_summary", P.get("naukri_headline", "")))
                page.locator("button").get_by_text("Save", exact=True).first.click(force=True)
                page.wait_for_timeout(2000)
                log("    [OK] Profile Summary updated successfully.")
            else:
                log("    [!] Profile summary edit button not found.")
        except Exception as e:
            log(f"    [!] Failed to update profile summary: {e}")

        # UPDATE HEADLINE
        try:
            log("\n[E] Updating Resume Headline...")
            page.evaluate("document.querySelector('.resumeHeadline .edit, .widgetHead .edit').click()")
            page.wait_for_timeout(2000)
            page.locator("#resumeHeadlineTxt").fill(P.get("naukri_headline", ""))
            page.locator("button").get_by_text("Save", exact=True).first.click(force=True)
            page.wait_for_timeout(2000)
            log("    [OK] Headline updated successfully.")
        except Exception as e:
            log(f"    [!] Failed to update headline: {e}")

        for emp_key, emp_data in EMP.items():
            add_or_update_company(page, emp_data)
            
        upload_resume(page, PROFILE_DIR)
        log("\n[OK] Naukri Profile Sync Complete!")

if __name__ == "__main__":
    run()