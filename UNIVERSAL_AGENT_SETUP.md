# Universal Autonomous Career Agent — Setup & Execution Guide

Welcome to the **Universal Autonomous Career Agent** (`F:\JOB AI AGENT`). This system is an enterprise-grade, multi-agent autonomous pipeline engineered to execute end-to-end job discovery, cognitive profile synthesis, factual resume tailoring, and automated ATS application submission across platforms including LinkedIn and Naukri.

This guide details environment setup, candidate profile sandboxing, cognitive configuration, and autonomous daemon execution.

---

## 1. Core Architecture & System Capabilities

- **Multi-Profile Sandboxing:** Dynamically loads candidate parameters, taxonomy skills, and credentials from `profiles/<profile_name>/` at runtime with zero code hardcoding. Multiple candidate profiles can run independently without collision.
- **Cognitive Profile Synthesis:** Autonomously analyzes human markdown resumes (`resume.md`) to extract domain taxonomy, seniority levels, core competencies, and search cycle designations (`cognitive_profile.json`).
- **Dual-Brain Cognitive Engine:**
  - **Gemini Hosted Mode:** Leverages Google Gemini models via API key when `GEMINI_API_KEY` is provided.
  - **Zero-API Mode (Primary):** When no API key is set, delegates reasoning to **Google Antigravity 2.0** via non-blocking File-Based IPC (`pending_question.json`). Eliminates terminal `stdin` freezes.
- **Two-Stage Job Evaluation & Gating:**
  - **Stage 1:** Deterministic hard filters check absolute negative keywords (C6 Guardrail), domain title alignment, and anchored experience bands.
  - **Stage 2:** Calibrated factual scoring runs first. Antigravity 2.0 IPC arbitration is strictly gated to the **borderline match score window ($40\% \le \text{score} \le 65\%$)**. High-fit roles ($\ge 60\%$) qualify instantly; blatant out-of-domain roles drop at Stage 1 ($0\%$).
- **Factual ATS Resume Tailoring:** Analyzes Job Descriptions to extract technical tokens (`C++`, `SAP S/4HANA`, `US GAAP`, etc.), dynamically adapts the Professional Summary, and prioritizes core competencies by keyword density. **Strictly zero hallucinations or invented credentials.**
- **Native Form Solving & Modal Stability:**
  - **LinkedIn Easy Apply:** Native modal automation with Guardrail H1 remediation (zero blind `options[0]` fallbacks, Antigravity IPC fallback for ambiguous dropdowns/radios, and automated modal dismissal with "Discard application" confirmation).
  - **Naukri Chatbot:** Container-isolated scrolling (`.chatbot_MessageContainer`), React synthetic event dispatch for `contenteditable`, and Guardrail C9 premature drawer closure / platform rejection detection.
- **Multi-Session Persistent Deduplication Ledger:** High-performance hybrid dictionary (`ProcessedLedger`) storing structured metadata (`status`, `company`, `title`, `score`, `timestamp`) with $O(1)$ lookup speed and atomic `.tmp` + `os.replace` disk persistence.
- **Three-Tier Verification & Stealth:** Physically verifies confirmation pages and DOM ledger history (`/myapply/historypage`). Uses randomized typing jitter (45–130ms), visual scanning pauses (400–900ms), and 30-minute batch cycles to emulate human browsing.

---

## 2. Directory Structure

The repository is structured as follows:

