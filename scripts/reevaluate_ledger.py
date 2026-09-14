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
# Term: [LEDGER_MAINTENANCE]
# Timestamp: 2026-09-12 14:00:00 +05:30
# Issue / Context: Deduplication ledger accumulated thousands of rejected/gated entries, starving subsequent discovery runs.
# Changes Made: Built utility to purge low_score, domain_gated, and failed_apply keys while strictly preserving successfully APPLIED jobs and negative company exclusions.
# Rationale: Allows candidate profile updates to re-evaluate previously skipped opportunities safely.
# Preventative Notes: Never delete entries marked as APPLIED in applications_tracker.csv.
#
# [ENTRY #002]
# Term: [BOM_STRIP_AND_DECOUPLING]
# Timestamp: 2026-09-13 16:10:00 +05:30
# Issue / Context: UTF-8 BOM on line 1 caused AST parsing errors; docstring contained hardcoded company names.
# Changes Made: Stripped BOM character; generalized docstring to reference candidate_config.json.
# Rationale: Syntax stability and compliance with Directive 2.
# Preventative Notes: Never save Python files with UTF-8 BOM encoding.
# ================================================================================
"""
scripts/reevaluate_ledger.py
Universal Ledger Maintenance Utility
Safely clears 'low_score', 'domain_gated', and 'failed_apply' entries from processed_ledger.json
so the continuous career agent can re-evaluate them against updated candidate resumes.
Strictly preserves:
- All successfully APPLIED jobs in applications_tracker.csv
- Negative company exclusions configured in candidate_config.json
- Fully profile-agnostic and non-destructive.
"""

import os
import sys
import json
import csv
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.utils.profile_context import ProfileContext, canonical_job_url, extract_platform_job_id


def clean_ledger_for_reevaluation(profile_path: str, dry_run: bool = False):
    profile_dir = Path(profile_path).resolve()
    ctx = ProfileContext(profile_dir, BASE_DIR)
    
    tracker_file = profile_dir / "output" / "applications_tracker.csv"
    applied_urls = set()
    if tracker_file.exists():
        with open(tracker_file, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "APPLIED" in row.get("Status", "").upper():
                    u = row.get("Job URL", "").strip().lower()
                    if u:
                        applied_urls.add(u)
                        can_u = canonical_job_url(u)
                        if can_u:
                            applied_urls.add(can_u)
                        jid = extract_platform_job_id(u)
                        if jid:
                            applied_urls.add(jid)

    ledger_file = profile_dir / "output" / "processed_ledger.json"
    if not ledger_file.exists():
        print(f"No processed_ledger.json found at {ledger_file}")
        return

    data = json.loads(ledger_file.read_text(encoding="utf-8"))
    print(f"Current total ledger keys: {len(data)}")
    print(f"Protected APPLIED keys: {len(applied_urls)}")

    negative_companies = [c.lower() for c in ctx.config.get("target_jobs", {}).get("negative_companies", [])]
    
    retained_ledger = {}
    removed_count = 0
    statuses_removed = {}

    for k, v in data.items():
        if not isinstance(v, dict):
            retained_ledger[k] = v
            continue

        status = v.get("status", "")
        company = str(v.get("company", "")).lower()

        # Always retain if applied or negative company
        is_negative = any(neg in company for neg in negative_companies if neg)
        is_applied = (k.lower() in applied_urls) or (status in ["applied", "composite_applied", "already_applied", "composite_already_applied"])

        if is_applied or is_negative or "negative" in status:
            retained_ledger[k] = v
            continue

        # Ungate candidates for re-evaluation: low_score, domain_gated, failed_apply, composite_gated
        if status in ["low_score", "domain_gated", "failed_apply", "composite_gated", "no_native_apply", "no_description"]:
            removed_count += 1
            statuses_removed[status] = statuses_removed.get(status, 0) + 1
            continue

        retained_ledger[k] = v

    print(f"\nRemoved {removed_count} unapplied/gated keys for re-evaluation:")
    for st, count in statuses_removed.items():
        print(f"  - {st}: {count}")

    print(f"Retained ledger keys: {len(retained_ledger)}")

    if not dry_run:
        tmp_file = ledger_file.with_name(ledger_file.name + ".tmp")
        tmp_file.write_text(json.dumps(retained_ledger, indent=2), encoding="utf-8")
        os.replace(tmp_file, ledger_file)
        print(f"\nSuccessfully updated {ledger_file}!")
    else:
        print("\nDry run completed. No files modified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean ledger for re-evaluation")
    parser.add_argument("--profile", required=True, help="Candidate profile path")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run")
    args = parser.parse_args()
    clean_ledger_for_reevaluation(args.profile, args.dry_run)
