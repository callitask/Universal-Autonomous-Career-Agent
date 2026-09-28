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
#
# [ENTRY #002]
# Term: [THROTTLED_SUBMIT_STATUS]
# Timestamp: 2026-09-27 20:35:00 +05:30
# Issue / Context: LinkedIn Easy Apply Submit clicks swallowed under portal
#   soft-throttle (no success text, no error, buttons gone) were booked as
#   generic FAILED, indistinguishable from form failures in the tracker.
# Changes Made: FAILED_SUBMIT_THROTTLED canonical failure status (kept OUT of
#   VERIFIED_SET — it is a failure, never a success).
# Rationale: Throttle evidence stays countable/auditable; scoped ledger resets
#   can re-queue these entries without touching genuine form failures.
# Preventative Notes: Never add a FAILED_* variant to VERIFIED_SET.
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
FAILED_SUBMIT_THROTTLED = "FAILED_SUBMIT_THROTTLED"

VERIFIED_SET = frozenset({APPLIED_1CLICK, APPLIED_CHATBOT, APPLIED_EASYAPPLY, VERIFIED_SUCCESS, SUBMITTED_SUCCESSFULLY})


def is_verified_success(status: str) -> bool:
    return str(status or "") in VERIFIED_SET


def needs_verification(status: str) -> bool:
    """True when caller claims success but has not shown DOM evidence yet."""
    return str(status or "").startswith("APPLIED") and not is_verified_success(status)
