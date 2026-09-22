# UNIVERSAL AUTONOMOUS CAREER AGENT: ARCHITECTURE REFERENCE

> **Document Version:** 5.3 — Multi-Key Round-Robin Gemini Rotation, SmartRateManager, Gemini Inline Batch Engine  
> **Last Updated:** 2026-09-23  
> **Purpose:** Comprehensive technical reference for the complete pipeline — how every module works, data flows, inter-process communication, DOM interaction patterns, multi-bullet regex isolation, two-tier early highlights gating, card-level experience band gating (Guardrail C24), and the chatbot reverse-engineering protocol. Upload this alongside `WORKSPACE_RULES.md` to ground the AI's understanding of the system before any coding session.

---

## 1. SYSTEM OVERVIEW

The Universal Autonomous Career Agent is a **three-daemon, file-coordinated, CDP-driven** autonomous pipeline that:

1. **Discovers** job postings on Naukri and LinkedIn via batched SRP scraping
2. **Pre-Filters Early Highlights** against negative candidate criteria directly from DOM before deep un-clamping
3. **Evaluates** each posting against the candidate's resume using Two-Stage Cognitive AI scoring (0-100) with multi-bullet regex isolation
4. **Tailors** the candidate's factual resume by reordering bullets for ATS keyword density
5. **Renders** a per-job PDF via Playwright's Chrome PDF engine
6. **Uploads** the tailored resume to the candidate's Naukri profile
7. **Applies** autonomously — solving 1-click apply and multi-step chatbot drawers
8. **Monitors and Relays IPC** questions via an asynchronous file-based IPC watcher and AG Brain cron loop within a 90-second SLA (120s for batch)
9. **Verifies** submission via DOM success markers
10. **Tracks** everything in CSV + JSON + persistent composite-key deduplication ledgers for audit

**Execution Model: The Three-Daemon Architecture**
Instead of a single blocking monolithic process or unmonitored terminal inputs, the system operates across three coordinated daemons:
- **Daemon 1 (Discovery & Application Runner — `continuous_career_agent.py`):** Runs the continuous discovery and application loop via Chrome DevTools Protocol (CDP port 9222). Orchestrates `04_job_discovery.py`, `generate_factual_tailored.py`, `02b_naukri_fast_resume_upload.py`, and `05_apply_jobs.py`. If a novel or un-cached chatbot question is encountered, writes to `pending_question.json` and polls non-blocking. Runs with default cooldown `--delay 30`.
- **Daemon 2 (IPC Watcher & Signal Relay — `core/ipc_watcher.py`):** Dedicated lightweight background daemon polling both `pending_question.json` (single IPC) and `batch_question.json` (batch IPC) within a single shared 2.0s poll loop (`run(poll=2.0)`). Emits immediate structured ASCII alerts to stdout.
- **Daemon 3 (AG Brain Cron Monitor — Recurring 1-Minute Heartbeat):** Scheduled periodic monitor running within the AG Brain agentic environment (`* * * * *`). Wakes up every 60 seconds, inspects Daemon 2 logs, `batch_question.json` (120s timeout SLA) and `pending_question.json` (90s SLA), synthesizes ground-truth factual answers from `resume.md` and candidate config, and commits the JSON answer directly.

**Architectural Separation of Concerns:**
- **Developer Scope (`core/`, `docs/`, `core/utils/`):** In coding sessions, the AI assistant operates strictly as the Principal Agent Developer, updating engine logic, documentation, and tooling. The developer **never manually edits files inside `profiles/`**.
- **Runtime Agent Scope (`profiles/`):** When the agent is executed, the agent itself autonomously and intelligently reads candidate resumes, synthesizes `cognitive_profile.json`, maintains `processed_ledger.json`, caches `auto_learned_truths`, and adapts `candidate_config.json` (e.g. starvation title auto-expansion) without manual developer patching.

---

## 2. PIPELINE EXECUTION SEQUENCE & THREE-DAEMON FLOW

**Batch Architecture v2.0:**
Instead of serial 90-second IPC blocking per job card, the system now uses an ARM->BRAIN->EXECUTE architecture per daemon cycle, processing exactly one designation per cycle.

```
[DAEMON 1: Discovery & Application Runner]
continuous_career_agent.py (daemon loop --delay 30)
  │
  ├─► [Optional] 02_profile_sync_naukri.py --profile <dir>
  ├─► [Optional] 03_profile_sync_linkedin.py --profile <dir>
  │
  └─► LOOP:
       ├─► 04_job_discovery.py --profile <dir>
       │    │
       │    ├─► [ARM PHASE]: Collect Job Cards
       │    │    ├─► SearchStateManager selects ONE active designation
       │    │    ├─► Scrape SRP (Search Results Pages 1-3 via SEO Slugs)
       │    │    ├─► SRP Card-Level Pre-Scan Gates (Salary Floor, Exp Band C24, Blacklist)
       │    │    └─► Accumulate into designation_batch_cards
       │    │
       │    ├─► [BRAIN PHASE]: Batch IPC Evaluation
       │    │    ├─► Write ALL cards to batch_question.json
       │    │    ├─► Wait up to 120s for AG Brain to reply in batch_answer.json
       │    │    └─► Parse [DEEP_SCAN, SKIP] decisions
       │    │
       │    ├─► [EXECUTE PHASE]: Deep Scan & Apply (Approved Cards Only)
       │    │    ├─► For each DEEP_SCAN card:
       │    │    ├─► Deep Scan: Open JD Detail Page & Un-clamp "Read More"
       │    │    ├─► Two-Stage Navigation Recovery C32 (commit 60s + domcontentloaded 75s)
       │    │    ├─► Stage 1 & Stage 2 Precision Match Score
       │    │    ├─► If score >= 60%:
       │    │    │    ├─► generate_factual_tailored.py --profile <dir>
       │    │    │    ├─► 02b_naukri_fast_resume_upload.py --profile <dir>
       │    │    │    └─► 05_apply_jobs.py --profile <dir>
       │    │
       │    └─► [ROTATE PHASE]:
       │         └─► SearchStateManager.record_stats() & advance() designation index
       │
       └── time.sleep(delay)  →  Next Cycle (default 30s)
```

─────────────────────────────────────────────────────────────────────────────
[DAEMON 2: IPC Signal Relay]
ipc_watcher.py --profile <dir> --poll 2.0
  │
  ├── Shared Polling Loop (every 2.0s):
  │    ├─► Check profiles/<profile>/output/pending_question.json
  │    │    └── When status == "PENDING":
  │    │         └── Emits immediate stdout signal:
  │    │              [IPC WATCHER] PENDING QUESTION DETECTED: "<Question Text>"
  │    │              [IPC WATCHER] Task Type: SCREENING_QUESTION | Options: [...]
  │    │
  │    └─► Check profiles/<profile>/output/batch_question.json
  │         └── When status == "PENDING":
  │              └── Emits immediate stdout signal:
  │                   [IPC WATCHER] BATCH QUESTION DETECTED: N cards
  │                   [IPC WATCHER] Awaiting batch_answer.json (120s SLA)

─────────────────────────────────────────────────────────────────────────────
[DAEMON 3: AG Brain Cron Monitor]
Cron Heartbeat (* * * * * / 60-second wake-up)
  │
  ├── Check batch_question.json & pending_question.json status
  ├── If batch_question.json status == "PENDING":
  │    ├── Evaluate card batch against candidate profile
  │    └── Write batch_answer.json with [DEEP_SCAN, SKIP] decisions (SLA: <120s)
  │
  └── If pending_question.json status == "PENDING":
       ├── Load candidate resume.md and candidate_config.json
       ├── Synthesize factual grounded response
       ├── Commit JSON answer with status="ANSWERED" (SLA: <90s)
       └── Daemon 1 consumes answer, unlinks file, submits form, resumes loop
