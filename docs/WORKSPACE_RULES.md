# UNIVERSAL AUTONOMOUS CAREER AGENT: WORKSPACE DEVELOPMENT & CODING RULES

> **Document Version:** 2.1 — Post-Audit Remediated  
> **Last Updated:** 2026-08-31  
> **Authority:** These rules are ABSOLUTE and OVERRIDE all model defaults. Violations cause runtime crashes, data corruption, phantom applications, or account bans.  
> **Workspace Root:** `F:\JOB AI AGENT`

---

## DIRECTIVE 1: ABSOLUTE FULL-FILE DELIVERY (ZERO PLACEHOLDERS / ZERO OMISSIONS)

1. Whenever creating or updating any file in `core/`, `profiles/`, or `utils/`, you must output the **100% complete, production-ready file from line 1 to the end**.
2. **Strictly Forbidden:** Never use comments like `# ... rest of the code remains the same ...`, `# ... existing methods ...`, truncated classes, or omitted helper functions.
3. Every method required by any caller in the pipeline (`ai_client.py`, `04_job_discovery.py`, `05_apply_jobs.py`, `generate_factual_tailored.py`, `02_profile_sync_naukri.py`, `02b_naukri_fast_resume_upload.py`, `03_profile_sync_linkedin.py`, `continuous_career_agent.py`) must be fully implemented.
4. Every code block must be a complete drop-in replacement that executes immediately with zero missing attributes, unresolved imports, or syntax errors.
5. **If a file exceeds the output window**, split the delivery into clearly marked sequential parts (`# === PART 1 OF 2 ===` ... `# === PART 2 OF 2 ===`), ensuring the concatenation produces a valid Python file.

---

## DIRECTIVE 2: STRICT ZERO-HARDCODING POLICY

1. **No Personal Data in Code:** No candidate names, email addresses, phone numbers, compensation numbers (CTCs), notice period days, city names, pin codes, or resume bullet points may be hardcoded inside `core/` scripts.
2. **Dynamic Profile Sandboxing:** All personal parameters, skill taxonomies, target job criteria, and file paths must resolve at runtime through `ProfileContext` from:
   * `profiles/<profile_name>/candidate_config.json`
   * `profiles/<profile_name>/resume.md`
3. **Dynamic Directory Resolution:** The engine must automatically locate the active candidate profile directory from command-line arguments (`--profile`) or dynamically scan `profiles/` for existing candidate configurations without hardcoded fallback strings.
4. **Isolated Output Paths:** All outputs (tailored resumes, PDF packages, trackers, search manifests, and screenshots) must write strictly to `profiles/<profile_name>/output/`.
5. **No Hardcoded Regex Intercepts for Screening Questions:** Never match questions like `"notice period"`, `"experience"`, `"CTC"` to hardcoded numeric values. Every screening question must be routed through: exact cache match in `auto_learned_truths` → AI model analysis → terminal fallback. No shortcuts.
6. **No Hardcoded Model Names as Constants:** Model identifiers (e.g., `gemini-2.5-flash`) should be configurable via `candidate_config.json` or environment variables when possible.

---

## DIRECTIVE 3: ANTIGRAVITY 2.0 DUAL-BRAIN ARCHITECTURE

1. **Pre-Selected AI Brain:** The system operates with Antigravity 2.0 (the model executing the terminal) as the primary cognitive decision-maker, supplemented by Gemini Flash when API keys are available.
2. **Non-Crashing Delimiter Fallback:** When Gemini API keys are absent, unconfigured, or rate-limited:
   * Never crash the pipeline or raise unhandled API rate-limit errors.
   * Seamlessly fallback to the interactive terminal hook via `stdin`/`stdout`.
3. **Multi-Line Delimiter Standard:** For multi-line responses (Cover Letters, Experience Bullet Rewriting, Skill Lists), the script must pause and ingest input until the isolated cutoff line `END_OF_ANSWER` is submitted.
4. **Self-Learning Knowledge Persistence:** Any novel question answered by the AI Brain must be cached immediately to `candidate_config.json` under `auto_learned_truths` to eliminate redundant queries.
5. **Strict Exact-Match Caching Only:** When checking `auto_learned_truths`, use strict `key.strip().lower() == question.strip().lower()` comparison. Never use substring or regex matching against cached keys — this caused the H4 learned truth poisoning bug.

