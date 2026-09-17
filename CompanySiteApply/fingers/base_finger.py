# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:54:00 +05:30
# Issue / Context: Base abstract contract for all ATS Finger plugins.
# Changes Made: Defined BaseATSFinger interface for platform-specific ATS handlers.
# Rationale: Standardizes can_handle(), inspect(), fill(), advance(), and verify()
#            so any ATS can be plugged in or modified without altering the master dispatcher.
# Preventative Notes: Subclasses must handle honeypot skipping and frame isolation.
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple


class BaseATSFinger(ABC):
    """
    Abstract Base Class for an ATS Finger (Platform Handler).
    Each finger knows the DOM idioms, anti-bot traps, and multi-step flow of one ATS engine.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """The canonical name of this ATS platform (e.g. 'oracle_cloud', 'workday')."""
        pass

    @abstractmethod
    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        """
        Inspects URL, title, and DOM markers to determine if this finger can handle the page.
        Returns:
            (is_supported, confidence_score_0_to_1, detailed_platform_variant)
        """
        pass

    @abstractmethod
    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        """
        Scrapes and catalogs the active form step:
        inputs, textareas, selects, buttons, honeypots, step title/number.
        """
        pass

    @abstractmethod
    def fill_step(self,
                  page: Any,
                  candidate_data: Dict[str, Any],
                  prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Fills fields on the current step using candidate_data.
        If essential data is missing, queries the user via prompt_user_callback.
        Returns execution status report.
        """
        pass

    @abstractmethod
    def advance_step(self, page: Any) -> Tuple[bool, str]:
        """
        Clicks the Next/Continue/Submit button for the current step and verifies progression.
        Returns (success, new_step_identifier_or_error).
        """
        pass

    @abstractmethod
    def is_complete(self, page: Any) -> Tuple[bool, str]:
        """
        Checks if the application has been successfully submitted (confirmation banner / URL change).
        """
        pass
