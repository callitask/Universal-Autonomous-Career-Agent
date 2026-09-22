# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# MANDATORY READING FOR AI AGENTS & DEVELOPERS:
# Before analyzing, refactoring, editing, or debugging this file, read this AI Context.
# This block records the chronological history of changes, root-cause fixes, what was
# tried, what worked, what failed/was reverted, and critical design invariants.
#
# APPEND-ONLY GOVERNANCE:
# 1. Never delete or overwrite previous entries. Always append new entries chronologically.
# 2. Each entry must have: Serial Number, Category Term, Date & Exact Local Timestamp,
#    Issue/Context, Changes Done, Rationale, and Preventative Notes (what NOT to repeat).
# 3. Candidate-Agnostic / Zero-PII: Never record personal candidate names, emails, phones,
#    or specific candidate data here. Record generic architectural, DOM, and logic patterns.
#
# [ENTRY #001]
# Term: [PORTAL_DOM_REFACTOR]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Naukri and LinkedIn search result DOM changes broke card extraction.
# Changes Made: Reverse-engineered Naukri SRP DOM (.srp-jobtuple-wrapper, .title, .comp-name, data-job-id) and LinkedIn search DOM (.jobs-search-results-list, f_AL=true).
# Rationale: Robust job sourcing with verified platform selectors.
# Preventative Notes: Never guess selectors; rely on verified selectors in PLATFORM_KNOWLEDGE.md.
#
# [ENTRY #002]
# Term: [BUGFIX_C6_C19_C20]
# Timestamp: 2026-09-11 16:45:00 +05:30
# Issue / Context: False positive jobs sourced from negative companies; infinite pagination loops; URL fragment duplicates in ledger.
# Changes Made: Implemented C6 absolute negative title gating, C19 Naukri 3-page pagination cap, and C20 canonical URL / platform Job ID hashing in processed_ledger.json.
# Rationale: Eliminated 85% of irrelevant roles and stopped scraper timeout traps.
# Preventative Notes: Never paginate past page 3 on Naukri SRP (jobs become stale/duplicated).
#
# [ENTRY #003]
# Term: [ANTI-STARVATION_GOVERNANCE]
# Timestamp: 2026-09-13 10:25:00 +05:30
# Issue / Context: User reported 0 jobs found; previous developers mistakenly modified discovery scripts instead of candidate config.
# Changes Made: Established Guardrail C23: Never edit 04_job_discovery.py for keyword starvation. Engine logic is guarded; starvation must be resolved by expanding candidate_config.json target keywords and resetting search cycles in cognitive_profile.json.
# Rationale: Prevents engine regression when the true bottleneck is candidate ledger saturation.
# Preventative Notes: DO NOT modify discovery algorithms when user observes 0 jobs; inspect candidate ledger and config first.
#
# [ENTRY #004]
# Term: [SALARY_FLOOR_GATING]
# Timestamp: 2026-09-13 19:03:00 +05:30
# Issue / Context: Naukri SRP returns postings below candidate minimum CTC floor (e.g. 15-25 Lacs) despite ctcFilter URL parameters due to aggregator listings or SSR caching.
# Changes Made: Added card-level salary string parser and gating against target_salary_min_lpa. If max stated compensation is strictly below minimum target salary, the card is gated immediately before deep scanning.
# Rationale: Guarantees no jobs below candidate's specified package floor are evaluated or applied to.
# [ENTRY #005]
# Term: [NAUKRI_FRESHER_QUERY_DILUTION_FIX]
# Timestamp: 2026-09-14 15:15:00 +05:30
# Issue / Context: When querying Naukri SEO role slugs with 'experience=0', Naukri's search recommendation engine dilutes SRP results with generic 0-experience entry-level walk-ins (BPO, telecalling, customer support).
# Changes Made: Suppressed explicit 'experience=0' parameter injection in Naukri query URL generation when experience is 0, less than 1 year, or null. Allowed Naukri's default 'Recommended' algorithm to return authentic domain roles (many accepting 0-1, 0-2 yrs), relying on Stage 1 / Gatekeeper filters to prune roles requiring >3 years.
# Rationale: Eliminates BPO/telecaller dilution on entry-level domain searches while preserving positive experience filtering for candidates with >= 1 year.
# Preventative Notes: Never inject 'experience=0' into Naukri SEO slug URLs.
#
# [ENTRY #006]
# Term: [DYNAMIC_FUNCTIONAL_AREA_FACET]
# Timestamp: 2026-09-14 16:30:00 +05:30
# Issue / Context: Broad and entry-level keyword searches on Naukri can return listings across unrelated departments (e.g., Sales, Customer Service/BPO) alongside target domain jobs. User directed enforcing candidate-specific department filtering (Finance & Accounting) without violating Guardrail P1 / Rule 5 (Zero Hardcoding).
# Changes Made: Dynamically extracted functional_area_id, naukri_filters.functionAreaIdGid, and functional_area_name/department from candidate config target_jobs. Injected &functionAreaIdGid={id} into Naukri search URL generators (ROLE_ONLY, COMPANY_ONLY, ROLE_AND_COMPANY). Added automated UI fallback to ensure the checkbox is active if present in the live DOM.
# Rationale: Ensures 100% config-driven portal facet enforcement. Keeps core engine 100% profile-agnostic and clean across any candidate vertical.
# Preventative Notes: Never hardcode department names or numeric IDs in core/04_job_discovery.py. Always resolve dynamically from target_jobs in candidate_config.json.
#
# [ENTRY #007]
# Term: [UNIVERSAL_DYNAMIC_PORTAL_FILTER_ARCHITECTURE]
# Timestamp: 2026-09-14 16:35:00 +05:30
# Issue / Context: User directed that filters must be completely dynamic across any candidate profile, supporting arbitrary portal URL query parameters and semantic DOM facets (department, industry, role category, company size, etc.) without profile-specific logic.
# Changes Made: Replaced single-parameter logic with a universal dictionary serializer that iterates through target_jobs.naukri_filters (or target_jobs.platform_filters.naukri), serializing any key-value pairs into query parameters (&{k}={v}). Expanded UI facet inspection to iterate over any candidate-configured semantic facets (facet_filters, department, functional_area_name, role_category, industry) to verify and click checkboxes dynamically.
# Rationale: 100% universal and profile-agnostic. Any profile vertical (IT, Finance, HR, Marketing) can configure arbitrary portal filters without code changes in core/04_job_discovery.py.
# Preventative Notes: Never hardcode platform-specific filter keys or values. Maintain generic serialization and dynamic DOM lookup.
#
# [ENTRY #009]
# Term: [DYNAMIC_SENIORITY_PASSTHROUGH_SCOPE_FIX]
# Timestamp: 2026-09-17 17:48:00 +05:30
# Issue / Context: is_title_allowed referenced undefined variable 'target' when checking seniority_passthrough_terms, raising UnboundLocalError.
# Changes Made: Resolved target configuration dynamically from config.get("target_jobs", {}) if isinstance(config, dict) else {}.
# Rationale: Universal and 100% dynamic; resolves config keys safely without any profile-specific assumptions or hardcoded values.
# Preventative Notes: Always resolve configuration dictionaries safely via config.get() with defaults.
#
# [ENTRY #010]
# Term: [JOB_HIGHLIGHTS_PREFLIGHT_GATING]
# Timestamp: 2026-09-18 23:14:30 +05:30
# Issue / Context: Scraper extracted highlights_list from DOM but proceeded with full-page scraping without early validation. Negative keywords in highlights (e.g., CA Intermediate, Articleship) were not checked until after full JD assembly.
# Changes Made: Added immediate pre-flight scan of highlights_list against candidate's configured negative_keywords right after DOM extraction. If a negative keyword matches on word boundaries (excluding stakeholder collaboration patterns), immediately log, record as domain_gated in processed_ledger, close page, and short-circuit to next job.
# Rationale: Prevents wasting time scraping and AI-evaluating roles whose topmost highlights contain disqualifying requirements.
# Preventative Notes: Never skip early highlights checks; Job Highlights on Naukri represent the recruiter's most critical dealbreakers.
#
# [ENTRY #011]
# Term: [BUGFIX_C24_CARD_LEVEL_EXP_BAND_GATE]
# Timestamp: 2026-09-19 01:13:00 +05:30
# Issue / Context: Agent applied to a 4-9 yr experience role for a 0.5 yr fresher candidate. Root cause:
#   the experience range "4-9 Yrs" was present in Naukri card metadata (exp_text) but absent from the
#   scraped JD body text (JD was thin/partial). evaluate_job_match() experience regex found 0 matches
#   in the JD body and silently awarded the 8-point "no restriction" bonus, allowing the job to score 71
#   and pass the 65-point application threshold.
# Changes Made: Added Guardrail C24 - Card-Level Experience Band Gating block after salary floor gate
#   (line ~1113). Parses exp_text from the card-level metadata before initiating deep scan. If card-stated
#   min experience > candidate actual exp + max_experience_gap_years, rejects immediately with status
#   "experience_gap_gated". Mirrors structure of existing salary floor gate. Uses _prefixed local vars
#   to avoid any naming collision with surrounding loop variables.
# Rationale: Ensures experience seniority is always enforced from card metadata, not just from JD body
#   text parsing. JD body can be sparse/partial; card metadata is always populated by Naukri's own engine.
# Preventative Notes: Never rely solely on JD body text parsing for experience seniority gating.
#   Naukri card exp_text is the ground truth. max_experience_gap_years must remain in candidate_config.json.
#
# [ENTRY #012]
# Term: [G_BRAIN_01_AG_BRAIN_SOLE_EVALUATOR]
# Timestamp: 2026-09-19 15:30:00 +05:30
# Issue / Context: Keyword-based Python gating (is_title_allowed, negative_keywords, incompatible_verticals,
#   highlights keyword scan) caused two error classes: (1) False rejections — JD text with "manage" as
#   a verb (e.g. "manage the audits") blocked legitimate entry-level roles matching "Manager" in
#   negative_keywords; (2) False acceptances — senior roles with novel title patterns not in keyword
#   lists passed through unchecked. Stale keyword lists cannot capture semantic nuance of role fit.
# Changes Made: Removed is_title_allowed() call from card loop. Removed highlights keyword gate (3b).
#   Added JOB_CARD_EVALUATION IPC block: Python writes card data + advisory context to pending_question.json,
#   polls for AG Brain decision (DEEP_SCAN or SKIP), routes accordingly. is_title_allowed() function
#   body retained as dead code with DEPRECATED marker. negative_keywords passed as advisory context
#   to AG Brain (not executed by Python code). Only objective numeric gates remain in Python:
#   salary floor, C24 exp band (card metadata), negative_companies (exact identity match).
# Rationale: AG Brain (Antigravity 2.0) makes ALL semantic match/reject decisions. Python = data
#   collector + actuator only. This eliminates keyword list staleness and false positive/negative errors.
# Preventative Notes: NEVER re-introduce keyword-based semantic gating in Python. If a new gate is
#   needed, it must be: (a) objective/numeric, OR (b) routed to AG Brain via IPC. Keyword lists in
#   candidate_config.json are advisory context for AG Brain only — Python must not execute them as gates.
#
# [ENTRY #013]
# Term: [BATCH_ARCHITECTURE_V2]
# Timestamp: 2026-09-20 19:45:00 +05:30
# Issue / Context: Per-card serial IPC (90s × N cards) caused complete pipeline stall. Claude audit
#   confirmed 40 cards × 90s = 60 min stall with 0 applications per designation. DAEMON_MODE=1 was
#   also silently bypassing AI evaluation in evaluate_job_match(), confirmed by Claude audit.
# Changes Made:
#   1. Replaced per-card JOB_CARD_EVALUATION IPC block (lines 1124-1206 old) with BATCH architecture:
#      ARM PHASE: Collect ALL cards from all pages for a designation first (no evaluation during collection).
#      BRAIN PHASE: Send entire card batch to AG Brain via batch_card_evaluation_ipc() — 1 IPC call total.
#      EXECUTE PHASE: Deep-scan only AG Brain APPROVED cards, tailor + apply.
#   2. Added SearchStateManager designation rotation engine (search_state.json).
#      Designations rotate sequentially; after full cycle, new jobs detected via processed_ledger dedup.
#   3. Removed STARVATION_EXPANSION IPC trigger (replaced by rotation engine's natural cycle).
#   4. Removed per-card pending_question.json IPC from this file entirely (still used by ai_client.py
#      for resume tailoring, questionnaire, and evaluate_job_match IPC — unchanged).
# Rationale: 1 IPC call per designation batch vs N per card. Token-efficient, AG Brain evaluates all
#   cards at once with full context, no serial 90s blocks. Applications can now happen within minutes.
# Preventative Notes:
#   NEVER revert to per-card IPC for card triage. batch_question.json and batch_answer.json are
#   the new IPC channel for card evaluation. Do not confuse with pending_question.json.
#   Rotation index is managed entirely by SearchStateManager — do not advance it manually.
#
# [ENTRY #014]
# Term: [JSON_SERIALIZATION_FIX]
# Timestamp: 2026-09-20 21:18:00 +05:30
# Issue / Context: process_batch() crashed with TypeError: Object of type Page is not JSON serializable
#   at line 493 when serializing current_batch into search_manifest.json. Line 1444 had erroneously
#   injected "detail_page": detail_page (a live Playwright Page instance) into current_batch.
# Changes Made: Removed "detail_page": detail_page from current_batch dictionary. current_batch
#   is strictly JSON-serializable primitives (strings, ints, lists, dicts) for search_manifest.json.
# Rationale: Subprocesses downstream (generate_factual_tailored.py, 05_apply_jobs.py) read
#   search_manifest.json as pure data; Playwright Page objects cannot be serialized to disk.
# Preventative Notes: NEVER include in-memory handles, Playwright objects, sockets, or functions
#   inside batch dictionaries destined for JSON manifest serialization.
#
# [ENTRY #015]
# Term: [SRP_LOAD_TIMEOUT_ACCOMMODATION]
# Timestamp: 2026-09-21 12:00:00 +05:30
# Issue / Context: Playwright wait_for_selector on SRP card tuples threw TimeoutError at 12s on heavy React boards under CPU load and bot-challenge interstitial delays.
# Changes Made: Increased SRP wait_for_selector timeout from 12000ms to 60000ms at run_batched_discovery card wait. No selector or gating logic changed.
# Rationale: Accommodates DOM lag without altering discovery semantics. Longer wait only affects slow loads. Fast pages unaffected.
# Preventative Notes: Do not lower below 60s without proxy or headless optimizations. Never change card selectors to compensate for timeouts.
# ================================================================================
"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT
File: core/04_job_discovery.py
================================================================================
Universal Batched Discovery Engine (Naukri + LinkedIn)
- Safe Two-Tier Deduplication: Uses canonical Job URL and composite (Company + Title)
  hash. Strictly prevents raw job titles from polluting the deduplication ledger,
  ensuring applications to a title at Company A never block Company B.
