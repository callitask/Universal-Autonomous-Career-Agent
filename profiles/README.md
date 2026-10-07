# Candidate Profiles Directory

This directory houses candidate profile sandboxes for the **Universal Autonomous Career Agent**. Each candidate's data, resume, configurations, and application ledgers are strictly isolated inside their own sandbox directory.

---

## Directory Structure

```
profiles/
├── default_user/                 <-- Master Blueprint / Schema Exemplar (Do NOT rename or delete)
│   ├── candidate_config.json     <-- Configuration template with bracketed schema placeholders
│   ├── resume.md                 <-- Markdown resume template with section guidelines
│   ├── README.md                 <-- Quick-start template instructions
│   └── output/                   <-- Standard sandbox output directory skeleton
│       ├── applications/
│       ├── logs/
│       └── resumes/
│
└── <firstname_lastname>/         <-- User Candidate Sandbox (created from default_user)
    ├── candidate_config.json     <-- [REQUIRED] Populated candidate parameters & ATS truths
    ├── resume.md                 <-- [REQUIRED] Candidate master resume in Markdown
    └── output/                   <-- [AUTO-GENERATED] Created and maintained at runtime
        ├── applications/         <-- [AUTO-GENERATED] Per-job tailored resumes and logs
        ├── search_manifest.json  <-- [AUTO-GENERATED] Discovered job postings
        ├── processed_ledger.json <-- [AUTO-GENERATED] Duplication prevention ledger
        └── applications_tracker.csv <-- [AUTO-GENERATED] Application status audit
```

---

## How to Onboard a New Candidate (3 Simple Steps)

### Step 1: Copy the Template Folder
Duplicate the `default_user/` folder and name the new folder using lowercase snake_case (`firstname_lastname`):
```powershell
# Example in PowerShell:
Copy-Item -Recurse profiles/default_user profiles/<candidate_slug>
```

### Step 2: Fill in the 2 Prerequisite Files
Inside the new `profiles/<firstname_lastname>/` folder, edit **only** these two files:
1. **`candidate_config.json`**:
   - Replace all `[BRACKETED]` placeholders with the candidate's real data (contact details, target keywords, cities, salary expectations, notice period, ATS screening answers).
   - If candidate is a college student / fresher: Set `total_experience_years` to `0` and include `"Internship"` and `"Job"` in `job_types`.
2. **`resume.md`**:
   - Replace the template sections with the candidate's actual qualifications, skills, experiences/internships, and education.
   - **Crucial Rule on Dates**: Format employment and internship dates clearly as `Month Year - Month Year` (e.g., `Jun 2023 - Dec 2023`) or `Month Year - Present`. This allows the agent's multi-attribute duplicate detector (`is_duplicate_employment_or_internship`) to parse exact start/end years and distinguish between different stints at the same organization.

### Step 3: Run the Agent
Run the agent specifying the candidate profile or let it auto-discover:
```powershell
# Explicit profile specification:
python core/04_job_discovery.py --profile profiles/<candidate_slug>

# Or sync live profile on Naukri:
python core/02_profile_sync_naukri.py --profile profiles/<candidate_slug>
```

---

## Important Rules & Safeguards

- **NEVER Manually Edit `output/applications/`**:
  The `output/` directory and its `applications/` subfolder are automatically created and populated by the agent. They store generated application logs and tailored resumes. Never create, modify, or delete files inside `output/applications/` by hand.
- **`default_user` Protection**:
  The core engine (`core/utils/profile_context.py`) automatically skips `default_user` when discovering candidates, guaranteeing that your starter blueprint remains untouched.
- **Candidate Isolation**:
  Candidate data in one folder is completely isolated from other candidates. No cross-candidate leakage occurs.
