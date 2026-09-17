# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-17 13:12:00 +05:30
# Issue / Context: Base contract for Company ATS Nails.
# Changes Made: Defined BaseNail interface providing lifecycle hooks for company-specific
#               questionnaires, custom demographic fields, and workflow adjustments.
# Rationale: Enables clean separation between ATS engine mechanics (Fingers) and company-level
#            business logic (Nails), allowing 100% testable and modular ATS adaptation.
# Preventative Notes: All methods should have sensible no-op defaults so nails only implement overrides.
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseNail(ABC):
    """
    Abstract Base Class for Company-Specific ATS Overrides (Nails).
    Attached to ATS Fingers to handle company-specific screening questions,
    custom form fields, unique modal structures, and demographic surveys.
    """

    @property
    @abstractmethod
    def company_name(self) -> str:
        """The canonical name of the company (e.g., 'JPMorgan Chase', 'Bristlecone')."""
        pass

    @abstractmethod
    def matches(self, url: str, page_title: str = "", page: Any = None) -> bool:
        """
        Determines whether this nail applies to the current career site URL or page context.
        """
        pass

    def handle_pre_step(self, page: Any, step_num: int, context: Dict[str, Any]) -> None:
        """
        Executed immediately upon arriving at a step before generic finger processing.
        """
        pass

    def handle_custom_fields(self, page: Any, step_num: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes company-specific form fields that generic fingers do not handle.
        Returns a dictionary of results/status.
        """
        return {}

    def override_screening_answer(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Provides company-curated answer overrides for screening questionnaires.
        Returns the resolved answer string, or None to fall back to generic finger/brain logic.
        """
        return None

    def handle_post_step(self, page: Any, step_num: int, context: Dict[str, Any]) -> None:
        """
        Executed after fields have been filled on a step before advancing.
        """
        pass
