# Platform Knowledge & Engineering Reference: Naukri.com

> **Document Version:** 2.0 — Dual-Channel Batch/Single IPC, Structured SEO Routing & Guardrail Alignment  
> **Last Updated:** 2026-09-21  
> **Authority:** Operational reference for portal behaviors, DOM patterns, and dual-channel IPC.

This document serves as the permanent knowledge repository for Naukri.com portal behavior, routing mechanics, DOM patterns, and historical traps encountered during autonomous agent operations.

---

## 1. URL Architecture & Search Routing

### The Canonical Structured SEO Slug Standard
Naukri's search engine relies on structured SEO slug URLs rather than generic parameter routing:

```
https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}?experience={years}&jobAge={days}&ctcFilter={bracket}
```

For pagination (Page 2+):
```
https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}-{page_num}?experience={years}&jobAge={days}&ctcFilter={bracket}
```

### Critical URL Routing Traps

1. **The `/jobs?k=` Redirect Trap:**
   - Constructing `https://www.naukri.com/jobs?k=...&l=...` causes Naukri's server to redirect immediately to `https://www.naukri.com/jobs-in-india?k=...`.
   - On this redirect page, Naukri fails to render `.srp-jobtuple-wrapper` components, resulting in **0 job cards found** and triggering false starvation.
   - **Rule:** Never use `/jobs?k=`. Always route directly to `{role_slug}-jobs-in-{loc_slug}`.

2. **The Pre-Encoded `%20` Slug Corruption Trap:**
   - If a search query is URL-encoded before slug generation (e.g. `urllib.parse.quote("java technical lead")` $\rightarrow$ `"java%20technical%20lead"`), and then passed into standard slug stripping (`re.sub(r'[^a-z0-9]+', '-', text)`), the `%` character is stripped, producing `"java-20technical-20lead"`.
   - This causes the browser to navigate to `https://www.naukri.com/java-20technical-20lead-jobs-in-bangalore`, which displays literal "java 20technical 20lead" in the search box and yields 0 results.
   - **Rule:** Always slugify raw plain text tokens: `re.sub(r'[^a-z0-9]+', '-', clean_q.lower()).strip('-')`.

3. **The Comma Trap (`%2C` $\rightarrow$ `"2c"`):**
   - Commas present in keywords or location strings (e.g. `"java technical lead,"`, `"Bangalore, Karnataka"`) encode as `%2C`.
   - Naukri's query parser treats `%2C` as the literal text token `"2c"` (searching for `java technical lead 2c in bangalore 2c`), returning **0 jobs**.
   - **Rule:** All tokens must be sanitized via `clean_search_token()` to strip commas, semicolons, and special characters before query construction or typing.

---

## 2. Header Search Bar & Suggestor Mechanics

When automating search via the Naukri global header (`execute_naukri_header_search`):

1. **Input Clearing Protocol:**
   - Existing text inside `.nI-gNb-sb__keywords input.suggestor-input` must be forcefully removed using `Control+A` + `Backspace`.
   - **Concatenation Trap:** If multiple keywords are queried sequentially without total input wiping, Naukri preserves previous chips, concatenating them into a single string (e.g. `"java technical lead, backend architect java, microservices architect"`), which returns 0 results.
2. **Auto-Comma Stripping:**
   - Clicking a suggestion chip from `.nI-gNb-sugg div.opt` or `.drop-layer` automatically appends `", "` to the input field.
   - Automation must proactively execute in-DOM JavaScript:
     ```javascript
     el.value = el.value.replace(/[,;\s]+$/, '').trim();
     el.dispatchEvent(new Event('input', { bubbles: true }));
     ```
3. **Location Dropdown Selection:**
   - Typing location requires clicking the top dropdown tuple (`.drop-layer .tuple-wrap div.opt`) to bind Naukri's internal React geo-filter state.

---

## 3. DOM Selectors & Component Reference

