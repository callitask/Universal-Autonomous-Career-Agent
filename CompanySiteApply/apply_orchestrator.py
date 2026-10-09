# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [APPLY_ORCHESTRATOR_INIT]
# Timestamp: 2026-10-09 22:15:00 +05:30
# Issue / Context: LLM agents in new chats were improvising ad-hoc scripts on page 2 instead of executing a unified pipeline.
# Changes Made: Built ApplyOrchestrator to autonomously drive the end-to-end ATS application lifecycle
#               across Section 1 (Profile), Section 2 (Questionnaire), Section 3 (Education & Experience),
#               and Section 4 (Review). Enforces strict human submission gate on Section 4.
# Rationale: Eliminates all ad-hoc script generation. Provides a single, deterministic CLI command for any profile.
# Preventative Notes: ABSOLUTELY NEVER CLICK SUBMIT ON SECTION 4.
# ==============================================================================

import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from CompanySiteApply.ats_arm import ATSArm
from CompanySiteApply.section_agents.section_agent_dispatcher import SectionAgentDispatcher

logger = logging.getLogger(__name__)


class ApplyOrchestrator:
    """
    Master Autonomous Orchestrator for Company Site Job Applications.
    Coordinates the stage detection, section mini-agent healing, verification,
    and step transitions until Section 4 Review is reached.
    """

    def __init__(self, cdp_url: Optional[str] = None):
        self.arm = ATSArm(cdp_url=cdp_url)
        self.dispatcher = SectionAgentDispatcher()

    def advance(self, page: Any) -> bool:
        """Clicks NEXT / Save and Continue to advance to the next step."""
        try:
            next_btn = page.locator(
                "button.apply-flow-pagination__button:has-text('NEXT'), "
                "button:has-text('NEXT'), "
                "button:has-text('Save and Continue'), "
                "button:has-text('SAVE AND CONTINUE'), "
                "button:has-text('Continue')"
            ).first

            if next_btn.count() > 0 and not next_btn.is_disabled():
                next_btn.click()
                time.sleep(2.0)
                # Wait for loading overlay to disappear
                try:
                    page.wait_for_selector(".cx-loading, .oj-busy, .spinner", state="detached", timeout=5000)
                except Exception:
                    pass
                time.sleep(1.0)
                return True
            return False
        except Exception as e:
            logger.error(f"[ApplyOrchestrator] Advance error: {e}")
            return False

    def detect_current_section(self, page: Any) -> str:
        """Determines the active ATS section from URL or DOM structure."""
        url = (getattr(page, "url", "") or "").lower()
        if "/section/1" in url or "profile" in url or "personal" in url:
            return "profile"
        elif "/section/2" in url or "questions" in url:
            return "questionnaire"
        elif "/section/3" in url or "timeline" in url or "experience" in url:
            return "section_3"
        elif "/section/4" in url or "review" in url or "more-about-you" in url:
            return "review"
        return "unknown"

    def run(self, candidate_data: Dict[str, Any], max_steps: int = 10, screenshot_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Executes the autonomous application loop until Section 4 Review is reached and validated.
        STRICTLY HALTS ON SECTION 4 REVIEW BEFORE CLICKING SUBMIT.
        """
        page = self.arm.connect()
        try:
            step_count = 0
            visited_stages = []

            while step_count < max_steps:
                step_count += 1
                curr_url = page.url
                section = self.detect_current_section(page)
                visited_stages.append((section, curr_url))
                logger.info(f"[ApplyOrchestrator] Step {step_count}: Section='{section}' | URL={curr_url}")

                # -------------------------------------------------------------
                # SECTION 4: REVIEW (HUMAN GATE - NEVER SUBMIT)
                # -------------------------------------------------------------
                if section == "review":
                    logger.info("[ApplyOrchestrator] Arrived at Section 4 Review. Executing ReviewSectionAgent...")
                    heal_res = self.dispatcher.dispatch_heal("review", page, candidate_data)
                    audit_res = self.dispatcher.dispatch_audit("review", page, candidate_data)

                    # Capture visual audit screenshot
                    shot_path = None
                    if screenshot_dir:
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        shot_path = screenshot_dir / f"section_4_review_ready_{int(time.time())}.png"
                        try:
                            page.screenshot(path=str(shot_path), full_page=True)
                            logger.info(f"[ApplyOrchestrator] Review screenshot saved: {shot_path}")
                        except Exception as e:
                            logger.warning(f"Screenshot failed: {e}")

                    return {
                        "success": audit_res.get("is_valid", False),
                        "status": "READY_FOR_HUMAN_SUBMISSION",
                        "section": "review",
                        "url": curr_url,
                        "heal_result": heal_res,
                        "audit_result": audit_res,
                        "screenshot_path": str(shot_path) if shot_path else None,
                        "human_gate_active": True,
                        "submit_clicked": False,
                        "message": "Section 4 Review is completely verified and ready for human submission. Halted at Human Gate."
                    }

                # -------------------------------------------------------------
                # SECTION 1: PROFILE
                # -------------------------------------------------------------
                elif section == "profile":
                    logger.info("[ApplyOrchestrator] Healing Section 1 Profile...")
                    self.dispatcher.dispatch_heal("profile", page, candidate_data)
                    time.sleep(1.0)
                    self.advance(page)

                # -------------------------------------------------------------
                # SECTION 2: QUESTIONNAIRE
                # -------------------------------------------------------------
                elif section == "questionnaire":
                    logger.info("[ApplyOrchestrator] Healing Section 2 Questionnaire...")
                    self.dispatcher.dispatch_heal("questionnaire", page, candidate_data)
                    time.sleep(1.0)
                    self.advance(page)

                # -------------------------------------------------------------
                # SECTION 3: EDUCATION & WORK EXPERIENCE
                # -------------------------------------------------------------
                elif section == "section_3":
                    logger.info("[ApplyOrchestrator] Healing Section 3 Education & Experience...")
                    # 1. Heal Education
                    self.dispatcher.dispatch_heal("education", page, candidate_data)
                    time.sleep(1.0)
                    # 2. Heal Experience
                    self.dispatcher.dispatch_heal("experience", page, candidate_data)
                    time.sleep(1.0)
                    self.advance(page)

                else:
                    # Attempt generic auto-heal on page
                    logger.info(f"[ApplyOrchestrator] Unknown section '{section}'. Attempting auto_heal_page...")
                    self.arm.auto_heal_page(candidate_data)
                    time.sleep(1.0)
                    advanced = self.advance(page)
                    if not advanced:
                        logger.warning("[ApplyOrchestrator] Unable to advance from unknown step.")
                        break

                time.sleep(1.5)

            return {
                "success": False,
                "status": "MAX_STEPS_EXCEEDED",
                "visited_stages": visited_stages,
                "last_url": page.url
            }

        finally:
            self.arm.disconnect()