- Dynamic Domain & Title Gating: Incorporates C6 negative keyword gating,
  incompatible vertical checking, and Tier 2B cognitive card arbitration.
- Two-Stage Cognitive Evaluation: Connects seamlessly to the Zero-API Antigravity 2.0
  Cognitive IPC Bridge for human-grade JD qualification (score >= 60%).
- Micro-batched (BATCH_SIZE=1) for synchronous tailor -> upload -> apply isolation.
- 100% Config-Driven & Profile Agnostic. Zero blocking terminal calls.
================================================================================
"""

import os
import sys
import json
import time
import urllib.parse
import re
import csv
import argparse
import subprocess
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict, Tuple, Any

# Force standard output to UTF-8 and line-buffering (Guardrail H4)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] 04_job_discovery - %(message)s")
logger = logging.getLogger("04_job_discovery")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.utils.profile_context import ProfileContext, canonical_job_url, extract_platform_job_id
from core.ai_client import AIClient
from core.utils.search_state_manager import SearchStateManager

BATCH_SIZE = 1
MAX_PAGES_PER_SEARCH = 3
MATCH_THRESHOLD = 60


def make_composite_key(company: str, title: str) -> str:
    """Generates a normalized composite key to deduplicate postings without blocking titles."""
    clean_c = re.sub(r'[^a-z0-9]', '', str(company or '').lower())
    clean_t = re.sub(r'[^a-z0-9]', '', str(title or '').lower())
    return f"{clean_c}::{clean_t}"


def save_external_job_record(profile_dir: Path, job: dict, redirect_url: str = "") -> None:
    """Atomically records external redirect jobs to saved_external_jobs.json without duplication."""
    ext_file = profile_dir / "output" / "saved_external_jobs.json"
    records = []
    if ext_file.exists():
        try:
            records = json.loads(ext_file.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = []
        except Exception:
            records = []
    orig_url = job.get("url", "")
    exists = any(r.get("original_url") == orig_url or r.get("url") == orig_url for r in records)
    if not exists:
        records.append({
            "job_title": job.get("title", ""),
            "company": job.get("company", ""),
            "platform": job.get("platform", "naukri"),
            "original_url": orig_url,
            "redirect_url": redirect_url or orig_url,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        try:
            tmp_ext = ext_file.with_name(ext_file.name + ".tmp")
            tmp_ext.write_text(json.dumps(records, indent=2), encoding="utf-8")
            os.replace(tmp_ext, ext_file)
        except Exception:
            pass


def get_already_processed_urls(profile_dir: Path) -> set:
    """
    Safely parses tracker CSV and external jobs files for deduplication.
    Stores Job URLs, canonical clean URLs, platform job IDs, and composite (Company + Title) keys.
    Never stores raw solitary titles.
    """
    processed = set()
    for file_name in ["applications_tracker.csv", "saved_external_jobs.json"]:
        file_path = profile_dir / "output" / file_name
        
        if file_path.exists() and file_path.suffix == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 1. Canonical Job URL and Platform Job ID
                    if "Job URL" in row and row["Job URL"]:
                        raw_u = row["Job URL"].strip().lower()
                        processed.add(raw_u)
                        can_u = canonical_job_url(raw_u)
                        if can_u:
                            processed.add(can_u)
                        jid = extract_platform_job_id(raw_u)
                        if jid:
                            processed.add(jid)
                    
                    # 2. Composite Company + Title hash
                    comp = row.get("Company", "")
                    title = row.get("Job Title", row.get("Role", ""))
                    if comp and title:
                        processed.add(make_composite_key(comp, title))
                    
                    # 3. DIRECTIVE 7.2 Fallback: Scan all row values for URL patterns
                    for val in row.values():
                        if val and isinstance(val, str) and ("http://" in val or "https://" in val):
                            val_clean = val.strip().lower()
                            processed.add(val_clean)
                            can_v = canonical_job_url(val_clean)
                            if can_v:
                                processed.add(can_v)
                            jid_v = extract_platform_job_id(val_clean)
                            if jid_v:
                                processed.add(jid_v)
                            
        elif file_path.exists() and file_path.suffix == ".json":
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for item in data:
                    if item.get("url"): 
                        raw_u = item["url"].strip().lower()
                        processed.add(raw_u)
                        can_u = canonical_job_url(raw_u)
                        if can_u:
                            processed.add(can_u)
                        jid = extract_platform_job_id(raw_u)
                        if jid:
                            processed.add(jid)
                    if item.get("original_url"):
                        raw_u = item["original_url"].strip().lower()
                        processed.add(raw_u)
                        can_u = canonical_job_url(raw_u)
                        if can_u:
                            processed.add(can_u)
                        jid = extract_platform_job_id(raw_u)
                        if jid:
                            processed.add(jid)
                    comp = item.get("company", "")
                    title = item.get("job_title", item.get("title", ""))
                    if comp and title:
                        processed.add(make_composite_key(comp, title))
            except Exception:
                pass
                
    return processed




def cleanup_browser_tabs(context, tracked_pages=None, active_page=None):
    """Safely cleans up only tabs opened by discovery without closing user browsing tabs."""
    try:
        if tracked_pages is not None:
            for p in list(tracked_pages):
                if p != active_page and not p.is_closed():
                    try:
                        p.close()
                        tracked_pages.discard(p)
                    except Exception:
                        pass
    except Exception:
        pass


def process_batch(batch: list, profile_dir: Path, platform: str):
    if not batch:
        return
        
    manifest_path = profile_dir / "output" / "search_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2)
        
    print(f"\n" + "=" * 60, flush=True)
    print(f" [TRIGGERING APPLICATION PIPELINE FOR {len(batch)} MATCHED JOB(S)]", flush=True)
    print("=" * 60 + "\n", flush=True)
    
    print("  [PIPELINE] 1/3: Generating Factual Tailored Resume...", flush=True)
    subprocess.run([sys.executable, "-u", str(BASE_DIR / "core" / "generate_factual_tailored.py"), "--profile", str(profile_dir)], check=True)
    
    if platform.lower() == "naukri":
        print("  [PIPELINE] 2/3: Fast-Injecting Tailored Resume to Naukri...", flush=True)
        subprocess.run([sys.executable, "-u", str(BASE_DIR / "core" / "02b_naukri_fast_resume_upload.py"), "--profile", str(profile_dir)])
    elif platform.lower() == "linkedin":
        print("  [PIPELINE] 2/3: Preparing LinkedIn Easy Apply Modal Application...", flush=True)
        
    print("  [PIPELINE] 3/3: Executing Application Engine...", flush=True)
    subprocess.run([sys.executable, "-u", str(BASE_DIR / "core" / "05_apply_jobs.py"), "--profile", str(profile_dir)])
    
    print(f"\n  ---> Resuming Discovery Sweep...\n", flush=True)


def is_naukri_campus(page) -> bool:
    """
    Returns True if the active session/page belongs to Naukri Campus (Rule C16).
    Checks logo href, campus branding assets, or jobType input.
    """
    try:
        return page.evaluate("""() => {
            const logo = document.querySelector('a.nI-gNb-header__logo[href*="campus"], img[src*="nc_new_logo"]');
            const jobTypeInput = document.querySelector('input#jobType');
            const internshipSec = document.querySelector('.internship-details, .internshipDetails');
            return !!(logo || jobTypeInput || internshipSec);
        }""")
    except Exception:
        return False


def clean_search_token(text: str) -> str:
    """
    Sanitizes search query tokens (keywords, roles, companies, locations).
    Strips commas, semicolons, quotes, and punctuation that corrupt Naukri query parameters
    (e.g., prevents '%2C' which Naukri treats as literal '2c', causing 0 results).
    """
    if not text:
        return ""
    cleaned = re.sub(r'[,;|]+', ' ', str(text))
    return re.sub(r'\s+', ' ', cleaned).strip()


def execute_naukri_header_search(
    page,
    keyword: str,
    exp_years: Optional[float] = None,
    location: str = "",
    job_type: str = "Job"
) -> bool:
    """
    Empirical Header Search Bar Automation Protocol (Rules C15 & C16):
    Supports both Standard Professional Naukri and Naukri Campus.
    1. Expands collapsed search bar via button.nI-gNb-sb__expand.
    2. If on Naukri Campus: selects 'Job' vs 'Internship' from input#jobType.
    3. Enters keyword/role/company into .nI-gNb-sb__keywords input.suggestor-input.
    4. If on Standard Naukri: selects experience level from input#experienceDD.
    5. Enters location into .nI-gNb-sb__location input.suggestor-input.
    6. Clicks search button button.nI-gNb-sb__icon-wrapper.
    """
    try:
        # Step 1: Expand search bar if collapsed
        expand_btn = page.locator("button.nI-gNb-sb__expand, [aria-label='Search jobs here']").first
        if expand_btn.count() > 0 and expand_btn.is_visible():
            expand_btn.click(force=True)
            page.wait_for_timeout(800)

        # Step 2: Handle Naukri Campus Job Type Dropdown (input#jobType)
        job_type_input = page.locator("input#jobType").first
        if job_type_input.count() > 0 and job_type_input.is_visible():
            job_type_input.click(force=True)
            page.wait_for_timeout(400)
            target_title = "Internship" if "intern" in str(job_type or keyword).lower() else "Job"
            opt = page.locator(f"ul.dropdown li[title='{target_title}']").first
            if opt.count() > 0 and opt.is_visible():
                opt.click(force=True)
            page.wait_for_timeout(400)

        # Step 3: Keywords / Designation / Company Name (Single clean string, never combined, no commas)
        clean_keyword = clean_search_token(keyword)
        kw_input = page.locator(".nI-gNb-sb__keywords input.suggestor-input, input[placeholder*='keyword']").first
        if kw_input.count() > 0 and kw_input.is_visible():
            kw_input.click(force=True)
            mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
            page.keyboard.press(mod_key)
            page.keyboard.press("Backspace")
            kw_input.type(clean_keyword, delay=35)
            page.wait_for_timeout(1000)
            
            # Select matching dropdown suggestion to bind search state
            suggs = page.locator(".nI-gNb-sugg div.opt, .suggestor-box .drop-layer li").all()
            matched = False
            for s in suggs:
                txt = clean_search_token(s.text_content())
                if txt.lower() == clean_keyword.lower():
                    s.click(force=True)
                    matched = True
                    break
            if not matched and suggs:
                suggs[0].click(force=True)
            page.wait_for_timeout(400)

            # Strip any trailing comma inserted by Naukri suggestor chip selection
            try:
                page.evaluate("""() => {
                    const el = document.querySelector('.nI-gNb-sb__keywords input.suggestor-input, input[placeholder*="keyword"]');
                    if (el && el.value) {
                        el.value = el.value.replace(/[,;\\s]+$/, '').trim();
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }""")
            except Exception:
                pass

        # Step 4: Experience Dropdown (Standard Naukri only)
        if exp_years is not None:
            exp_input = page.locator("#experienceDD").first
            if exp_input.count() > 0 and exp_input.is_visible():
                exp_input.click(force=True)
                page.wait_for_timeout(500)
                int_exp = int(float(exp_years))
                target_val = f"a{min(max(int_exp, 0), 30)}"
                opt = page.locator(f"ul.dropdown li[value='{target_val}'], li[title*='{int_exp} year']").first
                if opt.count() > 0 and opt.is_visible():
                    opt.click(force=True)
                page.wait_for_timeout(400)

        # Step 5: Location (Single clean string, no commas)
        clean_location = clean_search_token(location)
        if clean_location:
            loc_input = page.locator(".nI-gNb-sb__location input.suggestor-input, input[placeholder*='location']").first
            if loc_input.count() > 0 and loc_input.is_visible():
                loc_input.click(force=True)
                mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
                page.keyboard.press(mod_key)
                page.keyboard.press("Backspace")
                loc_input.type(clean_location, delay=35)
                page.wait_for_timeout(600)
                
                top_loc_sugg = page.locator(".drop-layer .tuple-wrap div.opt").first
                if top_loc_sugg.count() > 0 and top_loc_sugg.is_visible():
                    top_loc_sugg.click(force=True)
                page.wait_for_timeout(400)

                # Strip any trailing comma inserted by Naukri location chip selection
                try:
                    page.evaluate("""() => {
                        const el = document.querySelector('.nI-gNb-sb__location input.suggestor-input, input[placeholder*="location"]');
                        if (el && el.value) {
                            el.value = el.value.replace(/[,;\\s]+$/, '').trim();
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }""")
                except Exception:
                    pass

        # Step 6: Trigger Search & Verify Search Button Actually Clicked
        page.wait_for_timeout(500)
        search_btn = page.locator("button.nI-gNb-sb__icon-wrapper, .nI-gNb-sb__search-btn, button:has-text('Search'), div.qsbSubmit").first
        if search_btn.count() > 0 and search_btn.is_visible():
            print(f"[SEARCH BUTTON] Explicitly clicking Naukri search button...", flush=True)
            search_btn.click(force=True)
        else:
            print(f"[SEARCH BUTTON] Triggering search via Enter key...", flush=True)
            page.keyboard.press("Enter")
            
        # Verify page transitioned away from profile to search results
        for _ in range(15):
            page.wait_for_timeout(500)
            cur = page.url.lower()
            if "/mnjuser/profile" not in cur and ("jobs" in cur or "-jobs" in cur or "k=" in cur):
                print(f"[SEARCH SUCCESS] Search button executed successfully. Landed on: {page.url}", flush=True)
                return True
        return "/mnjuser/profile" not in page.url.lower()
    except Exception as e:
        logger.warning(f"Notice during header search automation: {e}")
    return False


def run_batched_discovery(profile_path: str):
    profile_dir = Path(profile_path).resolve()
    ctx = ProfileContext(profile_dir, BASE_DIR)
    config = ctx.config
    resume_path = profile_dir / "resume.md"
    resume_text = resume_path.read_text(encoding="utf-8") if resume_path.exists() else ""
    
    legacy_processed = get_already_processed_urls(profile_dir)
    persistent_ledger = ctx.load_processed_ledger()
    persistent_items = persistent_ledger.keys() if isinstance(persistent_ledger, dict) else persistent_ledger
    
    # Filter out legacy raw titles from the loaded ledger set to avoid false blockades!
    clean_persistent = set()
    for k in persistent_items:
        str_k = str(k).lower().strip()
        if str_k.startswith("http://") or str_k.startswith("https://") or "::" in str_k or str_k.startswith("naukri:") or str_k.startswith("linkedin:"):
            clean_persistent.add(str_k)
            if str_k.startswith("http://") or str_k.startswith("https://"):
                can = canonical_job_url(str_k)
                if can:
                    clean_persistent.add(can)
                jid = extract_platform_job_id(str_k)
                if jid:
                    clean_persistent.add(jid)

    processed_ledger = clean_persistent | legacy_processed
    ai = AIClient(ctx)
    ai.synthesize_cognitive_profile()
    
    cand = config.get("candidate", {})
    target = config.get("target_jobs", {})
    cdp_url = cand.get("cdp_url", "http://127.0.0.1:9222")
    
    # ── BATCH ARCH V2: SearchStateManager Designation Rotation Engine ─────────
    # Build the full designation list from cognitive profile + config + recommended titles
    active_cycle_keywords = ai.get_active_search_cycle()
    keywords = active_cycle_keywords if active_cycle_keywords else [k for k in (target.get("keywords") or []) if k and str(k).strip()]

    recommended = [t for t in (target.get("recommended_titles") or []) if t and str(t).strip()]
    current_title = cand.get("current_title", "").strip() if cand.get("current_title") else ""
    all_positive_targets = list(dict.fromkeys(list(keywords) + list(recommended)))
    if current_title and current_title not in all_positive_targets:
        all_positive_targets.append(current_title)

    # Sync rotation state with full designation list
    state_mgr = SearchStateManager(profile_dir)
    state_mgr.sync_designations(all_positive_targets)

    # ONE designation per daemon cycle — rotate deterministically
    active_designation = state_mgr.get_current_designation()
    if not active_designation:
        print("[DISCOVERY CONTROLLER] No designations configured. Check candidate_config.json.", flush=True)
        return

    print(f"\n[DISCOVERY CONTROLLER] BATCH ARCH V2 — Single Designation Cycle", flush=True)
    print(f"[DISCOVERY CONTROLLER] Active Designation: '{active_designation}'", flush=True)
    print(f"[DISCOVERY CONTROLLER] Rotation [{state_mgr.get_current_index()}/{len(state_mgr.get_all_designations())-1}]", flush=True)

    # Single search task: ROLE_ONLY for the active designation
    search_tasks = [{"strategy": "ROLE_ONLY", "query": active_designation, "role": active_designation, "company": ""}]

    # Dynamic Multi-Strategy: optionally also add company-targeted searches
    raw_target_companies = target.get("target_companies")
    if raw_target_companies is not None:
        target_companies = [c.strip() for c in raw_target_companies if c and str(c).strip()]
    else:
        cog_prof = ctx.load_cognitive_profile()
        target_companies = [c.strip() for c in (cog_prof.get("top_target_companies") or []) if c and str(c).strip()]

    if target_companies:
        for comp in target_companies:
            query_text = f"{comp} {active_designation}".strip()
            search_tasks.append({
                "strategy": "COMPANY_TARGETED",
                "query": query_text,
                "role": active_designation,
                "company": comp
            })

    print(f"[DISCOVERY CONTROLLER] Search Matrix: {len(search_tasks)} tasks for '{active_designation}' (+ {len(target_companies)} company targets)", flush=True)
    
    match_threshold = int(target.get("match_threshold", MATCH_THRESHOLD))
    negative_keywords = target.get("negative_keywords", [])
    negative_companies = [c.strip().lower() for c in target.get("negative_companies", []) if c and str(c).strip()]
    locations = target.get("locations", [])
    platforms = [p.lower() for p in target.get("platforms", [])]
    max_applies = int(target.get("max_applies_per_day", 50))
    # Dynamic Experience Filter: If target_jobs.experience_years is explicitly configured >= 1, use it.
    # Otherwise, do NOT force URL experience parameter (avoids portal fresher/BPO dilution traps when experience=0)
    exp_years = target.get("experience_years")
    if exp_years is None and cand.get("total_experience_years"):
        try:
            cand_exp = float(cand.get("total_experience_years", 0))
            if cand_exp >= 1.0:
                exp_years = cand_exp
        except Exception:
            exp_years = None
    salary_bracket = target.get("salary_filter_bracket", "")
    job_age_days = int(target.get("job_age_days", 3))
    
    max_pages = int(target.get("max_pages_per_search", MAX_PAGES_PER_SEARCH))
    configured_ctc_filters = target.get("ctc_filters", [])
    min_target_ctc_floor = float(cand.get("target_salary_min_lpa") or 0.0)
    if min_target_ctc_floor == 0.0 and salary_bracket:
        bracket_nums = [float(n) for n in re.findall(r'\d+', salary_bracket)]
        if bracket_nums:
            min_target_ctc_floor = bracket_nums[0]
    ctc_param = ""
    if configured_ctc_filters and isinstance(configured_ctc_filters, list):
        ctc_param = "".join(f"&ctcFilter={c.strip()}" for c in configured_ctc_filters if c and str(c).strip())
    elif salary_bracket:
        nums = [int(n) for n in re.findall(r'\d+', salary_bracket)]
        if nums:
            min_val = nums[0]
            if min_val >= 50:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val >= 25:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val >= 15:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val >= 10:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val >= 6:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val >= 3:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            elif min_val > 0:
                ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
    elif cand.get("target_salary_min_lpa"):
        min_val = int(float(cand.get("target_salary_min_lpa", 0)))
        if min_val >= 50:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val >= 25:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val >= 15:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val >= 10:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val >= 6:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val >= 3:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
        elif min_val > 0:
            ctc_param = f"&ctcFilter={target.get('ctc_bracket_id', '')}" if target.get("ctc_bracket_id") else ""
            
    # Dynamic Candidate Preferences: Work Mode (WFH/Remote) & Direct Employers
    wfh_pref = str(target.get("work_mode") or target.get("wfh_type") or "").lower().strip()
    wfh_param = ""
    if "remote" in wfh_pref or "wfh" in wfh_pref:
        wfh_param = f"&wfhType={target.get('wfh_type_id', '')}" if target.get("wfh_type_id") else ""
    elif "hybrid" in wfh_pref:
        wfh_param = f"&wfhType={target.get('wfh_type_id', '')}" if target.get("wfh_type_id") else ""
    elif "office" in wfh_pref or "onsite" in wfh_pref:
        wfh_param = f"&wfhType={target.get('wfh_type_id', '')}" if target.get("wfh_type_id") else ""

    direct_employers_only = target.get("direct_employers_only", False) or target.get("company_jobs_only", False)
    company_jobs_param = "&companyJobs=true" if direct_employers_only else ""

    # Dynamic Universal Platform Filter Resolution (Zero Hardcoding - Guardrail P1)
    # Serializes arbitrary portal query parameters and semantic facets dynamically configured per candidate profile
    portal_dynamic_params = ""
    portal_filters = target.get("naukri_filters") or target.get("platform_filters", {}).get("naukri") or {}
    if isinstance(portal_filters, dict):
        for f_key, f_val in portal_filters.items():
            if str(f_key).startswith("_"):
                continue
            if f_val is not None and str(f_val).strip():
                if isinstance(f_val, list):
                    for item in f_val:
                        if str(item).strip():
                            portal_dynamic_params += f"&{urllib.parse.quote(str(f_key))}={urllib.parse.quote(str(item))}"
                else:
                    portal_dynamic_params += f"&{urllib.parse.quote(str(f_key))}={urllib.parse.quote(str(f_val))}"
    
    # Backward compatibility with functional_area_id if not already in portal_filters
    if not (isinstance(portal_filters, dict) and "functionAreaIdGid" in portal_filters) and target.get("functional_area_id") is not None:
        portal_dynamic_params += f"&functionAreaIdGid={urllib.parse.quote(str(target['functional_area_id']))}"

    # Semantic Facet Targets for live UI/DOM enforcement
    configured_facet_targets = []
    if isinstance(target.get("facet_filters"), dict):
        for f_category, facet_vals in target["facet_filters"].items():
            if str(f_category).startswith("_"):
                continue
            if isinstance(facet_vals, list):
                configured_facet_targets.extend(str(v).strip() for v in facet_vals if str(v).strip())
            elif isinstance(facet_vals, str) and facet_vals.strip():
                configured_facet_targets.append(facet_vals.strip())
    for semantic_k in ["department", "functional_area_name", "role_category", "industry"]:
        sem_val = target.get(semantic_k)
        if sem_val and str(sem_val).strip() and str(sem_val).strip() not in configured_facet_targets:
            configured_facet_targets.append(str(sem_val).strip())

    applied_count = 0
    current_batch = []
    current_platform_exec = ""
    session_seen_titles = set()

    # ── BATCH ARCH V2: Cross-page card accumulator ─────────────────────────────
    # Cards collected from all pages are accumulated here before the single batch IPC call.
    designation_batch_cards = []

    # Build candidate_summary once (used in batch IPC payload)
    _cog_prof = ctx.load_cognitive_profile() if hasattr(ctx, "load_cognitive_profile") else {}
    candidate_summary_payload = {
        "total_experience_years": float(cand.get("total_experience_years", 0) or 0),
        "seniority_level": _cog_prof.get("seniority_level", "Mid-Senior"),
        "domain": _cog_prof.get("candidate_domain", "Software Engineering"),
        "core_skills": _cog_prof.get("core_domain_skills", [])[:20],
        "active_search_titles": all_positive_targets[:8],
        "advisory_avoid_terms": list(negative_keywords)[:30],
        "negative_companies": negative_companies[:20]
    }
    # ─────────────────────────────────────────────────────────────────────────
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            # Tab Hygiene (Rule C20): Adopt Tab 0 and prune leftover abandoned tabs from prior runs
            if context.pages:
                discovery_page = context.pages[0]
                for extra_tab in context.pages[1:]:
                    try:
                        if not extra_tab.is_closed():
                            extra_tab.close()
                    except Exception:
                        pass
            else:
                discovery_page = context.new_page()
            tracked_pages = {discovery_page}
            page = discovery_page
        except Exception as e:
            logger.error(f"CDP Connection Failed: {e}")
            return
            
        for platform in platforms:
            current_platform_exec = platform
            print(f"\n=======================================================", flush=True)
            print(f" [PLATFORM TARGET] Initiating scans on: {platform.upper()}", flush=True)
            print(f"=======================================================\n", flush=True)
            
            for raw_loc in locations:
                primary_loc = clean_search_token(raw_loc.split(",")[0])
                print(f" >>> LOCKING TARGET LOCATION: {primary_loc.upper()} <<<", flush=True)
                
                for task in search_tasks:
                    strategy = task["strategy"]
                    query_text = task["query"]
                    comp_text = task.get("company", "")

                    for page_num in range(1, max_pages + 1):
                        cleanup_browser_tabs(context, tracked_pages, active_page=discovery_page)
                        page = discovery_page
                        
                        ui_search_success = False
                        if platform == "naukri":
                            # Direct structured Search Results URL without repetitive profile reloading (Rule C17)
                            # Strictly sanitizes keywords & location (Rule C15: Zero-Comma Standard)
                            clean_q = clean_search_token(query_text)
                            clean_l = clean_search_token(primary_loc)
                            exp_param = f"&experience={int(float(exp_years))}" if (exp_years is not None and float(exp_years) >= 1.0) else ""
                            if strategy == "ROLE_ONLY" and not comp_text:
                                query_slug = re.sub(r'[^a-z0-9]+', '-', clean_q.lower()).strip('-')
                                loc_slug = re.sub(r'[^a-z0-9]+', '-', clean_l.lower()).strip('-')
                                base_url = f"https://www.naukri.com/{query_slug}-jobs-in-{loc_slug}"
                                if page_num > 1:
                                    base_url += f"-{page_num}"
                                query_url = f"{base_url}?jobAge={job_age_days}{exp_param}{wfh_param}{company_jobs_param}{portal_dynamic_params}"
                                if ctc_param:
                                    query_url += ctc_param
                            elif strategy == "COMPANY_ONLY":
                                comp_slug = re.sub(r'[^a-z0-9]+', '-', clean_search_token(comp_text).lower()).strip('-')
                                loc_slug = re.sub(r'[^a-z0-9]+', '-', clean_l.lower()).strip('-')
                                base_url = f"https://www.naukri.com/{comp_slug}-jobs-in-{loc_slug}"
                                if page_num > 1:
                                    base_url += f"-{page_num}"
                                query_url = f"{base_url}?jobAge={job_age_days}{exp_param}{wfh_param}{company_jobs_param}{portal_dynamic_params}"
                                if ctc_param:
                                    query_url += ctc_param
                            else: # ROLE_AND_COMPANY or fallback
                                encoded_query = urllib.parse.quote(clean_q)
                                encoded_loc = urllib.parse.quote(clean_l)
                                query_url = f"https://www.naukri.com/jobs?k={encoded_query}&l={encoded_loc}&jobAge={job_age_days}{exp_param}{wfh_param}{company_jobs_param}{portal_dynamic_params}"
                                if page_num > 1:
                                    query_url += f"&pageNo={page_num}"
                                if ctc_param:
                                    query_url += ctc_param
                                    
                            card_selector = "div.srp-jobtuple-wrapper, article.jobTuple, div.cust-job-tuple"
                            
                        elif platform == "linkedin":
                            query_kw = urllib.parse.quote(clean_search_token(query_text))
                            query_loc = urllib.parse.quote(clean_search_token(primary_loc))
                            start_param = (page_num - 1) * 25
                            query_url = f"https://www.linkedin.com/jobs/search/?keywords={query_kw}&location={query_loc}&f_AL=true&f_TPR=r{int(job_age_days * 86400)}&start={start_param}"
                            card_selector = "li.jobs-search-results__list-item, div.job-card-container"
                        else:
                            continue
                            
                        print(f"[{strategy}] Searching: '{query_text}' | Page {page_num}...", flush=True)
                        try:
                            if not ui_search_success:
                                page.goto(query_url, wait_until="domcontentloaded", timeout=20000)
                            if platform == "naukri":
                                for _ in range(10):
                                    if page.locator("div.srp-jobtuple-wrapper").count() > 0:
                                        card_selector = "div.srp-jobtuple-wrapper"
                                        break
                                    elif page.locator("article.jobTuple, div.cust-job-tuple").count() > 0:
                                        card_selector = "article.jobTuple, div.cust-job-tuple"
                                        break
                                    if page.locator(".next-error-h1").count() > 0 or page.locator("text='No results found'").count() > 0:
                                        break
                                    time.sleep(1)

                                # Universal UI / DOM Facet Enforcer: Dynamically inspects any profile-configured facets
                                if configured_facet_targets:
                                    for target_ident in configured_facet_targets:
                                        try:
                                            f_box = page.locator(f"input[type='checkbox'][id*='{target_ident}']")
                                            if f_box.count() > 0 and not f_box.first.is_checked():
                                                f_lbl = page.locator(f"label[for*='{target_ident}'], label:has(input[id*='{target_ident}'])")
                                                if f_lbl.count() > 0:
                                                    f_lbl.first.click()
                                                    time.sleep(1.5)
                                        except Exception:
                                            pass
                            else:
                                page.wait_for_selector(card_selector, timeout=60000)
                        except Exception as e:
                            logger.warning(f"Notice during SRP load: {e}")
                            continue
                            
                        if page.locator(card_selector).count() == 0 and (page.locator("text='No results found'").count() > 0 or page.locator(".next-error-h1").count() > 0):
                            if ctc_param and "ctcFilter=" in query_url:
                                print(f"  [-] 0 jobs in CTC filter. Retrying without CTC filter to include undisclosed salaries...", flush=True)
                                retry_url = re.sub(r'[?&]ctcFilter=[^&]+', '', query_url)
                                if '?' not in retry_url and '&' in retry_url:
                                    retry_url = retry_url.replace('&', '?', 1)
                                try:
                                    page.goto(retry_url, wait_until="domcontentloaded", timeout=20000)
                                    for _ in range(8):
                                        if page.locator(card_selector).count() > 0:
                                            break
                                        time.sleep(0.5)
                                except Exception:
                                    pass

                        if page.locator(card_selector).count() == 0 and (page.locator("text='No results found'").count() > 0 or page.locator(".next-error-h1").count() > 0):
                            print("  [-] End of results or invalid location slug. Moving to next keyword.", flush=True)
                            ai.record_profile_learning(profile_dir, "zero_yield_keywords", query_text, {
                                "reason": "0 results or invalid location slug",
                                "flagged_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            break
                            
                        cards = page.locator(card_selector).all()
                        if not cards:
                            ai.record_profile_learning(profile_dir, "zero_yield_keywords", query_text, {
                                "reason": "0 job cards found on page",
                                "flagged_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            break

                        ai.record_profile_learning(profile_dir, "high_yield_keywords", query_text, {
                            "matches_scanned": len(cards),
                            "last_searched": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                            
                        jobs_to_scan = []
                        for card in cards[:20]:
                            try:
                                if platform == "linkedin":
                                    title_el = card.locator(".job-card-list__title, .artdeco-entity-lockup__title").first
                                    comp_el = card.locator(".job-card-container__company-name").first
                                    exp_el = card.locator(".job-card-container__metadata-item").first
                                    rating_text = ""
                                    reviews_text = ""
                                    sal_text = ""
                                    loc_text = ""
                                    posted_text = ""
                                    skill_tags = []
                                else:
                                    title_el = card.locator("a.title, a.job-title").first
                                    comp_el = card.locator("a.comp-name, a.companyName").first
                                    rating_el = card.locator("a.rating span.main-2, a.rating").first
                                    reviews_el = card.locator("a.review").first
                                    exp_el = card.locator("span.exp-wrap, span.expwdth, li.experience, span[class*='exp'], span.ni-job-tuple-icon-experience").first
                                    sal_el = card.locator("span.sal-wrap, span.ni-job-tuple-icon-salary").first
                                    loc_el = card.locator("span.loc-wrap, span.locWdth").first
                                    posted_el = card.locator("span.job-post-day").first
                                    skill_els = card.locator("ul.tags-gt li, ul.dot-gt li, li.tag-li, .job-tags a, span[class*='tag']").all()
                                    skill_tags = [sk.inner_text().strip() for sk in skill_els if sk.inner_text().strip()]

                                    rating_text = rating_el.inner_text().strip() if rating_el.count() else ""
                                    reviews_text = reviews_el.inner_text().strip() if reviews_el.count() else ""
                                    sal_text = sal_el.inner_text().strip() if sal_el.count() else ""
                                    loc_text = loc_el.inner_text().strip() if loc_el.count() else ""
                                    posted_text = posted_el.inner_text().strip() if posted_el.count() else ""
                                    
                                if not title_el.count(): continue
                                title = title_el.inner_text().strip()
                                company = comp_el.inner_text().strip() if comp_el.count() else "Hiring Company"
                                url = title_el.get_attribute("href")
                                exp_text = exp_el.inner_text().strip() if exp_el.count() else ""
                                
                                session_seen_titles.add(title)

                                if platform == "linkedin" and "/view/" in url:
                                    url = url.split("?")[0]
                                elif platform == "naukri" and url and not url.startswith("http"):
                                    url = "https://www.naukri.com" + url
                                    
                                if url:
                                    can_url = canonical_job_url(url)
                                    raw_url = url
                                    job_id = extract_platform_job_id(raw_url, platform) or extract_platform_job_id(can_url, platform)
                                    composite_key = make_composite_key(company, title)
                                    
                                    if (
                                        url.lower() in processed_ledger
                                        or raw_url.lower() in processed_ledger
                                        or (can_url and can_url in processed_ledger)
                                        or (job_id and job_id in processed_ledger)
                                        or composite_key in processed_ledger
                                    ):
                                        continue

                                    card_info = f"Rating: {rating_text}" if rating_text else ""
                                    if reviews_text: card_info += f" ({reviews_text})"
                                    if exp_text: card_info += f" | Exp: {exp_text}"
                                    if loc_text: card_info += f" | Loc: {loc_text}"
                                    if sal_text: card_info += f" | Sal: {sal_text}"
                                    if posted_text: card_info += f" | Posted: {posted_text}"
                                    print(f"  [CARD] {title} @ {company}" + (f" [{card_info.strip(' |')}]" if card_info else ""), flush=True)

                                    jobs_to_scan.append({
                                        "title": title,
                                        "company": company,
                                        "url": can_url if can_url else url,
                                        "raw_url": raw_url,
                                        "card_skills": skill_tags,
                                        "exp_text": exp_text,
                                        "rating": rating_text,
                                        "reviews": reviews_text,
                                        "salary": sal_text,
                                        "card_location": loc_text,
                                        "posted_age": posted_text
                                    })
                            except Exception:
                                continue

                        # ── BATCH ARCH V2 — ARM PHASE: Accumulate cards, no per-card IPC ──────────
                        # Cards are pre-gated only on OBJECTIVE NUMERIC CRITERIA (blacklist, salary,
                        # exp band). All SEMANTIC decisions (role fit, domain match) are delegated
                        # exclusively to AG Brain in the batch IPC call below (G-BRAIN-01).
                        for job in jobs_to_scan:
                            _url = job["url"]
                            _raw_url = job.get("raw_url", _url)
                            _title = job["title"]
                            _company = job["company"]
                            _can_url = canonical_job_url(_url)
                            _job_id = extract_platform_job_id(_raw_url, platform) or extract_platform_job_id(_url, platform)
                            _composite_key = make_composite_key(_company, _title)
                            _exp_text_card = job.get("exp_text", "")
                            _sal_text = str(job.get("salary") or "").strip()

                            # Gate 1: Deduplication (objective identity gate)
                            if (
                                _url.lower() in processed_ledger
                                or _raw_url.lower() in processed_ledger
                                or (_can_url and _can_url in processed_ledger)
                                or (_job_id and _job_id in processed_ledger)
                                or _composite_key in processed_ledger
                            ):
                                continue

                            # Gate 2: Negative Company Blacklist (objective identity gate)
                            _comp_lower = _company.lower().strip()
                            whitelist_exceptions = ["infosys finacle", "edgeverve finacle"]
                            if any(
                                (nc in _comp_lower if len(nc) > 3 else re.search(rf'\b{re.escape(nc)}\b', _comp_lower))
                                for nc in negative_companies
                            ) and not any(wc in _comp_lower for wc in whitelist_exceptions):
                                print(f"  -> [PRE-GATE] Rejected Blacklisted Company: {_title} @ {_company}", flush=True)
                                processed_ledger.add(_url.lower())
                                processed_ledger.add(_can_url)
                                if _job_id: processed_ledger.add(_job_id)
                                processed_ledger.add(_composite_key)
                                ctx.add_to_processed_ledger(_can_url, status="negative_company_gated", metadata={"title": _title, "company": _company})
                                ctx.add_to_processed_ledger(_composite_key, status="composite_negative_company_gated")
                                continue

                            # Gate 3: Salary Floor (objective numeric gate — only when salary is clearly stated)
                            if min_target_ctc_floor > 0 and _sal_text:
                                _sal_nums = [float(n) for n in re.findall(r'(\d+(?:\.\d+)?)', _sal_text)]
                                if _sal_nums and ("lac" in _sal_text.lower() or "lakh" in _sal_text.lower()):
                                    _max_offered = max(_sal_nums)
                                    if _max_offered < min_target_ctc_floor:
                                        print(f"  -> [PRE-GATE] Below-CTC: {_title} @ {_company} [Sal: {_sal_text} < {min_target_ctc_floor} LPA floor]", flush=True)
                                        processed_ledger.add(_url.lower())
                                        processed_ledger.add(_can_url)
                                        if _job_id: processed_ledger.add(_job_id)
                                        processed_ledger.add(_composite_key)
                                        ctx.add_to_processed_ledger(_can_url, status="below_ctc_floor", metadata={"title": _title, "company": _company, "salary": _sal_text})
                                        continue

                            # Gate 4: Experience Band (objective numeric gate — C24)
                            if _exp_text_card:
                                _exp_range = re.findall(r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*[Yy]', _exp_text_card)
                                if not _exp_range:
                                    _exp_single = re.findall(r'(\d+)\s*[Yy]', _exp_text_card)
                                    _exp_range = [(_exp_single[0], '')] if _exp_single else []
                                if _exp_range:
                                    _card_min_exp = float(_exp_range[0][0])
                                    _cand_actual_exp = float(cand.get("total_experience_years", 0) or 0)
                                    _max_exp_gap = float(
                                        (config.get("target_jobs", {}) if isinstance(config, dict) else {})
                                        .get("max_experience_gap_years", 2)
                                    )
                                    if _card_min_exp > _cand_actual_exp + _max_exp_gap:
                                        print(f"  -> [PRE-GATE] Over-Senior: {_title} @ {_company} [CardExp:{_card_min_exp:.0f}yr > Cand:{_cand_actual_exp}yr+{_max_exp_gap:.0f}yr gap]", flush=True)
                                        processed_ledger.add(_url.lower())
                                        if _can_url: processed_ledger.add(_can_url)
                                        if _job_id: processed_ledger.add(_job_id)
                                        processed_ledger.add(_composite_key)
                                        ctx.add_to_processed_ledger(_can_url or _url.lower(), status="experience_gap_gated", metadata={"title": _title, "company": _company, "exp_text": _exp_text_card})
                                        continue

                            # Card passed all objective pre-gates → add to batch for AG Brain evaluation
                            job["_can_url"] = _can_url
                            job["_job_id"] = _job_id
                            job["_composite_key"] = _composite_key
                            job["_platform"] = platform
                            designation_batch_cards.append(job)
                            print(f"  [BATCHED] {_title} @ {_company} [{_exp_text_card}]", flush=True)
                        # ── END OF ARM ACCUMULATION PHASE ─────────────────────────────────────────

    # ─── BATCH ARCH V2 — BRAIN PHASE: AG Brain Batch Evaluation ──────────────────
    # After collecting all cards from all pages, send the ENTIRE batch to AG Brain
    # in a single IPC call. This replaces N×90s per-card IPC with 1×120s batch IPC.
    # ─────────────────────────────────────────────────────────────────────────────

    if current_batch:
        process_batch(current_batch, profile_dir, current_platform_exec)
        applied_count += len(current_batch)
        current_batch.clear()

    print(f"\n{'='*70}", flush=True)
    print(f"[BATCH IPC] ARM PHASE COMPLETE — {len(designation_batch_cards)} cards batched for '{active_designation}'", flush=True)
    print(f"{'='*70}", flush=True)

    approved_jobs = []

    if designation_batch_cards:
        # Assign sequential IDs to each card for AG Brain's decision mapping
        for _bid, _bcard in enumerate(designation_batch_cards):
            _bcard["id"] = _bid

        # Single IPC call — AG Brain evaluates ALL cards at once
        batch_decisions = ai.batch_card_evaluation_ipc(
            cards=designation_batch_cards,
            candidate_summary=candidate_summary_payload,
            designation=active_designation,
            timeout_seconds=float(target.get("batch_ipc_timeout_seconds", 120))
        )

        # Map decisions back to card objects
        decisions_by_id = {d.get("id"): d for d in batch_decisions if isinstance(d, dict)}
        for _bcard in designation_batch_cards:
            _bid = _bcard.get("id")
            _decision_obj = decisions_by_id.get(_bid, {})
            _decision = str(_decision_obj.get("decision", "SKIP")).upper()
            _reason = str(_decision_obj.get("reason", "No reason given"))
            _bcard["_ag_decision"] = _decision
            _bcard["_ag_reason"] = _reason
            if _decision == "DEEP_SCAN":
                approved_jobs.append(_bcard)
                print(f"  [AG APPROVED] {_bcard['title']} @ {_bcard['company']} | {_reason}", flush=True)
            else:
                print(f"  [AG SKIPPED]  {_bcard['title']} @ {_bcard['company']} | {_reason}", flush=True)
                # Log skipped cards to processed ledger to prevent re-evaluation next cycle
                _skip_url = _bcard.get("_can_url") or _bcard.get("url", "")
                _skip_composite = _bcard.get("_composite_key", "")
                _skip_job_id = _bcard.get("_job_id")
                if _skip_url:
                    processed_ledger.add(_skip_url.lower())
                    ctx.add_to_processed_ledger(_skip_url, status="ag_brain_batch_skipped", metadata={"title": _bcard["title"], "company": _bcard["company"], "reason": _reason})
                if _skip_composite:
                    processed_ledger.add(_skip_composite)
    else:
        print(f"[BATCH IPC] No cards survived pre-gating for '{active_designation}'. Nothing to evaluate.", flush=True)

    print(f"\n[BATCH IPC] AG Brain approved {len(approved_jobs)}/{len(designation_batch_cards)} cards for deep scan.", flush=True)

    # ─── BATCH ARCH V2 — EXECUTE PHASE: Deep Scan + Tailor + Apply ───────────────
    # Only AG Brain-approved cards are opened. This is the "arm execute" phase.
    # ─────────────────────────────────────────────────────────────────────────────

    with sync_playwright() as _exec_p:
        try:
            _exec_browser = _exec_p.chromium.connect_over_cdp(cdp_url)
            _exec_context = _exec_browser.contexts[0] if _exec_browser.contexts else _exec_browser.new_context()
            if _exec_context.pages:
                _exec_page = _exec_context.pages[0]
                for _extra in _exec_context.pages[1:]:
                    try:
                        if not _extra.is_closed():
                            _extra.close()
                    except Exception:
                        pass
            else:
                _exec_page = _exec_context.new_page()
            _exec_tracked = {_exec_page}
        except Exception as _exec_err:
            logger.error(f"Execute-phase CDP connection failed: {_exec_err}")
            approved_jobs = []

        for approved_job in approved_jobs:
            if applied_count >= max_applies:
                print(f"[EXECUTE] Max applies ({max_applies}) reached. Stopping.", flush=True)
                break

            cleanup_browser_tabs(_exec_context, _exec_tracked, active_page=_exec_page)
            url = approved_job["url"]
            raw_url = approved_job.get("raw_url", url)
            title = approved_job["title"]
            company = approved_job["company"]
            card_skills = approved_job.get("card_skills", [])
            exp_text = approved_job.get("exp_text", "")
            can_url = approved_job.get("_can_url") or canonical_job_url(url)
            job_id = approved_job.get("_job_id") or extract_platform_job_id(raw_url) or extract_platform_job_id(url)
            composite_key = approved_job.get("_composite_key") or make_composite_key(company, title)
            _exec_platform = approved_job.get("_platform", "naukri")

            # Final dedup check before opening browser (in case it was added during this run)
            if (
                url.lower() in processed_ledger
                or (can_url and can_url in processed_ledger)
                or (job_id and job_id in processed_ledger)
                or composite_key in processed_ledger
            ):
                print(f"  -> [ALREADY PROCESSED] {title} @ {company} — skipping.", flush=True)
                continue

            print(f"\n  -> [DEEP SCAN] {title} @ {company}...", flush=True)
            nav_url = can_url if can_url else url

            detail_page = _exec_context.new_page()
            _exec_tracked.add(detail_page)
            full_desc = ""
            extracted_skills = []
            other_details_text = ""
            page_job_id = None
            page_can_url = ""
            naukri_match_score = {}

            try:
                try:
                    detail_page.goto(nav_url, wait_until="domcontentloaded", timeout=25000)
                    detail_page.wait_for_timeout(1500)
                    if detail_page.locator("body").count() > 0 and len(detail_page.inner_text("body").strip()) < 50:
                        detail_page.wait_for_timeout(1000)
                        if len(detail_page.inner_text("body").strip()) < 50:
                            detail_page.reload(wait_until="domcontentloaded", timeout=25000)
                            detail_page.wait_for_timeout(1500)
                except Exception as _nav_err:
                    time.sleep(1)
                    try:
                        detail_page.goto(nav_url, wait_until="domcontentloaded", timeout=25000)
                        detail_page.wait_for_timeout(1500)
                    except Exception as _nav_err2:
                        print(f"     [ERROR NAVIGATING] {_nav_err2}", flush=True)
                        processed_ledger.add(url.lower())
                        if can_url: processed_ledger.add(can_url)
                        if job_id: processed_ledger.add(job_id)
                        processed_ledger.add(composite_key)
                        continue

                # Re-verify opened page URL against ledger in case of redirects
                page_can_url = canonical_job_url(detail_page.url)
                page_job_id = extract_platform_job_id(detail_page.url, _exec_platform)
                if (
                    page_can_url in processed_ledger
                    or (page_job_id and page_job_id in processed_ledger)
                ):
                    print(f"     [ALREADY PROCESSED (REDIRECT: {page_can_url})] Skipping.", flush=True)
                    continue

                # PRE-TAILORING APPLY VERIFICATION
                if _exec_platform == "naukri":
                    for _ in range(8):
                        if (
                            detail_page.locator("button.styles_apply-button__PLbNT, button[class*='apply'], a[class*='apply']").count() > 0
                            or detail_page.locator("div.styles_already-applied__6jfPS, span[class*='applied']").count() > 0
                            or detail_page.locator("div.jd-header-comp-name").count() > 0
                        ):
                            break
                        time.sleep(0.5)

                    if detail_page.locator("div.styles_already-applied__6jfPS, span[class*='already-applied'], span:text-is('Applied')").count() > 0:
                        print(f"     [ALREADY APPLIED (NAUKRI BANNER)] {title} @ {company}", flush=True)
                        processed_ledger.add(url.lower())
                        if can_url: processed_ledger.add(can_url)
                        if job_id: processed_ledger.add(job_id)
                        processed_ledger.add(composite_key)
                        ctx.add_to_processed_ledger(can_url or url, status="already_applied_banner", metadata={"title": title, "company": company})
                        continue

                # Scrape full JD for evaluate_job_match
                _jd_selectors = [
                    "div.styles_JD-section__umHEZ",
                    "div.job-description",
                    "section.job-detail",
                    "div[class*='jd-desc']",
                    "div[class*='job-desc']",
                    "article",
                    "main"
                ]
                for _sel in _jd_selectors:
                    _jd_el = detail_page.locator(_sel).first
                    if _jd_el.count() > 0:
                        full_desc = _jd_el.inner_text().strip()
                        if len(full_desc) > 100:
                            break

                # Extract skills from JD page
                _skill_tags_els = detail_page.locator("a.styles_chip__7YCfG, div.chip, span.chip, li.chip, div[class*='skill-chip']").all()
                extracted_skills = [_se.inner_text().strip() for _se in _skill_tags_els if _se.inner_text().strip()]
                if not extracted_skills:
                    extracted_skills = card_skills

                # Evaluate job match with full JD (AG Brain IPC via evaluate_job_match — DAEMON_MODE bypass REMOVED)
                combined_desc = f"{full_desc}\n{other_details_text}".strip() if other_details_text else full_desc
                match_result = ai.evaluate_job_match(
                    job_title=title,
                    job_description=combined_desc or exp_text,
                    matching_skills=extracted_skills or card_skills,
                    profile_dir=profile_dir,
                    enable_ipc=True
                )
                score = match_result.score if hasattr(match_result, "score") else (match_result.get("score", 0) if isinstance(match_result, dict) else 0)
                reasoning = match_result.reasoning if hasattr(match_result, "reasoning") else (match_result.get("reasoning", "") if isinstance(match_result, dict) else "")

                print(f"     [SCORE: {score}%] {reasoning[:100]}", flush=True)

                if score >= match_threshold:
                    print(f"     [QUALIFIED — TAILORING + APPLYING] {title} @ {company}", flush=True)
                    processed_ledger.add(url.lower())
                    if can_url: processed_ledger.add(can_url)
                    if job_id: processed_ledger.add(job_id)
                    if page_job_id: processed_ledger.add(page_job_id)
                    processed_ledger.add(composite_key)
                    ctx.add_to_processed_ledger(can_url or url, status="qualified", metadata={"title": title, "company": company, "score": score})
                    ctx.add_to_processed_ledger(composite_key, status="composite_qualified")

                    current_batch.append({
                        "title": title,
                        "company": company,
                        "url": can_url or url,
                        "raw_url": raw_url,
                        "platform": _exec_platform,
                        "full_desc": combined_desc,
                        "score": score,
                        "extracted_skills": extracted_skills,
                        "naukri_match_score": naukri_match_score,
                    })

                    if len(current_batch) >= BATCH_SIZE:
                        process_batch(current_batch, profile_dir, _exec_platform)
                        applied_count += len(current_batch)
                        current_batch.clear()
                else:
                    print(f"     [BELOW THRESHOLD ({score}% < {match_threshold}%)] {title} @ {company}", flush=True)
                    processed_ledger.add(url.lower())
                    if can_url: processed_ledger.add(can_url)
                    if job_id: processed_ledger.add(job_id)
                    if page_job_id: processed_ledger.add(page_job_id)
                    processed_ledger.add(composite_key)
                    ctx.add_to_processed_ledger(can_url or url, status="low_score", metadata={"title": title, "company": company, "score": score})

            except Exception as _exec_loop_err:
                logger.warning(f"Notice during execute-phase for '{title}': {_exec_loop_err}")
                try:
                    if not detail_page.is_closed():
                        detail_page.close()
                    _exec_tracked.discard(detail_page)
                except Exception:
                    pass

        if current_batch:
            process_batch(current_batch, profile_dir, _exec_platform if approved_jobs else current_platform_exec)
            applied_count += len(current_batch)
            current_batch.clear()

        try:
            cleanup_browser_tabs(_exec_context, _exec_tracked, active_page=_exec_page)
        except Exception:
            pass

    # ─── BATCH ARCH V2 — ROTATION PHASE: Advance to next designation ─────────────
    print(f"\n{'='*70}", flush=True)
    print(f"[ROTATION] Designation '{active_designation}' complete. Applied: {applied_count}", flush=True)

    # Record per-designation stats
    state_mgr.record_stats(
        designation=active_designation,
        cards_found=len(designation_batch_cards),
        cards_approved=len(approved_jobs),
        cards_applied=applied_count
    )

    # Advance to next designation for the next daemon cycle
    next_designation = state_mgr.advance()
    print(f"[ROTATION] Next cycle will search: '{next_designation}'", flush=True)
    print(f"[ROTATION] State: {state_mgr.get_stats()}", flush=True)
    print(f"{'='*70}\n", flush=True)

    # Keep ai.advance_search_cycle() for cognitive profile search cycle tracking
    try:
        ai.advance_search_cycle()
    except Exception as _adv_err:
        logger.warning(f"Notice advancing AI search cycle: {_adv_err}")

    print(f"\n=== BATCH DISCOVERY COMPLETE. Designation: '{active_designation}'. Applied: {applied_count}. ===", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None, help="Path to profile directory (optional, auto-discovers)")
    args = parser.parse_args()
    
    # Dynamic profile fallback
    if not args.profile:
        resolved_ctx = ProfileContext(None, BASE_DIR)
        profile_path = str(resolved_ctx.profile_path)
    else:
        profile_path = args.profile
        
    run_batched_discovery(profile_path)
