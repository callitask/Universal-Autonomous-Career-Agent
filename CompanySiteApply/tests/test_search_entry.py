# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_SEARCH_ENTRY_GUARD]
# Timestamp: 2026-10-13 00:30:00 +05:30
# Issue / Context: Scraper navigated to bare .../sites/CX_1002/jobs which
#                  Oracle CX rejects with "Page not found"; the URL-substring
#                  guard then skipped recovery and scraped the error page.
# Changes Made: Async regression tests pinning site-root entry, widget
#               liveness verification, and loud refusal on persistent 404.
# Preventative Notes: Never navigate Oracle CX by deep link without
#                     verifying the widget rendered.
# ==============================================================================

import unittest
from unittest.mock import AsyncMock, MagicMock

from CompanySiteApply.CompanyScraper.companies.jpmorgan.jpmorgan_scraper import (
    JPMorganScraper,
)

_SELECTORS = {"keyword_input": "#keyword", "location_input": "#location"}
_SITE_ROOT = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/"


def _page(title="Search Jobs", widget=True):
    page = MagicMock()
    page.title = AsyncMock(return_value=title)
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    el = MagicMock()
    el.count = AsyncMock(return_value=1 if widget else 0)
    el.is_visible = AsyncMock(return_value=widget)
    loc = MagicMock()
    loc.first = el
    page.locator.return_value = loc
    page.url = _SITE_ROOT + "jobs"
    return page


class TestSearchEntryGuard(unittest.IsolatedAsyncioTestCase):
    async def test_live_widget_skips_navigation(self):
        scraper = JPMorganScraper.__new__(JPMorganScraper)
        page = _page()
        self.assertTrue(await scraper._ensure_search_page(page, _SITE_ROOT, _SELECTORS))
        page.goto.assert_not_called()

    async def test_404_recovers_via_site_root(self):
        scraper = JPMorganScraper.__new__(JPMorganScraper)
        page = _page(title="Page not found. - Chase- Candidate Experience page Careers", widget=False)
        el = MagicMock()
        el.count = AsyncMock(side_effect=[0, 1])
        el.is_visible = AsyncMock(return_value=True)
        loc = MagicMock()
        loc.first = el
        page.locator.return_value = loc
        page.title = AsyncMock(side_effect=[
            "Page not found. - Chase- Candidate Experience page Careers",
            "Search Jobs",
            "Search Jobs",
        ])
        self.assertTrue(await scraper._ensure_search_page(page, _SITE_ROOT, _SELECTORS))
        called_urls = [c.args[0] for c in page.goto.await_args_list]
        self.assertTrue(all(u == _SITE_ROOT for u in called_urls))

    async def test_persistent_404_refuses_loudly(self):
        scraper = JPMorganScraper.__new__(JPMorganScraper)
        page = _page(title="Page not found.", widget=False)
        self.assertFalse(await scraper._ensure_search_page(page, _SITE_ROOT, _SELECTORS))


if __name__ == "__main__":
    unittest.main()