---

## DIRECTIVE 4: PIPELINE & METHOD SIGNATURE COMPATIBILITY

1. **Cross-Script Invocation Parity:** Any utility method called across scripts must support all existing caller signatures. Never remove, rename, or reorder positional parameters.

2. **`evaluate_job_match()` Contract:**
   ```python
   def evaluate_job_match(self, job_title, job_description, 
                          candidate_profile=None, resume_text=None, 
                          *args, **kwargs) -> MatchResult
   ```
   Must return a `MatchResult` object supporting:
   - Tuple unpacking: `score, reasoning, matching, missing = result`
   - Attribute access: `result.score`
   - Dict-style lookup: `result['score']` and `result.get('score', 0)`

3. **`ProfileContext` Constructor Contract:**
   ```python
   def __init__(self, profile_path=None, base_path=None)
   ```
   Must expose properties: `.output_dir`, `.manifest_path`, `.tracker_path`, `.profile_dir`, `.cdp_url`, `.candidate_name`, `.first_name`, `.last_name`, `.config`, `.resume_text`, `.taxonomy_skills`, `.ats_answers`, `.auto_learned_truths`

4. **`BrowserManager` Unified Interface:**
   Must expose `.get_context()`, `.new_page()`, and `.close()`, reusing existing pages and bringing them to the foreground via `.bring_to_front()`.

5. **`answer_screening_question()` Contract:**
   ```python
   def answer_screening_question(self, question, candidate_profile=None,
                                  options=None, control_type=None,
                                  resume_text=None, **kwargs) -> str
   ```

6. **`save_config()` Atomicity Contract:** Must use temporary file + `os.replace()`. Direct `open("w")` on `candidate_config.json` is forbidden.

---

## DIRECTIVE 5: PLATFORM ISOLATION & DOM SAFETY

1. **Decoupled Handlers:** Fixes and enhancements to Naukri automation scripts (`02_profile_sync_naukri.py`, `02b_naukri_fast_resume_upload.py`, Naukri scrapers/solvers) must never touch, break, or mutate LinkedIn scripts (`03_profile_sync_linkedin.py`, LinkedIn Easy Apply handlers), and vice versa.

2. **Container-Isolated Scrolling:** Never issue page-level scroll commands when a modal or chatbot drawer is active. Scroll exclusively within the identified dialog container (`.chatbot_MessageContainer`).

3. **Contenteditable Typing Standard:** When populating `contenteditable="true"` containers (Naukri chatbot, LinkedIn ProseMirror), never use `.fill()`. Always:
   - Focus the element via `.click(force=True)`
   - Select all (`Control+A` / `Meta+A`)
   - Clear (`Backspace`)
   - Emit text via `page.keyboard.type(str(answer), delay=30)` or `page.keyboard.insert_text()`

4. **Network Navigation Safety:** Never use `wait_until="networkidle"` for Naukri pages due to persistent telemetry WebSockets. Always use `wait_until="domcontentloaded"` paired with explicit selector polling.

5. **No Dangling Blank Tabs:** Scripts must never navigate to `about:blank` as a final state and terminate. The browser session must remain active, focused on the relevant application page.

6. **Greedy Selector Prohibition:** Never use `div[class*='chip']` as a UI control selector — it matches Naukri's `.chipMsg` branding logo. Use explicit class names: `div.radioItem`, `div.choiceChip`, `div.clickableChip`, `div.optionItem`.

7. **Single-Quote Safety in Selectors:** When injecting dynamic text into Playwright `:has-text()` selectors, always escape single quotes:
   ```python
   safe_opt = matched_option.replace("'", "\\'")
   f"div.radioItem:has-text('{safe_opt}')"
   ```

---

## DIRECTIVE 6: LIVE LOGGING & RUNTIME TELEMETRY

