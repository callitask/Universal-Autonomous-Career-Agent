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
# [ENTRY #002]
# Term: [PHASE7_STRUCTURED_READBACK_AND_IPC_INTEGRATION]
# Timestamp: 2026-10-12 22:10:00 +05:30
# Issue / Context: AG Brain needed empirical structured DOM readback to verify final application state
#                  alongside screenshot proof.
# Changes Made: Added structured DOM readback extraction (experience tiles, education tiles, documents)
#               and IPC serialization to audit().
# Rationale: Guarantees full cognitive verification before human gate halt.
# Preventative Notes: ABSOLUTELY NEVER CLICK SUBMIT.
# ==============================================================================

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.ipc.ipc_manager import IPCManager, build_question, get_effective_session_id

logger = logging.getLogger(__name__)


class VisualVerifierSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Visual Proof & Human Gate Enforcement.
    Captures full-page screenshots, audits for zero DOM errors, extracts structured DOM readback,
    verifies submit button status, and guarantees human-in-the-loop submission.
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
            return "/apply/section/4" in url or "/review" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            errors = page.evaluate('''() => {
                const errEls = Array.from(document.querySelectorAll('.cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message, [aria-invalid="true"]'));
                return errEls.filter(el => el.offsetWidth > 0 || el.offsetHeight > 0).map(el => el.innerText.trim()).filter(e => e && !e.toLowerCase().includes('saved') && !e.toLowerCase().includes('all set'));
            }''')

            # Structured DOM readback of application state
            readback = page.evaluate('''() => {
                const data = {
                    experience_tiles: [],
                    education_tiles: [],
                    documents: []
                };
                try {
                    const tiles = Array.from(document.querySelectorAll('.apply-flow-profile-item-tile, .cx-tile'));
                    tiles.forEach(t => {
                        const text = t.innerText || '';
                        if (/bachelor|master|degree|education/i.test(text)) {
                            data.education_tiles.push(text.split('\\n').map(s => s.trim()).filter(Boolean));
                        } else {
                            data.experience_tiles.push(text.split('\\n').map(s => s.trim()).filter(Boolean));
                        }
                    });
                    const docBtns = Array.from(document.querySelectorAll('.attachment-upload-button, .attachment-upload-button__download'));
                    docBtns.forEach(b => {
                        data.documents.push((b.innerText || '').trim());
                    });
                } catch (e) {}
                return data;
            }''')

            submit_btn = page.locator("button:has-text('SUBMIT'), input[type='submit']").first
            cnt = submit_btn.count()
            has_submit = cnt > 0 if isinstance(cnt, int) else bool(cnt)
            submit_ready = has_submit and not submit_btn.is_disabled()

            # Pre-submit order gate (incident 2026-10-13): navigating to the
            # review screen re-renders backend (alphabetical) order, discarding
            # any in-session Section 3 sort. The gate is only valid when the
            # REVIEW-screen tiles themselves read back newest-first.
            try:
                from CompanySiteApply.section_agents.scripts.s3_experience_ordering import (
                    is_reverse_chronological,
                    parse_tile_date_text,
                )
                exp_texts = [" ".join(t) for t in readback.get("experience_tiles", [])]
                order_keys = [parse_tile_date_text(t) for t in exp_texts]
                order_ok = bool(exp_texts) and is_reverse_chronological(order_keys)
            except Exception as oe:
                logger.debug(f"[VisualVerifierSubAgent] Order gate note: {oe}")
                order_ok = False
                order_keys = []

            # IPC Serialization
            try:
                job_id = str(candidate_data.get("job_id") or candidate_data.get("_ipc_job_id") or "")
                profile = str(candidate_data.get("profile") or candidate_data.get("_ipc_profile") or "")
                sess = get_effective_session_id(candidate_data if isinstance(candidate_data, dict) else {}, None) or "sess_visual_ver"
                ipc = IPCManager(sess, job_id, profile, "section_4", "visual_verification")
                ipc_q = build_question(
                    q_id="review_summary",
                    question_text="Final Review Summary Readback",
                    field_type="REVIEW_READBACK",
                    available_choices=[],
                    current_value=readback,
                    is_conditional=False,
                    is_required=True
                )
                ipc_q["answer"] = "VERIFIED_READY" if (len(errors) == 0 and submit_ready and order_ok) else "ACTION_REQUIRED"
                ipc.write_questions([ipc_q])
                ipc.write_answers([ipc_q])
                ipc.mark_done()
            except Exception as ie:
                logger.debug(f"[VisualVerifierSubAgent] IPC note: {ie}")

            order_flag = [] if order_ok else ["ORDER_UNVERIFIED: review-screen tiles not newest-first"]
            return {
                "is_valid": len(errors) == 0 and submit_ready and order_ok,
                "errors": errors + order_flag,
                "readback": readback,
                "chronological_order_correct": order_ok,
                "submit_button_ready": submit_ready,
                "human_gate_active": True,
                "submit_clicked": False
            }
        except Exception as e:
            logger.error(f"[VisualVerifierSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Heal the review screen, then audit. Healing here (not only in the
        ReviewSectionAgent coordinator) because the dispatcher routes "review"
        to granular sub-agents — coordinator-only code never executes live
        (incident 210788242: reorder sat dead while the gate tripped).
        """
        order_detail: Dict[str, Any] = {}
        try:
            from CompanySiteApply.section_agents.scripts.s3_experience_ordering import (
                reorder_experience_tiles,
            )
            for _attempt in range(1, 4):
                order_detail = reorder_experience_tiles(page)
                if order_detail.get("order_verified", False):
                    break
                time.sleep(1.0)
        except Exception as re_err:
            logger.debug(f"[VisualVerifierSubAgent] Review reorder note: {re_err}")
        audit_res = self.audit(page, candidate_data)
        return {
            "success": audit_res.get("is_valid", False),
            "subagent": self.section_name,
            "human_gate_active": True,
            "submit_clicked": False,
            "order_detail": {
                k: order_detail.get(k)
                for k in ("ko_sorted_count", "dom_sorted_count", "order_verified")
            },
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
