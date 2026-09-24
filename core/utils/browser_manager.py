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
# Term: [CDP_TAB_REUSE]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Launching new browser instances caused login session drops and duplicate window bloat.
# Changes Made: Built Playwright CDP browser manager attaching to active Chrome debug port (http://127.0.0.1:9222), reusing existing pages, and activating them via .bring_to_front().
# Rationale: Preserves logged-in portal cookies and reduces memory consumption.
# Preventative Notes: Never close the primary browser window; only close temporary worker tabs.
#
# [ENTRY #002]
# Term: [CODEBASE_PURITY_ENFORCEMENT]
# Timestamp: 2026-09-15 16:03:27 +05:30
# Issue / Context: Hardcoded 9222 CDP port fallback violated Rule 5.
# Changes Made: Removed default port args and rely on os.environ.
# Rationale: Ensure dynamic configuration.
# Preventative Notes: Never hardcode these values again.
#
# [ENTRY #003]
# Term: [MISSING_OS_IMPORT_FIX]
# Timestamp: 2026-09-23 12:03:00 +05:30
# Issue / Context: `os` module was used at line 54 (os.environ.get("CDP_URL")) but was never
#   imported, causing a NameError on every BrowserManager construction where cdp_url is omitted.
# Changes Made: Added `import os` to the import block.
# Rationale: NameError is a hard crash; the import is mandatory for env-based CDP URL resolution.
# Preventative Notes: Always verify all used stdlib modules appear in the import section.
#
# [ENTRY #004]
# Term: [CONTEXT_MANAGER_TEARDOWN]
# Timestamp: 2026-09-23 14:30:00 +05:30
# Issue / Context: sync_playwright().start() with no guaranteed teardown left
#   zombie drivers across daemon cycles.
# Changes Made: Added __enter__/__exit__ so `with BrowserManager() as ctx:` always
#   stops Playwright. close() remains backward compatible.
# Rationale: Deterministic cleanup without changing existing call sites.
# Preventative Notes: Prefer `with` blocks for new code; never terminate user Chrome.
# ================================================================================
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

import os
import time
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """
    Manages Playwright connection to an active Chrome instance via CDP.
    """

    def __init__(self, cdp_url: str = None):
        self.cdp_url = cdp_url or os.environ.get("CDP_URL")
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
                    f"Ensure Chrome is initialized with the correct remote-debugging-port. Error: {e}"
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
        """Creates and returns a fresh, dedicated browser page in the CDP context."""
        context = self.get_context()
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

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def get_browser_context(cdp_url: str = None) -> BrowserContext:
    """Functional helper for legacy cross-script invocations."""
    manager = BrowserManager(cdp_url=cdp_url)
    return manager.get_context()