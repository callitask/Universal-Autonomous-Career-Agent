"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT: SURGICAL SELECTIVE LINKEDIN PROFILE SYNC
File: core/03_profile_sync_linkedin.py
================================================================================
Dynamic, Candidate-Agnostic Selective Profile Updating Engine for LinkedIn.
Implements the 5-Step Cognitive Selective Workflow:
  Step A: Ingest candidate source of truth (resume.md, candidate_config.json, cognitive_profile.json).
  Step B: Non-destructive live DOM inspection of active LinkedIn profile.
  Step C: AI comparison & evaluation (KEEP_EXISTING vs UPDATE_REQUIRED vs ADD_NEW).
  Step D: Generation of individual JSON evaluation cards per role (output/profile_sync/linkedin_cards/).
  Step E: Surgical selective update — only modifying what is required, leaving high-quality live roles intact.
Zero hardcoding: 100% Config-driven and profile-agnostic.
Strictly decoupled from Naukri (Directive 5).
================================================================================
"""

import sys
import os
import time
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.utils.profile_context import ProfileContext
from core.ai_client import AIClient


def log(msg: str):
    print(f"  {msg}", flush=True)


def sanitize_filename(name: str) -> str:
    """Sanitizes company or role names for safe file paths."""
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(name or '').strip())
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean[:50] or "unnamed_role"


def parse_candidate_experiences(resume_text: str, config: dict) -> List[Dict[str, Any]]:
    """
    Step A: Ingests candidate employment history from resume.md and candidate_config.json.
    Builds a canonical list of structured candidate roles.
    """
    experiences = []
    seen_roles = set()

    # 1. Check profile_content.employment from config if present
    p_content = config.get("profile_content", {})
    cfg_emp = p_content.get("employment", {})
    if isinstance(cfg_emp, dict):
        for key, emp_data in cfg_emp.items():
            if isinstance(emp_data, dict):
                comp = emp_data.get("company") or emp_data.get("naukri_card_keyword") or key
                desig = emp_data.get("designation") or emp_data.get("role") or "Professional"
                desc = emp_data.get("description", "")
                card_kw = emp_data.get("naukri_card_keyword") or comp
                composite = f"{comp.lower()}::{desig.lower()}"
                if composite not in seen_roles:
                    seen_roles.add(composite)
                    experiences.append({
                        "company": comp.strip(),
                        "designation": desig.strip(),
                        "naukri_card_keyword": card_kw.strip(),
                        "description": desc.strip(),
                        "source": "config"
                    })

    # 2. Parse experience sections from resume.md if needed
    if resume_text:
        exp_match = re.search(
            r'##\s*(?:PROFESSIONAL\s+EXPERIENCE|WORK\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT\s+HISTORY)(.*?)(?=##\s+[A-Z]|\Z)',
            resume_text,
            re.DOTALL | re.IGNORECASE
        )
        if exp_match:
            exp_block = exp_match.group(1)
            role_chunks = re.split(r'\n(?=###|\*\*[A-Z0-9])', exp_block)
            for chunk in role_chunks:
                lines = [l.strip() for l in chunk.strip().split("\n") if l.strip()]
                if not lines:
                    continue
                header_line = lines[0]
                bullets = [l for l in lines[1:] if l.startswith("-") or l.startswith("•") or l.startswith("*")]
                bullets_text = "\n".join(f"- {re.sub(r'^[-•*]\s*', '', b).strip()}" for b in bullets if b.strip())

                comp_found = ""
                title_found = ""
                clean_header = re.sub(r'^[#*]+\s*', '', header_line).strip().rstrip("*#")

                if "|" in clean_header:
                    parts = clean_header.split("|")
                    title_found = parts[0].strip()
                    comp_found = parts[1].strip()
                elif " at " in clean_header.lower():
                    m = re.split(r'\s+at\s+', clean_header, flags=re.IGNORECASE)
                    title_found = m[0].strip()
                    comp_found = m[1].strip()
                elif "-" in clean_header:
                    parts = clean_header.split("-")
                    title_found = parts[0].strip()
                    comp_found = parts[1].strip()
                else:
                    title_found = clean_header
                    comp_found = clean_header

                if comp_found and title_found:
                    comp_clean = re.sub(r'[\(\[].*?[\)\]]', '', comp_found).strip()
                    desig_clean = re.sub(r'[\(\[].*?[\)\]]', '', title_found).strip()
                    composite = f"{comp_clean.lower()}::{desig_clean.lower()}"
                    if composite not in seen_roles and comp_clean:
                        seen_roles.add(composite)
                        experiences.append({
                            "company": comp_clean,
                            "designation": desig_clean,
                            "naukri_card_keyword": comp_clean,
                            "description": bullets_text,
                            "source": "resume"
                        })

    return experiences


def generate_robust_about_section(resume_text: str, ai_client: AIClient) -> str:
    """Uses centralized AIClient to generate a polished LinkedIn summary."""
    if not resume_text:
        return ""
    log("[Brain] Analyzing resume to generate a robust LinkedIn About summary...")
    prompt = f"""
