# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 23:01:00 +05:30
# Issue / Context: Master ATS Arm Orchestrator connecting CDP to pluggable fingers.
# Changes Made: Implemented ATSArm to manage CDP connection, detection, inspection, and step filling.
# Rationale: Acts as the central anatomical arm coordinating all platform fingers and parser doctor.
# Preventative Notes: Preserves active browser contexts; does not terminate user Chrome on exit.
# ==============================================================================

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright

from CompanySiteApply.ats_detector import ATSDetector
from CompanySiteApply.fingers import get_finger_for_page
from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.parser_doctor.review_verifier import ReviewVerifier

INSPECTIONS_DIR = Path(__file__).resolve().parent / "inspections"


class ATSArm:
    """
    The Anatomical Arm coordinating all enterprise ATS application tasks.
    Connects to Chrome via CDP, identifies ATS platform, and delegates to the appropriate finger.
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def connect(self) -> Any:
        """
        Connects over CDP to the active debugging browser session.
        Adopts the active page.
        """
        if not self.playwright:
            self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.connect_over_cdp(self.cdp_url)
        self.context = self.browser.contexts[0]
        # Find the page that is not about:blank or new-tab-page
        self.page = self.context.pages[0]
        for p in self.context.pages:
            if "jpmc.fa.oraclecloud.com" in p.url or "taleo" in p.url:
                self.page = p
                break
        return self.page

    def disconnect(self):
        """
        Safely disconnects Playwright without closing the user's Chrome browser.
        """
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None

    def inspect_active_tab(self, save_snapshot: bool = True) -> Dict[str, Any]:
        """
        Performs deep inspection of active tab:
        1. Classifies ATS platform and honeypots.
        2. Scrapes complete DOM form schema.
        3. Saves schema snapshot to CompanySiteApply/inspections/<platform>/.
        """
        page = self.connect()
        detection = ATSDetector.detect_platform(page)
        finger, confidence, variant = get_finger_for_page(page)
        step_schema = finger.inspect_current_step(page)

        result = {
            "detection": detection,
            "step_schema": step_schema,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if save_snapshot:
            platform_dir = INSPECTIONS_DIR / detection["platform_name"]
            platform_dir.mkdir(parents=True, exist_ok=True)
            step_name = step_schema.get("detected_step", "step")
            filename = f"{step_name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
            snapshot_path = platform_dir / filename
            snapshot_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            result["saved_snapshot_path"] = str(snapshot_path)

        return result

    def fill_and_advance(self,
                         candidate_data: Dict[str, Any],
                         prompt_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Executes active finger's fill_step and advances to the next screen.
        """
        page = self.connect()
        finger, confidence, variant = get_finger_for_page(page)

        fill_report = finger.fill_step(page, candidate_data, prompt_callback)
        if not fill_report.get("success"):
            return {
                "success": False,
                "stage": "fill_step",
                "report": fill_report
            }

        advance_ok, advance_msg = finger.advance_step(page)
        is_done, done_msg = finger.is_complete(page)

        return {
            "success": advance_ok,
            "stage": "advance_step",
            "fill_report": fill_report,
            "advance_message": advance_msg,
            "is_complete": is_done,
            "completion_message": done_msg
        }

    def heal_active_page(self, ground_truth_education: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Directly executes Parser Doctor to fix line wraps and college fields on active tab.
        """
        page = self.connect()
        exp_healed = ReviewVerifier.audit_and_heal_experience_descriptions(page)
        edu_healed = ReviewVerifier.audit_and_heal_education_fields(page, ground_truth_education)
        return {
            "healed_experience": exp_healed,
            "healed_education": edu_healed
        }