1. **Unbuffered Streaming:** Standard output must be configured with `line_buffering=True` and UTF-8 encoding on all platforms:
   ```python
   sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
   ```
2. **Transparent Progress Reporting:** Live terminal logs must clearly indicate:
   - Discovery states (keyword, location, page number, card counts)
   - Match scores and rejection reasons
   - Questionnaire prompts detected and AI responses
   - UI control classifications (`CONTENTEDITABLE`, `RADIO_CHIP`, `FILE_UPLOAD`, `DROPDOWN`, `UNKNOWN`)
   - Application submission verification results
3. **Structured Log Prefixes:** Use `[CATEGORY]` formatting for all log lines (e.g., `[CHATBOT]`, `[AI BRAIN]`, `[NAVIGATE]`, `[SUCCESS]`, `[FAILED]`, `[WARNING]`).

---

## DIRECTIVE 7: APPLICATION TRACKING & DEDUPLICATION INTEGRITY

1. **CSV Tracker Schema:** The canonical tracker CSV header is:
   ```
   Date,Company,Job Title,Platform,Job URL,Match Score,Status,Tailored Resume PDF,Notes
   ```
   All writes MUST use `csv.DictWriter` with these exact field names.

2. **Backward-Compatible Deduplication:** The `get_already_processed_urls()` function must handle BOTH old-format (`Date,Company,Role,Location,Platform,Status,FolderPath`) and new-format CSV headers. Use `csv.DictReader` and check for `"Job URL"` first, then fall back to scanning all row values for URL patterns (`https://`).

3. **Status Code Semantics:**

   | Status | Meaning |
   |:---|:---|
   | `VERIFIED_SUCCESS` | Tier-3 verified on platform history page |
   | `APPLIED_1CLICK` | Native success banner confirmed after 1-click apply |
   | `APPLIED_CHATBOT` | Chatbot drawer completed with success marker detected |
   | `REDIRECT_EXTERNAL` | External employer site — saved for manual application |
   | `SKIPPED_ALREADY_APPLIED` | Platform showed "Already Applied" banner |
   | `APPLY_BUTTON_NOT_FOUND` | No native apply trigger found on page |
   | `FAILED` | Application could not be committed |
   | `REQUIRES_MANUAL_INTERVENTION` | Unanswerable mandatory field encountered |

4. **No Phantom Successes:** Never return `APPLIED_1CLICK` or `APPLIED_CHATBOT` without explicit DOM-based confirmation. If no success banner or marker is found, return `FAILED`.

5. **Atomic External Jobs File:** Writes to `saved_external_jobs.json` must check for duplicates before appending.

---

## DIRECTIVE 8: KNOWN BUG PREVENTION GUARDRAILS

These are specific bugs that were discovered and fixed. If you ever modify these areas, you MUST preserve the fix:

### C1: No Unconditional 1-Click Fallthrough
**Rule:** `apply_single_job()` must NEVER have an unconditional `return "APPLIED_1CLICK"` at the end of the non-drawer branch. It must check success banners and return `"FAILED"` if none match.

### C2: CSV Deduplication Must Read URLs, Not Company Names
**Rule:** `get_already_processed_urls()` must use `csv.DictReader` and extract the `"Job URL"` column. Never use raw `split(",")[1]` index-based parsing.

### C3: Drawer Dismissal ≠ Completion
**Rule:** `check_completion_status()` must NEVER treat `drawer.count() == 0` or `not drawer.is_visible()` as confirmation of successful application. Only explicit success text markers count.

### C4: Atomic Config Writes
**Rule:** `save_config()` must write to a `.tmp` file first, then `os.replace()` to the target. Direct `open("w")` on `candidate_config.json` is forbidden.

### C6: Negative Keywords Are Absolute
**Rule:** `is_title_allowed()` must reject titles containing ANY negative keyword unconditionally. The presence of a positive target keyword must NOT override a negative keyword match.

### H1: No Blind `options[0]` Fallback
**Rule:** `_best_option_match()` must return `None` when no match is found. The caller must handle `None` by falling back to terminal intervention, not by silently picking the first option.

