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
from run_universal_apply import _resolve_candidate_profile, BLOCKED_STATUSES
from CompanySiteApply.utils.runtime_paths import artifacts_dir as _artifacts_dir


async def main():
    parser = argparse.ArgumentParser(description="Autonomous JPMC Job Search & Evaluation")
    parser.add_argument("--profile", default=None, help="Candidate profile name under profiles/ (auto-discovers if sole live profile)")
    parser.add_argument("--config", default=None, help="Explicit path to candidate_config.json")
    parser.add_argument("--keyword", default=None, help="Optional search keyword override")
    parser.add_argument("--location", default=None, help="Optional location override")
    parser.add_argument("--apply", action="store_true", help="Automatically proceed to tailor and apply to the #1 ranked role")
    parser.add_argument("--cdp-url", default=None, help="CDP endpoint URL (e.g. http://127.0.0.1:9222)")
    args = parser.parse_args()

    profile_slug, cfg_path = _resolve_candidate_profile(args.profile, args.config)
    candidate_data = json.loads(cfg_path.read_text(encoding="utf-8"))
    candidate_data["profile"] = profile_slug

    agent = AutonomousJobAgent(cdp_url=args.cdp_url)

    # Stage 1: Comprehend Profile
    agent.stage_1_comprehend_profile(profile_name=profile_slug, candidate_config=candidate_data)

    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(agent.cdp_url)
        ctx = b.contexts[0]
        portal_pages = [pg for pg in ctx.pages if "oraclecloud.com" in pg.url or "jpmorgan" in pg.url]
        page = portal_pages[0] if portal_pages else (ctx.pages[0] if ctx.pages else await ctx.new_page())

        # Stage 2: Autonomous Search
        eligible_jobs = await agent.stage_2_search_jobs(page, keyword=args.keyword, location=args.location)
        if not eligible_jobs:
            print("[Search & Eval] No eligible unapplied jobs found.")
            return

        # Stage 3: Evaluate & Rank
        ranked_jobs = await agent.stage_3_evaluate_and_rank(page, eligible_jobs, max_evaluations=6)
        
        # Save results to the candidate sandbox (never the repo root)
        from CompanySiteApply.utils.match_report import save_match_report
        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
        out_file = save_match_report(
            resolve_profile_dir(agent.profile_slug) / "output", ranked_jobs
        )
        print(f"\nSaved match report to: {out_file}")

        if args.apply and ranked_jobs:
            best_job = ranked_jobs[0]
            if best_job.get("is_eligible"):
                print(f"\n=== Autonomous Application Triggered for Job {best_job['job_id']}: {best_job['title']} ===")
                # Stage 4: Tailor documents
                tailor_res = agent.stage_4_tailor_documents(best_job)
                if not tailor_res.get("success"):
                    err_msg = tailor_res.get("error") or "Stage 4 cover letter tailoring failed or deferred."
                    fix_cmd = (
                        f"Fix tailoring input/header for job {best_job['job_id']}, re-run Stage 4, then run: "
                        f".venv\\Scripts\\python CompanySiteApply/section_agents/scripts/s4_cover_letter_upload.py "
                        f"--profile {profile_slug} --job-id {best_job['job_id']}"
                    )
                    print(
                        f"[Search & Eval] Stage 4 tailoring failed ({err_msg}). "
                        "Proceeding to fill Sections 1-4 without attaching cover letter; Section 4 will halt as REVIEW_BLOCKED."
                    )
                    best_job["_tailoring_failed"] = True
                    best_job["_tailoring_error"] = err_msg
                    best_job["_skip_document_upload"] = True
                    best_job["_missing_document"] = "cover_letter"
                    best_job["_fix_command"] = fix_cmd
                    if isinstance(agent.candidate_data, dict):
                        agent.candidate_data["_tailoring_failed"] = True
                        agent.candidate_data["_tailoring_error"] = err_msg
                        agent.candidate_data["_skip_document_upload"] = True
                        agent.candidate_data["_missing_document"] = "cover_letter"
                        agent.candidate_data["_fix_command"] = fix_cmd
                # Stage 5: Apply form
                app_res = await agent.stage_5_apply_form(page, best_job, screenshot_dir=_artifacts_dir())
                if not isinstance(app_res, dict):
                    app_res = {"status": "REVIEW_BLOCKED", "raw_result": app_res}
                if best_job.get("_tailoring_failed") and app_res.get("status") not in {"SECTION_BLOCKED", "ORDER_UNVERIFIED"}:
                    app_res["status"] = "REVIEW_BLOCKED"
                    app_res["blocked_reason"] = "TAILORING_BLOCKED"
                    app_res["missing_document"] = best_job.get("_missing_document", "cover_letter")
                    app_res["tailoring_error"] = best_job.get("_tailoring_error")
                    app_res["fix_command"] = best_job.get("_fix_command")
                # Stage 6: Human Gate & Ledger
                gate_res = await agent.stage_6_verify_and_gate(page, best_job, app_res, screenshot_dir=_artifacts_dir())
                if isinstance(gate_res, dict) and app_res.get("status") in BLOCKED_STATUSES:
                    gate_res["status"] = app_res["status"]
                    gate_res["ready_for_submission"] = False
                    gate_res.setdefault("blocked_reason", app_res.get("blocked_reason") or app_res.get("tailoring_error"))
                    gate_res.setdefault("missing_document", app_res.get("missing_document"))
                    gate_res.setdefault("fix_command", app_res.get("fix_command"))
                print("\n[Human Submission Gate Report]:")
                print(json.dumps(gate_res, indent=2))
            else:
                print(f"[Notice] Top job {best_job['job_id']} scored {best_job['score']}/100 and did not meet qualification threshold.")


if __name__ == "__main__":
    asyncio.run(main())
