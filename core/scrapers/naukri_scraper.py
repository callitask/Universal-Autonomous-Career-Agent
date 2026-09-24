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
# Term: [SEO_SLUG_GENERATION]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Naukri search forms failed on non-alphanumeric queries and special characters.
# Changes Made: Implemented dynamic SEO slugification ({kw}-jobs-in-{loc}) and URL fallback parameters.
# Rationale: Direct portal URL access bypassing flaky search box input interaction.
# Preventative Notes: Always clean punctuation from search keyword slugs.
#
# [ENTRY #002]
# Term: [CODEBASE_PURITY_ENFORCEMENT]
# Timestamp: 2026-09-15 16:03:27 +05:30
# Issue / Context: Hardcoded geographic location 'india' violated Rule 5.
# Changes Made: Removed fallback.
# Rationale: Locations must come from config.
# Preventative Notes: Never hardcode these values again.
# ================================================================================
import time
import re
from urllib.parse import quote_plus
from .base_scraper import JobBoardScraper

class NaukriScraper(JobBoardScraper):
    def build_urls(self):
        urls = []
        target_keywords = getattr(self.ctx, "target_keywords", [])
        target_locations = getattr(self.ctx, "target_locations", [])
        for kw in target_keywords[:3]:
            slug = "-".join(kw.lower().split())
            for loc in (target_locations or []):
                loc_slug = loc.lower().replace(" ", "-")
                urls.append((f"https://www.naukri.com/{slug}-jobs-in-{loc_slug}", loc, kw))
        return urls

    def scrape_jobs(self):
        urls = self.build_urls()
        results = []
        seen = set()
        
        for search_url, location, keyword in urls:
            self.logger.info(f"[NAUKRI] Searching: '{keyword}' in {location}...")
            try:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                self.random_sleep(3, 5)
                cards = self.page.locator("div.srp-jobtuple-wrapper").all()
                self.logger.info(f"  Found {len(cards)} candidate cards.")
                
                for card in cards[:4]:
                    title_elem = card.locator("a.title").first
                    title = title_elem.inner_text().strip()
                    job_url = title_elem.get_attribute("href")
                    
                    if job_url in seen: continue
                    seen.add(job_url)
                    
                    comp_elem = card.locator("a.comp-name").first
                    company = comp_elem.inner_text().strip() if comp_elem.is_visible() else "Target Company"
                    
                    jd_text = f"{title} at {company}"
                    if job_url:
                        # FIXED: Use self.page.context instead of self.browser.contexts[0]
                        detail_page = self.page.context.new_page()
                        try:
                            detail_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                            self.random_sleep(1, 2)
                            jd_elem = detail_page.locator(".job-desc, .jd-container").first
                            if jd_elem.is_visible(): jd_text = jd_elem.inner_text().strip()
                        except: pass
                        finally: detail_page.close()
                        
                    results.append({
                        "title": title, "company": company, "location": location,
                        "url": job_url, "platform": "naukri", "jd_text": jd_text
                    })
            except Exception as e:
                self.logger.error(f"  [!] Naukri Error: {e}")
        return results