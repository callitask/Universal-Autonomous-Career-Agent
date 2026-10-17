# CompanySiteApply: Enterprise ATS Form Filling Subsystem

> **Document Version:** 3.3 — Hard Advance Gates, Dispatcher Cascade, Pre-Submit Order Gate, JET Radio Coverage, Structured Role Outputs, BASE.md Seeding & Stage 4 Deterministic Tailoring & Zero-Hardcoding Architecture
> **Last Updated:** 2026-10-17  
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
├── tests/                          # Automated regression test suite (193 tests, 20 files)
│   ├── test_anatomy.py             # Portal anatomy model tests
│   ├── test_ai_brain_resolver.py   # Screening Q&A dedup + answers.json mirror tests
│   ├── test_answer_integrity.py    # Answer-integrity contract tests
│   ├── test_application_docs.py    # Structured role-layout contract tests
│   ├── test_autonomous_job_agent.py# Lifecycle & matching test suite
│   ├── test_company_workspace.py   # BASE.md seeding/resolution + blueprint-placeholder guard
│   ├── test_decisions_1_and_4.py   # Decision-gate regression tests
│   ├── test_dom_helpers.py         # Shared DOM helper tests
│   ├── test_experience_matcher.py  # resume.md bullet priority + employer matching tests
│   ├── test_ipc_and_modular_scripts.py # IPC lifecycle + discrete script tests
│   ├── test_match_report.py        # Match-report regression tests
│   ├── test_parser_doctor.py       # Line wrap & education healing tests
│   ├── test_repo_structure.py      # Repo layout / blueprint-only-profiles guard
│   ├── test_runtime_paths.py       # Operations-root resolution tests
│   ├── test_search_entry.py        # Site-root entry + 404-guard tests
│   ├── test_section_agents.py      # Section coordinator integration tests
│   ├── test_section_detection.py   # URL routing, gates, tripwires, cascade tests
│   ├── test_sub_agents.py          # Granular sub-agent audit & heal tests
│   ├── test_sync_bridge.py         # Sync-bridge regression tests
│   └── test_task1_gaps.py          # Task-1 gap regression tests
│
├── anatomy/                          # Portal anatomy models (base, oracle_cloud, surgical_auditor)
├── fingers/                          # Platform adapters: base/generic/oracle_cloud/workday/greenhouse (+ registry)
├── nails/                            # Company overrides: base_nail + oracle/{jpmc_nail, bristlecone_nail}
│
└── utils/                          # Common DOM, workspace, and security utilities (10 modules)
    ├── application_docs.py         # Structured role-layout contract (fixed names, exact paths, resolve_company_name)
    ├── company_workspace.py        # Company workspace ensure + 3-tier BASE.md seeding/resolution
    ├── config_resolver.py          # Dynamic search roots & candidate resolution
    ├── dom_helpers.py              # Framework-native JavaScript event dispatchers
    ├── experience_matcher.py       # resume.md bullet priority + fuzzy employer matching
    ├── honeypot_guard.py           # Anti-bot honeypot detection
    ├── match_report.py             # Cognitive match report writer
    ├── question_hygiene.py         # Screening-question normalization & dedup helpers
    ├── runtime_paths.py            # Operations-root path resolution (profiles/ipc/output)
    └── sync_bridge.py              # Profile/ledger sync bridge
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

### I. Per-Company Workspaces (Company Agents, Current & Future)

Resume/cover resolution is company-first: `company_site_apply/<CompanySlug>/`
(e.g. `JPMorganChase`) is created on demand by
`CompanySiteApply/utils/company_workspace.py` (`ensure_company_workspace()`),
seeded from the master `resume.md` into `resumes/BASE.md`, and searched before
the flat directory (`resolve_company_roots()`). Slugs are alphanumeric
(`company_slug()` strips `&`, spaces, and `Co/Inc/Ltd` suffixes). Inputs live
here: root `README.md`-only plus `resumes/BASE.md` and
`cover_letters/BASE.md` — auto-provisioned at Stage 4 start for every profile
identically.

