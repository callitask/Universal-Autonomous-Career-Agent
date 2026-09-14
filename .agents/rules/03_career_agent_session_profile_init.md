# Career Agent Session Init — Mandatory Auto-Load Protocol
# Loaded automatically at every Antigravity session start (F:\JOB AI AGENT\.agents\rules\)

## MANDATORY: Execute the following checklist at the start of EVERY session involving the Universal Autonomous Career Agent.

---

### STEP 1 — Mandatory Pre-Flight Documentation Ingestion
Before executing any user command, running any Python script (`python core/...`), or making any code changes, immediately read and internalize:
1. `F:\JOB AI AGENT\docs\WORKSPACE_RULES.md` (Directives 1-8, all Bug Prevention Guardrails P1, C1-C20, H1-H6, D1-D3)
2. `F:\JOB AI AGENT\docs\ARCHITECTURE_REFERENCE.md` (Module anatomy, IPC contracts, data schemas)
3. `F:\JOB AI AGENT\docs\PLATFORM_KNOWLEDGE.md` (Naukri/LinkedIn DOM patterns, SEO slugs, zero-comma rules)

Compliance is mandatory regardless of whether the user explicitly mentions the docs.

---

### STEP 2 — Identify Active Candidate Profile
1. Inspect `F:\JOB AI AGENT\profiles` to determine the target candidate directory:
   - If the user specifies a profile (e.g. `udaysagar_kandpal`), use `profiles/<specified_profile>`.
   - If unspecified, check the most recently active profile or default reference:
     * Canonical template & schema blueprint: `profiles/default_user`
     * Active candidate directory: `profiles/udaysagar_kandpal`
2. Recognize the dynamic sandbox boundary:
   - `profiles/<profile>/output/` is the dynamic runtime sandbox storing `processed_ledger.json`, `applications_tracker.csv`, `search_manifest.json`, and tailored resumes.
   - Modifying candidate profile data has NOTHING to do with developing core engine code. When refactoring engine code, edit `core/` or `scripts/`, never corrupting candidate data.

---

### STEP 3 — AG Brain Talent Architect Analysis & Push-Start Config
**Core Axiom: The AG Brain is the sole decider; Python scripts are strictly execution actuators.**
Python scripts must never contain hardcoded roles, seniority templates, or experience heuristics.

Before launching any job search or application script:
1. **Read Resume End-to-End**: Read `profiles/<profile>/resume.md` completely.
2. **Deep Cognitive Evaluation**: As an expert human talent architect, analyze:
   - Exact verified total experience (years, months).
   - Core primary technical or domain competencies.
   - Secondary tools, frameworks, and methodologies.
   - Authentic seniority tier (e.g., Senior, Lead, Staff, Principal, Manager, Architect).
3. **Push-Start Configuration Update**: Inspect and update `profiles/<profile>/candidate_config.json`:
   - `target_jobs.target_roles`: Authentic, high-precision job titles reflecting the candidate's exact tier.
   - `target_jobs.recommended_titles`: Strategic senior/adjacent designations to serve as search expansion targets.
   - `target_jobs.keywords`: Clean, high-yield search terms without invalid symbols or comma-delimited strings.
   - `skills.core_skills`: Top domain competencies extracted from verified work history.
   - `skills.secondary_skills`: Supporting platforms and tools.

---

### STEP 4 — Codebase Purity & Zero-Trust Audit
Before running any script or modifying code:
1. Verify that `ProfileContext.verify_codebase_purity()` passes with 0 violations.
2. Ensure there are ZERO hardcoded variables, company names, technology presets, or user paths in Python files.
3. Ensure the AI Context header in any touched `.py` file is read first and updated via append-only logging upon edits.

---

### STEP 5 — Subsystem Isolation Reminder
- **Universal Autonomous Career Agent** lives in `core/`, `scripts/`, `profiles/`, and `docs/`.
- **Sophron** lives in `Sophron/`.
- They are completely separate systems. Never mix imports, configurations, or operational boundaries.
