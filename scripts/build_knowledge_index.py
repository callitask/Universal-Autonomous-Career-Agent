#!/usr/bin/env python3
"""
# AI CONTEXT & CHANGE LOG
# Serial: 001 | Term: Phase 3 Dynamic Knowledge Index | Timestamp: 2026-09-21
# Issue: Need lightweight, dependency-free 2-layer Knowledge Graph + Local Vector Index
# Changes:
#   - Layer G: Deterministic JSON graph (nodes, edges, adjacency index) scoped by repo, tier, workspace_id
#   - Layer V: Local BM25/TF-IDF full-text index with chunk-level path:lines, sha256 hash, and metadata
#   - Staleness detection: --check flag exits non-zero on file hash or file count drift
#   - Retrieval demo: --query "<term>" returns ranked file:line citations
#   - Strict privacy: Ignores all profiles/<live>, indexes profiles/default_user as schema-exemplar only
# Preventative: Atomic writes (.tmp + os.replace), <30s execution, zero faiss/chroma/cloud dependencies
#
# Serial: 002 | Term: Dynamic profile exclusion + AST/PageRank upgrade | Timestamp: 2026-09-22
# Issue: LIVE_PROFILE_DENYLIST hardcoded four folder names, violating zero-hardcoding and breaking on new profiles. No grammar-aware structure or importance ranking. Full parse trees would blow LLM memory.
# Changes: Replaced static denylist with dynamic profiles/ scan (allow default_user only). Added stdlib-ast symbol extraction (functions/classes/imports/calls, signatures+docstrings only, never full trees). Added PageRank over call/import graph with BM25 weighting and summaries.json budget entry point. tree-sitter left as optional future, not required.
# Rationale: Dynamic exclusion survives new profiles. AST signatures give grammar awareness at low token cost. PageRank surfaces core engine over scratch. Summaries let new AI load <50KB first, full chunks on demand.
# Preventative: Never hardcode profile folder names. Never store full AST trees. Keep rebuild <30s. Keep stdlib-only unless owner approves new wheels.
"""

import os
import sys
import json
import math
import re
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set

# Ensure Windows stdout prints unicode safely
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Base directory roots (two-repo layout: JOB AI AGENT + sibling Sophron, never nested)
REPO_A_ROOT = Path(__file__).resolve().parent.parent
_ENV_SOPHRON = os.environ.get("SOPHRON_ROOT", "").strip()
if _ENV_SOPHRON:
    REPO_B_ROOT = Path(_ENV_SOPHRON)
elif (REPO_A_ROOT.parent / "Sophron").is_dir():
    REPO_B_ROOT = REPO_A_ROOT.parent / "Sophron"
else:
    REPO_B_ROOT = REPO_A_ROOT / "Sophron"  # legacy fallback (pre-extraction layout)
KNOWLEDGE_DIR = REPO_A_ROOT / "knowledge"
GRAPH_DIR = KNOWLEDGE_DIR / "graph"
VECTORS_DIR = KNOWLEDGE_DIR / "vectors"

LIVE_PROFILE_DENYLIST = frozenset()

def get_live_profile_names() -> Set[str]:
    try:
        profiles_dir = REPO_A_ROOT / "profiles"
        if not profiles_dir.is_dir():
            return set()
        return set(
            p.name for p in profiles_dir.iterdir()
            if p.is_dir() and p.name != "default_user" and not p.name.startswith(".")
        )
    except Exception:
        return set()

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "self", "def", "class", "import", "return", "true", "false", "none"
}

def compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

def tokenize(text: str) -> List[str]:
    clean = re.sub(r'[^a-zA-Z0-9_\.]+', ' ', text.lower())
    tokens = [t.strip('.') for t in clean.split() if len(t.strip('.')) > 1]
    return [t for t in tokens if t not in STOPWORDS]

