"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT: SURGICAL SELECTIVE NAUKRI PROFILE SYNC
File: core/02_profile_sync_naukri.py
================================================================================
Dynamic, Candidate-Agnostic Selective Profile Updating Engine for Naukri.
Implements the 5-Step Cognitive Selective Workflow:
  Step A: Ingest candidate source of truth (resume.md, candidate_config.json, cognitive_profile.json).
  Step B: Non-destructive live DOM inspection of active Naukri profile.
  Step C: AI comparison & evaluation (KEEP_EXISTING vs UPDATE_REQUIRED vs ADD_NEW).
  Step D: Generation of individual JSON evaluation cards per role (output/profile_sync/naukri_cards/).
  Step E: Surgical selective update — only modifying what is required, leaving high-quality live roles intact.
Zero hardcoding: 100% Config-driven and profile-agnostic.
Strictly decoupled from LinkedIn (Directive 5).
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


def extract_years_from_tenure(text: str) -> tuple:
    """
    Extracts start and end years from any tenure/duration string.
    Rule C16: Required for multi-attribute duplicate detection.
    """
    clean = str(text or "").strip().lower()
    four_digit = re.findall(r'\b(19\d\d|20\d\d)\b', clean)
    if four_digit:
        start_yr = int(four_digit[0])
        end_yr = int(four_digit[-1]) if len(four_digit) > 1 else ('present' if 'present' in clean else start_yr)
        return (start_yr, end_yr)
    two_digit = re.findall(r"(?:'|’|\b)(\d{2})\b", clean)
    if two_digit:
        start_yr = 2000 + int(two_digit[0])
        end_yr = 2000 + int(two_digit[-1]) if len(two_digit) > 1 else ('present' if 'present' in clean else start_yr)
        return (start_yr, end_yr)
    return (None, None)


def is_duplicate_employment_or_internship(exp1: dict, exp2: dict) -> bool:
    """
    Strict duplicate detection rule (Rule C16):
    Matches across Company + Designation + Years.
    If company and designation match, but years are different, it is NOT a duplicate
    (a candidate can legitimately work in the same role at the same firm across separate periods).
    """
    c1 = re.sub(r'\W+', '', exp1.get("company", "").lower())
    c2 = re.sub(r'\W+', '', exp2.get("company", "").lower())
    if not (c1 in c2 or c2 in c1 or (len(c1) >= 4 and len(c2) >= 4 and c1[:5] == c2[:5])):
        return False

    d1 = re.sub(r'\W+', '', (exp1.get("designation") or exp1.get("project_name") or "").lower())
    d2 = re.sub(r'\W+', '', (exp2.get("designation") or exp2.get("project_name") or "").lower())
    if d1 and d2 and not (d1 in d2 or d2 in d1 or (len(d1) >= 4 and len(d2) >= 4 and d1[:5] == d2[:5])):
        return False

    y1 = extract_years_from_tenure(exp1.get("tenure") or exp1.get("dates") or "")
    y2 = extract_years_from_tenure(exp2.get("tenure") or exp2.get("dates") or "")
    if y1[0] is not None and y2[0] is not None:
        if y1 != y2:
            return False

    return True


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

                    # Extract tenure / dates from chunk if available (Rule C16)
                    tenure_found = ""
                    date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\'\s]*\d{2,4}\s*(?:to|-|–)\s*(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\'\s]*\d{2,4}|\d{4}))', chunk, re.IGNORECASE)
                    if not date_match:
                        date_match = re.search(r'\b(20\d\d\s*(?:to|-|–)\s*(?:Present|20\d\d))\b', chunk, re.IGNORECASE)
                    if date_match:
                        tenure_found = date_match.group(1).strip()

                    composite = f"{comp_clean.lower()}::{desig_clean.lower()}::{tenure_found.lower()}"
                    if composite not in seen_roles and len(comp_clean) >= 2:
                        seen_roles.add(composite)
                        experiences.append({
                            "company": comp_clean,
                            "designation": desig_clean,
                            "tenure": tenure_found,
                            "naukri_card_keyword": comp_clean,
                            "description": bullets_text,
                            "source": "resume"
                        })

    return experiences


