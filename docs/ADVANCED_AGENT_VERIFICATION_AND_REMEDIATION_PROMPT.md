# Advanced Agent — Complete Verification, Documentation & Dynamic Knowledge-Graph Brief
> **Version:** 2.1 — Sibling Sophron at F:\Sophron, domain-split knowledge, model-agnostic intelligence
> **Last Updated:** 2026-09-22
> **Status:** VERIFICATION-FIRST. This is NOT a blind implementation order. Prove understanding first. A naive fix will corrupt the system.

> You are a higher-capability agent. A prior read-only audit made claims about this workspace.
> **Do NOT trust those claims blindly. Workarounds and intentional quirks exist.**
> First prove you understand the architecture, rules, and runtime reality line-by-line. Only fixes that survive your own independent verification with `file:line` evidence may proceed.

## 0. Non-negotiable owner constraints (read first, violations = breach)

1. **Two separate repos, not one (sibling layout since 2026-09-22).**
    - Repo A — **JOB AI AGENT** (root `F:\JOB AI AGENT\.git`, remote `callitask/Universal-Autonomous-Career-Agent`): `core/`, `CompanySiteApply/`, `scripts/`, `docs/`, `.agents/rules/`, `profiles/`, `knowledge/` (agent_structure only), root docs.
    - Repo B — **Sophron** (`F:\Sophron\.git`, remote `callitask/Sophron.git`, override via `SOPHRON_ROOT` env): `core/`, `graph_memory/`, `understanding_master/`, `interaction_history/`, `meta_cognition/`, `workspaces/`, `integration/`, `tests/`, `output/`, `master_agent_config.json`, `SYSTEM_PROMPT_INJECTION.md`, `session_registry.json`.
    - Treat git roots, commits, and concerns separately. Never commit both repos in one command. Never import across repos (`core/` must never import Sophron; Sophron must never drive job-application loops). Knowledge is split by `domain`: `agent_structure` (agent code/docs, updated on agent dev, free from personal intelligence) vs `personal_intelligence` (human + AI session learning, updated every AI session regardless of model — Antigravity, Muse, Claude — with `agent_model` + `software` logged). Document the boundary explicitly in every map you produce.

2. **Profiles are volatile dynamic data, never source of truth.**
   - `profiles/<live_profile>/` (`anshika_garg/`, `bharat_pandey/`, `suresh_chaudhary/`, `udaysagar_kandpal/`, any future folder) contains input + output that can be created, changed, deleted, or replaced per selected profile at any time.
   - **You may read ONLY `profiles/default_user/`** (schema blueprint: `candidate_config.json`, `resume.md`, `cover_letter_template.md`, `README.md`, `output/` skeleton) to learn input shape and output conventions.
    - **Forbidden:** reading live profile configs/resumes/ledgers/CSVs to justify engine changes; copying any live name, email, phone, city, PIN, CTC, title, or company into code, docs, rules, graph nodes, or vector chunks; editing anything under `profiles/<live>`. Engine code must stay generic via `ProfileContext` + `candidate_config.json` + `screening_heuristics`. Respect `.gitignore` (`profiles/`, `*.log`, scan leftovers; Sophron lives in its own sibling repo).

3. **License is personal proprietary only.**
   - No MIT grant exists. Correct end-state everywhere (`README.md`, `LICENSE`, `COPYRIGHT.md`): personal use only, no copy/distribute/modify/use without explicit written permission of the owner. Do not introduce any public license text.

4. **Deleted files stay deleted.**
   - `docs/SESSION_REPORT_2026-09-19.md` and `docs/AUDIT_REPORT_2026-09-20.md` were removed as useless. Do not reference, resurrect, or rebuild them. Prior claims sourced from them are void unless you re-derive them from code.

5. **Anti-corruption law:** intelligence = restraint. `UNDERSTANDING INCOMPLETE â€” no changes made` beats a confident wrong edit. Report diffs first; change code/docs/graph only on explicit owner approval per batch.

