#!/usr/bin/env python3
"""
Universal Autonomous Career Agent - Application Pipeline Runner.
Runs the end-to-end application lifecycle autonomously using Section Mini-Agents:
- Mode 1 (Autonomous Full Lifecycle): Search -> Evaluate & Match -> Tailor Documents -> Apply -> Gate & Verify
- Mode 2 (Active Page Apply): Runs Section Mini-Agents on the currently open application form.
"""

import sys
import os
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
from CompanySiteApply.utils.runtime_paths import artifacts_dir as _artifacts_dir

BLOCKED_STATUSES = {
    "TAILORING_BLOCKED",
    "SECTION_BLOCKED",
    "REVIEW_BLOCKED",
    "ORDER_UNVERIFIED",
    "ACTION_REQUIRED",
}


def _discover_single_live_profile() -> str:
    """Auto-discover the sole live profile in Operations (or repo fallback), excluding default_user."""
    ops_root = Path(os.environ.get("JOB_AGENT_OPERATIONS", str(ROOT.parent / "Operations JOB AI AGENT")))
    candidates = {}
    for base in (ops_root / "profiles", ROOT / "profiles"):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if (
                d.is_dir()
                and d.name != "default_user"
                and not d.name.startswith(".")
                and (d / "candidate_config.json").exists()
            ):
                candidates.setdefault(d.name, d / "candidate_config.json")
    names = sorted(candidates.keys())
    if len(names) == 0:
        raise RuntimeError(
            "No live candidate profile with candidate_config.json found under Operations or repo profiles/ "
            "(excluding 'default_user'). Pass --profile <slug> or --config <path>."
        )
    if len(names) > 1:
        raise RuntimeError(
            f"Multiple live candidate profiles found ({names}). "
            "Pass --profile <slug> explicitly to disambiguate."
        )
    return names[0]


def _resolve_candidate_profile(profile_arg: str | None, config_arg: str | None) -> tuple[str, Path]:
    from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
    if config_arg:
        cfg_path = Path(config_arg).resolve()
        if not cfg_path.exists():
            raise FileNotFoundError(f"Explicit --config file not found: {cfg_path}")
        profile_slug = (profile_arg or cfg_path.parent.name).strip().replace("\\", "/").split("/")[-1]
        if profile_slug == "default_user":
            raise ValueError("Refusing to run against 'default_user' blueprint profile.")
        return profile_slug, cfg_path
    clean_arg = profile_arg.strip().replace("\\", "/").split("/")[-1] if profile_arg else None
    if clean_arg == "default_user":
        raise ValueError("Refusing to run against 'default_user' blueprint profile.")
    profile_slug = clean_arg or _discover_single_live_profile()
    ops_cfg = resolve_profile_dir(profile_slug) / "candidate_config.json"
    repo_cfg = ROOT / "profiles" / profile_slug / "candidate_config.json"
    if ops_cfg.exists():
        return profile_slug, ops_cfg
    if repo_cfg.exists():
        return profile_slug, repo_cfg
    raise FileNotFoundError(
        f"candidate_config.json not found for profile '{profile_slug}' "
        f"(checked {ops_cfg} and {repo_cfg})."
    )


