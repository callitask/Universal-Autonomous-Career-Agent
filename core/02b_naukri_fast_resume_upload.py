#!/usr/bin/env python3
"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - FAST NAUKRI RESUME INJECTION
File: core/02b_naukri_fast_resume_upload.py
================================================================================
Attaches the latest tailored ATS resume directly to the candidate's active
Naukri profile via CDP without touching or modifying profile text fields.
Zero hardcoding: all paths, candidate names, and CDP URLs resolve dynamically.
Leaves the browser ready and focused on the active session without blanking out.
================================================================================
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.utils.profile_context import ProfileContext


def log(msg: str):
    print(f"  {msg}", flush=True)


def run_fast_upload(profile_path: str):
    print("\n" + "=" * 60, flush=True)
    print("  STEP 2: FAST NAUKRI RESUME INJECTION (ZERO PROFILE TOUCH)", flush=True)
    print("=" * 60, flush=True)

    profile_dir = Path(profile_path).resolve() if Path(profile_path).is_absolute() else (BASE_DIR / profile_path).resolve()
    ctx = ProfileContext(profile_path=profile_dir, base_path=BASE_DIR)
    config = ctx.config
    manifest_path = ctx.manifest_path

    if not manifest_path.exists():
        log("[!] Missing search_manifest.json. Aborting resume upload.")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[!] Error reading search_manifest.json: {e}")
        return

    cdp_url = config.get("candidate", {}).get("cdp_url", "http://127.0.0.1:9222")
    resume_to_upload = None

    if manifest and isinstance(manifest, list) and len(manifest) > 0:
        resume_to_upload = manifest[0].get("tailored_pdf") or manifest[0].get("pdf_path")

    # Fallback to newest generated tailored PDF in applications directory
    if not resume_to_upload or not os.path.exists(resume_to_upload):
        apps_dir = ctx.output_dir / "applications"
        if apps_dir.exists():
            pdfs = list(apps_dir.glob("*/*.pdf"))
            if pdfs:
                pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                resume_to_upload = str(pdfs[0].resolve())

    # Fallback to base candidate PDF in profile root
    if not resume_to_upload or not os.path.exists(resume_to_upload):
        cand_name = ctx.candidate_name.replace(" ", "_")
        profile_pdf = profile_dir / f"{cand_name}_Resume.pdf"
        if profile_pdf.exists():
            resume_to_upload = str(profile_pdf.resolve())

    if not resume_to_upload or not os.path.exists(resume_to_upload):
        log("  [!] No valid tailored PDF found. Skipping upload.")
        return

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()

            # Dedicated transient upload page with guaranteed closure
            upload_page = context.new_page()
            try:
                log("  [A] Navigating to Naukri Profile...")
                upload_page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
                upload_page.wait_for_timeout(2500)

                # Check if login is required
                if "login" in upload_page.url.lower():
                    log("  [!] Notice: Naukri session requires login in Chrome.")
                    return

                log(f"  [B] Uploading Tailored ATS Resume: {os.path.basename(resume_to_upload)}")
                file_input = upload_page.locator("input#attachCV, input[type='file'][id*='attachCV'], input[type='file']").first

                # Correct Playwright element detection
                if file_input.count() > 0:
                    file_input.set_input_files(resume_to_upload)
                    upload_page.wait_for_timeout(4000)  # Await processing toast
                    log("  [OK] Successfully updated profile resume with targeted ATS PDF.")
                else:
                    log("  [!] Could not locate file input element on profile page.")
            finally:
                try:
                    upload_page.close()
                except Exception:
                    pass

        except Exception as e:
            log(f"  [!] Fast upload notice: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast Naukri Resume Upload Engine")
    parser.add_argument("--profile", required=True, help="Path to profile directory")
    args = parser.parse_args()
    run_fast_upload(args.profile)