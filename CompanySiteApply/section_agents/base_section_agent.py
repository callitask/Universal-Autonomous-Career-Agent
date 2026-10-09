# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [BASE_SECTION_AGENT_INIT]
# Timestamp: 2026-10-09 20:35:00 +05:30
# Issue / Context: Monolithic ATS workflows needed decomposition into dedicated, modular section mini-agents.
# Changes Made: Implemented BaseSectionAgent abstract contract defining section_name, target_stage,
#               can_handle, audit, heal, and verify methods.
# Rationale: Guarantees strict section encapsulation and surgical micro-repair capabilities.
# Preventative Notes: Every derived agent must operate exclusively within its designated DOM boundary.
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseSectionAgent(ABC):
    """
    Abstract Base Class for Section-Wise Mini-Agents.
    Each Section Agent encapsulates the complete diagnostic, editing, and healing
    lifecycle for a single logical area of an ATS application (e.g. Education, Experience,
    Questionnaire, Profile, Review).
    """

    @property
    @abstractmethod
    def section_name(self) -> str:
        """Canonical section identifier (e.g. 'education', 'experience', 'questionnaire', 'profile', 'review')."""
        pass

    @property
    @abstractmethod
    def target_stage(self) -> str:
        """Target application step/stage (e.g. 'section_1', 'section_2', 'section_3', 'section_4')."""
        pass

    @abstractmethod
    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        """Determines whether this section agent applies to the current page state or diagnostic context."""
        pass

    @abstractmethod
    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits the section's fields against candidate ground truth.
        Returns a diagnostic report dictionary with 'is_valid' and list of 'issues'.
        MUST BE STRICTLY READ-ONLY.
        """
        pass

    @abstractmethod
    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically repairs any invalid, missing, or misaligned elements within this section.
        MUST NEVER modify or re-order sibling sections.
        """
        pass

    @abstractmethod
    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        """
        Verifies that all fields within this section are 100% compliant and error-free after healing.
        """
        pass
