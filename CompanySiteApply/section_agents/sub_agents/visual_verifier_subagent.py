# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [VISUAL_VERIFIER_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:46:20 +05:30
# Issue / Context: Needed independent visual artifact generation and strict Human Gate enforcement.
# Changes Made: Built VisualVerifierSubAgent to capture high-res full page audit screenshots,
#               verify 0 red DOM errors, verify submit readiness, and strictly enforce Human Gate.
# Rationale: Guarantees visual empirical proof of application readiness without automating final submission.
# Preventative Notes: ABSOLUTELY NEVER CLICK SUBMIT.
# ==============================================================================

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class VisualVerifierSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Visual Proof & Human Gate Enforcement.
    Captures full-page screenshots, audits for zero DOM errors, verifies submit button status,
    and guarantees human-in-the-loop submission.
    """

    @property
    def section_name(self) -> str:
        return "visual_verifier"

    @property
    def target_stage(self) -> str:
        return "section_4"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/4" in url or "review" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            errors = page.evaluate('''() => {
                const errEls = Array.from(document.querySelectorAll('.cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message, [aria-invalid="true"]'));
                return errEls.filter(el => el.offsetWidth > 0 || el.offsetHeight > 0).map(el => el.innerText.trim()).filter(e => e && !e.toLowerCase().includes('saved') && !e.toLowerCase().includes('all set'));
            }''')

            submit_btn = page.locator("button:has-text('SUBMIT'), input[type='submit']").first
            submit_ready = submit_btn.count() > 0 and not submit_btn.is_disabled()

            return {
                "is_valid": len(errors) == 0 and submit_ready,
                "errors": errors,
                "submit_button_ready": submit_ready,
                "human_gate_active": True,
                "submit_clicked": False
            }
        except Exception as e:
            logger.error(f"[VisualVerifierSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Visual verifier does not mutate; it audits and captures visual proof artifacts.
        """
        audit_res = self.audit(page, candidate_data)
        return {
            "success": audit_res.get("is_valid", False),
            "subagent": self.section_name,
            "human_gate_active": True,
            "submit_clicked": False,
            "audit": audit_res
        }

    def capture_screenshot(self, page: Any, output_path: Path) -> Path:
        """Captures full-page visual screenshot for human verification."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output_path), full_page=True)
        logger.info(f"[VisualVerifierSubAgent] Full page screenshot captured at: {output_path}")
        return output_path

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
