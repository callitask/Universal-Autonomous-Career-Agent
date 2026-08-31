# Universal Autonomous Career Agent

An enterprise-grade, fully autonomous AI agent designed to orchestrate the complete job application lifecycle. Operating via a dual-brain architecture (Gemini Flash + Antigravity 2.0 terminal fallback), this pipeline autonomously discovers roles, evaluates suitability, dynamically tailors ATS-compliant resumes, and executes multi-step applications across enterprise job portals.

## 🧠 System Architecture

The agent is built on a strict, candidate-agnostic framework. Zero personal data is hardcoded; everything resolves dynamically at runtime from isolated profile sandboxes.

*   **Discovery Engine:** Micro-batched (O(1)) job discovery sweeps utilizing Playwright over Chrome DevTools Protocol (CDP).
*   **Dual-Brain Reasoner:** Evaluates roles, scores matching taxonomy, and reverse-engineers dynamic recruiter screening questions in real-time.
*   **ATS Tailoring Engine:** Parses Markdown Master Resumes, scores bullet points against scraped Job Descriptions via NLP, and renders localized A4 PDFs.
*   **DOM Solver:** Navigates complex modal drawers, intercepts contenteditable fields, and resolves single-page application wrappers with behavioral human-emulation (keystroke jitter, viewport alignment).
*   **Cryptographic Verification:** Validates physical ledger entries on platform history pages before confirming an application as successful.

## 🚀 Key Features

*   **Zero-Hardcoding Policy:** Complete separation of codebase and candidate data.
*   **Platform Isolation:** Independent execution environments for diverse job platforms.
*   **Self-Learning Ledger:** O(1) exact-match caching for recurring screening questions to minimize API overhead and ensure deterministic truth scaling.
*   **Anti-Detection Behaviors:** Native session reuse, random execution jitter, and headless-evasion via persistent authenticated Chrome instances.

## 📂 Directory Structure

```text
.
├── core/                              # Execution pipeline scripts
│   ├── ai_client.py                   # Central AI reasoning brain
│   ├── 04_job_discovery.py            # Batched discovery orchestrator
│   ├── 05_apply_jobs.py               # DOM interaction and chatbot solver
│   └── generate_factual_tailored.py   # Markdown-to-PDF ATS compiler
├── docs/                              # Technical blueprints & rules
└── profiles/                          # .gitignored candidate sandboxes
```

## ⚠️ Data Privacy & Security

This repository contains the engine's source code only. The `profiles/` directory, which manages `candidate_config.json`, Master Resumes, and tracking ledgers, is strictly excluded via `.gitignore` to prevent the leakage of Personally Identifiable Information (PII).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.