# UNIVERSAL AUTONOMOUS CAREER AGENT: WORKSPACE DEVELOPMENT & CODING RULES

> **Document Version:** 3.0 — Post-Phase 1-4 Remediation Complete  
> **Last Updated:** 2026-09-03  
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
7. **Zero-Hardcoding via Cognitive Profile Synthesis:** Never hardcode domain words, vertical dictionaries, or soft skill sets in Python code. All domain models, core vs. soft skill taxonomies, domain acronyms, and multi-cycle designation queues must be synthesized dynamically by `AIClient.synthesize_cognitive_profile()` and saved to `profiles/<profile>/output/cognitive_profile.json`. Out-of-domain vertical checks and search cycles must read strictly from the candidate's cognitive profile.
8. **Strict Developer Boundary vs. Runtime Sandbox Separation:**
   - **Developer Role:** In any development session, the AI assistant acts strictly as the **Principal Agent Developer**, modifying only the engine code (`core/`), documentation (`docs/`), utilities (`core/utils/`), and test harnesses.
   - **Hands Off `profiles/`:** The developer must **NEVER manually edit files inside the `profiles/` directory** (including `candidate_config.json`, `resume.md`, or candidate sandboxes).
   - **Autonomous Runtime Adaptation:** The agent code must be engineered so that **when the agent runs**, the agent itself autonomously and smartly reads, synthesizes, adapts, and updates candidate data (e.g. `cognitive_profile.json`, `processed_ledger.json`, `auto_learned_truths`, and `recommended_titles`) at runtime without human or developer manual file patching.

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
 
2. **`evaluate_job_match()` Contract & Two-Stage Evaluation Engine:**
   ```python
   def evaluate_job_match(self, job_title: str, job_description: str, 
                          candidate_profile: Optional[Dict[str, Any]] = None, 
                          resume_text: Optional[str] = None, 
                          *args, **kwargs) -> MatchResult
   ```
   **Two-Stage Cognitive Qualification Architecture:**
   * **Stage 1: Deterministic Hard Filter (Gatekeeper)**
     - *C6 Absolute Negative Gating:* Role rejected immediately (`score=0`) if any negative keyword matches in `job_title` or JD header.
     - *Domain Title Alignment:* Role rejected (`score=0`) if zero phrase or root-stem token overlap (`dt[:5] == tt[:5]`) exists with target domains. Generic hierarchy words (`manager`, `executive`, `analyst`, `operations`) are excluded from domain stem matching.
     - *Incompatible Vertical Hard Gate:* Role rejected immediately (`score=0`) if job title, specifications, or JD belongs to an incompatible vertical (Pharmaceutical R&D, Healthcare Clinical, Civil/Mechanical Engineering, Software Dev, HR, BPO) without candidate functional domain alignment (rejects "Regulatory Manager" in Pharma while permitting "Finance Manager" in Pharma).
     - *Experience Band Filter:* Role rejected (`score=0`) if JD requires experience exceeding candidate total experience by > 3 years.
   * **Stage 2: Precision Semantic & Factual Scoring**
     - *Dual-Brain LLM Route:* Structured JSON evaluation via operational Gemini client.
     - *Ambiguous Score IPC Handshake:* Scores in 40–65 range optionally routed to `pending_question.json` File IPC for AG 2.0 evaluation.
     - *Deterministic Factual Fallback:* Title/Domain (0–35), Core Skills (0–45, strictly requiring $\ge 2$ distinct CORE domain skills; generic soft skills like "analytical" or "problem solving" are excluded from awarding points), Experience (0–20).
     - *Strict 60% Qualification Bar:* Any role scoring below 60% is rejected, eliminating 40% false positives.
   
   **Return Type (`MatchResult`):**
   Must return a `MatchResult` object supporting:
   - Tuple unpacking: `score, reasoning, matching, missing = result`
   - Attribute access: `result.score`, `result.reasoning`
   - Dict-style lookup: `result['score']` and `result.get('score', 0)`
 
3. **`generate_text()` Public Method Contract:**
   ```python
   def generate_text(self, prompt: str, default_fallback: str = "", **kwargs) -> str
   ```
   Mandatory public method on `AIClient` for profile summaries, ATS bullets, and arbitrary LLM text tasks. Uses operational Gemini API if configured; otherwise dispatches to `pending_question.json` File-Based IPC handshake without terminal stdin blocking.

