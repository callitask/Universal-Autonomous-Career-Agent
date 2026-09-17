# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-17 13:18:00 +05:30
# Issue / Context: Company ATS Nail for Bristlecone on Oracle Cloud HCM.
# Changes Made: Implemented BristleconeNail for Bristlecone Careers portal.
# Rationale: Standardizes company-specific ATS handling across the fleet.
# Preventative Notes: Preserves legacy Bristlecone honeypot & layout traits.
# ==============================================================================

from typing import Any, Dict, List, Optional
from CompanySiteApply.nails.base_nail import BaseNail


class BristleconeNail(BaseNail):
    """
    Company ATS Nail for Bristlecone career portal on Oracle Cloud HCM.
    """

    @property
    def company_name(self) -> str:
        return "Bristlecone"

    def matches(self, url: str, page_title: str = "", page: Any = None) -> bool:
        url_lower = (url or "").lower()
        title_lower = (page_title or "").lower()
        return "bristlecone" in url_lower or "bristlecone" in title_lower

    def handle_custom_fields(self, page: Any, step_num: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def override_screening_answer(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        return None
