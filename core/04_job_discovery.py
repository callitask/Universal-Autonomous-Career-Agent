"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT
File: core/04_job_discovery.py
================================================================================
Universal Batched Discovery Engine (Naukri + LinkedIn)
- Strict Domain & Title Gating: Completely dynamic, reading purely from candidate 
  config target_jobs constraints. Includes C6 strict negative gating and positive domain gating.
- Score Threshold: Automatically qualifies and applies to roles scoring >= 40%.
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

# Force standard output to UTF-8 and line-buffering (H4 Guardrail)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] 04_job_discovery - %(message)s")
logger = logging.getLogger("04_job_discovery")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.utils.profile_context import ProfileContext
from core.ai_client import AIClient

BATCH_SIZE = 1
MAX_PAGES_PER_SEARCH = 3
MATCH_THRESHOLD = 40


def get_already_processed_urls(profile_dir: Path) -> set:
    """C2 & N1 Fix: Safely parses CSV files handling both new and legacy headers for deduplication."""
    processed = set()
    for file_name in ["applications_tracker.csv", "saved_external_jobs.json"]:
        file_path = profile_dir / "output" / file_name
        
        if file_path.exists() and file_path.suffix == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 1. Try New Schema (Job URL & Job Title)
                    if "Job URL" in row and row["Job URL"]:
                        processed.add(row["Job URL"].strip().lower())
                    if "Job Title" in row and row["Job Title"]:
                        processed.add(row["Job Title"].strip().lower())
                    
                    # 2. Try Legacy Schema (Role maps to title in processed_ledger)
                    if "Role" in row and row["Role"]:
                        processed.add(row["Role"].strip().lower())
                    
                    # 3. DIRECTIVE 7.2 Fallback: Scan all row values for URL patterns
                    for val in row.values():
                        if val and isinstance(val, str) and ("http://" in val or "https://" in val):
                            processed.add(val.strip().lower())
                            
        elif file_path.exists() and file_path.suffix == ".json":
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for item in data:
                    if item.get("url"): 
                        processed.add(item["url"].strip().lower())
                    if item.get("title"): 
                        processed.add(item["title"].strip().lower())
                    if item.get("original_url"):
                        processed.add(item["original_url"].strip().lower())
            except Exception:
                pass
                
    return processed


def is_title_allowed(title: str, target_keywords: list, negative_keywords: list) -> bool:
    """
    C6 Fix: Strictly rejects titles containing negative keywords unconditionally.
    Positive Alignment: Requires the title to match at least one target keyword logically.
    """
    title_lower = title.lower().strip()

    # 1. Absolute Negative Rejection (C6 Guardrail)
    for neg in negative_keywords:
        neg_clean = neg.strip().lower()
        if neg_clean and re.search(rf'\b{re.escape(neg_clean)}\b', title_lower):
            return False

    # 2. Strict Positive Alignment (Domain Relevance)
    if not target_keywords:
        return True

    title_tokens = set([t for t in re.split(r'[\s/,-]+', title_lower) if len(t) > 2])
    
    for target in target_keywords:
        target_clean = target.strip().lower()
        if not target_clean: 
            continue
        
        # Direct substring/phrase match
        if target_clean in title_lower:
            return True
            
        # Token overlap match (e.g. "software engineer" vs "engineer, software")
        target_tokens = set([t for t in re.split(r'[\s/,-]+', target_clean) if len(t) > 2])
        if target_tokens and target_tokens.issubset(title_tokens):
            return True

    return False


