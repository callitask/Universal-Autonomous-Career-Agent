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

    def __init__(self):
        self.docs_subagent = DocumentsSubAgent()
        self.diversity_subagent = DiversitySubAgent()
        self.signature_subagent = SignatureSubAgent()
        self.visual_subagent = VisualVerifierSubAgent()

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
            return "/apply/section/4" in url or "review" in url.lower() or "more-about-you" in url.lower()
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

            # 4. Visual Verification & Human Gate
            vis_res = self.visual_subagent.heal(page, candidate_data)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "section": self.section_name,
                "documents": docs_res,
                "signature": sig_res,
                "visual": vis_res,
                "human_gate_active": True,
                "submit_clicked": False,
                "verified": verified
            }
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