```

**IPC Contract:** Scripts communicate via filesystem artifacts:
- `search_manifest.json` — Discovery → Tailoring → Application (enriched with `jd_path`, `description`, and `naukri_match_score`)
- `applications_tracker.csv` — Application → Deduplication (canonical 9-column schema)
- `processed_ledger.json` — Persistent composite key (`clean_company::clean_title`) + Job URL deduplication ledger
- `saved_external_jobs.json` — External redirect storage
- `candidate_config.json` — Self-learning truth cache (read/write by all scripts)
- `batch_question.json` / `batch_answer.json` — Asynchronous Batch Card Evaluation IPC channel between Discovery Engine and AG Brain (120s SLA)
- `pending_question.json` — Asynchronous Single-Query File-Based IPC handshake between Application Engine, IPC Watcher, and AG Brain (90s SLA)
- `search_state.json` — State persistence for `SearchStateManager` designation rotation
- `ques_ans_chatbot.json` — Per-job Q&A audit log stored alongside tailored resumes
- `Job_Description.md` — Raw un-clamped multi-section scraped JD markdown saved to `profiles/<profile>/output/applications/<Company>_<Role>/`
- `job_details.json` — Structured job metadata + `naukri_match_score` saved to `profiles/<profile>/output/applications/<Company>_<Role>/`
- `output/profile_sync/naukri_cards/` — Per-role evaluation cards (`KEEP_EXISTING` / `UPDATE_REQUIRED` / `ADD_NEW`)
- `output/profile_sync/naukri_sync_report.json` — Profile sync execution summary metrics

---

## 3. MODULE-BY-MODULE REFERENCE

### 3.1 `ai_client.py` — Central AI Reasoning Engine

**Classes:**
- `MatchResult(tuple)` — Hybrid result supporting tuple unpacking (`score, reasoning, matching, missing = result`), attribute access (`result.score`), and dict-style lookups (`result['score']`, `result.get('score', 0)`).
- `AIClient` — Gemini Flash + Antigravity 2.0 File-Based IPC dual-brain with portal match score calibration. Multi-key round-robin rotation with automatic fallback across 7 API keys.

**Multi-Key Round-Robin Architecture (v2.0):**
- `gemini_credentials.json` stores an array of API keys: `{"api_keys": ["key1", "key2", ...], "model": "...", "fallback_models": [...], "engine_enabled": true}`.
- At init, `AIClient.__init__` instantiates a `list` of `genai.Client` objects (`self._gemini_clients`), one per key.
- `self.gemini_client` is a `@property` (NOT a static attribute) — it returns `self._gemini_clients[self._current_client_idx]`. **Never assign to `self.gemini_client` directly — it has no setter.**
- `self._rotate_gemini_client()` is called inside the retry loop of `_call_gemini_with_fallback()`. Every failed or completed attempt cycles to the next key, distributing quota across all 7 accounts.
- Context is stateless and passed in the payload — rotation does not break conversation state.
- `SmartRateManager` (see `core/ai_rate_manager.py`) enforces a global 3.5s minimum delay between ALL API calls, and bans individual models for 120s upon receiving a 429 or 503.

**Gemini Inline Batch Engine (Priority 0.5):**
- When `gemini_credentials.json` has `engine_enabled: true` AND a valid `api_keys` list, batch job evaluation is intercepted BEFORE the AG Brain IPC channel.
- `_gemini_batch_evaluate_inline()` processes up to 40 cards per chunk (leveraging Gemini's 1M+ token context), calling `_call_gemini_with_fallback()` and rotating keys per chunk.
- Returns `[{id, decision, reason}]` list, bypassing `batch_question.json` / `batch_answer.json` file IPC entirely.
- Priority chain for batch evaluation: `Colab GPU Engine (engine_enabled=true)` → `Gemini Inline Engine` → `AG Brain File-Based IPC (batch_question.json)`.

**Key Methods:**
| Method | Purpose | Fallback Chain |
|:---|:---|:---|
| `generate_text(...)` | General LLM text generation (profile summary, bullets) | Operational Gemini client → `pending_question.json` File-Based IPC |
| `synthesize_cognitive_profile(...)` | Runtime Cognitive Profile Model synthesis | Gemini LLM → Deterministic Taxonomy Engine → saves to `cognitive_profile.json` |
| `get_active_search_cycle()` | Returns current batch of 5–8 designations | Loads `cognitive_profile.json` → returns active cycle |
| `advance_search_cycle()` | Advances designation batch across discovery sweeps | Increments `active_cycle_index` % cycles → saves `cognitive_profile.json` |
| `evaluate_job_match(...)` | Two-Stage Cognitive Qualification Engine with portal match score calibration (0-100) | Stage 1 Gatekeeper (C6 negative, domain stem, exp band, dynamic incompatible verticals) → Stage 2 Precision (Gemini JSON / IPC 40-65 / Heuristics with min 2 core skills, +10% portal match bonus, $\ge 60\%$ threshold) |
| `arbitrate_card_fit(...)` | Tier 2B Cognitive Card Arbitration (SRP) | Evaluates unfamiliar roles, dynamic acronyms, and card skills $\rightarrow$ Gemini / Heuristics against `cognitive_profile.json` |
| `analyze_and_expand_designations(...)` | Tier 4 Autonomous Starvation Recovery | Analyzes `resume.md` + experience + seen market titles $\rightarrow$ Auto-enriches `candidate_config.json` |
| `evaluate_profile_experience(...)` | Compares live card description with source of truth | Gemini / Heuristics → returns action decision & optimal text |
| `answer_screening_question(...)` | Resolves chatbot questions | Exact cache (`auto_learned_truths`) → Gemini API → Config-driven heuristic (`_heuristic_screening_answer` reads all keyword lists from `screening_heuristics` in `candidate_config.json`) → File IPC polling |
| `_best_option_match(...)` | Maps freeform answer to UI choices | Exact → word-boundary (`\b`) → numeric → boolean → `None` (H1/H2 compliant) |
| `_persist_learned_truth(...)` | Caches verified answers to config | Atomic via `ProfileContext.save_config()` (`.tmp` + `os.replace`) |
| `_fallback_antigravity_ipc(...)` | AG 2.0 Handshake Hook | Writes `pending_question.json` and polls until AG 2.0 fills the `"answer"` key |
| `_gemini_batch_evaluate_inline(...)` | Gemini Inline Batch Engine | Chunks cards (40/batch), calls `_call_gemini_with_fallback()`, rotates keys; bypasses IPC entirely |
| `_call_gemini_with_fallback(...)` | Core Gemini API call with multi-key rotation | Tries `self.gemini_client` → rotates to next key on 429/error → falls back to IPC |
| `_rotate_gemini_client()` | Advances round-robin key index | Cycles `self._current_client_idx` through `self._gemini_clients` list |

**Critical Design Decisions:**
- **Multi-Key Round-Robin:** `gemini_credentials.json` holds an `api_keys` array. `AIClient` builds one `genai.Client` per key. `self.gemini_client` is a `@property` returning the current key's client. `_rotate_gemini_client()` increments the index each retry. Result: free-tier quota multiplied ×N across N accounts.
- **SmartRateManager Pacing:** Global 3.5s floor between API calls prevents chatbot form-field overflow caused by rapid-fire Naukri chatbot questions. Models banned 120s on 429/503 before being retried.
- **Naukri Native Match Score Calibration (Stage 2 Component D):** When `naukri_match_score` (scraped from `div.styles_JDC__match-score__VnjLL`) is provided:
  - If `Keyskills == True` AND `Work Experience == True`: Grants a **+10% verified confidence bonus** to Stage 2 precision score.
  - If `Keyskills == True` (only): Grants a **+5% verified confidence bonus**.
  - If `Work Experience == True` (only): Grants a **+3% verified confidence bonus**.
  - Explanatory notes are automatically appended to `reasoning` (e.g., `[Naukri Portal Verified: Keyskills & Exp Match (+10%), Early Applicant, Location Match]`).
  - Active portal flags are injected into both the Gemini LLM prompt and the Antigravity 2.0 IPC prompt (`pending_question.json`) for factual arbitration.
- **Autonomous Cognitive Profile Synthesis:** At runtime, `AIClient.synthesize_cognitive_profile()` inspects the active candidate's `resume.md` and configuration, derives their domain (e.g. Finance & Accounting, Software Engineering, etc.), core vs. generic soft skills, domain acronyms, out-of-domain incompatible verticals, and multi-cycle designation queues (Cycle 1 core, Cycle 2 seniority/lateral, Cycle 3 specialized/functional) stored in `profiles/<profile>/output/cognitive_profile.json`.
- **Zero-Hardcoding Contract & Guardrail P1:** Zero vertical dictionaries, domain words, soft skill sets, or question-detection keyword lists exist in Python source code. All evaluation gates in `evaluate_job_match()`, `arbitrate_card_fit()`, and `_heuristic_screening_answer()` read dynamically from `cognitive_profile.json` and `candidate_config.json`. Specifically, all screening question keyword lists (notice period, relocation, interview mode, communication, experience, numeric detection, numeric exclusion, intern designation markers, and fallback text label) are stored in the `screening_heuristics` section of `candidate_config.json` — **never** as Python literals. See Section 4.1 for the complete `screening_heuristics` schema.
- **Two-Stage Cognitive Qualification Engine:** Stage 1 Deterministic Gatekeeper enforces C6 absolute negative keywords, domain root-stem token gating (excluding hierarchy stopwords), an **Incompatible Industry/Vertical Hard Gate** (rejecting verticals flagged incompatible by the cognitive profile), and an experience band filter (>3yr gap auto-rejects). Stage 2 Precision scoring enforces a strict 60% qualification bar and requires $\ge 2$ distinct **CORE functional domain skills** (excluding soft skills like "analytical" or "problem solving").
- **Tier 2 Stage 1 Gatekeeper Line-by-Line Job Highlights Gating:** In `evaluate_job_match()`, the engine isolates the `Job Highlights:` section if present. Unlike the general JD body, highlight bullets represent hard qualification criteria and minimum candidate eligibility filters set by the recruiter. The Gatekeeper scans each highlight line-by-line:
  - Any negative keyword match on word boundaries (`\b{kw}\b`) immediately drops the role (`score = 0`, rejection logged).
  - Un-prefixed matching: negative keywords in highlights do NOT require qualification prefix triggers (`"require"`, `"must have"`) because the entire bullet in a highlights section IS an explicit prerequisite.
- **Multi-Bullet Line-by-Line Regex Isolation Standard:** Solves the critical multi-bullet bleed bug. In multiline JD blocks, evaluating regex patterns (such as stakeholder/collaboration exemptions: `re.search(stakeholder_collab_pattern, ...)` across the entire multiline string allowed a collaboration phrase in bullet 2 (e.g. `"coordinate with auditors"`) to falsely exempt a mandatory disqualifying requirement in bullet 1 (e.g. `"Passed CA Intermediate"`). Regex exemption checks MUST be evaluated strictly line-by-line (`for line in highlights_content.splitlines():`) in complete semantic isolation.
- **Duty Header Scraper Classification Standard:** In `_analyze_jd_work_capability()`, `"job highlights"` is strictly excluded from `resp_headers`. Job highlights represent candidate eligibility prerequisites and recruiter criteria, NOT work duties. Classifying highlights as duties falsely awarded positive capability match points to disqualified candidates.
- **Tier 2B Cognitive Card Arbitration:** Evaluates unfamiliar roles, dynamic domain abbreviations, and visible skill chips while strictly rejecting incompatible verticals; does not contaminate candidate configuration with card titles.
- **Tier 4 Autonomous Starvation Recovery:** If 0 jobs are found in a sweep, the Brain analyzes all seen market titles, compares with `resume.md` and candidate's total experience, and expands `candidate_config.json` with high-yield senior designations within the candidate's domain.
- **Zero Terminal Blocking:** Removed `sys.stdin.readline()`. The background daemon will never freeze waiting for terminal input.
- **AG 2.0 File IPC Polling:** Non-blocking polling of `pending_question.json`. Once an answer is detected, it proceeds instantly and unlinks the file.
- **Strict Exact-Match Caching Only:** When checking `auto_learned_truths`, uses strict `key.strip().lower() == question.strip().lower()`.
- **Character Limits:** Automatically trims free-text IPC answers to 250 characters to prevent form-field overflow.

---

### 3.1c `ai_rate_manager.py` — Global Stateful Rate Manager (NEW — v2.0)

**Purpose:** Centralized, globally-instantiated pacing and health-tracking service for all Gemini API interactions.

**Key Behaviors:**
- **Global Floor Pacing:** Enforces a **3.5s minimum delay** between ANY consecutive Gemini API calls. This prevents the Naukri chatbot interaction loop from firing questions too rapidly, which was causing form submission race conditions.
- **Model Health Tracking:** Maintains a per-model ban registry. When a model returns a `429 (Too Many Requests)` or `503 (Service Unavailable)`, `SmartRateManager` bans that model for **120 seconds** before allowing it to be retried.
- **Integration:** Instantiated as a module-level singleton in `ai_client.py`. All API call paths (`_call_gemini_with_fallback()`, `answer_screening_question()`) call `rate_manager.wait_if_needed(model_name)` before dispatching and `rate_manager.record_result(model_name, success=False)` on failure.

---


### 3.1b `02_profile_sync_naukri.py` — Surgical Selective Profile Sync Engine

**The 5-Step Cognitive Selective Workflow:**
1. **Step A (Ground-Truth Ingestion):** Ingests candidate employment history from `resume.md` and `candidate_config.json` (`profile_content.employment`).
2. **Step B (Non-Destructive Live DOM Inspection):** Connects via CDP, navigates to `https://www.naukri.com/mnjuser/profile`, executes mandatory `window.scrollTo(0, 1200)` to mount `#lazyEmployment` and `#lazyKeySkills`, and scrapes live headline, summary, key skills, and employment cards.
3. **Step C (AI Evaluation & Decision Making):** For each candidate experience, compares live portal description against ground-truth resume via `ai_client.evaluate_profile_experience()`. Returns:
   - `KEEP_EXISTING`: Live card is already comprehensive and well-written. Left untouched.
   - `UPDATE_REQUIRED`: Outdated description or missing ATS keywords. Prepared for surgical update.
   - `ADD_NEW`: Role does not exist on live profile. Prepared for addition.