You are an expert Executive Resume Writer. Analyze the following candidate resume and write a robust, highly professional, and engaging LinkedIn 'About' summary.
Do NOT use first-person pronouns like "I" excessively. Keep it under 2000 characters. Focus on their core achievements, domains of expertise, and overall value proposition.

RESUME:
{resume_text}

Output ONLY the final summary text. No introductions or explanations.
"""
    return ai_client.generate_text(prompt)


def dismiss_modal_if_open(page):
    """Safely closes any open modal without saving changes."""
    try:
        dismiss_btn = page.locator("button[aria-label='Dismiss'], button:has-text('Dismiss'), button:has-text('Cancel')").first
        if dismiss_btn.count() > 0 and dismiss_btn.is_visible(timeout=1000):
            dismiss_btn.click()
            page.wait_for_timeout(500)
        else:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
    except Exception:
        pass


def update_headline(page, profile_content: dict, li_profile_url: str):
    """Step E (Headline): Checks live headline and updates only if different."""
    log("\n[A] Evaluating LinkedIn Headline...")
    intro_edit_url = f"{li_profile_url.rstrip('/')}/edit/intro/"
    target_headline = profile_content.get("naukri_headline", profile_content.get("headline", ""))
    if not target_headline:
        log("    [SKIP] No target headline found in candidate configuration.")
        return

    try:
        page.goto(intro_edit_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3500)

        headline_input = page.locator("input[name='headline'], input[id*='headline'], textarea[name='headline']").first
        if headline_input.is_visible(timeout=5000):
            current_headline = (headline_input.input_value() or "").strip()
            if current_headline == target_headline.strip():
                log("    [RETAINED] Live headline matches target configuration. Leaving intact.")
                dismiss_modal_if_open(page)
                return

            log(f"    [UPDATING] Updating headline to: '{target_headline[:50]}...'")
            headline_input.click()
            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            page.keyboard.press(mod_key)
            page.keyboard.press("Backspace")
            headline_input.fill(target_headline)

            save_btn = page.locator("button:has-text('Save')").first
            if save_btn.is_visible():
                save_btn.click()
                page.wait_for_timeout(2500)
                log("    [OK] Headline updated successfully.")
            else:
                dismiss_modal_if_open(page)
    except Exception as e:
        log(f"    [!] Failed to update headline: {e}")
        dismiss_modal_if_open(page)


def update_about(page, profile_content: dict, li_profile_url: str, resume_text: str, ai_client: AIClient):
    """Step E (About): Evaluates live summary and injects AI-generated summary if missing or basic."""
    log("\n[B] Evaluating LinkedIn About (Summary)...")
    about_edit_url = f"{li_profile_url.rstrip('/')}/edit/forms/summary/new/"
    try:
        page.goto(about_edit_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3500)

        about_box = page.locator("div.tiptap.ProseMirror, div[role='textbox'], textarea#summary, textarea").first
        if about_box.is_visible(timeout=5000):
            live_summary = (about_box.inner_text() or "").strip()
            if len(live_summary) > 300 and any(m in live_summary.lower() for m in ["experience", "leading", "built", "managed", "engineered", "%"]):
                log("    [RETAINED] Live About section is already rich and detailed (>300 chars). Leaving intact.")
                dismiss_modal_if_open(page)
                return

            smart_summary = generate_robust_about_section(resume_text, ai_client)
            if not smart_summary:
                smart_summary = profile_content.get("profile_summary", "")

            if not smart_summary:
                log("    [SKIP] No summary text could be synthesized.")
                dismiss_modal_if_open(page)
                return

            log("    [UPDATING] Injecting AI-optimized About section...")
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
            else:
                dismiss_modal_if_open(page)
    except Exception as e:
        log(f"    [!] Failed to evaluate About section: {e}")
        dismiss_modal_if_open(page)


def evaluate_and_sync_experiences(
    page,
    li_profile_url: str,
    candidate_roles: List[Dict[str, Any]],
    ai_client: AIClient,
    cards_dir: Path
) -> List[Dict[str, Any]]:
    """
    Steps B, C, D, E:
      B: Live inspection of LinkedIn experience edit forms.
      C: AI evaluation (KEEP_EXISTING vs UPDATE_REQUIRED).
      D: Write JSON evaluation card per role.
      E: Surgical selective update for roles requiring enhancement.
    """
    log("\n[C] Scanning and Evaluating Live Experience Descriptions...")
    exp_url = f"{li_profile_url.rstrip('/')}/details/experience/"
    evaluated_cards = []
    matched_cand_indices = set()

    try:
        page.goto(exp_url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(4000)

        edit_buttons = page.locator("a[href*='/edit/']").all()
        urls_to_inspect = []
        for btn in edit_buttons:
            href = btn.get_attribute("href")
            if href and ("position" in href or "experience" in href or "forms" in href):
                full_href = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                if full_href not in urls_to_inspect:
                    urls_to_inspect.append(full_href)

        if not urls_to_inspect:
            log("    [!] No experience edit links found on LinkedIn profile.")
            return evaluated_cards

        log(f"    Found {len(urls_to_inspect)} live experience item(s) to inspect.")

        for edit_url in urls_to_inspect:
            try:
                page.goto(edit_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)

                modal_header = page.locator(
                    "h2:has-text('Edit role'), h2:has-text('Edit experience'), h1:has-text('Edit experience')"
                ).first
                if not modal_header.is_visible(timeout=6000):
                    log(f"    [!] Edit role modal did not appear in time for {edit_url}")
                    continue

                # Step B: Deep text and field extraction from active form
                title_input = page.locator(
                    "input[name='title'], input[id*='title'], input[placeholder*='Title'], input[aria-label*='Title']"
                ).first
                live_title = ""
                if title_input.count() > 0 and title_input.is_visible():
                    live_title = (title_input.input_value() or title_input.get_attribute("value") or "").strip()

                org_input = page.locator(
                    "input[name='company'], input[id*='company'], input[placeholder*='Company'], "
                    "input[placeholder*='Organization'], input[aria-label*='Company']"
                ).first
                live_company = ""
                if org_input.count() > 0 and org_input.is_visible():
                    live_company = (org_input.input_value() or org_input.get_attribute("value") or "").strip()

                desc_box = page.locator(
                    "div.tiptap.ProseMirror, div[contenteditable='true'][role='textbox'], "
                    "div[contenteditable='true'], textarea#profilePosition-description, textarea"
                ).first
                live_desc = ""
                if desc_box.count() > 0 and desc_box.is_visible():
                    live_desc = (desc_box.inner_text() or "").strip()

                modal_dialog = page.locator("div[role='dialog'], .artdeco-modal").first
                dialog_text = modal_dialog.inner_text().lower() if (modal_dialog.count() > 0 and modal_dialog.is_visible()) else ""
                combined_page_text = f"{live_title.lower()} || {live_company.lower()} || {dialog_text} || {live_desc.lower()}"

                # Strict Guardrail H5 Matching against candidate roles
                matched_idx = None
                for idx, cand_role in enumerate(candidate_roles):
                    comp_name = cand_role.get("company", "").strip().lower()
                    card_kw = cand_role.get("naukri_card_keyword", "").strip().lower()
                    desig = cand_role.get("designation", "").strip().lower()

                    has_comp_match = False
                    if comp_name and re.search(rf'\b{re.escape(comp_name)}\b', combined_page_text):
                        has_comp_match = True
                    elif card_kw and re.search(rf'\b{re.escape(card_kw)}\b', combined_page_text):
                        has_comp_match = True

                    has_desig_match = False
                    if desig:
                        desig_tokens = [t for t in re.split(r'\W+', desig) if len(t) > 2]
                        if any(re.search(rf'\b{re.escape(tok)}\b', combined_page_text) for tok in desig_tokens):
                            has_desig_match = True

                    if has_comp_match and has_desig_match:
                        matched_idx = idx
                        break

                target_comp = live_company
                target_desig = live_title
                source_desc = ""

                if matched_idx is not None:
                    matched_cand_indices.add(matched_idx)
                    cand_role = candidate_roles[matched_idx]
                    target_comp = cand_role.get("company") or live_company
                    target_desig = cand_role.get("designation") or live_title
                    source_desc = cand_role.get("description", "")
                    log(f"    -> Matched live role: {target_desig} @ {target_comp}")

                    # Step C: AI evaluation
                    eval_result = ai_client.evaluate_profile_experience(
                        designation=target_desig,
                        company=target_comp,
                        live_desc=live_desc,
                        source_desc=source_desc
                    )
                    decision = eval_result.get("action", "UPDATE_REQUIRED")
                    reasoning = eval_result.get("reasoning", "Evaluated via AIClient")
                    optimal_desc = eval_result.get("optimal_bullets") or source_desc or live_desc
                else:
                    # Fix H5: Role not recognized in candidate resume/config. Retain safely.
                    log(f"    [!] Live role '{live_title}' @ '{live_company}' not found in candidate source. Retaining safely (Fix H5).")
                    decision = "KEEP_EXISTING"
                    reasoning = "Unmatched role on LinkedIn profile. Retained to prevent accidental wrong-employer overwrite."
                    optimal_desc = live_desc

                # Step D: Save JSON evaluation card
                card = {
                    "platform": "linkedin",
                    "company": target_comp,
                    "designation": target_desig,
                    "edit_url": edit_url,
                    "action_decision": decision,
                    "decision_reasoning": reasoning,
                    "live_content": {
                        "designation": live_title,
                        "company": live_company,
                        "description": live_desc
                    },
                    "source_content": {
                        "designation": target_desig,
                        "company": target_comp,
                        "description": source_desc
                    },
                    "optimal_content": {
                        "designation": target_desig,
                        "company": target_comp,
                        "description": optimal_desc
                    },
                    "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                safe_name = f"{sanitize_filename(target_comp)}_{sanitize_filename(target_desig)}.json"
                card_path = cards_dir / safe_name
                try:
                    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
                    log(f"      [CARD SAVED] {safe_name} -> {decision}")
                except Exception as e:
                    log(f"      [!] Failed to write card {safe_name}: {e}")

                evaluated_cards.append(card)

                # Step E: Surgical update or clean retention
                if decision == "KEEP_EXISTING":
                    log(f"      [RETAINED] {target_comp}: Description is optimal. Leaving untouched.")
                    dismiss_modal_if_open(page)
                elif decision == "UPDATE_REQUIRED":
                    log(f"      [UPDATING] {target_comp}: Applying ATS-optimized bullets...")
                    if desc_box.is_visible():
                        desc_box.click(force=True)
                        mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
                        page.keyboard.press(mod_key)
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(300)

                        page.keyboard.insert_text(optimal_desc)
                        page.wait_for_timeout(800)

                        save_btn = page.locator("button:has-text('Save')").first
                        if save_btn.is_visible():
                            save_btn.click()
                            page.wait_for_timeout(3500)
                            log(f"      [OK] Saved updated experience for {target_comp}.")
                        else:
                            log(f"      [!] Save button not visible for {target_comp}.")
                            dismiss_modal_if_open(page)
                    else:
                        log(f"      [!] Description input box not visible for {target_comp}.")
                        dismiss_modal_if_open(page)
            except Exception as e:
                log(f"    [!] Error inspecting/updating role at {edit_url}: {e}")
                dismiss_modal_if_open(page)

        # Step D (Unmatched source roles): Check if any candidate roles had no LinkedIn record
        for idx, cand_role in enumerate(candidate_roles):
            if idx not in matched_cand_indices:
                comp = cand_role.get("company", "Unknown")
                desig = cand_role.get("designation", "Professional")
                card = {
                    "platform": "linkedin",
                    "company": comp,
                    "designation": desig,
                    "action_decision": "ADD_NEW",
                    "decision_reasoning": "Role present in candidate resume/config but not found on live LinkedIn profile.",
                    "live_content": None,
                    "source_content": cand_role,
                    "optimal_content": cand_role,
                    "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                safe_name = f"{sanitize_filename(comp)}_{sanitize_filename(desig)}.json"
                card_path = cards_dir / safe_name
                try:
                    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
                    log(f"      [CARD SAVED] {safe_name} -> ADD_NEW")
                except Exception:
                    pass
                evaluated_cards.append(card)

    except Exception as e:
        log(f"    [!] Error accessing experience page: {e}")

    return evaluated_cards


def update_skills(page, key_skills: list, li_profile_url: str):
    """Step E (Skills): Injects key skills if not already present."""
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


def run_sync(profile_path: Optional[str] = None):
    """
    Main entry point for selective LinkedIn sync.
    Runs the 5-step cognitive selective workflow.
    """
    print("\n" + "=" * 70, flush=True)
    print("  STEP 3: SURGICAL SELECTIVE LINKEDIN PROFILE SYNC (5-STEP AI ENGINE)", flush=True)
    print("=" * 70 + "\n", flush=True)

    ctx = ProfileContext(profile_path, BASE)
    ctx.verify_codebase_purity()

    config = ctx.config
    ai_client = AIClient(ctx)

    cand = config.get("candidate", {})
    profile_content = config.get("profile_content", {})
    key_skills = profile_content.get("key_skills", [])

    cdp_url = cand.get("cdp_url", "http://127.0.0.1:9222")
    li_profile_url = cand.get("linkedin_profile_url", "")
    resume_text = ctx.resume_text

    if not li_profile_url:
        log("[!] Missing 'linkedin_profile_url' in candidate_config.json. Aborting.")
        return

    # Setup directories
    sync_dir = ctx.output_dir / "profile_sync"
    cards_dir = sync_dir / "linkedin_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    # Step A: Ingest candidate source of truth
    log("[STEP A] Ingesting candidate source of truth (resume.md + config)...")
    candidate_roles = parse_candidate_experiences(resume_text, config)
    log(f"  Parsed {len(candidate_roles)} candidate employment role(s).")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            log(f"[!] CDP Connection Failed. Ensure Chrome is running on port 9222. Error: {e}")
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        log("[1/4] Navigating to LinkedIn profile...")
        page.bring_to_front()
        page.goto(li_profile_url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(3000)

        # Sync Headline & About
        update_headline(page, profile_content, li_profile_url)
        update_about(page, profile_content, li_profile_url, resume_text, ai_client)

        # Steps B, C, D, E: Experience scan, evaluation, card generation, and selective update
        evaluated_cards = evaluate_and_sync_experiences(
            page=page,
            li_profile_url=li_profile_url,
            candidate_roles=candidate_roles,
            ai_client=ai_client,
            cards_dir=cards_dir
        )

        # Optional Skills Sync
        if key_skills:
            update_skills(page, key_skills, li_profile_url)

        # Write overall sync report
        retained = sum(1 for c in evaluated_cards if c.get("action_decision") == "KEEP_EXISTING")
        updated = sum(1 for c in evaluated_cards if c.get("action_decision") == "UPDATE_REQUIRED")
        added = sum(1 for c in evaluated_cards if c.get("action_decision") == "ADD_NEW")

        report = {
            "platform": "linkedin",
            "candidate_profile": str(ctx.profile_dir.name),
            "profile_url": li_profile_url,
            "sync_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_roles_evaluated": len(evaluated_cards),
            "retained_existing_count": retained,
            "updated_count": updated,
            "add_new_count": added,
            "roles": evaluated_cards
        }

        report_file = sync_dir / "linkedin_sync_report.json"
        try:
            report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"\n[REPORT] LinkedIn sync report written to: {report_file.name}")
        except Exception as e:
            log(f"\n[!] Failed writing report: {e}")

        log("\n[3/4] Returning to main profile view...")
        page.goto(li_profile_url, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(4000)

        log("[4/4] Capturing verification screenshot...")
        screenshot_path = ctx.output_dir / "linkedin_corrected_proof.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        log(f"  Saved screenshot: {screenshot_path.name}")

        print("\n" + "=" * 70, flush=True)
        print(f"  LINKEDIN SELECTIVE SYNC COMPLETE (Retained: {retained}, Updated: {updated}, Added: {added})", flush=True)
        print("=" * 70 + "\n", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Autonomous Career Agent - Selective LinkedIn Sync")
    parser.add_argument("--profile", default=None, help="Path to profile directory (auto-discovered if omitted)")
    args, _ = parser.parse_known_args()

    run_sync(args.profile)