def is_allowed_path(rel_path: str, repo: str) -> bool:
    norm = rel_path.replace("\\", "/")
    parts = norm.split("/")
    
    # Exclusions
    if any(p in [".git", "__pycache__", ".pytest_cache", ".vscode", "output", "logs", "knowledge"] for p in parts):
        return False
    if norm.endswith(".log") or norm.endswith(".pyc") or norm.endswith(".tmp"):
        return False
    if norm in ["scan_root.json", "scan_sophron.json", "desktop.ini"]:
        return False
    if "scratch" in parts:
        return False

    # Exclude root test harness directory so tests do not invalidate production knowledge index
    if repo == "Repo_A" and parts[0] == "tests":
        return False

    # Privacy gate: exclude live profiles dynamically (allow default_user only)
    if parts[0] == "profiles":
        if len(parts) > 1 and parts[1] != "default_user":
            return False
            
    # File extensions to include
    if not (norm.endswith(".py") or norm.endswith(".md") or norm.endswith(".json")):
        if not norm in ["LICENSE", ".gitignore"]:
            return False

    return True

def scan_repository_files(root: Path, repo_name: str) -> List[Tuple[Path, str]]:
    results = []
    live_names = get_live_profile_names() if repo_name == "Repo_A" else set()
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place (dynamic live-profile exclusion, no hardcoded names)
        pruned = []
        for d in dirnames:
            if d in [".git", "__pycache__", "output", "logs", "scratch", "knowledge"]:
                continue
            if repo_name == "Repo_A" and d in live_names and Path(dirpath).resolve() == (REPO_A_ROOT / "profiles").resolve():
                continue
            pruned.append(d)
        dirnames[:] = pruned
        for f in filenames:
            full_path = Path(dirpath) / f
            try:
                rel_path = full_path.relative_to(root).as_posix()
            except ValueError:
                continue
            if is_allowed_path(rel_path, repo_name):
                results.append((full_path, rel_path))
    return sorted(results, key=lambda x: x[1])

