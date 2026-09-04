"""
continuous_career_agent.py
Universal Master Orchestrator Daemon
Zero hardcoded profiles, paths, or settings.
"""

import time
import argparse
import subprocess
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] continuous_career_agent - %(message)s')
logger = logging.getLogger("continuous_career_agent")

CORE_DIR = Path(__file__).resolve().parent
BASE_DIR = CORE_DIR.parent

def run_step(step_name, script_name, profile_arg):
    logger.info(f"---> [DAEMON] Initiating: {step_name}...")
    try:
        script_path = str(CORE_DIR / script_name)
        cmd = [sys.executable, script_path, "--profile", profile_arg]
        subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
        logger.info(f"---> [DAEMON] {step_name} completed successfully.")
        return True
    except subprocess.CalledProcessError:
        logger.error(f"---> [DAEMON] {step_name} exited with error. Proceeding to next step.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Continuous Universal Career Agent")
    parser.add_argument("--profile", required=True, help="Profile path (e.g., profiles/bharat_pandey)")
    parser.add_argument("--analyze", action="store_true", help="Run AI Profile Analyzer to synthesize cognitive profile from resume")
    parser.add_argument("--sync-profile", action="store_true", help="Sync Naukri & LinkedIn profile info once")
    parser.add_argument("--delay", type=int, default=30, help="Seconds to sleep between full batch cycles")
    args = parser.parse_args()

    profile_arg = args.profile
    cycle = 1

    logger.info("=========================================================")
    logger.info("  [DAEMON] CONTINUOUS UNIVERSAL CAREER AGENT ENGAGED")
    logger.info(f"  [ACTIVE PROFILE]  {profile_arg}")
    logger.info("=========================================================")

    if args.analyze:
        run_step("Cognitive Profile Analysis & Synthesis", "01_ai_analyzer.py", profile_arg)

    if args.sync_profile:
        run_step("Naukri Profile Sync", "02_profile_sync_naukri.py", profile_arg)
        run_step("LinkedIn Profile Sync", "03_profile_sync_linkedin.py", profile_arg)

    try:
        while True:
            logger.info(f"\n=================== DAEMON CYCLE #{cycle} ===================")

            # The Interleaved Discovery engine now internally orchestrates tailoring and applying
            run_step("Interleaved Discovery & Application Engine", "04_job_discovery.py", profile_arg)

            logger.info(f"[DAEMON] Cycle #{cycle} complete. Entering {args.delay}-second cooldown before next scan...")
            time.sleep(args.delay)
            cycle += 1

    except KeyboardInterrupt:
        logger.info("[STOP] Daemon stopped manually by user.")

if __name__ == "__main__":
    main()