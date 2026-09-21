# KNOWLEDGE GRAPH & VECTOR DATABASE LOG

> **Purpose:** To log every structural or semantic change made to the Vector Database and Knowledge Graph representations used by the Universal Autonomous Career Agent. This ensures future AIs can trace the evolution of the embedded memory, understand *why* architectural components are linked, and safely update the graph structure without repetition.

## Initial Setup (2026-09-20)
* **Action:** Standardized the Knowledge Graph / Vector Memory references.
* **Context:** The system utilizes `Sophron` (the Master Agent cognitive graph) situated in `F:\JOB AI AGENT\Sophron`. It contains the distributed semantic graph memory across `nodes.json`, `edges.json`, and `graph_index.json`. *(Historical note 2026-09-22: nested path retired — Sophron extracted to sibling `F:\Sophron` preserving history; see Phase 6 below. Original entry preserved.)*
* **Decision:** We are formalizing this structure so that every future AI agent loading into the workspace immediately reads this changelog and understands that to update long-term knowledge, it must interact with the `Sophron` semantic graph memory.
* **How it works:** 
  1. Core architectural concepts, rules, and deprecated systems are modeled as Nodes.
  2. The relationships between scripts, IPC daemons, and rules are modeled as Edges.
  3. When future AIs generate new architectural insights, they must update the `Sophron` graph files to ensure the learning is persisted.

## Required Process for Future Graph Updates
Whenever a new system is built, a bug is caught, or an architecture is modified, the AI Developer must:
1. Update `KNOWLEDGE_GRAPH_CHANGELOG.md` with the date, action, context, and decision.
2. Update the corresponding `nodes.json` and `edges.json` in `Sophron/graph_memory`.
3. Update `DEPRECATED_SYSTEMS_CHANGELOG.md` if an old feature was replaced.

## Phase 2 Documentation Remediation & Synchronization (2026-09-21)
* **Action:** Comprehensive cross-repository documentation remediation and empirical alignment.
* **Context:** Verification audit identified discrepancies in license grants (MIT remnant in README), guardrail counts (stale 18 vs 43 in code), duplicate DIRECTIVE 8 headings, stale URL slug patterns, and missing subsystem contracts (`CompanySiteApply/nails`, `CompanyScraper`, `inspections`).
* **Changes Applied:**
  1. **License Alignment (Q1):** Replaced public MIT reference with explicit proprietary closed-source notice in `README.md` and `UNIVERSAL_AGENT_SETUP.md`.
  2. **Guardrail Counts & Heading Integrity (Q2, Q14):** Corrected guardrail count in `README.md` and `WORKSPACE_RULES.md` to 43 (33 C, 6 H, 3 D, 1 P); re-sequenced duplicate `## DIRECTIVE 8` (Tooling Guide) to `## DIRECTIVE 9`.
  3. **Dual-Channel IPC Architecture (Q4):** Added Section 13 to `PLATFORM_KNOWLEDGE.md` and updated `ARCHITECTURE_REFERENCE.md` detailing dual-channel file IPC (`batch_question.json` 120s timeout and `pending_question.json` 90s SLA) and shared 2.0s polling in Daemon 2 (`ipc_watcher.py`).
  4. **Subsystem Documentation (Q8, Q9):** Expanded `CompanySiteApply/README.md` and root `README.md` with complete contracts for Fingers, Nails (`jpmc_nail`, `bristlecone_nail`), `CompanyScraper`, `ParserDoctor`, and `DOMHelpers`.
  5. **Tier C Classification:** Created `CompanySiteApply/inspections/README.md` cataloging 11 DOM snapshot captures as Tier C non-executable reference samples.
  6. **Deployment Guide & Prompts (Q12, Q13):** Updated `REFERENCE_DEPLOYMENT_GUIDE.md` and `UNIVERSAL_AGENT_SETUP.md` with Batch v2.0, `SearchStateManager`, and 3-daemon execution; added pre-Batch warning to `UNIVERSAL_AGENT_PROMPT_v2.md`; synchronized `.agents/README.md` with code `--delay 30` and shared 2.0s poll.
  7. **Profiles Hygiene (Q13a):** Scrubbed live profile references from `profiles/README.md`, referencing `default_user/` as the sole schema exemplar.

