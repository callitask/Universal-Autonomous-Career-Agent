# UNIVERSAL AUTONOMOUS CAREER AGENT: ARCHITECTURE REFERENCE

> **Document Version:** 2.1  
> **Last Updated:** 2026-08-31  
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
- `search_manifest.json` — Discovery → Tailoring → Application
- `applications_tracker.csv` — Application → Deduplication
- `saved_external_jobs.json` — External redirect storage
- `candidate_config.json` — Self-learning truth cache (read/write by all scripts)

---

## 3. MODULE-BY-MODULE REFERENCE

### 3.1 `ai_client.py` — Central AI Reasoning Engine (426 lines)

**Classes:**
- `MatchResult(tuple)` — Hybrid result supporting tuple unpacking, attribute access, and dict-style lookups
- `AIClient` — Gemini Flash + Antigravity 2.0 terminal dual-brain

**Key Methods:**
| Method | Purpose | Fallback Chain |
|:---|:---|:---|
| `generate_text(prompt, system_instruction, default_fallback)` | General text generation | Gemini → default string → terminal stdin |
| `evaluate_job_match(job_title, job_description, ...)` | Scores job suitability 0-100 | Gemini JSON → heuristic word overlap → MatchResult(60) |
| `answer_screening_question(question, options, ...)` | Resolves chatbot questions | Exact cache → Gemini analysis → terminal stdin |
| `_best_option_match(target, options)` | Maps freeform answer to UI choices | Exact → word-boundary → numeric → boolean → None |
| `_persist_learned_truth(question, answer)` | Caches answers to config | Atomic via ProfileContext.save_config() |
| `score_and_reorder_bullets(bullets, jd)` | Reorders resume bullets by JD relevance | Word-set intersection scoring |
| `_fallback_antigravity_interactive(prompt, ...)` | Terminal stdin/stdout hook | Single-line or END_OF_ANSWER multiline |

**Critical Design Decisions:**
- `_best_option_match` returns `None` (not `options[0]`) when no match found
- Exact-match only for learned truth lookup (no substring/regex)
- Quote stripping on AI responses: `replace('"', '').replace("'", "")` — note this corrupts apostrophe words like `Bachelor's`

---

### 3.2 `04_job_discovery.py` — Batched Discovery Engine (349 lines)

**Execution Flow:**
1. Connect to Chrome via CDP at `candidate.cdp_url`
2. Load dedup ledger from CSV + external JSON
3. For each (platform × location × keyword × page):
   a. Navigate to search results page (SRP)
   b. Extract up to 15 job cards per page, up to 3 pages
   c. For each card: check dedup → title gate → navigate to detail page
   d. Check for external apply button → reject if present
   e. Extract full JD text + skill tags
   f. AI score evaluation → queue if score ≥ 40
   g. When batch reaches BATCH_SIZE=1: trigger tailoring → upload → apply pipeline
4. Resume discovery sweep

**Naukri URL Pattern:**
```
https://www.naukri.com/{keyword-slug}-jobs-in-{location-slug}[-{page}]?experience={N}[&ctcFilter={lo}to{hi}]
```

**LinkedIn URL Pattern:**
```
https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}&f_AL=true&start={N*25}
```

**Deduplication Sources:**
- `applications_tracker.csv` → `"Job URL"` column via DictReader
- `saved_external_jobs.json` → `url` and `title` fields
- In-memory `processed_ledger` set (populated at startup, updated during run)

---

### 3.3 `05_apply_jobs.py` — Application Engine (769 lines)

**Two Main Classes:**

#### `ChatbotResolver` — DOM Chatbot Reverse-Engineering
- **Question Extraction:** Iterates `li.botItem .botMsg` elements in reverse, filtering greetings that contain candidate name + welcome phrases
- **Control Detection Priority:** `FILE_UPLOAD` → `CONTENTEDITABLE` → `RADIO_CHIP` → `DROPDOWN` → body fallback → `UNKNOWN`
- **Contenteditable Input Protocol:** Click → Ctrl+A → Backspace → keyboard.type(delay=30) → JS event dispatch → Send button click
- **Chip Selection:** Escapes single quotes, tries multiple selector patterns, clicks matching chip + Save/Next button
- **Completion Detection:** Scans for success text markers in drawer AND page body. Does NOT treat drawer disappearance as completion.

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
- **Critical Safety:** The `FAILED` return is the default when no confirmation is found. `APPLIED_1CLICK` requires explicit success banner DOM match.

---

### 3.4 `generate_factual_tailored.py` — Resume Tailoring & PDF (318 lines)

**Algorithm:**
1. Parse `resume.md` into sections via markdown heading regex (`^#{1,4}\s+`)
2. Extract JD keywords: tokenize with `[a-z][a-z\-]+`, filter stopwords, build bigrams, add taxonomy skills
3. Score each bullet: count keyword occurrences via substring match
4. Stable-sort bullets within each section by score (highest first)
5. Reassemble markdown → convert to HTML via `markdown` library → wrap in ATS-compliant CSS template
6. Render PDF via Playwright's `page.pdf()` using Chrome's print engine

**Known Issue:** Keyword extraction regex `[a-z][a-z\-]+` strips tech names with numbers/symbols (`C++`, `.NET`, `K8s`). Scoring uses substring `kw in bullet_lower` which can false-positive (`"art" in "smart"`).

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
    "score": 85
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
| Gemini API key missing | Falls back to terminal stdin | ✅ Correct |
| Gemini API rate limited | Falls back to terminal stdin | ✅ Correct |
| CDP Chrome not running | Logs error, exits gracefully | ✅ Correct |
| Naukri selector hash changed | Silently fails to extract JD/skills | ⚠️ Needs fallback selectors |
| Chatbot drawer never opens | Returns FAILED | ✅ Correct (was bug C1, now fixed) |
| Unknown form control type | Falls back to contenteditable | ⚠️ May fail on sliders/date pickers |
| `candidate_config.json` corrupted | Returns `{}`, risks overwrite | ⚠️ Atomic save prevents future corruption but doesn't recover existing corruption |
| PDF generation crashes | `check=True` aborts application | ✅ Correct (was bug H6, now fixed) |
| All chatbot iterations exhausted | Checks completion, returns FAILED if not done | ✅ Correct |