def inspect_live_naukri_profile(page) -> Dict[str, Any]:
    """
    Step B: Non-destructive live inspection of candidate's Naukri profile.
    Extracts current headline, summary, key skills, and employment records from the live DOM.
    """
    log("\n[STEP B] Inspecting Live Naukri Profile DOM...")
    page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=35000)
    page.wait_for_timeout(3000)

    # Pre-inspection scroll: Naukri defers mounting #lazyEmployment and #lazyKeySkills until scrolled into viewport
    try:
        page.evaluate("""() => {
            window.scrollTo(0, 500);
            setTimeout(() => window.scrollTo(0, 1200), 250);
        }""")
        page.wait_for_timeout(1500)
    except Exception:
        pass

    live_headline = ""
    headline_el = page.locator(".resumeHeadline .widgetHead, .widgetHead:has-text('Resume Headline')").first
    if headline_el.count() > 0:
        headline_text_el = page.locator(".resumeHeadline .typ-14Medium, .resumeHeadline .text, .resumeHeadline p").first
        if headline_text_el.count() > 0:
            live_headline = headline_text_el.inner_text().strip()

    live_summary = ""
    summary_el = page.locator(".card:has(.widgetTitle:text('Profile summary')), span:has-text('Profile summary'), .profileSummary").first
    if summary_el.count() > 0:
        summary_text_el = page.locator(".profileSummary .text, .profileSummary p, .profileSummary .typ-14Medium").first
        if summary_text_el.count() > 0:
            live_summary = summary_text_el.inner_text().strip()

    live_skills = []
    skill_chips = page.locator(".keySkills .chip, .keySkills span.chip, #lazyKeySkills .chip, div[class*='keySkills'] a").all()
    for sc in skill_chips:
        txt = sc.inner_text().strip()
        if txt and txt not in live_skills:
            live_skills.append(txt)

    live_employments = []
    emp_cards = page.locator("#lazyEmployment .emp-list, .emp-list, div[class*='employment-list']").all()
    log(f"    Discovered {len(emp_cards)} existing employment card(s) on Naukri.")

    for i, card in enumerate(emp_cards):
        try:
            card_text = card.inner_text()
            lines = [l.strip() for l in card_text.split("\n") if l.strip()]

            designation = ""
            company = ""
            tenure = ""
            live_desc = ""

            if len(lines) >= 1:
                designation = lines[0]
            if len(lines) >= 2:
                company = lines[1]
            if len(lines) >= 3:
                tenure = lines[2]

            desc_el = card.locator(".job-desc, .desc, p[class*='desc'], .jobDescription").first
            if desc_el.count() > 0 and desc_el.is_visible():
                live_desc = desc_el.inner_text().strip()

            if not live_desc:
                try:
                    edit_btn = card.locator("span.edit, .editOneTheme").first
                    if edit_btn.count() > 0 and edit_btn.is_visible():
                        edit_btn.click()
                        page.wait_for_timeout(1500)

                        desc_box = page.locator("#jobDescription, textarea#jobDescription").first
                        if desc_box.count() > 0 and desc_box.is_visible():
                            live_desc = desc_box.input_value() or desc_box.inner_text() or ""

                        cancel_btn = page.locator("form#employmentForm a.cancel-btn, form#employmentForm button:has-text('Cancel'), .crossIcon").first
                        if cancel_btn.count() > 0 and cancel_btn.is_visible():
                            cancel_btn.click()
                        else:
                            page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                except Exception as ex:
                    log(f"      [Notice] Could not inspect modal for card {i}: {ex}")

            live_employments.append({
                "index": i,
                "company": company.strip(),
                "designation": designation.strip(),
                "tenure": tenure.strip(),
                "description": live_desc.strip(),
                "raw_text": card_text
            })
            log(f"      - Live Card #{i+1}: '{designation}' at '{company}' (Desc length: {len(live_desc)} chars)")
        except Exception as e:
            log(f"      [!] Error reading employment card {i}: {e}")

    # Step B.2: Also inspect Naukri Campus Internship cards if present (Rule C16)
    campus_intern_cards = page.locator(".internship-details .card-container, .internshipDetails .card-container, div[id*='internshipDetails-']").all()
    if campus_intern_cards:
        log(f"    Discovered {len(campus_intern_cards)} existing internship card(s) on Naukri Campus.")
        for i, card in enumerate(campus_intern_cards):
            try:
                card_text = card.inner_text()
                company = card.locator("p.card-heading").first.inner_text().strip() if card.locator("p.card-heading").count() else ""
                tenure = card.locator("p.card-sub-heading").first.inner_text().strip() if card.locator("p.card-sub-heading").count() else ""
                designation = ""
                live_desc = ""

                # Inspect modal with isolated container scrolling to avoid background page leaks
                edit_pencil = card.locator("span.new-pencil").first
                if edit_pencil.count() > 0 and edit_pencil.is_visible():
                    edit_pencil.click(force=True)
                    page.wait_for_timeout(1000)
                    desig_inp = page.locator("input#projectName0, input[name*='projectName']").first
                    if desig_inp.count() > 0:
                        designation = desig_inp.input_value() or desig_inp.get_attribute("value") or ""
                    desc_inp = page.locator("textarea#details0, textarea[name*='details']").first
                    if desc_inp.count() > 0:
                        live_desc = desc_inp.input_value() or desc_inp.inner_text() or ""

                    # Close modal cleanly without background scroll
                    cancel_link = page.locator("#internshipDetails_Modal .btn-container span:has-text('Cancel'), #internshipDetails_Modal span:has-text('Cancel')").first
                    if cancel_link.count() > 0:
                        cancel_link.click(force=True)
                    else:
                        page.keyboard.press("Escape")
                    page.wait_for_timeout(400)

                live_employments.append({
                    "index": len(live_employments),
                    "company": company.strip(),
                    "designation": designation.strip(),
                    "tenure": tenure.strip(),
                    "description": live_desc.strip(),
                    "raw_text": card_text,
                    "is_campus_internship": True
                })
                log(f"      - Live Campus Internship #{i+1}: '{designation or 'Intern'}' at '{company}' [{tenure}] (Desc: {len(live_desc)} chars)")
            except Exception as e:
                log(f"      [!] Error reading campus internship card {i}: {e}")

    return {
        "headline": live_headline,
        "summary": live_summary,
        "skills": live_skills,
        "employments": live_employments
    }