---

## 1. Complete line-by-line analysis scope (everything except live profiles)

You must walk the tree file-by-file. No sampling. For **every** `.py`, `.md`, `.json` in scope, record: purpose, classes/functions with signatures, callers/consumers, contracts/guardrails enforced, DOM selectors/IPC keys touched, and whether docs describe it correctly.

**1A. Root Repo A â€” JOB AI AGENT (exclude `__pycache__`, `output.log`, OS files):**
- Root files: `README.md`, `UNIVERSAL_AGENT_SETUP.md`, `UNIVERSAL_AGENT_PROMPT_v2.md`, `COPYRIGHT.md`, `LICENSE`, `.gitignore`, `desktop.ini` (note OS artifact, do not document as architecture).
- `.agents/rules/`: `ACTIVE_CONSTRAINT_BLOCK.md` (GATE 1â€“11), `SCAR_TISSUE.md` (append-only), `00_user_cognitive_os.md`, `01_sophron_session_init.md`, `02_career_agent_operational_rules.md`, `03_career_agent_session_profile_init.md`, `workspace_rules.md`; `.agents/README.md` (v4.0 Batch â€” current launch directive).
- `core/` (all 19 source files, no exceptions):
  - Top: `01_ai_analyzer.py`, `02_profile_sync_naukri.py`, `02b_naukri_fast_resume_upload.py`, `03_profile_sync_linkedin.py`, `04_job_discovery.py`, `05_apply_jobs.py`, `ai_client.py`, `continuous_career_agent.py`, `generate_factual_tailored.py`, `ipc_auto_resolver.py`, `ipc_watcher.py`
  - `core/utils/`: `browser_manager.py`, `profile_context.py`, `search_state_manager.py`
  - `core/scrapers/`: `__init__.py`, `base_scraper.py`, `linkedin_scraper.py`, `naukri_scraper.py` (verify `WORKSPACE Appendix A` `DEAD CODE` claim â€” live or dead?)
  - `core/knowledge/`: `platform_heuristics.json`
- `CompanySiteApply/` â€” historically under-documented, document fully line-by-line:
  - Root: `__init__.py`, `ats_arm.py`, `ats_detector.py`, `cli.py` (note `input(">> ")` debug CLI â€” only stdin exception; never port to `core/`)
  - `fingers/`: `__init__.py` (registry order), `base_finger.py`, `oracle_cloud_finger.py`, `workday_finger.py`, `greenhouse_finger.py`, `generic_finger.py`
  - `nails/` (currently undocumented in README): `__init__.py`, `base_nail.py`, `oracle/__init__.py`, `oracle/jpmc_nail.py`, `oracle/bristlecone_nail.py` â€” capture company-override pattern vs finger pattern
  - `CompanyScraper/` (currently undocumented): `__init__.py`, `base_scraper.py`, `cli_scraper.py`, `companies/__init__.py`, `companies/jpmorgan/__init__.py`, `companies/jpmorgan/jpmorgan_scraper.py`, `companies/jpmorgan/config.json`
  - `parser_doctor/`: `__init__.py`, `line_wrap_healer.py`, `education_healer.py`, `review_verifier.py`
  - `utils/`: `__init__.py`, `dom_helpers.py`, `honeypot_guard.py`
  - `inspections/`: `generic_adaptive/adaptive_form_step_*.json` (2), `oracle_cloud_hcm/authentication_email_*.json` + `unknown_*.json` (9) â€” schema, not live PII to copy
  - `tests/`: `test_parser_doctor.py`
  - Docs: `README.md`, `SCOPE_OF_EDIT.md`