### H2: Word-Boundary Matching Only
**Rule:** Option matching must use `re.search(rf'\b{re.escape(target)}\b', option)`. Never use bare `target in option` substring checks.

### H3: Escape Quotes in Selectors
**Rule:** Before injecting `matched_option` into `:has-text()` selectors, always escape single quotes with `\\'`.

### H4: Subprocess Telemetry Phantom Freeze
**Rule:** When executing inside a background subprocess chain (`continuous_career_agent.py` -> `05_apply_jobs.py`), Windows block-buffers the output. All `print()` statements MUST use `flush=True` or the terminal will appear frozen.

### H5: React ContentEditable State Lock
**Rule:** Playwright's `page.keyboard.type` does not reliably trigger React 16+ internal state updates on custom `contenteditable` divs, leaving the "Save" button `disabled`. You MUST use `page.keyboard.insert_text()`, followed by JS `document.execCommand('insertText')`, manual event dispatching (`input`, `change`, `keydown`), and manually removing the `.disabled` class from the submit button.

### H6: stdin Subprocess Blocking
**Rule:** Never use `sys.stdin.readline()` or `input()` inside the pipeline. Because the scripts run as nested daemon subprocesses, terminal prompts will permanently hang the execution loop. Use File-Based IPC polling (`pending_question.json`) instead.

---

## APPENDIX A: DIRECTORY STRUCTURE CONTRACT

```
F:\JOB AI AGENT\
├── core/                              # Python execution scripts (NEVER hardcode paths)
│   ├── ai_client.py                   # Central AI reasoning engine
│   ├── 01_ai_analyzer.py              # One-time profile keyword extraction
│   ├── 02_profile_sync_naukri.py      # Naukri profile sync
│   ├── 02b_naukri_fast_resume_upload.py # Atomic resume upload
│   ├── 03_profile_sync_linkedin.py    # LinkedIn profile sync
│   ├── 04_job_discovery.py            # Batched job scraper + orchestrator
│   ├── 05_apply_jobs.py               # Application engine + chatbot solver
│   ├── generate_factual_tailored.py   # Resume tailoring + PDF generation
│   ├── continuous_career_agent.py     # Daemon loop orchestrator
│   ├── utils/
│   │   ├── profile_context.py         # Multi-user sandbox context manager
│   │   └── browser_manager.py         # CDP browser lifecycle manager
│   └── scrapers/                      # DEAD CODE — do not use or reference
│
├── profiles/                          # Per-candidate sandboxed data
│   └── <profile_name>/
│       ├── candidate_config.json      # Master configuration (all candidate truths)
│       ├── resume.md                  # Factual reverse-chronological resume
│       └── output/
│           ├── applications/          # Per-job tailored resume folders
│           ├── applications_tracker.csv
│           ├── search_manifest.json
│           ├── saved_external_jobs.json
│           └── logs/
│
├── docs/                              # Reference documentation
└── .agents/rules/                     # Agent workspace rules
```

## APPENDIX B: CROSS-SCRIPT IMPORT MAP

| Script | Imports From |
|:---|:---|
| `04_job_discovery.py` | `core.utils.profile_context.ProfileContext`, `ai_client.AIClient` |
| `05_apply_jobs.py` | `core.utils.profile_context.ProfileContext`, `core.utils.browser_manager.BrowserManager`, `core.ai_client.AIClient` |
| `generate_factual_tailored.py` | `core.utils.profile_context.ProfileContext`, `core.ai_client.AIClient` |
| `02_profile_sync_naukri.py` | `ai_client.AIClient`, `core.utils.profile_context.ProfileContext` |
| `02b_naukri_fast_resume_upload.py` | `core.utils.profile_context.ProfileContext` |
| `03_profile_sync_linkedin.py` | `google.genai` (separate SDK instance) |
| `continuous_career_agent.py` | `subprocess` only (shell orchestration) |

**WARNING:** `03_profile_sync_linkedin.py` uses `from google import genai` (new SDK) while all other scripts use `import google.generativeai as genai` (legacy SDK). These are **different packages**. Do not mix them.
