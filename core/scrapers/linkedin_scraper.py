import time
import re
from urllib.parse import quote_plus
from .base_scraper import JobBoardScraper

class LinkedInScraper(JobBoardScraper):
    def build_urls(self):
        urls = []
        kw_str = quote_plus(" ".join(self.ctx.target_keywords[:4]))
        for loc in (self.ctx.target_locations or []):
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