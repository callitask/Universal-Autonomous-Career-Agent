# Platform Knowledge & Engineering Reference: Naukri.com

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