- `scripts/`: `reevaluate_ledger.py` (only file â€” document purpose + ledger statuses it touches)
- `docs/`: `WORKSPACE_RULES.md`, `ARCHITECTURE_REFERENCE.md`, `PLATFORM_KNOWLEDGE.md`, `GEMINI_WEB_AI_PROMPTS.md`, `REFERENCE_DEPLOYMENT_GUIDE.md`, `COMPANY_ATS_KNOWLEDGE.md`, `ORACLE_HCM_ATS_DEEP_DIVE.md`, `STRATEGIC_RESUME_TAILORING.md`, `UNIVERSAL_ATS_REVERSE_ENGINEERING_PLAYBOOK.md`, `KNOWLEDGE_GRAPH_CHANGELOG.md`, `DEPRECATED_SYSTEMS_CHANGELOG.md`, plus this brief
- `profiles/default_user/` ONLY: `candidate_config.json` (full `screening_heuristics` schema), `resume.md` (format), `cover_letter_template.md`, `README.md`, `output/` skeleton
- `scratch/answer_resume.py` (note scratch status â€” do not promote to architecture)

**1B. Root Repo B â€” Sophron (separate git root, cognitive memory only):**
- `README.md`, `SYSTEM_PROMPT_INJECTION.md`, `master_agent_config.json` (note stale `transcript_path` UUID pattern), `session_registry.json`, `.gitignore`
- `core/`: `__init__.py`, `workspace_guard.py`, `graph_memory_engine.py`, `persona_loader.py`, `transcript_learner.py`, `decision_emulator.py`, `self_healing_advisor.py`, `antigravity_context_bridge.py`, `run_master_agent.py`, `sophron_write_guard.py`, `sync_brain.py`
- `graph_memory/`: `nodes.json`, `edges.json`, `graph_index.json` (verify counts + sync)
- `understanding_master/` (all subdirs: `learned_insights/`, `macro_synthesis/BOOT_SUMMARY.md` + `current_week_trend.md`, `parallel_digital_twin/`, `predictive_reaction_engine/`, `profile_preferences/`, `self_learning_loop/`, `session_rules/`, `thinking_patterns/`, `debugging_protocols/`, `goals_and_vision/`, `instruction_styles/`, `multitasking_cards/`, `interaction_history/`)
- `interaction_history/` (`reflections_index.json`, `turn_*.json`, `session_summary_20260917.md`)
- `meta_cognition/` (4 subdirs), `workspaces/universal_autonomous_career_agent/` (`workspace_manifest.json`, `domain_rules/`, `platform_schemas/`, `task_ledger.json`), `integration/00_user_cognitive_os.md`, `tests/test_master_agent_suite.py`, `output/audits/system_audit_report.json` + `output/advice/`

**Method:** for each file, log `path:lines`, header presence (`AI CONTEXT` for `.py`), exports, and one-line `docs-match?` verdict. Produce a full directory-tree appendix in your report. If a file is not described in any doc (e.g. `nails/`, `CompanyScraper/`, `ipc_auto_resolver.py`, `sync_brain.py`, `reevaluate_ledger.py`), mark it `UNDOCUMENTED â€” must document`.

---

## 2. Understanding gates (no edits until all pass)

In your own words (not doc paraphrase), prove:

(a) **Three-daemon runtime:** Daemon 1 (`continuous_career_agent.py` loop + `--delay` actual default), Daemon 2 (`ipc_watcher.py` shared `poll` behavior for `pending_question.json` + `batch_question/batch_answer.json`), Daemon 3 (1-min cron). State actual timeouts/SLAs you measured (90s single / 120s batch) and poll intervals from code, not docs.
(b) **Batch ARMâ†’BRAINâ†’EXECUTE** (`batch_card_evaluation_ipc`, `SearchStateManager` one-designation-per-cycle, `record_stats`/`advance`, `get_active_search_cycle`/`advance_search_cycle`) vs old per-card flow. Where does per-card IPC still live (tailoring/chatbot) and where was it removed (discovery)?
(c) **Brain vs actuator boundary:** what Python may decide (numeric: salary floor, C24 exp band, exact company identity, dedup) vs what must route to AG Brain via IPC. Where is the boundary enforced (`verify_codebase_purity`, GATE 11)?
(d) **Three load-bearing workarounds** that look wrong (e.g. `options[0]` retry layers, URL slug vs `/jobs?k`, timer values, PII-looking Oracle exemplars, retained dead-code comments). For each: what failure it prevents (`SCAR_TISSUE` / `AI CONTEXT ENTRY`), what breaks if removed.
(e) **Two-repo isolation + finger/nail split:** Career Agent (`core/` portals) vs `CompanySiteApply` fingers (platform engines) vs nails (company overrides) vs `CompanyScraper` vs `parser_doctor`; Sophron (memory only). Why Company-site apply stays on-demand/human-gated, never background daemon.
(f) **Profiles volatility:** why `profiles/<live>` can never justify engine changes; how `_auto_discover_profile_dir` (excludes `default_user`), `output/` sandboxing, and purity checks enforce it.

