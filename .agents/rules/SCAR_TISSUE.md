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
- **Fix applied**: Added Guardrail C24 (card-level exp band gate) in `04_job_discovery.py`; added 6 negative keyword entries to `profiles/<profile>/candidate_config.json`.
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

## [2026-09-22] FALSE POSITIVE MATCH ON INFRASTRUCTURE PATCHING ARCHITECT
- **File**: `core/ai_client.py` → `evaluate_job_match()`
- **What happened**: Agent deep-scanned and applied to "Enterprise Patching Governance Advisor/Architect" at World Wide Technology for a Lead Java Backend Architect candidate. Root cause: The heuristic mathematical scorer awarded 71 points (title points for "Architect" + 35 work-capability points because Udaysagar's resume has IT Governance). The fallback IPC timed out after 25s, so the heuristic score was accepted, and negative_keywords lacked specific IT infrastructure patching terms.
- **Correct behavior**: (1) Never approve or fall back to high heuristic scores on pure infrastructure/patching/ITSM roles for software engineering profiles. (2) Immediately populate `candidate_config.json["target_jobs"]["negative_keywords"]` with `Patching`, `Patch Management`, `Vulnerability Management`, `ITSM`, `IT Infrastructure Management`.
- **Never repeat**: Never let non-software engineering architect roles (Patching, Infrastructure, ServiceNow, ERP) pass into deep scan or apply. Ensure both batch triage and negative keywords strictly exclude IT Operations and Patching.

---

## [2026-09-23] GEMINI_CLIENT PROPERTY SETTER CONFUSION DURING ROUND-ROBIN REFACTOR
- **File**: `core/ai_client.py` → `AIClient.__init__` and `_rotate_gemini_client()`
- **What happened**: When implementing multi-key round-robin, `self.gemini_client` was converted to a `@property`. The old `self.gemini_client = None` static assignment at the bottom of `__init__` caused an `AttributeError: can't set attribute`. Then, when re-adding the Colab init block to fix `AttributeError: 'AIClient' object has no attribute 'colab_client'`, the entire Colab initialization block was accidentally placed INSIDE `_rotate_gemini_client()` instead of `__init__`. This silently broke colab credential loading.
- **Correct behavior**: `self.gemini_client` MUST be a `@property` with no setter. NEVER assign `self.gemini_client = ...` anywhere — use `self._gemini_clients` and `self._current_client_idx` directly. All startup initialization code (`self.colab_client = None`, credential loading) belongs in `__init__`, NOT in `_rotate_gemini_client()`.
- **Never repeat**: After any refactor of `AIClient`, verify with `git diff` that no init-time code was displaced into a method. The `@property` decorator on `gemini_client` is permanent and must never be converted back to a static attribute.

## [2026-09-23] PROFILE CONFIG EDITED VIA THROWAWAY PYTHON SCRIPT INSTEAD OF DIRECTLY
- **What happened**: To update `candidate_config.json` role titles, AI wrote a `scripts/update_roles.py` file and ran it. User correctly called this out: the config JSON should be edited directly, not through a hardcoded script.
- **Correct behavior**: `candidate_config.json` is a data file. Edit it directly using `replace_file_content` or the `view_file` → Python `json.load/dump` one-liner pattern. Never create a named script just to mutate a config value.
- **Never repeat**: Config JSON files (`candidate_config.json`, `gemini_credentials.json`, etc.) are directly editable data files. Never create intermediary Python scripts to update them unless the user explicitly requests a migration utility.

## [2026-09-27] DEADLINE-FREE NETWORK CALL FROZE WHOLE CYCLE
- **File**: `core/ai_client.py` → `_call_gemini_with_fallback()`
- **What happened**: Live daemon wedged 7+ minutes with zero output mid-deep-scan (page loaded, JD scraped). Every other wait in the system has a deadline (IPC 90s, batch 120s, nav C32) — the raw SDK call had none, so one stalled socket froze the cycle. Diagnosed line-precise only because the freeze point (post-scrape, pre-score) was readable in logs.
- **Correct behavior**: Worker-thread `result(timeout)` from `target_jobs.gemini_call_timeout_seconds` (default 90s); expiry rotates keys, teardown never blocks, exhaustion raises into existing fallbacks (Guardrail C36).
- **Never repeat**: Never ship a network call without a finite deadline. When a freeze has zero output, bisect by pipeline checkpoint (page? JD? score?) before touching anything.

## [2026-09-27] UNGROUNDED NUMERIC EXPERIENCE ANSWERS TYPED INTO VALIDATED FIELDS
- **File**: `core/ai_client.py` → `answer_screening_question()` (+ prompt DB)
- **What happened**: Total experience answered "0 years" and mapped Spring Boot answered "3 years" (map: 8) into LinkedIn validated fields → red errors → adapt-retry burned → honest abort. Mechanism: the explicit skill-years map never reached the model prompt (names only), and no layer checked model numerics against truth. "Professional/work experience" phrasing additionally bypassed total-type detection entirely.
- **Correct behavior**: Skill-years map in the prompt DB (models never estimate mapped skills) + C35 validator healing total/known-skill numerics at all three answer return points; "professional/work experience" added to `total_experience_keywords` (blueprint + live); unknown skills/prose/months untouched.
- **Never repeat**: Never let a numeric answer reach a portal without a truth check. Never hardcode question phrases in Python — extend `screening_heuristics`, never literals.

## [2026-09-28] PAY-SCALE GARBAGE + MISSING SKILL KEY GUESSES
- **File**: `core/ai_client.py` → `_format_ctc_answer()` (new); `candidate_config.json` skill map + `screening_heuristics`
- **What happened**: Expected pay typed as "21.12 LPA" / "2112000 LPA" (rupees digits wearing an LPA unit) into validated boxes; team management answered "1 year" vs owner-stated 2.5 because the skill map had no such key and the model estimated. Owner directive: detect field scale/type and answer canonically, never guess.
- **Correct behavior**: CTC Qs disambiguated current-XOR-expected emit profile canonicals (question scale outranks answer sniffing; bare ambiguous controls untouched); "team management": 2.5 added as owner-confirmed fact; whole-coercion numeric-controls only; plural agreement fixed ("2.5 year" → "2.5 years").
- **Never repeat**: Never emit pay figures in a scale the field didn't declare. Never let the model estimate a skill the owner can pin — ask, then pin it in the map.

## [2026-09-28] CATALOGUED-BUT-NEVER-WIRED DISCOVERY MECHANICS
- **File**: `core/04_job_discovery.py` (read-more click, expansion trigger)
- **What happened**: Two documented capabilities were fiction: the Naukri read-more selector lived only in a JSON catalog with zero code readers (descriptions would truncate if Naukri reactivates), and `analyze_and_expand_designations()` had zero callers since Batch v2 (market titles never entered config). Docs claimed both; code did neither. Caught only because the owner asked for proof, not prose.
- **Correct behavior**: Universal pre-scrape expander pass (C37) + zero-yield market expansion hook with budget caps (C37). Docs describe only what code provably does.
- **Never repeat**: Never trust a capability claim without a caller/clicker. Grep the verb (click/call), not the noun, when verifying a feature.

## [2026-09-29] SILENT DEDUP READ AS BROKEN RETRIEVAL
- **File**: `core/04_job_discovery.py` → ARM card loop
- **What happened**: Owner watched full Naukri pages with zero log lines and concluded the scraper was dead after 5 hours. Live DOM probe proved 20/20 cards extract fine — the ledger `continue` was simply silent, so a saturated inventory looked identical to dead selectors. Single supervised cycle reproduced the healthy path end to end.
- **Correct behavior**: Per-page ledger-skip count with explicit "(retrieval healthy)" marker (logging only, zero behavior change).
- **Never repeat**: Every silent skip path must narrate itself. When a user reports "finds nothing", first split saturation vs breakage with a live DOM count before touching any code.

## [2026-10-07] SECRETS CARRIED IN LIVE PROFILE CONFIGS
- **File**: `profiles/<live>/candidate_config.json` (`candidate.gemini_api_key`, `candidate.gemini_model`); readers in `core/ai_client.py` and `core/ipc_auto_resolver.py`
- **What happened**: API key and model lived in a per-profile runtime file that gets copied and backed up, making every copy a secret carrier. Code treated the profile as a secrets source, contradicting the global-secrets-only policy in `test_colab_connection.py`.
- **Correct behavior**: Secrets resolve ONLY from `gemini_credentials.json` / `colab_credentials.json` or environment. Profiles scrubbed with timestamped backups; code paths removed; `ProfileContext` warns on secrets-capable profile keys.
- **Never repeat**: Never add `*_api_key` or model-secret keys to any profile schema. New secrets go in the global git-ignored credential file or env first.

## [2026-10-07] RESIDUAL SCREENING LITERALS AFTER CLAIMED MIGRATION
- **File**: `core/ai_client.py` → `_heuristic_screening_answer()` and `_best_option_match()`
- **What happened**: Header claimed full extraction to `screening_heuristics`, but ~20 literal lists (general-exp, zero-equivalents, CTC scale/current/expected, disability, age, auth, sponsorship, military, passport, education, boolean-positive, proficiency tiers) remained inline.
- **Correct behavior**: All lists migrated to 21 new `screening_heuristics` keys in the `default_user` blueprint and ARCHITECTURE_REFERENCE schema; Python reads via `sh.get()` with blueprint-mirroring fallbacks for old profiles.
- **Never repeat**: After a heuristics migration, grep `for k in [` and `in [` in `ai_client.py` — a clean migration leaves zero question-domain literals.

## [2026-10-07] ASSUMED ATS DEFAULTS IN COMPANY_SITE_APPLY
- **File**: `CompanySiteApply/CompanyScraper/base_scraper.py`, `fingers/oracle_cloud_finger.py`, `nails/oracle/jpmc_nail.py`
- **What happened**: Assumed stack (`Java/...`), city (`Bangalore`), salutation/country/degree/major/dates (`Mr./India/...`), demographics (`Asian/Male`), fixed Yes/No screening answers, and `options[0]` fallback shipped as defaults.
- **Correct behavior**: Config-driven with empty-skip; human-gated operator fills unknowns; JPMC `_match_choice` returns None (H1); screening gated on candidate truth.
- **Never repeat**: Never invent identity or stack in ATS adapters. Unknown fields stay blank for the operator.

## [2026-10-07] ADVANCING PAST RED FIELDS + SESSION-STATE ASSUMPTIONS ON LIVE PORTALS
- **File**: Supervised JPMC CX_1001 run (scripts, then `select_jet_combo`/`verify_step_advanced` hardening)
- **What happened**: Scripts verified page-advance (URL change) but never per-field persistence, carrying red/invalid fields and wiped values across sections. Separately assumed a fresh session: values die on re-render, Back-navigation, and relogin (email wiped by terms modal; city/pills wiped by navigation; only server-persisted profile fields survive).
- **Correct behavior**: Standing Directive 10 page loop — triage the session first (fresh/partial/intact), then per page: discover live, verify state, fill/correct/upload, re-verify (max 3 passes, residuals to retry/AI/operator), advance only when clean. `docs/COMPANY_PORTAL_PAGELOOP_PROTOCOL.md` is the mandatory preload for all future portal work.
- **Never repeat**: Never treat "clicked" or "page changed" as "correct". Every fill ends in DOM read-back proof; every session starts with a state audit.
## [2026-10-07] TITLE PILL SKIPPED + NO PRE-ADVANCE GATE ON LIVE PORTALS
- **File**: Supervised JPMC CX_1001 Section-1 run
- **What happened**: Title Mr. was fixed, then a re-render wiped it and later scripts never re-asserted it — user caught it visually. Pill selection was verified with aria-pressed/class matching while these pills are role=radio with aria-checked. Separately, probe scripts kept passing [arg] lists to (x)=> JS functions taking scalars (TypeError), wasting live runs.
- **Correct behavior**: Immediately before every NEXT: re-assert all critical pills/fields and re-read invalid flags (double-gate), then advance. Verify radio pills ONLY via aria-checked. Pass scalars to scalar JS params; keep a checklist that survives across scripts in one run.
- **Never repeat**: Never assume an earlier fix survived a re-render. The gate before NEXT re-proves everything.

## [2026-10-08] MISSING .input-row--invalid IN ERROR SELECTORS + REQUIRED FIELDS ALLOWING ADVANCE
- **File**: Supervised JPMC CX_1001 Section-2 run
- **What happened**: Advanced past Section 2 while leaving a required multi-select combobox empty. The error checker missed it because the container used `.input-row--invalid`, which wasn't in the error selector list. Furthermore, the portal allowed advancing to Section 3 despite the missing required field.
- **Correct behavior**: Error selectors MUST include `.input-row--invalid`, `[aria-invalid="true"]`, and check for texts like "This information is required". Even if the NEXT button is enabled, perform a strict local validation of all fields marked required before clicking.
- **Never repeat**: Never trust the NEXT button's enabled state as proof of page validity. Always verify required fields are populated and use comprehensive DOM error selectors.

## [2026-10-08] ASSUMING PRE-FILLED DATA IS CORRECT + SKIPPING SECTION VALIDATION
- **File**: Supervised JPMC CX_1001 Section-3 run
- **What happened**: I saw that the Education and Experience tiles had no red errors and their titles looked roughly correct, so I assumed the pre-filled data (like "December 2015" for graduation month) was correct. I skipped opening and verifying each work experience tile against the config/resume.
- **Correct behavior**: "ALWAYS read current values/selections BEFORE editing; VERIFY every pre-filled value". Every tile must be opened, its fields read, and cross-referenced with the source of truth (`candidate_config.json` / `resume.md`) before advancing.
- **Never repeat**: Never trust ATS pre-filled data. A green/no-error state just means the data fits the schema, not that it is truthful to the candidate.

## [2026-10-08] COMBOBOX JS SYNTAX CORRUPTION + CACHE LOOP EARLY BREAK + RADIO GROUP MULTI-SELECT OVERWRITE
- **File**: `CompanySiteApply/utils/dom_helpers.py`, `core/ai_client.py`, `CompanySiteApply/fingers/oracle_cloud_finger.py`
- **What happened**: 
  1. `DOMHelpers.select_jet_combo` had corrupted JS string concatenation in `page.evaluate()` (`querySelector('[name="' + nm + '"]')`), evaluating to an invalid CSS selector `[name= + nm + ]`. This caused `_read()` to return `'missing'` on every poll, triggering a destructive last-resort typing fallback that clicked the clear-X reset button and wiped City/Country.
  2. In `ai_client.py` -> `answer_screening_question`, when checking `ats.items()`, if `matched_opt` was `None` for a matched question substring (e.g. `'primary area of expertise'` returning `'Software Engineering'`), the loop executed `break` instead of `continue`. This stopped evaluation before reaching more specific keys (like `'area of expertise'`), causing a fall-through to heuristics.
  3. `_heuristic_screening_answer` matched generic English words (`development`, `native`) from `domain_tokens` against tech stacks and returned multiple options joined by `|||`. Looping and clicking each pill in a single-choice radio group (`SingleSelectPills`) caused subsequent clicks to uncheck previous ones, leaving the wrong option (`UI/Frontend development`) selected.
  4. In `oracle_cloud_finger.py`, multi-combobox selector passed `f"#{combo_id}"` with IDs starting with digits (`#300052930132102-48`), throwing CSS selector syntax errors in Playwright, and passed `options=[]` which bypassed cached truth.
- **Correct behavior**:
  1. Always use JS backtick template literals `` `[name="${nm}"]` `` in `page.evaluate()`.
  2. Use `continue` instead of `break` in `ats.items()` when a key's value doesn't match available options so subsequent specific keys are checked.
  3. Skill matching must be restricted to explicit skills (no generic `domain_tokens` matching), and single-choice controls (`RADIO`, `single choice`, `select one`) must strictly return only the single best match.
  4. Pass attribute selectors `[id='...']` for DOM elements with numeric-prefixed IDs.
- **Never repeat**: Never join multiple answers with `|||` for single-choice/radio questions. Never use `break` prematurely in candidate cache dictionary scans. Always use safe attribute selectors `[id='...']` for dynamic IDs.

## [2026-10-08] COMBOBOX RESET BUTTON FOCUS + IGNORING RED ERROR LABELS ON ADVANCE
- **File**: `CompanySiteApply/fingers/oracle_cloud_finger.py`, `CompanySiteApply/utils/dom_helpers.py`
- **What happened**: When selecting City / State in Oracle Cloud HCM comboboxes, tabbing or clicking away caused browser focus to land on the adjacent clear/reset button (`[id$='-reset-button']`, `.icon-clear`, `button[aria-label*='Clear']`), wiping the committed value and turning the field red with "The City field is required." / "The State field is required." The agent then clicked NEXT despite red error messages being visible on the DOM.
- **Correct behavior**:
  1. Never click any button containing `clear`, `close`, `remove`, `reset`, `delete` unless verified.
  2. Avoid keyboard `Tab` across combobox fields when an adjacent reset button exists. Commit via explicit item click + blur/escape.
  3. Strict Pre-Advance Red Error Gate: NEVER click NEXT or advance if ANY red error exists (`.cx-messages__message--error`, `.cx-form-control__error-message`, `.app-form-item__error`, `.oj-form-control-error-message`, `[role='alert']`, `*:has-text('is required')`). All red errors must be resolved and confirmed 0 before advancing.
- **Never repeat**: Never advance past red validation errors. Never let focus or generic button clicks hit clear/reset buttons.

## [2026-10-08] LINKEDIN URL TRUNCATION BY ORACLE HCM RESUME AUTO-PARSER
- **File**: Oracle HCM Section 4 (`siteLink-1`)
- **What happened**: Oracle HCM auto-parsed a previous resume header and extracted a truncated LinkedIn URL (`https://linkedin.com/in/udaykan` missing `dpal`). Because the automation did not inspect or validate link fields against `candidate_config.json`, the corrupted URL remained on Section 4.
- **Correct behavior**: Always inspect all link inputs (`input[id*='siteLink']`, `input[aria-label*='Link']`, `input[placeholder*='linkedin']`). If the value is truncated or missing, explicitly override with the candidate's canonical `linkedin_profile_url` (`https://www.linkedin.com/in/udaykandpal`).
- **Never repeat**: Never trust auto-parsed URLs in candidate links. Always verify full URL string completeness against config.

## [2026-10-08] COVER LETTER REMOVAL BEFORE RE-UPLOAD + NO TABLES / CLEAN EXECUTIVE BUSINESS FORMAT
- **File**: `core/generate_professional_cover_letter.py`, `docs/templates/PROFESSIONAL_COVER_LETTER_TEMPLATE.md`
- **What happened**: When generating a cover letter, an obsolete cover letter remained on the portal because it wasn't removed first. Furthermore, early drafts used HTML tables and decorative boxy card containers, which are inappropriate for Tier-1 corporate and banking cover letters.
- **Correct behavior**:
  1. If a cover letter is already attached (`REMOVE COVER LETTER`), click remove first, then upload the fresh PDF.
  2. Professional executive cover letters must NOT contain `<table>` metadata blocks or flashy callout container cards. They must follow standard clean business typography (standard date line, recipient block, Re: line, salutation, body paragraphs, and clean indented bullet points without boxes or tables).
- **Never repeat**: Never upload a cover letter without deleting the previous one first. Never put tables or flashy cards/boxes in professional cover letters.

## [2026-10-08] PREFERRED LOCATIONS COMBOBOX PILL SELECTION & CLEAR-X RESISTANCE
- **File**: `CompanySiteApply/fingers/oracle_cloud_finger.py`, Section 1
- **What happened**: The multi-select combobox for `preferredLocations` was not reliably populated because clicking the small toggle button failed to open the listbox, or navigating past it clicked the adjacent clear-X button.
- **Correct behavior**: Always click `input[name='preferredLocations']` directly to open `[id^='preferredLocations'][id$='-listbox']`, select the target list item (`.cx-select__list-item`) to form a verified pill (e.g. `33437-Embassy Tech Village - Parcel`), and never click any button with `aria-label*='Remove value'` or clear-X icons.
- **Never repeat**: Never click toggle buttons when input click opens the listbox. Never click generic buttons adjacent to comboboxes.

## [2026-10-08] ORACLE HCM SECTION 3 INLINE FORM HEALING LOCK
- **File**: `CompanySiteApply/fingers/oracle_cloud_finger.py`, `heal_all_experience_tiles.py`
- **What happened**: Section 3 tile editing in Oracle HCM CX is rendered INLINE (`.apply-flow__content-form`, `.standard-apply-flow-profile-item`), not in `.app-dialog`. While editing, parent tiles are hidden (`profile-item-list--disabled { display: none }`).
- **Correct behavior**: Iterate through all tiles dynamically. Open tile, set Country (`India`) via combobox dropdown click, fill City (`Bengaluru`/`Noida`/`Delhi`), click Internal Candidate (`No`), format achievements into authentic `• ` bullet points from `resume.md`, click SAVE, and wait for `input[id^='employerName']:visible` to become hidden (form closed) before touching the next tile. This proven logic is frozen and must never be altered.
- **Never repeat**: Never look for `.app-dialog` on Oracle HCM inline experience tiles. Never scroll or click subsequent tiles while an inline form is still open.



## [2026-10-12] KNOCKOUT VM EXPERIENCE TILE SORT UNRELIABLE — USE DOM TEXT DATE PARSE
- **File**: `CompanySiteApply/nails/oracle/jpmc_nail.py` → `reorder_experience_tiles()`, `experience_section_agent.py` → `_reorder_tiles_reverse_chronological()`
- **What happened**: Both files sort tiles via Knockout VM `parent.forms.sort()` using `modA.startDate()` + `localeCompare()`. Oracle HCM stores `startDate` in mixed formats (`"03/2026"`, `"September 2021"`, `null`). Live run confirmed wrong order: Cognizant (current/03/2026) buried in the middle; TCS (09/2021) appeared after Navyug (06/2018).
- **Correct behavior**: Parse visible tile text using regex (`(\d{2})\/(\d{4})` → YYYYMM integer). Re-insert DOM tiles via `tileList.appendChild(tile)`. Tiles with "Present" → sort value 999999 (always first). Spec in `docs/SECTION_IPC_ARCHITECTURE.md §4.1`.
- **Never repeat**: Never use `startDate()` Knockout observable for sort. Never `localeCompare()` ATS portal date strings.

## [2026-10-12] CONDITIONAL SECTION 2 QUESTIONS MISSED AFTER BINARY PILL FILL
- **File**: `binary_question_subagent.py` → `heal()`, `questionnaire_section_agent.py`
- **What happened**: After `BinaryQuestionSubAgent` answers 6 binary pills, a NEW question appears: "Please select the relevant years of work experience…" as a radio chip group. `heal()` exits after the first DOM scan and never re-scans. Confirmed unanswered in Section 4 screenshot.
- **Correct behavior**: After ALL Section 2 primary sub-agents complete, run a 3-pass conditional rescan. Each pass re-queries DOM for newly visible required questions, writes to IPC, AG Brain answers, script fills. Repeat until no new questions found (max 3 passes). Spec in `docs/SECTION_IPC_ARCHITECTURE.md §3, §4.3`.
- **Never repeat**: Never exit Section 2 after a single pass. Always run at least one conditional rescan.

## [2026-10-12] TERMS MODAL BLOCKS SECTION 1 SUB-AGENTS — ORCHESTRATOR BLIND SPOT
- **File**: `apply_orchestrator.py` → `run()` loop
- **What happened**: `#applyFlowLegalDisclaimer` full-page Terms modal is active when Section 1 sub-agents are dispatched. `detect_current_section()` sees URL `/apply/section/1` correctly, but form elements have `offsetWidth: 0` under the modal. `PreferredLocationSubAgent.heal()` times out. The email handler at line 117 does NOT handle this modal.
- **Correct behavior**: At top of every `while` iteration, before section detection, check for `#applyFlowLegalDisclaimer, .apply-flow-full-page-agreement`. If visible → click AGREE → wait for detach → `continue`. See `docs/SECTION_IPC_ARCHITECTURE.md §4.2`.
- **Never repeat**: Never dispatch section sub-agents without first confirming no full-page modal is overlaid.

## [2026-10-12] PREVIEW-URL COLLISION ROUTES SECTION 1 TO REVIEW
- **File**: `apply_orchestrator.py` → `detect_current_section()` (+ `review`/`diversity`/`signature` `can_handle`)
- **What happened**: Oracle URLs contain `/jobs/preview/<id>/`; naked `"review" in path` matched inside "preview", misrouting Section 1 (req 210780039) to Section 4 Review. Same flaw in three `can_handle` matchers and in job-ID regexes missing `/jobs/preview/`.
- **Correct behavior**: Numbered sections first; keyword fallback requires the `/review` boundary; job-ID regex covers `jobs?/preview/|job/|requisitions?/|preview/`. Pinned by `tests/test_section_detection.py`.
- **Never repeat**: Never substring-match `review`/`email` against full portal URLs without boundaries.

## [2026-10-12] COVER LETTER SHIPPED WITH EMPTY `(Job ID: )`
- **File**: `core/generate_professional_cover_letter.py` + `s4_cover_letter_upload.py` + `documents_subagent.py`
- **What happened**: Letter generated before the preview-URL job-ID fix rendered `Re: Application for X (Job ID: )` and was uploaded as if tailored.
- **Correct behavior**: Template omits the parenthetical when ID is empty (loud warning); every upload path verifies the companion `Cover_Letter.txt` names the requisition via `verify_cover_letter_job_id()` and regenerates on mismatch. Pinned by `tests/test_cover_letter_job_id.py`.
- **Never repeat**: Never treat a tailored file as valid without content verification.

## [2026-10-12] INDIA-ONLY ENFORCEMENT VIA `allowed_countries` HARD GATE
- **File**: `cognitive_job_matcher.py` + `autonomous_job_agent.py` (Stage 2)
- **What happened**: Location was 20 soft points, so Jersey City req 210776611 scored 80/100 and was applied despite `locations: ['Bangalore']`. Portal search also ran unfiltered ("Bangalore" matched no Oracle autocomplete suggestion).
- **Correct behavior**: `target_jobs.allowed_countries` (e.g. `["India"]`) disqualifies out-of-country reqs at score 0 (`out-of-country`); absent key stays neutral. Stage 2 searches the allowed country first. Pinned by country-gate tests.
- **Never repeat**: Never treat geography as bonus points when the candidate rule is a hard constraint.

## [2026-10-13] ADVANCING PAST FAILED SECTIONS — `SECTION_BLOCKED` GATE
- **File**: `apply_orchestrator.py` (`_heal_section_with_gate`) + `section_agent_dispatcher.py` (cascade passes)
- **What happened**: Post-audit flagged an unanswered required pill on req 210765001; the orchestrator logged "Retrying..." and advanced anyway. Dispatcher healed each sub-agent once, abandoning questions revealed mid-heal.
- **Correct behavior**: Retry each section 3x; on persistent failure halt with `SECTION_BLOCKED` (never advance). Dispatcher re-heals newly-invalidated agents (cascade, max 3). Pinned by gate + cascade tests.
- **Never repeat**: Never advance on `success: False`. A BLOCKED halt is a correct outcome.

## [2026-10-13] REVIEW SCREEN RE-RENDERS BACKEND ORDER — `ORDER_UNVERIFIED` GATE
- **File**: `visual_verifier_subagent.py` + `review_section_agent.py` + `s3_experience_ordering.py`
- **What happened**: Section 3→4 navigation re-mounts tiles in backend (alphabetical) order, discarding the in-session sort; the gate still reported READY.
- **Correct behavior**: Re-sort on the review screen, verify descending runtime dates (`order_verified`); unverified order fails the gate loudly. Backend order resets every fresh login — re-sort in the submit session. Within one session, a Section 3 KO sort propagates into Section 4 (verified live 210788242) — still always re-verify on review, never assume.
- **Never repeat**: Never claim sorted order without review-screen readback.

## [2026-10-13] BARE DEEP LINKS 404 — SITE-ROOT SEARCH ENTRY
- **File**: `jpmorgan_scraper.py` (`_ensure_search_page`)
- **What happened**: Bare `.../sites/CX_1002/jobs` deep link 404s without search context; the URL-substring guard then scraped the error page.
- **Correct behavior**: Enter via site root, verify the keyword widget is live (2 attempts), refuse loudly on persistent 404. Pinned by `tests/test_search_entry.py`.
- **Never repeat**: Never navigate Oracle CX by deep link without verifying the widget rendered.

## [2026-10-13] SCANNER EMITTED OPTION TEXT AS QUESTION — SELF-ECHO FLIP
- **File**: `s2_*_questions.py` scans + `ai_brain_resolver.py` fallback
- **What happened**: Req 210788242: label fallback emitted pill text "No Prior Experience" as the question; the brain echoed it back (`fallback → options[0]`); the click flipped a correct "At least 5 years" pick on the single-select group (proven by `screening_answers.json` + Section 2 proof).
- **Correct behavior**: `question_hygiene.drop_option_titled_questions()` drops option-titled rows in all three healers; brain refuses self-echo (`REFUSED_SELF_ECHO`, answer None); unknown questions and non-Yes/No pairs defer instead of blind-picking. Pinned by `tests/test_answer_integrity.py`.
- **Never repeat**: Never answer a question that is one of its own options. Never default-pick `options[0]`/`"Yes"` for unrecognized input.

## [2026-10-13] ANSWERED-BUT-WRONG NEVER REVISITED + EMAIL ADVANCE UNGATED
- **File**: `s2_competency_questions.py` (`scan_competency_rows` truth check), `s2_conditional_questions.py` (read-back), `apply_orchestrator.py` (email gate)
- **What happened**: Req 210788242 showed a selected-but-wrong tier pick nobody re-checked (audits only looked for emptiness), and the email step advanced without confirming acceptance.
- **Correct behavior**: Answered rows are re-resolved against brain truth and re-clicked on mismatch (audit flags `mismatched_answers` too); conditional pill/radio clicks require read-back match; email advances only with the address populated and the checkbox checked, else `SECTION_BLOCKED`.
- **Never repeat**: Never audit for emptiness alone; never advance any step without verifying its own completion.

## [2026-10-13] COORDINATOR-ONLY CODE NEVER EXECUTES LIVE
- **File**: `review_section_agent.py` → `visual_verifier_subagent.py`
- **What happened**: Req 210788242: reorder retry lived in `ReviewSectionAgent.heal()`, but the dispatcher routes "review" to 4 granular sub-agents — the coordinator fallback never fires. Same dead-code trap as the questionnaire 4-pass loop before it.
- **Correct behavior**: Healing logic must live in the sub-agent the dispatcher actually calls (`VisualVerifierSubAgent.heal()` reorders + verifies with retry). After adding any coordinator logic, grep the dispatch mapping to prove it executes.
- **Never repeat**: Never trust coordinator code paths without tracing the live dispatch route.

## [2026-10-13] LATE-REVEALED REQUIRED WIDGETS + STALE RESUME PARITY
- **File**: `apply_orchestrator.py` (`_section_has_visible_errors`), `dropdown_question_subagent.py` (orphan sweep), `s4_resume_upload.py` (filename-aware freshness)
- **What happened**: Req 210788242: a required languages combobox revealed after the final audit sat empty with Oracle's red "required" text while the section reported PASS; resume uploads checked filled-state only, unlike cover letters.
- **Correct behavior**: Gate-level independent error-text sweep blocks advance regardless of subagent verdicts; dropdown audit sweeps required comboboxes outside standard row containers; resume resolution prefers candidate-name newest-first and replaces filename-mismatched attachments.
- **Never repeat**: Never let audits be the only eyes on a section; never check document presence without identity.

## [2026-10-13] REQUIRED-STAR INVISIBLE TO TEXT CHECKS + UNSCOPED LISTBOX QUERIES
- **File**: `dropdown_question_subagent.py`, `s2_conditional_questions.py`, `s2_dropdown_questions.py`, `questionnaire_section_agent.py`
- **What happened**: Req 210788242 languages combobox: red asterisk renders as an EMPTY span (no literal `*` in text), `required` lives on the label class, `aria-required` on the input — all three audit layers checked literal text only and passed an empty required field. Separately, global listbox queries collided with 9 SPA toggles and the ODA chatbot listbox.
- **Correct behavior**: Required = literal `*` OR star-span/label-required class OR `aria-required` (all scans + tripwire); listbox discovery scoped via the row input's `aria-controls` with ODA exclusion and row/global fallbacks.
- **Never repeat**: Never check required-ness by text alone on Oracle JET; never query listboxes globally on an SPA.

## [2026-10-13] COVER TITLE FROM BARE H1 + REVIEW REORDER SINGLE-SHOT
- **File**: `s4_cover_letter_upload.py`, `generate_professional_cover_letter.py`, `review_section_agent.py`
- **What happened**: Req 210788242: title selector included bare `h1`, capturing a JD section header ("Work Summary") into the letter; review-screen reorder ran once and its failure ended the run.
- **Correct behavior**: Strict job-title selectors only; defer synthesis when the title is unknown; companion-txt title verification (`verify_cover_letter_job_title`) triggers regeneration on mismatch; review reorder retries 3x with per-attempt diagnostics in the heal result.
- **Never repeat**: Never read titles from bare heading tags; never single-shot a render-sensitive reorder.

## [2026-10-13] REACT LISTBOX NEEDS FILTER TEXT — FETCH FALLBACK
- **File**: `s2_dropdown_questions.py`
- **What happened**: Req 210772077 languages listbox loads options only after filter text is typed; open-and-read returned empty, so nothing was ever selected and the agent hand-typed the pills via scratch instead.
- **Correct behavior**: Empty fetch triggers filter-typing (`a`, then `e`), re-read, input cleared afterwards. Pinned by filter-typing test.
- **Never repeat**: Never assume an opened listbox is populated; always handle the empty-options case.

## [2026-10-13] PER-COMPANY WORKSPACES + STAGE 4 ARCHIVE GAP
- **File**: `utils/company_workspace.py`, `autonomous_job_agent.py`, `s4_resume_upload.py`, `s4_cover_letter_upload.py`
- **What happened**: Resumes/letters resolved from a flat namespace (no per-company product framing); Stage 4 never wrote the per-application `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/` archive (only cli_scraper did).
- **Correct behavior**: `ensure_company_workspace()` self-provisions `company_site_apply/<Slug>/` (+ seed from master, skeleton-only for blueprints); resolution is company-first; Stage 4 archives docs per application via `_archive_application_docs()`. `company_profiles.json` maps service firms to the flat generic base and product/tech/finance firms to workspaces with cover tones; unlisted companies default to workspaces.
- **Never repeat**: Never resolve candidate documents without company scoping; never finish tailoring without archiving.

## [2026-10-13] SYNC GENERATOR INSIDE ASYNC LOOP - THREAD OFFLOAD
- **File**: `autonomous_job_agent.py` Stage 4 + `s4_cover_letter_upload.py` on-demand synthesis → shared `utils/sync_bridge.py`
- **What happened**: `generate_tailored_cover_letter()` (sync_playwright) crashed inside `--autonomous`'s event loop; the fallback note swallowed it and the stale letter survived. Stage 5's `orchestrator.run()` had the identical latent crash, plus a bare `.../apply` deep-link 404 on entry.
- **Correct behavior**: Single tested `call_sync_offloaded()` bridge for all sync-in-async calls (never inline idiom copies); Stage 5 enters via job page + APPLY NOW click. Shared `save_match_report()` helper also replaced duplicated untested writes (one copy had an out-of-scope `cfg_path` NameError).
- **Never repeat**: Never call sync Playwright code from async flows without the bridge. Never duplicate untested I/O across launchers. Never deep-link Oracle `.../apply`.
## [2026-10-14] RUNTIME DATA OUT OF THE CODEBASE — OPERATIONS ROOT
- **File**: `utils/runtime_paths.py`, resolvers, launchers, `core/utils/profile_context.py`
- **What happened**: Live profiles, artifacts, inspections, and IPC state lived inside the git-tracked tree.
- **Correct behavior**: Sibling `Operations JOB AI AGENT/` holds `profiles/`, `artifacts/`, `inspections/`, `ipc/`, `logs/` (env-overridable); repo keeps code + blueprint. All resolvers prefer Operations with repo fallback. Pinned by `tests/test_runtime_paths.py`.
- **Never repeat**: Never store runtime input/output under the code tree; never hardcode a data location outside `runtime_paths.py`.


## [2026-10-14] RUN TRANSCRIPT WRITER + PER-REQ FILENAMES
- **File**: `apply_orchestrator.py` (`_write_transcript`), `generate_professional_cover_letter.py` (per-req PDF names)
- **What happened**: Forensic runs reconstructed behavior from chat memory; generated letters overwrote each other under one filename.
- **Correct behavior**: Every orchestrator return writes `artifacts/run_transcript_<status>_<ts>.json` (verdicts, gate errors, proofs, URLs); tailored PDFs render as `{Name}_Cover_Letter_{job_id}.pdf`.
- **Never repeat**: Never end a run without a machine-readable transcript; never write per-req outputs under a constant filename.

## [2026-10-14] STALE COVER LETTER UPLOAD VIA SUFFIX-GLOB MISS (REQ 210791831)
- **File**: `s4_cover_letter_upload.py` (+ `documents_subagent.py`, `generate_professional_cover_letter.py` per-req `{Name}_Cover_Letter_{jobid}.pdf` naming)
- **What happened**: Section 4 generated per-req files with a job-ID filename suffix while the uploader globbed `*{jobid}*cover*letter*.pdf` (job-ID prefix order) — the glob never matched, fallback `candidates[0]` picked the stale generic letter, and req 210791831 uploaded 210765001 content.
- **Correct behavior**: Structured-layout contract — fixed names `<Stem>_Resume.pdf` / `<Stem>_Cover_Letter.pdf` inside `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/` (+ `resume/`/`cover_letters/` mirrors); uploaders try the exact role path FIRST, glob is legacy fallback only, no job-id filename suffixes, no `candidates[0]`. Supersedes the 2026-10-14 per-req-filename note above. Pinned by `CompanySiteApply/tests/test_application_docs.py`.
- **Never repeat**: Never glob for a file the generator names differently; never default-pick `candidates[0]` for identity documents.

## [2026-10-14] STRUCTURED-DOC VERIFICATION + OPERATOR SUBMIT (REQ 210791831)
- **File**: `artifacts/scratch/run_docs_heal.py` (scratch, since removed), `section_agents/sub_agents/documents_subagent.py`, `section_agents/scripts/s4_cover_letter_upload.py`, `section_agents/scripts/s4_resume_upload.py`
- **What happened**: After the structured-layout fix, Antigravity re-ran Section 4 documents-only via `DocumentsSubAgent.heal()` on the live tab: pre-docs empty (stale removed), post-docs both `--filled` with FIXED names from `APPLIED ON COMPANY WEBSITE/JPMorgan_Chase_Co/Sr_Manager_of_Software_Engineering_Java_AWS_React_210791831/{resume,cover_letters}/`, `Cover_Letter.txt` verified ID 210791831 + full title, visual verifier 9/9 order + diversity + signature clean, transcript `run_transcript_READY_FOR_HUMAN_SUBMISSION_1791954232.json` + proof `section_4_review_structured_docs_1791954232.png`. Operator then clicked SUBMIT manually; ledger `jpmc:210791831` marked SUBMITTED. No prod `.py` edits this run (only `Analyzed`, scratch `Edited` under Operations artifacts/scratch, since cleaned). Repo `screenshots/visual_audit/` regenerable captures removed post-submit.
- **Correct behavior**: Docs-only heal via the exact role path, transcript + proof per run, human clicks Submit, ledger moves READY -> SUBMITTED, scratch probes live under Operations artifacts/scratch (never repo root) and are cleaned after success.
- **Never repeat**: Never re-upload generic company_site_apply PDFs for a role folder requisition; never leave ledger READY after an operator-confirmed submit; never keep scratch probes or regenerable screenshots after closeout.

## [2026-10-14] PLACEHOLDER RECIPIENT BLOCK (REQ 210791831 COVER LETTER)
- **File**: `core/generate_professional_cover_letter.py` (`generate_tailored_cover_letter`)
- **What happened**: The submitted cover letter rendered "Hiring Organization Engineering Team / Hiring Organization / Bengaluru, Karnataka, India" in the recipient block. Cause: `company` defaulted to the literal "Hiring Organization" when `jd_data.company` was empty (pre-fix Stage 4 passed empty `details.company`), and `org_location` was wired to the candidate address instead of the requisition location. Base resume verified clean — fault is generator-only. The submitted PDF (already operator-submitted) is left intact as the record of what was sent.
- **Correct behavior**: Placeholder/empty company now raises `ValueError` (callers defer as `REVIEW_BLOCKED`/`ACTION_REQUIRED` instead of shipping); recipient `org_location` uses the requisition location with candidate address as fallback only. Pinned by `tests/test_cover_letter_job_id.py::test_rejects_placeholder_company` and `::test_recipient_uses_job_location_not_candidate` (suite now 7).
- **Never repeat**: Never default a company name to a plausible-looking literal; a tailored letter without a real company must fail loudly, never render.

## [2026-10-14] COMPANY-AT-SOURCE STAMPING + JOB-LOCATION RECIPIENT BLOCK
- **File**: `CompanyScraper/companies/jpmorgan/jpmorgan_scraper.py`, `utils/application_docs.py` (`resolve_company_name`, `resolve_job_location`), `autonomous_job_agent.py` Stage 4, `s4_cover_letter_upload.py`, `documents_subagent.py`, `generate_professional_cover_letter.py`
- **What happened**: Follow-up to the placeholder-block fix: the scraper never stamped `company` into tiles/details, so every consumer saw "" (ledger `company` empty, Stage 4 defaulted). `resolve_company_name` then defaulted blindly to JPMorgan (correct for CX_1002, wrong for every future portal). On-demand regeneration passed the *candidate* city as the letter location, re-showing the home city as the company city.
- **Correct behavior**: Scraper stamps `company` at the source (tiles + details). `resolve_company_name(..., default_company=)` takes the portal context (Stage 4 passes `scraper.company_name`, canonicalized "JPMorgan Chase" -> "JPMorgan Chase & Co."); truly unknown returns "" so the generator raises instead of shipping. Recipient `org_location` resolves live-DOM job city -> requisition location -> candidate fallback. Stage 4 refuses to tailor when company is unresolvable; s4 on-demand defers the same way. Hiring-team line stays "{Company} Engineering Team" (company dynamic; Oracle CX exposes no hiring-manager person — never invent one). Pinned by `test_application_docs.py` (+3: unknown->"", canonicalization, DOM-over-candidate location); suite now 145.
- **Never repeat**: Never consume a scraped job without a stamped company; never default one portal's company globally; never feed candidate address where a requisition address belongs.

## [2026-10-14] AG-BRAIN-OWNED RECIPIENT HEADER + WORKSPACE BASE LAYOUT
- **File**: `ai_brain_resolver.py` (`resolve_recipient_header`), `autonomous_job_agent.py` Stage 4, `s4_cover_letter_upload.py`, `documents_subagent.py`, `utils/company_workspace.py`, scraper `jpmorgan_scraper.py`
- **What happened**: (a) Recipient identity was decided by Python heuristics with a blind portal default, and the scraper never stamped `company` — any gap printed a plausible-but-wrong block (wasted req 210791831). (b) Workspace root held waste (`company.json`, `cover_letter_base.md`, root `resume.md`) while `resumes/` sat empty; operators hand-placed base files.
- **Correct behavior**: (a) `AIBrainResolver.resolve_recipient_header()` arbitrates company/location/team from ranked evidence (stamped > URL hint > candidate hints > portal default); conflicts and unknowns refuse loudly (persisted `REFUSED_RECIPIENT_UNVERIFIED`, callers defer). Person names never invented — team is "{Company} Engineering Team" unless stated. Scraper stamps company at source. (b) Workspace root holds README only; bases are `resumes/BASE.md` + `cover_letters/BASE.md` (seeded from profile master, legacy auto-migrated). Pinned by 4 brain tests + 1 migration test; suite 150 (+7 cover-id, +10 knowledge).
- **Never repeat**: Never let Python pick document identity unsupervised; never store base files outside their subfolders; never invent a hiring-manager name.

## [2026-10-15] APPROVED DEEP-AUDIT REMEDIATION (DECISIONS 1-4, NEW-1..NEW-8, M-2..M-6)
- **Files**: root runners + `profile_context.py`; `autonomous_job_agent.py` Stages 4-6; `documents_subagent.py`, `s4_*_upload.py` (+ `--job-id`), `review_section_agent.py`, `apply_orchestrator.py`, dispatcher `skip_retry` lift, `greenhouse_finger.py` human gate; generator (`Co..` dedup, vertical-aware team, `and N more` strip, PDF-freshness helper); word-boundary tile scoping; `build_knowledge_index.py` (Operations scan, `async def`, legacy exclusion); `reevaluate_ledger.py`; `phase_4_run.ps1`; blueprint depollution + `.gitignore`; docs/prompt count + contract updates.
- **What happened**: Pre-edit safety checkpoint `a54646b` pushed to `origin/main`. Applied the merged Gemini audit's PATCH_01/PATCH_02 with corrections: plain URLs (M-2), spaced exits (M-3), disk-true edits (M-4), guardrail count kept at 46 (NEW-6), flags on `candidate_data` not `candidate_config` (NEW-1), `--job-id` actually implemented (NEW-2). Rejected M-1 (braces/docstrings present). Fixed self-caused green-suite breaks (mock-truthy login wall, `re` alias typo, stale archive test asserting pre-contract behavior).
- **Correct behavior**: Fill-everything/upload-nothing/defer-loudly lifecycle; Operations auto-discovery CLI; Greenhouse submit gated; session walls halt; purity scans root launchers. Gates green: 159 CompanySiteApply + 7 cover-id + 10 knowledge OK, index FRESH, purity `(True, [])`, phase_4 end-to-end pass. Changes held uncommitted for principal sign-off.
- **Never repeat**: Never apply merged-audit diffs without disk-verifying every hunk, flag name, CLI contract, and count first.
