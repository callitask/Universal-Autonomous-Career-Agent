# Universal Autonomous Career Agent

An enterprise-grade, fully autonomous AI agent designed to orchestrate the complete job application lifecycle. Operating via a dual-brain architecture (Gemini Hosted Mode + Antigravity 2.0 File-Based IPC), this pipeline autonomously discovers roles, evaluates suitability, dynamically tailors ATS-compliant resumes, and executes multi-step applications across enterprise job portals.

## 🧠 System Architecture

The agent is built on a strict, candidate-agnostic framework. Zero personal data is hardcoded; everything resolves dynamically at runtime from isolated profile sandboxes.

*   **Empirical DOM Invariant vs. Dynamic Runtime Separation:** Decouples platform layout, attributes, and tags (DOM invariant layer) from dynamic candidate and job data (runtime layer), guaranteeing high reliability across portal layout evolutions.
*   **Discovery Engine & SRP Card Telemetry:** Micro-batched ($O(1)$) job discovery sweeps utilizing Playwright over Chrome DevTools Protocol (CDP) with dynamic URL parameter injection (`wfhType`, `companyJobs`). Scrapes granular search results card data: Designation, Company, Rating, Review Count, Experience, Salary, Location, Skill Chips, and Posting Recency.
*   **Deep Multi-Section JD Ingestion & "Read More" Un-Clamping:** Automatically un-clamps CSS-truncated descriptions (`-webkit-line-clamp: 5` on `div.styles_read-more__TFiRZ`) by clicking `span.styles_rm-link__RgrMs`, expanding extracted JD context from 3.4k to 7.2k+ characters across Job Highlights, Responsibilities, Benefits, Specifications, Education, and Key Skills.
*   **Naukri Native Match Score Cognitive Booster:** Scrapes live portal match criteria (`div.styles_JDC__match-score__VnjLL` for `Early Applicant`, `Keyskills`, `Location`, `Work Experience`) via state icons (`.ni-icon-check_circle` vs `.ni-icon-crossMatchscore`), injecting a verified confidence bonus (+10% for Keyskills + Exp) into the Stage 2 evaluation engine.
*   **Dual-Brain Reasoner:** Evaluates roles, scores matching taxonomy, and reverse-engineers dynamic recruiter screening questions in real-time via Gemini or non-blocking File-Based IPC (`pending_question.json`).
*   **Cognitive Selective Profile Sync:** 5-step evaluation engine that audits live portal profiles against ground-truth resumes, generates per-role JSON evaluation cards (`KEEP_EXISTING` vs `UPDATE_REQUIRED` vs `ADD_NEW`), and performs surgical updates via verified modal selectors.
*   **ATS Tailoring Engine:** Parses Markdown Master Resumes, scores bullet points against scraped Job Descriptions via NLP, and renders localized A4 PDFs.
*   **DOM Solver:** Navigates complex modal drawers, intercepts contenteditable fields, and resolves single-page application wrappers with behavioral human-emulation (keystroke jitter, viewport alignment).
*   **Cryptographic Verification:** Validates physical ledger entries on platform history pages before confirming an application as successful.

## 🚀 Key Features

*   **Guardrail P1 (Codebase Purity Enforcer):** Automated runtime AST and token purity verification (`ctx.verify_codebase_purity()`) ensuring zero candidate PII or hardcoded values in `core/`.
*   **Dynamic Startup & Profile Auto-Discovery:** Automatic runtime profile discovery (making `--profile` optional) and pre-flight CDP port 9222 diagnostics before automation loops start.
*   **Zero-Hardcoding Policy:** Complete separation of codebase and candidate data sandboxes (`profiles/`).
*   **Platform Isolation:** Independent, decoupled execution environments for diverse job platforms (Naukri & LinkedIn).
*   **Self-Learning Ledger:** $O(1)$ exact-match caching for recurring screening questions to minimize API overhead and ensure deterministic truth scaling.
*   **Anti-Detection Behaviors:** Native session reuse, random execution jitter (45–130ms), and headless-evasion via persistent authenticated Chrome instances.

## 📂 Directory Structure

```text
.
├── core/                              # Execution pipeline scripts
│   ├── continuous_career_agent.py     # Master autonomous daemon loop
│   ├── 01_ai_analyzer.py              # Cognitive profile synthesizer
│   ├── 02_profile_sync_naukri.py      # Surgical selective Naukri profile sync
│   ├── 02b_naukri_fast_resume_upload.py # Standalone fast resume PDF uploader
│   ├── 03_profile_sync_linkedin.py    # LinkedIn profile updater
│   ├── 04_job_discovery.py            # Batched discovery orchestrator, SRP scraper & match score extractor
│   ├── 05_apply_jobs.py               # DOM interaction, chatbot solver & Easy Apply handler
│   ├── generate_factual_tailored.py   # Markdown-to-PDF ATS compiler
│   ├── ai_client.py                   # Central AI reasoning brain, match score booster & IPC bridge
│   └── utils/
│       ├── profile_context.py         # ProfileContext, Purity Enforcer & ProcessedLedger
│       └── browser_manager.py         # CDP browser lifecycle manager
├── docs/                              # Technical blueprints, DOM catalogs & rules
│   ├── WORKSPACE_RULES.md             # 8 directives & 18 bug prevention guardrails
│   ├── ARCHITECTURE_REFERENCE.md      # Full architecture, DOM schemas & IPC contracts
│   ├── REFERENCE_DEPLOYMENT_GUIDE.md  # 5-minute candidate onboarding & verification guide
│   └── GEMINI_WEB_AI_PROMPTS.md       # Onboarding prompts for Gemini Web AI
└── profiles/                          # .gitignored candidate sandboxes
```

## ⚠️ Data Privacy & Security

This repository contains the engine's source code only. The `profiles/` directory, which manages `candidate_config.json`, Master Resumes, and tracking ledgers, is strictly excluded via `.gitignore` to prevent the leakage of Personally Identifiable Information (PII).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.