def chunk_markdown(content: str, rel_path: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = content.splitlines()
    current_header = "Header"
    chunk_start = 1
    chunk_lines = []

    for i, line in enumerate(lines, start=1):
        if line.startswith("## ") or line.startswith("# "):
            if chunk_lines:
                text_block = "\n".join(chunk_lines)
                chunks.append({
                    "section": current_header,
                    "start_line": chunk_start,
                    "end_line": i - 1,
                    "content": text_block,
                    "hash": compute_sha256(text_block)
                })
            current_header = line.lstrip("#").strip()
            chunk_start = i
            chunk_lines = [line]
        else:
            chunk_lines.append(line)

    if chunk_lines:
        text_block = "\n".join(chunk_lines)
        chunks.append({
            "section": current_header,
            "start_line": chunk_start,
            "end_line": len(lines),
            "content": text_block,
            "hash": compute_sha256(text_block)
        })

    return chunks

def chunk_python(content: str, rel_path: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = content.splitlines()
    chunk_start = 1
    current_symbol = "Module Header"
    chunk_lines = []

    for i, line in enumerate(lines, start=1):
        # Chunk on top-level classes and functions
        if re.match(r'^(class\s+[A-Za-z0-9_]+|def\s+[A-Za-z0-9_]+)', line):
            if chunk_lines:
                text_block = "\n".join(chunk_lines)
                chunks.append({
                    "section": current_symbol,
                    "start_line": chunk_start,
                    "end_line": i - 1,
                    "content": text_block,
                    "hash": compute_sha256(text_block)
                })
            match = re.match(r'^(class|def)\s+([A-Za-z0-9_]+)', line)
            current_symbol = f"{match.group(1)} {match.group(2)}" if match else line.strip()
            chunk_start = i
            chunk_lines = [line]
        else:
            chunk_lines.append(line)

    if chunk_lines:
        text_block = "\n".join(chunk_lines)
        chunks.append({
            "section": current_symbol,
            "start_line": chunk_start,
            "end_line": len(lines),
            "content": text_block,
            "hash": compute_sha256(text_block)
        })

    return chunks

def determine_tier(rel_path: str, repo: str) -> str:
    p = rel_path.replace("\\", "/")
    if p.startswith("core/"):
        return "core_engine"
    if p.startswith("CompanySiteApply/"):
        return "company_site_apply"
    if p.startswith("docs/"):
        return "documentation"
    if p.startswith(".agents/"):
        return "agent_rules"
    if p.startswith("profiles/default_user/"):
        return "schema_exemplar"
    if p.startswith("scripts/"):
        return "scripts"
    if repo == "Repo_B":
        if p.startswith("core/"):
            return "sophron_core"
        if p.startswith("graph_memory/"):
            return "sophron_graph"
        if p.startswith("meta_cognition/"):
            return "sophron_meta_cognition"
        if p.startswith("workspaces/"):
            return "sophron_workspaces"
        if p.startswith("interaction_history/"):
            return "sophron_history"
        return "sophron_meta"
    return "root"

def determine_domain(rel_path: str, repo: str, tier: str) -> str:
    p = rel_path.replace("\\", "/")
    if repo == "Repo_B":
        if tier in ("sophron_history", "sophron_meta", "sophron_meta_cognition", "sophron_workspaces"):
            return "personal_intelligence"
        if "understanding_master/" in p or "interaction_history/" in p:
            return "personal_intelligence"
        return "agent_structure"
    if tier == "schema_exemplar":
        return "agent_structure"
    return "agent_structure"

def extract_ast_symbols(content: str) -> Dict[str, Any]:
    try:
        import ast as _ast
        tree = _ast.parse(content)
    except Exception:
        return {"functions": [], "classes": [], "imports": [], "calls": [], "summaries": []}
    functions, classes, imports, calls, summaries = [], [], [], [], []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.FunctionDef):
            args = [a.arg for a in node.args.args][:6]
            doc = (_ast.get_docstring(node) or "").splitlines()
            first = doc[0].strip()[:140] if doc else ""
            functions.append({"name": node.name, "line": node.lineno, "args": args, "summary": first})
            summaries.append(f"def {node.name}({', '.join(args)}): {first}".strip())
        elif isinstance(node, _ast.ClassDef):
            doc = (_ast.get_docstring(node) or "").splitlines()
            first = doc[0].strip()[:140] if doc else ""
            classes.append({"name": node.name, "line": node.lineno, "summary": first})
            summaries.append(f"class {node.name}: {first}".strip())
        elif isinstance(node, _ast.Import):
            for a in node.names:
                imports.append(a.name.split(".")[0])
        elif isinstance(node, _ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
        elif isinstance(node, _ast.Call):
            f = node.func
            if isinstance(f, _ast.Name):
                calls.append(f.id)
            elif isinstance(f, _ast.Attribute):
                calls.append(f.attr)
    return {"functions": functions, "classes": classes, "imports": imports, "calls": calls, "summaries": summaries[:12]}

def compute_pagerank(adjacency: Dict[str, List[Dict[str, str]]], damping: float = 0.85, iterations: int = 20) -> Dict[str, float]:
    nodes = list(adjacency.keys())
    for edges in adjacency.values():
        for e in edges:
            t = e.get("target")
            if t and t not in adjacency:
                nodes.append(t)
    nodes = sorted(set(nodes))
    n = len(nodes)
    if n == 0:
        return {}
    rank = {x: 1.0 / n for x in nodes}
    outdeg = {x: max(1, len(adjacency.get(x, []))) for x in nodes}
    incoming: Dict[str, List[str]] = {x: [] for x in nodes}
    for s, edges in adjacency.items():
        for e in edges:
            t = e.get("target")
            if t in incoming:
                incoming[t].append(s)
    for _ in range(iterations):
        new_rank = {}
        for x in nodes:
            s = sum(rank[src] / outdeg[src] for src in incoming[x])
            new_rank[x] = (1 - damping) / n + damping * s
        rank = new_rank
    return rank

def atomic_write_json(target_path: Path, data: Any):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, target_path)

class KnowledgeIndexBuilder:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.adjacency = {}
        self.chunks = []
        self.file_hashes = {}
        self.doc_frequencies = {}
        self.total_chunks = 0
        self.summaries = []
        self.pagerank = {}

    def add_node(self, node_id: str, node_type: str, label: str, repo: str, tier: str, properties: Dict[str, Any], domain: str = ""):
        node = {
            "id": node_id,
            "type": node_type,
            "label": label,
            "repo": repo,
            "tier": tier,
            "domain": domain or ("personal_intelligence" if tier in ("sophron_history", "sophron_meta", "sophron_meta_cognition", "sophron_workspaces") else "agent_structure"),
            "workspace_id": "job_ai_agent" if repo == "Repo_A" else "sophron",
            "properties": properties
        }
        self.nodes.append(node)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, source: str, target: str, relation: str, properties: Dict[str, Any] = None):
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "properties": properties or {}
        }
        self.edges.append(edge)
        if source not in self.adjacency:
            self.adjacency[source] = []
        self.adjacency[source].append({"target": target, "relation": relation})

    def build_all(self):
        print("[KnowledgeIndex] Scanning Repo A and Repo B (Sophron)...")
        repo_a_files = scan_repository_files(REPO_A_ROOT, "Repo_A")
        # Exclude Sophron from Repo A scan if walk visited it
        repo_a_files = [(p, r) for p, r in repo_a_files if not r.startswith("Sophron/")]
        repo_b_files = scan_repository_files(REPO_B_ROOT, "Repo_B")

        all_entries = [(p, r, "Repo_A") for p, r in repo_a_files] + [(p, r, "Repo_B") for p, r in repo_b_files]
        print(f"[KnowledgeIndex] Found {len(all_entries)} eligible source files.")

        chunk_id_seq = 0
        for full_path, rel_path, repo in all_entries:
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"[Warn] Could not read {full_path}: {e}")
                continue

            file_hash = compute_sha256(content)
            key = f"{repo}:{rel_path}"
            self.file_hashes[key] = {
                "hash": file_hash,
                "lines": len(content.splitlines()),
                "bytes": len(content.encode("utf-8"))
            }

            tier = determine_tier(rel_path, repo)
            domain = determine_domain(rel_path, repo, tier)
            file_node_id = f"file::{repo}::{rel_path}"
            self.add_node(
                node_id=file_node_id,
                node_type="file",
                label=rel_path,
                repo=repo,
                tier=tier,
                domain=domain,
                properties={
                    "path": rel_path,
                    "lines": len(content.splitlines()),
                    "sha256": file_hash
                }
            )

            # Grammar-aware AST pass (stdlib only, signatures + docstrings, never full trees)
            if rel_path.endswith(".py"):
                try:
                    symbols = extract_ast_symbols(content)
                    for fn in symbols["functions"][:40]:
                        fid = f"func::{repo}::{rel_path}::{fn['name']}"
                        self.add_node(fid, "function", fn["name"], repo, tier, {"path": rel_path, "line": fn["line"], "summary": fn["summary"]})
                        self.add_edge(file_node_id, fid, "DEFINES")
                    for cl in symbols["classes"][:20]:
                        cid = f"class::{repo}::{rel_path}::{cl['name']}"
                        self.add_node(cid, "class", cl["name"], repo, tier, {"path": rel_path, "line": cl["line"], "summary": cl["summary"]})
                        self.add_edge(file_node_id, cid, "DEFINES")
                    for imp in sorted(set(symbols["imports"]))[:20]:
                        self.add_edge(file_node_id, f"import::{imp}", "IMPORTS")
                    for call in sorted(set(symbols["calls"]))[:30]:
                        self.add_edge(file_node_id, f"symbol::{call}", "CALLS")
                    if symbols["summaries"]:
                        self.summaries.append({"path": rel_path, "repo": repo, "tier": tier, "domain": domain, "lines": f"1:{len(content.splitlines())}", "summary": "; ".join(symbols["summaries"][:6])[:500]})
                except Exception:
                    pass

            # Chunk file for Layer V
            if rel_path.endswith(".py"):
                file_chunks = chunk_python(content, rel_path)
            elif rel_path.endswith(".md"):
                file_chunks = chunk_markdown(content, rel_path)
            else:
                text_block = content
                file_chunks = [{
                    "section": "Document",
                    "start_line": 1,
                    "end_line": len(content.splitlines()) or 1,
                    "content": text_block,
                    "hash": compute_sha256(text_block)
                }]

            for c in file_chunks:
                chunk_id = f"chunk_{chunk_id_seq:05d}"
                chunk_id_seq += 1
                tokens = tokenize(c["content"])
                
                # Update doc frequencies for BM25
                unique_tokens = set(tokens)
                for ut in unique_tokens:
                    self.doc_frequencies[ut] = self.doc_frequencies.get(ut, 0) + 1

                chunk_entry = {
                    "id": chunk_id,
                    "repo": repo,
                    "tier": tier,
                    "domain": domain,
                    "path": rel_path,
                    "lines": f"{c['start_line']}:{c['end_line']}",
                    "section": c["section"],
                    "sha256": c["hash"],
                    "tokens_count": len(tokens),
                    "text": c["content"]
                }
                self.chunks.append(chunk_entry)

                # Link chunk to file in graph
                chunk_node_id = f"chunk::{repo}::{chunk_id}"
                self.add_node(
                    node_id=chunk_node_id,
                    node_type="chunk",
                    label=f"{rel_path}:{c['start_line']}-{c['end_line']}",
                    repo=repo,
                    tier=tier,
                    domain=domain,
                    properties={
                        "path": rel_path,
                        "section": c["section"],
                        "lines": f"{c['start_line']}:{c['end_line']}"
                    }
                )
                self.add_edge(file_node_id, chunk_node_id, "CONTAINS_CHUNK")

        self.total_chunks = len(self.chunks)

        # Build Domain Architecture Edges (Guardrails, IPC Channels, Systems)
        self._build_architectural_graph()

        print(f"[KnowledgeIndex] Indexed {len(self.nodes)} nodes, {len(self.edges)} edges, {self.total_chunks} chunks.")
        self._save_indices()

    def _build_architectural_graph(self):
        # Register Core Architectural Entities
        entities = [
            ("guardrail::P1", "guardrail", "Guardrail P1 (Codebase Purity)", "Repo_A", "core_engine"),
            ("guardrail::C6", "guardrail", "Guardrail C6 (Negative Gating)", "Repo_A", "core_engine"),
            ("guardrail::C24", "guardrail", "Guardrail C24 (Card Exp Band Gate)", "Repo_A", "core_engine"),
            ("guardrail::C32", "guardrail", "Guardrail C32 (Two-Stage Nav Recovery)", "Repo_A", "core_engine"),
            ("guardrail::C34", "guardrail", "Guardrail C34 (Radio Chip Option Fallback)", "Repo_A", "core_engine"),
            ("ipc_channel::single", "ipc_channel", "pending_question.json", "Repo_A", "ipc"),
            ("ipc_channel::batch", "ipc_channel", "batch_question.json", "Repo_A", "ipc"),
            ("system::discovery", "system", "04_job_discovery.py", "Repo_A", "core_engine"),
            ("system::application", "system", "05_apply_jobs.py", "Repo_A", "core_engine"),
            ("system::ai_client", "system", "ai_client.py", "Repo_A", "core_engine"),
            ("system::ipc_watcher", "system", "ipc_watcher.py", "Repo_A", "core_engine"),
            ("system::company_site_apply", "system", "CompanySiteApply", "Repo_A", "company_site_apply"),
            ("system::sophron_memory", "system", "Sophron Cognitive Memory", "Repo_B", "sophron_core")
        ]
        for eid, etype, elabel, erepo, etier in entities:
            self.add_node(eid, etype, elabel, erepo, etier, {})

        # Connect files to architectural entities
        file_mappings = [
            ("file::Repo_A::core/04_job_discovery.py", "system::discovery", "IMPLEMENTS"),
            ("file::Repo_A::core/04_job_discovery.py", "guardrail::C24", "ENFORCES"),
            ("file::Repo_A::core/04_job_discovery.py", "ipc_channel::batch", "WRITES"),
            ("file::Repo_A::core/05_apply_jobs.py", "system::application", "IMPLEMENTS"),
            ("file::Repo_A::core/05_apply_jobs.py", "guardrail::C32", "ENFORCES"),
            ("file::Repo_A::core/05_apply_jobs.py", "guardrail::C34", "ENFORCES"),
            ("file::Repo_A::core/05_apply_jobs.py", "ipc_channel::single", "WRITES"),
            ("file::Repo_A::core/ai_client.py", "system::ai_client", "IMPLEMENTS"),
            ("file::Repo_A::core/ai_client.py", "guardrail::C6", "ENFORCES"),
            ("file::Repo_A::core/ai_client.py", "ipc_channel::single", "READS"),
            ("file::Repo_A::core/ai_client.py", "ipc_channel::batch", "READS"),
            ("file::Repo_A::core/ipc_watcher.py", "system::ipc_watcher", "IMPLEMENTS"),
            ("file::Repo_A::core/ipc_watcher.py", "ipc_channel::single", "READS"),
            ("file::Repo_A::core/ipc_watcher.py", "ipc_channel::batch", "READS"),
            ("file::Repo_A::core/utils/profile_context.py", "guardrail::P1", "ENFORCES"),
            ("file::Repo_B::core/graph_memory_engine.py", "system::sophron_memory", "IMPLEMENTS")
        ]
        for src, tgt, rel in file_mappings:
            if any(n["id"] == src for n in self.nodes):
                self.add_edge(src, tgt, rel)

    def _save_indices(self):
        # PageRank over call/import graph for LLM ranking (core > scratch without loading trees)
        try:
            self.pagerank = compute_pagerank(self.adjacency)
        except Exception:
            self.pagerank = {}
        # 1. Save Graph
        atomic_write_json(GRAPH_DIR / "nodes.json", self.nodes)
        atomic_write_json(GRAPH_DIR / "edges.json", self.edges)
        atomic_write_json(GRAPH_DIR / "graph_index.json", self.adjacency)
        atomic_write_json(GRAPH_DIR / "pagerank.json", self.pagerank)
        atomic_write_json(GRAPH_DIR / "summaries.json", self.summaries)

        # 2. Save Vectors & IDF dictionary
        idf = {}
        for word, count in self.doc_frequencies.items():
            # BM25 IDF: ln((N - n + 0.5) / (n + 0.5) + 1)
            idf[word] = round(math.log(1 + (self.total_chunks - count + 0.5) / (count + 0.5)), 4)

        atomic_write_json(VECTORS_DIR / "chunks.json", self.chunks)
        atomic_write_json(VECTORS_DIR / "idf.json", idf)

        # 3. Save Metadata for staleness detection
        from collections import Counter as _Counter
        domain_counts = dict(_Counter(c.get("domain", "agent_structure") for c in self.chunks))
        meta = {
            "index_version": "2.2.0",
            "generator": "build_knowledge_index.py",
            "total_files": len(self.file_hashes),
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_chunks": self.total_chunks,
            "total_summaries": len(self.summaries),
            "domain_counts": domain_counts,
            "sophron_root": str(REPO_B_ROOT),
            "vocab_size": len(idf),
            "file_hashes": self.file_hashes
        }
        atomic_write_json(VECTORS_DIR / "index_meta.json", meta)
        print("[KnowledgeIndex] Successfully wrote graph and vector indices to knowledge/ directory.")

    def check_staleness(self) -> Tuple[bool, List[str]]:
        meta_file = VECTORS_DIR / "index_meta.json"
        if not meta_file.exists():
            return False, ["index_meta.json does not exist. Rebuild required."]

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        stored_hashes = meta.get("file_hashes", {})
        issues = []

        # Current files on disk
        repo_a_files = scan_repository_files(REPO_A_ROOT, "Repo_A")
        repo_a_files = [(p, r) for p, r in repo_a_files if not r.startswith("Sophron/")]
        repo_b_files = scan_repository_files(REPO_B_ROOT, "Repo_B")
        all_disk_entries = [(p, r, "Repo_A") for p, r in repo_a_files] + [(p, r, "Repo_B") for p, r in repo_b_files]
        current_keys = set()

        for full_path, rel_path, repo in all_disk_entries:
            key = f"{repo}:{rel_path}"
            current_keys.add(key)
            if key not in stored_hashes:
                issues.append(f"Unindexed new file on disk: {key}")
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    curr_hash = compute_sha256(f.read())
            except Exception as e:
                issues.append(f"Cannot read file {full_path}: {e}")
                continue

            if curr_hash != stored_hashes[key]["hash"]:
                issues.append(f"File content modified (hash mismatch): {key}")

        for stored_key in stored_hashes:
            if stored_key not in current_keys:
                issues.append(f"File deleted or moved from disk: {stored_key}")

        is_fresh = len(issues) == 0
        return is_fresh, issues

    def query(self, query_str: str, top_k: int = 5, domain: str = "all") -> List[Dict[str, Any]]:
        chunks_file = VECTORS_DIR / "chunks.json"
        idf_file = VECTORS_DIR / "idf.json"
        pagerank_file = GRAPH_DIR / "pagerank.json"

        if not chunks_file.exists() or not idf_file.exists():
            print("[Error] Index files missing. Run with --build first.")
            return []

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        with open(idf_file, "r", encoding="utf-8") as f:
            idf_dict = json.load(f)
        try:
            pagerank = json.load(open(pagerank_file, "r", encoding="utf-8")) if pagerank_file.exists() else {}
        except Exception:
            pagerank = {}

        q_tokens = tokenize(query_str)
        if not q_tokens:
            return []

        # BM25-lite parameters
        k1 = 1.5
        b = 0.75
        total_len = sum(c.get("tokens_count", 1) for c in chunks)
        avg_len = total_len / max(1, len(chunks))

        scored = []
        for c in chunks:
            if domain != "all" and c.get("domain", "agent_structure") != domain:
                continue
            text = c["text"]
            chunk_tokens = tokenize(text)
            doc_len = len(chunk_tokens)
            if doc_len == 0:
                continue

            token_freqs = {}
            for t in chunk_tokens:
                token_freqs[t] = token_freqs.get(t, 0) + 1

            score = 0.0
            for qt in q_tokens:
                if qt in token_freqs:
                    freq = token_freqs[qt]
                    term_idf = idf_dict.get(qt, 1.0)
                    numerator = freq * (k1 + 1)
                    denominator = freq + k1 * (1 - b + b * (doc_len / avg_len))
                    score += term_idf * (numerator / denominator)

            if score > 0.0:
                file_key = f"file::{c['repo']}::{c['path']}"
                pr = float(pagerank.get(file_key, 0.0)) if pagerank else 0.0
                pr_boost = 0.6 + 0.4 * min(1.0, pr * 50.0) if pr > 0 else 1.0
                tier_boost = {"core_engine": 1.3, "company_site_apply": 1.2, "scripts": 1.15, "sophron_core": 1.2, "documentation": 1.0, "agent_rules": 1.05, "schema_exemplar": 1.0}.get(c.get("tier", ""), 1.0)
                weighted = round(score * pr_boost * tier_boost, 3)
                scored.append({
                    "score": weighted,
                    "base_score": round(score, 3),
                    "pagerank": round(pr, 6),
                    "repo": c["repo"],
                    "tier": c["tier"],
                    "domain": c.get("domain", "agent_structure"),
                    "path": c["path"],
                    "lines": c["lines"],
                    "section": c["section"],
                    "snippet": text.strip().splitlines()[0][:120] if text else ""
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

def main():
    parser = argparse.ArgumentParser(description="Universal Autonomous Career Agent - Knowledge Index & Staleness Checker")
    parser.add_argument("--build", action="store_true", help="Build graph and vector index from scratch")
    parser.add_argument("--check", action="store_true", help="Verify index freshness and check for drift/staleness")
    parser.add_argument("--query", type=str, help="Search the local vector index using full-text BM25 ranking")
    parser.add_argument("--top", type=int, default=5, help="Number of query results to return")
    parser.add_argument("--domain", type=str, default="all", choices=["all", "agent_structure", "personal_intelligence"], help="Filter retrieval by knowledge domain")

    args = parser.parse_args()
    builder = KnowledgeIndexBuilder()

    if args.check:
        print("[KnowledgeIndex] Checking index freshness...")
        is_fresh, issues = builder.check_staleness()
        if is_fresh:
            print("[KnowledgeIndex] PASS: Index is 100% fresh and synchronized with disk.")
            sys.exit(0)
        else:
            print(f"[KnowledgeIndex] FAIL: Stale index detected ({len(issues)} issues):")
            for iss in issues[:15]:
                print(f"  - {iss}")
            if len(issues) > 15:
                print(f"  ... and {len(issues) - 15} more.")
            print("[KnowledgeIndex] Run `python scripts/build_knowledge_index.py --build` to update.")
            sys.exit(1)

    elif args.query:
        print(f"[KnowledgeIndex] Querying index for: '{args.query}'")
        results = builder.query(args.query, top_k=args.top, domain=args.domain)
        if not results:
            print("[KnowledgeIndex] No matching chunks found.")
        else:
            print(f"[KnowledgeIndex] Top {len(results)} matches:")
            for i, r in enumerate(results, start=1):
                print(f"{i}. [{r['score']}] {r['repo']}|{r.get('domain','agent_structure')} | {r['path']}:{r['lines']} ({r['section']})")
                print(f"   Snippet: {r['snippet']}...")
        sys.exit(0)

    else:
        # Default action is to build
        print("[KnowledgeIndex] Building knowledge graph and vector index...")
        builder.build_all()
        print("[KnowledgeIndex] Verification check following build:")
        fresh, _ = builder.check_staleness()
        print(f"[KnowledgeIndex] Index status: {'FRESH' if fresh else 'UNSYNCHRONIZED'}")

if __name__ == "__main__":
    main()