If any gate fails, return `UNDERSTANDING INCOMPLETE` with gaps â€” do not proceed.

---

## 3. Prior claims to re-verify (questions, not orders)

Verdict each with `file:line` evidence: `[PASS]` / `[WARN]` / `[FAIL]` / `[CRITICAL]` / `[UNKNOWN]`. Prior claim loses on conflict. Deleted reports are out of scope.

**Q1 License:** Is any MIT grant real? Confirm correct end-state is personal proprietary only. Fix must align `README` + `LICENSE` + `COPYRIGHT.md` with zero public-license language.
**Q2 Guardrail counts:** Count `### C/H/D/P` in `WORKSPACE_RULES.md` yourself (â‰ˆ33C+6H+3D+1P=43?). Are all `18`/`15` claims stale? Are C24/C25/C26/C32/C34 real in code?
**Q3 G-BRAIN-01 vs C6/C28:** Does running code enforce GATE 11 (no Python semantic gating; `is_title_allowed` dead-commented; no active highlights-list code) while C6/C28 + `ARCH` Stage-1 still mandate Python `negative_keywords` matching? Which side is live? Do not delete either side until live behavior is proven.
**Q4 IPC dual-channel:** Verify writers/readers/cleanup for `batch_question/batch_answer.json` (120s) vs `pending_question.json` (tailoring/chatbot). Which docs still claim single-file?
**Q5 Task taxonomy:** grep all `task_type`. Map `BATCH_JOB_EVALUATION` vs `JOB_CARD_EVALUATION` vs `JOB_EVALUATION` vs `JOB_FULL_EVALUATION` (real or invented?) vs `QUESTIONNAIRE` vs `SCREENING_QUESTION` vs `PROFILE_SYNTHESIS`/`RESUME_TAILORING`/`STARVATION_EXPANSION`. Propose canonical map only after tracing every producer/consumer.
**Q6 `is_title_allowed`:** dead comments + zero calls (retain?) vs full purge (safe?). Check repo-wide references including docs/tooling.
**Q7 Timers/thresholds:** `>=60%` apply vs `ARCH` diagram `>=50%` (entry vs apply conflation?); `0.5s` Daemon1 vs `2.0s` Daemon2 vs claimed batch `1s` vs single `sleep(poll)`; `--delay` 30 vs `90/>=60s` vs `30-min` guides. Which are load-bearing for 120s waits?
**Q8 Root README tree:** list `core/` yourself. Omitted: `ipc_watcher.py`, `ipc_auto_resolver.py`, `search_state_manager.py`, `knowledge/platform_heuristics.json`, `scrapers/*`, `scripts/*`? Is `scrapers/` dead per Appendix A?
**Q9 CompanySiteApply gaps:** verify `nails/`, `CompanyScraper/`, `inspections/generic_adaptive/`, 9 Oracle JSONs, `utils/__init__.py` exist but undocumented. Extend docs or confirm intentionally internal?
**Q10 Output paths:** which paths does code actually write â€” `output/applications/<Co>_<Role>/` vs `APPLIED ON COMPANY WEBSITE/...`? Reconcile or explicitly document split; do not unify blindly.
**Q11 PII/zero-hardcoding:** distinguish (a) doc exemplars vs (b) code defaults (`oracle_cloud_finger.py` PIN/city fallbacks?) vs (c) captured `inspections/*.json` live data. Which trip `verify_codebase_purity()`? Justify each scrub â€” healing knowledge must survive.
**Q12 Deployment guides:** verify every stale line in `REFERENCE_DEPLOYMENT_GUIDE` v3.1 2026-09-09 + `UNIVERSAL_AGENT_SETUP` (`30-min`, counts, missing Batch/SearchState/watcher/C24-C34). Update/version-bump or archive?
**Q13 Profiles/Sophron/prompt staleness:** `rahul_sharma/` example non-existent? Actual live folders? `Sophron/README` `21/14` vs measured `55/63`, `master_agent/` vs `Sophron/` paths, omitted `sophron_write_guard.py`/`sync_brain.py`, interaction-file counts, stale CLI paths; `PROMPT_v2` v3.0 pre-Batch.
**Q14 Version drift:** `ACTIVE_CONSTRAINT_BLOCK` v1.1 vs GATE 11 date; unversioned `PLATFORM_KNOWLEDGE`/`COMPANY_ATS`/`ORACLE`/`PLAYBOOK`; `ARCH` `/jobs?k` vs slug; undocumented `ag_brain_batch_skipped` + `top_target_companies`; C34 `options[0]` vs H1 tension; duplicate `DIRECTIVE 8` heading.
**Q15 Graph/vector truth (replaces old Q15 â€” now BUILD, not just rename):** prior check found zero `faiss|chromadb|qdrant|pinecone|sentence_transformer|embedding|cosine|sklearn` in `Sophron/`; `graph_memory_engine.py` = JSON traversal, `transcript_learner.py` = regex counting, `persona_loader.py` = file scan, `graph_index.json` = plain adjacency. Confirm. Then per Section 5, BUILD the missing dynamic system (do not merely rename docs).
**Q16 Profiles boundary:** verify auto-discovery exclusion, sandboxing, pre-flight banner, purity forbidden-strings, `.gitignore` blocks. List any `.py`/doc embedding a live profile literal. Reference `default_user` only.

