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
- `search_manifest.json` — Discovery → Tailoring → Application (enriched with `jd_path` and `description`)
- `applications_tracker.csv` — Application → Deduplication (canonical 9-column schema)
- `saved_external_jobs.json` — External redirect storage
- `candidate_config.json` — Self-learning truth cache (read/write by all scripts)
- `pending_question.json` — Async File-Based IPC handshake between the Application Engine and AG 2.0 (replaces terminal stdin blocking)
- `ques_ans_chatbot.json` — Per-job Q&A audit log stored alongside tailored resumes
- `Job_Description.md` — Raw scraped JD markdown saved to `profiles/<profile>/output/applications/<Company>_<Role>/`
- `job_details.json` — Structured job metadata saved to `profiles/<profile>/output/applications/<Company>_<Role>/`

---

## 3. MODULE-BY-MODULE REFERENCE

### 3.1 `ai_client.py` — Central AI Reasoning Engine

**Classes:**
- `MatchResult(tuple)` — Hybrid result supporting tuple unpacking (`score, reasoning, matching, missing = result`), attribute access (`result.score`), and dict-style lookups (`result['score']`, `result.get('score', 0)`).
- `AIClient` — Gemini Flash + Antigravity 2.0 File-Based IPC dual-brain.

**Key Methods:**
| Method | Purpose | Fallback Chain |
|:---|:---|:---|
| `generate_text(...)` | General LLM text generation (profile summary, bullets) | Operational Gemini client → `pending_question.json` File-Based IPC |
| `evaluate_job_match(...)` | Two-Stage Cognitive Qualification Engine (0-100) | Stage 1 Gatekeeper (C6 negative, domain stem, exp band) → Stage 2 Precision (Gemini JSON / IPC 40-65 / Heuristics with min 2 skills, $\ge 60\%$ threshold) |
| `answer_screening_question(...)` | Resolves chatbot questions | Exact cache (`auto_learned_truths`) → Gemini API → File IPC polling |
| `_best_option_match(...)` | Maps freeform answer to UI choices | Exact → word-boundary (`\b`) → numeric → boolean → `None` (H1/H2 compliant) |
| `_persist_learned_truth(...)` | Caches verified answers to config | Atomic via `ProfileContext.save_config()` (`.tmp` + `os.replace`) |
| `_fallback_antigravity_ipc(...)` | AG 2.0 Handshake Hook | Writes `pending_question.json` and polls until AG 2.0 fills the `"answer"` key |

**Critical Design Decisions:**
- **Two-Stage Cognitive Qualification Engine:** Stage 1 Deterministic Gatekeeper (C6 absolute negative keyword gating, domain root-stem token gating `dt[:5] == tt[:5]`, experience band filter auto-rejecting >3yr gap) eliminates false-positive applications to out-of-domain roles. Stage 2 Precision scoring enforces a strict 60% qualification bar and minimum 2 core skills requirement.
- **Zero Terminal Blocking:** Removed `sys.stdin.readline()`. The background daemon will never freeze waiting for terminal input.
- **AG 2.0 File IPC Polling:** Non-blocking polling of `pending_question.json`. Once an answer is detected, it proceeds instantly and unlinks the file.
- **Strict Exact-Match Caching Only:** When checking `auto_learned_truths`, uses strict `key.strip().lower() == question.strip().lower()`.
- **Character Limits:** Automatically trims free-text IPC answers to 250 characters to prevent form-field overflow.

---

### 3.2 `04_job_discovery.py` — Batched Discovery Engine

**Execution Flow:**
1. Connect to Chrome via CDP at `candidate.cdp_url`
2. Load dedup ledger from CSV + external JSON
3. For each (platform × location × keyword × page):
   a. Navigate to search results page (SRP)
   b. Extract up to 15 job cards per page, up to 3 pages
   c. For each card: check dedup → title gate → navigate to detail page
   d. Check for external apply button → gate and record to `saved_external_jobs.json` if present
   e. Extract full JD text + skill tags
   f. Two-Stage AI score evaluation → qualify only if `score >= 60`
   g. Dynamically sanitize application folder: `profiles/<profile>/output/applications/<Company>_<Role>/`
   h. Immediately write `Job_Description.md` and `job_details.json` to the application folder
   i. Append enriched job entry (`jd_path`, `description`) to `search_manifest.json`
   j. When batch reaches BATCH_SIZE=1: trigger tailoring → upload → apply pipeline
4. Resume discovery sweep

**Non-Hijacking Tab Cleanup:**
`cleanup_browser_tabs(context, tracked_pages, active_page)` tracks only Playwright pages created by discovery workers, safely closing non-active worker tabs while strictly protecting unrelated user browsing tabs.

**Naukri URL Pattern:**
```
https://www.naukri.com/{keyword-slug}-jobs-in-{location-slug}[-{page}]?experience={N}[&ctcFilter={lo}to{hi}]
```

