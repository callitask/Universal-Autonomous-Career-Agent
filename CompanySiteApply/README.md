# CompanySiteApply: Enterprise ATS Form Filling Subsystem

> **Document Version:** 3.0 — Cognitive Sub-Agent Dispatch, Autonomous Career Agent Lifecycle, Stale Document Healing & Zero-Hardcoding Architecture  
> **Last Updated:** 2026-10-11  
> **Execution Mode:** Autonomous Full Lifecycle & On-Demand Human-Gated (Decoupled from background daemons)

A decoupled, modular automation subsystem for applying directly to company career sites and enterprise Applicant Tracking Systems (ATSs) like Oracle Cloud HCM, Workday, and Greenhouse.

---

## 1. Directory Structure

```
CompanySiteApply/
├── README.md                       # Subsystem overview and architectural contracts
├── SCOPE_OF_EDIT.md                # 100-Day extensibility guide & engineering rules
├── autonomous_job_agent.py         # Master 6-Stage Autonomous Career Lifecycle Controller
├── cognitive_job_matcher.py        # 100% Dynamic, profile-grounded job scoring engine
├── apply_orchestrator.py           # Cognitive Section Dispatch Coordinator
├── ai_brain_resolver.py            # Antigravity 2.0 Brain for screening questions & knowledge index
├── ats_arm.py                      # CDP connection bridge & legacy inspection arm
├── ats_detector.py                 # Platform fingerprinting & honeypot detector
├── cli.py                          # Interactive CLI for inspection & manual form filling
│
├── section_agents/                 # Top-Level Section Coordinators
│   ├── base_section_agent.py       # BaseSectionAgent abstract contract
│   ├── section_agent_dispatcher.py # evaluate_and_heal_section & Sub-Agent Registry
│   ├── profile_section_agent.py    # Section 1 Coordinator (Personal Info + Preferred Location)
│   ├── questionnaire_section_agent.py # Section 2 Coordinator (Pills + Dropdowns + Yes/No)
│   ├── education_section_agent.py  # Section 3 Education Modal Coordinator
│   ├── experience_section_agent.py # Section 3 Experience Reordering Coordinator
│   ├── review_section_agent.py     # Section 4 Review, Documents & Diversity Coordinator
│   └── sub_agents/                 # Granular Sub-Agents (Single Responsibility)
│       ├── personal_details_subagent.py     # Section 1 Personal Info
│       ├── preferred_location_subagent.py   # Section 1 Facility / Preferred Location
│       ├── technical_competency_subagent.py # Section 2 Competency Radio Pills
│       ├── dropdown_question_subagent.py    # Section 2 Multi-select Dropdowns
│       ├── binary_question_subagent.py      # Section 2 Regulatory Yes/No Pills
│       ├── education_subagent.py            # Section 3 Education Form & Autocomplete
│       ├── experience_subagent.py           # Section 3 Experience Ordering & Bullets
│       ├── documents_subagent.py            # Section 4 Document Upload & Stale Healing
│       ├── diversity_subagent.py            # Section 4 Diversity Demographics
│       ├── signature_subagent.py            # Section 4 E-Signature & Agreement
│       └── visual_verifier_subagent.py      # Full-page screenshot & error audit
│
├── CompanyScraper/                 # Direct corporate career site scrapers
│   ├── base_scraper.py             # BaseCompanyScraper contract & ranking logic
│   └── companies/                  # Company-specific scrapers
│       └── jpmorgan/               # JPMorgan Chase Oracle HCM portal scraper
│           ├── config.json         # Portal endpoint and selector configurations
│           └── jpmorgan_scraper.py # Scraper implementation
│
├── parser_doctor/                  # ATS Resume Parser healing engine
│   ├── line_wrap_healer.py         # Heals fragmented margin line wraps in text
│   ├── education_healer.py         # Fixes swapped degree vs. college mappings
│   └── review_verifier.py          # Coordinates DOM-level pre-submit verification
│
├── tests/                          # Automated regression test suite (66 tests)
│   ├── test_autonomous_job_agent.py# Lifecycle & matching test suite
│   ├── test_ai_brain_resolver.py   # Screening Q&A dynamic deduction tests
│   ├── test_sub_agents.py          # Granular sub-agent audit & heal tests
│   ├── test_section_agents.py      # Section coordinator integration tests
│   └── test_parser_doctor.py       # Line wrap & education healing tests
│
└── utils/                          # Common DOM and security utilities
    ├── config_resolver.py          # Dynamic search roots & candidate resolution
    ├── dom_helpers.py              # Framework-native JavaScript event dispatchers
    └── honeypot_guard.py           # Anti-bot honeypot detection
```