4. **Step D (JSON Evaluation Card Generation):** Saves an individual JSON card for each evaluated role into `profiles/<profile>/output/profile_sync/naukri_cards/<Company>_<Role>.json` documenting live content, optimal content, action decision, and reasoning. Produces `naukri_sync_report.json` with aggregate metrics.
5. **Step E (Surgical Selective Execution via Empirical Form Selectors):** Updates only roles flagged `UPDATE_REQUIRED` or `ADD_NEW` using verified empirical selectors:
   - **Resume Headline**: `.resumeHeadline span.edit.icon` opens modal with `textarea#resumeHeadlineTxt` (250 char limit), cancel `a.cancel-btn`, and save `button.btn-dark-ot`.
   - **Key Skills**: `.keySkills span.edit.icon` opens modal with `.suggester-input input`, adds chips, and saves via `button.btn-dark-ot`.
   - **Employment**: `#lazyEmployment .emp-list` with `span.edit` opens `form#employmentForm` with `textarea#jobDescription`, cancel `a.cancel-btn`, and save `button#submitEmployment`.
   Leaves all `KEEP_EXISTING` cards completely untouched. Syncs resume headline, summary, and uploads tailored PDF.

---

### 3.2 `04_job_discovery.py` — Batched Discovery Engine

**Execution Flow:**
1. Connect to Chrome via CDP at `candidate.cdp_url`
2. Verify codebase purity via `ctx.verify_codebase_purity()` (Guardrail P1)
3. Load persistent dedup ledger (`processed_ledger.json`) + CSV + external JSON; initialize `session_seen_titles = set()`
4. Retrieve active cycle of 5–8 designations via `ai.get_active_search_cycle()`
5. Map candidate preferences into dynamic URL parameters:
   - `wfhType=3` (Remote/WFH), `wfhType=2` (Hybrid), `wfhType=0` (Onsite/Office)
   - `companyJobs=true` (Direct Employers only)
6. Multi-Strategy Search Matrix:
   - Strategy A: Role Only (Broad domain sweep)
   - Strategy B: Company Only (Direct company infiltration)
   - Strategy C: Role AND Company Combined (Precision match)
