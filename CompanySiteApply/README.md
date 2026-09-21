# CompanySiteApply: Enterprise ATS Form Filling Subsystem

> **Document Version:** 2.0 — Modular Fingers & Nails Architecture, CompanyScraper Integration & Parser Doctor Contracts  
> **Last Updated:** 2026-09-21  
> **Execution Mode:** On-Demand / Human-Gated only (Decoupled from background daemons)

A decoupled, modular multi-fingered automation subsystem for applying directly to company career sites and enterprise Applicant Tracking Systems (ATSs).

---

## 1. Directory Structure

```
CompanySiteApply/
├── README.md                       # This overview document and architecture contracts
├── SCOPE_OF_EDIT.md                # 100-Day extensibility guide & engineering rules
├── ats_arm.py                      # Master orchestrator & CDP bridge
├── ats_detector.py                 # Platform fingerprinting & honeypot detector
├── cli.py                          # Interactive CLI for inspection & manual form filling
│
├── fingers/                        # Pluggable ATS platform adapters ("The Fingers")
│   ├── __init__.py                 # Dynamic finger registry & get_finger_for_page factory
│   ├── base_finger.py              # BaseATSFinger abstract interface
│   ├── oracle_cloud_finger.py      # Oracle Cloud HCM (Candidate Experience) & Taleo
│   ├── workday_finger.py           # Workday multi-step wizard & review editor
│   ├── greenhouse_finger.py        # Greenhouse application board handler
│   └── generic_finger.py           # Adaptive fallback for custom company portals
│
├── nails/                          # Company-specific customizations ("The Nails")
│   ├── __init__.py                 # Nail exports
│   ├── base_nail.py                # BaseNail abstract interface
│   └── oracle/                     # Oracle HCM company-specific nails
│       ├── __init__.py
│       ├── jpmc_nail.py            # JPMorgan Chase custom field overrides
│       └── bristlecone_nail.py     # Bristlecone custom field overrides
│
├── CompanyScraper/                 # Direct company career site scrapers
│   ├── __init__.py
│   ├── base_scraper.py             # BaseCompanyScraper contract & ranking logic
│   ├── cli_scraper.py              # Scraper CLI runner & job export coordinator
│   └── companies/                  # Company-specific scrapers
│       ├── __init__.py
│       └── jpmorgan/               # JPMorgan Chase portal scraper implementation
│           ├── __init__.py
│           ├── config.json         # Portal endpoint and selector configurations
│           └── jpmorgan_scraper.py # Scraper implementation
│
├── parser_doctor/                  # ATS Resume Parser healing engine
│   ├── __init__.py
│   ├── line_wrap_healer.py         # Heals broken margin line wraps in experience text
│   ├── education_healer.py         # Fixes swapped degree vs. college mappings
│   └── review_verifier.py          # Coordinates DOM-level audit & healing
│
├── inspections/                    # Captured empirical reverse-engineered DOM schemas (Tier C)
│   ├── generic_adaptive/          # Adaptive form step snapshots
│   └── oracle_cloud_hcm/          # Saved Oracle Cloud step schemas
│
├── tests/                          # Automated regression test suite
│   └── test_parser_doctor.py       # Unit tests for line wrap & education healing
│
└── utils/                          # Common DOM and security utilities
    ├── __init__.py
    ├── dom_helpers.py              # Native framework event dispatchers (JET, React, native inputs)
    └── honeypot_guard.py           # Anti-bot honeypot and invisible trap detection
```

---

## 2. Architecture & Subsystem Contracts

### A. The Finger vs. Nail Split
*   **The Finger (`CompanySiteApply/fingers/`):** Implements broad, platform-level ATS mechanics (e.g., Oracle Cloud HCM, Workday, Greenhouse). Manages standard steps: resume upload, auto-parse wait, standard demographics, experience tile editing, verification PIN entry, and review submission.
*   **The Nail (`CompanySiteApply/nails/`):** Implements company-specific overrides and unique demographic/compliance fields for a specific employer on top of a base Finger.
    *   *Example:* `JPMCNail` handles Indian Uniformed Forces / Military Status (`#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-8`), specialized employment dropdowns, and compliance questionnaires specific to JPMorgan Chase on Oracle HCM.
    *   *Activation:* `OracleCloudFinger` queries `self.get_active_nail(page, page.url)` to dynamically delegate custom fields.

### B. CompanyScraper Subsystem
*   **Purpose:** Ingests external corporate job postings directly from primary corporate career sites (e.g., JPMorgan Careers) without relying on intermediate job boards.
*   **Ranking & Filtering:** `BaseCompanyScraper.score_job()` calculates title relevance, candidate skill overlap, and geographic suitability.
*   **Output Convention:** By design, inspected direct opportunities save to `APPLIED ON COMPANY WEBSITE/<Company>/<Role>/job_description.json` or `output/<Company>_scraped_jobs.json`.

### C. Parser Doctor
*   **Purpose:** Inspects and repairs common ATS resume parsing anomalies before form submission.
*   **`LineWrapHealer`:** Detects and reconciles fragmented bullet points caused by PDF margin wrapping.
*   **`EducationHealer`:** Solves swapped degree and institution fields in Oracle Cloud HCM modal dialogs.
*   **`ReviewVerifier`:** Executes comprehensive pre-submission verification to ensure zero red-validation errors.

### D. DOM Helpers & Honeypot Guards
*   **`DOMHelpers`:** Dispatches framework-native JavaScript events (React Synthetic Events, Oracle JET dispatchers) to guarantee input persistence.
*   **`HoneypotGuard`:** Scans page DOM for hidden, off-screen, or zero-opacity input fields (common anti-automation traps) to prevent accidental completion that would blacklist the session.

---

## 3. Data Classification & Codebase Hygiene

*   **Tier B Literals (Code Defaults):** Hardcoded demographic/location fallbacks in `oracle_cloud_finger.py` (e.g. `"560100"`, `"Bangalore"`, `"Asian"`, `"Male"`) and `jpmc_nail.py` are recognized Directive 2 violations slated for extraction to `candidate_config.json`. Because `ProfileContext.verify_codebase_purity()` scopes strictly to `core/` and `scripts/`, these are maintained with defensive fallbacks until config refactoring.
*   **Tier C Samples (`inspections/`):** All JSON files in `CompanySiteApply/inspections/` are historical DOM capture dumps for reverse-engineering. They are non-executable reference samples.

---

## 4. CLI Quick Reference

Ensure your target career page is open in Chrome running on remote debugging port 9222:

```powershell
# 1. Deeply inspect the active page and detect platform + honeypots
python CompanySiteApply/cli.py inspect

# 2. Quick detection of ATS engine & confidence score
python CompanySiteApply/cli.py detect

# 3. Run Parser Doctor to heal broken line wraps in experience text on the active tab
python CompanySiteApply/cli.py heal

# 4. Step-by-step fill the form (prompting for missing fields)
python CompanySiteApply/cli.py fill --email candidate@example.com
```

---

## 5. Integration with Core Pipeline

*   `core/04_job_discovery.py` saves external company job listings to `profiles/<profile>/output/saved_external_jobs.json`.
*   When the user reviews saved jobs and requests assistance with an enterprise application, `CompanySiteApply` executes on demand.
*   `CompanySiteApply` is **completely decoupled** from `core/` and never runs as an unprompted background loop.