```text
F:\JOB AI AGENT\
│
├── core/                                 # Production execution pipeline
│   ├── 01_ai_analyzer.py                 # Resume analyzer & cognitive profile synthesizer
│   ├── 02_profile_sync_naukri.py         # Naukri profile sync (zero-delay non-blocking wait)
│   ├── 02b_naukri_fast_resume_upload.py  # Standalone fast resume PDF uploader
│   ├── 03_profile_sync_linkedin.py       # LinkedIn profile updater
│   ├── 04_job_discovery.py               # Multi-cycle job scraper & domain evaluator
│   ├── generate_factual_tailored.py      # Factual ATS resume tailor & PDF compiler
│   ├── 05_apply_jobs.py                  # Form solver (LinkedIn Easy Apply & Naukri Chatbot)
│   ├── ai_client.py                      # Dual-brain cognitive engine & IPC bridge
│   ├── continuous_career_agent.py        # Master continuous autonomous daemon
│   ├── scrapers/                         # Platform-specific scraping implementations
│   │   ├── base_scraper.py               # Common scraper interface & recency filters
│   │   ├── linkedin_scraper.py           # LinkedIn job search scraper
│   │   └── naukri_scraper.py             # Naukri job search scraper
│   └── utils/                            # Shared core utilities
│       ├── profile_context.py            # ProfileContext & ProcessedLedger hybrid dict
│       └── browser_manager.py            # Chrome DevTools Protocol (CDP) session manager
│
├── profiles/                             # Candidate profiles directory (Autonomous Sandboxes)
│   └── <candidate_name>/                 # Individual candidate sandbox folder
│       ├── candidate_config.json         # Candidate details, credentials, CTC, target filters
│       ├── resume.md                     # Master markdown resume (Factual source of truth)
│       └── output/                       # Runtime outputs and multi-session state
│           ├── applications/             # Per-job tailored PDF resumes & job_details.json
│           ├── cognitive_profile.json    # Synthesized candidate taxonomy & search cycles
│           ├── processed_ledger.json     # O(1) multi-session persistent deduplication ledger
│           ├── search_manifest.json      # Active execution batch manifest
│           ├── applications_tracker.csv  # Canonical application audit trail
│           └── pending_question.json     # Antigravity 2.0 cognitive IPC exchange file
│
└── docs/                                 # Authoritative documentation & blueprints
    ├── WORKSPACE_RULES.md                # 8 mandatory directives & 12 bug prevention guardrails
    ├── ARCHITECTURE_REFERENCE.md         # Comprehensive system architecture & data contracts
    └── GEMINI_WEB_AI_PROMPTS.md          # 3-step onboarding prompts for Gemini Web AI
```

---

### 3. Environment & Prerequisites Setup

### A. Python Environment
Ensure Python 3.10+ is installed:
```bash
pip install playwright markdown
playwright install chromium
```
*(Optional: install `google-genai` if utilizing Gemini API hosted mode).*

### B. Launch Isolated Chrome Profile with CDP (Crucial Step)
The agent operates through the Chrome DevTools Protocol (CDP on port 9222) to attach to an active browser session with established login cookies.

1. Open PowerShell or Command Prompt.
2. Launch a dedicated Chrome instance:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeProfiles\JobAgentProfile" --no-first-run --no-default-browser-check
```
3. In this Chrome window, **log in to your LinkedIn and Naukri accounts**. Keep this browser window open.

### C. AI Intelligence Mode Configuration

#### Mode 1: Zero-API Antigravity 2.0 Mode (Recommended & Default)
No API key is required. When `GEMINI_API_KEY` is not set, `AIClient` automatically routes cognitive reasoning tasks (profile synthesis, borderline job match arbitration, screening questions) to `profiles/<profile>/output/pending_question.json`.

#### Mode 2: Gemini API Hosted Mode (Optional)
If you prefer hosted Gemini API execution, export your API key before launching:
- **Windows (PowerShell):**
  ```powershell
  $env:GEMINI_API_KEY="your-api-key-here"
  ```
- **Linux/macOS:**
  ```bash
  export GEMINI_API_KEY="your-api-key-here"
  ```

---

## 4. Configuring Candidate Profiles

The agent supports any number of candidate profiles inside `profiles/`.

### Step 4.1: Create Profile Sandbox Directory
Create a folder inside `profiles/` (e.g., `profiles/john_doe/`).

### Step 4.2: Populate `resume.md`
Add the candidate's master resume in markdown format (`profiles/<candidate_name>/resume.md`):
- Maintain strict reverse-chronological order.
- Include all quantifiable metrics, employers, designations, and technologies.
- This file is the **strictly factual ground truth**. The tailoring engine will never invent details outside this text.

### Step 4.3: Populate `candidate_config.json`
Configure `profiles/<candidate_name>/candidate_config.json`:
- **`candidate`**: Full name, contact info, current/expected CTC, notice period, location, and CDP URL (`http://127.0.0.1:9222`).
- **`target_jobs`**: Target keywords, locations, minimum salary, `job_age_days` (default 3), and `negative_keywords`.
- **`taxonomy_skills`**: Core domain skills (`primary` and `secondary`).
- **`ats_answers`**: Factual ground-truth answers for common application fields (e.g. total experience, legal authorization).
- **`auto_learned_truths`**: Pre-seeded or autonomously learned answers to screening questions.

