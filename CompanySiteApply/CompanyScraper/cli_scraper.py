# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [CLI_SCRAPER_INTERFACE]
# Timestamp: 2026-09-16 12:44:00 +05:30
# Issue / Context: Interactive CLI entrypoint for searching & scraping company career portals.
# Changes Made: Implemented cli_scraper.py supporting company dispatching, dynamic
#               candidate config loading, profile match ranking, and JSON export.
# Rationale: Standardizes company discovery and targeted role selection.
# ==============================================================================

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.async_api import async_playwright
from CompanySiteApply.CompanyScraper.companies.jpmorgan.jpmorgan_scraper import JPMorganScraper
from CompanySiteApply.utils.config_resolver import resolve_candidate_config

COMPANY_MAP = {
    "jpmorgan": JPMorganScraper,
    "jpmc": JPMorganScraper
}


def load_candidate_config(config_path: str | None = None) -> Dict[str, Any]:
    return resolve_candidate_config(explicit_path=config_path)


async def run_scraper(company: str,
                      keyword: str,
                      location: str,
                      top_n: int = 5,
                      inspect_top: bool = True,
                      config_path: str | None = None,
                      profile_dir: str | None = None):
    scraper_cls = COMPANY_MAP.get(company.lower())
    if not scraper_cls:
        print(f"Error: Unknown company '{company}'. Available: {list(COMPANY_MAP.keys())}")
        return

    candidate_cfg = load_candidate_config(config_path) if config_path else resolve_candidate_config(
        candidate_data={"profile_dir": profile_dir} if profile_dir else None
    )
    scraper = scraper_cls()

    print(f"==================================================")
    print(f"  CompanyScraper: {scraper.company_name} ({scraper.portal_type})")
    print(f"  Target Keyword: '{keyword}' | Location: '{location}'")
    print(f"==================================================")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        
        # Check for existing page or create new
        pages = context.pages
        target_page = None
        for page in pages:
            if "jpmc" in page.url or "oraclecloud" in page.url:
                target_page = page
                break
        if not target_page:
            target_page = await context.new_page()

        await target_page.bring_to_front()

        # 1. Search jobs
        jobs = await scraper.search_jobs(target_page, keyword, location)
        if not jobs:
            print("No jobs found matching criteria.")
            return

        # 2. Score jobs based on candidate profile
        ranked_jobs = []
        for j in jobs:
            match_score = scraper.score_job_match(j, candidate_cfg)
            j["match_score"] = match_score
            ranked_jobs.append(j)

        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)

        print(f"\nTop {min(top_n, len(ranked_jobs))} Ranked Roles for Candidate:")
        for idx, r in enumerate(ranked_jobs[:top_n], start=1):
            print(f"  [{idx}] Match: {int(r['match_score'] * 100)}% | ID: {r['job_id']} | Title: {r['title']}")
            print(f"      Location: {r['location']}")
            print(f"      Link: {r['href']}")

        # 3. Deeply inspect the #1 target role if requested
        if inspect_top and ranked_jobs:
            top_role = ranked_jobs[0]
            print(f"\n--- Deeply Inspecting Top Role: {top_role['title']} ({top_role['job_id']}) ---")
            details = await scraper.scrape_job_details(target_page, top_role["href"])
            print(f"Job Category: {details.get('category')}")
            print(f"Posting Date: {details.get('posting_date')}")
            print(f"Apply Button Present: {details.get('has_apply_button')}")
            desc_snippet = details.get('description', '')[:800].encode('ascii', 'replace').decode('ascii')
            print(f"\nDescription Snippet:\n{desc_snippet}...\n")

            # Save top role details to candidate output directory (dynamic, no hardcoded profile)
            from CompanySiteApply.utils.config_resolver import _repo_root as _root
            from core.utils.sanitize import safe_filename
            _base = Path(profile_dir) if profile_dir else (_root() / "profiles" / "default_user")
            output_dir = _base / "APPLIED ON COMPANY WEBSITE" / safe_filename(scraper.company_name) / safe_filename(top_role['title'])
            output_dir.mkdir(parents=True, exist_ok=True)
            jd_path = output_dir / "job_description.json"
            jd_path.write_text(json.dumps(details, indent=2), encoding="utf-8")
            print(f"Saved job description to: {jd_path}")

        # Export all scraped jobs
        from pathlib import Path as _P
        _base = _P(profile_dir) if profile_dir else (_root() / "profiles" / "default_user")
        export_path = str(_base / "output" / f"{company}_scraped_jobs.json")
        scraper.export_scraped_jobs(export_path)


def main():
    parser = argparse.ArgumentParser(description="CompanyScraper CLI")
    parser.add_argument("--company", type=str, default="jpmorgan", help="Target company name")
    parser.add_argument("--keyword", type=str, default="", help="Job search keyword")
    parser.add_argument("--location", type=str, default="", help="Target location")
    parser.add_argument("--top", type=int, default=5, help="Number of top jobs to display")
    parser.add_argument("--no-inspect", action="store_true", help="Skip deep inspection of top role")
    parser.add_argument("--config", type=str, default=None, help="Path to candidate_config.json")
    parser.add_argument("--profile", type=str, default=None, help="Profile dir (e.g. profiles/default_user)")

    args = parser.parse_args()
    asyncio.run(run_scraper(
        company=args.company,
        keyword=args.keyword,
        location=args.location,
        top_n=args.top,
        inspect_top=not args.no_inspect,
        config_path=args.config,
        profile_dir=args.profile,
    ))


if __name__ == "__main__":
    main()