4. **Job Discovery Disk Persistence Contract (`04_job_discovery.py`):**
   Upon identifying a qualified job (`score >= 60`):
   - Dynamically sanitize folder name: `profiles/<profile>/output/applications/<Company>_<Role>/`
   - Immediately write `Job_Description.md` (UTF-8 markdown) and `job_details.json` to the application folder *before* calling `process_batch()`.
   - Append `jd_path` and `description` to the `job_entry` recorded in `search_manifest.json`.

5. **`ProfileContext` Constructor Contract:**
   ```python
   def __init__(self, profile_path=None, base_path=None)
   ```
   Must expose properties: `.output_dir`, `.manifest_path`, `.tracker_path`, `.profile_dir`, `.cdp_url`, `.candidate_name`, `.first_name`, `.last_name`, `.config`, `.resume_text`, `.taxonomy_skills`, `.ats_answers`, `.auto_learned_truths`
 
6. **`BrowserManager` Unified Interface:**
   Must expose `.get_context()`, `.new_page()`, and `.close()`, reusing existing pages and bringing them to the foreground via `.bring_to_front()`.
 
7. **`answer_screening_question()` Contract:**
   ```python
   def answer_screening_question(self, question, candidate_profile=None,
                                  options=None, control_type=None,
                                  resume_text=None, **kwargs) -> str
   ```
 
8. **`save_config()` Atomicity Contract:** Must use temporary file + `os.replace()`. Direct `open("w")` on `candidate_config.json` is forbidden.

9. **`arbitrate_card_fit()` Public Method Contract (`AIClient`):**
   ```python
   def arbitrate_card_fit(self, title: str, card_skills: list = None, exp_text: str = "", candidate_profile: dict = None) -> tuple[bool, str]
   ```
   Tier 2B Cognitive Card Arbitration: Evaluates whether an unfamiliar, abbreviated, or creative job role on the search results page conceptually aligns with candidate domain, skills taxonomy, and seniority tier. Evaluates domain acronyms and incompatible verticals dynamically derived from `cognitive_profile.json` (zero hardcoded strings).

10. **`analyze_and_expand_designations()` Public Method Contract (`AIClient`):**
    ```python
    def analyze_and_expand_designations(self, resume_text: str, candidate_exp: float, current_keywords: list, market_seen_titles: list = None) -> list[str]
    ```
    Tier 4 Starvation Auto-Healing: Inspects `resume.md` and candidate's total experience alongside live market titles seen during search starvation to infer and return 5–8 high-yield senior designations strictly within the candidate's synthesized domain.

11. **`synthesize_cognitive_profile()` Public Method Contract (`AIClient`):**
    ```python
    def synthesize_cognitive_profile(self, force_refresh: bool = False) -> Dict[str, Any]
    ```
    Analyzes `resume.md` and candidate configuration at runtime to derive: `candidate_domain`, `years_of_experience`, `seniority_level`, `core_domain_skills`, `generic_soft_skills`, `domain_acronyms`, `incompatible_verticals`, and `search_cycles`. Saves atomically to `profiles/<profile>/output/cognitive_profile.json`.

12. **`get_active_search_cycle()` & `advance_search_cycle()` Contracts (`AIClient`):**
    ```python
    def get_active_search_cycle(self) -> List[str]
    def advance_search_cycle(self) -> int
    ```
    Cycles through dynamically inferred designations in batches of 5–8 titles (Cycle 1 core, Cycle 2 seniority/lateral, Cycle 3 specialized/functional) and advances to the next cycle index across runs.

13. **Multi-Session Persistent Deduplication Ledger Contract (`core/utils/profile_context.py` & `core/04_job_discovery.py`):**
    ```python
    ctx.load_processed_ledger() -> ProcessedLedger (subclasses dict with set API parity)
    ctx.add_to_processed_ledger(item: str, status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs)
    ```
    Persists evaluated, rejected, external-applied, or qualified job URLs and composite keys (`clean_company::clean_title`) to `profiles/<profile>/output/processed_ledger.json` alongside structured metadata (`status`, `company`, `title`, `score`, `timestamp`). Provides $O(1)$ deduplication lookup speed, case/whitespace normalization, and backward compatibility with legacy list schemas.
    **CRITICAL LEDGER RULE:** Solitary job titles must NEVER be added to `processed_ledger.json` (e.g., adding just `"Senior Accountant"`). Doing so blocks all applications to that title across the entire market. Only composite keys (`f"{clean_company}::{clean_title}"`) and job URLs are permitted in the ledger.

