# Universal Autonomous Career Agent

> **[CONFIDENTIAL] PROPRIETARY & CONFIDENTIAL [CONFIDENTIAL]**
> 
> This repository and its contents are closed-source and strictly confidential. 
> No public license is granted. You may not copy, distribute, modify, or use this code without explicit written permission.


An enterprise-grade, fully autonomous AI agent designed to orchestrate the complete job application lifecycle. Operating via a dual-brain architecture (Gemini Hosted Mode + Antigravity 2.0 File-Based IPC), this pipeline autonomously discovers roles, evaluates suitability, dynamically tailors ATS-compliant resumes, and executes multi-step applications across enterprise job portals.

## System Architecture

The agent is built on a strict, candidate-agnostic framework. Zero personal data is hardcoded; everything resolves dynamically at runtime from isolated profile sandboxes.

*   **Batch Architecture v2.0:** Job discovery operates in an ARM->BRAIN->EXECUTE flow, collecting a batch of job cards for a rotating designation, waiting for a single batch IPC decision from AG Brain via batch_question.json, and then executing deep-scans only on approved cards.
*   **Three-Daemon Autonomous Architecture:** The system coordinates three specialized daemons to ensure non-blocking continuous execution and sub-minute IPC response times:
    *   **Daemon 1 (Discovery & Apply Runner — `continuous_career_agent.py`):** Runs the CDP-connected discovery and application pipeline, un-clamping JDs, rendering tailored PDFs, uploading resumes, and solving application forms.
    *   **Daemon 2 (IPC Signal Relay — `core/ipc_watcher.py`):** Dedicated lightweight daemon polling both `pending_question.json` (single IPC) and `batch_question.json` (batch IPC) within a single shared 2.0s poll interval (`run(poll=2.0)`), emitting real-time structured ASCII notifications upon detecting in-flight questions.
    *   **Daemon 3 (AG Brain Cron Monitor):** 1-minute recurring cron heartbeat (`* * * * *`) that checks watcher alerts, synthesizes grounded candidate answers from `resume.md` and configuration, and answers before the 90-second recruiter timeout SLA (empirically $<30$s).
*   **Two-Tier Job Highlights Pre-Flight Gater:** Recruiter eligibility prerequisites and dealbreakers (e.g. CA Intermediate, Articleship, ICAI) located in `ul.styles_JDC__job-highlight-list__QZC12 li` are scanned immediately upon page load before un-clamping or LLM scoring, dropping disqualified roles in ~1.5s with multi-bullet line-by-line regex isolation.
*   **Card-Level Experience Band Gating (Guardrail C24):** Parses the SRP card's `exp_text` metadata (e.g. `"4 - 9 Yrs"`) **before** initiating a deep-scan of the job detail page. If the card-stated minimum experience exceeds `candidate.total_experience_years + target_jobs.max_experience_gap_years` (both sourced dynamically from the active profile's `candidate_config.json` — zero hardcoding), the job is immediately rejected with ledger status `experience_gap_gated` without spending any tokens on deep scraping or AI evaluation. This closes the thin-JD false-positive vector where a sparse JD body contains no experience text, causing the JD-body regex to silently award the "no restriction" bonus score.
*   **Radio Chip Option-Constrained Resolution (Guardrail C34):** Solves qualitative proficiency options (`['Beginner', 'Intermediate', 'Expert']`) when candidates have zero experience by mapping to the lowest proficiency tier rather than unconstrained strings, enforcing option conformity before DOM click with automatic fallback retries.
*   **Two-Stage Page Navigation Timeout Recovery (Guardrail C32):** Resilient two-stage navigation (`commit` [60s] + `domcontentloaded` [75s]) that gracefully recovers from third-party syndicated gateway timeouts without crashing or leaving zombie tabs.
*   **Empirical DOM Invariant vs. Dynamic Runtime Separation:** Decouples platform layout, attributes, and tags (DOM invariant layer) from dynamic candidate and job data (runtime layer), guaranteeing high reliability across portal layout evolutions.
*   **Discovery Engine & SRP Card Telemetry:** Micro-batched ($O(1)$) job discovery sweeps utilizing Playwright over Chrome DevTools Protocol (CDP) with dynamic URL parameter injection (`wfhType`, `companyJobs`). Scrapes granular search results card data: Designation, Company, Rating, Review Count, Experience, Salary, Location, Skill Chips, and Posting Recency.
*   **Deep Multi-Section JD Ingestion & "Read More" Un-Clamping:** Automatically un-clamps CSS-truncated descriptions (`-webkit-line-clamp: 5` on `div.styles_read-more__TFiRZ`) by clicking `span.styles_rm-link__RgrMs`, expanding extracted JD context from 3.4k to 7.2k+ characters across Job Highlights, Responsibilities, Benefits, Specifications, Education, and Key Skills.
*   **Naukri Native Match Score Cognitive Booster:** Scrapes live portal match criteria (`div.styles_JDC__match-score__VnjLL` for `Early Applicant`, `Keyskills`, `Location`, `Work Experience`) via state icons (`.ni-icon-check_circle` vs `.ni-icon-crossMatchscore`), injecting a verified confidence bonus (+10% for Keyskills + Exp) into the Stage 2 evaluation engine.
*   **Dual-Brain Reasoner:** Evaluates roles, scores matching taxonomy, and reverse-engineers dynamic recruiter screening questions in real-time via Gemini or non-blocking File-Based IPC (`pending_question.json`).
*   **Cognitive Selective Profile Sync:** 5-step evaluation engine that audits live portal profiles against ground-truth resumes, generates per-role JSON evaluation cards (`KEEP_EXISTING` vs `UPDATE_REQUIRED` vs `ADD_NEW`), and performs surgical updates via verified modal selectors.
*   **ATS Tailoring Engine:** Parses Markdown Master Resumes, scores bullet points against scraped Job Descriptions via NLP, and renders localized A4 PDFs.
*   **DOM Solver:** Navigates complex modal drawers, intercepts contenteditable fields, and resolves single-page application wrappers with behavioral human-emulation (keystroke jitter, viewport alignment).
*   **Cryptographic Verification:** Validates physical ledger entries on platform history pages before confirming an application as successful.

