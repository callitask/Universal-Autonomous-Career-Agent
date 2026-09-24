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
# Term: [ABSTRACT_INTERFACE]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Consistent contract required across disparate job portal scrapers.
# Changes Made: Created abstract base class BaseScraper defining search_jobs() and extract_job_details().
# Rationale: Polymorphic scraper invocation in 04_job_discovery.py.
# Preventative Notes: Never implement portal-specific logic in base_scraper.py.
#
# [ENTRY #002]
# Term: [CTX_LOGGER_MISSING_ATTRIBUTE_FIX]
# Timestamp: 2026-09-23 12:05:00 +05:30
# Issue / Context: JobBoardScraper.__init__ set self.logger = ctx.logger but ProfileContext
#   has no .logger attribute, causing AttributeError on every scraper instantiation.
#   The entire scrapers package was therefore dead code.
# Changes Made: Added `import logging`, created module-level _DEFAULT_LOGGER, and replaced
#   `ctx.logger` with `getattr(ctx, "logger", _DEFAULT_LOGGER)` to degrade gracefully.
# Rationale: Scrapers must be importable and functional without requiring ProfileContext changes.
#   The getattr guard future-proofs against ProfileContext gaining a .logger property later.
# Preventative Notes: Never assume ProfileContext attributes exist without checking the class
#   definition. Use getattr guards for optional interface attributes.
# ================================================================================
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
import time
import random

_DEFAULT_LOGGER = logging.getLogger("career_agent.scrapers")

class JobBoardScraper(ABC):
    def __init__(self, ctx, page, browser):
        self.ctx = ctx
        self.page = page
        self.browser = browser
        # ctx.logger does not exist on ProfileContext — use stdlib logger as safe default.
        self.logger = getattr(ctx, "logger", _DEFAULT_LOGGER)

    def random_sleep(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(random.uniform(min_s, max_s))

    @abstractmethod
    def scrape_jobs(self) -> List[Dict[str, Any]]:
        pass