def cleanup_browser_tabs(context):
    try:
        pages = context.pages
        while len(pages) > 1:
            pages[-1].close()
            pages = context.pages
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
    # H6 Fix: Add check=True to halt if PDF tailoring fails
    subprocess.run([sys.executable, str(BASE_DIR / "core" / "generate_factual_tailored.py"), "--profile", str(profile_dir)], check=True)
    
    if platform.lower() == "naukri":
        print("  [PIPELINE] 2/3: Fast-Injecting Tailored Resume to Naukri...", flush=True)
        subprocess.run([sys.executable, str(BASE_DIR / "core" / "02b_naukri_fast_resume_upload.py"), "--profile", str(profile_dir)])
    elif platform.lower() == "linkedin":
        print("  [PIPELINE] 2/3: Synchronizing Profile with LinkedIn...", flush=True)
        subprocess.run([sys.executable, str(BASE_DIR / "core" / "03_profile_sync_linkedin.py"), "--profile", str(profile_dir)])
        
    print("  [PIPELINE] 3/3: Executing Application Engine...", flush=True)
    subprocess.run([sys.executable, str(BASE_DIR / "core" / "05_apply_jobs.py"), "--profile", str(profile_dir)])
    
    print(f"\n  ---> Resuming Discovery Sweep...\n", flush=True)


