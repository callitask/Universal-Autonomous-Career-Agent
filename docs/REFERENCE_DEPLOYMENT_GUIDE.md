# UNIVERSAL DEPLOYMENT GUIDE
**System:** Anti-Gravity Autonomous Career Operations Engine  
**Architecture:** Variable-Driven, Candidate-Agnostic, Multi-Profile, Batch Architecture v2.0  
**Document Version:** 4.0 — Batch Architecture v2.0, Three-Daemon Runtime, Dual-Channel IPC & C24-C34 Guardrails  
**Last Updated:** 2026-09-21

---

## 1. Quick Start (Deploy for Any New Candidate in Under 5 Minutes)

### Step 1: Create Isolated Chrome Profile
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeProfiles\<CandidateName>" --no-first-run --no-default-browser-check
```
- **Why:** Each candidate gets completely isolated cookies, session tokens, canvas fingerprints, and local storage. Zero cross-contamination between profiles.
- **Log into LinkedIn and Naukri** manually in the launched Chrome window.

### Step 2: Prepare Candidate Resume
Place the candidate's factual reverse-chronological resume in `profiles/<CandidateName>/resume.md`.

**Strict Resume Rules:**
- **Order:** Reverse-Chronological (Present -> Past)
- **Length:** 1-2 pages maximum
- **Formatting:** Single-column, left-aligned, bullet-pointed quantifiable impact

### Step 3: Configure Candidate Truth Ledger
Edit `profiles/<CandidateName>/candidate_config.json`:

```json
{
  "candidate": {
    "full_name": "<Full Name>",
    "email": "<email>",
    "phone": "<phone>",
    "location": "<City / Region>",
    "pincode": "<6-digit pincode>",
    "total_experience_years": 0,
    "current_ctc_lpa": 0,
    "expected_ctc_lpa": 0,
    "notice_period_days": 0,
    "resume_filename": "Target_Resume.pdf",
    "cdp_url": "http://127.0.0.1:9222"
  },
  "target_jobs": {
    "keywords": ["<Keyword1>", "<Keyword2>"],
    "negative_keywords": ["Sales", "Intern"],
    "max_experience_gap_years": 2,
    "locations": ["<City1>", "<City2>"],
    "platforms": ["Naukri", "LinkedIn"],
    "work_mode": "hybrid",
    "direct_employers_only": false
  },
  "ats_answers": {
    "notice_period": "<N> Days",
    "current_ctc_lakhs": 0,
    "expected_ctc_lakhs": 0,
    "pincode": "<pincode>",
    "skill_years_experience": {
      "<Skill1>": 0,
      "<Skill2>": 0
    }
  },
  "auto_learned_truths": {
    "pincode": "<pincode>",
    "pin code": "<pincode>",
    "zip code": "<pincode>"
  }
}
```

### Step 4: Run the Three-Daemon Autonomous Engine

The system operates across three coordinating daemons to maintain continuous application velocity and sub-minute IPC response times:

#### Terminal 1 — Daemon 1 (Discovery & Execution Loop):
```bash
python core/continuous_career_agent.py --delay 30
```
*(Runs continuous cycles with `--delay 30` cooldown between designations. `SearchStateManager` rotates sequentially through candidate target designations; `--profile` is automatically discovered if omitted).*

#### Terminal 2 — Daemon 2 (IPC Signal Relay):
```bash
python core/ipc_watcher.py --poll 2.0
```
*(Monitors `pending_question.json` and `batch_question.json` within a single shared 2.0s polling loop, emitting real-time structured ASCII alerts for AG Brain).*

#### Terminal 3 / Background — Daemon 3 (AG Brain Cron Monitor):
Runs a 1-minute cron heartbeat (`* * * * *`) that parses watcher alerts, resolves questions from candidate truths, and writes answers to `batch_answer.json` (120s timeout SLA) or `pending_question.json` (90s timeout SLA).

---

### Step 5: The Batch Execution Lifecycle (ARM → BRAIN → EXECUTE)

1. **ARM Phase (`04_job_discovery.py`):**
   - Uses `SearchStateManager` to pick the current active designation.
   - Scrapes SRP cards across multiple pages using canonical structured SEO slugs (`/{slug}-jobs-in-{loc}`).
   - Applies objective numeric pre-gates: CTC salary floor and **Card-Level Experience Band Gating (Guardrail C24)**: if card min experience $> \text{candidate actual exp} + \text{max\_experience\_gap\_years}$, rejects immediately with status `experience_gap_gated`.
   - Accumulates qualified cards into `batch_question.json`.
2. **BRAIN Phase:**
   - Sends the entire card batch to AG Brain via `batch_question.json` ($O(1)$ token overhead).
   - Waits up to 120s for AG Brain to return `batch_answer.json` with `DEEP_SCAN` or `SKIP` decisions.
3. **EXECUTE Phase:**
   - For `DEEP_SCAN` cards only: opens detail page with **Two-Stage Navigation Recovery (Guardrail C32)** (`commit` [60s] + `domcontentloaded` [75s]), un-clamps description (`span.styles_rm-link__RgrMs`), extracts 7.2k+ chars of full JD, and scores via Stage 2 cognitive qualification ($\ge 60\%$).
   - Compiles ATS-tailored PDF (`generate_factual_tailored.py`).
   - Executes fast PDF upload (`02b_naukri_fast_resume_upload.py`).
   - Completes application form & chatbot interaction (`05_apply_jobs.py`), employing **Radio Chip Option-Constrained Resolution (Guardrail C34)** for proficiency tiers.
4. **ROTATE Phase:**
   - `SearchStateManager.advance()` advances the designation index and records cycle telemetry.
   - Pauses for `--delay 30` seconds before next designation.

---

## 2. ATS Keyword Prominence & Dynamic Skill Taxonomy

The resume tailoring engine (`generate_factual_tailored.py`) analyzes the actual, full job description loaded directly from `Job_Description.md` on disk (never defaulting to generic title strings when JD exists). It extracts technical keywords (preserving `C++`, `.NET`, `K8s`, `SAP S/4HANA`, `Dynamics 365`, `SQL`, `Python3`, `C#`), scores all bullets in `resume.md` using pre-compiled word-boundary matching (`\b`), and dynamically reorders the candidate's bullets using a stable sort to maximize ATS keyword match on a per-role basis.