## Phase 3 Dynamic Knowledge Graph & Local Vector Index Build (2026-09-21)
* **Action:** Implemented two-layer dynamic retrieval architecture (Layer G + Layer V) spanning Repo A and Repo B.
* **Context:** Replaced purely static and descriptive claims with an empirical, executable, dependency-free retrieval engine without external cloud or vector database dependencies.
* **Artifacts & Implementations:**
  1. **Builder Script (`scripts/build_knowledge_index.py`):**
     - Walks both Repo A (`JOB AI AGENT`) and Repo B (`Sophron`).
     - Excludes `.git`, `__pycache__`, `output`, `logs`, `scratch`, and all dynamic live profiles (`profiles/<live_profile>/`).
     - Indexes `profiles/default_user/` strictly as `schema_exemplar`.
     - Chunks Python files by top-level class/def and Markdown by `##` section headings.
  2. **Layer G (Deterministic Knowledge Graph):**
     - Generated `knowledge/graph/nodes.json`, `knowledge/graph/edges.json`, and `knowledge/graph/graph_index.json`.
     - Models explicit `repo`, `tier`, `workspace_id`, and relationships (`IMPLEMENTS`, `ENFORCES`, `READS`, `WRITES`, `CONTAINS_CHUNK`).
  3. **Layer V (Local BM25-Lite Vector Index):**
     - Generated `knowledge/vectors/chunks.json`, `knowledge/vectors/idf.json`, and `knowledge/vectors/index_meta.json`.
     - Provides BM25 ranking across all code and documentation chunks with exact `path:lines` citation and SHA-256 hashes.
  4. **Staleness Detection (`--check`):**
     - Compares live file hashes on disk against `index_meta.json`. Exits with code 0 on clean/fresh index and non-zero on file drift or missing files.
  5. **Verification & Testing (`tests/test_knowledge_index.py`):**
     - 6 comprehensive tests asserting index file existence, zero live-profile leakage, presence of `default_user` schema exemplar, freshness idempotency, planted staleness detection, and BM25 search retrieval.
  6. **Documentation (`docs/QUERY_GUIDE.md`):**
     - Comprehensive guide explaining Layer G graph traversal, Layer V BM25 querying, programmatic imports, and AI agent citation rules.

## Phase 4 Post-Audit Cleanup (2026-09-21)
* **Action:** Confirmed deletion of legacy file `audit command prompt.md`.
* **Context:** The file was identified as a deleted legacy artifact during Phase 1 baseline. Owner approved the permanent deletion, removing it from all working tracking mechanisms.

## Phase 6 Sophron Extraction + Domain-Split Knowledge (2026-09-22)
* **Action:** Extracted Sophron from nested `F:\JOB AI AGENT\Sophron` to sibling `F:\Sophron` preserving `.git` history and `callitask/Sophron.git` remote. Root `.gitignore` Sophron block retired. Rewrote cross-references to `F:\Sophron` + `SOPHRON_ROOT` env. Split knowledge by `domain`: `agent_structure` (agent code/docs, dev-updated, intelligence-free) vs `personal_intelligence` (every AI session, model-agnostic with `agent_model` + `software`). Index v2.2.0 adds AST signatures, PageRank + tier boost, `summaries.json`, `--domain` filter, dynamic profile exclusion.
* **Context:** Sophron is general human+AI intelligence (Jarvis-like, trains across Antigravity/Muse/Claude), not a JOB AI AGENT subfolder. JobAgent keeps its own separate agent-structure index. No mixing.
* **Decision:** Two repos, two commits, zero cross-imports. `core/*.py` has zero Sophron imports (verified). JobAgent `--domain agent_structure` for dev; Sophron `--domain personal_intelligence` for learning.

## Phase 5 Index v2.1 Grammar + Rank + Dynamic Exclusion (2026-09-22)
* **Action:** Replaced hardcoded profile denylist with dynamic `profiles/` scan (allow `default_user` only). Added stdlib-AST symbol extraction (functions/classes/imports/calls, signatures + first docstring line, never full trees), PageRank over call/import graph with tier-boosted BM25, and `summaries.json` budget entry point. Bumped `index_version` to `2.1.0`.
* **Context:** Static denylist broke on new profiles and violated zero-hardcoding. Word-only BM25 surfaced docs over code. Full trees would blow LLM memory.
* **Decision:** Dynamic exclusion + grammar signatures + `score*PageRank*tier` ranking. tree-sitter optional future, not required. Stdlib-only, atomic writes, rebuild <30s. Tests extended to 9 (pagerank/summaries, dynamic exclusion, tier-boost).
