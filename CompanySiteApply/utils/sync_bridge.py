# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [SYNC_BRIDGE_INIT]
# Timestamp: 2026-10-13 18:00:00 +05:30
# Issue / Context: Sync Playwright calls (sync_playwright, orchestrator.run,
#                  cover-letter PDF render) crash inside --autonomous's event
#                  loop. The thread-offload idiom was copy-pasted at three call
#                  sites (incident: duplicated idiom drifts).
# Changes Made: Single call_sync_offloaded() bridge + unit tests.
# Rationale: One tested path for sync-in-async execution across the subsystem.
# Preventative Notes: Never inline get_running_loop/ThreadPoolExecutor again.
# ==============================================================================

"""Sync-in-async bridge for Playwright-bound calls."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


def call_sync_offloaded(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run sync fn now: worker thread if a loop runs, inline otherwise."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn(*args, **kwargs)
    with ThreadPoolExecutor(max_workers=1) as _ex:
        return _ex.submit(fn, *args, **kwargs).result()
