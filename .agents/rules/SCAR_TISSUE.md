# SCAR TISSUE LOG - Append Only. Never Delete. Never Edit Prior Entries.
# Purpose: Empirical record of actual rule violations + exact corrections.
#          This is more powerful than WORKSPACE_RULES.md because it is concrete, not abstract.
#          Every entry is a scar from a real failure. Re-read at every session start.
# Format: [DATE] VIOLATION TYPE -> What happened -> Correct behavior -> Never repeat

---

## [2026-09-09] HEURISTIC LEAK IN PYTHON SCRIPT
- **File**: core/ai_client.py -> analyze_and_expand_designations()
- **What happened**: AI added if candidate_exp >= 8.0: standard_templates = [...] as a fallback branch. Python script was making intelligent role decisions.
- **Correct behavior**: Python scripts are strictly actuators. The AG Brain generates designation lists via IPC or pre-configures them in candidate_config.json during session push-start. No experience threshold branching, no hardcoded role templates, ever.
- **Never repeat**: Before writing ANY conditional logic in core/*.py that branches on candidate attributes - STOP. That logic belongs in the AG Brain, not in code.

---

## [2026-09-10] CITY NAME HARDCODING
- **File**: core/02_profile_sync_naukri.py
- **What happened**: AI wrote a literal city string ("Bangalore") as a default fallback when the profile location list was empty.
- **Correct behavior**: Read from candidate_config.json["target_jobs"]["preferred_locations"] via ProfileContext. If the list is empty, raise a configuration error - do NOT silently default to any hardcoded city.
- **Never repeat**: Zero string literals for locations, cities, company names, or skills in any core/ or scripts/ file. All values resolve from ProfileContext at runtime.

---

## [2026-09-11] SOPHRON WRITE GUARD BYPASS
- **What happened**: AI used open(file, "w") + json.dump() to write to nodes.json directly, bypassing the SophronWriteGuard. Caused race condition when two AG sessions were running simultaneously.
- **Correct behavior**: ALL writes to shared Sophron files (nodes.json, edges.json, graph_index.json, reflections_index.json, current_week_trend.md) MUST go through guard.safe_write_json(). The guard must be instantiated first via SophronWriteGuard(session_uuid, workspace, task_summary) and guard.register_session() called before any read or write.
- **Never repeat**: If you are about to call open() on any Sophron file, you are doing it wrong. Always guard.safe_write_json().

---

## [2026-09-11] SOPHRON SESSION INIT SKIPPED
- **What happened**: AI skipped guard.register_session() at session start and skipped guard.deregister_session() at end. Multi-session detection (detect_multitasking()) never ran. Session registry became stale.
- **Correct behavior**: Session init (STEP 0 of 01_sophron_session_init.md) is non-negotiable. Instantiate guard, register_session(), run detect_multitasking(), then proceed. At session end: deregister_session(). This is not optional.
- **Never repeat**: SophronWriteGuard must be the first operation, before reading ANY file in a Sophron session.

---

## [2026-09-11] TRANSCRIPT PATH STALE
- **What happened**: master_agent_config.json still pointed to the UUID of a previous session. transcript_learner.py was ingesting from a dead session's transcript.
- **Correct behavior**: STEP 2 of 01_sophron_session_init.md - check master_agent_config.json -> paths -> transcript_path UUID. If it doesn't match current session UUID, update it immediately before running transcript learner.
- **Never repeat**: Always update the transcript path at the start of every session. Current session UUID is always available in the conversation metadata.

---

## [2026-09-13] RESUME TAILORING WITH HALLUCINATED CREDENTIALS
- **What happened**: AI-generated resume tailoring answer in pending_question.json included a skill claim not present in the candidate's resume.md, in order to better match the job description.
- **Correct behavior**: RESUME_TAILORING answers must be derived 100% from the actual content of profiles/$PROFILE/resume.md. If the candidate does not have a skill, the tailored summary does NOT mention it. ATS purity > match score.
- **Never repeat**: Before writing any RESUME_TAILORING JSON answer, verify every claim against resume.md. No invented competencies. No extrapolated expertise. Factual grounding only.

---

## [2026-09-13] MILESTONE SOPHRON CARDS SKIPPED (MOST FREQUENT VIOLATION)
- **What happened**: Multiple sessions (turns 27-40) completed significant work (daemon launches, config changes, apply cycles) without writing Sophron insight cards. Cards were only written at the end when user reminded the AI.
- **Correct behavior**: A milestone card MUST be written after: every task completion, every user correction, every topic switch, every plan approval, every discovery. Not just at session end.
- **Never repeat**: Every 5 exchanges, silently self-check: "Have I written a Sophron card recently?" If no, write one now. This is non-negotiable per STEP 4 of 01_sophron_session_init.md.

---

## [2026-09-14] CONTEXT SWITCH NOT RECORDED IN SOPHRON
- **What happened**: User shifted context mid-session from monitoring the live job agent daemon to discussing Sophron architecture + rule enforcement. The Sophron card written after this did NOT record that a context switch occurred, why it occurred, or what the previous context was.
- **Correct behavior**: Every insight card written after a context switch must include CONTEXT_TRANSITION fields: previous_context, trigger_for_switch, new_context, cognitive_load_at_switch.
- **Never repeat**: If the user's message represents a topic change from the prior message - flag it. Include CONTEXT_TRANSITION in that card. This is how Sophron builds a true workflow record.

---

## [2026-09-17] SCREENING QUESTION KEYWORD LISTS HARDCODED IN PYTHON
- **File**: `core/ai_client.py` → `_heuristic_screening_answer()` and `_is_standard_screening_query()`
- **What happened**: 14+ Python literal lists (notice period triggers, relocation keywords, interview mode keywords, numeric question triggers, exclusions, etc.) were hardcoded inline in `ai_client.py`. The list `["describe","explain","projects",...]` in `numeric_question_exclusions` contained `"projects"`, blocking the question `"How many years of BFSI projects?"` from routing to the integer answer path.
- **Correct behavior**: ALL screening question keyword lists MUST reside in `candidate_config.json["screening_heuristics"]`. Python reads them via `sh = cfg.get("screening_heuristics", {})` then `sh.get("key", [])`. Zero literals permitted. `"projects"` must be ABSENT from `numeric_question_exclusions`.
- **Never repeat**: Before adding ANY `if any(k in q_clean for k in [...])` literal list in `ai_client.py` — STOP. Add the list as a new key in `screening_heuristics` in both config files and read it via `sh.get()`.

---

## [2026-09-17] HARDCODED "internship" IN EXPERIENCE FALLBACK TEMPLATE
- **File**: `core/ai_client.py` → `_heuristic_screening_answer()` Section 5 draft text (×4 occurrences)
- **What happened**: The fallback text template used the literal word `"internship"` when building experience descriptions. This caused the live bug where a Senior Associate at Cognizant (full-time employment) was described as `"internship as Senior Associate at Cognizant"` — factually wrong and professionally damaging on live job applications.
- **Correct behavior**: The template label word must be `sh.get("fallback_text_label", "experience")`. Config value = `"experience"`. Template: `f"{_exp_label} as {primary_role} at {primary_company}"`.
- **Never repeat**: Never hardcode the word `"internship"` (or any career level label) in Python templates. If the label needs to change per candidate, it lives in config.


---
# INSTRUCTIONS FOR ADDING NEW ENTRIES:
# 1. Append at the bottom of this file (never edit or delete above)
# 2. Format: ## [DATE] VIOLATION TYPE
# 3. Include: File/context, what happened, correct behavior, "never repeat" directive
# 4. Keep each entry under 10 lines
# 5. This file must be re-read at every session start (part of STEP 1 cold-start load)

---

## [2026-09-19] THIN-JD EXPERIENCE BAND FALSE POSITIVE → SENIOR ROLE APPLICATION
- **File**: `core/04_job_discovery.py` → card-level gating section; `core/ai_client.py` → `evaluate_job_match()` exp_matches block
- **What happened**: Agent applied to a 4-9 yr experience role for a 0.5 yr fresher candidate (score: 71). Root cause: The job's JD body text was sparse/thin — the experience range "4-9 Yrs" existed only in Naukri card metadata (`exp_text`) but never appeared in the scraped `full_desc`. The `evaluate_job_match()` experience regex found `0 matches` in the body and silently awarded the 8-point "no restriction" default bonus. Additionally, `"Consultant"` was absent from `negative_keywords`, so the title gate also let it through.
- **Correct behavior**: (1) Card-level experience band gating must run against `exp_text` BEFORE deep scanning, exactly mirroring the salary floor gate. If card min exp > candidate exp + max_experience_gap_years → reject immediately as `experience_gap_gated`. (2) Senior consulting titles (`Consultant`, `Process Excellence`, `Finance Transformation`) must be in `negative_keywords` for fresher profiles.
- **Fix applied**: Added Guardrail C24 (card-level exp band gate) in `04_job_discovery.py`; added 6 negative keyword entries to `profiles/anshika_garg/candidate_config.json`.
- **Never repeat**: Never trust JD body text alone for experience seniority enforcement. Naukri card `exp_text` is populated by the platform itself and is always authoritative. Always enforce seniority at card level before wasting tokens on deep scan.

[2026-09-19] KEYWORD-GATE ARCHITECTURE CAUSES FALSE POSITIVES AND FALSE NEGATIVES
Root Cause: Python is_title_allowed() + highlights keyword gate used stale keyword lists to make
semantic match/reject decisions on job cards. This caused: (1) False rejections — "manage" as verb
in JD body blocked entry-level roles because "Manager" was in negative_keywords; (2) False acceptances
— senior roles with novel title patterns not in any keyword list passed unchecked.
Fix Applied: G-BRAIN-01 — Removed is_title_allowed() call from card loop. Removed highlights keyword
gate. All semantic decisions now route to AG Brain via JOB_CARD_EVALUATION IPC. Python retains only
objective numeric gates: salary floor, C24 exp band, negative_companies (exact identity).
Principle: Python = arms and legs (data collection + actuation). AG Brain = sole decision-maker for
all semantic job fit evaluations. Keyword lists in config are advisory context for AG Brain only.

---

## [2026-09-21] DIRECTIVE 2 TIER B LITERAL DEFAULTS IN COMPANY_SITE_APPLY
- **File**: `CompanySiteApply/fingers/oracle_cloud_finger.py` (lines 510, 515, 934, 938), `CompanySiteApply/CompanyScraper/base_scraper.py` (line 102), `CompanySiteApply/nails/oracle/jpmc_nail.py` (lines 68, 86).
- **What happened**: Hardcoded literals ("560100", "Bangalore", "Asian", "Male") were embedded as fallback defaults in `CompanySiteApply/`. These survived undetected by `verify_codebase_purity()` because purity scanning explicitly scopes to `core/` and `scripts/` only, leaving `CompanySiteApply/` un-audited.
- **Correct behavior**: All demographics, zip codes, and cities must resolve dynamically from `candidate_config.json` via `ProfileContext` or user prompts. `CompanySiteApply/` runs strictly on-demand/human-gated, but must not harbor hardcoded candidate assumptions.
- **Never repeat**: Never embed candidate defaults or demographic assumptions in ATS finger/nail adapters. When adding fallback values in `CompanySiteApply/`, always resolve from `candidate_data.get()` and prompt the operator if missing.

## [2026-09-21] SRP & ATS Load Latency Accommodations
- **Context:** Core engine files (04_job_discovery and 05_apply_jobs) were failing prematurely with 12s/15s timeouts on heavy SPA boards and ATS platforms due to bot-detection interstitials or API load latency.
- **Fix:** Increased Playwright `timeout` kwargs to 60s/75s across discovery and application layers.
- **Preventative:** Do not lower these timeout values unless structural headless proxy optimizations are implemented.
