# Universal Autonomous Career Agent: Complete Engineering & Strengthening Plan

## 1. Overview
This plan outlines the complete implementation to upgrade the **Universal Autonomous Career Agent** into a truly autonomous, intelligent, zero-API career orchestration system. 

The core architectural enhancement is establishing **Google Antigravity 2.0 as the primary cognitive brain** via an expanded File-Based IPC protocol (`pending_question.json`). This allows the agent to analyze candidate profiles, understand candidate skills with human-level comprehension, search and match jobs accurately, factually tailor ATS resumes, and solve platform questionnaires autonomously without needing external API keys.

---

## 2. User Review & Architectural Directives

> [!IMPORTANT]
> **Strict Zero-Hardcoding & Profile Sandboxing (Directive 2 Clause 8):**
> Under no circumstances will any candidate values, names, CTCs, or domains be hardcoded into Python files. The `profiles/` directory remains untouched by the developer; all candidate sandboxes will be dynamically inspected and autonomously maintained by the running agent at runtime.

> [!IMPORTANT]
> **Directive 1 Full-File Delivery:**
> Every modified script (`core/ai_client.py`, `core/04_job_discovery.py`, `core/05_apply_jobs.py`, `core/generate_factual_tailored.py`, `core/02_profile_sync_naukri.py`) will be delivered 100% complete from line 1 to EOF with zero placeholder comments or omitted methods.

---

## 3. Proposed Changes & Component Architecture

### Component 1: `core/ai_client.py` — The Universal Zero-API Cognitive Brain

#### [MODIFY] [ai_client.py](file:///F:/JOB%20AI%20AGENT/core/ai_client.py)
1. **Zero-API Antigravity 2.0 Cognitive IPC Bridge:**
   - Expand `_fallback_antigravity_ipc()` to handle structured tasks beyond simple questionnaires:
     - `task_type="PROFILE_SYNTHESIS"`: When no Gemini API key is available, writes prompt containing `resume.md` and candidate config to `pending_question.json`. Antigravity 2.0 synthesizes domain, core skills, soft skills, domain acronyms, incompatible verticals, and 3-cycle designation queues.
     - `task_type="JOB_EVALUATION"`: Sends full JD, candidate profile, and resume excerpt to `pending_question.json` for Antigravity 2.0 to evaluate with human-level precision, returning 0–100 score, reasoning, matching skills, and missing skills.
     - `task_type="RESUME_TAILORING"`: Sends JD and master resume summary/competencies to `pending_question.json` for Antigravity 2.0 to produce a targeted summary and prioritized competency order.
     - `task_type="STARVATION_EXPANSION"`: Sends seen market titles and candidate experience to `pending_question.json` for Antigravity 2.0 to expand senior designations.
     - `task_type="QUESTIONNAIRE"`: Preserves existing high-speed Q&A resolution.
2. **Elimination of Hardcoded Taxonomies:**
   - Remove static `INDUSTRY_TAXONOMY` (7 industries) in favor of dynamic runtime synthesis by Antigravity 2.0, with a resilient semantic fallback that dynamically clusters skills from `resume.md`.
3. **Fix Experience Parsing Regex (Defect 2):**
   - Anchor experience regex matching strictly to requirements keywords (`minimum`, `min`, `experience`, `relevant experience`). Filter out company age statements (e.g., "over 25 years in business") to eliminate false rejections.
4. **Fix Incompatible Vertical Gating (Defect 3):**
   - Implement functional domain title override: If the job title belongs to candidate's domain (e.g. "Finance", "Accounts", "Tax", "Audit"), cross-functional tooling mentions in the JD (e.g. "software", "sql", "database") will NOT trigger an incompatible industry rejection.
5. **Preserve Immutable Public Contracts:**
   - Maintain exact signatures for `evaluate_job_match()`, `generate_text()`, `arbitrate_card_fit()`, `synthesize_cognitive_profile()`, and `MatchResult`.

---

### Component 2: `core/04_job_discovery.py` — Discovery & Safe Deduplication Engine

#### [MODIFY] [04_job_discovery.py](file:///F:/JOB%20AI%20AGENT/core/04_job_discovery.py)
1. **Fix Catastrophic Title-Ledger Deduplication Bug (Defect 1):**
   - Remove `title.lower() in processed_ledger` and `ctx.add_to_processed_ledger(title.lower(), status="processed_title")`.
   - Implement safe two-tier deduplication:
     * Tier 1: Canonical Job URL (`url.strip().lower()`).
     * Tier 2: Composite Company + Title key (`f"{clean_company}::{clean_title}"`).
   - Ensures an application to "Senior Accountant" at Company A never blocks an application to "Senior Accountant" at Company B.