---

## 4. Documentation remediation (only after Section 2 passes)

Bring every in-scope `.md` to correct-and-current without copying live profile values:

- Fix `README.md` tree (add missing `core/` files, `scripts/`, correct guardrail counts, fix MIT line to personal proprietary, keep proprietary header).
- Resolve `WORKSPACE_RULES.md` duplicate `DIRECTIVE 8`, correct counts, reconcile or explicitly flag G-BRAIN-01 vs C6/C28 (do not silently delete either rule â€” document live behavior + migration intent), add C24/C32/C34 code refs.
- Update `ARCHITECTURE_REFERENCE.md` to Batch v2 reality (IPC file list, task-type canonical map from Q5, `60%` vs `50%` disambiguation, SEO-slug canonical URL, Daemon 2 dual-watch, `search_state.json` contract).
- Version/date `PLATFORM_KNOWLEDGE.md` (add version header) + dual-channel daemon section; correct `GEMINI_WEB_AI_PROMPTS.md` counts; rewrite or version-bump `REFERENCE_DEPLOYMENT_GUIDE.md` + `UNIVERSAL_AGENT_SETUP.md` (remove `30-min`, add Batch/SearchState/watcher/C24-C34).
- Document `CompanySiteApply` fully: `nails/` pattern + Oracle nails, `CompanyScraper/` + JPMorgan example, `inspections/` schemas, `cli.py` vs `cli_scraper.py`, finger registry order. Update `SCOPE_OF_EDIT.md` if scope changed.
- Fix `profiles/README.md` example (remove non-existent profile, list `default_user` as only reference), `Sophron/README.md` counts/paths/omitted cores/files/CLI, `ACTIVE_CONSTRAINT_BLOCK.md` version bump for GATE 11, `.agents/README.md` delay/poll values to match code or justify deviation.
- Scrub PII per Q11 tiers: keep teaching exemplars clearly labeled `EXEMPLAR â€” not a default`, remove runtime literal defaults into config, quarantine captured live PII in inspections (redact or mark `captured sample â€” do not copy`).
- Bump `Document Version` + `Last Updated` ONLY on files changed; log each change in `KNOWLEDGE_GRAPH_CHANGELOG.md` + `DEPRECATED_SYSTEMS_CHANGELOG.md` where architecture changed; never rewrite `SCAR_TISSUE.md` history (append only) or `AI CONTEXT` headers (append-only entries with serial/term/timestamp/rationale/preventative notes, zero PII).

