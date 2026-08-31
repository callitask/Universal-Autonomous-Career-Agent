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
            page.bring_to_front()
            return page
        page = context.new_page()
        page.bring_to_front()
        return page

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