| Component | Verified Selector | Notes |
|:---|:---|:---|
| Job Card Wrapper | `div.srp-jobtuple-wrapper` | Modern React SRP tuple container (20 per page) |
| Job Title Link | `a.title, a.job-title` | Direct anchor to job details |
| Company Name | `a.comp-name, .comp-name` | Employer or recruitment firm |
| Experience Metadata | `span.exp-wrap span.exp` | e.g. "8-12 Yrs" |
| Match Score Box | `div.styles_JDC__match-score__VnjLL` | ATS fit signals (`Keyskills`, `Location`, `Experience`) |
| Job Highlights List | `ul.styles_JDC__job-highlight-list__QZC12 li` | Recruiter eligibility prerequisites (pre-flight gated before unclamp) |
| Unclamp JD | `span.styles_rm-link__RgrMs` | "Read More" button to reveal full description |
| Native Apply Button | `button#apply-button, button.apply-button` | Triggers 1-click or chatbot drawer |
| External Save Button | `button#save-button, .styles_save-job-button__k2e8x` | Bookmarks external company website roles |
| Chatbot Drawer | `.chatbot_DrawerContentWrapper` | Scoped container for screening questions |
| Chatbot Submit Button | `.sendMsgbtn_container .send:not(.disabled) .sendMsg` | Clickable `Save` div (NOT a `<button>`) |

---

## 4. Browser Tab Hygiene Standards

- Automation must adopt `context.pages[0]` on startup.
- Never spawn unbounded tabs across discovery cycles.
- Detail tabs opened to inspect full job descriptions (`context.new_page()`) must be destroyed immediately in `finally:` blocks.
- Exactly 1 browser tab must remain active during normal daemon execution.

---

## 5. Diagnostic & Auto-Healing Tools Reference

- **`/browser`**: Live inspection of active Chrome session via CDP.
- **`chrome-devtools`**: Automated DOM tree inspection (`take_snapshot`) and in-page script evaluation (`evaluate_script`).
- **`troubleshooting`**: Diagnoses CDP connection drops, port 9222 conflicts, or Chrome remote debugging issues.
- **`debug-optimize-lcp`**: Diagnoses page load latency, TTFB bottlenecks, and render blocking on heavy SPA portal pages.
- **`a11y-debugging`**: Deep accessibility audit of hidden modal controls and focus management in application drawers.

---

## 6. Starvation, Deduplication Saturation & Self-Healing Protocol

