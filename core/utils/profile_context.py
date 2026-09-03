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
import json
import argparse
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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