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
# Term: [PACKAGE_INITIALIZATION]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Standardized package exports needed for portal scrapers.
# Changes Made: Exported BaseScraper, NaukriScraper, LinkedInScraper.
# Rationale: Clean modular imports across discovery pipeline.
# Preventative Notes: Keep scraper implementations isolated in their respective files.
# ================================================================================