## Key Features

*   **Guardrail P1 (Codebase Purity Enforcer):** Automated runtime AST and token purity verification (`ctx.verify_codebase_purity()`) ensuring zero candidate PII or hardcoded values in `core/`.
*   **Dynamic Startup & Profile Auto-Discovery:** Automatic runtime profile discovery (making `--profile` optional) and pre-flight CDP port 9222 diagnostics before automation loops start.
*   **Zero-Hardcoding Policy:** Complete separation of codebase and candidate data sandboxes (`profiles/`).
*   **Platform Isolation:** Independent, decoupled execution environments for diverse job platforms (Naukri & LinkedIn).
*   **Self-Learning Ledger:** $O(1)$ exact-match caching for recurring screening questions to minimize API overhead and ensure deterministic truth scaling.
*   **Anti-Detection Behaviors:** Native session reuse, random execution jitter (45–130ms), and headless-evasion via persistent authenticated Chrome instances.

## Directory Structure

```text
.
├── core/                              # Execution pipeline scripts
│   ├── continuous_career_agent.py     # Master autonomous daemon loop (Daemon 1)
│   ├── 01_ai_analyzer.py              # Cognitive profile synthesizer
│   ├── 02_profile_sync_naukri.py      # Surgical selective Naukri profile sync
│   ├── 02b_naukri_fast_resume_upload.py # Standalone fast resume PDF uploader
│   ├── 03_profile_sync_linkedin.py    # LinkedIn profile updater
│   ├── 04_job_discovery.py            # Batched discovery orchestrator, SRP scraper & match score extractor
│   ├── 05_apply_jobs.py               # DOM interaction, chatbot solver & Easy Apply handler
│   ├── generate_factual_tailored.py   # Markdown-to-PDF ATS compiler
│   ├── ai_client.py                   # Central AI reasoning brain, match score booster & IPC bridge
│   ├── ipc_watcher.py                 # File-based IPC signal relay daemon (Daemon 2)
│   ├── ipc_auto_resolver.py           # Standalone IPC question auto-resolver utility
│   ├── knowledge/
│   │   └── platform_heuristics.json   # Platform DOM selectors, slug routing & circuit breakers
│   ├── scrapers/                      # Portal scraper base classes and implementations
│   │   ├── base_scraper.py
│   │   ├── naukri_scraper.py
│   │   └── linkedin_scraper.py
│   └── utils/
│       ├── profile_context.py         # ProfileContext, Purity Enforcer & ProcessedLedger
│       ├── browser_manager.py         # CDP browser lifecycle manager
│       └── search_state_manager.py    # Sequential designation rotation & cycle persistence
├── CompanySiteApply/                  # On-demand direct company ATS application engine
│   ├── cli.py                         # Interactive CLI runner for direct ATS applications
│   ├── ats_arm.py                     # ATS orchestrator arm
│   ├── ats_detector.py                # Portal platform detection engine
│   ├── fingers/                       # ATS platform adapters (Oracle Cloud HCM, Workday, Greenhouse, etc.)
│   ├── nails/                         # Company-specific ATS customization layers (JPMC, Bristlecone)
│   ├── CompanyScraper/                # Direct company career site scrapers
│   ├── parser_doctor/                 # ATS resume parsing healing and review verification
│   └── utils/                         # DOM helpers & honeypot guards
├── scripts/                           # Operational and maintenance utilities
│   └── reevaluate_ledger.py           # Ledger re-evaluation reset utility
├── docs/                              # Technical blueprints, DOM catalogs & rules
│   ├── WORKSPACE_RULES.md             # 8 directives & 43 bug prevention guardrails (33 C, 6 H, 3 D, 1 P)
│   ├── ARCHITECTURE_REFERENCE.md      # Full architecture, DOM schemas & IPC contracts
│   ├── REFERENCE_DEPLOYMENT_GUIDE.md  # 5-minute candidate onboarding & verification guide
│   └── GEMINI_WEB_AI_PROMPTS.md       # Onboarding prompts for Gemini Web AI
└── profiles/                          # .gitignored candidate sandboxes (default_user schema exemplar)
```

## [WARNING] Data Privacy & Security

This repository contains the engine's source code only. The `profiles/` directory, which manages `candidate_config.json`, Master Resumes, and tracking ledgers, is strictly excluded via `.gitignore` to prevent the leakage of Personally Identifiable Information (PII).

## License

Proprietary and Confidential. Copyright (c) 2026 Amitsagar Kandpal. All Rights Reserved.
This software and its documentation are strictly proprietary and confidential. No public or open-source license (such as MIT or Apache) is granted. See [LICENSE](LICENSE) and [COPYRIGHT.md](COPYRIGHT.md) for details.