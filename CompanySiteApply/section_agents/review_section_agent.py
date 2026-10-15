# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [REVIEW_SECTION_AGENT_MODULAR_REFACTOR]
# Timestamp: 2026-10-09 22:46:40 +05:30
# Issue / Context: Section 4 review needed modular decomposition across documents, diversity, signature, and visual proof.
# Changes Made: Refactored ReviewSectionAgent to act as Master Coordinator orchestrating
#               DocumentsSubAgent, DiversitySubAgent, SignatureSubAgent, and VisualVerifierSubAgent.
# Rationale: Guarantees fresh tailored document attachment (removing old files) and strict human gate enforcement.
# Preventative Notes: ABSOLUTELY NEVER CLICK SUBMIT.
#
# [ENTRY #002]
# Term: [DECISION1_BLOCKED_PASSTHROUGH]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Tailoring-block details died inside documents heal output.
# Changes Made: skip_retry/status/blocked_reason/missing_document/error/
#               fix_command lifted into review heal result; other subagents
#               still run before REVIEW_BLOCKED is returned.
# Rationale: One pass fills everything; the gate names the missing document.
# Preventative Notes: Never retry an intentionally skipped upload.
# ==============================================================================
# [ENTRY #002]
# Term: [REVIEW_PREVIEW_COLLISION_FIX]
# Timestamp: 2026-10-12 22:11:00 +05:30
# Issue / Context: Naked 'review' in url matched /jobs/preview/... URLs, causing false-positive section 4 routing.
# Changes Made: Updated can_handle to use '/review' instead of naked 'review'.
# Rationale: Prevents premature routing on preview URLs.
# ==============================================================================

import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.section_agents.sub_agents.documents_subagent import DocumentsSubAgent
from CompanySiteApply.section_agents.sub_agents.diversity_subagent import DiversitySubAgent
from CompanySiteApply.section_agents.sub_agents.signature_subagent import SignatureSubAgent
from CompanySiteApply.section_agents.sub_agents.visual_verifier_subagent import VisualVerifierSubAgent

logger = logging.getLogger(__name__)


