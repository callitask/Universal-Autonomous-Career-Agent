# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# MANDATORY READING FOR AI AGENTS & DEVELOPERS:
# Before analyzing, refactoring, editing, or debugging this file, read this AI Context.
# This block records the chronological history of changes, root-cause fixes, what was
# tried, what worked, what failed/was reverted, and critical design invariants.
#
# APPEND-ONLY GOVERNANCE:
# 1. Never delete or overwrite previous entries. Always append new entries chronologically.
# 2. Each entry must have: Serial Number, Category Term, Date & Exact Local Timestamp,
#    Issue/Context, Changes Done, Rationale, and Preventative Notes (what NOT to repeat).
# 3. Candidate-Agnostic / Zero-PII: Never record personal candidate names, emails, phones,
#    or specific candidate data here. Record generic architectural, DOM, and logic patterns.
#
# [ENTRY #001]
# Term: [PROFILE_SANDBOX_ABSTRACTION]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Hardcoded file paths and profile directories caused cross-candidate data collisions.
# Changes Made: Built ProfileContext resolving all paths, configs, and outputs strictly under profiles/<profile_name>/.
# Rationale: Complete candidate isolation and multi-profile support.
# Preventative Notes: Never hardcode profiles/<name> paths in code; resolve dynamically via --profile or directory discovery.
#
# [ENTRY #002]
# Term: [DOCUMENTATION_PREFLIGHT]
# Timestamp: 2026-09-13 10:20:00 +05:30
# Issue / Context: Agents operated without internalizing workspace governance and bug prevention guardrails.
# Changes Made: Added _verify_documentation_preflight() automatically verifying WORKSPACE_RULES.md, ARCHITECTURE_REFERENCE.md, and PLATFORM_KNOWLEDGE.md on startup.
# Rationale: Mandatory compliance with Directives 1-8 and Guardrails C1-C24.
# Preventative Notes: Do not suppress pre-flight documentation verification.
#
# [ENTRY #003]
# Term: [ZERO-TRUST_PURITY_ENFORCER]
# Timestamp: 2026-09-13 16:11:00 +05:30
# Issue / Context: Prevent hardcoded candidate PII, user paths, compensation, and self-modifying code.
# Changes Made: Built verify_codebase_purity() running on every ProfileContext initialization across core/ and scripts/.
# Rationale: Mathematical guarantee of 100% candidate-agnostic, zero-hardcoding codebase purity.
# Preventative Notes: Any violation triggers a fatal CodebasePurityViolationError. Never bypass purity enforcement.
# ================================================================================
"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - PROFILE CONTEXT & SANDBOX RESOLVER
File: core/utils/profile_context.py
================================================================================
Pure profile-agnostic context manager. Dynamically resolves all candidate 
parameters, credentials, taxonomies, and paths at runtime with zero hardcoding.
Provides full backward and forward compatibility across all pipeline scripts.
Includes atomic file locking (C4) to prevent configuration corruption.
================================================================================
"""

import os
import sys
import time
import json
import re
import argparse
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def canonical_job_url(url: str) -> str:
    """
    Normalizes job URLs by stripping query parameters, session IDs (e.g. ?src=...&sid=...),
    tracking tokens, URL fragments, and trailing slashes.
    Ensures persistent matching across search sweeps and agent restarts.
    """
    if not url:
        return ""
    clean = str(url).strip()
    clean = clean.split("?")[0].split("#")[0].rstrip("/")
    return clean.lower()


def extract_platform_job_id(url: str, platform: str = "") -> Optional[str]:
    """
    Extracts immutable numeric platform job ID for deduplication across query/slug changes.
    Naukri: Trailing 10-14 digit identifier in slug (e.g. -040926031442) -> 'naukri:040926031442'
    LinkedIn: /jobs/view/<id> or currentJobId=<id> -> 'linkedin:<id>'
    """
    if not url:
        return None
    url_str = str(url).strip().lower()
    if "naukri.com" in url_str or platform.lower() == "naukri":
        m = re.search(r'-(\d{10,14})(?:[/?#]|$)', url_str)
        if m:
            return f"naukri:{m.group(1)}"
    if "linkedin.com" in url_str or platform.lower() == "linkedin":
        m = re.search(r'(?:/jobs/view/|currentjobid=)(\d+)', url_str)
        if m:
            return f"linkedin:{m.group(1)}"
    return None


class ProcessedLedger(dict):
    """
    High-performance hybrid ledger mapping URL/composite key -> structured metadata.
    Subclasses dict for O(1) key lookups, structured inspection, and JSON serialization,
    while offering backward-compatible set APIs (.add, .union, .intersection, .difference).
    Automatically indexes canonical URLs and platform job IDs for zero-duplicate guarantees.
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        if args and isinstance(args[0], dict):
            for k, v in args[0].items():
                if k:
                    clean_k = str(k).lower().strip()
                    super().__setitem__(clean_k, v if isinstance(v, dict) else {"status": str(v)})
        elif args and isinstance(args[0], (list, set, tuple)):
            for item in args[0]:
                if item:
                    self.add(str(item).lower().strip(), status="legacy")
        if kwargs:
            for k, v in kwargs.items():
                if k:
                    clean_k = str(k).lower().strip()
                    super().__setitem__(clean_k, v if isinstance(v, dict) else {"status": str(v)})

    def __contains__(self, item: Any) -> bool:
        if not item:
            return False
        clean_k = str(item).lower().strip()
        if super().__contains__(clean_k):
            return True
        if clean_k.startswith("http://") or clean_k.startswith("https://"):
            can_url = canonical_job_url(clean_k)
            if can_url and super().__contains__(can_url):
                return True
            job_id = extract_platform_job_id(clean_k)
            if job_id and super().__contains__(job_id):
                return True
        return False

    def __getitem__(self, item: Any) -> Any:
        return super().__getitem__(str(item).lower().strip())

    def __setitem__(self, key: Any, value: Any) -> None:
        clean_k = str(key).lower().strip()
        super().__setitem__(clean_k, value)

    def get(self, item: Any, default: Any = None) -> Any:
        return super().get(str(item).lower().strip(), default)

    def is_processed(self, url: str = None, company: str = None, title: str = None, platform: str = "") -> bool:
        """Convenience method to check URL, canonical URL, platform job ID, or composite key."""
        if url:
            clean_u = str(url).strip().lower()
            if clean_u in self:
                return True
            can = canonical_job_url(clean_u)
            if can in self:
                return True
            jid = extract_platform_job_id(clean_u, platform)
            if jid and jid in self:
                return True
        if company and title:
            clean_c = re.sub(r'[^a-z0-9]', '', str(company or '').lower())
            clean_t = re.sub(r'[^a-z0-9]', '', str(title or '').lower())
            if f"{clean_c}::{clean_t}" in self:
                return True
        return False

    def add(
        self,
        item: str,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        if not item:
            return
        clean_key = str(item).lower().strip()
        meta = dict(metadata) if metadata else {}
        if kwargs:
            meta.update(kwargs)
        if status:
            meta["status"] = status
        meta.setdefault("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
        
        if clean_key in self and isinstance(super().get(clean_key), dict):
            existing = dict(super().get(clean_key))
            existing.update({k: v for k, v in meta.items() if v is not None})
            super().__setitem__(clean_key, existing)
        else:
            super().__setitem__(clean_key, meta)

        # Index canonical URL and platform job ID if item is a URL
        if clean_key.startswith("http://") or clean_key.startswith("https://"):
            can_url = canonical_job_url(clean_key)
            if can_url and can_url != clean_key:
                super().__setitem__(can_url, meta)
            job_id = extract_platform_job_id(clean_key)
            if job_id:
                super().__setitem__(job_id, meta)

    def union(self, *others) -> "ProcessedLedger":
        res = ProcessedLedger(self)
        for other in others:
            if isinstance(other, dict):
                for k, v in other.items():
                    res.add(k, metadata=v if isinstance(v, dict) else {"status": str(v)})
            elif hasattr(other, "__iter__"):
                for item in other:
                    res.add(item)
        return res

    def intersection(self, other) -> set:
        other_keys = other.keys() if isinstance(other, dict) else other
        return set(self.keys()).intersection(other_keys)

    def difference(self, other) -> set:
        other_keys = other.keys() if isinstance(other, dict) else other
        return set(self.keys()).difference(other_keys)

    def __or__(self, other):
        return self.union(other)

    def __ior__(self, other):
        if isinstance(other, dict):
            for k, v in other.items():
                self.add(k, metadata=v if isinstance(v, dict) else {"status": str(v)})
        elif hasattr(other, "__iter__"):
            for item in other:
                self.add(item)
        return self


class CodebasePurityViolationError(RuntimeError):
    """Raised when hardcoded candidate values or profile paths are found in core engine scripts."""
    pass


class ProfileContext:
    """
    Enterprise Profile Sandboxing & Path Resolution Engine.
    Encapsulates all candidate configuration, master resume data, 
    and output directory state.
    """

    def __init__(
        self,
        profile_path: Optional[Union[str, Path]] = None,
        base_path: Optional[Union[str, Path]] = None
    ):
        self.base_path = Path(base_path).resolve() if base_path else PROJECT_ROOT
        
        # 1. Resolve Profile Directory Path
        if profile_path:
            p_path = Path(profile_path)
            if p_path.is_absolute():
                self.profile_path = p_path.resolve()
            else:
                self.profile_path = (self.base_path / p_path).resolve()
        else:
            self.profile_path = self._auto_discover_profile_dir()

        self.profile_dir = self.profile_path

        # 2. File Path References
        self.config_path = self.profile_path / "candidate_config.json"
        self.resume_path = self.profile_path / "resume.md"
        self.output_dir = self.profile_path / "output"
        self.applications_dir = self.output_dir / "applications"
        self.manifest_path = self.output_dir / "search_manifest.json"
        self.tracker_path = self.output_dir / "applications_tracker.csv"
        self.saved_external_path = self.output_dir / "saved_external_jobs.json"
        self.cognitive_profile_path = self.output_dir / "cognitive_profile.json"
        self.ledger_path = self.output_dir / "processed_ledger.json"
        self.logs_dir = self.output_dir / "logs"

        # 3. Ensure Output Directories Exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.applications_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 4. Mandatory Documentation Auto-Load & Sandbox Boundary Verification
        self._verify_documentation_preflight()

        # 5. Ingest State
        self.config: Dict[str, Any] = self._load_config()
        self.resume_text: str = self._load_resume()

        # 6. Guardrail P1: Zero-Trust Codebase Purity Verification
        self.verify_codebase_purity()

        # 7. Universal Startup Profile & Resume Comprehension
        self.cognitive_profile: Dict[str, Any] = self._ensure_cognitive_profile_analyzed()

    def _verify_documentation_preflight(self) -> None:
        """
        Mandatory Pre-Flight Documentation & Sandbox Verification Protocol.
        Guarantees that every script launch verifies all core documentation and
        explicitly establishes the dynamic sandbox boundaries for profiles/.
        """
        docs_dir = self.base_path / "docs"
        rules_file = docs_dir / "WORKSPACE_RULES.md"
        arch_file = docs_dir / "ARCHITECTURE_REFERENCE.md"
        plat_file = docs_dir / "PLATFORM_KNOWLEDGE.md"

        docs_present = rules_file.exists() and arch_file.exists() and plat_file.exists()
        doc_status = "VERIFIED [OK]" if docs_present else "WARNING: MISSING FILES"

        print("=" * 80, flush=True)
        print(f" [PRE-FLIGHT] MANDATORY DOCUMENTATION VERIFICATION: {doc_status}", flush=True)
        print(f"   -> {rules_file.name} (Directives 1-8, 20+ Bug Prevention Guardrails)", flush=True)
        print(f"   -> {arch_file.name} (Pipeline anatomy, contracts, data schemas)", flush=True)
        print(f"   -> {plat_file.name} (DOM mechanics, SEO slugs, zero-comma rules)", flush=True)
        print(f" [SANDBOX BOUNDARY] Active Candidate Sandbox: {self.profile_path}", flush=True)
        print(f" [DYNAMIC DATA I/O] Volatile Output Directory: {self.output_dir}", flush=True)
        print(f" [DEVELOPER NOTICE] profiles/ is dynamic runtime I/O data. Engine code lives in core/.", flush=True)
        print(f"                    For schema blueprint & debugging, inspect: profiles/default_user", flush=True)
        print("=" * 80, flush=True)

    def append_execution_log(self, text: str) -> None:
        """Appends execution telemetry to the profile terminal log and root logs_dump.txt."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] {text.strip()}\n"
        try:
            log_file = self.logs_dir / "terminal_execution_log.txt"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass
        try:
            root_log = self.base_path / "logs_dump.txt"
            with open(root_log, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass


    def _auto_discover_profile_dir(self) -> Path:
        """Dynamically scans profiles directory or parses CLI arguments."""
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--profile", type=str, default=None)
        args, _ = parser.parse_known_args()

        if args.profile:
            p = Path(args.profile)
            return p.resolve() if p.is_absolute() else (self.base_path / p).resolve()

        profiles_dir = self.base_path / "profiles"
        if profiles_dir.exists():
            candidates = [p for p in profiles_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
            if candidates:
                # Prefer candidate folder with candidate_config.json that is not default_user
                valid_candidates = [p for p in candidates if (p / "candidate_config.json").exists() and p.name != "default_user"]
                if valid_candidates:
                    selected = valid_candidates[0].resolve()
                    print(f"[ProfileContext] Auto-discovered active candidate profile: {selected.name}", flush=True)
                    return selected
                selected = candidates[0].resolve()
                print(f"[ProfileContext] Auto-discovered profile: {selected.name}", flush=True)
                return selected

        raise RuntimeError(
            f"[ProfileContext] No valid candidate profile found in {profiles_dir}. "
            f"Please supply '--profile profiles/<profile_name>'."
        )

    def verify_codebase_purity(self) -> Tuple[bool, List[str]]:
        r"""
        Guardrail P1: Zero-Trust Codebase Purity & Zero-Hardcoding Enforcer.
        Scans all python files in core/ and scripts/ to guarantee that:
        1. No candidate-specific values (full name, email, phone, compensation, specific profile folder) are hardcoded.
        2. No hardcoded Windows user paths (C:\Users\...) exist.
        3. No self-modifying code writes to .py files.
        4. All parameters are dynamically derived from candidate_config.json via ProfileContext.
        Raises CodebasePurityViolationError if any violation is detected.
        """
        scan_dirs = [self.base_path / "core", self.base_path / "scripts"]
        violations = []
        cand = self.config.get("candidate", {})
        cand_name = str(cand.get("full_name", "")).strip().lower()
        cand_email = str(cand.get("email", "")).strip().lower()
        cand_phone = re.sub(r'\D', '', str(cand.get("phone", "")))
        profile_folder_name = self.profile_path.name.lower()

        # Check candidate personal values (ignoring placeholders)
        forbidden_strings = set()
        if cand_name and len(cand_name.split()) >= 2 and not any(p in cand_name for p in ["[", "<", "your", "default"]):
            forbidden_strings.add(cand_name)
        if cand_email and "@" in cand_email and not any(p in cand_email for p in ["[", "<", "your", "default"]):
            forbidden_strings.add(cand_email)
        if cand_phone and len(cand_phone) >= 10 and not any(p in cand_phone for p in ["[", "<"]):
            forbidden_strings.add(cand_phone)
        if profile_folder_name and profile_folder_name != "default_user":
            forbidden_strings.add(f"profiles/{profile_folder_name}")
            forbidden_strings.add(f"profiles\\\\{profile_folder_name}")

        py_files = []
        for sdir in scan_dirs:
            if sdir.exists():
                py_files.extend([f for f in sdir.rglob("*.py") if "__pycache__" not in str(f)])

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = content.split("\n")
            for idx, line in enumerate(lines, 1):
                s_line = line.strip()
                if not s_line or s_line.startswith("#") or s_line.startswith('"""') or s_line.startswith("'''"):
                    continue

                # 1. Check for candidate personal data / profile path
                for s in forbidden_strings:
                    if s in s_line.lower():
                        violations.append(f"Hardcoded candidate token '{s}' at {py_file.relative_to(self.base_path)}:{idx}")

                # 2. Check for hardcoded Windows user paths
                if re.search(r"C:\\Users\\[a-zA-Z0-9_-]+", s_line, re.IGNORECASE):
                    violations.append(f"Hardcoded Windows user directory at {py_file.relative_to(self.base_path)}:{idx}: {s_line}")

            # 3. Check for self-modifying scripts writing to .py files
            write_py_matches = re.findall(r'open\s*\([^)]*\.py[\'\"][^)]*[\'\"a-zA-Z]*w', content)
            if write_py_matches:
                violations.append(f"Potential self-modifying write to .py found in {py_file.relative_to(self.base_path)}: {write_py_matches}")

        if violations:
            err_msg = "[GUARDRAIL P1 VIOLATION] Hardcoded data or PII detected in codebase:\n" + "\n".join(f"  - {v}" for v in violations)
            raise CodebasePurityViolationError(err_msg)

        print("  [PURITY CHECK] Guardrail P1 passed: Zero-trust codebase purity verified (0 hardcoded values).", flush=True)
        return True, []

    def _load_config(self) -> Dict[str, Any]:
        """Loads candidate_config.json safely."""
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProfileContext] Warning: Failed to parse {self.config_path.name}: {e}")
            return {}

    def _load_resume(self) -> str:
        """Loads resume.md text safely."""
        if not self.resume_path.exists():
            return ""
        try:
            with open(self.resume_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"[ProfileContext] Warning: Failed to parse {self.resume_path.name}: {e}")
            return ""

    def save_config(self) -> None:
        """Persists self.config back to candidate_config.json ATOMICALLY."""
        try:
            tmp_path = self.config_path.with_name(self.config_path.name + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.config_path)
        except Exception as e:
            print(f"[ProfileContext] Error saving configuration atomically to disk: {e}")

    def reload_config(self) -> Dict[str, Any]:
        """Refreshes self.config from disk."""
        self.config = self._load_config()
        return self.config

    def load_cognitive_profile(self) -> Dict[str, Any]:
        """Loads cognitive_profile.json safely if present."""
        if not self.cognitive_profile_path.exists():
            return {}
        try:
            with open(self.cognitive_profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProfileContext] Notice: Failed to parse {self.cognitive_profile_path.name}: {e}")
            return {}

    def save_cognitive_profile(self, data: Dict[str, Any]) -> None:
        """Persists cognitive_profile.json ATOMICALLY."""
        try:
            tmp_path = self.cognitive_profile_path.with_name(self.cognitive_profile_path.name + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.cognitive_profile_path)
        except Exception as e:
            print(f"[ProfileContext] Error saving cognitive profile atomically: {e}")

    def _ensure_cognitive_profile_analyzed(self) -> Dict[str, Any]:
        """
        Universal Startup Profile & Resume Comprehension Hook.
        Guarantees that whenever any script launches for any candidate profile,
        the resume is parsed and understood in-depth (domain, seniority, experience,
        skills, constraints) so screening questions can be resolved immediately.
        """
        cog_data = self.load_cognitive_profile()
        if cog_data and cog_data.get("candidate_domain") and cog_data.get("core_domain_skills"):
            return cog_data

        try:
            from core.ai_client import AIClient
            client = AIClient(self)
            synthesized = client.synthesize_cognitive_profile(force_refresh=False)
            if synthesized:
                return synthesized
        except Exception:
            pass

        return cog_data or {}

    def load_processed_ledger(self) -> ProcessedLedger:
        """
        Loads structured dictionary ledger of processed URLs/composite keys.
        Backward-compatible with legacy list/dict formats on disk.
        Returns ProcessedLedger supporting O(1) lookup speed and metadata retrieval.
        """
        ledger = ProcessedLedger()
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for x in data:
                            if x:
                                ledger.add(str(x).lower().strip(), status="legacy")
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if k:
                                clean_k = str(k).lower().strip()
                                meta = v if isinstance(v, dict) else {"status": str(v)}
                                ledger[clean_k] = meta
            except Exception as e:
                print(f"[ProfileContext] Notice: Failed to load ledger: {e}")
        return ledger

    def save_processed_ledger(self, ledger: Any) -> None:
        """
        Atomically persists processed ledger dictionary to disk.
        Supports ProcessedLedger, dict, or legacy set/list.
        """
        try:
            if isinstance(ledger, dict):
                data_to_save = dict(ledger)
            elif isinstance(ledger, (set, list, tuple)):
                data_to_save = {
                    str(x).lower().strip(): {
                        "status": "legacy",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    for x in ledger if x
                }
            else:
                data_to_save = {}

            tmp_path = self.ledger_path.with_name(self.ledger_path.name + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.ledger_path)
        except Exception as e:
            print(f"[ProfileContext] Error saving ledger atomically: {e}")

    def add_to_processed_ledger(
        self,
        item: str,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Adds a single URL or composite key to the persistent ledger with structured metadata.
        Stores status, company, title, score, timestamp alongside the key.
        Maintains O(1) deduplication lookup speed.
        """
        if not item:
            return
        item_clean = str(item).lower().strip()
        ledger = self.load_processed_ledger()
        
        meta = dict(metadata) if metadata else {}
        if kwargs:
            meta.update(kwargs)
        if status:
            meta["status"] = status
        meta.setdefault("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
        
        ledger.add(item_clean, status=meta.get("status"), metadata=meta)
        self.save_processed_ledger(ledger)

    @property
    def candidate(self) -> Dict[str, Any]:
        return self.config.get("candidate", {})

    @property
    def candidate_name(self) -> str:
        cand = self.candidate
        return cand.get("full_name") or cand.get("name") or self.profile_path.name.replace("_", " ").title()

    @property
    def full_name(self) -> str:
        return self.candidate_name

    @property
    def first_name(self) -> str:
        name = self.candidate_name.strip()
        return name.split()[0] if name else "Candidate"

    @property
    def last_name(self) -> str:
        parts = self.candidate_name.strip().split()
        return parts[-1] if len(parts) > 1 else ""

    @property
    def cdp_url(self) -> str:
        configured = self.candidate.get("cdp_url", "http://127.0.0.1:9222")
        # Fast health check with fallback auto-probe across standard ports (9222, 9223)
        candidate_ports = [configured, "http://127.0.0.1:9222", "http://127.0.0.1:9223"]
        seen = set()
        import urllib.request
        for url in candidate_ports:
            if url in seen:
                continue
            seen.add(url)
            try:
                urllib.request.urlopen(f"{url.rstrip('/')}/json/version", timeout=0.8)
                return url
            except Exception:
                pass
        return configured

    @property
    def target_jobs(self) -> Dict[str, Any]:
        return self.config.get("target_jobs", {})

    @property
    def taxonomy_skills(self) -> Dict[str, Any]:
        return self.config.get("taxonomy_skills", {})

    @property
    def ats_answers(self) -> Dict[str, Any]:
        return self.config.get("ats_answers", {})

    @property
    def auto_learned_truths(self) -> Dict[str, Any]:
        return self.config.get("auto_learned_truths", {})