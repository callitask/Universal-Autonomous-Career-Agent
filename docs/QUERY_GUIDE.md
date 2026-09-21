# Dynamic Knowledge & Vector Retrieval Guide
> **Document Version:** 1.0.0
> **Last Updated:** 2026-09-21
> **Classification:** Personal Proprietary — Universal Autonomous Career Agent & Sophron Memory System

---

## 1. Overview & Architecture

The codebase incorporates a dependency-free, two-layer dynamic knowledge retrieval architecture spanning both **Repo A** (`JOB AI AGENT`) and **Repo B** (`Sophron`):

1. **Layer G (Deterministic Knowledge Graph)**:
   - **Location**: `knowledge/graph/nodes.json`, `knowledge/graph/edges.json`, `knowledge/graph/graph_index.json`
   - **Purpose**: Provides structured entity and relationship traversal across systems, guardrails, files, functions, and IPC channels.
   - **Scoping**: Explicit `repo` (`Repo_A` or `Repo_B`), `tier` (`core_engine`, `company_site_apply`, `documentation`, `agent_rules`, `schema_exemplar`, etc.), and `workspace_id`.
   - **Supported Relations**: `IMPLEMENTS`, `ENFORCES`, `READS`, `WRITES`, `CALLS`, `CONTAINS_CHUNK`, `DOCUMENTED_BY`.

2. **Layer V (Local BM25-Lite Vector Index)**:
   - **Location**: `knowledge/vectors/chunks.json`, `knowledge/vectors/idf.json`, `knowledge/vectors/index_meta.json`
   - **Purpose**: Sub-second full-text BM25 ranking across code blocks (top-level classes and functions) and documentation sections (`##` headings).
   - **Metadata & Citations**: Every chunk records exact `path`, `lines` (`start:end`), section header, and content SHA-256 hash.

---

## 2. CLI Usage

All index inspection, verification, and querying is executed via `scripts/build_knowledge_index.py`. Sophron lives at `F:\Sophron` (sibling repo); override with `SOPHRON_ROOT` env var. Never index nested `Sophron/` (retired layout).

### 2.0 Domain-split retrieval (`agent_structure` vs `personal_intelligence`)
```powershell
python scripts/build_knowledge_index.py --query "batch_question IPC" --top 3 --domain agent_structure
python scripts/build_knowledge_index.py --query "user prefers direct tone" --top 3 --domain personal_intelligence
```
- `agent_structure`: agent code/docs, updated on agent dev, free from personal intelligence. JobAgent runs use this.
- `personal_intelligence`: human + AI session learning (any model — Antigravity, Muse, Claude — logged with `agent_model` + `software`), updated every AI session. Sophron runs use this.

### 2.1 Searching the Index (`--query`)
To find relevant code and doc blocks with exact `file:line` citations:
```powershell
python scripts/build_knowledge_index.py --query "batch_question IPC" --top 3
```
Example Output:
```text
[KnowledgeIndex] Querying index for: 'batch_question IPC'
[KnowledgeIndex] Top 3 matches:
1. [6.656] Repo_A | docs/QUERY_GUIDE.md:25:62 (2. CLI Usage)
   Snippet: ## 2. CLI Usage...
2. [4.917] Repo_A | docs/ADVANCED_AGENT_VERIFICATION_AND_REMEDIATION_PROMPT.md:71:85 (2. Understanding gates)
   Snippet: ## 2. Understanding gates (no edits until all pass)...
3. [3.224] Repo_A | core/ipc_watcher.py:146:240 (def run)
   Snippet: def run(profile_dir: str, poll: float = 2.0):...
```

### 2.2 Checking Freshness & Staleness (`--check`)
To verify that the working tree on disk matches the stored SHA-256 file hashes and that no unindexed files exist:
```powershell
python scripts/build_knowledge_index.py --check
```
- **Exit Code `0`**: Index is 100% fresh and synchronized.
- **Exit Code `1`**: Staleness or drift detected (outputs exact offending files).

### 2.3 Rebuilding the Index (`--build`)
To rescan both repositories, re-chunk, re-compute BM25 IDF weights, and atomically update the index:
```powershell
python scripts/build_knowledge_index.py --build
```
Execution takes < 3.0 seconds across 280+ files and 900+ graph nodes.

---

## 3. Programmatic Usage in Agent Memory

### 3.1 Loading and Traversing Layer G (Graph)
```python
import json
from pathlib import Path

knowledge_dir = Path("knowledge/graph")
with open(knowledge_dir / "graph_index.json", "r", encoding="utf-8") as f:
    adjacency = json.load(f)

# Find all entities connected to core/04_job_discovery.py
connected = adjacency.get("file::Repo_A::core/04_job_discovery.py", [])
for edge in connected:
    print(f"-> [{edge['relation']}] {edge['target']}")
```

### 3.2 Querying Layer V (Vectors) via Python
```python
from scripts.build_knowledge_index import KnowledgeIndexBuilder

builder = KnowledgeIndexBuilder()
results = builder.query("SearchStateManager active cycle", top_k=3)
for hit in results:
    print(f"{hit['path']}:{hit['lines']} (Score: {hit['score']})")
```

---

## 4. Citation Rules for AI Agents

Whenever an AI agent answers an architectural question or implements a code modification:
1. **Mandatory File:Line Grounding**: Agents must cite exact `file:line` locations returned by Layer V or validated in source code.
2. **Never Rely on Docstrings Alone**: Always trace active execution routines (`run()`, `evaluate()`) to verify runtime intervals and configurations.
3. **Strict Profile Isolation**: Never cite, query, or index dynamic profiles (`profiles/<live_profile>/`). Only `profiles/default_user/` may be referenced as the schema exemplar.

---

## 5. Maintenance & CI Integration

- Any addition of a `.py`, `.md`, or `.json` file to `core/`, `CompanySiteApply/`, `docs/`, `.agents/`, or `Sophron/` must be followed by `python scripts/build_knowledge_index.py --build`.
- Run `python -m unittest tests/test_knowledge_index.py` to assert privacy isolation, schema integrity, and freshness idempotency.
- Operational auto-update: run `--check` in pre-flight before coding sessions and after every edit batch. `--build` is incremental by hash (only changed files re-chunked) and idempotent. New `profiles/<name>/` folders are auto-excluded (only `default_user` indexed). `summaries.json` is the <50KB budget entry point for new AI; full chunks load on demand with `file:line` citations. PageRank + tier boost keeps `core_engine` above generic docs without loading parse trees.
