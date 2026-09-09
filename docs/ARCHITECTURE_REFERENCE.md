# UNIVERSAL AUTONOMOUS CAREER AGENT: ARCHITECTURE REFERENCE

> **Document Version:** 3.0 — Post-Phase 1-4 Remediation Complete  
> **Last Updated:** 2026-09-03  
> **Purpose:** Comprehensive technical reference for the complete pipeline — how every module works, data flows, inter-process communication, DOM interaction patterns, and the chatbot reverse-engineering protocol. Upload this alongside `WORKSPACE_RULES.md` to ground the AI's understanding of the system before any coding session.

---

## 1. SYSTEM OVERVIEW

The Universal Autonomous Career Agent is a **multi-process, file-coordinated, CDP-driven** automation pipeline that:

1. **Discovers** job postings on Naukri and LinkedIn via batched SRP scraping
2. **Evaluates** each posting against the candidate's resume using AI scoring (0-100)
3. **Tailors** the candidate's factual resume by reordering bullets for ATS keyword density
4. **Renders** a per-job PDF via Playwright's Chrome PDF engine
5. **Uploads** the tailored resume to the candidate's Naukri profile
6. **Applies** autonomously — solving 1-click apply and multi-step chatbot drawers
7. **Verifies** submission via DOM success markers
8. **Tracks** everything in CSV + JSON for audit

**Execution Model:** Sequential subprocess chain. No threading. No async. Each phase runs as a standalone Python process orchestrated by `continuous_career_agent.py` or `04_job_discovery.py`.

**Architectural Separation of Concerns:**
- **Developer Scope (`core/`, `docs/`, `core/utils/`):** In coding sessions, the AI assistant operates strictly as the Principal Agent Developer, updating engine logic, documentation, and tooling. The developer **never manually edits files inside `profiles/`**.
- **Runtime Agent Scope (`profiles/`):** When the agent is executed, the agent itself autonomously and intelligently reads candidate resumes, synthesizes `cognitive_profile.json`, maintains `processed_ledger.json`, caches `auto_learned_truths`, and adapts `candidate_config.json` (e.g. starvation title auto-expansion) without manual developer patching.

---

## 2. PIPELINE EXECUTION SEQUENCE

```
continuous_career_agent.py (daemon loop)
  │
  ├── [Optional] 02_profile_sync_naukri.py --profile <dir>
  ├── [Optional] 03_profile_sync_linkedin.py --profile <dir>
  │
  └── LOOP:
       ├── 04_job_discovery.py --profile <dir>
       │    │
       │    ├── [Per matched job, BATCH_SIZE=1]:
       │    │    ├── generate_factual_tailored.py --profile <dir>
       │    │    ├── 02b_naukri_fast_resume_upload.py --profile <dir>  (or 03_profile_sync_linkedin.py)
       │    │    └── 05_apply_jobs.py --profile <dir>
       │    │
       │    └── Resume scanning next keyword/location/page...
       │
       └── time.sleep(delay)  →  Next Cycle
```

**IPC Contract:** Scripts communicate via filesystem artifacts:
- `search_manifest.json` — Discovery → Tailoring → Application (enriched with `jd_path`, `description`, and `naukri_match_score`)
- `applications_tracker.csv` — Application → Deduplication (canonical 9-column schema)
- `saved_external_jobs.json` — External redirect storage
- `candidate_config.json` — Self-learning truth cache (read/write by all scripts)
- `pending_question.json` — Async File-Based IPC handshake between the Application Engine and AG 2.0 (replaces terminal stdin blocking)
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
- `AIClient` — Gemini Flash + Antigravity 2.0 File-Based IPC dual-brain with portal match score calibration.

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
| `answer_screening_question(...)` | Resolves chatbot questions | Exact cache (`auto_learned_truths`) → Gemini API → File IPC polling |
| `_best_option_match(...)` | Maps freeform answer to UI choices | Exact → word-boundary (`\b`) → numeric → boolean → `None` (H1/H2 compliant) |
| `_persist_learned_truth(...)` | Caches verified answers to config | Atomic via `ProfileContext.save_config()` (`.tmp` + `os.replace`) |
| `_fallback_antigravity_ipc(...)` | AG 2.0 Handshake Hook | Writes `pending_question.json` and polls until AG 2.0 fills the `"answer"` key |

