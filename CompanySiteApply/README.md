# CompanySiteApply: Enterprise ATS Form Filling Subsystem

A decoupled, modular multi-fingered automation subsystem for applying directly to company career sites and enterprise Applicant Tracking Systems (ATSs).

---

## 1. Directory Structure

```
CompanySiteApply/
├── README.md                       # This overview document
├── SCOPE_OF_EDIT.md                # 100-Day extensibility guide & engineering rules
├── ats_arm.py                      # Master orchestrator & CDP bridge
├── ats_detector.py                 # Platform fingerprinting & honeypot detector
├── cli.py                          # Interactive CLI for inspection & manual form filling
│
├── fingers/                        # Pluggable ATS platform adapters ("The Fingers")
│   ├── __init__.py                 # Dynamic finger registry & factory
│   ├── base_finger.py              # BaseATSFinger abstract interface
│   ├── oracle_cloud_finger.py      # Oracle Cloud HCM (Candidate Experience) & Taleo
│   ├── workday_finger.py           # Workday multi-step wizard & review editor
│   ├── greenhouse_finger.py        # Greenhouse application board handler
│   └── generic_finger.py           # Adaptive fallback for custom company portals
│
├── parser_doctor/                  # ATS Resume Parser healing engine
│   ├── __init__.py
│   ├── line_wrap_healer.py         # Heals broken margin line wraps in experience text
│   ├── education_healer.py         # Fixes swapped degree vs. college mappings
│   └── review_verifier.py          # Coordinates DOM-level audit & healing
│
├── inspections/                    # Captured empirical reverse-engineered DOM schemas
│   └── oracle_cloud_hcm/           # Saved Oracle Cloud step schemas
│
├── tests/                          # Automated regression test suite
│   └── test_parser_doctor.py       # Unit tests for line wrap & education healing
│
└── utils/
    ├── dom_helpers.py              # Native framework event dispatchers (JET, React)
    └── honeypot_guard.py           # Anti-bot honeypot detector
```

---

## 2. CLI Quick Reference

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

## 3. Integration with Core Pipeline

- `core/04_job_discovery.py` saves external company job listings to `profiles/<profile>/output/saved_external_jobs.json`.
- When the user reviews saved jobs and requests assistance with an enterprise application, `CompanySiteApply` executes on demand.
- `CompanySiteApply` is **completely decoupled** from `core/` and never runs as an unprompted background loop.
