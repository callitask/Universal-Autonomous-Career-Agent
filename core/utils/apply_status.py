# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-23 14:00:00 +05:30
# Issue / Context: APPLIED_* strings scattered across 04/05/tracker with no
#   single verification rule; premature APPLIED_CHATBOT violated C1/C3.
# Changes Made: Created apply_status.py with canonical constants + helpers.
# Rationale: One importable contract; success requires explicit DOM evidence.
# Preventative Notes: Never return APPLIED_* without is_verified_success().
#   Keep this file free of Playwright imports (pure logic only).
# ================================================================================
"""Canonical application statuses + verification helpers. Pure logic, no I/O."""
from __future__ import annotations

APPLIED_1CLICK = "APPLIED_1CLICK"
APPLIED_CHATBOT = "APPLIED_CHATBOT"
APPLIED_EASYAPPLY = "APPLIED_LINKEDIN_EASY_APPLY"
VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
SUBMITTED_SUCCESSFULLY = "SUBMITTED_SUCCESSFULLY"
FAILED = "FAILED"
DRAWER_CLOSED = "DRAWER_CLOSED"
REQUIRES_MANUAL = "REQUIRES_MANUAL_INTERVENTION"
FAILED_PLATFORM = "FAILED_PLATFORM_REJECTED"

VERIFIED_SET = frozenset({APPLIED_1CLICK, APPLIED_CHATBOT, APPLIED_EASYAPPLY, VERIFIED_SUCCESS, SUBMITTED_SUCCESSFULLY})


def is_verified_success(status: str) -> bool:
    return str(status or "") in VERIFIED_SET


def needs_verification(status: str) -> bool:
    """True when caller claims success but has not shown DOM evidence yet."""
    return str(status or "").startswith("APPLIED") and not is_verified_success(status)
