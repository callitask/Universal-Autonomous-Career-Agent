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
        if neg_clean and re.search(rf'\b{re.escape(neg_clean)}\b', title_lower):
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
        "general", "global", "regional", "assistant", "deputy", "group", "team"
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
    raw_target_companies = target.get("target_companies", [])
    target_companies = [c.strip() for c in raw_target_companies if c and str(c).strip()]
    if not target_companies:
        cog_prof = ctx.load_cognitive_profile()
        target_companies = [c.strip() for c in (cog_prof.get("top_target_companies") or []) if c and str(c).strip()]

    search_tasks = []
    # 1. Strategy A: Role Only (Broad Domain Sweep)
    for kw in keywords:
        search_tasks.append({
            "strategy": "ROLE_ONLY",
            "query": kw,
            "role": kw,
            "company": ""
        })

    # 2. Strategy B: Target Company Only (Company Infiltration)
    for comp in target_companies:
        search_tasks.append({
            "strategy": "COMPANY_ONLY",
            "query": comp,
            "role": "",
            "company": comp
        })

    # 3. Strategy C: Role AND Company Combined (Precision Match)
    if target_companies:
        for kw in keywords[:3]:
            for comp in target_companies[:3]:
                search_tasks.append({
                    "strategy": "ROLE_AND_COMPANY",
                    "query": f"{kw} {comp}",
                    "role": kw,
                    "company": comp
                })

    print(f"[DISCOVERY CONTROLLER] Multi-Strategy Search Matrix: {len(search_tasks)} tasks (Roles: {len(keywords)}, Companies: {len(target_companies)})", flush=True)
    
    negative_keywords = target.get("negative_keywords", [])
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
                        
                        if platform == "naukri":
                            if strategy == "ROLE_ONLY":
                                query_slug = re.sub(r'[^a-z0-9]+', '-', query_text.lower()).strip('-')
                                loc_slug = re.sub(r'[^a-z0-9]+', '-', primary_loc.lower()).strip('-')
                                base_url = f"https://www.naukri.com/{query_slug}-jobs-in-{loc_slug}"
                                if page_num > 1:
                                    base_url += f"-{page_num}"
                                query_url = f"{base_url}?experience={int(float(exp_years or 0))}&jobAge={job_age_days}{wfh_param}{company_jobs_param}"
                                if ctc_filter:
                                    query_url += f"&ctcFilter={ctc_filter}"
                            elif strategy == "COMPANY_ONLY":
                                encoded_comp = urllib.parse.quote(comp_text)
                                encoded_loc = urllib.parse.quote(primary_loc)
                                query_url = f"https://www.naukri.com/jobs?k={encoded_comp}&l={encoded_loc}&experience={int(float(exp_years or 0))}&jobAge={job_age_days}{wfh_param}{company_jobs_param}"
                                if page_num > 1:
                                    query_url += f"&pageNo={page_num}"
                                if ctc_filter:
                                    query_url += f"&ctcFilter={ctc_filter}"
                            else: # ROLE_AND_COMPANY
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
                                    skill_tags = []
                                else:
                                    title_el = card.locator("a.title, a.job-title").first
                                    comp_el = card.locator("a.comp-name, a.companyName").first
                                    exp_el = card.locator("span.expwdth, li.experience, span[class*='exp'], span.ni-job-tuple-icon-experience").first
                                    skill_els = card.locator("ul.tags-gt li, ul.dot-gt li, .job-tags a, span[class*='tag']").all()
                                    skill_tags = [sk.inner_text().strip() for sk in skill_els if sk.inner_text().strip()]
                                    
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
                                    jobs_to_scan.append({
                                        "title": title,
                                        "company": company,
                                        "url": can_url if can_url else url,
                                        "raw_url": url,
                                        "card_skills": skill_tags,
                                        "exp_text": exp_text
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
                                    desc_selector = ".styles_JDC__dang-inner-html__h0K4t, .dang-inner-html, .job-desc, section.job-desc, .styles_Jd__text__bWMxs"
                                    for _ in range(8):
                                        if detail_page.locator(desc_selector).count() > 0 and len(detail_page.locator(desc_selector).first.inner_text().strip()) > 50:
                                            break
                                        time.sleep(1)
                                    desc_el = detail_page.locator(desc_selector).first
                                    skills_el = detail_page.locator(".styles_key-skill__GIPn_ a span, .styles_chip__7YCfG span, a.styles_chip__7YqPJ, .tags a, .job-tags a").all()
                                    details_el = detail_page.locator("div[class*='other-details'], div.other-details, div[class*='jds-details'], section[class*='job-desc-container'] [class*='details']").first
                                    other_details_text = details_el.inner_text().strip() if details_el.count() else ""
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
                                extracted_skills = [sk.inner_text().strip() for sk in skills_el if sk.inner_text().strip()]
                                
                                if other_details_text:
                                    full_desc += f"\n\nJob Specifications:\n{other_details_text}"
                                if extracted_skills:
                                    full_desc += f"\n\nRequired Skills: {', '.join(extracted_skills)}"

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
                                
                            eval_res = ai.evaluate_job_match(title, full_desc, config, resume_text)
                            score = eval_res.get("score", 0) if isinstance(eval_res, dict) else (eval_res[0] if isinstance(eval_res, tuple) else 0)
                            
                            if score >= MATCH_THRESHOLD:
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
                                    "description": full_desc
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
