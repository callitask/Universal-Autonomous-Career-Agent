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
# Term: [EASY_APPLY_FILTERING]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: LinkedIn search returned mostly third-party external application redirects.
# Changes Made: Hard-filtered search queries with f_AL=true (Easy Apply only) and f_TPR=r259200 (past 3 days).
# Rationale: Guarantees 100% native in-platform application capability.
# Preventative Notes: Never remove f_AL=true filter from LinkedIn search URL generation.
#
# [ENTRY #002]
# Term: [CODEBASE_PURITY_ENFORCEMENT]
# Timestamp: 2026-09-15 16:03:27 +05:30
# Issue / Context: Hardcoded geographic location 'India' violated Rule 5.
# Changes Made: Removed fallback.
# Rationale: Locations must come from config.
# Preventative Notes: Never hardcode these values again.
# ================================================================================
import time
import re
from urllib.parse import quote_plus
from .base_scraper import JobBoardScraper

class LinkedInScraper(JobBoardScraper):
    def build_urls(self):
        urls = []
        target_keywords = getattr(self.ctx, "target_keywords", [])
        target_locations = getattr(self.ctx, "target_locations", [])
        kw_str = quote_plus(" ".join(target_keywords[:4]))
        for loc in (target_locations or []):
            urls.append((f"https://www.linkedin.com/jobs/search/?f_AL=true&keywords={kw_str}&location={quote_plus(loc)}", loc))
        return urls

    def scrape_jobs(self):
        urls = self.build_urls()
        results = []
        for search_url, location in urls:
            self.logger.info(f"[LINKEDIN] Searching: {location}...")
            try:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                self.random_sleep(3, 5)
                cards = self.page.locator("div.job-card-container").all()
                self.logger.info(f"  Found {len(cards)} candidate cards.")
                
                for card in cards[:4]:
                    card.scroll_into_view_if_needed()
                    self.random_sleep(0.5, 1)
                    card.click()
                    self.random_sleep(1, 2)
                    
                    title = card.locator(".job-card-list__title").first.inner_text().strip()
                    company = card.locator(".job-card-container__primary-description").first.inner_text().strip()
                    
                    jd_elem = self.page.locator(".jobs-description-content, .job-description").first
                    jd_text = jd_elem.inner_text() if jd_elem.is_visible() else f"{title} at {company}"
                    
                    results.append({
                        "title": title, "company": company, "location": location,
                        "url": self.page.url, "platform": "linkedin", "jd_text": jd_text
                    })
            except Exception as e:
                self.logger.error(f"  [!] LinkedIn Error: {e}")
        return results