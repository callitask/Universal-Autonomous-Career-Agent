# CompanySiteApply Inspections Catalog (Tier C: Captured Samples)

> **CLASSIFICATION:** TIER C — CAPTURED LIVE DOM SAMPLES (DO NOT COPY / DO NOT RUN AS CANDIDATE DEFAULTS)  
> **PURPOSE:** Reference schemas for reverse-engineering dynamic ATS step forms and selector structures.  
> **STATUS:** Non-executable empirical dumps.

This directory contains empirical DOM structure snapshots captured by `CompanySiteApply/cli.py inspect` and `ats_arm.py`.

## Directory Contents

### `generic_adaptive/`
*   `adaptive_form_step_20260917_104832.json` — Captured schema snapshot for generic adaptive form detector.
*   `adaptive_form_step_20260917_104847.json` — Captured schema snapshot for generic adaptive form detector.

### `oracle_cloud_hcm/`
*   `authentication_email_20260915_224532.json` — Oracle Cloud HCM email verification step DOM schema.
*   `authentication_email_20260915_234000.json` — Oracle Cloud HCM email verification step DOM schema.
*   `authentication_email_20260917_104943.json` — Oracle Cloud HCM email verification step DOM schema.
*   `authentication_email_20260917_104958.json` — Oracle Cloud HCM email verification step DOM schema.
*   `unknown_20260915_234134.json` — Oracle Cloud HCM personal details & profile import tile schema.
*   `unknown_20260915_234732.json` — Oracle Cloud HCM experience/education section form schema.
*   `unknown_20260917_105041.json` — Oracle Cloud HCM complete multi-step wizard inspection dump.
*   `unknown_20260917_105350.json` — Oracle Cloud HCM complete multi-step wizard inspection dump.
*   `unknown_20260917_110906.json` — Oracle Cloud HCM review and submit step inspection dump.

## Governance & Hygiene Rules
1. **Never copy values:** Never use names, numbers, or placeholder text from these JSON files as runtime code defaults.
2. **Read-only reference:** Used solely to design locators and test DOM selector resilience against portal redesigns.
