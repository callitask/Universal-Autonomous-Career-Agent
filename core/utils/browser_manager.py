"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - BROWSER & CDP CONTEXT MANAGER
File: core/utils/browser_manager.py
================================================================================
Universal CDP (Chrome DevTools Protocol) browser connector and context manager.
Connects directly to running Chrome instances on port 9222, providing resilient
page lifecycle, tab reuse, foreground focusing, and context management across all platforms.
================================================================================
"""

import time
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """
    Manages Playwright connection to an active Chrome instance via CDP.
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    def start(self) -> BrowserContext:
        """Starts Playwright and connects to Chrome over CDP."""
        if not self.playwright:
            self.playwright = sync_playwright().start()

        if not self.browser or not self.browser.is_connected():
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(self.cdp_url)
            except Exception as e:
                raise RuntimeError(
                    f"[BrowserManager] Failed to connect to Chrome at {self.cdp_url}. "
                    f"Ensure Chrome is initialized with '--remote-debugging-port=9222'. Error: {e}"
                )

        if self.browser.contexts:
            self.context = self.browser.contexts[0]
        else:
            self.context = self.browser.new_context()

        return self.context

    def get_context(self) -> BrowserContext:
        """Returns the active browser context, initializing if necessary."""
        if not self.context or not self.browser or not self.browser.is_connected():
            return self.start()
        return self.context

    def new_page(self) -> Page:
        """Returns an active page by reusing open tabs or creating a new focused page."""
        context = self.get_context()
        if context.pages:
            page = context.pages[0]
            try:
                if not page.is_closed():
                    page.bring_to_front()
                    return page
            except Exception:
                pass
        page = context.new_page()
        page.bring_to_front()
        return page

    def new_transient_page(self) -> Page:
        """Opens a dedicated transient page and brings it to front."""
        context = self.get_context()
        page = context.new_page()
        page.bring_to_front()
        return page

    def close_page(self, page: Optional[Page]) -> None:
        """Safely closes a page if it is open and connected."""
        if page is not None:
            try:
                if not page.is_closed():
                    page.close()
            except Exception:
                pass

    def close_orphaned_blank_pages(self) -> None:
        """Safely closes empty about:blank tabs without closing the user's primary window."""
        try:
            context = self.get_context()
            pages = list(context.pages)
            if len(pages) > 1:
                for p in pages:
                    try:
                        if not p.is_closed() and p.url == "about:blank":
                            p.close()
                    except Exception:
                        pass
        except Exception:
            pass

    def close(self):
        """Closes Playwright connection cleanly without terminating user's Chrome instance."""
        try:
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
                self.browser = None
                self.context = None
        except Exception:
            pass


def get_browser_context(cdp_url: str = "http://127.0.0.1:9222") -> BrowserContext:
    """Functional helper for legacy cross-script invocations."""
    manager = BrowserManager(cdp_url=cdp_url)
    return manager.get_context()