2. **Incompatible Industry Check in `is_title_allowed()`:**
   - Add check against `incompatible_verticals` from `cognitive_profile.json` before passing card to deep scan, preventing wasted page loads.
3. **Seamless IPC Integration:**
   - Ensure `evaluate_job_match()` routes to Antigravity 2.0 IPC when no API key is present, providing real semantic evaluation instead of brittle regex scoring.

---

### Component 3: `core/05_apply_jobs.py` — Application Engine & LinkedIn Easy Apply

#### [MODIFY] [05_apply_jobs.py](file:///F:/JOB%20AI%20AGENT/core/05_apply_jobs.py)
1. **Implement `LinkedInApplyHandler`:**
   - Detect `button.jobs-apply-button`, `button:has-text('Easy Apply')`, and `.jobs-apply-button--top-card`.
   - Handle multi-step modal (`div.jobs-easy-apply-modal`, `.artdeco-modal`).
   - Solve form controls: text inputs, phone numbers, numeric years of experience, radio buttons, dropdowns, and file upload for tailored PDF.
   - Advance through steps: "Next" $\rightarrow$ "Review" $\rightarrow$ "Submit application".
   - Verify submission on LinkedIn confirmation screens (`Application sent`, `Your application was sent to...`).
   - Log outcome to `applications_tracker.csv` with status `APPLIED_LINKEDIN_EASY_APPLY`.
2. **Preserve All Naukri Chatbot Guardrails:**
   - Preserve Guardrail C9 platform rejection banner detection and premature drawer closure detection.
   - Preserve Guardrail H5 React contenteditable typing and synthetic event dispatch.
   - Preserve Guardrail C7 3x stuck question loop breaker.

---

### Component 4: `core/generate_factual_tailored.py` — Factual ATS Resume Tailoring Engine

#### [MODIFY] [generate_factual_tailored.py](file:///F:/JOB%20AI%20AGENT/core/generate_factual_tailored.py)
1. **Factual ATS Tailoring Intelligence (Zero Hallucinations):**
   - Dynamically tailor the **Professional Summary** to align with the target job's primary domain and mission using factual resume data via `AIClient`.
   - Dynamically prioritize and group **Core Competencies / Skills** to place the JD's required skills first.
   - Reorder experience bullets based on JD keyword relevance with bold highlighting of matching technical terms.
   - Compute and record an **ATS Match Index ($0-100\%$)** in `job_details.json`.
2. **A4 Page Budget & Layout Protection:**
   - Enforce CSS page rules and dynamic margins to ensure clean 1-page or 2-page print layout without single-line overflow pages.

---

### Component 5: `core/02_profile_sync_naukri.py` — Context & Automation Fix

#### [MODIFY] [02_profile_sync_naukri.py](file:///F:/JOB%20AI%20AGENT/core/02_profile_sync_naukri.py)
1. **Multi-User Context Desync Fix:**
   - Replace `AI_CLIENT = AIClient()` with `AI_CLIENT = AIClient(CTX)` to guarantee proper sandbox isolation in multi-profile setups.
2. **Eliminate Hardcoded 30s Wait:**
   - Automate start/end date selection where possible or route via IPC rather than freezing the script on an arbitrary 30-second delay.

---

### Component 6: Documentation & Workspace Reference

#### [MODIFY] [WORKSPACE_RULES.md](file:///F:/JOB%20AI%20AGENT/docs/WORKSPACE_RULES.md)
- Update with documentation of the Unified Zero-API Antigravity 2.0 Cognitive IPC Bridge, LinkedIn Easy Apply specifications, and Composite Deduplication Ledger rules.

#### [MODIFY] [ARCHITECTURE_REFERENCE.md](file:///F:/JOB%20AI%20AGENT/docs/ARCHITECTURE_REFERENCE.md)
- Update pipeline execution sequence and IPC contract diagrams to document the multi-task `pending_question.json` schema and LinkedIn handler architecture.

---

## 4. Verification Plan

### Automated Verification
- Run Python syntax checks (`python -m py_compile`) on all modified files in `core/`.
- Verify imports across scripts (`core.utils.profile_context`, `core.ai_client`, `core.utils.browser_manager`).
- Test `evaluate_job_match()` with test fixtures covering:
  * Company age in description (e.g., "25 years of excellence") $\rightarrow$ must not auto-reject.
  * Cross-functional tooling (e.g., "software" in accounting JD) $\rightarrow$ must not reject as software engineering.
  * Composite deduplication $\rightarrow$ same title at different companies must not be skipped.
- Test `generate_factual_tailored.py` output structure and PDF generation.

### Verification of Dead Code Cleanup
- Remove obsolete scratch scripts in the artifact scratch directory.
