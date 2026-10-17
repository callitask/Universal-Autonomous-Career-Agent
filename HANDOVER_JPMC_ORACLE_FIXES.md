# Handover: Enterprise ATS & Company Site Autonomous Application Subsystem

> **Status:** Fully Integrated, Tested (202 CompanySiteApply Unit Tests + 25 Cover Letter Tests + 10 Knowledge Index Tests Passing as of 2026-10-17), and Production-Ready
> *(Historical snapshots in this handover citing older counts describe the state at authoring time.)*  
> **Architecture:** 6-Stage Autonomous Lifecycle, Cognitive Sub-Agent Dispatch, Dynamic Brain Q&A, and Stale Document Healing  
> **Key Constraint:** **STRICT HUMAN SUBMISSION GATE (Never click SUBMIT on Section 4).**

---

## 1. System Overview

The Company Site Apply subsystem (`CompanySiteApply/`) provides 100% config-driven, autonomous application execution directly on corporate career portals (such as JPMorgan Chase on Oracle Cloud HCM).

### Zero-Hardcoding Guarantee:
- Zero candidate PII (names, emails, phones, addresses) is hardcoded in Python code.
- Zero assumptions regarding candidate vertical, skills, or experience years (works uniformly for Software Engineering, Internal Audit, Finance, Operations, Talent Acquisition, etc.).
- All candidate data resolves dynamically from `profiles/<profile_name>/candidate_config.json` and master `resume.md`.

---

## 2. The 6 Chronological Stages

```
[Stage 1: Comprehend Profile] 
  → Ingests candidate config, master resume, and skills taxonomy dynamically.
[Stage 2: Portal Search] 
  → Dispatches JPMorganScraper using candidate's target keywords & preferred locations.
  → Prunes roles already applied via DOM tile inspection or processed_ledger.json.
[Stage 3: Cognitive Match Evaluation] 
  → Scrapes full JD and evaluates factual fit (0-100) via CognitiveJobMatcher.
  → Ranks unapplied candidate roles and selects the top-scoring requisition.
[Stage 4: Document Tailoring] 
  → Generates bespoke, ATS-compliant cover letter PDF matching exact job_id and title, directly into the structured role folder. Recipient header is AG-Brain-owned (refusals halt). On failure: stamps `_tailoring_failed`, fills all sections anyway, skips document upload, halts `REVIEW_BLOCKED` (`TAILORING_BLOCKED`) with missing document + single-step `s4_*_upload.py --job-id` fix command.
  → `BASE.md`-driven, both artifacts: `resolve_base_resume_md()` / `resolve_base_cover_letter_md()` walk 4 tiers with 3-tier non-overwriting seeding (`_is_real_base_md()` rejects `[FIRSTNAME LASTNAME]` / `[FULL NAME]` / `{{FULL_NAME}}`, so a hand-written base is never clobbered). Cover prose is synthesized from `cover_letters/BASE.md` via `_parse_base_cover_letter_md()` (`Cover_Letter.md` + `_split_paragraphs()` `<p>` rendering, `9.2pt`/`1.4`); the role resume is tailored deterministically by `tailor_and_compile_role_resume(..., allow_ipc=False)` into `<role_dir>/resume.md` + `<Stem>_Resume.pdf`, with `_strip_html_comments()` removing audit markers. Master-PDF copy is an explicit fallback only when no `BASE.md` resolves or compilation fails.
[Stage 5: Section Mini-Agent Dispatch (Form Apply)] 
  → Enters via the job page + APPLY NOW click (bare `.../apply` deep links 404).
  → Coordinates Section 1 -> Section 2 -> Section 3 -> Section 4 with pre-audit, surgical micro-heal, and post-audit.
  → Section 3 bullets prefer markdown: `load_role_bullets_for_employer()` reads `Achievements` from `<Role>_<jobid>/resume.md` -> company `resumes/BASE.md` -> master `resume.md`, while city/country/dates stay pinned to structured `employment`/`work_experience`. Section 2 Q&A is deduplicated on `(job_id, normalized_question)` and mirrored into `<Role>_<jobid>/answers.json` as `screening_qa`.
  → Failing sections halt as `SECTION_BLOCKED`/`REVIEW_BLOCKED` — never advance past unverified work. Intentionally skipped steps carry `skip_retry=True` (no pointless retries). Mid-run login walls halt as `SECTION_BLOCKED` (`SESSION_EXPIRED_OR_LOGIN_REQUIRED`).
[Stage 6: Visual Audit & Human Submission Gate] 
  → Captures high-res verification screenshot.
  → Records the exact run status in profiles/<profile>/output/processed_ledger.json (`READY_FOR_HUMAN_SUBMISSION` or the exact blocked status — never false READY) with `ready_for_submission: False` when blocked.
  → Strictly halts before clicking SUBMIT for human review.
```

---

## 3. Engineering Solutions & Solved Traps

1. **Pre-Uploaded Stale Document Retention:** Oracle Cloud HCM retains draft attachments across applications. `DocumentsSubAgent` evaluates session freshness (`_fresh_cover_uploaded`). If a document was not uploaded in the active session for the active requisition, it is flagged as `PRE_UPLOADED_STALE`, removed, and replaced with the role's fresh tailored PDF. DOM display filenames are never trusted (fixed names repeat across requisitions) — every run removes-if-filled, uploads, and verifies Job ID + title + PDF freshness (`st_mtime >= txt_mtime - 5.0`).
2. **Reverse-Chronological Experience Ordering:** JET resume parser often shuffles work history tiles out of order. `ExperienceSubAgent` and `JPMCNail` dynamically parse dates and enforce strict reverse-chronological ordering (most recent first).
3. **Screening Questionnaire Intelligence:** `AIBrainResolver` acts as the cognitive brain for screening forms, dynamically mapping candidate credentials to dropdowns, multi-select comboboxes, competency pills, and binary declarations with zero bad fallbacks.
4. **Hierarchical Section Dispatch:** `evaluate_and_heal_section` isolates failures. If Section 1 Preferred Location fails, only `PreferredLocationSubAgent.heal()` runs; Personal Details is untouched and never re-clicked.
5. **Human Submission Gate:** Submission is strictly human-gated. The agent prepares everything, verifies green checkmarks, enables the Submit button, captures full-page screenshot proof, and alerts the user.

---

## 4. Operational Playbook for New Chats

### How to Start the Agent in a Fresh Chat:
Simply instruct Antigravity:
> *"Run the autonomous company site application agent for profile [profile_name] on JPMC career portal. Follow the 6-stage lifecycle in CompanySiteApply/autonomous_job_agent.py, ensure all sub-agents execute with zero hardcoding, and halt at Section 4 before clicking SUBMIT."*

### Command-Line Execution (live profiles resolve under `F:\Operations JOB AI AGENT\profiles\`; `--profile` auto-discovers the sole live profile, or pass `--profile <profile_slug>` explicitly when more than one live profile exists):
```powershell
# Run full autonomous lifecycle (add --profile <slug> when >1 live profile exists in Operations)
.venv\Scripts\python run_universal_apply.py --profile <profile_slug> --autonomous

# Run active tab application (for forms already open; ATSArm scrapes job_id/title/company from the open tab)
.venv\Scripts\python run_universal_apply.py --profile <profile_slug>

# Run test suite
.venv\Scripts\python -m unittest discover -s CompanySiteApply/tests
```
