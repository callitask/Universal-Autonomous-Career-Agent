# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:47:00 +05:30
# Issue / Context: Anti-bot honeypot detection and safety layer.
# Changes Made: Implemented HoneypotGuard to detect and flag honeypot inputs across ATS portals.
# Rationale: Enterprise ATSs (like Oracle Cloud HCM) embed decoy inputs (e.g. input[name="honey-pot"]) to detect automated scrapers. Filling them causes instant silent rejection.
# Preventative Notes: Never fill flagged honeypot elements under any circumstances.
# [ENTRY #002]
# Term: [FALSE_POSITIVE_FIX]
# Timestamp: 2026-09-23 14:30:00 +05:30
# Issue / Context: Any display:none/opacity:0 field was flagged, hiding legit
#   file inputs, CSRF tokens, and framework-managed fields (valid fields skipped).
# Changes Made: Hidden styling alone no longer flags. Requires honeypot name/id
#   pattern OR (hidden + suspicious off-screen/tabindex/aria signal). File and
#   CSRF inputs are explicitly exempt.
# Rationale: Precision over recall; never skip valid fields.
# Preventative Notes: Keep HONEYPOT_NAME_PATTERNS as primary signal.
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

        # 2. Hidden styling alone is NOT a honeypot (file inputs, CSRF, frameworks
        # legitimately hide fields). Only flag when combined with suspicious signals.
        input_type = str(element_info.get("type") or "").lower()
        if input_type in ("file", "hidden"):
            # file inputs are often opacity:0 by design; hidden inputs hold CSRF tokens.
            # Only flag if name/id explicitly matches a honeypot pattern (handled above).
            return False
        style_l = style.lower()
        hidden_style = any(
            s in style_l
            for s in ("display: none", "display:none", "visibility: hidden",
                      "visibility:hidden", "opacity: 0", "opacity:0",
                      "left: -999", "top: -999")
        )
        if not hidden_style and not element_info.get("aria_hidden") in (True, "true"):
            if not (tabindex in (-1, "-1") and not is_visible):
                return False
        # Hidden + suspicious: off-screen position, aria-hidden, or negative tabindex
        # combined with a generic decoy-looking name counts; plain hidden does not.
        if hidden_style:
            suspicious_name = bool(re.search(r"trap|decoy|honey|hp|bot|spam|verify.*url|confirm.*email", f"{name} {elem_id}", re.I))
            offscreen = ("-999" in style_l) or (element_info.get("aria_hidden") in (True, "true")) or (tabindex in (-1, "-1"))
            return bool(suspicious_name or offscreen)
        if element_info.get("aria_hidden") in (True, "true"):
            return tabindex in (-1, "-1") or not is_visible
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
