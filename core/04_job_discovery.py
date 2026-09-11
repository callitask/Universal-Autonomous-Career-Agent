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


def is_title_allowed(
    title: str,
    target_keywords: list,
    negative_keywords: list,
    card_skills: list = None,
    exp_text: str = "",
    ai_client = None,
    config: dict = None,
    ctx = None
) -> bool:
    """
    Tier 2 Multi-Pass Gating & Cognitive Arbitration:
    - 1. C6 Fix: Strictly rejects titles containing negative keywords unconditionally.
    - 2. Incompatible Vertical Gate: Detects and filters obvious out-of-domain verticals.
    - 3. Deterministic Positive Match: Matches titles using prefix/stem-aware matching,
         domain tokens, or card skill tags from the search page.
    - 4. Tier 2B Cognitive Triage: If unfamiliar or abbreviated, consults the AI Brain
         (ai_client.arbitrate_card_fit).
    """
    title_lower = title.lower().strip()

    # 1. Absolute Negative Rejection (C6 Guardrail)
    for neg in negative_keywords:
        neg_clean = str(neg).strip().lower() if neg else ""
        if not neg_clean:
            continue
        if neg_clean in title_lower if ' ' in neg_clean else re.search(rf'\b{re.escape(neg_clean)}\b', title_lower):
            return False
        if card_skills:
            for cs in card_skills:
                cs_lower = cs.lower().strip()
                if neg_clean == cs_lower or re.search(rf'\b{re.escape(neg_clean)}\b', cs_lower):
                    return False

    # 2. Incompatible Vertical Quick Gating
    if ctx:
        cog_prof = ctx.load_cognitive_profile()
        if cog_prof:
            cand_domain = cog_prof.get("candidate_domain", "").lower()
            incompatibles = cog_prof.get("incompatible_verticals", {})
            for vert_name, vert_markers in incompatibles.items():
                for marker in vert_markers[:5]:
                    if re.search(rf'\b{re.escape(marker)}\b', title_lower):
                        # Verify if candidate domain function is in title
                        domain_words = [w for w in re.split(r'[\s/,-]+', cand_domain) if len(w) > 3]
                        if not any(re.search(rf'\b{re.escape(dw)}\b', title_lower) for dw in domain_words):
                            return False

    # 3. Strict Positive Alignment (Domain Relevance)
    if not target_keywords:
        return True

    # 3.1 Direct exact phrase match (case-insensitive)
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        if not target_clean:
            continue
        if re.search(rf'\b{re.escape(target_clean)}\b', title_lower) or target_clean in title_lower:
            return True

    title_tokens = [t for t in re.split(r'[\s/,-]+', title_lower) if len(t) > 2]
    if not title_tokens:
        return False

    def token_matches(target_tok: str, tok_list: list) -> bool:
        for tok in tok_list:
            if tok == target_tok:
                return True
            if len(tok) >= 4 and len(target_tok) >= 4 and (tok.startswith(target_tok[:5]) or target_tok.startswith(tok[:5])):
                return True
        return False

    stopwords = {
        "and", "for", "the", "with", "lead", "senior", "junior", "manager",
        "executive", "officer", "associate", "specialist", "staff", "principal",
        "head", "director", "vp", "intern", "trainee", "expert", "consultant",
        "general", "global", "regional", "assistant", "deputy", "group", "team",
        "engineer", "developer", "engineering"
    }

    # 3.2 Target Phrase Stem/Prefix Overlap
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        if not target_clean:
            continue

        target_tokens = [t for t in re.split(r'[\s/,-]+', target_clean) if len(t) > 2 and t not in stopwords]
        if not target_tokens:
            target_tokens = [t for t in re.split(r'[\s/,-]+', target_clean) if len(t) > 2]

        if target_tokens and all(token_matches(tt, title_tokens) for tt in target_tokens):
            return True

    # 3.3 Primary Domain Keyword Direct Match
    dynamic_domain_tokens = set()
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        for t in re.split(r'[\s/,-]+', target_clean):
            if len(t) >= 4 and t not in stopwords:
                dynamic_domain_tokens.add(t)

    for tt in title_tokens:
        if tt in dynamic_domain_tokens:
            return True
        for dt in dynamic_domain_tokens:
            if len(tt) >= 4 and len(dt) >= 4 and (tt.startswith(dt[:5]) or dt.startswith(tt[:5])):
                return True

    # 3.4 Card Skills Overlap
    if card_skills:
        for cs in card_skills:
            cs_clean = cs.lower().strip()
            if cs_clean in dynamic_domain_tokens:
                return True
            for dt in dynamic_domain_tokens:
                if len(cs_clean) >= 4 and len(dt) >= 4 and (cs_clean.startswith(dt[:5]) or dt.startswith(cs_clean[:5])):
                    return True

    # 4. Tier 2B: Cognitive Brain Arbitration
    if ai_client and hasattr(ai_client, "arbitrate_card_fit"):
        fits, reason = ai_client.arbitrate_card_fit(
            title=title,
            card_skills=card_skills,
            exp_text=exp_text,
            candidate_profile=config
        )
        if fits:
            print(f"     [COGNITIVE BRAIN APPROVED FOR DEEP SCAN]: '{title}' ({reason})", flush=True)
            return True

    return False


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
    subprocess.run([sys.executable, str(BASE_DIR / "core" / "generate_factual_tailored.py"), "--profile", str(profile_dir)], check=True)
    
    if platform.lower() == "naukri":
        print("  [PIPELINE] 2/3: Fast-Injecting Tailored Resume to Naukri...", flush=True)
        subprocess.run([sys.executable, str(BASE_DIR / "core" / "02b_naukri_fast_resume_upload.py"), "--profile", str(profile_dir)])
    elif platform.lower() == "linkedin":
        print("  [PIPELINE] 2/3: Preparing LinkedIn Easy Apply Modal Application...", flush=True)
        
    print("  [PIPELINE] 3/3: Executing Application Engine...", flush=True)
    subprocess.run([sys.executable, str(BASE_DIR / "core" / "05_apply_jobs.py"), "--profile", str(profile_dir)])
    
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

        # Step 3: Keywords / Designation / Company Name (Single clean string, never combined)
        clean_keyword = str(keyword).strip()
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
                txt = s.text_content().strip()
                if txt.lower() == clean_keyword.lower():
                    s.click(force=True)
                    matched = True
                    break
            if not matched and suggs:
                suggs[0].click(force=True)
            page.wait_for_timeout(400)

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

        # Step 5: Location
        if location:
            loc_input = page.locator(".nI-gNb-sb__location input.suggestor-input, input[placeholder*='location']").first
            if loc_input.count() > 0 and loc_input.is_visible():
                loc_input.click(force=True)
                mod_key = "Meta+A" if sys.platform == "darwin" else "Control+A"
                page.keyboard.press(mod_key)
                page.keyboard.press("Backspace")
                loc_input.type(str(location), delay=35)
                page.wait_for_timeout(600)
                
                top_loc_sugg = page.locator(".drop-layer .tuple-wrap div.opt").first
                if top_loc_sugg.count() > 0 and top_loc_sugg.is_visible():
                    top_loc_sugg.click(force=True)
                page.wait_for_timeout(400)

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
    
    # Dynamic Search Cycles: Retrieve active cycle of 5-8 designations from Cognitive Brain
    active_cycle_keywords = ai.get_active_search_cycle()
    keywords = active_cycle_keywords if active_cycle_keywords else [k for k in (target.get("keywords") or []) if k and str(k).strip()]
    print(f"[DISCOVERY CONTROLLER] Active Search Cycle contains {len(keywords)} designations: {keywords}", flush=True)

    recommended = [t for t in (target.get("recommended_titles") or []) if t and str(t).strip()]
    current_title = cand.get("current_title", "").strip() if cand.get("current_title") else ""
    all_positive_targets = list(keywords) + list(recommended)
    if current_title and current_title not in all_positive_targets:
        all_positive_targets.append(current_title)

    # Dynamic Multi-Strategy Matrix: Role-Only, Company-Only, and Role + Company
    raw_target_companies = target.get("target_companies")
    if raw_target_companies is not None:
        target_companies = [c.strip() for c in raw_target_companies if c and str(c).strip()]
    else:
        cog_prof = ctx.load_cognitive_profile()
        target_companies = [c.strip() for c in (cog_prof.get("top_target_companies") or []) if c and str(c).strip()]

    search_tasks = []
    # 1. Broad / Target Designations & Keywords (Single Entity Only, never combined)
    for kw in keywords:
        search_tasks.append({
            "strategy": "ROLE_ONLY",
            "query": kw,
            "role": kw,
            "company": ""
        })

    # 2. Company Name Specific Searches (Single Entity Only: pure company name in search box, never merged with role)
    if target_companies:
        for comp in target_companies:
            search_tasks.append({
                "strategy": "COMPANY_ONLY",
                "query": comp,
                "role": "",
                "company": comp
            })

    print(f"[DISCOVERY CONTROLLER] Single-Entity Search Matrix: {len(search_tasks)} tasks (Roles: {len(keywords)}, Companies: {len(target_companies)})", flush=True)
    
    match_threshold = int(target.get("match_threshold", MATCH_THRESHOLD))
    negative_keywords = target.get("negative_keywords", [])
    negative_companies = [c.strip().lower() for c in target.get("negative_companies", []) if c and str(c).strip()]
    locations = target.get("locations", [])
    platforms = [p.lower() for p in target.get("platforms", ["naukri"])]
    exp_years = target.get("experience_years", cand.get("total_experience_years", 0))
    max_applies = int(target.get("max_applies_per_day", 50))
    salary_bracket = target.get("salary_filter_bracket", "")
    job_age_days = int(target.get("job_age_days", 3))
    
    ctc_filter = ""
    if salary_bracket:
        nums = re.findall(r'\d+', salary_bracket)
        if len(nums) >= 2:
            ctc_filter = f"{nums[0]}to{nums[1]}"
            
    # Dynamic Candidate Preferences: Work Mode (WFH/Remote) & Direct Employers
    wfh_pref = str(target.get("work_mode") or target.get("wfh_type") or "").lower().strip()
    wfh_param = ""
    if "remote" in wfh_pref or "wfh" in wfh_pref:
        wfh_param = "&wfhType=3"
    elif "hybrid" in wfh_pref:
        wfh_param = "&wfhType=2"
    elif "office" in wfh_pref or "onsite" in wfh_pref:
        wfh_param = "&wfhType=0"

    direct_employers_only = target.get("direct_employers_only", False) or target.get("company_jobs_only", False)
    company_jobs_param = "&companyJobs=true" if direct_employers_only else ""

    applied_count = 0
    current_batch = []
    current_platform_exec = ""
    session_seen_titles = set()
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
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
                primary_loc = raw_loc.split(",")[0].strip()
                print(f" >>> LOCKING TARGET LOCATION: {primary_loc.upper()} <<<", flush=True)
                
                for task in search_tasks:
                    strategy = task["strategy"]
                    query_text = task["query"]
                    comp_text = task.get("company", "")

                    for page_num in range(1, MAX_PAGES_PER_SEARCH + 1):
                        cleanup_browser_tabs(context, tracked_pages, active_page=discovery_page)
                        page = discovery_page
                        
                        ui_search_success = False
                        if platform == "naukri":
                            # Direct structured Search Results URL without repetitive profile reloading
                            if strategy == "ROLE_ONLY" and not comp_text:
                                query_slug = re.sub(r'[^a-z0-9]+', '-', query_text.lower()).strip('-')
                                loc_slug = re.sub(r'[^a-z0-9]+', '-', primary_loc.lower()).strip('-')
                                base_url = f"https://www.naukri.com/{query_slug}-jobs-in-{loc_slug}"
                                if page_num > 1:
                                    base_url += f"-{page_num}"
                                query_url = f"{base_url}?experience={int(float(exp_years or 0))}&jobAge={job_age_days}{wfh_param}{company_jobs_param}"
                                if ctc_filter:
                                    query_url += f"&ctcFilter={ctc_filter}"
                            else: # COMPANY_ONLY, single keyword, or fallback
                                encoded_query = urllib.parse.quote(query_text)
                                encoded_loc = urllib.parse.quote(primary_loc)
                                query_url = f"https://www.naukri.com/jobs?k={encoded_query}&l={encoded_loc}&experience={int(float(exp_years or 0))}&jobAge={job_age_days}{wfh_param}{company_jobs_param}"
                                if page_num > 1:
                                    query_url += f"&pageNo={page_num}"
                                if ctc_filter:
                                    query_url += f"&ctcFilter={ctc_filter}"
                                    
                            card_selector = "div.srp-jobtuple-wrapper, article.jobTuple, div.cust-job-tuple"
                            
                        elif platform == "linkedin":
                            query_kw = urllib.parse.quote(query_text)
                            query_loc = urllib.parse.quote(primary_loc)
                            start_param = (page_num - 1) * 25
                            query_url = f"https://www.linkedin.com/jobs/search/?keywords={query_kw}&location={query_loc}&f_AL=true&f_TPR=r259200&start={start_param}"
                            card_selector = "li.jobs-search-results__list-item, div.job-card-container"
                        else:
                            continue
                            
                        print(f"[{strategy}] Searching: '{query_text}' | Page {page_num}...", flush=True)
                        try:
                            if not ui_search_success:
                                page.goto(query_url, wait_until="domcontentloaded", timeout=20000)
                            if platform == "naukri":
                                for _ in range(10):
                                    if page.locator(card_selector).count() > 0:
                                        break
                                    if page.locator(".next-error-h1").count() > 0 or page.locator("text='No results found'").count() > 0:
                                        break
                                    time.sleep(1)
                            else:
                                page.wait_for_selector(card_selector, timeout=12000)
                        except Exception as e:
                            logger.warning(f"Notice during SRP load: {e}")
                            continue
                            
                        if page.locator("text='No results found'").count() > 0 or page.locator(".next-error-h1").count() > 0:
                            print("  [-] End of results or invalid location slug. Moving to next keyword.", flush=True)
                            break
                            
                        cards = page.locator(card_selector).all()
                        if not cards:
                            break
                            
                        jobs_to_scan = []
                        for card in cards[:15]:
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

                                card_info = f"Rating: {rating_text}" if rating_text else ""
                                if reviews_text: card_info += f" ({reviews_text})"
                                if exp_text: card_info += f" | Exp: {exp_text}"
                                if loc_text: card_info += f" | Loc: {loc_text}"
                                if sal_text: card_info += f" | Sal: {sal_text}"
                                if posted_text: card_info += f" | Posted: {posted_text}"
                                print(f"  [CARD] {title} @ {company}" + (f" [{card_info.strip(' |')}]" if card_info else ""), flush=True)
                                
                                if platform == "linkedin" and "/view/" in url:
                                    url = url.split("?")[0]
                                elif platform == "naukri" and url and not url.startswith("http"):
                                    url = "https://www.naukri.com" + url
                                    
                                if url:
                                    can_url = canonical_job_url(url)
                                    jobs_to_scan.append({
                                        "title": title,
                                        "company": company,
                                        "url": can_url if can_url else url,
                                        "raw_url": url,
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
                                
                        for job in jobs_to_scan:
                            cleanup_browser_tabs(context, tracked_pages, active_page=discovery_page)
                            page = discovery_page
                            url = job["url"]
                            raw_url = job.get("raw_url", url)
                            title = job["title"]
                            company = job["company"]
                            card_skills = job.get("card_skills", [])
                            exp_text = job.get("exp_text", "")
                            
                            # Safe Multi-Tier Deduplication: Check Raw URL, Canonical URL, Platform Job ID, and Composite key
                            composite_key = make_composite_key(company, title)
                            can_url = canonical_job_url(url)
                            job_id = extract_platform_job_id(raw_url, platform) or extract_platform_job_id(url, platform)

                            if (
                                url.lower() in processed_ledger
                                or raw_url.lower() in processed_ledger
                                or can_url in processed_ledger
                                or (job_id and job_id in processed_ledger)
                                or composite_key in processed_ledger
                            ):
                                continue

                            # Negative Company Gating (e.g. TCS / Tata Consultancy Services)
                            comp_lower = company.lower().strip()
                            if any(
                                (nc in comp_lower if len(nc) > 3 else re.search(rf'\b{re.escape(nc)}\b', comp_lower))
                                for nc in negative_companies
                            ):
                                print(f"  -> Rejecting Negative Company Job: {title} @ {company} [COMPANY EXCLUDED]", flush=True)
                                processed_ledger.add(url.lower())
                                processed_ledger.add(can_url)
                                if job_id: processed_ledger.add(job_id)
                                processed_ledger.add(composite_key)
                                ctx.add_to_processed_ledger(can_url, status="negative_company_gated", metadata={"title": title, "company": company})
                                ctx.add_to_processed_ledger(composite_key, status="composite_negative_company_gated")
                                continue
                                
                            if not is_title_allowed(
                                title,
                                all_positive_targets,
                                negative_keywords,
                                card_skills=card_skills,
                                exp_text=exp_text,
                                ai_client=ai,
                                config=config,
                                ctx=ctx
                            ):
                                print(f"  -> Rejecting Irrelevant Job: {title} @ {company} [DOMAIN GATED]", flush=True)
                                processed_ledger.add(url.lower())
                                processed_ledger.add(can_url)
                                if job_id: processed_ledger.add(job_id)
                                processed_ledger.add(composite_key)
                                ctx.add_to_processed_ledger(can_url, status="domain_gated", metadata={"title": title, "company": company})
                                ctx.add_to_processed_ledger(composite_key, status="composite_gated")
                                continue
                                
                            print(f"  -> Deep Scanning: {title} @ {company}...", flush=True)
                            nav_url = can_url if can_url else url
                            
                            detail_page = context.new_page()
                            tracked_pages.add(detail_page)
                            scan_success = False
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
                                    # Anti-Blank Page Protection: verify body has rendered
                                    if detail_page.locator("body").count() > 0 and len(detail_page.inner_text("body").strip()) < 50:
                                        detail_page.wait_for_timeout(1000)
                                        if len(detail_page.inner_text("body").strip()) < 50:
                                            detail_page.reload(wait_until="domcontentloaded", timeout=25000)
                                            detail_page.wait_for_timeout(1500)
                                except Exception as parse_error:
                                    time.sleep(1)
                                    try:
                                        detail_page.goto(nav_url, wait_until="domcontentloaded", timeout=25000)
                                        detail_page.wait_for_timeout(1500)
                                    except Exception as e2:
                                        print(f"     [ERROR READING FULL DESCRIPTION] Details: {str(e2)}", flush=True)
                                        continue

                                # Re-verify opened page URL against ledger in case of redirects
                                page_can_url = canonical_job_url(detail_page.url)
                                page_job_id = extract_platform_job_id(detail_page.url, platform)
                                if (
                                    page_can_url in processed_ledger
                                    or (page_job_id and page_job_id in processed_ledger)
                                ):
                                    print(f"     [ALREADY PROCESSED (REDIRECTED: {page_can_url})] Skipping.", flush=True)
                                    continue

                                # PRE-TAILORING NATIVE 1-CLICK APPLY VERIFICATION (Eliminates Token Waste)
                                if platform == "naukri":
                                    # Wait for apply button or already applied banner to render in DOM
                                    for _ in range(8):
                                        if (
                                            detail_page.locator("button#apply-button, button.apply-button, button:has-text('Apply on Naukri'), button:has-text('Apply'), div.apply-button-container button, .styles_jds-apply-button__WbS2i button").count() > 0
                                            or detail_page.locator("button:has-text('Apply on company website'), a:has-text('Apply on company website'), button:has-text('Apply on Company Site'), a:has-text('Apply on Company Site'), #company-site-button").count() > 0
                                            or detail_page.locator("button:has-text('Already Applied'), span:has-text('Already Applied'), div:has-text('You have already applied'), button:has-text('Applied')").count() > 0
                                        ):
                                            break
                                        time.sleep(0.5)

                                    # 1. Already Applied Check
                                    is_already_applied = detail_page.locator("button:has-text('Already Applied'), span:has-text('Already Applied'), div:has-text('You have already applied'), button:has-text('Applied')").count() > 0
                                    if is_already_applied:
                                        print("     [ALREADY APPLIED ON NAUKRI - SKIPPING]", flush=True)
                                        processed_ledger.add(url.lower())
                                        processed_ledger.add(can_url)
                                        if job_id: processed_ledger.add(job_id)
                                        if page_job_id: processed_ledger.add(page_job_id)
                                        processed_ledger.add(composite_key)
                                        ctx.add_to_processed_ledger(can_url, status="already_applied", metadata={"title": title, "company": company})
                                        ctx.add_to_processed_ledger(composite_key, status="composite_already_applied")
                                        continue

                                    # 2. External Apply Check
                                    is_external = detail_page.locator("button:has-text('Apply on company website'), a:has-text('Apply on company website'), button:has-text('Apply on Company Site'), a:has-text('Apply on Company Site'), #company-site-button").count() > 0
                                    if is_external:
                                        print("     [EXTERNAL APPLY GATED - ZERO TOKEN TAILORING]", flush=True)
                                        processed_ledger.add(url.lower())
                                        processed_ledger.add(can_url)
                                        if job_id: processed_ledger.add(job_id)
                                        if page_job_id: processed_ledger.add(page_job_id)
                                        processed_ledger.add(composite_key)
                                        ctx.add_to_processed_ledger(can_url, status="external_apply", metadata={"title": title, "company": company})
                                        ctx.add_to_processed_ledger(composite_key, status="composite_external")
                                        save_external_job_record(profile_dir, {"title": title, "company": company, "platform": platform, "url": can_url}, detail_page.url)
                                        continue

                                    # 3. Native Apply Check
                                    has_native_apply = detail_page.locator("button#apply-button, button.apply-button, button:has-text('Apply on Naukri'), button:has-text('Apply'), div.apply-button-container button, .styles_jds-apply-button__WbS2i button").count() > 0
                                    if not has_native_apply:
                                        print("     [NO NATIVE APPLY BUTTON FOUND ON NAUKRI - SKIPPING]", flush=True)
                                        processed_ledger.add(url.lower())
                                        processed_ledger.add(can_url)
                                        if job_id: processed_ledger.add(job_id)
                                        if page_job_id: processed_ledger.add(page_job_id)
                                        processed_ledger.add(composite_key)
                                        ctx.add_to_processed_ledger(can_url, status="no_native_apply", metadata={"title": title, "company": company})
                                        continue

                                elif platform == "linkedin":
                                    for _ in range(8):
                                        if (
                                            detail_page.locator("button:has-text('Easy Apply'), button.jobs-apply-button:has-text('Easy Apply')").count() > 0
                                            or detail_page.locator(".jobs-s-apply__applied-date, span:has-text('Applied'), button:has-text('Applied')").count() > 0
                                            or detail_page.locator("button:has-text('Apply')").count() > 0
                                        ):
                                            break
                                        time.sleep(0.5)

                                    # 1. Already Applied Check
                                    is_already_applied = detail_page.locator(".jobs-s-apply__applied-date, span:has-text('Applied'), button:has-text('Applied')").count() > 0
                                    if is_already_applied:
                                        print("     [ALREADY APPLIED ON LINKEDIN - SKIPPING]", flush=True)
                                        processed_ledger.add(url.lower())
                                        processed_ledger.add(can_url)
                                        if job_id: processed_ledger.add(job_id)
                                        if page_job_id: processed_ledger.add(page_job_id)
                                        processed_ledger.add(composite_key)
                                        ctx.add_to_processed_ledger(can_url, status="already_applied", metadata={"title": title, "company": company})
                                        ctx.add_to_processed_ledger(composite_key, status="composite_already_applied")
                                        continue

                                    # 2. Native Easy Apply Check
                                    has_easy_apply = detail_page.locator("button:has-text('Easy Apply'), button.jobs-apply-button:has-text('Easy Apply')").count() > 0
                                    if not has_easy_apply:
                                        print("     [EXTERNAL APPLY ON LINKEDIN - ZERO TOKEN TAILORING]", flush=True)
                                        processed_ledger.add(url.lower())
                                        processed_ledger.add(can_url)
                                        if job_id: processed_ledger.add(job_id)
                                        if page_job_id: processed_ledger.add(page_job_id)
                                        processed_ledger.add(composite_key)
                                        ctx.add_to_processed_ledger(can_url, status="external_apply", metadata={"title": title, "company": company})
                                        ctx.add_to_processed_ledger(composite_key, status="composite_external")
                                        save_external_job_record(profile_dir, {"title": title, "company": company, "platform": platform, "url": can_url}, detail_page.url)
                                        continue
                                    
                                if platform == "naukri":
                                    # 1. Scrape Naukri Native Match Score (ATS Portal Signals)
                                    try:
                                        naukri_match_score = detail_page.evaluate("""() => {
                                            const scores = {};
                                            const container = document.querySelector('div.styles_JDC__match-score__VnjLL, div[class*="match-score"]');
                                            if (!container) return scores;
                                            const items = container.querySelectorAll('div.styles_MS__details__iS7mj, div[class*="MS__details"]');
                                            items.forEach(it => {
                                                const label = it.querySelector('span')?.innerText?.trim();
                                                const isMatched = it.querySelector('i.ni-icon-check_circle') !== null;
                                                if (label) {
                                                    scores[label] = isMatched;
                                                }
                                            });
                                            return scores;
                                        }""")
                                        if naukri_match_score:
                                            print(f"     [NAUKRI MATCH SCORE] {json.dumps(naukri_match_score)}", flush=True)
                                    except Exception:
                                        naukri_match_score = {}

                                    # 2. Click "Read More" to un-clamp full description and culture/benefits
                                    try:
                                        detail_page.evaluate("""() => {
                                            const rmEls = Array.from(document.querySelectorAll('span.styles_rm-link__RgrMs, .customReadMoreLabelClass, .styles_read-more-link__dD_5h, .read-more-label, span.rm-link, div[class*="read-more"] span, div[class*="read-more"] a'));
                                            for (const el of rmEls) {
                                                if (el && el.innerText && el.innerText.toLowerCase().includes('read more')) {
                                                    el.click();
                                                }
                                            }
                                        }""")
                                        detail_page.wait_for_timeout(600)
                                    except Exception:
                                        pass

                                    # 3. Extract Job Highlights
                                    highlights_els = detail_page.locator("ul.styles_JDC__job-highlight-list__QZC12 li, ul[class*='job-highlight'] li").all()
                                    highlights_list = [h.inner_text().strip() for h in highlights_els if h.inner_text().strip()]

                                    # 4. Extract Main Job Description
                                    desc_selector = ".styles_JDC__dang-inner-html__h0K4t, .dang-inner-html, .job-desc, section.job-desc, .styles_Jd__text__bWMxs"
                                    for _ in range(8):
                                        if detail_page.locator(desc_selector).count() > 0 and len(detail_page.locator(desc_selector).first.inner_text().strip()) > 50:
                                            break
                                        time.sleep(1)
                                    desc_el = detail_page.locator(desc_selector).first
                                    main_desc = desc_el.inner_text().strip() if desc_el.count() else ""

                                    # 5. Extract Extended Description (un-clamped by Read More)
                                    ext_desc_el = detail_page.locator("div.styles_read-more__TFiRZ, div[class*='read-more-below-slides-desc']").first
                                    ext_desc = ext_desc_el.inner_text().strip() if ext_desc_el.count() else ""

                                    # 6. Extract Deduplicated Key Skills
                                    skills_el = detail_page.locator("div.styles_key-skill__GIPn_ a span, a.styles_chip__7YqPJ span, .styles_chip__7YCfG span, .tags a, .job-tags a").all()
                                    raw_skills = [sk.inner_text().strip() for sk in skills_el if sk.inner_text().strip()]
                                    extracted_skills = list(dict.fromkeys(raw_skills))

                                    # 7. Extract Specifications & Education
                                    details_el = detail_page.locator("div.styles_other-details__oEN4O, div[class*='other-details'], div.other-details, div[class*='jds-details'], section[class*='job-desc-container'] [class*='details']").first
                                    other_details_text = details_el.inner_text().strip() if details_el.count() else ""

                                    edu_el = detail_page.locator("div.styles_education__KXFkO, div[class*='education']").first
                                    edu_text = edu_el.inner_text().strip() if edu_el.count() else ""

                                    # 8. Assemble Full Comprehensive JD
                                    desc_sections = []
                                    if highlights_list:
                                        desc_sections.append("Job Highlights:\n" + "\n".join(f"- {h}" for h in highlights_list))
                                    if main_desc:
                                        desc_sections.append(f"Job Description:\n{main_desc}")
                                    if ext_desc and ext_desc not in main_desc:
                                        desc_sections.append(f"Additional Details & Benefits:\n{ext_desc}")
                                    if other_details_text:
                                        desc_sections.append(f"Job Specifications:\n{other_details_text}")
                                    if edu_text:
                                        desc_sections.append(f"Education Requirements:\n{edu_text}")
                                    if extracted_skills:
                                        desc_sections.append(f"Key Skills: {', '.join(extracted_skills)}")

                                    full_desc = "\n\n".join(desc_sections) if desc_sections else main_desc
                                else:
                                    desc_selector = "div.jobs-description__content, div.description__text"
                                    for _ in range(8):
                                        if detail_page.locator(desc_selector).count() > 0:
                                            break
                                        time.sleep(1)
                                    desc_el = detail_page.locator(desc_selector).first
                                    skills_el = []
                                    other_details_text = ""
                                    full_desc = desc_el.inner_text().strip() if desc_el.count() else ""
                                    extracted_skills = []

                                scan_success = True
                            finally:
                                try:
                                    if not detail_page.is_closed():
                                        detail_page.close()
                                except Exception:
                                    pass
                                tracked_pages.discard(detail_page)

                            if not scan_success or not full_desc:
                                if not full_desc and scan_success:
                                    print("     [FAILED - NO DESCRIPTION FOUND ON PAGE]", flush=True)
                                    processed_ledger.add(url.lower())
                                    processed_ledger.add(can_url)
                                    if job_id: processed_ledger.add(job_id)
                                    if page_job_id: processed_ledger.add(page_job_id)
                                    processed_ledger.add(composite_key)
                                    ctx.add_to_processed_ledger(can_url, status="no_description", metadata={"title": title, "company": company})
                                continue
                                
                            eval_res = ai.evaluate_job_match(
                                title,
                                full_desc,
                                config,
                                resume_text,
                                naukri_match_score=naukri_match_score
                            )
                            score = eval_res.get("score", 0) if isinstance(eval_res, dict) else (eval_res[0] if isinstance(eval_res, tuple) else 0)
                            
                            if score >= match_threshold:
                                print(f"     [MATCH QUEUED! Score: {score}%]", flush=True)

                                clean_c = re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_")[:50]
                                clean_t = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]
                                app_folder = profile_dir / "output" / "applications" / f"{clean_c}_{clean_t}"
                                app_folder.mkdir(parents=True, exist_ok=True)

                                jd_file_path = app_folder / "Job_Description.md"
                                jd_file_path.write_text(full_desc, encoding="utf-8")

                                job_meta = {
                                    "title": title,
                                    "company": company,
                                    "location": primary_loc,
                                    "url": can_url if can_url else url,
                                    "platform": platform,
                                    "score": score,
                                    "extracted_skills": extracted_skills,
                                    "naukri_match_score": naukri_match_score,
                                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                                (app_folder / "job_details.json").write_text(json.dumps(job_meta, indent=2), encoding="utf-8")

                                job_entry = {
                                    "title": title,
                                    "company": company,
                                    "location": primary_loc,
                                    "url": can_url if can_url else url,
                                    "platform": platform,
                                    "score": score,
                                    "jd_path": str(jd_file_path.resolve()),
                                    "description": full_desc,
                                    "naukri_match_score": naukri_match_score
                                }
                                current_batch.append(job_entry)
                                processed_ledger.add(url.lower())
                                processed_ledger.add(can_url)
                                if job_id: processed_ledger.add(job_id)
                                if page_job_id: processed_ledger.add(page_job_id)
                                processed_ledger.add(composite_key)
                                ctx.add_to_processed_ledger(can_url, status="qualified", metadata={"title": title, "company": company, "score": score})
                                ctx.add_to_processed_ledger(composite_key, status="composite_qualified")
                                
                                if len(current_batch) >= BATCH_SIZE:
                                    process_batch(current_batch, profile_dir, current_platform_exec)
                                    applied_count += len(current_batch)
                                    current_batch.clear()
                            else:
                                print(f"     [FAILED. Score: {score}%]", flush=True)
                                processed_ledger.add(url.lower())
                                processed_ledger.add(can_url)
                                if job_id: processed_ledger.add(job_id)
                                if page_job_id: processed_ledger.add(page_job_id)
                                processed_ledger.add(composite_key)
                                ctx.add_to_processed_ledger(can_url, status="low_score", metadata={"title": title, "company": company, "score": score})
                                
                            if applied_count >= max_applies:
                                break
                        if applied_count >= max_applies:
                            break
                    if applied_count >= max_applies:
                        break
                if applied_count >= max_applies:
                    break
            if applied_count >= max_applies:
                break
                
    if current_batch:
        process_batch(current_batch, profile_dir, current_platform_exec)
        applied_count += len(current_batch)
        current_batch.clear()
        
    # Tier 4: Autonomous Starvation Recovery & Seniority Auto-Expansion
    if applied_count == 0 and session_seen_titles:
        print(f"\n=======================================================", flush=True)
        print(f" [STARVATION DETECTED] 0 applications qualified across discovery sweep.", flush=True)
        print(f" Triggering Autonomous Brain Starvation Analysis & Seniority Expansion...", flush=True)
        print(f"=======================================================\n", flush=True)
        try:
            expanded_titles = ai.analyze_and_expand_designations(
                resume_text=resume_text,
                candidate_exp=float(exp_years or 0),
                current_keywords=keywords,
                market_seen_titles=list(session_seen_titles)
            )
            if expanded_titles:
                current_recommended = ctx.config.setdefault("target_jobs", {}).setdefault("recommended_titles", [])
                added = []
                for et in expanded_titles:
                    if et not in current_recommended and et not in keywords:
                        current_recommended.append(et)
                        added.append(et)
                if added:
                    ctx.save_config()
                    print(f" [STARVATION AUTO-HEALED] Discovered {len(added)} senior designations matching candidate profile:", flush=True)
                    for t in added:
                        print(f"   + {t}", flush=True)
                    print(f" Config updated atomically. Next discovery cycle will search with expanded target keywords.\n", flush=True)
        except Exception as starvation_err:
            logger.warning(f"Notice during starvation analysis: {starvation_err}")

    # Advance search cycle for next run
    try:
        ai.advance_search_cycle()
    except Exception as e:
        logger.warning(f"Notice advancing search cycle: {e}")

    try:
        if discovery_page and not discovery_page.is_closed():
            discovery_page.close()
    except Exception:
        pass

    print(f"\n=== BATCH DISCOVERY COMPLETE. Processed {applied_count} total applications. ===", flush=True)


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