class ReviewSectionAgent(BaseSectionAgent):
    """
    Master Coordinator for Section 4: Supporting Documents, Diversity, Signature, and Visual Gate.
    Orchestrates DocumentsSubAgent, DiversitySubAgent, SignatureSubAgent, and VisualVerifierSubAgent.
    Enforces strict, non-negotiable human gate before submission.
    """

    def __init__(
        self,
        docs_subagent: Optional[DocumentsSubAgent] = None,
        diversity_subagent: Optional[DiversitySubAgent] = None,
        signature_subagent: Optional[SignatureSubAgent] = None,
        visual_subagent: Optional[VisualVerifierSubAgent] = None
    ):
        self.docs_subagent = docs_subagent or DocumentsSubAgent()
        self.diversity_subagent = diversity_subagent or DiversitySubAgent()
        self.signature_subagent = signature_subagent or SignatureSubAgent()
        self.visual_subagent = visual_subagent or VisualVerifierSubAgent()

    @property
    def section_name(self) -> str:
        return "review"

    @property
    def target_stage(self) -> str:
        return "section_4"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("section") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/4" in url or "/review" in url.lower() or "more-about-you" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits Section 4 review fields across documents, diversity, signature, and submit readiness.
        """
        try:
            docs_audit = self.docs_subagent.audit(page, candidate_data)
            div_audit = self.diversity_subagent.audit(page, candidate_data)
            sig_audit = self.signature_subagent.audit(page, candidate_data)
            vis_audit = self.visual_subagent.audit(page, candidate_data)

            is_valid = (
                docs_audit.get("is_valid", False) and
                div_audit.get("is_valid", False) and
                sig_audit.get("is_valid", False) and
                vis_audit.get("is_valid", False)
            )

            return {
                "is_valid": is_valid,
                "documents": docs_audit,
                "diversity": div_audit,
                "signature": sig_audit,
                "visual_verification": vis_audit,
                "human_gate_active": True,
                "submit_clicked": False
            }
        except Exception as e:
            logger.error(f"[ReviewSectionAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically heals documents (refreshing to tailored), diversity, and signature.
        STRICTLY HALTS PRIOR TO CLICKING SUBMIT.
        """
        try:
            # 1. Documents (removes old resume/cover letter, attaches fresh tailored versions)
            docs_res = self.docs_subagent.heal(page, candidate_data)
            time.sleep(1.0)

            # 2. Diversity & Demographics
            demographics = candidate_data.get("demographics") or {} if isinstance(candidate_data, dict) else {}
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            ethnicity_val = str(demographics.get("ethnicity") or demographics.get("race") or cand.get("ethnicity") or cand.get("race") or "").strip()
            gender_val = str(demographics.get("gender") or cand.get("gender") or "").strip()
            military_val = str(demographics.get("military_status") or demographics.get("veteran") or cand.get("military_status") or "").strip()

            if ethnicity_val and "decline" not in ethnicity_val.lower():
                self._select_exact_dropdown(page, "ETHNICITY", ethnicity_val)
            if gender_val and "decline" not in gender_val.lower():
                self._select_exact_dropdown(page, "GENDER", gender_val)
            if military_val:
                self._select_exact_dropdown(page, "ATTRIBUTE16", military_val)

            # 3. E-Signature & Agreements
            sig_res = self.signature_subagent.heal(page, candidate_data)
            time.sleep(0.5)

            # 4. Enforce reverse-chronological ordering on Section 4 review tiles.
            # The review screen re-renders backend order on navigation, so the
            # Section 3 sort does not survive the trip. Re-sort HERE and verify
            # from the review DOM — an unverified order fails the gate loudly.
            # Retry: a single pass can lose to a late Knockout re-render.
            order_verified = False
            order_res: Dict[str, Any] = {}
            try:
                from CompanySiteApply.section_agents.scripts.s3_experience_ordering import (
                    reorder_experience_tiles,
                )
                for _attempt in range(1, 4):
                    order_res = reorder_experience_tiles(page)
                    order_verified = bool(order_res.get("order_verified", False))
                    if order_verified:
                        if _attempt > 1:
                            logger.info(f"[ReviewSectionAgent] Review order verified on attempt {_attempt}.")
                        break
                    logger.warning(
                        f"[ReviewSectionAgent] Review reorder attempt {_attempt}/3 unverified: "
                        f"ko={order_res.get('ko_sorted_count')} dom={order_res.get('dom_sorted_count')}."
                    )
                    time.sleep(1.0)
                if not order_verified:
                    logger.warning(f"[ReviewSectionAgent] Order NOT verified on review screen: {order_res}")
            except Exception as re_err:
                logger.debug(f"[ReviewSectionAgent] Experience tile reorder note: {re_err}")

            # 5. Visual Verification & Human Gate
            vis_res = self.visual_subagent.heal(page, candidate_data)

            verified = self.verify(page, candidate_data)
            if not order_verified:
                logger.warning("[ReviewSectionAgent] Halting gate: review-screen order unverified.")
            # Decision 1: surface tailoring-block details; docs intentionally
            # skipped (skip_retry) — other subagents above still ran.
            _out = {
                "success": verified and order_verified,
                "section": self.section_name,
                "documents": docs_res,
                "signature": sig_res,
                "visual": vis_res,
                "order_verified": order_verified,
                "order_detail": {
                    k: order_res.get(k)
                    for k in ("ko_sorted_count", "dom_sorted_count", "order_verified", "tiles_order")
                },
                "human_gate_active": True,
                "submit_clicked": False,
                "verified": verified and order_verified
            }
            if isinstance(docs_res, dict) and docs_res.get("skip_retry"):
                _out["skip_retry"] = True
                for _k in ("status", "blocked_reason", "missing_document",
                           "error", "fix_command"):
                    if docs_res.get(_k) is not None:
                        _out.setdefault(_k, docs_res[_k])
                _out.setdefault("status", "REVIEW_BLOCKED")
            return _out
        except Exception as e:
            logger.error(f"[ReviewSectionAgent] Heal error: {e}")
            return {"success": False, "section": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False

    def _select_exact_dropdown(self, page: Any, partial_id: str, exact_text: str):
        return self.diversity_subagent._select_exact_dropdown(page, partial_id, exact_text)

