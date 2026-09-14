# Career Agent Operational Rules & Workspace Governance (Mandatory Auto-Load)

These rules are loaded automatically at every session start and before every prompt turn for F:\JOB AI AGENT. They govern the behavior of the AI Agent (Antigravity Brain) and developers operating within this workspace.

---

## RULE 1: MANDATORY DOCUMENTATION AUTO-LOAD & PRE-FLIGHT PROTOCOL

1. **Automatic Documentation Ingestion**:
   Whenever this agent is started, or before executing any user command, running any Python script (python core/...), or making any code changes, the agent MUST immediately read and internalize the core documentation files in F:\JOB AI AGENT\docs\:
   - F:\JOB AI AGENT\docs\WORKSPACE_RULES.md (Directives 1-8 and all 20+ Bug Prevention Guardrails)
   - F:\JOB AI AGENT\docs\ARCHITECTURE_REFERENCE.md (Module anatomy, IPC contracts, data schemas)
   - F:\JOB AI AGENT\docs\PLATFORM_KNOWLEDGE.md (Naukri/LinkedIn DOM patterns, SEO slugs, zero-comma rules)
2. **Universal Compliance**:
   This requirement applies regardless of whether the user asks to read the docs or not. It guarantees that all workspace restrictions, known bug guardrails (P1, C1-C20, H1-H6, D1-D3), and environment boundaries are strictly respected at all times.
3. **No Assumptions**:
   Never guess portal selectors, method signatures, or data structures. Ground all decisions in the verified documentation and live DOM inspection.

---

## RULE 2: DYNAMIC PROFILE SANDBOX BOUNDARIES & DEVELOPER ROLE

1. **profiles/ Directory Purpose**:
   F:\JOB AI AGENT\profiles is the **dynamic runtime data sandbox** for the Universal Autonomous Career Agent.
   - It contains candidate-specific inputs (candidate_config.json, resume.md) and runtime generated outputs.
   - Specifically, the output/ subfolder inside each candidate profile (profiles/<profile_name>/output/) is where the agent dynamically stores large, volatile runtime artifacts:
     * processed_ledger.json (1,000+ deduplication entries)
     * applications_tracker.csv (audit log of applications)
     * search_manifest.json & saved_external_jobs.json
     * applications/ (per-job tailored resumes, PDFs, and scraped Job_Description.md)
     * logs/ (terminal logs and screenshot diagnostics)
     * cognitive_profile.json (runtime synthesized domain taxonomy)
2. **Developer Separation of Concerns**:
   - The engine code lives in core/, docs/, and scripts/.
   - **Scanning or modifying profiles/ has nothing to do with developing, upgrading, or editing the agent code.**
   - When developing or refactoring the engine, the agent/developer modifies core/, docs/, or test scripts - NEVER the candidate data in profiles/.
3. **Demo Blueprint Reference (default_user)**:
   - Whenever the agent or developer needs to analyze how data is structured, input, or output during debugging or development, use the canonical template:
     F:\JOB AI AGENT\profiles\default_user
   - default_user is the clean, uncorrupted blueprint showing the intended schema for candidate_config.json, resume.md, and output/.

---

## RULE 3: USER OBSERVATION & STARVATION INTERVENTION PROTOCOL

1. **Trigger Condition**:
   When the agent is running scanning and applying jobs, and the user observes and mentions that:
   - No jobs are being applied to, OR
   - The agent is not able to find jobs / is stuck in a loop / is hallucinating.
2. **Action Protocol (Config-First, Hands Off Core Engine)**:
   - **STRICTLY FORBIDDEN**: Do NOT immediately scan or modify core/04_job_discovery.py, core/05_apply_jobs.py, or other core Python engine scripts. The engine logic is already verified and guarded.
   - **MANDATORY PROCEDURE**:
     1. Inspect the active candidate profile being executed (profiles/<active_profile>/resume.md, candidate_config.json, output/processed_ledger.json, and output/cognitive_profile.json).
     2. Identify the root cause of the starvation (e.g., all existing keywords exhausted in the 1,800+ entry ledger, or negative company exclusions blocking all page 1 results).
     3. **Edit candidate_config.json for that profile**: Add new, high-yield job designations and search keywords derived strictly from the candidate's verified profile and resume.
     4. **Relevance Guarantee**: Ensure all newly added search titles and skills are 100% relevant and aligned with the candidate's actual years of experience, core technical stack, and seniority tier.
     5. Reset or refresh the active search cycles in cognitive_profile.json so the running engine immediately searches for the newly configured roles.