**Critical Design Decisions:**
- **Naukri Native Match Score Calibration (Stage 2 Component D):** When `naukri_match_score` (scraped from `div.styles_JDC__match-score__VnjLL`) is provided:
  - If `Keyskills == True` AND `Work Experience == True`: Grants a **+10% verified confidence bonus** to Stage 2 precision score.
  - If `Keyskills == True` (only): Grants a **+5% verified confidence bonus**.
  - If `Work Experience == True` (only): Grants a **+3% verified confidence bonus**.
  - Explanatory notes are automatically appended to `reasoning` (e.g., `[Naukri Portal Verified: Keyskills & Exp Match (+10%), Early Applicant, Location Match]`).
  - Active portal flags are injected into both the Gemini LLM prompt and the Antigravity 2.0 IPC prompt (`pending_question.json`) for factual arbitration.
- **Autonomous Cognitive Profile Synthesis:** At runtime, `AIClient.synthesize_cognitive_profile()` inspects the active candidate's `resume.md` and configuration, derives their domain (e.g. Finance & Accounting, Software Engineering, etc.), core vs. generic soft skills, domain acronyms, out-of-domain incompatible verticals, and multi-cycle designation queues (Cycle 1 core, Cycle 2 seniority/lateral, Cycle 3 specialized/functional) stored in `profiles/<profile>/output/cognitive_profile.json`.
- **Zero-Hardcoding Contract & Guardrail P1:** Zero vertical dictionaries, domain words, or soft skill sets exist in Python source code. All evaluation gates in `evaluate_job_match()` and `arbitrate_card_fit()` read dynamically from `cognitive_profile.json`.
- **Two-Stage Cognitive Qualification Engine:** Stage 1 Deterministic Gatekeeper enforces C6 absolute negative keywords, domain root-stem token gating (excluding hierarchy stopwords), an **Incompatible Industry/Vertical Hard Gate** (rejecting verticals flagged incompatible by the cognitive profile), and an experience band filter (>3yr gap auto-rejects). Stage 2 Precision scoring enforces a strict 60% qualification bar and requires $\ge 2$ distinct **CORE functional domain skills** (excluding soft skills like "analytical" or "problem solving").
- **Tier 2B Cognitive Card Arbitration:** Evaluates unfamiliar roles, dynamic domain abbreviations, and visible skill chips while strictly rejecting incompatible verticals; does not contaminate candidate configuration with card titles.
- **Tier 4 Autonomous Starvation Recovery:** If 0 jobs are found in a sweep, the Brain analyzes all seen market titles, compares with `resume.md` and candidate's total experience, and expands `candidate_config.json` with high-yield senior designations within the candidate's domain.
- **Zero Terminal Blocking:** Removed `sys.stdin.readline()`. The background daemon will never freeze waiting for terminal input.
- **AG 2.0 File IPC Polling:** Non-blocking polling of `pending_question.json`. Once an answer is detected, it proceeds instantly and unlinks the file.
- **Strict Exact-Match Caching Only:** When checking `auto_learned_truths`, uses strict `key.strip().lower() == question.strip().lower()`.
- **Character Limits:** Automatically trims free-text IPC answers to 250 characters to prevent form-field overflow.

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
   c. Multi-Pass Gating (`is_title_allowed`):
      - C6 Negative Check (Absolute drop)
      - Direct Keyword / Stem Match
      - Card Skills Match
      - Tier 2B Cognitive Brain Arbitration (`ai.arbitrate_card_fit`)
   d. Deep scan detail page:
      - Check for native apply (`#apply-button`) vs external redirect (`#company-site-button`)
      - **Un-clamp "Read More"** (`span.styles_rm-link__RgrMs`), expanding hidden responsibilities and benefits from 3.4k to 7.2k+ characters (Guardrail C12)
      - **Scrape Naukri Native Match Score** (`div.styles_JDC__match-score__VnjLL`, checking `i.ni-icon-check_circle` vs `i.ni-icon-crossMatchscore` for Early Applicant, Keyskills, Location, Work Experience) (Guardrail C13)
      - Assemble multi-section description: Highlights, Description, Read More, Specifications, Education, and Key Skills
   e. Two-Stage AI score evaluation passing `naukri_match_score` $\rightarrow$ qualify only if `score >= 60`
   f. Write `Job_Description.md` and `job_details.json` (including `naukri_match_score`) to application folder
   g. Append enriched job entry to `search_manifest.json`
   h. When batch reaches BATCH_SIZE=1: trigger tailoring → upload → apply pipeline
8. Resume discovery sweep & advance search cycle via `ai.advance_search_cycle()`

