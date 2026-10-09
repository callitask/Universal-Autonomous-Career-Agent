#!/usr/bin/env python3
"""
Universal Autonomous Career Agent - Application Pipeline Runner.
Runs the end-to-end application lifecycle autonomously using Section Mini-Agents:
- Section 1: ProfileSectionAgent
- Section 2: QuestionnaireSectionAgent
- Section 3: EducationSectionAgent & ExperienceSectionAgent
- Section 4: ReviewSectionAgent (Strict Human Gate - HALTS before SUBMIT)
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from CompanySiteApply.apply_orchestrator import ApplyOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Universal Autonomous Career Agent - Application Runner")
    parser.add_argument("--profile", default="udaysagar_kandpal", help="Profile folder name under profiles/")
    parser.add_argument("--config", default=None, help="Explicit path to candidate_config.json")
    parser.add_argument("--cdp-url", default=None, help="CDP endpoint URL (defaults to env or candidate_config)")
    args = parser.parse_args()

    cfg_path = Path(args.config) if args.config else (ROOT / "profiles" / args.profile / "candidate_config.json")
    if not cfg_path.exists():
        cfg_path = ROOT / "profiles" / "default_user" / "candidate_config.json"

    print(f"[Universal Apply Runner] Loading candidate profile from: {cfg_path}")
    candidate_data = json.loads(cfg_path.read_text(encoding="utf-8"))

    cdp_endpoint = args.cdp_url or candidate_data.get("candidate", {}).get("cdp_url") or "http://127.0.0.1:9222"
    orchestrator = ApplyOrchestrator(cdp_url=cdp_endpoint)
    artifacts_dir = ROOT / "artifacts"
    
    print(f"[Universal Apply Runner] Connecting to CDP at {cdp_endpoint}...")
    result = orchestrator.run(candidate_data, screenshot_dir=artifacts_dir)
    print("\n[Application Execution Result]:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
