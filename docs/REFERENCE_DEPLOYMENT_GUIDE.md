# UNIVERSAL DEPLOYMENT GUIDE
**System:** Anti-Gravity Autonomous Career Operations Engine  
**Architecture:** Variable-Driven, Candidate-Agnostic, Multi-Profile  
**Last Updated:** 2026-08-25

---

## 1. Quick Start (Deploy for Any New Candidate in Under 5 Minutes)

### Step 1: Create Isolated Chrome Profile
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeProfiles\<CandidateName>" --no-first-run --no-default-browser-check
```
- **Why:** Each candidate gets completely isolated cookies, session tokens, canvas fingerprints, and local storage. Zero cross-contamination between profiles.
- **Log into LinkedIn and Naukri** manually in the launched Chrome window.

### Step 2: Prepare Candidate Resume
Place the candidate's factual reverse-chronological resume in `templates/Master_Resume_Template.md`.

**Strict Resume Rules:**
- **Order:** Reverse-Chronological (Present -> Past)
- **Length:** 1-2 pages maximum
- **Formatting:** Single-column, left-aligned, bullet-pointed quantifiable impact

### Step 3: Configure Candidate Truth Ledger
Edit `config/candidate_config.json`:

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
    "locations": ["<City1>", "<City2>"],
    "platforms": ["Naukri", "LinkedIn"]
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

### Step 4: Run the Autonomous Daemon
```bash
cd core/
python continuous_career_agent.py
```

**Pipeline per cycle:**
1. `04_job_discovery.py` -> Deep scrapes LinkedIn & Naukri with random sampling
2. `generate_factual_tailored.py` -> Compiles ATS-optimized PDFs per role
3. `05_apply_jobs.py` -> Applies with form solving, chatbot interaction, and verification
4. 30-minute deep-sleep -> Account preservation pacing

---

## 2. ATS Keyword Prominence & Dynamic Skill Taxonomy

The resume tailoring engine (`generate_factual_tailored.py`) analyzes each job description, extracts meaningful keywords, and scores all bullets in `Master_Resume_Template.md`. It then dynamically reorders the candidate's bullets to maximize ATS keyword match on a per-role basis, ensuring the most relevant experience is listed first for every application.

**Matching Portal Dropdowns Without Enter Key:**
Skills are mapped to exact Naukri suggestion taxonomy (`ul.Sdrop li`). The engine clicks the matching dropdown option directly rather than typing + Enter, preventing phantom skill entries.

---

## 3. Three-Tier Verification Protocol

| Tier | Description | Implementation |
|:---|:---|:---|
| **Tier 1 (Planned)** | Job sourced from manifest and validated for candidate fit | `search_manifest.json` |
| **Tier 2 (Submitted)** | Final "Submit" button clicked and confirmation detected | `05_apply_jobs.py` modal confirmation trap |
| **Tier 3 (Verified)** | Physical DOM confirmation on platform history page | Naukri: `/myapply/historypage` DOM text scan; LinkedIn: `/jobs-tracker/?stage=applied` |

Only **Tier 3** verification elevates status to `VERIFIED_SUCCESS`.

---

## 4. Mandatory Field Safety Protocol

When a form field is marked `*` or `required` and the answer is not found in:
1. `CANDIDATE_TRUTHS` dictionary (hardcoded)
2. `auto_learned_truths` in `01_CANDIDATE_CONFIG.json` (O(1) cache)
3. Gemini RAG fallback (API-based contextual answer)

...the engine executes a **graceful abort**: `Escape` → `Discard` → logs `REQUIRES_MANUAL_INTERVENTION` with the exact question text for human review. **Zero guessed data is ever submitted.**

---

## 5. Behavioral Anti-Detection Standards

| Parameter | Value | Purpose |
|:---|:---|:---|
| Keystroke Jitter | 45ms – 130ms per character | Eliminates robotic typing signature |
| Pre-Click Visual Scan | 400ms – 900ms pause | Simulates human eye gaze before mouse click |
| Inter-Job Cooldown | 25s – 75s randomized | Prevents rate-limiting between applications |
| Batch Cycle Sleep | 30 minutes | Emulates human session pacing |