---

## 5. Dynamic vector-database + knowledge-graph build (required)

Current state to confirm: file-based JSON graph + regex learner, mislabeled as `vector database` / `sub-millisecond semantic retrieval`. Build a real, lightweight, **dynamic** system future AIs can query with ease, without heavy external services unless owner approves.

**5.1 What to build (two layers, two repos aware):**
- **Layer G (deterministic graph):** extend `Sophron/graph_memory/` (`nodes.json`, `edges.json`, `graph_index.json`) + add `CareerAgent/graph/` (new, e.g. `docs/knowledge_graph/` or `core/knowledge/graph/` â€” choose one, document why) OR keep single graph with explicit `repo: career_agent | sophron` + `tier` + `workspace_id` on every node. Minimum node types: `file`, `class`, `function`, `doc`, `guardrail`, `ipc_channel`, `dom_selector`, `task_type`, `repo`. Minimum edge types: `IMPLEMENTS`, `ENFORCES`, `READS`, `WRITES`, `CALLS`, `DOCUMENTED_BY`, `CONTRADICTS`, `SCOPED_TO_REPO`.
- **Layer V (local vector index, no cloud):** dependency-light full-text + TF-IDF/cosine index over chunked code + docs (e.g. `knowledge_index/vectors.json` + `chunks.jsonl` + `index_meta.json` with chunk `path:lines`, `repo`, `type`). Prefer stdlib + `scikit-learn` TF-IDF if already available; otherwise stdlib token-overlap + BM25-lite. No `faiss`/`chroma`/`openai-embeddings` without explicit owner approval. Every chunk records source `file:lines` + content hash for staleness detection.
- **Coverage:** every file in Section 1 (both repos). Chunk `.py` by top-level def/class + header; chunk `.md` by `##` section. **Exclude** `profiles/<live>/*`, `__pycache__/`, `.git/`, `*.log`, OS files. **Include** `profiles/default_user/` schema chunks labeled `schema-exemplar`.
- **Maps to generate:** directory-tree map, import/call map (`Appendix B` extended to `CompanySiteApply` + `Sophron/core`), IPC producer/consumer map, guardrailâ†’code map, task-type canonical map, DOM-selectorâ†’user map, docâ†’code coverage map (flags `UNDOCUMENTED`).