**4-step resolution + 3-tier non-overwriting seeding.** Seeding writes a tier
**only when the file is absent or still a placeholder blueprint**
(`_is_real_base_md()` rejects `[FIRSTNAME LASTNAME]`, `[FULL NAME]` and
`{{FULL_NAME}}`), so a hand-written `BASE.md` is never clobbered. Resolution
then walks 4 tiers, first hit wins:

| Resolver | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
| --- | --- | --- | --- | --- |
| `resolve_base_resume_md(profile_dir, company_name)` | `company_site_apply/<Slug>/resumes/BASE.md` | `company_site_apply/<legacy>/resumes/BASE.md` (each legacy space-separated dirname, `_legacy_company_dirnames()`) | `company_site_apply/resume.md` | `profile_dir/resume.md` |
| `resolve_base_cover_letter_md(profile_dir, company_name)` | `company_site_apply/<Slug>/cover_letters/BASE.md` | `company_site_apply/<legacy_dir>/cover_letters/BASE.md` | `company_site_apply/cover_letter.md` | `profile_dir/cover_letter_template.md` |

Both return `None` when every tier is missing or is a placeholder blueprint, and
both are re-exported from `CompanySiteApply/utils/application_docs.py`.

**Future company agents:** call `ensure_company_workspace(candidate_data,
company)` at run start — the workspace (plus `cover_letters/`, `resumes/`,
`README.md`) self-provisions; no layout rediscovery, no hardcoded paths.
`company_profiles.json` decides framing: `service` firms use the flat generic
base, product/tech/finance firms (and unlisted ones) use workspaces with
per-company cover tones. `cover_letters/BASE.md` (seeded once per workspace,
never overwritten) is the tone reference; generated per-requisition PDFs land
in the structured role folder (§J), never beside it with per-req suffixes.
Blueprint (`profiles/default_user/`) carries skeleton + README only, never PII.

### J. Structured Role Outputs — Fixed Names in `<Role>_<jobid>/` (2026-10-14)

Stage 4 (`autonomous_job_agent.stage_4_tailor_documents`) generates directly
into the role dir via `CompanySiteApply/utils/application_docs.py`, never the
flat `company_site_apply` root:

```
profiles/<slug>/APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/
├── <Stem>_Resume.pdf          # FIXED name (flat canonical)
├── <Stem>_Cover_Letter.pdf    # FIXED name (flat canonical)
├── resume/<Stem>_Resume.pdf           # mirrored copy
├── cover_letters/<Stem>_Cover_Letter.pdf  # mirrored copy
├── resume.md                   # BASE.md-driven tailored role resume (Stage 4)
├── answers.json                # screening_qa mirror for this role (Stage 5)
├── Cover_Letter.txt           # role-specific companions
└── Cover_Letter.md            # base-markdown prose source for the above
```

- **Stage 4 deterministic role-resume tailoring** (`core/generate_factual_tailored.py`):
  `tailor_and_compile_role_resume(..., allow_ipc=False)` tailors the resolved
  company `resumes/BASE.md` into `<role_dir>/resume.md` and compiles
  `<Stem>_Resume.pdf`. `allow_ipc=False` keeps the standalone compiler off the
  IPC brain (the ATS flow already has context), and `_strip_html_comments()`
  removes `<!-- ... -->` audit markers before PDF rendering. Falls back to a
  master-PDF copy only when no `BASE.md` resolves or compilation fails.
- **Stage 4 base-markdown cover-letter synthesis** (`core/generate_professional_cover_letter.py`):
  `_parse_base_cover_letter_md()` substitutes the `BASE.md` placeholder set
  (`[Job Title]`, `[Company Name]`, `[City, State, Country]`, and the alternate
  spellings `[Exact Job Title]`, `[Company]`, `[Company Location]`), parses
  `- `/`* `/`• ` bullets into `(title, body)` tuples, and emits `Cover_Letter.md`.
  `_split_paragraphs()` renders `\n\n`-separated blocks as distinct `<p>` tags in
  HTML/PDF (9.2pt font, 1.4 line-height CSS) while keeping raw `\n\n` in
  `Cover_Letter.txt`. Company-framed prose reaches the PDF untouched; the
  generic boilerplate fallback runs only when no `BASE.md` resolved.