### Root Cause Analysis: The Zero-Application Loop
1. **Keyword Saturation in Persistent Ledger:**
   - Over dozens of continuous daemon sweeps (e.g. Cycle #1 to #35), when a profile's target keywords are restricted to narrow variations of a single role (e.g., 8 permutations of "Technical Lead"), the agent processes all available jobs on the portal for that location and adds them to `processed_ledger.json` (accumulating 1,800+ entries).
   - Once all matching cards on pages 1–3 are in the ledger or gated by negative companies (TCS, Infosys), every card extracted on SRP is skipped:
     ```python
     if can_url in processed_ledger or composite_key in processed_ledger:
         continue
     ```
   - Sourced jobs drop to 0, causing the cycle to finish with 0 applications.
2. **Latent Fallback Corruption Trap:**
   - When 0 jobs qualify, Tier 4 Starvation Recovery triggers `ai.analyze_and_expand_designations()`.
   - If Antigravity IPC (`pending_question.json`) or Gemini API times out, the previous fallback mechanically stripped prefixes and prepended `"Assistant Manager"` or `"Lead"`, generating invalid titles (e.g., `"Assistant Manager - Tech Java"`, `"Assistant Manager - Technical - Microservices"`).
   - These corrupted titles yielded 0 results on Naukri, locking the engine into an infinite starvation loop.
3. **Latent `taxonomy_skills` Dict Crash:**
   - `naukri_it_skills` contains dictionary objects (`{'skill_name': 'Core Java', ...}`). Unchecked `.strip()` calls crashed profile synthesis.

### Permanent Resolution & Self-Healing Standard
1. **Config-First Intervention (Guardrail C23):**
   - When the user observes no jobs being applied to, the agent must **never touch or edit `04_job_discovery.py` or `05_apply_jobs.py`**.
   - The agent inspects `resume.md` and expands `candidate_config.json` with clean, diverse, high-yield senior designations (e.g., for a 10-year Java Architect: *Principal Software Engineer*, *Solutions Architect*, *Staff Software Engineer*, *Enterprise Integration Architect*, *Microservices Architect*, *Distributed Systems Architect*).
2. **Domain-Aware Title Fallback:**
   - `analyze_and_expand_designations()` and `synthesize_cognitive_profile()` use domain-aware mapping. For technical engineering tracks ($\ge 8$ years), senior roles map to *Principal / Staff / Solutions Architect*, completely eliminating corporate banking prefixes like *"Assistant Manager"*.
3. **Multi-Type Skill Parsing:**
   - `taxonomy_skills` parser handles both primitive strings and structured dictionaries (`skill_name`), guaranteeing 100% crash resilience.

---

## 7. Two-Tier Job Highlights DOM Mechanics & Multi-Bullet Isolation Protocol

### The Naukri Highlights Architecture
Naukri renders a dedicated `Job Highlights` block situated immediately above the main Job Description container:
```html
<ul class="styles_JDC__job-highlight-list__QZC12">
    <li>B.Com/M.Com/CA Inter with 2-5 years experience in accounting</li>
    <li>Coordinate with statutory and internal auditors for quarterly reporting</li>
</ul>
```

### Empirical Findings:
1. **Prerequisite Nature of Highlights:**
   - In Naukri's platform design, recruiters use the Highlights list for hard prerequisites (degrees, certifications, experience prerequisites).
   - In the general JD body, terms like `"CA"` or `"Auditor"` may appear in collaborative contexts (*"liaise with CA firms"* or *"coordinate with internal auditors"*).
   - In `Job Highlights`, however, bullet items are almost exclusively candidate qualifications.
2. **Tier 1 Scraper Pre-Flight Gating:**
   - Instead of immediately expanding the full JD via `span.styles_rm-link__RgrMs` (which costs 800–1200ms of layout thrashing), `04_job_discovery.py` extracts `ul.styles_JDC__job-highlight-list__QZC12 li` directly upon page load.
   - It runs word-boundary regex checks against `candidate_config.json["target_jobs"]["negative_keywords"]`.
   - If any negative keyword matches (e.g. `\bCA\b`, `\bCA Intermediate\b`), the page is closed immediately, `domain_gated` is recorded in `processed_ledger.json`, and the pipeline proceeds to the next card. This saves ~1.5 seconds per disqualified role.
3. **The Multi-Bullet Regex Isolation Standard:**
   - **The Bug:** Historically, evaluating exemption regexes (such as `re.search(r'\b(?:coordinate|liaise)\s+with\b', highlights_text)`) across the combined multiline highlights block caused a fatal flaw. Bullet 2's phrase `"coordinate with statutory auditors"` caused the entire highlights block to be treated as a collaboration context, exempting Bullet 1's `"CA Inter with 2-5 years experience"`.
   - **The Live Fix:** All multiline blocks MUST be split into individual lines (`highlights_content.splitlines()`) and evaluated in strict isolation. An exemption in one bullet can never bleed into or exempt adjacent bullets.
4. **Exclusion from Responsibility Headers:**
   - In `_analyze_jd_work_capability()`, `"job highlights"` must never be included in `resp_headers`. Highlights are recruiter prerequisites, not day-to-day duties. Treating them as duties awards positive capability points to disqualified candidates.

---

## 8. Three-Daemon Architecture & The 90-Second Recruiter Question SLA

To prevent background automation processes from freezing or timing out on novel recruiter screening questions, the system implements a Three-Daemon Architecture:

### Daemon Topology
1. **Daemon 1: Continuous Discovery & Application Runner (`continuous_career_agent.py`)**
   - Connects to Chrome on port 9222 via CDP.
   - Traverses SRP cards, un-clamps JDs, gates, renders tailored ATS PDF resumes, uploads resumes, and navigates chatbot drawers.
   - When encountering a novel question not in `auto_learned_truths` or config heuristics:
     - Writes the question, control type, options, and full prompt to `profiles/<profile>/output/pending_question.json`.
     - Sets `"status": "PENDING"`.
     - Polls `pending_question.json` at 0.5s intervals for up to 90 seconds without terminal blocking.
2. **Daemon 2: Asynchronous IPC Signal Relay (`core/ipc_watcher.py`)**
   - Lightweight, non-blocking process polling `pending_question.json` every 2.0 seconds.
   - When `"status": "PENDING"` is observed, immediately outputs a structured, loud ASCII banner to stdout.
   - Prints question text, options, control type, and prompt snippet.
   - Serves as the real-time telemetry beacon for Daemon 3.
3. **Daemon 3: AG Brain Cron Monitor (Recurring 1-Minute Awake Loop)**
   - Operates as a scheduled recurring cron job (`* * * * *`) within the AG Brain agentic environment.
   - Wakes up every 60 seconds, inspects Daemon 2 logs, and checks `pending_question.json`.
   - Reads `resume.md` and `candidate_config.json` to synthesize an authentic, grounded, factual answer.
   - Sets `"status": "ANSWERED"` and commits the answer string or JSON object.
   - Guaranteed SLA: Daemon 1 receives the answer well before its 90-second timeout, unlinks the file, and submits the chatbot form.

---

## 9. Third-Party Syndicated Job Redirection Latency & Navigation Timeout Protocol

### The Third-Party Redirect Hang
Certain job listings aggregated on Naukri (e.g., outsourced postings via Purview India, Leading Client, or syndication brokers) route through intermediate redirects or external tracker gateways that either stall indefinitely or exceed default Playwright navigation limits.

### Empirical Two-Stage Navigation Fallback Standard:
1. **Stage 1 (`commit` - 12,000ms):**
   - Wait until HTTP response headers are received and document navigation has committed.
2. **Stage 2 (`domcontentloaded` - 15,000ms):**
   - Wait until DOM content is loaded and available for interaction.
3. **Resilience & State Recovery:**
   - If either stage times out or throws an unhandled network error:
     - Catch `PlaywrightTimeoutError` / `Exception` cleanly.
     - Log `[ERROR] Page navigation failed to load job URL within timeout: <url>`.
     - Record `FAILED` in `applications_tracker.csv`.
     - Return control cleanly so the caller advances to the next job in the discovery manifest without browser crash or zombie tabs.

---

## 10. Negative Keywords: The Standalone Generic Noun Collision Trap

### Root Cause Analysis:
In domain-specific professions such as Finance, Accounting, Audit, and Compliance, job descriptions routinely list business software tools:
- *"B.Com graduate with skills in Accounting Software, Tally, GST"*
- *"Proficient in ERP Software, SAP, or Oracle Financials"*

When a configuration includes broad standalone words like `"Software"` in `target_jobs.negative_keywords`:
- Word-boundary regex `\bSoftware\b` matches the phrase *"Accounting Software"*.
- The Gatekeeper falsely rejects ideal accounting postings with `[HIGHLIGHTS GATED: Negative keyword 'Software']`.

### The Composite Term Standard:
- Standalone generic nouns (such as `"Software"`, `"Developer"`, `"Engineer"`) are strictly prohibited in `negative_keywords`.
- Role exclusion filters must always use composite, role-specific terms:
  - `"Software Engineer"`
  - `"Software Developer"`
  - `"Software Development"`
  - `"Full Stack Developer"`
  - `"Backend Engineer"`
- This cleanly excludes tech engineering jobs while preserving accounting and finance roles requiring business software tools.

---

## 11. Free-Text Screening Honesty & Candidate Non-Hallucination Standard

### Chatbot Screening Ground Truth Invariant:
When Naukri's application chatbot presents open-ended or free-text questions concerning tools or ERP systems (e.g. *"Which ERP systems do you have hands-on experience with?"* or *"Explain your experience with SAP/Oracle"*):
1. **Never Hallucinate Unverified Tools:**
   - The AG Brain must NEVER claim or fabricate hands-on experience in enterprise systems that are absent from `resume.md` and `candidate_config.json`.
2. **Factual and Transparent Disclosures:**
   - Clearly state the candidate's actual verified tool stack (e.g. Tally, Advanced MS Excel, Power BI).
   - Honestly disclose lack of prior exposure to the specific platform asked (e.g. *"No direct prior experience in SAP/Oracle; proficient in Tally, Advanced MS Excel, and financial modeling with high adaptability to learn enterprise ERP systems"*).
3. **Preserving Recruiter Trust:**
   - Truthful disclosures ensure candidate integrity and prevent immediate disqualification during technical interview rounds.

---

## 12. Chatbot Radio Chip Constraints & Proficiency Tier Patterns

### Empirical DOM Structure:
On the Naukri chatbot drawer, single-select and multi-select questions are rendered using custom radio/checkbox containers:
```html
<div class="ssrc__radio-btn-container">
    <input type="radio" class="ssrc__radio" id="opt_0" name="choice">
    <label class="ssrc__label" for="opt_0">Beginner</label>
</div>
```
- The Playwright selector strictly targets: `label.ssrc__label:has-text('{safe_opt}')` or `.ssrc__radio-btn-container:has-text('{safe_opt}') label.ssrc__label`.
- Clicking the `<label>` reliably toggles the underlying `<input>` radio, activates React internal component state, and enables the `.send` button container.

### The Proficiency Tiers Pattern & Zero Experience Dilemma:
Recruiters frequently ask practical tool exposure questions with qualitative proficiency chips rather than numeric years:
- Question: *"How much practical experience do you have working on SAP?"*
- Choices: `['Beginner', 'Intermediate', 'Expert']` (no "None" or "0" option provided).

**The Trap:**
- If the AI or heuristic calculates `0` years and outputs `"0"`, `label.ssrc__label:has-text("0")` finds 0 elements.
- The chatbot resolver falls back to typing `"0"` into an inactive or hidden contenteditable field.
- The form stays unanswered, repeats 3 times, triggers Guardrail C7, and aborts the application as `FAILED`.

**The Solution (Guardrail C34):**
1. When options are constrained to proficiency levels, zero experience / novice exposure maps automatically to the lowest proficiency tier:
   `["beginner", "basic", "novice", "entry", "elementary", "foundational", "learning"]`.
2. The answer returned to `execute_chip_selection` MUST exist in `options`. If an un-matched string is returned, the engine forces `ans = options[0]`.
3. If clicking the chosen option fails, the engine retries clicking `options[0]` before attempting any contenteditable fallback.

---

## 13. Dual-Channel File-Based IPC & Signal Routing

The autonomous pipeline communicates with Antigravity 2.0 (AG Brain) via two asynchronous file IPC channels located inside `profiles/<profile>/output/`:

### Channel 1: Batch Card Triage (`batch_question.json` / `batch_answer.json`)
*   **Purpose:** Evaluates an entire batch of SRP cards for a designation in a single handshake ($O(1)$ token overhead) rather than serial $N \times 90$s queries.
*   **Trigger:** Written by `04_job_discovery.py` after collecting cards across result pages.
*   **Timeout / SLA:** 120-second timeout default (`batch_ipc_timeout_seconds`).
*   **Decisions:** `DEEP_SCAN` (proceeds to detail page un-clamping, precision scoring, and application) or `SKIP` (records deduplication in ledger and discards).
*   **Watcher Daemon:** Monitored by `core/ipc_watcher.py` via its shared 2.0s polling loop, emitting structured batch alerts.

### Channel 2: Single-Target Deep Inquiries (`pending_question.json`)
*   **Purpose:** Handles low-latency, single-query arbitration for deep-scan phases:
    1.  **Chatbot Screening Questions (`SCREENING_QUESTION`):** Real-time candidate answers for mandatory recruiter chatbot prompts.
    2.  **Ambiguous Job Qualification (`JOB_EVALUATION`):** Second-opinion scoring for borderline fit scores (40–65% range).
    3.  **Dynamic Resume Tailoring (`RESUME_TAILORING` / `QUESTIONNAIRE`):** Custom impact bullet synthesis and cover letters.
*   **Timeout / SLA:** 90-second SLA (60s for `STARVATION_EXPANSION`).
*   **Handshake Lifecycle:** `PENDING` $\rightarrow$ AG Brain computes answer from candidate ground truths $\rightarrow$ `ANSWERED` with atomic JSON replacement.