**Matching Portal Dropdowns Without Enter Key:**
Skills are mapped to exact Naukri suggestion taxonomy (`ul.Sdrop li`). The engine clicks the matching dropdown option directly rather than typing + Enter, preventing phantom skill entries.

---

## 3. Three-Tier Verification Protocol

| Tier | Description | Implementation |
|:---|:---|:---|
| **Tier 1 (Planned)** | Job sourced from manifest, un-clamped, and qualified by Two-Stage Cognitive Evaluation Engine ($\ge 60\%$ score, C6 gatekeeper, domain stem alignment, min 2 skills, Naukri native match score calibration) | `search_manifest.json` |
| **Tier 2 (Submitted)** | Final "Submit" button clicked and confirmation detected | `05_apply_jobs.py` modal confirmation trap |
| **Tier 3 (Verified)** | Physical DOM confirmation on platform history page | Naukri: `/myapply/historypage` DOM text scan; LinkedIn: `/jobs-tracker/?stage=applied` |

Only **Tier 3** verification elevates status to `VERIFIED_SUCCESS`.

---

## 4. Mandatory Field Safety Protocol

When a form field is marked `*` or `required` and the answer is not found in:
1. `auto_learned_truths` in `candidate_config.json` ($O(1)$ exact-match cache)
2. `candidate_config.json` structured fields (`candidate`, `ats_answers`, `taxonomy_skills`)
3. `AIClient` grounded resume reasoning (Gemini API or Antigravity 2.0 File IPC)

...the engine executes a **graceful abort**: `Escape` → `Discard` → logs `REQUIRES_MANUAL_INTERVENTION` with the exact question text for human review. **Zero guessed or invented data is ever submitted.**

---

## 5. Behavioral Anti-Detection Standards

| Parameter | Value | Purpose |
|:---|:---|:---|
| Keystroke Jitter | 45ms – 130ms per character | Eliminates robotic typing signature |
| Pre-Click Visual Scan | 400ms – 900ms pause | Simulates human eye gaze before mouse click |
| Inter-Job Cooldown | 25s – 75s randomized | Prevents rate-limiting between applications |
| Batch Cycle Sleep | 30 minutes | Emulates human session pacing |
