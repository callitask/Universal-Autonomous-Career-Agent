# CompanySiteApply: Enterprise ATS Form Filling Subsystem

> **Document Version:** 3.1 — Hard Advance Gates, Dispatcher Cascade, Pre-Submit Order Gate, JET Radio Coverage & Zero-Hardcoding Architecture
> **Last Updated:** 2026-10-13  
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
├── ipc/                            # IPC Message Bus (AG Brain ↔ Section Scripts)
│   ├── ipc_manager.py              # write_questions(), write_answers(), wait_for_answers(), mark_done(), reset()
│   ├── section_question.json       # Active IPC handshake file (NOT committed to git)
│   └── ipc_error.log               # IPC timeout & error log
│
├── section_agents/                 # Top-Level Section Coordinators
│   ├── base_section_agent.py       # BaseSectionAgent abstract contract
│   ├── section_agent_dispatcher.py # evaluate_and_heal_section & Sub-Agent Registry
│   ├── profile_section_agent.py    # Section 1 Coordinator (Personal Info + Preferred Location)
│   ├── questionnaire_section_agent.py # Section 2 Coordinator (Pills + Dropdowns + Yes/No + Conditional)
│   ├── education_section_agent.py  # Section 3 Education Modal Coordinator
│   ├── experience_section_agent.py # Section 3 Experience Reordering Coordinator
│   ├── review_section_agent.py     # Section 4 Review, Documents & Diversity Coordinator
│   │
│   ├── scripts/                    # Independent Subsection Actuator Scripts (IPC-aware)
│   │   ├── s2_binary_questions.py      # Discover → IPC write → wait ANSWERED → fill DOM
│   │   ├── s2_competency_questions.py  # Radio pill competency questions via IPC
│   │   ├── s2_dropdown_questions.py    # Dropdown/combobox questions via IPC
│   │   ├── s2_conditional_questions.py # Re-scan for newly visible questions after first pass
│   │   ├── s3_experience_tile.py       # Single experience tile edit/verify (--tile-index N)
│   │   ├── s3_education_tile.py        # Education tile edit/verify
│   │   ├── s3_experience_ordering.py   # DOM text date parse + tile re-insertion sort
│   │   ├── s4_resume_upload.py         # Independent resume upload (check → upload if missing)
│   │   └── s4_cover_letter_upload.py   # Independent cover letter (stale → remove → upload)
│   │
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
├── tests/                          # Automated regression test suite (122 tests)
│   ├── test_autonomous_job_agent.py# Lifecycle & matching test suite
│   ├── test_ai_brain_resolver.py   # Screening Q&A dynamic deduction tests
│   ├── test_sub_agents.py          # Granular sub-agent audit & heal tests
│   ├── test_section_agents.py      # Section coordinator integration tests
│   ├── test_parser_doctor.py       # Line wrap & education healing tests
│   ├── test_ipc_and_modular_scripts.py # IPC lifecycle + discrete script tests
│   ├── test_section_detection.py   # URL routing, gates, tripwires, cascade tests
│   ├── test_experience_matcher.py  # resume.md parsing + employer matching tests
│   ├── test_search_entry.py        # Site-root entry + 404-guard tests
│   ├── test_dom_helpers.py         # Shared DOM helper tests
│   └── test_anatomy.py             # Portal anatomy model tests
│
├── anatomy/                          # Portal anatomy models (base, oracle_cloud, surgical_auditor)
├── fingers/                          # Platform adapters: base/generic/oracle_cloud/workday/greenhouse (+ registry)
├── nails/                            # Company overrides: base_nail + oracle/{jpmc_nail, bristlecone_nail}
│
└── utils/                          # Common DOM and security utilities
    ├── config_resolver.py          # Dynamic search roots & candidate resolution
    ├── dom_helpers.py              # Framework-native JavaScript event dispatchers
    ├── honeypot_guard.py           # Anti-bot honeypot detection
    └── experience_matcher.py       # resume.md parsing + fuzzy employer matching
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

> [!NOTE]
> **Fixed (Phase 2, verified):** `s3_experience_ordering.py` parses visible tile text to numeric keys (`YYYY*100+MM`, `Present` = 99999999) across the Knockout VM and raw DOM, then verifies descending order (`order_verified`). `jpmc_nail.py` and `experience_section_agent.py` delegate to it. Never compare `MM/YYYY` strings. See `docs/SECTION_IPC_ARCHITECTURE.md §4.1`.

### E. Section IPC Architecture (AG Brain-Gated Question Protocol)

> **Full Spec:** `docs/SECTION_IPC_ARCHITECTURE.md`

Instead of scripts calling `AIBrainResolver.resolve_question()` inline during DOM interaction, the redesigned pipeline uses an IPC file handshake:

1. **Script discovers** form questions → writes to `CompanySiteApply/ipc/section_question.json` with `status = ANSWER_REQUIRED`.
2. **AG Brain reads** IPC, matches each question against the loaded candidate profile/resume/config, populates `questions[].answer`, sets `status = ANSWERED`.
3. **Script reads** the answers from IPC, fills DOM fields, verifies read-back, reports result.
4. **Orchestrator** polls IPC status, advances only when all subsections verify clean.

Two execution modes (verified 2026-10-12):
- **Sync fast-path (default, single process):** `heal_*` writes questions, calls `AIBrainResolver.resolve_question()` in-process, then `write_answers()` + DOM actuation. The IPC file is the audit trail.
- **Async brain switch (external brain process):** script writes `ANSWER_REQUIRED` and blocks on `wait_for_answers()`; the external brain drives `AIBrainResolver.answer_ipc_file()` (reads via `from_file()`, resolves, writes `ANSWERED`). Use when the brain runs in a separate process.
- **Session correlation:** `ApplyOrchestrator.run()` generates one `session_id` and injects it into `candidate_data["_ipc_session_id"]`; every script resolves it via `get_effective_session_id()` instead of isolated `sess_*` placeholders.

This ensures:
- All semantic decisions are made by AG Brain with full profile context (not mid-DOM-fill).
- Each subsection is independently re-runnable without re-running the full section.
- Conditional questions (dynamically revealed after earlier answers) are caught by a 4-pass rescan.

### F. Conditional Question Handling

Section 2 questions on Oracle HCM can be conditional — answering a binary Yes/No pill reveals a new question group (e.g. "Please select your relevant years of work experience"). A missed conditional stays missed unless re-scanned. The fix is a **4-pass conditional rescan loop** that runs after all primary questions are answered.

### G. Terms & Conditions Modal Trap

Oracle HCM shows a full-page Terms & Conditions agreement (`#applyFlowLegalDisclaimer`) that overlays the entire form on first load. The orchestrator must detect and dismiss this modal BEFORE calling any section mini-agent. Fix in Phase 1 of `docs/SECTION_IPC_ARCHITECTURE.md §4.2`.

### H. Document Upload Independence (Section 4)

Resume and cover letter uploads are now fully independent:
- `s4_cover_letter_upload.py` — checks if cover letter is stale (not uploaded this session for this job) → REMOVE first → upload fresh PDF.
- `s4_resume_upload.py` — checks if resume is present → if missing → upload tailored resume PDF.
- Each script is callable independently. Stale cover but present resume → ONLY cover letter re-uploaded.

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