def run_active_page_apply(args, candidate_data, cdp_endpoint):
    orchestrator = ApplyOrchestrator(cdp_url=cdp_endpoint)
    artifacts_dir = _artifacts_dir()
    
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
    agent.stage_1_comprehend_profile(profile_name=candidate_data["profile"], candidate_config=candidate_data)

    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp(agent.cdp_url)
        ctx = b.contexts[0]
        portal_pages = [pg for pg in ctx.pages if "oraclecloud.com" in pg.url or "jpmorgan" in pg.url]
        page = portal_pages[0] if portal_pages else (ctx.pages[0] if ctx.pages else await ctx.new_page())

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
        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
        out_file = save_match_report(resolve_profile_dir(agent.profile_slug) / "output", ranked_jobs)
        print(f"[Universal Apply Runner] Saved job match report to {out_file}")

        best_job = ranked_jobs[0]
        if not best_job.get("is_eligible"):
            print(f"[Universal Apply Runner] Top job {best_job['job_id']} scored {best_job['score']}/100 - Below eligibility threshold.")
            return {"status": "BELOW_THRESHOLD", "top_job": best_job}

        # Stage 4: Requisition Document Tailoring
        print(f"\n[Universal Apply Runner] Tailoring documents for Job {best_job['job_id']}: {best_job['title']}...")
        tailor_res = agent.stage_4_tailor_documents(best_job)
        if not tailor_res.get("success"):
            err_msg = tailor_res.get("error") or "Stage 4 cover letter tailoring failed or deferred."
            fix_cmd = (
                f"Fix tailoring input/header for job {best_job['job_id']}, re-run Stage 4, then run: "
                f".venv\\Scripts\\python CompanySiteApply/section_agents/scripts/s4_cover_letter_upload.py "
                f"--profile {candidate_data['profile']} --job-id {best_job['job_id']}"
            )
            print(
                f"[Universal Apply Runner] Stage 4 tailoring failed ({err_msg}). "
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

        # Stage 5: Section Mini-Agent Dispatch & Form Application
        print(f"\n[Universal Apply Runner] Applying to Job {best_job['job_id']}...")
        app_res = await agent.stage_5_apply_form(page, best_job, screenshot_dir=_artifacts_dir())
        if not isinstance(app_res, dict):
            app_res = {"status": "REVIEW_BLOCKED", "raw_result": app_res}
        if best_job.get("_tailoring_failed") and app_res.get("status") not in {"SECTION_BLOCKED", "ORDER_UNVERIFIED"}:
            app_res["status"] = "REVIEW_BLOCKED"
            app_res["blocked_reason"] = "TAILORING_BLOCKED"
            app_res["missing_document"] = best_job.get("_missing_document", "cover_letter")
            app_res["tailoring_error"] = best_job.get("_tailoring_error")
            app_res["fix_command"] = best_job.get("_fix_command")

        # Stage 6: Visual Audit, Human Submission Gate & Ledger Persistence
        gate_res = await agent.stage_6_verify_and_gate(page, best_job, app_res, screenshot_dir=_artifacts_dir())
        if isinstance(gate_res, dict) and app_res.get("status") in BLOCKED_STATUSES:
            gate_res["status"] = app_res["status"]
            gate_res["ready_for_submission"] = False
            gate_res.setdefault("blocked_reason", app_res.get("blocked_reason") or app_res.get("tailoring_error"))
            gate_res.setdefault("missing_document", app_res.get("missing_document"))
            gate_res.setdefault("fix_command", app_res.get("fix_command"))
        print("\n[Human Submission Gate Report]:")
        print(json.dumps(gate_res, indent=2))
        return gate_res


def main():
    parser = argparse.ArgumentParser(description="Universal Autonomous Career Agent - Application Runner")
    parser.add_argument("--profile", default=None, help="Profile folder name under profiles/ (auto-discovers if sole live profile)")
    parser.add_argument("--config", default=None, help="Explicit path to candidate_config.json")
    parser.add_argument("--cdp-url", default=None, help="CDP endpoint URL (defaults to env or candidate_config)")
    parser.add_argument("--autonomous", action="store_true", help="Run full autonomous lifecycle (Search -> Match -> Tailor -> Apply -> Gate)")
    parser.add_argument("--keyword", default=None, help="Optional search keyword override for autonomous mode")
    parser.add_argument("--location", default=None, help="Optional search location override for autonomous mode")
    parser.add_argument("--max-eval", type=int, default=5, help="Max jobs to inspect in autonomous mode")
    args = parser.parse_args()

    profile_slug, cfg_path = _resolve_candidate_profile(args.profile, args.config)
    args.profile = profile_slug

    print(f"[Universal Apply Runner] Loading candidate profile from: {cfg_path}")
    candidate_data = json.loads(cfg_path.read_text(encoding="utf-8"))
    candidate_data["profile"] = profile_slug

    cdp_endpoint = args.cdp_url or os.environ.get("CDP_URL") or candidate_data.get("candidate", {}).get("cdp_url") or "http://127.0.0.1:9222"

    if args.autonomous:
        asyncio.run(run_autonomous_lifecycle(args, candidate_data, cdp_endpoint))
    else:
        run_active_page_apply(args, candidate_data, cdp_endpoint)


if __name__ == "__main__":
    main()
