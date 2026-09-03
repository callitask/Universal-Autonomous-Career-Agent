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
MATCH_THRESHOLD = 60


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
    - 2. Deterministic Positive Match: Matches titles using prefix/stem-aware matching,
         domain tokens, or card skill tags from the search page.
    - 3. Tier 2B Cognitive Triage: If unfamiliar or abbreviated, consults the AI Brain
         (ai_client.arbitrate_card_fit). If approved, learns the title into config and passes!
    """
    title_lower = title.lower().strip()

    # 1. Absolute Negative Rejection (C6 Guardrail)
    for neg in negative_keywords:
        neg_clean = str(neg).strip().lower() if neg else ""
        if neg_clean and re.search(rf'\b{re.escape(neg_clean)}\b', title_lower):
            return False

    # 2. Strict Positive Alignment (Domain Relevance)
    if not target_keywords:
        return True

    # 2.1 Direct exact phrase match (case-insensitive)
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        if not target_clean:
            continue
        if re.search(rf'\b{re.escape(target_clean)}\b', title_lower) or target_clean in title_lower:
            return True

    title_tokens = [t for t in re.split(r'[\s/,-]+', title_lower) if len(t) > 2]
    if not title_tokens:
        return False

    # Helper function: tests if a target token matches any title token via exact match or stem/prefix
    def token_matches(target_tok: str, tok_list: list) -> bool:
        for tok in tok_list:
            if tok == target_tok:
                return True
            # Stem/prefix matching for words with length >= 4 (e.g. account/accounts, finance/financial, audit/auditor)
            if len(tok) >= 4 and len(target_tok) >= 4 and (tok.startswith(target_tok[:5]) or target_tok.startswith(tok[:5])):
                return True
        return False

    stopwords = {
        "and", "for", "the", "with", "lead", "senior", "junior", "manager",
        "executive", "officer", "associate", "specialist", "staff", "principal",
        "head", "director", "vp", "intern", "trainee", "expert", "consultant",
        "general", "global", "regional", "assistant", "deputy", "group", "team"
    }

    # 2.2 Target Phrase Stem/Prefix Overlap
    # If all significant tokens of any target keyword match title tokens (via exact or stem match)
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        if not target_clean:
            continue

        target_tokens = [t for t in re.split(r'[\s/,-]+', target_clean) if len(t) > 2 and t not in stopwords]
        if not target_tokens:
            target_tokens = [t for t in re.split(r'[\s/,-]+', target_clean) if len(t) > 2]

        if target_tokens and all(token_matches(tt, title_tokens) for tt in target_tokens):
            return True

    # 2.3 Primary Domain Keyword Direct Match
    # Dynamically extract domain tokens (length >= 4, non-stopwords) from candidate target keywords
    dynamic_domain_tokens = set()
    for target in target_keywords:
        target_clean = str(target).strip().lower() if target else ""
        for t in re.split(r'[\s/,-]+', target_clean):
            if len(t) >= 4 and t not in stopwords:
                dynamic_domain_tokens.add(t)

    # Allow direct domain token matches if a primary domain word is present in the title
    for tt in title_tokens:
        if tt in dynamic_domain_tokens:
            return True
        for dt in dynamic_domain_tokens:
            if len(tt) >= 4 and len(dt) >= 4 and (tt.startswith(dt[:5]) or dt.startswith(tt[:5])):
                return True

    # 2.4 Card Skills Overlap (if search card displayed skill tags)
    if card_skills:
        for cs in card_skills:
            cs_clean = cs.lower().strip()
            if cs_clean in dynamic_domain_tokens:
                return True
            for dt in dynamic_domain_tokens:
                if len(cs_clean) >= 4 and len(dt) >= 4 and (cs_clean.startswith(dt[:5]) or dt.startswith(cs_clean[:5])):
                    return True

    # 3. Tier 2B: Cognitive Brain Arbitration (Fallback for unfamiliar / creative titles)
    if ai_client and hasattr(ai_client, "arbitrate_card_fit"):
        fits, reason = ai_client.arbitrate_card_fit(
            title=title,
            card_skills=card_skills,
            exp_text=exp_text,
            candidate_profile=config
        )
        if fits:
            print(f"     [COGNITIVE BRAIN APPROVED]: '{title}' ({reason})", flush=True)
            # Autonomously learn and persist this new title into candidate_config.json
            if ctx and hasattr(ctx, "config") and hasattr(ctx, "save_config"):
                try:
                    recommended = ctx.config.setdefault("target_jobs", {}).setdefault("recommended_titles", [])
                    clean_title_cand = re.sub(r'[\s/,-]+', ' ', title).strip()
                    if clean_title_cand and clean_title_cand not in recommended:
                        recommended.append(clean_title_cand)
                        ctx.save_config()
                        print(f"     [BRAIN LEARNED NEW DESIGNATION]: Persisted '{clean_title_cand}' to recommended_titles.", flush=True)
                except Exception:
                    pass
            return True

    return False


def cleanup_browser_tabs(context, tracked_pages=None, active_page=None):
    """
    Safely cleans up only tabs opened by the discovery runner without closing unrelated user tabs.
    Preserves user browsing tabs while cleaning up redundant discovery pages.
    """
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
    
    keywords = [k for k in (target.get("keywords") or []) if k and str(k).strip()]
    recommended = [t for t in (target.get("recommended_titles") or []) if t and str(t).strip()]
    current_title = cand.get("current_title", "").strip() if cand.get("current_title") else ""
    all_positive_targets = list(keywords) + list(recommended)
    if current_title and current_title not in all_positive_targets:
        all_positive_targets.append(current_title)
    
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
                
                for kw in keywords:
                    for page_num in range(1, MAX_PAGES_PER_SEARCH + 1):
                        cleanup_browser_tabs(context, tracked_pages, active_page=discovery_page)
                        page = discovery_page
                        
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
                                    jobs_to_scan.append({
                                        "title": title,
                                        "company": company,
                                        "url": url,
                                        "card_skills": skill_tags,
                                        "exp_text": exp_text
                                    })
                            except Exception:
                                continue
                                
                        for job in jobs_to_scan:
                            cleanup_browser_tabs(context, tracked_pages, active_page=discovery_page)
                            page = discovery_page
                            url = job["url"]
                            title = job["title"]
                            company = job["company"]
                            card_skills = job.get("card_skills", [])
                            exp_text = job.get("exp_text", "")
                            
                            if url.lower() in processed_ledger or title.lower() in processed_ledger:
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

                                # Sanitize folder names dynamically (Phase 2 Requirement)
                                clean_c = re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_")[:50]
                                clean_t = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]
                                app_folder = profile_dir / "output" / "applications" / f"{clean_c}_{clean_t}"
                                app_folder.mkdir(parents=True, exist_ok=True)

                                # Immediately write real scraped description to disk
                                jd_file_path = app_folder / "Job_Description.md"
                                jd_file_path.write_text(full_desc, encoding="utf-8")

                                # Write job metadata to job_details.json
                                job_meta = {
                                    "title": title,
                                    "company": company,
                                    "location": primary_loc,
                                    "url": url,
                                    "platform": platform,
                                    "score": score,
                                    "extracted_skills": extracted_skills,
                                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                                (app_folder / "job_details.json").write_text(json.dumps(job_meta, indent=2), encoding="utf-8")

                                # Include jd_path and description in search_manifest.json entry
                                job_entry = {
                                    "title": title,
                                    "company": company,
                                    "location": primary_loc,
                                    "url": url,
                                    "platform": platform,
                                    "score": score,
                                    "jd_path": str(jd_file_path.resolve()),
                                    "description": full_desc
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

    try:
        if discovery_page and not discovery_page.is_closed():
            discovery_page.close()
    except Exception:
        pass

    print(f"\n=== BATCH DISCOVERY COMPLETE. Processed {applied_count} total applications. ===", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    run_batched_discovery(args.profile)