7. For each (strategy × location × task × page):
   a. Navigate to search results page (SRP) with recency filter (`&jobAge=3` or `&f_TPR=r259200`) and URL parameters
   b. Extract up to 20 job cards per page using granular card selectors:
      - **Job Title**: `a.title` (`title`, `href`, `innerText`)
      - **Company Name**: `a.comp-name`
      - **Rating & Reviews**: `a.rating span.main-2` and `a.review`
      - **Experience**: `span.exp-wrap` / `span.expwdth`
      - **Salary**: `span.sal-wrap` / `span.ni-job-tuple-icon-salary`
      - **Location**: `span.loc-wrap` / `span.locWdth`
      - **Snippet**: `span.job-desc`
      - **Skill Tags**: `ul.tags-gt li.dot-gt.tag-li`
      - **Recency**: `span.job-post-day`
      - **Bookmark**: `span.save-job-tag`
   c. Objective Pre-Gating & Batch Card Evaluation (GATE 11 & Guardrail C24):
      - Python executes strictly objective numeric pre-gates on SRP card metadata:
        - CTC Salary Floor check
        - C24 Card-Level Experience Band Gating (`card_min_exp > cand_exp + max_experience_gap_years` → `experience_gap_gated`)
        - Exact Company Blacklist Match
      - `is_title_allowed()` function body is retained as deprecated dead code (Rule GATE 11); Python does not execute keyword semantic gating in the discovery loop.
      - Qualified cards are accumulated into `batch_question.json` and sent to AG Brain in a single batch IPC call (120s SLA) returning `[DEEP_SCAN, SKIP]` decisions.
   d. Deep scan detail page (DEEP_SCAN approved cards only):
      - Check for native apply (`#apply-button`) vs external redirect (`#company-site-button`)
      - **Tier 1 Scraper Pre-Flight Highlights Gating (Fast Rejection):**
        - Extracts raw highlight strings from `ul.styles_JDC__job-highlight-list__QZC12 li` immediately upon page load.
        - Evaluates each highlight line against `candidate_config.json["target_jobs"]["negative_keywords"]` using word-boundary regex (`\b{kw}\b`).
        - If any negative keyword matches: logs `[HIGHLIGHTS GATED: Negative keyword '{kw}' in highlight: '{text}']`, writes `domain_gated` to `processed_ledger.json`, closes detail tab, and short-circuits.
        - Bypasses unnecessary un-clamping, Native Match Score scraping, and LLM evaluation, saving ~1.5s per disqualified page.
      - **Un-clamp "Read More"** (`span.styles_rm-link__RgrMs`), expanding hidden responsibilities and benefits from 3.4k to 7.2k+ characters (Guardrail C12)
      - **Scrape Naukri Native Match Score** (`div.styles_JDC__match-score__VnjLL`, checking `i.ni-icon-check_circle` vs `i.ni-icon-crossMatchscore` for Early Applicant, Keyskills, Location, Work Experience) (Guardrail C13)
      - Assemble multi-section description: Highlights, Description, Read More, Specifications, Education, and Key Skills
   e. Two-Stage AI score evaluation passing `naukri_match_score` $\rightarrow$ qualify only if `score >= 60`
   f. Write `Job_Description.md` and `job_details.json` (including `naukri_match_score`) to application folder
   g. Append enriched job entry to `search_manifest.json`
   h. When batch reaches BATCH_SIZE=1: trigger tailoring → upload → apply pipeline
8. Resume discovery sweep & advance search cycle via `SearchStateManager.advance()`

