# Universal Autonomous Career Agent - Setup & Execution Guide

Welcome to the **Universal Autonomous Career Agent**. This system is an end-to-end, multi-agent AI pipeline designed to automate job discovery, factual resume tailoring, and ATS application submission (with behavioral anti-detection stealth) across platforms like LinkedIn and Naukri.

This guide explains how to set up the environment, configure your candidate profile, and run the system autonomously.

---

## 1. System Capabilities

- **Deep Discovery:** Scrapes job platforms based on your targeted keywords and randomizes search parameters to prevent feed stagnation.
- **Dynamic Factual Tailoring:** Analyzes job descriptions and re-orders/emphasizes your *existing, factual* resume bullet points to maximize ATS keyword density. **Zero hallucinations.**
- **Autonomous Form Solving:** Solves multi-step LinkedIn Easy Apply modals and Naukri chatbot drawers. Handles dropdowns, sliders, and multi-select chips.
- **Three-Tier Verification:** Ensures applications are truly submitted by physically verifying confirmation pages and DOM ledger history (`/myapply/historypage`).
- **Human Emulation:** Uses randomized typing jitter (45-130ms), visual scanning pauses (400-900ms), and 30-minute batch cycles to emulate human browsing and prevent account bans.

---

## 2. Directory Structure

Your workspace is organized as follows:

```text
F:\JOB AI AGENT\
│
├── core/                           # Python execution scripts
│   ├── 02_profile_sync_naukri.py   # Naukri profile updater
│   ├── 03_profile_sync_linkedin.py # LinkedIn profile updater
│   ├── 04_job_discovery.py         # Job scraper (LinkedIn & Naukri)
│   ├── generate_factual_tailored.py# Resume tailoring & PDF compiler
│   ├── 05_apply_jobs.py            # Form solver and applicator
│   └── continuous_career_agent.py  # Master daemon loop (Runs 04 -> Tailor -> 05)
│
├── config/                         
│   └── candidate_config.json       # Master configuration (Your profile, CTC, filters)
│
├── templates/
│   └── Master_Resume_Template.md   # Your master markdown resume (Strict Reverse-Chronological)
│
├── docs/                           # Reference material and setup guides
│
└── output/                         # System generated outputs
    ├── applications/               # Generated per-job folders (Tailored PDF & Job Description)
    ├── resumes/                    # General rendered resumes
    └── logs/                       # System logs and tracker CSVs
```

---

## 3. Environment & Prerequisites Setup

### A. Install Python Dependencies
You need Python 3.10+ installed. Open a terminal and run:
```bash
pip install playwright markdown
playwright install chromium
```


### C. Configure Gemini API Key
The agent uses Gemini for deep AI profile analysis and robust job-matching. You must set your API key as an environment variable before running the agent:

**Windows (PowerShell):**
`powershell
$env:GEMINI_API_KEY="your-api-key-here"
`

**Mac/Linux:**
`ash
export GEMINI_API_KEY="your-api-key-here"
`

### B. Launch Isolated Chrome Profile (Crucial Step)
The agent operates through the Chrome DevTools Protocol (CDP). You must start a dedicated Chrome instance *before* running the agent. This keeps your job-search cookies separate from your personal browsing.

1. Open PowerShell or Command Prompt.
2. Run the following command (replace `<YourName>` with your actual name to create a new folder):
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeProfiles\<YourName>" --no-first-run --no-default-browser-check
```
3. In this newly opened Chrome window, **manually log in** to your LinkedIn and Naukri accounts. Leave this browser window open.

---

## 4. Configuring Your Candidate Profile

Before running the agent, you must configure it for your specific background.

### Step 4.1: Update `config/candidate_config.json`
Open the config file and replace all placeholder values (`[YOUR NAME]`, `[YOUR PINCODE]`, etc.) with your actual details. 
- **`candidate`**: Basic contact info, current/expected CTC, and notice period.
- **`target_jobs`**: Keywords and locations the scraper will search for.
- **`ats_answers`**: Ground-truth answers used to fill out form fields automatically (e.g., years of experience with specific skills).
- **`auto_learned_truths`**: As the agent encounters new questions, it learns the answers. You can pre-seed this with location/pincode data.

### Step 4.2: Update `templates/Master_Resume_Template.md`
This is the base template for your resume.
- Keep the structure clean and use bullet points.
- Ensure the order is **Strictly Reverse-Chronological** (Current job first, oldest job last).
- Ensure all quantifiable metrics are bolded (e.g., **98% accuracy**).

### Step 4.3: Customize the ATS Tailoring Engine (IMPORTANT)
The script `core/generate_factual_tailored.py` determines how your resume adapts to different Job Descriptions. 

You **DO NOT** need to edit Python code for this. The tailoring engine is entirely template-driven:
1. Ensure your `templates/Master_Resume_Template.md` is well-structured with markdown headings (e.g., `### Company Name`).
2. Include all possible bullet points you want to use.
3. When a job is discovered, the engine will read your Job Description, extract keywords, score all your bullets, and automatically reorder the most relevant bullets to the top of each section.
4. The system then renders the tailored PDF dynamically.

## 5. Running the Agent

Once configuration is complete and your CDP Chrome window is open (on port 9222), start the autonomous daemon:

```bash
cd "F:\JOB AI AGENT\core"
python continuous_career_agent.py
```

### What happens next?
1. **Discovery:** The agent navigates to job boards and scrapes listings matching your config.
2. **Tailoring:** It analyzes the Job Descriptions and generates a custom, ATS-optimized PDF resume in `output/applications/`.
3. **Application:** It loops through the discovered jobs, attaches the correct PDF, answers the form questions using your configured `CANDIDATE_TRUTHS`, and submits.
4. **Verification:** It physically verifies the submission in the platform's history ledger.
5. **Sleep:** It goes into a 30-minute cooldown to prevent account flagging before starting the next batch.

---

## 6. Tracking & Manual Intervention

- **Application Tracker:** All applications are logged in `output/applications_tracker.csv`.
- **Status Codes:** Look for `VERIFIED_SUCCESS` (fully completed and confirmed) or `SUBMITTED_SUCCESSFULLY`.
- **Manual Intervention:** If the agent encounters a mandatory form field (`*`) that it does not know the answer to, it will *abort* to avoid guessing or hallucinating data. It will log the status as `REQUIRES_MANUAL_INTERVENTION`. You can manually apply to these roles using the URLs saved in the tracker.
- **External ATS:** Roles redirecting to Workday, SuccessFactors, etc., will be safely aborted and logged as `REDIRECT_EXTERNAL` for you to complete manually.