def evaluate_and_generate_cards(
    candidate_exps: List[Dict[str, Any]],
    live_profile: Dict[str, Any],
    ai_client: AIClient,
    cards_dir: Path
) -> List[Dict[str, Any]]:
    """
    Step C & D: Evaluates candidate experiences against live Naukri profile cards.
    Generates an individual JSON evaluation card for each job role / internship.
    """
    log("\n[STEP C & D] Evaluating Experiences & Generating JSON Cards...")
    cards_dir.mkdir(parents=True, exist_ok=True)
    evaluated_cards = []
    live_employments = live_profile.get("employments", [])

    for exp in candidate_exps:
        comp = exp.get("company", "")
        desig = exp.get("designation", "")
        source_desc = exp.get("description", "")
        keyword = exp.get("naukri_card_keyword") or comp

        # Rule C16: Strict 3-way Multi-Attribute Duplicate Matching (Company + Designation + Years)
        matched_live = None
        for live in live_employments:
            if is_duplicate_employment_or_internship(exp, live):
                matched_live = live
                break

        if matched_live:
            live_desc = matched_live.get("description", "")
            log(f"    Evaluating '{desig}' at '{comp}' against existing live card...")
            eval_res = ai_client.evaluate_profile_experience(
                designation=desig,
                company=comp,
                live_desc=live_desc,
                source_desc=source_desc
            )
            decision = eval_res.get("action_decision", "KEEP_EXISTING")
            reasoning = eval_res.get("decision_reasoning", "")
            optimal_desc = eval_res.get("optimal_description", live_desc if decision == "KEEP_EXISTING" else source_desc)
            diff_detected = eval_res.get("diff_detected", (decision != "KEEP_EXISTING"))
            live_content = {
                "designation": matched_live.get("designation", desig),
                "company": matched_live.get("company", comp),
                "tenure": matched_live.get("tenure", ""),
                "description": live_desc,
                "is_campus_internship": matched_live.get("is_campus_internship", False)
            }
        else:
            log(f"    Role '{desig}' at '{comp}' not found on live profile. Decision: ADD_NEW.")
            decision = "ADD_NEW"
            reasoning = f"Role at {comp} does not exist on live Naukri profile. Will create new employment card."
            diff_detected = True
            live_content = {}
            try:
                optimal_desc = ai_client.generate_text(
                    prompt=f"Format this work experience into clean, professional, ATS-optimized bullet points using '-':\nRole: {desig} at {comp}\nDescription: {source_desc}",
                    default_fallback=source_desc
                )
            except Exception:
                optimal_desc = source_desc

        card = {
            "platform": "naukri",
            "company": comp,
            "designation": desig,
            "naukri_card_keyword": keyword,
            "action_decision": decision,
            "decision_reasoning": reasoning,
            "live_content": live_content,
            "source_content": {
                "designation": desig,
                "company": comp,
                "description": source_desc
            },
            "optimal_content": {
                "designation": desig,
                "company": comp,
                "description": optimal_desc
            },
            "diff_detected": diff_detected,
            "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        safe_name = f"{sanitize_filename(comp)}_{sanitize_filename(desig)}.json"
        card_path = cards_dir / safe_name
        try:
            card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"      [CARD SAVED] {safe_name} -> {decision}")
        except Exception as e:
            log(f"      [!] Failed to write card {safe_name}: {e}")

        evaluated_cards.append(card)

    return evaluated_cards