---

## 2. Key Architecture Concepts

### A. The 6-Stage Autonomous Lifecycle (`AutonomousJobAgent`)
1. **Stage 1: Comprehend Profile**: Dynamically ingests `candidate_config.json`, master `resume.md`, and skills taxonomy with **zero hardcoding** across Tech, Finance, HR, Sales, and Operations.
2. **Stage 2: Portal Search**: Autonomously executes career site searches using candidate's target keywords and preferred locations via `JPMorganScraper`. Prunes roles already applied via DOM tile check or `processed_ledger.json`.
3. **Stage 3: Cognitive Match Evaluation**: Scores candidate jobs using `CognitiveJobMatcher` (0–100 factual fit based on candidate skills, seniority alignment, and location).
4. **Stage 4: Document Tailoring**: Generates bespoke, role-specific cover letter PDFs referencing the exact `job_id`, `job_title`, and company.
5. **Stage 5: Form Application**: Dispatches section mini-agents to complete Sections 1, 2, 3, and 4 in strict chronological order with non-destructive pre-audits and surgical micro-heals.
6. **Stage 6: Visual Audit & Human Gate**: Captures full-page verification screenshot proof, records entry in `processed_ledger.json`, and **strictly halts before clicking Submit**.

### B. Cognitive Section Dispatch & Micro-Healing
Instead of generating one-off scripts when an error occurs:
- The coordinator calls `evaluate_and_heal_section(section_name, page, candidate_data)`.
- It executes a **Pre-Audit** across all sub-agents of that section.
- Compliant sub-agents are **bypassed entirely** (zero redundant clicks or resets).
- Only failing sub-agents execute their isolated `heal()` routine.
- A **Post-Audit** confirms resolution before advancing to the next section.

### C. Pre-Uploaded Stale Document Detection & Healing
Oracle Cloud HCM persists draft attachments across sessions. If a user previously applied to a different role (e.g. *Principal Software Engineer*), the draft retains that stale file.
- `DocumentsSubAgent` evaluates session freshness (`_fresh_cover_uploaded`).
- If an attachment exists on the page but was not uploaded in the active session for the active job context, the audit flags:
  ```json
  {"is_valid": false, "is_preuploaded_cover": true, "cover_status": "PRE_UPLOADED_STALE"}
  ```
- Healing clicks `REMOVE COVER LETTER`, waits for `.attachment-upload-button--waiting`, uploads the freshly tailored document, and verifies `.attachment-upload-button--filled` with `"Your cover letter was changed."`.

### D. Reverse-Chronological Experience Ordering
Oracle HCM resume parser frequently shuffles work experience tiles out of order. `ExperienceSubAgent` and `JPMCNail` dynamically parse date spans from tiles and enforce strict reverse-chronological ordering (most recent role at the top).

---

## 3. Strict Human Submission Gate (Invariant)

> [!CAUTION]
> **NEVER CLICK SUBMIT ON SECTION 4.**  
> The agent is strictly prohibited from clicking the final `SUBMIT` button. The application must halt on Section 4 Review with all checkmarks green and the Submit button enabled, presenting the user with screenshot verification proof to finalize the submission manually.

---

## 4. Execution Commands

### Autonomous Full Lifecycle (Search -> Match -> Tailor -> Apply -> Gate):
```powershell
.venv\Scripts\python run_universal_apply.py --autonomous --profile <profile_name>
```

### Search & Rank Requisitions Only:
```powershell
.venv\Scripts\python search_and_evaluate_jpmc_jobs.py --profile <profile_name>
```

### Active Tab Apply Mode (For Already Open Forms):
```powershell
.venv\Scripts\python run_universal_apply.py --profile <profile_name>
```

### Run Test Suite:
```powershell
.venv\Scripts\python -m unittest discover -s CompanySiteApply/tests
```
