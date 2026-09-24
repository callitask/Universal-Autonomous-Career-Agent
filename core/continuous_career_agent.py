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
# Term: [DAEMON_ORCHESTRATION]
# Timestamp: 2026-09-09 12:00:00 +05:30
# Issue / Context: Running individual scripts manually was inefficient for continuous background operation.
# Changes Made: Built infinite daemon loop executing Cycle: Discovery -> Match Evaluation -> Tailoring -> Resume Injection -> Application -> Ledger Update.
# Rationale: Fully autonomous multi-hour application runs.
# Preventative Notes: Ensure inter-cycle delay prevents portal rate-limiting.
#
# [ENTRY #002]
# Term: [TELEMETRY_LOGGING]
# Timestamp: 2026-09-13 10:20:00 +05:30
# Issue / Context: Lack of cycle-by-cycle telemetry made diagnosing starvation bottlenecks difficult.
# Changes Made: Added execution telemetry recording to profiles/<profile>/output/logs/terminal_execution_log.txt and logs_dump.txt.
# Rationale: Enables AG Brain autonomous monitoring and self-healing.
# Preventative Notes: Ensure logging handles missing directories gracefully without crashing.
#
# [ENTRY #003]
# Term: [DAEMON_MODE_ENVIRONMENT_EXPORT]
# Timestamp: 2026-09-14 17:00:00 +05:30
# Issue / Context: Background execution of discovery pipeline required autonomous fast heuristic scoring without 25s IPC timeout delays.
# Changes Made: Injected os.environ["DAEMON_MODE"] = "1" at top of daemon orchestrator.
# Rationale: Guarantees child discovery processes evaluate job fit instantaneously using calibrated semantic models.
# Preventative Notes: Always ensure daemon processes propagate DAEMON_MODE=1 to subprocesses.
#   NOTE (2026-09-20): DAEMON_MODE=1 no longer bypasses AI evaluation (Claude audit fix). It is
#   kept as an env variable for legacy compatibility but has no functional effect on scoring.
#
# [ENTRY #004]
# Term: [BATCH_ARCH_V2_ORCHESTRATION]
# Timestamp: 2026-09-20 19:55:00 +05:30
# Issue / Context: Batch Architecture v2.0 changes each daemon cycle to process ONE designation.
#   SearchStateManager tracks which designation to search next, rotating automatically.
#   Each cycle: collect cards → AG Brain batch eval → apply approved cards → rotate.
# Changes Made: Added cycle logging for active designation from search_state.json.
#   No structural changes to orchestration loop — discovery script itself handles rotation.
#   DAEMON_MODE=1 kept for env compat but no longer bypasses AI scoring.
# Rationale: Each daemon cycle = one designation = one batch IPC call. Clean, observable, debuggable.
# Preventative Notes: Do NOT set a very short --delay between cycles during batch IPC wait.
#   The batch IPC has a 120s timeout by default. Set --delay >= 60s so AG Brain has time.
#   Rotation state is in search_state.json — do NOT reset it manually between cycles.
# ================================================================================
"""
continuous_career_agent.py
Universal Master Orchestrator Daemon
Zero hardcoded profiles, paths, or settings.
"""

import os
import time
import argparse
import subprocess
import logging
import sys
from pathlib import Path