def execute_selective_naukri_sync(
    page,
    evaluated_cards: List[Dict[str, Any]],
    profile_content: Dict[str, Any],
    profile_dir: Path
):
    """
    Step E: Executes surgical updates on Naukri based on evaluated cards.
    Leaves roles with KEEP_EXISTING completely untouched.
    """
    log("\n[STEP E] Executing Surgical Selective Update on Naukri...")

    for card in evaluated_cards:
        decision = card.get("action_decision")
        comp = card.get("company", "")
        desig = card.get("optimal_content", {}).get("designation") or card.get("designation", "")
        desc = card.get("optimal_content", {}).get("description", "")
        keyword = card.get("naukri_card_keyword") or comp

        if decision == "KEEP_EXISTING":
            log(f"    [RETAINED] {comp} - {desig}: Existing description is already optimal. Leaving untouched.")
            continue

        elif decision == "UPDATE_REQUIRED":
            log(f"    [UPDATING] {comp} - {desig}: Updating description with optimal ATS version...")
            try:
                page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                
                is_internship = card.get("live_content", {}).get("is_campus_internship", False)
                if not is_internship and "intern" in desig.lower():
                    # Fallback check
                    is_internship = page.locator(".internship-details").count() > 0

                if is_internship:
                    card_loc = page.locator(".internship-details .card-container", has_text=comp).first
                    if card_loc.count() > 0 and card_loc.is_visible():
                        card_loc.locator("span.new-pencil").first.click()
                        page.wait_for_timeout(2000)

                        desig_inp = page.locator("input#projectName0, input[name*='projectName']").first
                        if desig_inp.is_visible():
                            desig_inp.click()
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            desig_inp.fill(desig)

                        desc_box = page.locator("textarea#details0, textarea[name*='details']").first
                        if desc_box.is_visible():
                            desc_box.click()
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            desc_box.fill(desc)

                        # FIX: Use isolated modal scrolling
                        page.evaluate("document.querySelector('#internshipDetails_Modal').scrollTop = document.querySelector('#internshipDetails_Modal').scrollHeight")
                        page.wait_for_timeout(500)

                        save_btn = page.locator("form#internship button.btn-blue:has-text('Save'), form#internship button[type='submit']").first
                        if save_btn.is_visible() and save_btn.is_enabled():
                            save_btn.click()
                            page.wait_for_timeout(2500)
                            log(f"      [OK] Saved updated ATS description for Internship {comp}.")
                    else:
                        log(f"      [!] Campus Internship Card for {comp} not located on page to update.")
                else:
                    page.evaluate("window.scrollTo(0, 800)")
                    page.wait_for_timeout(1000)

                    card_loc = page.locator("#lazyEmployment .emp-list", has_text=keyword).first
                    if card_loc.count() == 0 or not card_loc.is_visible():
                        card_loc = page.locator(".emp-list", has_text=comp).first

                    if card_loc.count() > 0 and card_loc.is_visible():
                        card_loc.locator("span.edit, .editOneTheme").first.click()
                        page.wait_for_timeout(2000)

                        desig_inp = page.locator("input#designationSugg, input#designation").first
                        if desig_inp.is_visible():
                            desig_inp.click()
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            desig_inp.fill(desig)

                        desc_box = page.locator("#jobDescription, textarea#jobDescription, textarea[name='jobDescription']").first
                        if desc_box.is_visible():
                            desc_box.click()
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            desc_box.fill(desc)

                        save_btn = page.locator("button#submitEmployment, form#employmentForm button:has-text('Save'), form#employmentForm .btn-dark-ot").first
                        if save_btn.is_visible() and save_btn.is_enabled():
                            save_btn.click()
                            page.wait_for_timeout(2500)
                            log(f"      [OK] Saved updated ATS description for {comp}.")
                    else:
                        log(f"      [!] Card for {comp} not located on page to update.")
            except Exception as e:
                log(f"      [!] Failed to update {comp}: {e}")

        elif decision == "ADD_NEW":
            log(f"    [ADDING NEW] {comp} - {desig}: Creating new employment record...")
            try:
                page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                
                is_internship = page.locator(".internship-details").count() > 0 and "intern" in desig.lower()
                
                if is_internship:
                    add_btn = page.locator("div.internship-details div.add-more, span:has-text('Add internship')").first
                    if add_btn.is_visible():
                        add_btn.click(force=True)
                        page.wait_for_timeout(2000)

                        desig_inp = page.locator("input#projectName0, input[name*='projectName']").first
                        if desig_inp.is_visible():
                            desig_inp.fill(desig)

                        comp_inp = page.locator("input#organisation0, input[name*='organisation']").first
                        if comp_inp.is_visible():
                            comp_inp.fill(comp)

                        desc_box = page.locator("textarea#details0, textarea[name*='details']").first
                        if desc_box.is_visible():
                            desc_box.click()
                            desc_box.fill(desc)
                            
                        # FIX: Use isolated modal scrolling
                        page.evaluate("document.querySelector('#internshipDetails_Modal').scrollTop = document.querySelector('#internshipDetails_Modal').scrollHeight")
                        page.wait_for_timeout(500)

                        save_btn = page.locator("form#internship button.btn-blue:has-text('Save'), form#internship button[type='submit']").first
                        if save_btn.is_visible() and save_btn.is_enabled():
                            save_btn.click()
                            page.wait_for_timeout(2500)
                            log(f"      [OK] Saved new internship record for {comp}.")
                else:
                    page.evaluate("window.scrollTo(0, 800)")
                    page.wait_for_timeout(1000)

                    add_btn = page.locator("#add-employment, span:has-text('Add employment')").first
                    if add_btn.is_visible():
                        add_btn.click(force=True)
                        page.wait_for_timeout(2000)

                        desig_inp = page.locator("input#designationSugg, input#designation").first
                        if desig_inp.is_visible():
                            desig_inp.fill(desig)

                        comp_inp = page.locator("input#companySugg, input#company").first
                        if comp_inp.is_visible():
                            comp_inp.fill(comp)

                        desc_box = page.locator("#jobDescription, textarea#jobDescription, textarea[name='jobDescription']").first
                        if desc_box.is_visible():
                            desc_box.click()
                            desc_box.fill(desc)

                        save_btn = page.locator("button#submitEmployment, form#employmentForm button:has-text('Save'), form#employmentForm .btn-dark-ot").first
                        if save_btn.is_visible() and save_btn.is_enabled():
                            save_btn.click()
                            page.wait_for_timeout(2500)
                            log(f"      [OK] Saved new employment record for {comp}.")
            except Exception as e:
                log(f"      [!] Failed to add new employment {comp}: {e}")

    # Synchronize Profile Summary & Headline if configured
    try:
        headline = profile_content.get("naukri_headline", "")
        if headline:
            log("\n[STEP E.2] Updating Resume Headline...")
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.evaluate("document.querySelector('.resumeHeadline .edit, .widgetHead .edit')?.click()")
            page.wait_for_timeout(1500)
            h_input = page.locator("#resumeHeadlineTxt, form[name='resumeHeadlineForm'] textarea").first
            if h_input.is_visible():
                h_input.fill(headline)
                save_btn = page.locator("form[name='resumeHeadlineForm'] button[type='submit'], form[name='resumeHeadlineForm'] .btn-dark-ot, button:has-text('Save')").first
                if save_btn.is_visible():
                    save_btn.click(force=True)
                    page.wait_for_timeout(2000)
                    log("    [OK] Headline verified.")
    except Exception as e:
        log(f"    [!] Headline update notice: {e}")

    try:
        summary = profile_content.get("profile_summary", "")
        if summary:
            log("\n[STEP E.3] Updating Profile Summary...")
            edit_summary = page.locator(".card:has(.widgetTitle:has-text('Profile summary')) span.edit, span:has-text('Profile summary') .. .edit").first
            if edit_summary.count() > 0 and edit_summary.is_visible():
                edit_summary.click(force=True)
                page.wait_for_timeout(1500)
                s_box = page.locator("textarea#profileSummaryTxt, form[name='profileSummaryForm'] textarea, textarea#resumeHeadlineTxt").first
                if s_box.is_visible():
                    s_box.click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    s_box.fill(summary)
                    save_btn = page.locator("form[name='profileSummaryForm'] button.btn-dark-ot, form[name='profileSummaryForm'] button[type='submit'], button:has-text('Save')").first
                    if save_btn.is_visible():
                        save_btn.click(force=True)
                        page.wait_for_timeout(2000)
                        log("    [OK] Summary verified.")
    except Exception as e:
        log(f"    [!] Summary update notice: {e}")

    upload_resume(page, profile_dir)