**Naukri Canonical Structured SEO Slug Standard (Rule C17):**
```
https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}?jobAge={days}&experience={years}&ctcFilter={bracket}
```
Pagination (Page 2+):
```
https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}-{page_num}?jobAge={days}&experience={years}&ctcFilter={bracket}
```
*(Note: As documented in `platform_heuristics.json:15-19`, generic `/jobs?k=...` URLs are strictly PROHIBITED as Naukri's server automatically redirects them to `/jobs-in-india?k=...`, which collapses the `.srp-jobtuple-wrapper` components and returns 0 vacancies. Canonical structured SEO slugs with dynamic query parameters reliably return 20 job cards per page).*

**Naukri 3-Field Header Search Bar Protocol (UI Automation):**
When navigating via in-browser UI form interaction (`execute_naukri_header_search()`):
1. **Collapsed Trigger:** Detects and clicks `button.nI-gNb-sb__expand[aria-label="Search jobs here"]` to toggle `.nI-gNb-sb__main--expand`.
2. **Campus vs Standard Switching:**
   - On **Standard Naukri**: Field 1 is Keywords, Field 2 is Experience (`#experienceDD`), Field 3 is Location.
   - On **Naukri Campus** (`is_naukri_campus()`): Field 1 is Job Type (`input#jobType` with options `Job` [`ajob`] or `Internship` [`ainternship`]), Field 2 is Keywords, Field 3 is Location.
   - For internships, applies parameters: `qinternshipFlag=true`, `qproductJobSource=2`, and `naukriCampus=true`.
3. **Field 1 / Keywords (Zero-Comma Standard):** Enters sanitized search term into `.nI-gNb-sb__keywords input.suggestor-input` (`placeholder="Enter keyword / designation / companies"`). All commas, semicolons, and special punctuation must be stripped before typing. Commas produce `%2C` query tokens that Naukri evaluates as literal `"2c"`, causing total zero-result failure.
4. **Suggestor Auto-Comma Cleanup:** Clicking suggestion chips in Naukri's suggestor dropdown automatically inserts `", "` into the field. Automation must strip this trailing comma before submitting.
5. **Field 2 / Experience (Standard):** Clicks `input#experienceDD` to open `ul.dropdown`. Selects `li[value='a{exp}']` (`a0` for fresher, `a1` for 1 yr, up to `a30` for 30 yrs).
6. **Field 3 / Location (Zero-Comma Standard):** Enters sanitized location into `.nI-gNb-sb__location input.suggestor-input` (`placeholder="Enter location"`), ensuring no trailing commas or state designations (e.g., `"Bangalore"`, never `"Bangalore, Karnataka"`).
7. **Search Submission:** Clicks `button.nI-gNb-sb__icon-wrapper` (`aria-label="Search"`). Generates unified canonical URL with `nignbevent_src=jobsearchDeskGNB`.

**Campus Multi-Attribute Duplicate Prevention Protocol (Rule C16):**
In `02_profile_sync_naukri.py`, duplicate evaluation strictly enforces a 3-way match:
- `Company + Designation + Years/Tenure`.
- If candidate worked at the same company in the same role across different years (e.g. 2022 vs 2024), it is strictly recognized as a separate legitimate stint (`ADD_NEW` / independent card evaluation) and must not be overwritten or skipped.
- When `#internshipDetails_Modal` is open on Naukri Campus, scrolling is container-isolated to `document.querySelector('#internshipDetails_Modal').scrollTop` to prevent background page scroll leaks.

---

### 3.3 `05_apply_jobs.py` — Application Engine

**Two Main Classes:**

#### `ChatbotResolver` — DOM Chatbot Reverse-Engineering
- **Question Extraction:** Iterates `li.botItem .botMsg` elements in reverse, filtering greetings containing candidate name.
- **Control Detection Priority:** `FILE_UPLOAD` → `DATE_INPUT` → `RADIO_CHIP` (chips, toggle pills, custom radios, excluding `.chipMsg`) → `DROPDOWN` → `CONTENTEDITABLE` → `UNKNOWN`.
- **Contenteditable React Protocol:** Click → Ctrl+A → Backspace → `page.keyboard.insert_text(answer)` → native `document.execCommand('insertText')` → manual `dispatchEvent` (Input/Change/Keydown/Keyup) → forcefully remove `.disabled` class and `disabled` attribute from Send/Submit button.
- **Empirical Radio Selection:** Targets exact Naukri radio/checkbox label containers (`label.ssrc__label`, `input.ssrc__radio`, `input.ssrc__checkbox`) to reliably trigger React event listeners and enable the submission container.
- **Chatbot Drawer Submit Scoping:** Submissions target `.sendMsgbtn_container .send:not(.disabled) .sendMsg` strictly scoped within `get_drawer()`, preventing background page bookmark click interference.
- **Platform Rejection Banner Detection (Guardrail C9):** Checks for platform rejection banners and aborts immediately (`FAILED_PLATFORM_REJECTED`).
- **Premature Drawer Closure Detection (Guardrail C9):** Detects unmounted or dismissed chatbot drawers (`not resolver.is_drawer_open()`), verifies completion, and aborts immediately (`DRAWER_CLOSED`).
- **Zero-Experience Screening Circuit-Breaker (Rule C18):** If candidate answers `0` to a screening question targeting a core technology named in the job title (e.g. `SAP BTP`), the engine immediately aborts the questionnaire (`REJECTED_ZERO_EXPERIENCE_SCREENING`) and closes the drawer without submitting.
- **External Redirect Save Bookmark Standard (Rule C18):** When external employer redirects are detected (`"Apply on company website"`), clicks the native `Save` button (`button:has-text('Save')`) on Naukri to bookmark the role before recording as `REDIRECT_EXTERNAL`.
- **3x Stuck Question Loop Breaker (Guardrail C7):** Aborts on 3 repeated questions without progress.
- **Adaptive Answer Formatter:** Automatically formats repeated screening answers (e.g. `9` -> `9 years` or `30` -> `30 Days`) based on question semantics to pass frontend portal validation.

#### `LinkedInApplyHandler` — Native LinkedIn Easy Apply Modal Automation
- **Modal Detection & Container Scoping:** Identifies `div.jobs-easy-apply-modal` without background interference.
- **Dynamic Field Resolution:** Resolves phones, text inputs, radio groups, dropdowns, and uploads tailored ATS PDF resumes.
- **Modal Stepping & State Progression:** Advances through "Next", "Review", and commits via "Submit application".
- **Safe Dismissal:** Calls `discard_and_close_modal()` on unresolvable fields without leaving dangling modals.
  - Phone inputs: `input[id*='phoneNumber']`, auto-populated from `candidate.phone`.
  - Text/Numeric inputs: Question text extracted from preceding `label` or `legend` $\rightarrow$ resolved via `AIClient.answer_screening_question()`.
  - Radio groups & single-selects: Options mapped via `_best_option_match()` and clicked.
  - Dropdown selects: Handles standard HTML `<select>` and custom LinkedIn dropdown wrappers.
  - Resume attachment: Automatically injects tailored PDF into `input[type='file']` if an upload step appears.
- **Modal Stepping & State Progression:** Repeatedly clicks "Next" or "Review" buttons until the "Submit application" button appears.
- **Confirmation & Error Handling:** Validates submission via `.artdeco-modal__header:has-text('Application sent')` or dialog dismissal; discards modal cleanly if unresolvable mandatory fields are encountered.

#### `ApplicationEngine` — Batch Orchestrator
- **Status Flow:**
  ```
  Navigate → External Check → Already Applied Check → Click Apply (Naukri or LinkedIn)
       ↓                                                    ↓
  REDIRECT_EXTERNAL                               Poll for Drawer / Modal
       ↓                                           ↓                     ↓
  SKIPPED_ALREADY_APPLIED                    Drawer / Modal Open    No Drawer / Modal
                                                ↓                        ↓
                                         Chatbot / Modal Loop      Check Banners
                                              ↓                        ↓         ↓
                                     APPLIED_CHATBOT / APPLIED_EASYAPPLY  APPLIED_1CLICK  FAILED
  ```
- **Critical Safety:** The `FAILED` return is the default when no confirmation is found. `APPLIED_1CLICK` strictly requires explicit success banner DOM match or redirect URLs (`/myapply/saveApply`, `myapply/historypage`). `check_completion_status()` strictly requires text markers; missing drawer is never treated as completion.

---

### 3.4 `generate_factual_tailored.py` — Resume Tailoring & PDF

**Algorithm:**
1. Parse `resume.md` into sections via markdown heading regex (`^#{1,4}\s+`)
2. Ingest real JD text from `manifest_jd_path` or application folder `Job_Description.md` (never defaults to `f"{title} at {company}"` when JD exists)
3. Extract JD keywords: upgraded technical token regex `r'[a-z0-9]+(?:\+\+|#)?|[.][a-z0-9]+|[a-z0-9]+(?:[/\-.][a-z0-9]+)+'` preserving technical terms like `C++`, `.NET`, `K8s`, `SAP S/4HANA`, `Dynamics 365`, `SQL`, `Python3`, `C#`
4. Score each bullet: pre-compiled word-boundary regex (`\b`) eliminates substring collisions (`"art"` vs `"smart"`)
5. Stable-sort bullets within each section by `(-score, idx)` to preserve original order on ties
6. Reassemble markdown → convert to HTML via `markdown` library → wrap in ATS-compliant CSS template
7. Render PDF via Playwright's `page.pdf()` using Chrome's print engine

---

### 3.5 `profile_context.py` — Multi-User Sandbox Manager (166 lines)

**Profile Resolution Hierarchy:**
1. Explicit `profile_path` parameter
2. CLI `--profile <path>` argument
3. Auto-discover: first valid candidate subdirectory in `profiles/` with `candidate_config.json` (strictly excluding `default_user`, which serves as the immutable template blueprint)

**Atomic Save Protocol:**
```python
tmp_path = config_path.with_name(config_path.name + ".tmp")
write to tmp_path
os.replace(tmp_path, config_path)  # Atomic on all OSes
```

---

### 3.6 `browser_manager.py` — CDP Lifecycle Manager (76 lines)

- Connects to existing Chrome instance via `chromium.connect_over_cdp(cdp_url)`
- Reuses `browser.contexts[0]` for cookie/session persistence
- `new_page()` reuses `context.pages[0]` if available, brings to foreground
- Does NOT terminate Chrome on `.close()` — only stops Playwright

**Architectural Note:** Currently only `05_apply_jobs.py` uses `BrowserManager`. All other scripts create their own `sync_playwright()` contexts directly. This causes redundant CDP connections and potential tab hijacking.

---

### 3.7 `continuous_career_agent.py` — Daemon Orchestrator (64 lines)

- Infinite `while True` loop running `04_job_discovery.py` via `subprocess.run()`
- Optional `--sync-profile` flag triggers `02_profile_sync_naukri.py` and `03_profile_sync_linkedin.py` before the loop
- Configurable `--delay` between cycles (default: 30 seconds)
- `KeyboardInterrupt` for clean shutdown

---

### 3.8 `ipc_watcher.py` — Daemon 2: Asynchronous IPC Signal Relay (142 lines)

- Dedicated background process running concurrently with `continuous_career_agent.py`.
- **Purpose**: Acts as an un-buffered bridge between Daemon 1 (running the Playwright application engine) and Daemon 3 (AG Brain).
- **Execution**:
  ```bash
  python core/ipc_watcher.py --profile profiles/<profile_name> --poll 2.0
  ```
- **Operational Mechanics**:
  1. Polls `profiles/<profile_name>/output/pending_question.json` at a configurable interval (default 2.0 seconds).
  2. Detects files where `"status": "PENDING"` and `"answer": null`.
  3. Formats and prints a loud, structured ASCII alert block to `stdout` containing:
     - Timestamp (`HH:MM:SS`)
     - `TASK_TYPE` (`SCREENING_QUESTION`, `PROFILE_SYNTHESIS`, `RESUME_TAILORING`, `JOB_EVALUATION`, `STARVATION_EXPANSION`)
     - `CONTROL_TYPE` (`RADIO_CHIP`, `CONTENTEDITABLE`, `DROPDOWN`, `FILE_UPLOAD`, `DATE_INPUT`)
     - `QUESTION` text and optional `OPTIONS` list
     - `FULL_PROMPT` snippet for AG Brain context
  4. De-duplicates logs so the same question is printed once per occurrence (`last_printed_ts`), avoiding log flooding.
  5. Emits periodic heartbeat logs every 30 polling iterations (`Heartbeat: waiting for pending question...`).
- **Zero API / Zero Hardcoding**: Contains no external AI API dependencies and zero candidate PII. Serves purely as a transparent signal relay.

---

## 4. DATA SCHEMA REFERENCE

### 4.1 `candidate_config.json` Schema
```json
{
  "candidate": {
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "pincode": "string",
    "total_experience_years": 0,
    "current_ctc_lpa": 0,
    "expected_ctc_lpa": 0,
    "notice_period_days": 0,
    "resume_filename": "Target_Resume.pdf",
    "cdp_url": "http://127.0.0.1:9222",
    "linkedin_profile_url": "string"
  },
  "target_jobs": {
    "keywords": ["keyword1", "keyword2"],
    "negative_keywords": ["Sales", "Intern"],
    "locations": ["City1", "City2"],
    "platforms": ["Naukri", "LinkedIn"],
    "experience_years": 0,
    "salary_filter_bracket": "10-20 LPA",
    "max_applies_per_day": 50
  },
  "taxonomy_skills": {
    "Domain Skills": ["skill1", "skill2"],
    "Technical Skills": ["tool1", "tool2"]
  },
  "ats_answers": {
    "notice_period": "N Days",
    "current_ctc_lakhs": 0,
    "expected_ctc_lakhs": 0,
    "skill_years_experience": { "Skill1": 0 }
  },
  "auto_learned_truths": {
    "exact question text": "cached answer"
  },
  "screening_heuristics": {
    "standard_screening_patterns": ["notice period", "willing to relocate", "mode of interview", "communication", "total experience"],
    "notice_period_keywords": ["notice period", "last working day", "serving notice", "joining time"],
    "notice_numeric_detect_keywords": ["how many days", "days notice", "notice in days", "number of days"],
    "notice_numeric_exclusion_keywords": ["immediate", "immediately", "currently serving", "relieved"],
    "notice_option_match_keywords": ["30 days", "60 days", "90 days", "immediate", "1 month", "2 months", "3 months", "more than 3 months"],
    "relocation_keywords": ["relocate", "relocation", "willing to move", "open to relocate", "shift to", "move to"],
    "interview_keywords": ["mode of interview", "interview mode", "preferred interview", "interview type", "interview preference"],
    "interview_virtual_keywords": ["virtual", "video", "online", "remote interview", "zoom", "teams", "google meet"],
    "interview_f2f_keywords": ["face to face", "f2f", "in person", "onsite interview", "in-person", "physical interview"],
    "interview_virtual_options": ["virtual", "video", "online"],
    "communication_keywords": ["fluent comms", "fluent communication", "communication skills", "communication level", "language proficiency", "english communication"],
    "communication_positive_options": ["fluent", "excellent", "native", "proficient", "advanced"],
    "total_experience_keywords": ["total experience", "total years", "overall experience", "years of total", "total work experience"],
    "months_format_keywords": ["in months", "(months)", "(in months)", "number of months", "months of experience", "months experience"],
    "skill_experience_keywords": ["years of experience", "how many years", "experience do you have", "hands-on experience", "experience in months", "months of experience", "describe your experience", "explain your experience", "tell us about your experience", "experience in ", "experience with "],
    "numeric_question_triggers": ["how many years", "years of experience", "experience in years", "number of years", "how long", "in numbers", "in digits", "enter digits", "enter numbers"],
    "numeric_question_exclusions": ["describe", "explain", "detail", "tell us", "write about", "elaborate"],
    "intern_designation_markers": ["intern", "trainee", "apprentice", "graduate trainee"],
    "fallback_text_label": "experience"
  }
}
```

> **`screening_heuristics` is the zero-hardcoding enforcement section.** All keyword lists used by `_heuristic_screening_answer()` and `_is_standard_screening_query()` in `ai_client.py` are read exclusively from this config block. Python source code contains **zero** inline keyword literals for question detection. To tune screening behavior, edit config — never Python.
>
> **`fallback_text_label`** controls the word used when drafting experience descriptions (e.g. `"experience as Senior Associate at TCS"` instead of `"internship as ..."`). Default: `"experience"`.
>
> **`numeric_question_exclusions`** intentionally does **not** contain `"projects"` — this fixes the bug where `"How many years of BFSI projects?"` was incorrectly routed to text path instead of integer path.



### 4.2 `search_manifest.json` Schema
```json
[
  {
    "title": "Job Title",
    "company": "Company Name",
    "location": "City",
    "url": "https://www.naukri.com/job-listings-...",
    "platform": "naukri",
    "score": 85,
    "jd_path": "profiles/<profile>/output/applications/<Company>_<Role>/Job_Description.md",
    "description": "Full un-clamped job description text scraped from detail page...",
    "naukri_match_score": {
      "Early Applicant": true,
      "Keyskills": true,
      "Location": true,
      "Work Experience": true
    }
  }
]
```

### 4.2b `job_details.json` Schema (Per-Application Metadata)
```json
{
  "title": "Job Title",
  "company": "Company Name",
  "location": "City",
  "url": "https://www.naukri.com/job-listings-...",
  "platform": "naukri",
  "score": 85,
  "match_reasoning": "Reasoning string with portal confidence bonus notes...",
  "matching_skills": ["Skill1", "Skill2"],
  "missing_skills": ["Skill3"],
  "naukri_match_score": {
    "Early Applicant": true,
    "Keyskills": true,
    "Location": true,
    "Work Experience": true
  },
  "scraped_at": "2026-09-09 13:30:00"
}
```

### 4.3 `applications_tracker.csv` Schema (Current)
```
Date,Company,Job Title,Platform,Job URL,Match Score,Status,Tailored Resume PDF,Notes
```

### 4.4 `applications_tracker.csv` Schema (Legacy — must still be parseable)
```
Date,Company,Role,Location,Platform,Status,FolderPath
```

### 4.5 `saved_external_jobs.json` Schema
```json
[
  {
    "job_title": "string",
    "company": "string",
    "platform": "naukri",
    "original_url": "https://...",
    "redirect_url": "https://...",
    "saved_at": "2026-08-31 02:36:40"
  }
]
```

### 4.6 `pending_question.json` Schema (Antigravity 2.0 Zero-API File IPC)
```json
{
  "task_type": "PROFILE_SYNTHESIS | JOB_EVALUATION | RESUME_TAILORING | SCREENING_QUESTION | STARVATION_EXPANSION",
  "question": "Human-readable description or extracted portal question",
  "prompt": "Full context-rich LLM prompt",
  "options": ["Optional list of choices for dropdowns / radio chips"],
  "control_type": "CONTENTEDITABLE | RADIO_CHIP | DROPDOWN | DATE_INPUT | FILE_UPLOAD | UNKNOWN",
  "created_at": "2026-09-04 14:30:00",
  "status": "PENDING",
  "answer": null
}
```

### 4.7 `cognitive_profile.json` Schema (Synthesized Cognitive Model)
```json
{
  "candidate_domain": "Financial Services & Accounting Operations",
  "primary_title": "Senior Manager - Accounts & Finance",
  "years_of_experience": 11.0,
  "seniority_level": "Senior Manager / Associate Director",
  "core_domain_skills": ["Financial Reporting", "Statutory Audit", "Taxation", "SAP S/4HANA", "IFRS"],
  "generic_soft_skills": ["Analytical", "Problem Solving", "Team Leadership", "Communication"],
  "domain_acronyms": {
    "AR": "Accounts Receivable",
    "AP": "Accounts Payable",
    "GL": "General Ledger"
  },
  "incompatible_verticals": {
    "Software Engineering": ["developer", "react", "frontend", "backend", "full stack"],
    "Pharmaceutical R&D": ["clinical trial", "formulation", "pharmacovigilance"]
  },
  "search_cycles": [
    ["Senior Finance Manager", "Lead Accountant", "Financial Controller"],
    ["Associate Director Finance", "Head of Accounts", "VP Finance"],
    ["Statutory Compliance Manager", "Internal Audit Lead", "Treasury Manager"]
  ],
  "active_cycle_index": 0,
  "last_synthesized": "2026-09-04 14:30:00"
}
```

### 4.8 `naukri_cards/<Company>_<Role>.json` Schema (Selective Evaluation Card)
```json
{
  "platform": "naukri",
  "company": "Company Name",
  "designation": "Role Title",
  "naukri_card_keyword": "Keyword",
  "action_decision": "KEEP_EXISTING | UPDATE_REQUIRED | ADD_NEW",
  "decision_reasoning": "Reasoning explaining ATS keyword alignment or role completeness",
  "live_content": {
    "designation": "Role Title",
    "company": "Company Name",
    "tenure": "2022 - Present",
    "description": "Live scraped profile card text..."
  },
  "source_content": {
    "designation": "Role Title",
    "company": "Company Name",
    "description": "Ground truth resume text..."
  },
  "optimal_content": {
    "designation": "Role Title",
    "company": "Company Name",
    "description": "Selected ATS-optimal text..."
  },
  "diff_detected": true,
  "evaluated_at": "2026-09-09 10:30:00"
}
```

### 4.9 `naukri_sync_report.json` Schema (Profile Sync Aggregate Report)
```json
{
  "timestamp": "2026-09-09 10:30:00",
  "total_evaluated": 3,
  "retained_optimal": 2,
  "updated": 1,
  "added_new": 0,
  "cards": [ /* array of evaluated card objects */ ]
}
```

### 4.10 `processed_ledger.json` Schema (Composite Deduplication Ledger)
```json
{
  "https://www.naukri.com/job-listings-...": {
    "title": "Job Title",
    "company": "Company Name",
    "score": 75,
    "status": "qualified | rejected | domain_gated | external_apply | applied_chatbot | applied_1click",
    "timestamp": "2026-09-18 23:09:19"
  },
  "naukri:<numeric_job_id>": {
    "title": "Job Title",
    "company": "Company Name",
    "score": 75,
    "status": "qualified | domain_gated",
    "timestamp": "2026-09-18 23:09:19"
  },
  "<clean_company>::<clean_title>": {
    "status": "composite_qualified | composite_rejected | domain_gated",
    "timestamp": "2026-09-18 23:09:19"
  }
}
```
> **Composite Key Deduplication Rule:** The ledger uses $O(1)$ dictionary lookups supporting `clean_company::clean_title` (`re.sub(r'[^a-z0-9]', '', company.lower()) + '::' + re.sub(r'[^a-z0-9]', '', title.lower())`) to prevent re-applying to the exact same role across multiple discovery runs or locations, while strictly forbidding solitary bare titles (`"Accountant"`) from ever being stored as keys (preventing market starvation).

---

## 5. EMPIRICAL NAUKRI DOM ANATOMY CATALOG

### 5.1 Search Results Page (SRP) Component Catalog

```
div.srp-jobtuple-wrapper (article.jobTuple, data-job-id="<id>")
├── a.title                                   ← Job Designation / Role Title
├── a.comp-name                               ← Employer Company Name
├── a.rating span.main-2                      ← Glassdoor/AmbitionBox Star Rating
├── a.review                                  ← Total Review Count
├── span.exp-wrap (i.ni-job-tuple-icon-srp-experience) ← Required Experience Band
├── span.sal-wrap (span.ni-job-tuple-icon-salary)     ← Stated Salary Bracket
├── span.loc-wrap (i.ni-job-tuple-icon-srp-location)   ← Job Location
├── span.job-desc                             ← Clamped Preview Snippet
├── ul.tags-gt                                ← Key Skills Tag Container
│   └── li.dot-gt.tag-li                      ← Individual Skill Chip
├── span.job-post-day                         ← Posting Recency ("1 day ago")
└── span.save-job-tag                         ← Bookmark / Save Icon
```

*Pagination Container:* `div.styles_pagination-cont__sWhS6` (`#lastCompMark`), previous `a.styles_previous__PobAs`, next `a.styles_btn-secondary__2AsIP:not(.styles_previous__PobAs)`, page links `div.styles_pages__v1rAK a`.

---

### 5.2 Job Details (JD) Page Anatomy

```
.styles_jhc__header__P1S8O (Header Container)
├── h1.styles_jd-header-title__rZwM1          ← Job Title
├── .styles_jd-header-comp-name__MvqAI a       ← Company Name
├── span.styles_amb-rating__4UyFL             ← Company Rating
├── div.styles_jhc__exp__k_giM span           ← Experience Requirement
├── div.styles_jhc__salary__jdfEC span        ← Compensation Bracket
└── div.styles_jhc__location__W_pVs a         ← Work Location

div.styles_JDC__match-score__VnjLL (Naukri Native Match Score Container)
└── div.styles_MS__details__iS7mj (4 evaluation items)
    ├── Early Applicant: i.ni-icon-check_circle (Matched) | i.ni-icon-crossMatchscore (Unmatched)
    ├── Keyskills:       i.ni-icon-check_circle (Matched) | i.ni-icon-crossMatchscore (Unmatched)
    ├── Location:        i.ni-icon-check_circle (Matched) | i.ni-icon-crossMatchscore (Unmatched)
    └── Work Experience: i.ni-icon-check_circle (Matched) | i.ni-icon-crossMatchscore (Unmatched)

div.styles_read-more__TFiRZ (Clamped Description Container)
├── ul.styles_JDC__job-highlight-list__QZC12   ← Job Highlights bullet points
├── div.styles_JDC__dang-inner-html__h0K4t    ← Primary Job Description HTML
└── span.styles_rm-link__RgrMs                 ← "Read More" trigger (un-clamps -webkit-line-clamp: 5)

div.styles_other-details__oEN4O               ← Role Specifications (Role, Industry, Department)
div.styles_education__KXFkO                   ← Education Requirements (UG / PG)
div.styles_key-skill__GIPn_ a span             ← Deduplicated Key Skill Chips
button#apply-button                           ← Native 1-Click / Chatbot Apply Trigger
button#company-site-button                    ← External Redirect Portal Trigger
```

---

### 5.3 Chatbot Drawer DOM Anatomy

```
.chatbot_DrawerContentWrapper (or div[class*='chatbot_Drawer'], div[class*='_chatbotContainer'])
├── .chatbot_MessageContainer (scrollable message list)
│   ├── li.botItem .botMsg                     ← Recruiter questions
│   ├── li.userItem .userMsg                   ← Candidate responses
│   └── ...
├── div.textArea[contenteditable]              ← Free-text input container
├── .singleselect-radiobutton-container        ← Single-select radio wrapper
│   └── .ssrc__radio-btn-container
│       ├── input.ssrc__radio                  ← Native radio input
│       └── label.ssrc__label                  ← Explicit click target for option selection
├── .multiselect-checkbox-container            ← Multi-select checkbox wrapper
│   └── .ssrc__checkbox-btn-container
│       ├── input.ssrc__checkbox               ← Native checkbox input
│       └── label.ssrc__label                  ← Explicit click target for multi-select
├── div.radioItem / div.choiceChip             ← Custom choice chips (excluding .chipMsg)
├── input[type='date']                         ← Date inputs
├── input[type='file']                         ← Resume upload (input#attachCV)
├── select                                     ← HTML dropdown
└── .sendMsgbtn_container
    └── .send:not(.disabled) .sendMsg          ← Scoped submit button (tabindex="0" div)
```

---

### 5.4 Profile Page & Edit Modals DOM Anatomy

```
https://www.naukri.com/mnjuser/profile
├── .resumeHeadline
│   ├── span.edit.icon                         ← Edit Headline Trigger
│   ├── textarea#resumeHeadlineTxt             ← Headline Textarea (250 char limit)
│   ├── a.cancel-btn                           ← Cancel Trigger
│   └── button.btn-dark-ot                     ← Save Trigger
├── .keySkills
│   ├── span.edit.icon                         ← Edit Key Skills Trigger
│   ├── .suggester-input input                 ← Skill Suggester Input Field
│   ├── .chip                                  ← Selected Skill Chips
│   └── button.btn-dark-ot                     ← Save Trigger
├── #lazyEmployment .emp-list
│   ├── span.edit                              ← Edit Employment Trigger
│   └── form#employmentForm                    ← Employment Modal Form
│       ├── input#designationSugg              ← Designation Input
│       ├── input#companySugg                  ← Company Input
│       ├── textarea#jobDescription            ← Job Description Textarea
│       ├── form#employmentForm a.cancel-btn   ← Cancel Trigger
│       └── button#submitEmployment            ← Save Trigger
└── li.collection-item.typ-14Medium            ← 11 Left Navigation Quick Links
```

**Selector Fragility:** Naukri uses CSS Modules with build-hash suffixes (e.g., `__h0K4t`, `__WbS2i`). These change on every Naukri deployment. Always provide robust un-hashed fallback selectors scoped to container parents.

---

## 6. ANTI-DETECTION BEHAVIORAL STANDARDS

| Parameter | Value | Purpose |
|:---|:---|:---|
| Keystroke Delay | 30ms per character | Eliminates robotic typing signature |
| Pre-Click Pause | 200-500ms | Simulates human visual scanning |
| Post-Answer Wait | 2500ms | Allows DOM/WebSocket to propagate next question |
| Inter-Job Cooldown | 2s between applications | Prevents rate-limiting |
| Batch Cycle Sleep | Configurable (default 30s) | Emulates human session pacing |
| CDP Session | Reuse authenticated Chrome | Bypasses bot detection via real fingerprints |
| Navigation Mode | `domcontentloaded` | Avoids hanging on Naukri's persistent WebSockets |

---

## 7. FAILURE MODE REFERENCE

| Failure Scenario | Current Behavior | Expected Behavior |
|:---|:---|:---|
| Candidate data in core/*.py | Fatal halt via `verify_codebase_purity()` | [PASS] Correct (Guardrail P1) |
| Lazy-loaded DOM not mounted | Pre-inspection `window.scrollTo(0, 1200)` hydrates cards | [PASS] Correct (Guardrail C11) |
| JD text truncated to 5 lines | Click `span.styles_rm-link__RgrMs` un-clamps full text | [PASS] Correct (Guardrail C12) |
| Portal match score ignored | Scrapes `div.styles_JDC__match-score__VnjLL`, awards +10% bonus | [PASS] Correct (Guardrail C13) |
| Profile edit modal targets fragile | Uses verified IDs (`#resumeHeadlineTxt`, `#submitEmployment`) | [PASS] Correct (Guardrail C14) |
| Chatbot submit clicked background | Strictly scoped to `.sendMsgbtn_container .send .sendMsg` | [PASS] Correct (Guardrail C10) |
| Gemini API key missing | Dispatches to `pending_question.json` File-Based IPC | [PASS] Correct (H6 compliant) |
| Gemini API rate limited | Dispatches to `pending_question.json` File-Based IPC | [PASS] Correct (H6 compliant) |
| CDP Chrome not running | Pre-flight check detects port 9222 down, logs instructions | [PASS] Correct |
| Naukri selector hash changed | Uses robust un-hashed fallback selectors | [PASS] Handled |
| Chatbot drawer never opens | Returns FAILED | [PASS] Correct (C1 compliant) |
| Unknown form control type | Scans interactive chips or dispatches to File IPC | [PASS] Correct (Bug 4 fix) |
| Active question stuck 3x | Halts loop, logs REQUIRES_MANUAL_INTERVENTION | [PASS] Correct (C7 breaker) |
| `candidate_config.json` write | Atomic write via .tmp + os.replace | [PASS] Correct (C4 compliant) |
| PDF generation crashes | check=True aborts application | [PASS] Correct (H6 compliant) |
| All chatbot iterations exhausted | Checks completion, returns FAILED if not done | [PASS] Correct (C3 compliant) |
| Hardcoded keyword lists in `ai_client.py` | Fatal halt via `verify_codebase_purity()` | [PASS] Fixed — all keyword lists moved to `screening_heuristics` in config (v4.0) |
| `"internship"` word in experience fallback | Caused `"internship as Senior Associate"` hallucination | [PASS] Fixed — `fallback_text_label: "experience"` in config; Python reads `sh.get("fallback_text_label", "experience")` |
| `"projects"` in `numeric_question_exclusions` | Blocked `"How many years of BFSI projects?"` from integer path | [PASS] Fixed — `"projects"` removed from config exclusion list (v4.0) |
| Multi-bullet collaboration regex bleed | Collaboration regex in bullet 2 blinded negative keyword in bullet 1 | [PASS] Fixed — Multi-bullet line-by-line regex isolation evaluates each bullet independently (v5.0) |
| Highlights classified as responsibilities | Highlights parsed as work duties, awarding positive capability points | [PASS] Fixed — `"job highlights"` removed from `resp_headers` in `_analyze_jd_work_capability()` (v5.0) |
| Job Highlights not scanned before unclamp | Full JD loaded and un-clamped before negative qualification was caught | [PASS] Fixed — Tier 1 Scraper Pre-Flight Gating scans `ul.styles_JDC__job-highlight-list__QZC12 li` immediately on page load (v5.0) |
| Stale runner process memory on code edit | Long-running runner daemon ran old Python bytecode in Windows RAM | [PASS] Fixed — Three-Daemon operational architecture mandates graceful restart of runner daemon on engine code updates (v5.0) |
| Chatbot question 90s SLA timeout | Novel screening question risked timing out during background runs | [PASS] Fixed — Three-Daemon Architecture (Daemon 2 `ipc_watcher.py` + Daemon 3 1-min cron monitor) answers questions within SLA (v5.0) |
| Standalone generic negative keyword false positives | Standalone generic nouns (`"Software"`) matched legitimate tools (`"Accounting Software"`), falsely disqualifying valid finance roles | [PASS] Fixed — Composite Term Standard mandates role-specific phrases (`"Software Engineer"`, `"Software Developer"`) in `negative_keywords` (Guardrail C31) |
| Syndicated portal redirect hangs | `page.goto()` hung indefinitely on slow/dead third-party syndicated URLs (Purview India, Leading Client) | [PASS] Fixed — Two-Stage Fallback (`commit` [60s] + `domcontentloaded` [75s]) catches timeout cleanly, logs FAILED, and advances pipeline without crashing (Guardrail C32) |
| Chatbot screening tool hallucinations | Open-ended chatbot questions regarding unverified ERPs/tools risked model hallucinations | [PASS] Fixed — Free-Text Screening Ground Truth Standard strictly bounds answers to candidate's verified stack with honest disclosures (Guardrail C33) |
| Radio chip option mismatch / DOM selection failure | Non-conforming answer (e.g. numeric "0" vs `['Beginner', 'Intermediate', 'Expert']`) broke chip click, causing stuck loop and application failure | [PASS] Fixed — Option-Constrained Resolution with proficiency tier fallback (`_best_option_match`), heuristic option filtering, and pre-click conformity check with retry (Guardrail C34) |

---

## 8. CONFIRMED GROUND TRUTH APPLICATIONS AUDIT TRAIL (28 CONFIRMED)

All applications below have been autonomously verified via DOM success banners, history redirects, or completed chatbot questionnaires:

| # | Date & Timestamp | Company | Job Title | Platform | Status | Screening Q&A / Method |
|:---|:---|:---|:---|:---|:---|:---|
| 1 | 2026-09-18 23:24:51 | Pierag Consulting | Associate | Naukri | `APPLIED_CHATBOT` | Solved 3 questions (Relocation: Yes, Stat Audit: Stat Audit, Accounting Standard: Ind As) |
| 2 | 2026-09-18 23:26:35 | Garg Mukesh & Associates | Audit Associate | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 3 | 2026-09-18 23:28:10 | Safeli Smart Llp | Accounts Executive And Internal Auditor | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 4 | 2026-09-18 23:30:15 | Genpact | Specialist - MDM | Naukri | `APPLIED_CHATBOT` | Solved MDM screening questionnaire |
| 5 | 2026-09-18 23:32:45 | FedEx | Senior Financial Analyst | Naukri | `APPLIED_CHATBOT` | Solved financial analysis screening |
| 6 | 2026-09-18 23:34:20 | Ikiraon Global | Financial Planning Analyst | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 7 | 2026-09-18 23:35:50 | VBR & Associates | Audit Associate | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 8 | 2026-09-18 23:37:25 | Wellgen | Accounting Specialist | Naukri | `APPLIED_CHATBOT` | Solved accounting questions |
| 9 | 2026-09-18 23:39:10 | Delhi Apartments | Junior Accounts Executive | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 10 | 2026-09-18 23:41:00 | Allied Industries | Finance Associate | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 11 | 2026-09-18 23:42:30 | XMS Solutions | Process Analyst | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 12 | 2026-09-18 23:44:15 | Metaphor Infotech | Account Payable Associate | Naukri | `APPLIED_CHATBOT` | Solved AP screening questionnaire |
| 13 | 2026-09-18 23:46:00 | Metaphor Infotech | Senior AP Executive | Naukri | `APPLIED_CHATBOT` | Solved AP questions |
| 14 | 2026-09-18 23:47:45 | Cloudxtreme | Finance Operations Analyst | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 15 | 2026-09-18 23:49:30 | Sutherland | Associate - Financial Analysis | Naukri | `APPLIED_CHATBOT` | Solved finance questions |
| 16 | 2026-09-18 23:51:48 | GLOBAL GIANT MNC | Senior Finance Executive OTC, RTR, FP&A | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 17 | 2026-09-18 23:52:50 | AXA Global Business Services | Senior Analyst | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 18 | 2026-09-18 23:53:59 | Aon | SOX Coordinator | Naukri | `APPLIED_CHATBOT` | Solved SOX control & compliance questions |
| 19 | 2026-09-18 23:57:37 | Ujjivan Small Finance Bank | Auditor | Naukri | `APPLIED_CHATBOT` | Solved auditing experience questionnaire |
| 20 | 2026-09-19 00:00:09 | Talent Corner HR Services | Senior Accountant - D2C | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 21 | 2026-09-19 00:04:42 | Deloitte US-India Offices | Record To Report Analyst | Naukri | `APPLIED_CHATBOT` | Solved R2R experience questionnaire |
| 22 | 2026-09-19 00:07:44 | Layam Flexi | Finance Executive | Naukri | `APPLIED_CHATBOT` | Solved 3 questions (Import Export: 0, General Ledger: 1, Relocation: Yes) |
| 23 | 2026-09-19 00:08:21 | Max Healthcare | Cashier - Accounts & Finance | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 24 | 2026-09-19 00:12:49 | ManpowerGroup Services India | Senior Executive - OTC | Naukri | `APPLIED_CHATBOT` | Solved OTC questions (E-Invoicing: 1, Order to Cash: 0) |
| 25 | 2026-09-19 00:13:34 | Hiring for Leading Financial Services Co. | Accounts Executive | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 26 | 2026-09-19 00:14:10 | Hiring for Leading Food & Beverage Co. | Accounts Officer | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect |
| 27 | 2026-09-19 00:16:41 | Finance and accounts MNC | Accounts Payable Associate SAP Specialisation | Naukri | `APPLIED_CHATBOT` | Solved 3 questions (Contractual: Yes, 3rd-party: Yes, Night shift: Yes) |
| 28 | 2026-09-19 00:22:48 | Anaptyss | Technology Risk Management Control Testing | Naukri | `APPLIED_1CLICK` | 1-Click Apply confirmed via redirect (NLB Services / 2-7 Yrs / Noida & Gurugram) |