- **Stage 5 Section 3 markdown bullet priority**
  (`CompanySiteApply/utils/experience_matcher.py`):
  `load_role_bullets_for_employer()` sources `Achievements` bullets from
  `<Role>_<jobid>/resume.md` → company `resumes/BASE.md` → master `resume.md`,
  while city/country/dates stay grounded in the structured
  `company_site_profile.employment` / `work_experience` records.
- **Stage 5 Q&A ledger + per-role mirror** (`CompanySiteApply/ai_brain_resolver.py`):
  `_is_noise_record()` and `_compact_history()` deduplicate `screening_answers.json`
  in place on `(job_id, normalized_question)`, and `_mirror_role_answers()`
  writes the `screening_qa` block into `<Role>_<jobid>/answers.json` (folder
  discovery falls back to `*/*_<jobid>`).

- **Stem** is the Title-Cased profile slug (`profile_stem()` prefers the
  folder identity, e.g. `first_last` → `First_Last`, `full_name` fallback
  only) — stable across renames so one role folder never forks two stems.
- **Company** never resolves to the literal `"company"`
  (`resolve_company_name()` in `application_docs.py`, portal-aware default,
  empty when truly unknown so the generator refuses loudly).
- **Recipient block is AG-Brain-owned**: `AIBrainResolver.resolve_recipient_header()`
  arbitrates company/city/team from ranked evidence; conflicts and unknowns
  refuse (`REFUSED_RECIPIENT_UNVERIFIED`) and callers defer.
- Multiple jobs per company and same-title different-IDs coexist via
  `<Role>_<jobid>` folders. No per-req filename suffixes for upload.

### K. Runtime Operations Layout (Code In Repo, Data Outside)

Live profiles, artifacts, inspections, and the IPC bus live in the sibling
`F:\Operations JOB AI AGENT\` data root (override via `JOB_AGENT_OPERATIONS`
env), never in the git tree. `CompanySiteApply/utils/runtime_paths.py` is the
single choke point (`operations_root()`, `profiles_root()`,
`resolve_profile_dir()` with repo fallback for the blueprint); every present
and future path resolution flows through it. The repo keeps code + the
`default_user` blueprint only. Gemini/Colab credential files carry
`engine_enabled=false` (disabled) and are gitignored.

### L. Document Upload Independence — Exact-Path-First (Section 4)
Resume and cover letter uploads are fully independent (both accept `--job-id`), and both try the exact
structured role path FIRST (`application_doc_paths()` for
`APPLIED/.../<Company>/<Role>_<jobid>/` with FIXED names — no glob):
- `s4_cover_letter_upload.py` — exact role path first (verified Job ID + title against the role folder, plus PDF `st_mtime >= txt st_mtime - 5.0`); stale cover (not uploaded this session for this job) → REMOVE first → upload fresh PDF. DOM display filenames are never trusted. Glob newest-first is legacy fallback only. If Stage 4 tailoring failed (`_tailoring_failed`), removes any stale draft, uploads NOTHING, and returns `REVIEW_BLOCKED` (`skip_retry=True`) with missing document + fix command.
- `s4_resume_upload.py` — exact role path first; if resume present → skip. Glob fallback is resume-constrained (`*token*resume*.pdf`) and skips `APPLIED` trees for base inputs.
- Each script is callable independently. Stale cover but present resume → ONLY cover letter re-uploaded.

### M. Tailoring Gate, Session Walls & Portal Submit Gates (2026-10-15)
- Fill-everything/upload-nothing: Stage 4 failure stamps `_tailoring_failed` on `best_job` + `candidate_data`; Section 4 still completes diversity/signature/visual, then halts `REVIEW_BLOCKED`. Stage 6 and the ledger propagate blocked statuses and never report ready. Re-upload surgically via the `s4_*_upload.py --job-id` scripts.
- Mid-run login/session walls halt immediately as `SECTION_BLOCKED` (`SESSION_EXPIRED_OR_LOGIN_REQUIRED`) instead of looping to `MAX_STEPS_EXCEEDED`.
- Submit is human-only on every portal: Greenhouse `advance_step` (like Oracle) requires explicit `allow_submit=True`, which agents never pass.

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
