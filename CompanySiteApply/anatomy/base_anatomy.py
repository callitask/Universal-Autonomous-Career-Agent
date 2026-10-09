# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [ATS_ANATOMY_MODEL_INIT]
# Timestamp: 2026-10-09 18:50:00 +05:30
# Issue / Context: Monolithic ATS workflows risked re-executing or corrupting flawless sections
#                  when a single nested field (e.g. Education School) required healing.
# Changes Made: Implemented the Anatomical ATS Hierarchy:
#               - PageBone (Level 2: Skeletal Page/Stage Navigation)
#               - SectionSurface (Level 3: Exposed Organ/Section Boundary)
#               - FormMatrix (Level 4: Nested Modal/Card Tissue)
#               - FieldCell (Level 5: Atomic Field Data/Paint)
# Rationale: Guarantees strict section and modal isolation. When an audit detects an issue
#            in a sub-component, only that specific FormMatrix/FieldCell is surgically repaired.
# Preventative Notes: Never trigger full-page or sibling-section re-runs from a FieldCell failure.
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CellAuditResult:
    """Result of an individual atomic field audit."""
    field_name: str
    is_valid: bool
    current_value: Any
    expected_value: Any
    error_message: Optional[str] = None


@dataclass
class SectionAuditResult:
    """Result of a section-level audit."""
    section_name: str
    is_valid: bool
    cell_results: List[CellAuditResult] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)


class FieldCell(ABC):
    """
    Level 5: The Nail Polish / Cell data.
    Encapsulates atomic field interaction, native event dispatching, and Knockout binding.
    """
    def __init__(self, name: str, selector: str):
        self.name = name
        self.selector = selector

    @abstractmethod
    def read_value(self, page: Any, scope: Any = None) -> Any:
        """Reads back current value from DOM."""
        pass

    @abstractmethod
    def write_value(self, page: Any, value: Any, scope: Any = None) -> bool:
        """Writes value natively into DOM and commits framework observables."""
        pass

    @abstractmethod
    def verify_value(self, page: Any, expected: Any, scope: Any = None) -> bool:
        """Verifies current value matches expected ground truth."""
        pass


class FormMatrix(ABC):
    """
    Level 4: The Nail / Tissue.
    Represents a discrete modal dialog, edit form, or profile tile card.
    """
    @property
    @abstractmethod
    def form_name(self) -> str:
        """Canonical name of this form matrix (e.g., 'EducationModal', 'WorkExperienceTile')."""
        pass

    @abstractmethod
    def is_active(self, page: Any) -> bool:
        """Checks if this form/modal is currently open and visible in DOM."""
        pass

    @abstractmethod
    def open_for_edit(self, page: Any, index: int = 0) -> bool:
        """Opens this discrete card/modal for editing without touching siblings."""
        pass

    @abstractmethod
    def commit_and_save(self, page: Any) -> bool:
        """Commits changes via the form's local SAVE button and waits for closure."""
        pass

    @abstractmethod
    def cancel_or_close(self, page: Any) -> bool:
        """Safely closes form without saving if audit determines no changes needed."""
        pass


class SectionSurface(ABC):
    """
    Level 3: The Exposed Section Surface / Organ.
    Represents an isolated logical area on an ATS page (e.g., EducationSection, ExperienceSection).
    Provides micro-healing isolated strictly to its own boundary.
    """
    @property
    @abstractmethod
    def section_name(self) -> str:
        """Canonical name (e.g., 'Education', 'WorkExperience', 'Diversity')."""
        pass

    @abstractmethod
    def audit(self, page: Any, ground_truth: Dict[str, Any]) -> SectionAuditResult:
        """Audits section data against ground truth without making any modifications."""
        pass

    @abstractmethod
    def heal_isolated(self, page: Any, ground_truth: Dict[str, Any]) -> bool:
        """
        Surgically heals only the missing/corrupted elements within this section.
        MUST NEVER interact with or reorder sibling sections.
        """
        pass


class PageBone(ABC):
    """
    Level 2: The Skeletal Bone / Page Router.
    Represents an ATS page/step (e.g., Section 1 Contact, Section 2 Screening, Section 3 History, Section 4 Review).
    Manages navigation and delegates to child SectionSurfaces.
    """
    @property
    @abstractmethod
    def page_index(self) -> int:
        """Step index (1-based)."""
        pass

    @property
    @abstractmethod
    def page_title(self) -> str:
        """Human-readable page title."""
        pass

    @abstractmethod
    def is_current_page(self, page: Any) -> bool:
        """Checks if browser URL / DOM currently corresponds to this page bone."""
        pass

    @abstractmethod
    def get_sections(self) -> List[SectionSurface]:
        """Returns ordered list of SectionSurfaces present on this page bone."""
        pass

    def audit_all_sections(self, page: Any, ground_truth: Dict[str, Any]) -> List[SectionAuditResult]:
        """Audits all sections sequentially on this page without modifying any data."""
        results = []
        for sec in self.get_sections():
            res = sec.audit(page, ground_truth)
            results.append(res)
        return results