**5.2 Dynamic update contract (every edit updates maps/directions):**
- Add ONE rebuild entrypoint (e.g. `scripts/rebuild_knowledge_index.py` + `Sophron/core/rebuild_graph_index.py` or a single wrapper â€” justify choice) that: (a) rescans trees, (b) re-chunks changed files by hash, (c) regenerates `nodes/edges/adjacency` + `vectors/chunks/meta`, (d) verifies `graph_index.json` in sync (counts match), (e) appends `KNOWLEDGE_GRAPH_CHANGELOG.md` entry (date/action/context/decision), (f) fails loudly on missing maps.
- Wire freshness checks: `ProfileContext._verify_documentation_preflight`-style banner or standalone `python scripts/rebuild_knowledge_index.py --check` that exits non-zero when index is stale (hash mismatch, node/edge count drift, undocumented new file). Document the check in `WORKSPACE_RULES.md` (new C-rule) + `SCOPE_OF_EDIT.md` + `Sophron` session-init so every dev session runs it.
- No live-profile polling: rebuild must ignore `profiles/<live>` by default (allowlist only `default_user/` + code/docs). Prove exclusion with a test (e.g. extend `tests/test_parser_doctor.py` pattern or add `tests/test_knowledge_index_isolation.py` asserting zero live-profile strings in index).
- Version the index (`index_meta.json`: `index_version`, `built_at`, `repo_commits`, `file_hashes`) so future AI can tell staleness at a glance. Provide a `QUERY_GUIDE.md` (how future AI loads graph + vector: `GraphMemoryEngine` usage + vector lookup example + `file:line` citation rule).

**5.3 Constraints:**
- No new cloud services, API keys, or binary wheels without owner approval. Keep rebuild <30s on this repo. Keep JSON human-readable (indent 2). Atomic writes (`.tmp` + `os.replace`) + write-guard locking for shared Sophron files. Never embed live PII in nodes/chunks. Keep Sophron vs Career Agent graphs namespaced (`SCOPED_TO_REPO`) to honor two-repo isolation.

---

## 6. Corruption-safety rules (apply to every edit)

- Profiles inviolability (Section 0.2) + zero-hardcoding (no city/company/CTC/model/path/keyword-list literals; `screening_heuristics` via `sh.get()`; `fallback_text_label` via config).
- Append-only: `AI CONTEXT` headers (serial/term/timestamp/issue/changes/rationale/preventative, zero PII) + `SCAR_TISSUE.md` + `current_week_trend.md`; never rewrite history.
- Atomic I/O (`.tmp` + `os.replace`), `guard.safe_write_json` / `safe_append_line` for Sophron shared files, `register/deregister_session` discipline.
- IPC safety: never mix single vs batch files; preserve 90s/120s SLAs; scoped `.sendMsg` + drawer/container isolation; `domcontentloaded` (never `networkidle` on Naukri); no `about:blank` terminal state; no `sys.stdin`/`input()` in `core/` (CLI debug exception stays in `CompanySiteApply/cli.py`).
- Subsystem gating: Company-site apply on-demand/human-reviewed, never daemonized; `honeypot` never filled; platform isolation (Naukri vs LinkedIn) preserved.
- License + privacy: personal proprietary everywhere; redaction tiers per Q11; `.gitignore` respected.
- Diffs-first workflow: implement in small batches (docs â†’ graph â†’ vectors â†’ rebuild hook â†’ tests), show `git diff --stat` + key hunks, run relevant tests (`CompanySiteApply/tests/test_parser_doctor.py`, `Sophron/tests/test_master_agent_suite.py`, purity check, index `--check`), commit only on explicit approval, separate commits per repo.

---

## 7. Deliverables + acceptance

1. **Understanding memo** (Section 2 gates aâ€“f, own diagram + flow narrative).
2. **Claim matrix Q1â€“Q16** with verdict + `file:line` + workaround notes; **rejected-claims list** (not implemented).
3. **Docs diff** for every changed `.md` (version/date bumped, counts/paths corrected, CompanySiteApply + Sophron gaps closed, no live PII added).
4. **Graph + vector build:** new/updated `nodes/edges/graph_index` + `vectors/chunks/meta` + rebuild script(s) + `QUERY_GUIDE.md` + isolation test + `KNOWLEDGE_GRAPH_CHANGELOG.md` entry. Prove: rebuild is idempotent, `--check` detects a planted stale file, live-profile strings absent, future-AI query demo returns `file:line` citations.
5. **Freshness proof:** `verify_codebase_purity()` green, relevant test suites green, `git status/diff` clean per repo except intended files.

> If understanding, matrix, or freshness proof is incomplete â€” stop, report gaps, make no further changes.
