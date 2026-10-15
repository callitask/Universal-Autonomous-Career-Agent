# Universal Autonomous Career Agent: Workspace Execution Rules
<!-- Amended 2026-10-14: Operations-root live data, CompanySiteApply structured-layout contract, 150+5+10 suite -->

Execution approved for F:\JOB AI AGENT. Live runtime data lives under `F:\Operations JOB AI AGENT\` (env-overridable via `JOB_AGENT_OPERATIONS`); the repo keeps code + the `default_user` blueprint only.

## Mandatory Operating Protocols:
1. **Auto-Load Documentation (Rule 1)**: The agent MUST read `docs/WORKSPACE_RULES.md`, `docs/ARCHITECTURE_REFERENCE.md`, and `docs/PLATFORM_KNOWLEDGE.md` at session start and before running any commands or modifying code.
2. **Dynamic Profile Sandbox Boundaries (Rule 2)**: `profiles/` is dynamic runtime I/O data (live under the Operations root); `profiles/<profile>/output/` stores dynamic artifacts (ledger, PDFs, logs). CompanySiteApply layout (2026-10-14, profile-agnostic): inputs `company_site_apply/<Slug>/resumes|cover_letters`, outputs `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/` with fixed `<Stem>_Resume.pdf` / `<Stem>_Cover_Letter.pdf` + `resume/`/`cover_letters/` subfolders + role `Cover_Letter.txt`/`.html` (no job-id filename suffixes; uploaders exact-path-first). Do NOT scan or edit `profiles/` when developing/editing the agent. For data structure inspection, refer to blueprint `profiles/default_user`. Suite: 150 CompanySiteApply tests + 7 cover-letter-id tests + 10 knowledge tests.
3. **User Observation & Starvation Intervention (Rule 3)**: When user reports no jobs applied / agent not finding jobs, do NOT modify `04_job_discovery.py` or `05_apply_jobs.py`. Instead, inspect the candidate's `resume.md` and edit `candidate_config.json` with fresh, highly relevant roles.
4. **AG Brain Monitoring & Self-Healing (Rule 4)**: The AG Brain monitors terminal execution logs (`logs_dump.txt`, `terminal_execution_log.txt`), diagnoses saturation/loops, self-heals by expanding search keywords, and persists findings in knowledge files.

See detailed rules in: `F:\JOB AI AGENT\.agents\rules\02_career_agent_operational_rules.md`.