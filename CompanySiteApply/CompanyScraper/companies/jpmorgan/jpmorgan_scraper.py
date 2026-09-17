# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [JPMC_SCRAPER_IMPLEMENTATION]
# Timestamp: 2026-09-16 12:42:00 +05:30
# Issue / Context: Scraper for JPMorgan Chase Oracle Cloud HCM Candidate Experience portal.
# Changes Made: Implemented JPMorganScraper inheriting BaseCompanyScraper, supporting
#               query parameter navigation, DOM tile extraction, and detailed JD scraping.
# Rationale: Enables autonomous discovery and targeted role evaluation for JPMC.
# Preventative Notes: Config loaded dynamically from config.json; zero hardcoding.
# ==============================================================================

import json
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from CompanySiteApply.CompanyScraper.base_scraper import BaseCompanyScraper


class JPMorganScraper(BaseCompanyScraper):
    """
    Company-specific scraper for JPMorgan Chase on Oracle Cloud HCM (CX_1001).
    """

    def __init__(self, cdp_url: str = "http://localhost:9222"):
        super().__init__(cdp_url)
        # Load config dynamically from same folder
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    @property
    def company_name(self) -> str:
        return self.config.get("company_name", "JPMorgan Chase")

    @property
    def portal_type(self) -> str:
        return self.config.get("portal_type", "oracle_cloud_hcm")

    async def search_jobs(self,
                          page: Any,
                          keyword: str,
                          location: str,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a targeted search query on JPMC Oracle HCM portal.
        """
        base_url = self.config["base_jobs_url"]
        params = {"keyword": keyword}
        if location:
            params["location"] = location
            
        search_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print(f"[{self.company_name}] Navigating to search URL: {search_url}")
        
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Scrape job cards from the DOM
        selectors = self.config["selectors"]
        job_tiles_data = await page.evaluate("""(selectors) => {
            const tiles = Array.from(document.querySelectorAll(selectors.job_tile));
            return tiles.map(tile => {
                const link = tile.querySelector(selectors.job_link);
                const titleEl = tile.querySelector(selectors.job_title);
                const locEl = tile.querySelector(selectors.job_location);
                const snipEl = tile.querySelector(selectors.job_snippet);
                
                let title = titleEl ? titleEl.innerText.trim() : '';
                if (!title && link) title = link.innerText.trim();
                
                // Fallback title extraction from first line of text
                if (!title) {
                    const lines = tile.innerText.trim().split('\\n').map(l => l.trim()).filter(Boolean);
                    title = lines[0] || 'Unknown Role';
                }
                
                // Extract Job ID from link href
                const href = link ? link.href : '';
                const idMatch = href.match(/\\/job\\/(\\d+)/);
                const jobId = idMatch ? idMatch[1] : '';
                
                return {
                    job_id: jobId,
                    title: title,
                    href: href,
                    location: locEl ? locEl.innerText.trim() : '',
                    snippet: snipEl ? snipEl.innerText.trim() : '',
                    full_tile_text: tile.innerText.trim().replace(/\\n/g, ' -- ')
                };
            });
        }""", selectors)

        self.scraped_jobs = job_tiles_data
        print(f"[{self.company_name}] Extracted {len(self.scraped_jobs)} job tiles.")
        return self.scraped_jobs

    async def scrape_job_details(self, page: Any, job_id_or_url: str) -> Dict[str, Any]:
        """
        Deeply inspects an individual job description page.
        """
        if job_id_or_url.startswith("http"):
            target_url = job_id_or_url
        else:
            target_url = f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job_id_or_url}"

        print(f"[{self.company_name}] Inspecting job detail: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        selectors = self.config["selectors"]
        details = await page.evaluate("""(selectors) => {
            const titleEl = document.querySelector(selectors.detail_title);
            const subEl = document.querySelector(selectors.detail_subtitle);
            const descEl = document.querySelector(selectors.detail_description);
            let applyBtn = null;
            try {
                applyBtn = document.querySelector(selectors.apply_button);
            } catch(e) {}
            if (!applyBtn) {
                applyBtn = Array.from(document.querySelectorAll('button, a')).find(b => (b.innerText || '').toUpperCase().includes('APPLY'));
            }
            const fullText = document.body.innerText;
            
            // Extract Requisition ID / Job Identification
            const idMatch = fullText.match(/Job Identification\\s*\\n\\s*(\\d+)/i) || 
                            window.location.href.match(/\\/job\\/(\\d+)/);
            
            // Extract Category
            const catMatch = fullText.match(/Job Category\\s*\\n\\s*([^\\n]+)/i);
            
            // Extract Posting Date
            const postMatch = fullText.match(/Posting Date\\s*\\n\\s*([^\\n]+)/i);

            return {
                job_id: idMatch ? idMatch[1] : '',
                title: titleEl ? titleEl.innerText.trim() : '',
                location: subEl ? subEl.innerText.trim() : '',
                category: catMatch ? catMatch[1].trim() : '',
                posting_date: postMatch ? postMatch[1].trim() : '',
                apply_url: window.location.href,
                has_apply_button: !!applyBtn,
                description: descEl ? descEl.innerText.trim() : fullText.slice(0, 3000),
                full_text: fullText
            };
        }""", selectors)

        return details