def run_batched_discovery(profile_path: str):
    profile_dir = Path(profile_path).resolve()
    ctx = ProfileContext(profile_dir, BASE_DIR)
    config = ctx.config
    resume_path = profile_dir / "resume.md"
    resume_text = resume_path.read_text(encoding="utf-8") if resume_path.exists() else ""
    
    processed_ledger = get_already_processed_urls(profile_dir)
    ai = AIClient(ctx)
    
    cand = config.get("candidate", {})
    target = config.get("target_jobs", {})
    cdp_url = cand.get("cdp_url", "http://127.0.0.1:9222")
    
    keywords = target.get("keywords", [])
    recommended = target.get("recommended_titles", [])
    all_positive_targets = keywords + recommended
    
    negative_keywords = target.get("negative_keywords", [])
    locations = target.get("locations", [])
    platforms = [p.lower() for p in target.get("platforms", ["naukri"])]
    exp_years = target.get("experience_years", cand.get("total_experience_years", 0))
    max_applies = int(target.get("max_applies_per_day", 50))
    salary_bracket = target.get("salary_filter_bracket", "")
    
    ctc_filter = ""
    if salary_bracket:
        nums = re.findall(r'\d+', salary_bracket)
        if len(nums) >= 2:
            ctc_filter = f"{nums[0]}to{nums[1]}"
            
    applied_count = 0
    current_batch = []
    current_platform_exec = ""
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            cleanup_browser_tabs(context)
            page = context.pages[0] if context.pages else context.new_page()
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
                
                for kw in keywords:
                    for page_num in range(1, MAX_PAGES_PER_SEARCH + 1):
                        cleanup_browser_tabs(context)
                        page = context.pages[0]
                        
                        if platform == "naukri":
                            query_kw = re.sub(r'[^a-z0-9]+', '-', kw.lower()).strip('-')
                            query_loc = re.sub(r'[^a-z0-9]+', '-', primary_loc.lower()).strip('-')
                            base_url = f"https://www.naukri.com/{query_kw}-jobs-in-{query_loc}"
                            if page_num > 1:
                                base_url += f"-{page_num}"
                            query_url = f"{base_url}?experience={int(float(exp_years or 0))}"
                            if ctc_filter:
                                query_url += f"&ctcFilter={ctc_filter}"
                            card_selector = "div.srp-jobtuple-wrapper, article.jobTuple, div.cust-job-tuple"
                            
                        elif platform == "linkedin":
                            query_kw = urllib.parse.quote(kw)
                            query_loc = urllib.parse.quote(primary_loc)
                            start_param = (page_num - 1) * 25
                            query_url = f"https://www.linkedin.com/jobs/search/?keywords={query_kw}&location={query_loc}&f_AL=true&start={start_param}"
                            card_selector = "li.jobs-search-results__list-item, div.job-card-container"
                        else:
                            continue
                            
                        print(f"Searching: '{kw}' | Page {page_num}...", flush=True)
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
                                else:
                                    title_el = card.locator("a.title, a.job-title").first
                                    comp_el = card.locator("a.comp-name, a.companyName").first
                                    
                                if not title_el.count(): continue
                                title = title_el.inner_text().strip()
                                company = comp_el.inner_text().strip() if comp_el.count() else "Hiring Company"
                                url = title_el.get_attribute("href")
                                
                                if platform == "linkedin" and "/view/" in url:
                                    url = url.split("?")[0]
                                elif platform == "naukri" and url and not url.startswith("http"):
                                    url = "https://www.naukri.com" + url
                                    
                                if url:
                                    jobs_to_scan.append({"title": title, "company": company, "url": url})
                            except Exception:
                                continue
                                
                        for job in jobs_to_scan:
                            cleanup_browser_tabs(context)
                            page = context.pages[0]
                            url = job["url"]
                            title = job["title"]
                            company = job["company"]
                            
                            if url.lower() in processed_ledger or title.lower() in processed_ledger:
                                continue
                                
                            if not is_title_allowed(title, all_positive_targets, negative_keywords):
                                print(f"  -> Rejecting Irrelevant Job: {title} @ {company} [DOMAIN GATED]", flush=True)
                                processed_ledger.add(url.lower())
                                continue
                                
                            print(f"  -> Deep Scanning: {title} @ {company}...", flush=True)
                            try:
                                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            except Exception as parse_error:
                                time.sleep(1)
                                try:
                                    page.goto("about:blank")
                                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                                except Exception as e2:
                                    print(f"     [ERROR READING FULL DESCRIPTION] Details: {str(e2)}", flush=True)
                                    continue
                                    
                            is_external = page.locator("button:has-text('Apply on company website'), a:has-text('Apply on company website'), button:has-text('Apply on Company Site'), #company-site-button").count() > 0
                            
                            if is_external:
                                print("     [EXTERNAL APPLY REJECTED]", flush=True)
                                processed_ledger.add(url.lower())
                                continue
                                
                            full_desc = ""
                            extracted_skills = []
                            
                            if platform == "naukri":
                                desc_selector = ".styles_JDC__dang-inner-html__h0K4t, .dang-inner-html, .job-desc, section.job-desc, .styles_Jd__text__bWMxs"
                                for _ in range(8):
                                    if page.locator(desc_selector).count() > 0 and len(page.locator(desc_selector).first.inner_text().strip()) > 50:
                                        break
                                    time.sleep(1)
                                desc_el = page.locator(desc_selector).first
                                skills_el = page.locator(".styles_key-skill__GIPn_ a span, .styles_chip__7YCfG span, a.styles_chip__7YqPJ, .tags a, .job-tags a").all()
                            else:
                                desc_selector = "div.jobs-description__content, div.description__text"
                                for _ in range(8):
                                    if page.locator(desc_selector).count() > 0:
                                        break
                                    time.sleep(1)
                                desc_el = page.locator(desc_selector).first
                                skills_el = []
                                
                            full_desc = desc_el.inner_text().strip() if desc_el.count() else ""
                            extracted_skills = [sk.inner_text().strip() for sk in skills_el if sk.inner_text().strip()]
                            
                            if extracted_skills:
                                full_desc += f"\n\nRequired Skills: {', '.join(extracted_skills)}"
                                
                            if not full_desc:
                                print("     [FAILED - NO DESCRIPTION FOUND ON PAGE]", flush=True)
                                processed_ledger.add(url.lower())
                                continue
                                
                            eval_res = ai.evaluate_job_match(title, full_desc, config, resume_text)
                            score = eval_res.get("score", 0) if isinstance(eval_res, dict) else (eval_res[0] if isinstance(eval_res, tuple) else 0)
                            
                            if score >= MATCH_THRESHOLD:
                                print(f"     [MATCH QUEUED! Score: {score}%]", flush=True)
                                job_entry = {
                                    "title": title, "company": company, "location": primary_loc,
                                    "url": url, "platform": platform, "score": score
                                }
                                current_batch.append(job_entry)
                                processed_ledger.add(url.lower())
                                processed_ledger.add(title.lower())
                                
                                if len(current_batch) >= BATCH_SIZE:
                                    process_batch(current_batch, profile_dir, current_platform_exec)
                                    applied_count += len(current_batch)
                                    current_batch.clear()
                            else:
                                print(f"     [FAILED. Score: {score}%]", flush=True)
                                processed_ledger.add(url.lower())
                                
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
        
    print(f"\n=== BATCH DISCOVERY COMPLETE. Processed {applied_count} total applications. ===", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    run_batched_discovery(args.profile)