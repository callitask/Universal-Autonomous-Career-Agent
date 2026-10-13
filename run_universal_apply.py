#!/usr/bin/env python3
"""
Universal Autonomous Career Agent - Application Pipeline Runner.
Runs the end-to-end application lifecycle autonomously using Section Mini-Agents:
- Mode 1 (Autonomous Full Lifecycle): Search -> Evaluate & Match -> Tailor Documents -> Apply -> Gate & Verify
- Mode 2 (Active Page Apply): Runs Section Mini-Agents on the currently open application form.
"""

import sys
import json
import argparse
import asyncio
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
from CompanySiteApply.autonomous_job_agent import AutonomousJobAgent


def run_active_page_apply(args, candidate_data, cdp_endpoint):
    orchestrator = ApplyOrchestrator(cdp_url=cdp_endpoint)
    artifacts_dir = ROOT / "artifacts"
    
    print(f"[Universal Apply Runner] Connecting to CDP at {cdp_endpoint} (Active Tab Apply Mode)...")
    result = orchestrator.run(candidate_data, screenshot_dir=artifacts_dir)
    print("\n[Application Execution Result]:")
    print(json.dumps(result, indent=2))
    return result


async def run_autonomous_lifecycle(args, candidate_data, cdp_endpoint):
    from playwright.async_api import async_playwright
    print(f"[Universal Apply Runner] Launching Master Autonomous Lifecycle Controller at {cdp_endpoint}...")
    agent = AutonomousJobAgent(cdp_url=cdp_endpoint)
    
    # Stage 1: Comprehend Profile
    agent.stage_1_comprehend_profile(profile_name=args.profile, candidate_config=candidate_data)

    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(agent.cdp_url)
        page = b.contexts[0].pages[0]

        # Stage 2: Autonomous Portal Search
        eligible_jobs = await agent.stage_2_search_jobs(page, keyword=args.keyword, location=args.location)
        if not eligible_jobs:
            print("[Universal Apply Runner] No eligible unapplied jobs found.")
            return {"status": "NO_ELIGIBLE_JOBS"}

        # Stage 3: Cognitive Match Evaluation & Ranking
        ranked_jobs = await agent.stage_3_evaluate_and_rank(page, eligible_jobs, max_evaluations=args.max_eval)
        if not ranked_jobs:
            print("[Universal Apply Runner] Could not evaluate jobs.")
            return {"status": "EVALUATION_FAILED"}

        # Save match results into the candidate's sandbox (never the repo root)
        from CompanySiteApply.utils.match_report import save_match_report
        out_file = save_match_report(ROOT / "profiles" / agent.profile_slug / "output", ranked_jobs)
        print(f"[Universal Apply Runner] Saved job match report to {out_file}")

        best_job = ranked_jobs[0]
        if not best_job.get("is_eligible"):
            print(f"[Universal Apply Runner] Top job {best_job['job_id']} scored {best_job['score']}/100 - Below eligibility threshold.")
            return {"status": "BELOW_THRESHOLD", "top_job": best_job}

        # Stage 4: Requisition Document Tailoring
        print(f"\n[Universal Apply Runner] Tailoring documents for Job {best_job['job_id']}: {best_job['title']}...")
        tailor_res = agent.stage_4_tailor_documents(best_job)
        if not tailor_res.get("success"):
            print(f"[Universal Apply Runner] Warning: Document tailoring encountered an issue: {tailor_res.get('error')}")

        # Stage 5: Section Mini-Agent Dispatch & Form Application
        print(f"\n[Universal Apply Runner] Applying to Job {best_job['job_id']}...")
        app_res = await agent.stage_5_apply_form(page, best_job, screenshot_dir=ROOT / "artifacts")

        # Stage 6: Visual Audit, Human Submission Gate & Ledger Persistence
        gate_res = await agent.stage_6_verify_and_gate(page, best_job, app_res, screenshot_dir=ROOT / "artifacts")
        print("\n[Human Submission Gate Report]:")
        print(json.dumps(gate_res, indent=2))
        return gate_res


def main():
    parser = argparse.ArgumentParser(description="Universal Autonomous Career Agent - Application Runner")
    parser.add_argument("--profile", default="udaysagar_kandpal", help="Profile folder name under profiles/")
    parser.add_argument("--config", default=None, help="Explicit path to candidate_config.json")
    parser.add_argument("--cdp-url", default=None, help="CDP endpoint URL (defaults to env or candidate_config)")
    parser.add_argument("--autonomous", action="store_true", help="Run full autonomous lifecycle (Search -> Match -> Tailor -> Apply -> Gate)")
    parser.add_argument("--keyword", default=None, help="Optional search keyword override for autonomous mode")
    parser.add_argument("--location", default=None, help="Optional search location override for autonomous mode")
    parser.add_argument("--max-eval", type=int, default=5, help="Max jobs to inspect in autonomous mode")
    args = parser.parse_args()

    cfg_path = Path(args.config) if args.config else (ROOT / "profiles" / args.profile / "candidate_config.json")
    if not cfg_path.exists():
        cfg_path = ROOT / "profiles" / "default_user" / "candidate_config.json"

    print(f"[Universal Apply Runner] Loading candidate profile from: {cfg_path}")
    candidate_data = json.loads(cfg_path.read_text(encoding="utf-8"))
    candidate_data["profile"] = args.profile

    cdp_endpoint = args.cdp_url or candidate_data.get("candidate", {}).get("cdp_url") or "http://127.0.0.1:9222"

    if args.autonomous:
        asyncio.run(run_autonomous_lifecycle(args, candidate_data, cdp_endpoint))
    else:
        run_active_page_apply(args, candidate_data, cdp_endpoint)


if __name__ == "__main__":
    main()