**LinkedIn URL Pattern:**
```
https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}&f_AL=true&start={N*25}
```

**Deduplication Sources:**
- `applications_tracker.csv` → `"Job URL"` column via `csv.DictReader`
- `saved_external_jobs.json` → `url` and `title` fields
- In-memory `processed_ledger` set (populated at startup, updated during run)

---

### 3.3 `05_apply_jobs.py` — Application Engine

**Two Main Classes:**

#### `ChatbotResolver` — DOM Chatbot Reverse-Engineering
- **Question Extraction:** Iterates `li.botItem .botMsg` elements in reverse, filtering greetings containing candidate name.
- **Control Detection Priority:** `FILE_UPLOAD` → `DATE_INPUT` → `RADIO_CHIP` (chips, toggle pills, custom radios, excluding `.chipMsg`) → `DROPDOWN` → `CONTENTEDITABLE` → `UNKNOWN`.
- **Contenteditable React Protocol:** Click → Ctrl+A → Backspace → `page.keyboard.insert_text(answer)` → native `document.execCommand('insertText')` → manual `dispatchEvent` (Input/Change/Keydown/Keyup) → forcefully remove `.disabled` class and `disabled` attribute from Send/Submit button.
- **Chip Selection:** Escapes single quotes via `replace("'", "\\'")` (H3 Guardrail), clicks matching chip/label natively and via Playwright locators, and triggers Save/Next button.
- **Bug 4 Fix & Unknown Control Fallback:** Checks visibility of `contenteditable` input before attempting typing; if no visible input exists, extracts all visible interactive labels/chips and routes to `pending_question.json` IPC to prevent blind typing loops into detached DOM nodes.
- **3x Stuck Question Loop Breaker:** If active question repeats $\ge 3$ times without progress, immediately aborts the loop, logs `REQUIRES_MANUAL_INTERVENTION`, and writes `[ABORTED_STUCK_3X]` into `ques_ans_chatbot.json`.
- **Per-Job Audit Logging:** Every question asked, the control type detected, and the resolved answer are appended to `profiles/<profile>/output/applications/<Company>_<Role>/ques_ans_chatbot.json`.

#### `ApplicationEngine` — Batch Orchestrator
- **Status Flow:**
  ```
  Navigate → External Check → Already Applied Check → Click Apply
       ↓                                                    ↓
  REDIRECT_EXTERNAL                               Poll for Drawer
       ↓                                           ↓           ↓
  SKIPPED_ALREADY_APPLIED                    Drawer Open    No Drawer
                                                ↓              ↓
                                         Chatbot Loop    Check Banners
                                              ↓              ↓         ↓
                                      APPLIED_CHATBOT   APPLIED_1CLICK  FAILED
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
    "description": "Full raw job description text scraped from detail page..."
  }
]
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

---

## 5. NAUKRI CHATBOT DRAWER DOM ANATOMY

```
.chatbot_DrawerContentWrapper (or div[class*='chatbot_Drawer'])
├── .chatbot_MessageContainer (scrollable message list)
│   ├── li.botItem .botMsg          ← Recruiter questions
│   ├── li.userItem .userMsg        ← Candidate responses
│   └── ...
├── div.textArea[contenteditable]   ← Free-text input
├── div.radioItem / div.choiceChip  ← Choice chips (NOT div[class*='chip'])
├── input[type='date']              ← Date inputs
├── input[type='file']              ← Resume upload
├── select                          ← HTML dropdown
└── .sendMsgbtn_container .sendMsg  ← Submit button
```

**Selector Fragility:** Naukri uses CSS Modules with build-hash suffixes (e.g., `__h0K4t`, `__WbS2i`). These change on every Naukri deployment. Always provide fallback selectors without hashes.

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
| Gemini API key missing | Dispatches to `pending_question.json` File-Based IPC | ✅ Correct (H6 compliant) |
| Gemini API rate limited | Dispatches to `pending_question.json` File-Based IPC | ✅ Correct (H6 compliant) |
| CDP Chrome not running | Logs error, exits gracefully | ✅ Correct |
| Naukri selector hash changed | Uses robust un-hashed fallback selectors | ✅ Handled |
| Chatbot drawer never opens | Returns FAILED | ✅ Correct (C1 compliant) |
| Unknown form control type | Scans interactive chips or dispatches to File IPC | ✅ Correct (Bug 4 fix) |
| Active question stuck 3x | Halts loop, logs REQUIRES_MANUAL_INTERVENTION | ✅ Correct (C7 breaker) |
| `candidate_config.json` write | Atomic write via .tmp + os.replace | ✅ Correct (C4 compliant) |
| PDF generation crashes | check=True aborts application | ✅ Correct (H6 compliant) |
| All chatbot iterations exhausted | Checks completion, returns FAILED if not done | ✅ Correct (C3 compliant) |
