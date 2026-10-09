# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [SIGNATURE_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:45:50 +05:30
# Issue / Context: Isolating terms, agreement, and legal signature into a dedicated sub-agent.
# Changes Made: Built SignatureSubAgent handling Full Name E-Signature and optional LinkedIn URL.
# Rationale: Guarantees full legal signature compliance without touching documents or diversity inputs.
# Preventative Notes: Never leave e-signature blank.
# ==============================================================================

import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class SignatureSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Section 4 E-Signature, Agreements, and Profile Links.
    """

    @property
    def section_name(self) -> str:
        return "signature"

    @property
    def target_stage(self) -> str:
        return "section_4"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/4" in url or "review" in url.lower() or "more-about-you" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sig_input = page.locator("input[name='fullName']:visible, input[id^='fullName']:visible").first
            has_sig = sig_input.count() > 0 and bool(sig_input.input_value().strip())

            return {
                "is_valid": has_sig,
                "has_signature": has_sig
            }
        except Exception as e:
            logger.error(f"[SignatureSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            full_name = str(cand.get("full_name") or f"{cand.get('first_name', '')} {cand.get('last_name', '')}").strip()
            linkedin_url = str(cand.get("linkedin_profile_url") or cand.get("linkedin_url") or cand.get("linkedin") or "").strip()

            # 1. LinkedIn link
            link_input = page.locator("input[name*='siteLink']:visible, input[id*='siteLink']:visible").first
            if link_input.count() > 0 and not link_input.input_value().strip() and linkedin_url:
                link_input.fill(linkedin_url)
                link_input.dispatch_event("input")
                link_input.dispatch_event("change")

            # 2. E-Signature Full Name
            sig_input = page.locator("input[name='fullName']:visible, input[id^='fullName']:visible").first
            if sig_input.count() > 0 and not sig_input.input_value().strip() and full_name:
                sig_input.fill(full_name)
                sig_input.dispatch_event("input")
                sig_input.dispatch_event("change")

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[SignatureSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False