14. **Discovery Recency Filter Contract (`04_job_discovery.py`):**
    All discovery searches must include platform-level freshness parameters (`&jobAge=3` on Naukri; `&f_TPR=r259200` on LinkedIn) derived from `target_jobs.job_age_days` (default 3 days) to eliminate stale postings.

15. **Zero-API Cognitive IPC Protocol Contract (`ai_client.py`):**
    When `GEMINI_API_KEY` is not present, `AIClient` delegates reasoning to Google Antigravity 2.0 via `profiles/<profile>/output/pending_question.json`. Supports 5 distinct task types:
    - `PROFILE_SYNTHESIS`: Cognitive profile extraction from resume markdown.
    - `JOB_EVALUATION`: Two-stage semantic and factual qualification scoring ($0-100\%$).
    - `RESUME_TAILORING`: Targeted summary adaptation and core competencies reordering.
    - `SCREENING_QUESTION`: Portal chatbot / Easy Apply modal form input resolution.
    - `STARVATION_EXPANSION`: Designation queue expansion on 0 matches.
    The agent polls `pending_question.json` at 0.5s intervals and resumes immediately upon answer ingestion, unlinking the file. Terminal `stdin` is strictly prohibited.

16. **LinkedIn Easy Apply Modal Automation Contract (`05_apply_jobs.py`):**
    `LinkedInApplyHandler` manages native LinkedIn Easy Apply multi-step modal automation:
    - Traverses modals inside `div.jobs-easy-apply-modal` or `div[data-test-modal]`.
    - Handles text inputs, phone fields, single-select radios, and native/custom dropdowns.
    - Resolves screening queries through `AIClient.answer_screening_question()`.
    - Automatically uploads tailored ATS PDF (`input[type='file']`) when resume upload step appears.
    - Advances through multi-step forms using "Next", "Review", and commits via "Submit application".
    - Detects unresolvable errors and clicks modal dismiss / discard without leaving dangling state.

---

## DIRECTIVE 5: PLATFORM ISOLATION & DOM SAFETY

1. **Decoupled Handlers:** Fixes and enhancements to Naukri automation scripts (`02_profile_sync_naukri.py`, `02b_naukri_fast_resume_upload.py`, Naukri scrapers/solvers) must never touch, break, or mutate LinkedIn scripts (`03_profile_sync_linkedin.py`, LinkedIn Easy Apply handlers), and vice versa.

2. **Container-Isolated Scrolling:** Never issue page-level scroll commands when a modal or chatbot drawer is active. Scroll exclusively within the identified dialog container (`.chatbot_MessageContainer` on Naukri; `.jobs-easy-apply-modal` on LinkedIn).

3. **Contenteditable Typing Standard:** When populating `contenteditable="true"` containers (Naukri chatbot, LinkedIn ProseMirror), never use `.fill()`. Always:
   - Focus the element via `.click(force=True)`
   - Select all (`Control+A` / `Meta+A`)
   - Clear (`Backspace`)
   - Emit text via `page.keyboard.type(str(answer), delay=30)` or `page.keyboard.insert_text()`

4. **Network Navigation Safety:** Never use `wait_until="networkidle"` for Naukri pages due to persistent telemetry WebSockets. Always use `wait_until="domcontentloaded"` paired with explicit selector polling.

5. **No Dangling Blank Tabs:** Scripts must never navigate to `about:blank` as a final state and terminate. The browser session must remain active, focused on the relevant application page.

6. **Expanded UI Control Detection & Greedy Selector Prohibition:**
   `detect_ui_control()` must recognize:
   - File uploaders (`input[type='file']`)
   - Date inputs (`input[type='date']`, `input.datePicker`)
   - Yes/No toggle pills (`div.togglePill`, `button.toggle`, `div[class*='toggle']`, `div.yesNoToggle`)
   - Custom radio wrappers (`label.ssrc__label`, `div.customRadio`, `div.radioItem`, `label[class*='radio']`, `ul.ChoiceList li`)
   - Multi-select chips (`div.clickableChip`, `div.choiceChip`)
   - Standard `<select>` and custom dropdowns
   - Contenteditable text areas
   Never use greedy `div[class*='chip']` without filtering — it matches Naukri's `.chipMsg` branding logo. Strictly ignore `.chipMsg` to prevent false radio detection.

