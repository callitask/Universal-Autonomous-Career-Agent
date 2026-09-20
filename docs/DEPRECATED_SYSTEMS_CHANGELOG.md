# UNIVERSAL AUTONOMOUS CAREER AGENT: DEPRECATED SYSTEMS & ARCHITECTURAL DECISIONS

> **Purpose:** Document systems, architectures, and features that were downgraded, removed, or significantly refactored. Future AI agents must read this document before attempting to re-implement old features. This prevents repeating past mistakes and explains *why* certain approaches were abandoned.

## 1. Terminal Standard Input (Blocking IPC)
* **Removed From:** `core/ai_client.py`, `core/05_apply_jobs.py`
* **When:** Transition to Antigravity 2.0
* **Reason:** Calling `sys.stdin.readline()` inside a background subprocess permanently hung the application pipeline. Background daemons have no interactive TTY attached.
* **Replaced With:** File-Based Asynchronous IPC (`pending_question.json`) and the `ipc_watcher.py` Daemon. The system now uses non-blocking polling, allowing the background daemon to wait without freezing.

## 2. Serial 90-Second IPC Blocking (Batch Architecture v1.0)
* **Removed From:** `core/04_job_discovery.py`
* **When:** Batch Architecture v2.0 Update
* **Reason:** Pausing the entire discovery loop for up to 90 seconds per single job card evaluation created severe bottlenecks, limiting throughput.
* **Replaced With:** ARM -> BRAIN -> EXECUTE Architecture. The scraper collects all job cards for a designation (ARM), dispatches them in bulk to `batch_question.json` (BRAIN), and executes deep scans only on approved cards (EXECUTE).

## 3. Python-Hardcoded Keyword Screening Lists
* **Removed From:** `core/ai_client.py` (`_is_standard_screening_query`, `_heuristic_screening_answer`)
* **When:** Guardrail P1 Enforcement (Zero-Trust)
* **Reason:** Hardcoding screening keywords (e.g., notice period triggers, relocation, interview modes) directly in Python code violates the zero-hardcoding mandate. When new tools/roles emerged, Python scripts required manual developer updates, causing regressions.
* **Replaced With:** Dynamic `screening_heuristics` block in `profiles/<profile>/candidate_config.json`. The agent dynamically resolves all detection regex patterns via JSON.

## 4. Single-Title Ledger Deduplication
* **Removed From:** `core/utils/profile_context.py`, `core/04_job_discovery.py`
* **When:** Anti-Starvation D1 Fix
* **Reason:** Writing a solitary job title (e.g., `"Senior Accountant"`) to `processed_ledger.json` caused the deduplication engine to falsely reject *every* future job with that title across all companies.
* **Replaced With:** Composite Key Deduplication (`clean_company::clean_title`).

## 5. Regex Multi-Bullet Bleeding
* **Removed From:** `core/ai_client.py` (Stage 1 Qualification)
* **When:** Guardrail v5.0 Fix
* **Reason:** Evaluating regular expressions across entire multiline blocks (`highlights_content.splitlines()`) allowed matches in bullet 2 to mistakenly exempt negative filters in bullet 1.
* **Replaced With:** Strict line-by-line regex isolation.

## 6. Greedy Naukri Selector `div[class*='chip']`
* **Removed From:** `core/05_apply_jobs.py`
* **When:** Bug 4 Fix
* **Reason:** Matched the Naukri branding logo (`.chipMsg`), causing the application loop to repeatedly attempt clicking the logo instead of resolving radio buttons.
* **Replaced With:** Highly specific empirical selectors (`div.clickableChip`, `label.ssrc__label`) excluding `.chipMsg`.

## 7. Direct File Writing for Configuration
* **Removed From:** `core/utils/profile_context.py`
* **When:** Guardrail C4 Fix
* **Reason:** Direct `open("w")` on `candidate_config.json` resulted in corrupted/empty files if the daemon crashed during the write operation.
* **Replaced With:** Atomic `.tmp` file write followed by `os.replace()`.
