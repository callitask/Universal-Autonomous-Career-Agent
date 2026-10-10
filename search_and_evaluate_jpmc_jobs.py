#!/usr/bin/env python3
"""
Autonomous JPMC Career Site Search & Match Evaluator.
100% Config-Driven & Zero Hardcoding:
Uses CognitiveJobMatcher and AutonomousJobAgent to search, evaluate, and rank jobs
dynamically according to any candidate profile metadata and skills taxonomy.
"""

import sys
import json
import argparse
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from CompanySiteApply.autonomous_job_agent import AutonomousJobAgent


async def main():
    parser = argparse.ArgumentParser(description="Autonomous JPMC Job Search & Evaluation")
    parser.add_argument("--profile", default=None, help="Candidate profile name under profiles/")
    parser.add_argument("--keyword", default=None, help="Optional search keyword override")
    parser.add_argument("--location", default=None, help="Optional location override")
    parser.add_argument("--apply", action="store_true", help="Automatically proceed to tailor and apply to the #1 ranked role")
    parser.add_argument("--cdp-url", default=None, help="CDP endpoint URL (e.g. http://127.0.0.1:9222)")
    args = parser.parse_args()

    agent = AutonomousJobAgent(cdp_url=args.cdp_url)
    
    # Stage 1: Comprehend Profile
    agent.stage_1_comprehend_profile(profile_name=args.profile)

    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(agent.cdp_url)
        page = b.contexts[0].pages[0]

        # Stage 2: Autonomous Search
        eligible_jobs = await agent.stage_2_search_jobs(page, keyword=args.keyword, location=args.location)
        if not eligible_jobs:
            print("[Search & Eval] No eligible unapplied jobs found.")
            return

        # Stage 3: Evaluate & Rank
        ranked_jobs = await agent.stage_3_evaluate_and_rank(page, eligible_jobs, max_evaluations=6)
        
        # Save results to inspection json
        out_file = REPO_ROOT / "jpmc_job_matches.json"
        out_file.write_text(json.dumps(ranked_jobs, indent=2), encoding="utf-8")
        print(f"\nSaved match report to: {out_file}")

        if args.apply and ranked_jobs:
            best_job = ranked_jobs[0]
            if best_job.get("is_eligible"):
                print(f"\n=== Autonomous Application Triggered for Job {best_job['job_id']}: {best_job['title']} ===")
                # Stage 4: Tailor documents
                agent.stage_4_tailor_documents(best_job)

                # Stage 5: Apply form
                app_res = await agent.stage_5_apply_form(page, best_job)

                # Stage 6: Human Gate & Ledger
                gate_res = await agent.stage_6_verify_and_gate(page, best_job, app_res)
                print("\n[Human Submission Gate Report]:")
                print(json.dumps(gate_res, indent=2))
            else:
                print(f"[Notice] Top job {best_job['job_id']} scored {best_job['score']}/100 and did not meet qualification threshold.")


if __name__ == "__main__":
    asyncio.run(main())
