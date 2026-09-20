# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# MANDATORY READING FOR AI AGENTS & DEVELOPERS:
# Before analyzing, refactoring, editing, or debugging this file, read this AI Context.
#
# APPEND-ONLY GOVERNANCE:
# 1. Never delete or overwrite previous entries. Always append new entries chronologically.
# 2. Each entry must have: Serial Number, Category Term, Date & Exact Local Timestamp,
#    Issue/Context, Changes Done, Rationale, and Preventative Notes (what NOT to repeat).
# 3. Candidate-Agnostic / Zero-PII: Never record personal candidate names, emails, phones,
#    or specific candidate data here.
#
# [ENTRY #001]
# Term: [SEARCH_STATE_MANAGER_INIT]
# Timestamp: 2026-09-19 23:30:00 +05:30
# Issue / Context: Batch Architecture v2.0 requires designation rotation with persistent state.
# Changes Made: Created SearchStateManager to track current designation index, rotation list,
#   per-designation stats, and cycle metadata across daemon restarts.
# Rationale: Replaces ad-hoc STARVATION_EXPANSION with a principled rotation engine.
#   Designation list is the single source of truth; rotation is deterministic and resumable.
# Preventative Notes:
#   - Never hardcode designation names or indexes here.
#   - Always use atomic save (write-to-temp + rename) to prevent corruption.
#   - search_state.json lives under output/, not under profile root.
# ================================================================================
"""
search_state_manager.py
Designation Rotation Engine — Persistent State Manager

Manages which search designation/keyword the discovery engine should use next.
Provides smart rotation across all configured designations, tracks per-designation
stats, and supports resuming across daemon restarts without duplication.

Usage:
    from core.utils.search_state_manager import SearchStateManager
    state = SearchStateManager(profile_dir)
    designation = state.get_current_designation()
    state.record_stats(designation, cards_found=40, approved=8, applied=5)
    state.advance()
"""

import json
import time
import os
from pathlib import Path
from typing import List, Optional, Dict, Any


class SearchStateManager:
    """
    Manages designation rotation state across daemon cycles.
    All state is persisted to output/search_state.json under the profile directory.
    """

    STATE_FILE = "search_state.json"

    def __init__(self, profile_dir: Path):
        self.profile_dir = Path(profile_dir).resolve()
        self.state_path = self.profile_dir / "output" / self.STATE_FILE
        self._state: Dict[str, Any] = {}
        self._load()

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def get_current_designation(self) -> Optional[str]:
        """Returns the designation to search next. None if list is empty."""
        desigs = self._state.get("all_designations", [])
        if not desigs:
            return None
        idx = self._state.get("current_designation_index", 0) % len(desigs)
        return desigs[idx]

    def get_current_index(self) -> int:
        """Returns the current designation index."""
        desigs = self._state.get("all_designations", [])
        if not desigs:
            return 0
        return self._state.get("current_designation_index", 0) % len(desigs)

    def advance(self) -> str:
        """
        Advance to the next designation in the rotation.
        Wraps around to 0 when the full list is exhausted.
        Returns the NEW current designation after advancing.
        """
        desigs = self._state.get("all_designations", [])
        if not desigs:
            return ""
        old_idx = self._state.get("current_designation_index", 0)
        new_idx = (old_idx + 1) % len(desigs)
        self._state["current_designation_index"] = new_idx
        self._state["last_advanced_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if new_idx == 0:
            self._state["full_cycles_completed"] = self._state.get("full_cycles_completed", 0) + 1
            print(f"[SEARCH STATE] Full designation rotation cycle completed. Starting cycle #{self._state['full_cycles_completed'] + 1}.", flush=True)
        self._save()
        new_desig = desigs[new_idx]
        print(f"[SEARCH STATE] Rotated to designation [{new_idx}/{len(desigs)-1}]: '{new_desig}'", flush=True)
        return new_desig

    def record_stats(self, designation: str, cards_found: int = 0, cards_approved: int = 0, cards_applied: int = 0):
        """Record stats for a completed designation search."""
        if "designation_stats" not in self._state:
            self._state["designation_stats"] = {}
        self._state["designation_stats"][designation] = {
            "last_searched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cards_found": cards_found,
            "cards_approved": cards_approved,
            "cards_applied": cards_applied
        }
        self._save()

    def sync_designations(self, new_list: List[str]) -> bool:
        """
        Sync the designation list with a new authoritative list from config/cognitive profile.
        Preserves current index position (best effort).
        Adds new designations; keeps existing ones that still exist in new_list.
        Returns True if list changed.
        """
        old_list = self._state.get("all_designations", [])
        # Preserve order: keep old entries that are still valid, append new ones
        merged = [d for d in old_list if d in new_list]
        for d in new_list:
            if d not in merged:
                merged.append(d)
        if merged == old_list:
            return False  # No change
        # Adjust index if current designation still exists
        current = self.get_current_designation()
        self._state["all_designations"] = merged
        if current and current in merged:
            self._state["current_designation_index"] = merged.index(current)
        else:
            self._state["current_designation_index"] = 0
        self._save()
        print(f"[SEARCH STATE] Designation list synced: {len(old_list)} → {len(merged)} entries.", flush=True)
        return True

    def append_designations(self, new_desigs: List[str]) -> int:
        """Append new designations from AG Brain expansion (no duplicates). Returns count added."""
        existing = set(self._state.get("all_designations", []))
        added = 0
        for d in new_desigs:
            if d and d.strip() and d not in existing:
                self._state.setdefault("all_designations", []).append(d)
                existing.add(d)
                added += 1
        if added:
            self._save()
            print(f"[SEARCH STATE] Appended {added} new designations from AG Brain expansion.", flush=True)
        return added

    def get_all_designations(self) -> List[str]:
        """Return full list of all designations in rotation."""
        return list(self._state.get("all_designations", []))

    def get_stats(self) -> Dict[str, Any]:
        """Return a summary of the current state."""
        desigs = self._state.get("all_designations", [])
        return {
            "current_designation": self.get_current_designation(),
            "current_index": self.get_current_index(),
            "total_designations": len(desigs),
            "full_cycles_completed": self._state.get("full_cycles_completed", 0),
            "last_advanced_at": self._state.get("last_advanced_at", "never"),
        }

    # ─────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────

    def _load(self):
        """Load state from disk. Creates a default state if not found."""
        if self.state_path.exists():
            try:
                self._state = json.loads(self.state_path.read_text(encoding="utf-8"))
                return
            except Exception as e:
                print(f"[SEARCH STATE] Warning: could not parse state file ({e}). Resetting.", flush=True)
        self._state = {
            "current_designation_index": 0,
            "all_designations": [],
            "full_cycles_completed": 0,
            "last_advanced_at": None,
            "designation_stats": {}
        }

    def _save(self):
        """Atomically save state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
            os.replace(tmp, self.state_path)
        except Exception as e:
            print(f"[SEARCH STATE] Warning: could not save state ({e}).", flush=True)