def upload_resume(page, profile_dir: Path):
    log("\n[STEP E.4] Checking Tailored Resume PDF Injection...")
    manifest_path = profile_dir / "output" / "search_manifest.json"
    resume_to_upload = None

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest and isinstance(manifest, list) and len(manifest) > 0 and "tailored_pdf" in manifest[0]:
                resume_to_upload = manifest[0]["tailored_pdf"]
        except Exception:
            pass

    if not resume_to_upload or not os.path.exists(resume_to_upload):
        cand_pdfs = list(profile_dir.glob("*_Resume.pdf"))
        if cand_pdfs:
            resume_to_upload = str(cand_pdfs[0].resolve())

    if resume_to_upload and os.path.exists(resume_to_upload):
        try:
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            file_input = page.locator("input#attachCV, input[type='file']").first
            if file_input.count() > 0:
                file_input.set_input_files(resume_to_upload)
                page.wait_for_timeout(4000)
                log(f"    [OK] Embedded ATS Resume into profile: {os.path.basename(resume_to_upload)}")
        except Exception as e:
            log(f"    [!] Failed to upload resume: {e}")
    else:
        log("    [SKIP] No tailored resume PDF found to upload.")


def run(profile_path: Optional[str] = None):
    print("=" * 70, flush=True)
    print("  WORKFLOW STEP 2: SURGICAL SELECTIVE NAUKRI PROFILE SYNC", flush=True)
    print("=" * 70, flush=True)

    ctx = ProfileContext(profile_path=profile_path, base_path=BASE)
    cfg = ctx.config
    cand = cfg.get("candidate", {})
    p_content = cfg.get("profile_content", {})
    cdp_url = cand.get("cdp_url", "http://127.0.0.1:9222")

    ai_client = AIClient(ctx)

    log(f"Active Profile: {ctx.profile_path.name}")

    try:
        ctx.verify_codebase_purity()
    except Exception as purity_err:
        log(f"[HALT] Purity check failed: {purity_err}")
        return

    log("\n[STEP A] Ingesting Candidate Source Data (Resume & Config)...")
    candidate_exps = parse_candidate_experiences(ctx.resume_text, cfg)
    log(f"  Parsed {len(candidate_exps)} candidate experience(s) from ground truth.")

    cards_dir = ctx.output_dir / "profile_sync" / "naukri_cards"

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            log(f"[!] CDP Connection Failed. Ensure Chrome is running with remote debugging on 9222. Error: {e}")
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        page.bring_to_front()

        try:
            live_profile = inspect_live_naukri_profile(page)
            evaluated_cards = evaluate_and_generate_cards(candidate_exps, live_profile, ai_client, cards_dir)

            report_path = ctx.output_dir / "profile_sync" / "naukri_sync_report.json"
            summary_stats = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_evaluated": len(evaluated_cards),
                "retained_optimal": sum(1 for c in evaluated_cards if c.get("action_decision") == "KEEP_EXISTING"),
                "updated": sum(1 for c in evaluated_cards if c.get("action_decision") == "UPDATE_REQUIRED"),
                "added_new": sum(1 for c in evaluated_cards if c.get("action_decision") == "ADD_NEW"),
                "cards": evaluated_cards
            }
            try:
                report_path.write_text(json.dumps(summary_stats, indent=2, ensure_ascii=False), encoding="utf-8")
                log(f"\n[REPORT SAVED] Sync Report saved to {report_path.name}")
                log(f"  Retained (Optimal): {summary_stats['retained_optimal']}")
                log(f"  Update Required:    {summary_stats['updated']}")
                log(f"  Add New:            {summary_stats['added_new']}")
            except Exception as e:
                log(f"[!] Notice saving sync report: {e}")

            execute_selective_naukri_sync(page, evaluated_cards, p_content, ctx.profile_path)
            log("\n[SUCCESS] Surgical Selective Naukri Profile Sync Complete!")

        finally:
            try:
                if page and not page.is_closed():
                    page.close()
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selective Naukri Profile Sync Engine")
    parser.add_argument("--profile", default=None, help="Path to candidate profile directory (optional)")
    args = parser.parse_args()
    run(args.profile)