### Step 4.4: Synthesize Cognitive Profile
Run the AI analyzer to understand the candidate's background and produce `cognitive_profile.json`:
```bash
python core/01_ai_analyzer.py --profile profiles/<candidate_name>
```

---

## 5. Running the Autonomous Agent

Launch the master continuous career agent:

```bash
python core/continuous_career_agent.py --profile profiles/<candidate_name>
```

### Supported CLI Flags:
| Flag | Description |
|:---|:---|
| `--profile <path>` | Path to candidate profile directory (e.g., `profiles/john_doe`). If omitted, auto-discovers the first directory in `profiles/`. |
| `--analyze` | Forces re-synthesis of `cognitive_profile.json` before starting discovery. |
| `--sync-profile` | Triggers Naukri and LinkedIn profile updates before the discovery loop. |
| `--single-cycle` | Executes a single discovery, tailoring, and application cycle, then exits. |

### Execution Cycle Walkthrough:
1. **Discovery (`core/04_job_discovery.py`):**
   - Scrapes fresh jobs using platform recency filters (`&jobAge=3` on Naukri, `&f_TPR=r259200` on LinkedIn).
   - Checks the $O(1)$ persistent ledger (`processed_ledger.json`) to skip previously evaluated jobs.
   - Evaluates match scores via two-stage filtering: $\ge 60\%$ qualifies, $< 40\%$ rejects, and $40-65\%$ invokes Antigravity 2.0 IPC arbitration.
2. **Resume Tailoring (`core/generate_factual_tailored.py`):**
   - Extracts technical keywords from the job description.
   - Factual summary adaptation and bullet point reordering render an ATS-optimized PDF resume in `profiles/<profile>/output/applications/<Company>_<Role>/`.
3. **Application Execution (`core/05_apply_jobs.py`):**
   - **LinkedIn:** `LinkedInApplyHandler` navigates multi-step Easy Apply modals, selects radios/dropdowns without blind fallbacks, uploads the tailored PDF, and submits.
   - **Naukri:** `ChatbotResolver` solves interactive drawer questions and attaches the tailored PDF.
4. **Verification & Cooldown:**
   - Verifies submission in platform history ledgers and logs to `applications_tracker.csv`.
   - Sleeps for 30 minutes before advancing to the next search cycle.

---

## 6. Tracking & Status Codes

All applications are tracked in `profiles/<profile_name>/output/applications_tracker.csv`.

| Status Code | Description |
|:---|:---|
| `VERIFIED_SUCCESS` | Application successfully submitted and confirmed via DOM ledger check. |
| `SUBMITTED_SUCCESSFULLY` | Application successfully submitted via standard confirmation screen. |
| `REQUIRES_MANUAL_INTERVENTION` | Form encountered an unresolvable required field; logged for manual review. |
| `REDIRECT_EXTERNAL` | Job requires external company portal application (Workday, Taleo, etc.). |
| `DOMAIN_GATED` | Rejected during Stage 1 due to negative keywords or out-of-domain title. |
| `LOW_SCORE` | Evaluated and rejected due to low semantic match score ($< 60\%$). |
| `FAILED_PLATFORM_REJECTED` | Platform rejected application due to profile criteria mismatch. |
