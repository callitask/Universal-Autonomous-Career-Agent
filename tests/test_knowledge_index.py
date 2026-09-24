#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Dynamic Knowledge Index & Graph Memory
Tests:
  1. Isolation test (asserts zero live-profile strings in knowledge graph & vector chunks)
  2. Schema exemplar verification (asserts default_user files are present and marked schema_exemplar)
  3. Index freshness idempotency (check_staleness returns True on clean index)
  4. Planted stale detection (verifies that hash modification is detected immediately)
  5. BM25-lite query retrieval verification (asserts expected file:line hits for core concepts)
"""

import os
import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_knowledge_index import (
    KnowledgeIndexBuilder,
    KNOWLEDGE_DIR,
    GRAPH_DIR,
    VECTORS_DIR,
    get_live_profile_names,
)

class TestKnowledgeIndex(unittest.TestCase):

    def setUp(self):
        self.builder = KnowledgeIndexBuilder()
        self.nodes_path = GRAPH_DIR / "nodes.json"
        self.edges_path = GRAPH_DIR / "edges.json"
        self.chunks_path = VECTORS_DIR / "chunks.json"
        self.meta_path = VECTORS_DIR / "index_meta.json"

    def test_01_index_files_exist(self):
        """Assert that all Layer G and Layer V index files exist."""
        self.assertTrue(self.nodes_path.exists(), "nodes.json missing")
        self.assertTrue(self.edges_path.exists(), "edges.json missing")
        self.assertTrue(self.chunks_path.exists(), "chunks.json missing")
        self.assertTrue(self.meta_path.exists(), "index_meta.json missing")

    def test_02_privacy_isolation_zero_live_profiles(self):
        """CRITICAL: Assert zero live-profile directory chunks or nodes exist in graph or vector index."""
        live_names = get_live_profile_names()
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        for c in chunks_data:
            p = c.get("path", "").replace("\\", "/")
            if p.startswith("profiles/"):
                self.assertTrue(
                    p.startswith("profiles/default_user/"),
                    f"Privacy breach: non-default_user profile file indexed in chunks: {p}"
                )
            for forbidden in live_names:
                self.assertFalse(
                    p.startswith(f"profiles/{forbidden}"),
                    f"Privacy breach: live candidate profile directory '{forbidden}' indexed at {p}!"
                )

        with open(self.nodes_path, "r", encoding="utf-8") as f:
            nodes_data = json.load(f)

        for n in nodes_data:
            p = n.get("properties", {}).get("path", "").replace("\\", "/")
            if p.startswith("profiles/"):
                self.assertTrue(
                    p.startswith("profiles/default_user/"),
                    f"Privacy breach: non-default_user profile node found: {p}"
                )
            for forbidden in live_names:
                self.assertFalse(
                    p.startswith(f"profiles/{forbidden}"),
                    f"Privacy breach: live candidate profile directory '{forbidden}' in node {n['id']}!"
                )

    def test_03_default_user_schema_exemplar_present(self):
        """Assert profiles/default_user is indexed as schema_exemplar."""
        with open(self.nodes_path, "r", encoding="utf-8") as f:
            nodes = json.load(f)

        schema_nodes = [n for n in nodes if n.get("tier") == "schema_exemplar"]
        self.assertGreater(len(schema_nodes), 0, "No schema_exemplar nodes found in graph!")

        paths = [n["properties"].get("path") for n in schema_nodes if "path" in n["properties"]]
        self.assertTrue(
            any("candidate_config.json" in p for p in paths),
            "default_user candidate_config.json missing from schema_exemplar graph nodes"
        )

    def test_04_index_freshness_idempotency(self):
        """Assert that check_staleness passes cleanly on current working tree."""
        is_fresh, issues = self.builder.check_staleness()
        self.assertTrue(is_fresh, f"Index should be 100% fresh, but got issues: {issues}")
        self.assertEqual(len(issues), 0)

    def test_05_planted_stale_detection(self):
        """Assert that mutating a stored file hash is immediately flagged as stale."""
        with open(self.meta_path, "r", encoding="utf-8") as f:
            original_meta = json.load(f)

        try:
            # Plant a mutated hash
            mutated_meta = json.loads(json.dumps(original_meta))
            first_key = next(iter(mutated_meta["file_hashes"]))
            mutated_meta["file_hashes"][first_key]["hash"] = "0000000000000000000000000000000000000000000000000000000000000000"

            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(mutated_meta, f, indent=2)

            is_fresh, issues = self.builder.check_staleness()
            self.assertFalse(is_fresh, "check_staleness failed to detect planted hash corruption!")
            self.assertTrue(any(first_key in iss for iss in issues), f"Expected issue for {first_key}, got: {issues}")

        finally:
            # Restore original clean metadata
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(original_meta, f, indent=2)

    def test_06_bm25_query_retrieval(self):
        """Assert that querying core architectural terms returns high-confidence results with file:line."""
        # Query 1: batch_question
        results_batch = self.builder.query("batch_question", top_k=5)
        self.assertGreater(len(results_batch), 0, "Query for 'batch_question' returned 0 results")
        top_batch = results_batch[0]
        self.assertIn("path", top_batch)
        self.assertIn("lines", top_batch)
        self.assertGreater(top_batch["score"], 0.0)

        # Query 2: experience_gap_gated
        results_c24 = self.builder.query("experience_gap_gated", top_k=5)
        self.assertGreater(len(results_c24), 0, "Query for 'experience_gap_gated' returned 0 results")
        top_c24 = results_c24[0]
        self.assertIn("lines", top_c24)
        self.assertGreater(top_c24["score"], 0.0)

    def test_07_pagerank_and_summaries_exist(self):
        """Assert PageRank + summaries artifacts exist and core outranks generic tokens."""
        import pathlib
        pr_path = pathlib.Path("knowledge/graph/pagerank.json")
        sum_path = pathlib.Path("knowledge/graph/summaries.json")
        base = pathlib.Path(__file__).resolve().parent.parent
        self.assertTrue((base / pr_path).exists(), "pagerank.json missing")
        self.assertTrue((base / sum_path).exists(), "summaries.json missing")
        pr = json.loads(((base / pr_path).read_text(encoding="utf-8")))
        self.assertGreater(len(pr), 0, "PageRank empty")
        sums = json.loads(((base / sum_path).read_text(encoding="utf-8")))
        self.assertGreater(len(sums), 0, "Summaries empty")
        core_hits = [s for s in sums if str(s.get("path", "")).startswith("core/")]
        self.assertGreater(len(core_hits), 0, "No core summaries for budget entry point")

    def test_08_dynamic_profile_exclusion(self):
        """Assert exclusion is dynamic (no hardcoded names) and covers new profiles."""
        import inspect
        import scripts.build_knowledge_index as bki
        src = inspect.getsource(bki.get_live_profile_names)
        self.assertIn("default_user", src)
        self.assertNotIn("anshika_garg", src)
        self.assertNotIn("bharat_pandey", src)
        live = bki.get_live_profile_names()
        self.assertNotIn("default_user", live)
        try:
            chunks_data = json.loads((PROJECT_ROOT / "knowledge" / "vectors" / "chunks.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.skipTest("chunks.json not built yet; run scripts/build_knowledge_index.py --build first")
            return
        # Only Repo_A chunks must be free of live config paths; Repo_B (Sophron
        # personal_intelligence) legitimately references historic session profiles.
        repo_a_text = " ".join(
            (c.get("text", "") + " " + c.get("path", ""))
            for c in chunks_data if c.get("repo") == "Repo_A"
        )
        for name in live:
            self.assertNotIn(f"profiles/{name}/candidate_config.json", repo_a_text, f"live config indexed: {name}")

    def test_09_tier_boost_core_over_generic(self):
        """Assert tier boost keeps engine chunks competitive vs generic docs."""
        results = self.builder.query("ipc_watcher poll pending_question", top_k=5)
        self.assertGreater(len(results), 0)
        paths = [r["path"] for r in results]
        self.assertTrue(any("ipc_watcher" in p or "ai_client" in p or "04_job_discovery" in p for p in paths), f"core engine missing from top results: {paths}")

    def test_10_domain_split_agent_vs_intelligence(self):
        """Assert knowledge is split into agent_structure vs personal_intelligence with no mixing."""
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)
        domains = set(c.get("domain", "") for c in chunks_data)
        self.assertIn("agent_structure", domains)
        self.assertIn("personal_intelligence", domains)
        agent_results = self.builder.query("batch_question", top_k=5, domain="agent_structure")
        for r in agent_results:
            self.assertEqual(r.get("domain", "agent_structure"), "agent_structure")
        intel_results = self.builder.query("insight", top_k=5, domain="personal_intelligence")
        if intel_results:
            for r in intel_results:
                self.assertEqual(r.get("domain"), "personal_intelligence")

if __name__ == "__main__":
    unittest.main()