7. **Single-Quote Safety in Selectors:** When injecting dynamic text into Playwright `:has-text()` selectors, always escape single quotes:
   ```python
   safe_opt = matched_option.replace("'", "\\'")
   f"div.radioItem:has-text('{safe_opt}')"
   ```

8. **Browser Tab Hygiene & Non-Hijacking Execution:**
   `cleanup_browser_tabs(context, tracked_pages, active_page)` must track only Playwright pages created by discovery workers, and never blindly loop through `context.pages` closing user browsing tabs.

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
   - UI control classifications (`CONTENTEDITABLE`, `RADIO_CHIP`, `FILE_UPLOAD`, `DROPDOWN`, `DATE_INPUT`, `UNKNOWN`)
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
   | `REQUIRES_MANUAL_INTERVENTION` | Unanswerable mandatory field or stuck loop encountered |

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
**Rule:** `is_title_allowed()` and `evaluate_job_match()` Stage 1 must reject titles containing ANY negative keyword unconditionally. The presence of a positive target keyword must NOT override a negative keyword match.

### C7: 3x Stuck Question Loop Breaker
**Rule:** `_handle_chatbot_loop()` must track consecutive question repeats (`active_q == last_processed_q`). If any question repeats $\ge 3$ times without progress, do not burn the remaining iteration budget. Immediately abort the loop, log `REQUIRES_MANUAL_INTERVENTION`, write `[ABORTED_STUCK_3X]` into `ques_ans_chatbot.json`, and return `"FAILED"`.

### C8: Bug 4 Unknown Control Fallback & Detached DOM Protection
**Rule:** When `detect_ui_control()` returns `UNKNOWN`: verify if a `contenteditable` input is actually visible before attempting typing. If no visible input field exists, do NOT force text typing into detached DOM nodes. Extract all visible interactive labels/chips in the drawer and route through `pending_question.json` File-Based IPC so AG 2.0 can inspect the UI state and supply the appropriate action or value.

### C9: Platform Rejection Banner & Premature Drawer Closure Guardrail
**Rule:** `_handle_chatbot_loop()` in `05_apply_jobs.py` must actively detect platform rejection banners ("Oops! Your application was not accepted due to incomplete information...", "application was not accepted", "unable to apply") and abort immediately (`FAILED_PLATFORM_REJECTED`) rather than looping blindly across 25 iterations. Furthermore, if the chatbot drawer unmounts or closes prematurely (`not resolver.is_drawer_open()`), the loop must re-verify completion status and abort immediately (`DRAWER_CLOSED`) instead of hanging on empty queries.

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

### D1: Composite Ledger Deduplication (Anti-Title Starvation)
**Rule:** `04_job_discovery.py` must NEVER insert raw, solitary job titles into `processed_ledger.json`. Adding bare titles causes the agent to reject every subsequent job with that title across all other companies in the market. Deduplication must strictly use the composite key: `f"{clean_company}::{clean_title}"` or direct Job URLs.

### D2: Anchored Experience Parsing & Company Age Filtering
**Rule:** When parsing required experience from job descriptions in `ai_client.py` and `04_job_discovery.py`, regex matching must be anchored to requirement phrases (`minimum`, `exp`, `years of experience`, `relevant experience`). Never match naked `r'(\d+)\s*years'` across entire JD text, which matches company founding history (e.g., *"Serving clients for 25+ years"*) and causes false auto-rejections of candidates. Any parsed number $> 20$ must be ignored unless candidate experience itself exceeds 18 years.

### D3: Cross-Functional Domain Title Overrides
**Rule:** Non-technical domain roles (Finance, Operations, Accounting, Legal, Supply Chain) frequently list software tools like "SQL database", "Accounting Software", or "Python scripting". The Incompatible Vertical hard gate in `evaluate_job_match()` must inspect the job title first. If the job title aligns with the candidate's core domain, technical tools mentioned in the JD must NOT trigger an out-of-domain tech vertical rejection.

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
