# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:47:00 +05:30
# Issue / Context: Anti-bot honeypot detection and safety layer.
# Changes Made: Implemented HoneypotGuard to detect and flag honeypot inputs across ATS portals.
# Rationale: Enterprise ATSs (like Oracle Cloud HCM) embed decoy inputs (e.g. input[name="honey-pot"])
#            to detect automated scrapers. Filling them causes instant silent rejection.
# Preventative Notes: Never fill flagged honeypot elements under any circumstances.
# ==============================================================================

import re
from typing import Any, Dict, List, Optional


class HoneypotGuard:
    """
    Guards against anti-bot honeypot fields, hidden trap inputs, and decoy controls.
    """

    # Common honeypot field name/id tokens
    HONEYPOT_NAME_PATTERNS = [
        re.compile(r"honey[-_]?pot", re.IGNORECASE),
        re.compile(r"^hp[-_]", re.IGNORECASE),
        re.compile(r"bot[-_]?trap", re.IGNORECASE),
        re.compile(r"decoy", re.IGNORECASE),
        re.compile(r"^confirm[-_]?email[-_]?secondary$", re.IGNORECASE),
        re.compile(r"^website[-_]?url[-_]?verification$", re.IGNORECASE),
    ]

    @classmethod
    def is_honeypot(cls, element_info: Dict[str, Any]) -> bool:
        """
        Evaluates whether a DOM input/element is a honeypot trap.

        Args:
            element_info: Dictionary containing 'name', 'id', 'class', 'style',
                          'is_visible', 'tabindex', 'aria_hidden'.
        """
        name = element_info.get("name") or ""
        elem_id = element_info.get("id") or ""
        classes = element_info.get("class") or ""
        style = element_info.get("style") or ""
        is_visible = element_info.get("is_visible", True)
        tabindex = element_info.get("tabindex")

        # 1. Direct name/id regex pattern check
        for pat in cls.HONEYPOT_NAME_PATTERNS:
            if pat.search(name) or pat.search(elem_id):
                return True

        # 2. Hidden via inline styling while being an input
        if "display: none" in style.lower() or "display:none" in style.lower():
            return True
        if "visibility: hidden" in style.lower() or "visibility:hidden" in style.lower():
            return True
        if "opacity: 0" in style.lower() or "opacity:0" in style.lower():
            return True
        if "left: -999" in style.lower() or "top: -999" in style.lower():
            return True

        # 3. Off-screen or hidden via aria/tabindex
        if element_info.get("aria_hidden") in (True, "true"):
            return True
        if tabindex in (-1, "-1") and not is_visible:
            return True

        return False

    @classmethod
    def filter_safe_inputs(cls, inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters out honeypot and hidden decoy inputs from a list of candidate inputs.
        """
        safe_inputs = []
        for inp in inputs:
            if cls.is_honeypot(inp):
                continue
            safe_inputs.append(inp)
        return safe_inputs
