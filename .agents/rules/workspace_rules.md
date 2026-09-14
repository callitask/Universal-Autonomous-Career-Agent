# Universal Autonomous Career Agent: Workspace Execution Rules

Execution approved for F:\JOB AI AGENT.

## Mandatory Operating Protocols:
1. **Auto-Load Documentation (Rule 1)**: The agent MUST read `docs/WORKSPACE_RULES.md`, `docs/ARCHITECTURE_REFERENCE.md`, and `docs/PLATFORM_KNOWLEDGE.md` at session start and before running any commands or modifying code.
2. **Dynamic Profile Sandbox Boundaries (Rule 2)**: `profiles/` is dynamic runtime I/O data; `profiles/<profile>/output/` stores dynamic artifacts (ledger, PDFs, logs). Do NOT scan or edit `profiles/` when developing/editing the agent. For data structure inspection, refer to blueprint `profiles/default_user`.
3. **User Observation & Starvation Intervention (Rule 3)**: When user reports no jobs applied / agent not finding jobs, do NOT modify `04_job_discovery.py` or `05_apply_jobs.py`. Instead, inspect the candidate's `resume.md` and edit `candidate_config.json` with fresh, highly relevant roles.
4. **AG Brain Monitoring & Self-Healing (Rule 4)**: The AG Brain monitors terminal execution logs (`logs_dump.txt`, `terminal_execution_log.txt`), diagnoses saturation/loops, self-heals by expanding search keywords, and persists findings in knowledge files.

See detailed rules in: `F:\JOB AI AGENT\.agents\rules\02_career_agent_operational_rules.md`.