---

## RULE 4: AG BRAIN AUTONOMOUS MONITORING, LOG AUDITING & SELF-HEALING

1. **AG Brain as an Active Observer & Monitor**:
   The AG Brain must act as an observant monitor alongside the user. It does not just execute scripts blindly; it continuously watches runtime behavior and evaluates execution health.
2. **Terminal Log Auditing**:
   - The agent must read terminal logs from logs_dump.txt or profiles/<profile>/output/logs/terminal_execution_log.txt.
   - It checks:
     * Cycle counts and progress (e.g., Cycle #35, Cycle #36).
     * Sourced cards vs. skipped cards (e.g., detecting if all cards on pages 1-3 are already in processed_ledger.json).
     * Domain gating rejection rates and negative company exclusions.
     * IPC timeouts (e.g. pending_question.json timing out on STARVATION_EXPANSION).
     * Repetitive loops or stuck questions in application drawers.
3. **Self-Healing Loop**:
   - If the log reveals keyword saturation (0 qualified jobs across entire cycles):
     The AG Brain autonomously updates candidate_config.json with fresh, relevant titles.
   - If the log reveals repetitive question loops or format mismatches:
     The AG Brain records the verified answer in candidate_config.json under auto_learned_truths.
4. **Knowledge Persistence & Anti-Regression**:
   - Every critical finding, platform behavior change, or fixed issue must be permanently documented in:
     * docs/PLATFORM_KNOWLEDGE.md (portal-level mechanics, DOM selectors, anti-starvation rules)
     * profiles/<profile>/output/cognitive_learnings.json (candidate-specific learnings)
   - This guarantees that in the future, when the agent is updated, upgraded, or analyzed, the same mistakes and bottlenecks are never repeated.

---

## RULE 5: ZERO-TRUST CODEBASE PURITY & DYNAMIC CONFIG ENFORCEMENT

1. **Zero-Trust Hardcoding Prohibition**:
   - There must be **ZERO hardcoded data, constants, variables, tech stacks, domains, company names, cities, models, or filesystem paths** in any Python file across `core/`, `scripts/`, or subsystems.
   - Specifically prohibited in Python code:
     * Specific technologies/languages as default anchors or fallbacks (e.g. `"Java"`, `"Python"`, `"React"`).
     * Specific company names as hardcoded exclusion checks (e.g. `"TCS"`, `"Infosys"`).
     * Specific city names as defaults or filters (e.g. `"Bangalore"`, `"Pune"`).
     * Specific model identifiers as constants (e.g. `"gemini-1.5-flash"`).
     * Hardcoded Windows user home paths (e.g. `C:\Users\<username>\...`).
     * Hardcoded workspace drive paths (e.g. `F:\JOB AI AGENT\...`).
2. **Dynamic Resolution via `candidate_config.json` & `ProfileContext`**:
   - Every candidate parameter (target locations, target roles, negative companies, compensation, notice period, CDP ports, AI models) MUST be fetched dynamically from `candidate_config.json` via `ProfileContext`.
   - Domain taxonomies, core vs. soft skills, and designation expansion queues MUST be synthesized dynamically from the candidate's verified profile and resume (`cognitive_profile.json`).
3. **Mandatory Pre-Flight Enforcement**:
   - Whenever any script starts, any command is executed, or the agent initializes, edits, fixes, or debugs code, `ProfileContext.verify_codebase_purity()` automatically executes.
   - If ANY hardcoded variable, candidate PII, or absolute path is introduced, the system triggers a fatal `CodebasePurityViolationError` and halts execution immediately.

---

## RULE 6: MANDATORY AI CONTEXT HEADER MAINTENANCE & ANTI-REGRESSION LOGGING

1. **Mandatory First-Read Protocol**:
   - Every Python file in `core/` and `scripts/` contains an `# AI CONTEXT & CHANGE LOG` block at the very top (commented out so runtime execution is unaffected).
   - Whenever an AI agent or developer analyzes, inspects, edits, fixes, or refactors a `.py` file, they MUST read the AI Context header first before proposing or executing code changes.
2. **Append-Only Logging Requirement**:
   - Every modification, fix, refactoring, or reverted experiment MUST be logged by appending a new entry to the AI Context header of the affected file.
   - **Never delete or overwrite previous entries.**
3. **Mandatory Entry Schema**:
   Each appended entry must strictly include:
   - **Serial Number**: Incrementing sequential number (e.g. `[ENTRY #003]`).
   - **Term / Category**: Standardized category (e.g. `[BUGFIX]`, `[REFACTOR]`, `[OPTIMIZATION]`, `[DOM_UPDATE]`, `[GOVERNANCE]`).
   - **Timestamp**: Date and exact local timestamp with timezone (e.g. `YYYY-MM-DD HH:MM:SS +05:30`).
   - **Issue / Context**: Crisp, to-the-point explanation of the problem or requirement.
   - **Changes Made**: Specific functions, classes, selectors, or logic modified.
   - **Rationale**: Why the change was made in this specific way.
   - **Preventative Notes / Do Not Repeat**: Explicit guidance on what failed, what was reverted, and what future AIs must NOT attempt, preventing circular regression loops.
4. **Candidate-Agnostic & Zero-PII Invariant**:
   - Even when user requests are triggered by observing a specific candidate run, **NEVER write candidate personal details, names, emails, phones, or profile titles into the AI Context**.
   - Record only generic, architectural, DOM, algorithmic, and engineering issues.

---

## RULE 7: AG BRAIN AS TALENT STRATEGIST — SESSION STARTUP & PUSH-START PROTOCOL

1. **Fundamental Philosophy: Brain vs. Actuator**:
   - Python scripts (`core/`, `scripts/`) are **strictly an execution actuator / browser medium** interfacing between job portals (Naukri, LinkedIn) and the AG Brain.
   - Python scripts must **NEVER make heuristic choices, invent roles, apply hardcoded role templates, or branch on experience thresholds** (e.g., `if exp >= 8.0: roles = [...]`). Zero synthetic strings or heuristics belong in code.
   - The **AG Brain (Antigravity AI model)** is the **sole decider, talent strategist, and cognitive authority**.
2. **Session Push-Start Protocol**:
   - At the beginning of EVERY new session, or whenever the user indicates a profile to work on, the AG Brain MUST execute this push-start sequence before launching any scripts:
     1. **Profile Identification**: Check which candidate profile in `profiles/` is targeted (e.g. `profiles/udaysagar_kandpal/`, or user-specified).
     2. **Deep Resume Analysis**: Read `profiles/<profile>/resume.md` end-to-end. Analyze it deeply as a human talent architect—internalizing total years of experience, core technical stack, domain depth, leadership scope, and career trajectory.
     3. **Push-Start Configuration**: Inspect and intelligently update `profiles/<profile>/candidate_config.json` with authentic, high-yield talent parameters:
        * `target_jobs.target_roles`: Authentic titles matching the candidate's exact seniority and vertical.
        * `target_jobs.recommended_titles`: Strategic senior/lead/architect expansions derived intelligently from their experience and stack.
        * `target_jobs.keywords`: Clean, portal-searchable keyword anchors without invalid characters or comma syntax.
        * `skills.core_skills`: Top primary domain competencies extracted from their authentic work experience.
        * `skills.secondary_skills`: Supporting tools, cloud platforms, and methodologies.
     4. **Cognitive Profile Alignment**: Ensure `output/cognitive_profile.json` search cycles reflect these intelligently curated titles.
3. **Runtime Execution Consumption**:
   - Python discovery and application scripts simply consume these AG Brain-curated titles from `candidate_config.json` via `ProfileContext`.
   - In the event of portal search starvation, the script queries the AG Brain via IPC (`generate_text(task_type="STARVATION_EXPANSION")`). If IPC is offline, the script falls back strictly to the unexhausted backup titles pre-configured by the AG Brain in `candidate_config.json`.

---

## RULE 8: SUBSYSTEM ISOLATION — CAREER AGENT VS. SOPHRON DUALITY

1. **Strict Architectural Separation**:
   - `F:\JOB AI AGENT` houses two distinct, decoupled systems:
     * **Universal Autonomous Career Agent**: Operates in `core/`, `scripts/`, `profiles/`, and `docs/`. Governs job search, portal discovery, ATS tailoring, and application execution.
     * **Sophron**: Operates in `Sophron/` (`Sophron/core/`, `Sophron/graph_memory/`, `Sophron/understanding_master/`). Governs meta-cognitive tracking, user psychological analysis, and session memory.
2. **Zero Mixing / Cross-Pollination**:
   - Career Agent scripts MUST NEVER import from `Sophron/`, write to `Sophron/`, or depend on Sophron modules.
   - Sophron scripts MUST NEVER modify candidate profile configurations or interfere with job application loops.
   - When developing, debugging, or configuring the Career Agent, focus exclusively on the Career Agent boundary. Keep the two systems completely distinct.



