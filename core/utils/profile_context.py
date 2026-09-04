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
import argparse
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ProcessedLedger(dict):
    """
    High-performance hybrid ledger mapping URL/composite key -> structured metadata.
    Subclasses dict for O(1) key lookups, structured inspection, and JSON serialization,
    while offering backward-compatible set APIs (.add, .union, .intersection, .difference).
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
        return super().__contains__(clean_k)

    def __getitem__(self, item: Any) -> Any:
        return super().__getitem__(str(item).lower().strip())

    def __setitem__(self, key: Any, value: Any) -> None:
        clean_k = str(key).lower().strip()
        super().__setitem__(clean_k, value)

    def get(self, item: Any, default: Any = None) -> Any:
        return super().get(str(item).lower().strip(), default)

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

        # 3. Ensure Output Directories Exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.applications_dir.mkdir(parents=True, exist_ok=True)

        # 4. Ingest State
        self.config: Dict[str, Any] = self._load_config()
        self.resume_text: str = self._load_resume()

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
            candidates = [p for p in profiles_dir.iterdir() if p.is_dir()]
            if candidates:
                return candidates[0].resolve()

        raise RuntimeError(
            f"[ProfileContext] No valid candidate profile found in {profiles_dir}. "
            f"Please supply '--profile profiles/<profile_name>'."
        )

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
        return self.candidate.get("cdp_url", "http://127.0.0.1:9222")

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