os.environ["DAEMON_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] continuous_career_agent - %(message)s')
logger = logging.getLogger("continuous_career_agent")

CORE_DIR = Path(__file__).resolve().parent
BASE_DIR = CORE_DIR.parent

import urllib.request

sys.path.insert(0, str(BASE_DIR))
from core.utils.profile_context import ProfileContext

def check_cdp_status(cdp_url: str):
    try:
        urllib.request.urlopen(f"{cdp_url.rstrip('/')}/json/version", timeout=2)
        logger.info(f"  [PRE-FLIGHT] Chrome CDP reachable at {cdp_url}")
        return True
    except Exception as e:
        logger.warning(
            f"  [PRE-FLIGHT NOTICE] Chrome CDP not responding at {cdp_url}. "
            f"Please ensure Chrome is launched with '--remote-debugging-port=9222'. Detail: {e}"
        )
        return False

def run_step(step_name, script_name, profile_arg, ctx=None):
    msg = f"---> [DAEMON] Initiating: {step_name}..."
    logger.info(msg)
    if ctx:
        ctx.append_execution_log(msg)
    try:
        script_path = str(CORE_DIR / script_name)
        cmd = [sys.executable, script_path, "--profile", profile_arg]
        subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
        done_msg = f"---> [DAEMON] {step_name} completed successfully."
        logger.info(done_msg)
        if ctx:
            ctx.append_execution_log(done_msg)
        return True
    except subprocess.CalledProcessError as err:
        err_msg = f"---> [DAEMON] {step_name} exited with error code {err.returncode}. Proceeding to next step."
        logger.error(err_msg)
        if ctx:
            ctx.append_execution_log(err_msg)
        return False

def main():
    parser = argparse.ArgumentParser(description="Continuous Universal Career Agent")
    parser.add_argument("--profile", default=None, help="Profile path (e.g., profiles/<profile_name>)")
    parser.add_argument("--analyze", action="store_true", help="Run AI Profile Analyzer to synthesize cognitive profile from resume")
    parser.add_argument("--sync-profile", action="store_true", help="Sync Naukri & LinkedIn profile info once")
    parser.add_argument("--delay", type=int, default=30, help="Seconds to sleep between full batch cycles")
    args = parser.parse_args()

    # Dynamic Profile Resolution
    ctx = ProfileContext(args.profile, BASE_DIR)
    profile_arg = str(ctx.profile_path)
    cycle = 1

    logger.info("=========================================================")
    logger.info("  [DAEMON] CONTINUOUS UNIVERSAL CAREER AGENT ENGAGED")
    logger.info(f"  [ACTIVE PROFILE]  {ctx.profile_path.name}")
    logger.info("=========================================================")

    # Guardrail P1: Pre-flight Codebase Purity Verification
    try:
        ctx.verify_codebase_purity()
    except Exception as purity_err:
        logger.error(f"[SECURITY HALT] {purity_err}")
        sys.exit(1)

    # Pre-flight Chrome CDP Check — abort if Chrome is not reachable (Fix #14 — 2026-09-23)
    if not check_cdp_status(ctx.cdp_url):
        logger.error(
            "[PREFLIGHT FAIL] Chrome CDP is not reachable. "
            "Start Chrome with --remote-debugging-port before running the daemon. Aborting."
        )
        sys.exit(1)

    # Universal Step 0: Automatic Cognitive Profile Analysis & Resume Comprehension
    cog_model = ctx.load_cognitive_profile()
    if args.analyze or not (cog_model and cog_model.get("candidate_domain") and cog_model.get("core_domain_skills")):
        run_step("Cognitive Profile Analysis & Synthesis", "01_ai_analyzer.py", profile_arg, ctx=ctx)

    if args.sync_profile:
        run_step("Naukri Profile Sync", "02_profile_sync_naukri.py", profile_arg, ctx=ctx)
        run_step("LinkedIn Profile Sync", "03_profile_sync_linkedin.py", profile_arg, ctx=ctx)

    try:
        while True:
            cycle_start = f"\n=================== DAEMON CYCLE #{cycle} ==================="
            logger.info(cycle_start)
            ctx.append_execution_log(cycle_start)

            # Log current rotation state (Batch Arch v2.0 — SearchStateManager)
            try:
                from core.utils.search_state_manager import SearchStateManager
                _sm = SearchStateManager(ctx.profile_path)
                _active = _sm.get_current_designation()
                _idx = _sm.get_current_index()
                _total = len(_sm.get_all_designations())
                _stats = _sm.get_stats()
                logger.info(f"  [ROTATION] Cycle #{cycle}: designation [{_idx}/{_total-1}] = '{_active}'")
                logger.info(f"  [ROTATION] Stats: {_stats}")
                ctx.append_execution_log(f"[ROTATION] Designation: '{_active}' [{_idx}/{_total-1}]")
            except Exception as _rot_err:
                logger.debug(f"  [ROTATION] SearchStateManager not available yet: {_rot_err}")

            # The Interleaved Discovery engine now internally orchestrates tailoring and applying
            run_step("Interleaved Discovery & Application Engine", "04_job_discovery.py", profile_arg, ctx=ctx)

            cycle_done = f"[DAEMON] Cycle #{cycle} complete. Entering {args.delay}-second cooldown before next scan..."
            logger.info(cycle_done)
            ctx.append_execution_log(cycle_done)
            time.sleep(args.delay)
            cycle += 1

    except KeyboardInterrupt:
        logger.info("[STOP] Daemon stopped manually by user.")


if __name__ == "__main__":
    main()