**Naukri URL Pattern:**
```
https://www.naukri.com/{keyword-slug}-jobs-in-{location-slug}[-{page}]?experience={N}&jobAge={age}&wfhType={mode}&companyJobs={bool}[&ctcFilter={lo}to{hi}]
```
149: 
150: ---
151: 
152: ### 3.3 `05_apply_jobs.py` — Application Engine
153: 
154: **Two Main Classes:**
155: 
156: #### `ChatbotResolver` — DOM Chatbot Reverse-Engineering
157: - **Question Extraction:** Iterates `li.botItem .botMsg` elements in reverse, filtering greetings containing candidate name.
158: - **Control Detection Priority:** `FILE_UPLOAD` → `DATE_INPUT` → `RADIO_CHIP` (chips, toggle pills, custom radios, excluding `.chipMsg`) → `DROPDOWN` → `CONTENTEDITABLE` → `UNKNOWN`.
159: - **Contenteditable React Protocol:** Click → Ctrl+A → Backspace → `page.keyboard.insert_text(answer)` → native `document.execCommand('insertText')` → manual `dispatchEvent` (Input/Change/Keydown/Keyup) → forcefully remove `.disabled` class and `disabled` attribute from Send/Submit button.
160: - **Empirical Radio Selection:** Targets exact Naukri radio/checkbox label containers (`label.ssrc__label`, `input.ssrc__radio`, `input.ssrc__checkbox`) to reliably trigger React event listeners and enable the submission container.
161: - **Chatbot Drawer Submit Scoping:** Submissions target `.sendMsgbtn_container .send:not(.disabled) .sendMsg` strictly scoped within `get_drawer()`, preventing background page bookmark click interference.
162: - **Platform Rejection Banner Detection (Guardrail C9):** Checks for platform rejection banners and aborts immediately (`FAILED_PLATFORM_REJECTED`).
163: - **Premature Drawer Closure Detection (Guardrail C9):** Detects unmounted or dismissed chatbot drawers (`not resolver.is_drawer_open()`), verifies completion, and aborts immediately (`DRAWER_CLOSED`).
164: - **3x Stuck Question Loop Breaker (Guardrail C7):** Aborts on 3 repeated questions without progress.
165: - **Adaptive Answer Formatter:** Automatically formats repeated screening answers (e.g. `9` -> `9 years` or `30` -> `30 Days`) based on question semantics to pass frontend portal validation.
166: 
167: #### `LinkedInApplyHandler` — Native LinkedIn Easy Apply Modal Automation
168: - **Modal Detection & Container Scoping:** Identifies `div.jobs-easy-apply-modal` without background interference.
169: - **Dynamic Field Resolution:** Resolves phones, text inputs, radio groups, dropdowns, and uploads tailored ATS PDF resumes.
170: - **Modal Stepping & State Progression:** Advances through "Next", "Review", and commits via "Submit application".
171: - **Safe Dismissal:** Calls `discard_and_close_modal()` on unresolvable fields without leaving dangling modals.
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
3. Auto-discover: first subdirectory in `profiles/`

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
  }
}
```

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
| Candidate data in core/*.py | Fatal halt via `verify_codebase_purity()` | ✅ Correct (Guardrail P1) |
| Lazy-loaded DOM not mounted | Pre-inspection `window.scrollTo(0, 1200)` hydrates cards | ✅ Correct (Guardrail C11) |
| JD text truncated to 5 lines | Click `span.styles_rm-link__RgrMs` un-clamps full text | ✅ Correct (Guardrail C12) |
| Portal match score ignored | Scrapes `div.styles_JDC__match-score__VnjLL`, awards +10% bonus | ✅ Correct (Guardrail C13) |
| Profile edit modal targets fragile | Uses verified IDs (`#resumeHeadlineTxt`, `#submitEmployment`) | ✅ Correct (Guardrail C14) |
| Chatbot submit clicked background | Strictly scoped to `.sendMsgbtn_container .send .sendMsg` | ✅ Correct (Guardrail C10) |
| Gemini API key missing | Dispatches to `pending_question.json` File-Based IPC | ✅ Correct (H6 compliant) |
| Gemini API rate limited | Dispatches to `pending_question.json` File-Based IPC | ✅ Correct (H6 compliant) |
| CDP Chrome not running | Pre-flight check detects port 9222 down, logs instructions | ✅ Correct |
| Naukri selector hash changed | Uses robust un-hashed fallback selectors | ✅ Handled |
| Chatbot drawer never opens | Returns FAILED | ✅ Correct (C1 compliant) |
| Unknown form control type | Scans interactive chips or dispatches to File IPC | ✅ Correct (Bug 4 fix) |
| Active question stuck 3x | Halts loop, logs REQUIRES_MANUAL_INTERVENTION | ✅ Correct (C7 breaker) |
| `candidate_config.json` write | Atomic write via .tmp + os.replace | ✅ Correct (C4 compliant) |
| PDF generation crashes | check=True aborts application | ✅ Correct (H6 compliant) |
| All chatbot iterations exhausted | Checks completion, returns FAILED if not done | ✅ Correct (C3 compliant) |
