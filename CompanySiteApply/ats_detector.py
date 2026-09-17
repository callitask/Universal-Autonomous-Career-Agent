# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 23:00:00 +05:30
# Issue / Context: ATS Platform detection and signature inspection engine.
# Changes Made: Implemented ATSDetector to classify live pages and identify anti-bot traps.
# Rationale: Provides fast, deterministic ATS identification before dispatching to specific finger.
# Preventative Notes: Scans for honeypot markers alongside platform signatures.
# ==============================================================================

from typing import Any, Dict, Tuple
from CompanySiteApply.fingers import get_finger_for_page
from CompanySiteApply.utils.honeypot_guard import HoneypotGuard


class ATSDetector:
    """
    Detector and inspector for enterprise ATS platforms and career pages.
    """

    @classmethod
    def detect_platform(cls, page: Any) -> Dict[str, Any]:
        """
        Analyzes the active browser page and returns platform classification and trap status.
        """
        finger, confidence, variant = get_finger_for_page(page)
        url = getattr(page, "url", "")
        title = ""
        try:
            title = page.title()
        except Exception:
            pass

        # Check for honeypots on page
        honeypot_count = 0
        honeypot_names = []
        try:
            inputs = page.locator("input").all()
            for inp in inputs:
                elem_info = {
                    "name": inp.get_attribute("name"),
                    "id": inp.get_attribute("id"),
                    "style": inp.get_attribute("style") or "",
                    "is_visible": inp.is_visible()
                }
                if HoneypotGuard.is_honeypot(elem_info):
                    honeypot_count += 1
                    honeypot_names.append(elem_info.get("name") or elem_info.get("id"))
        except Exception:
            pass

        return {
            "platform_name": finger.platform_name,
            "platform_variant": variant,
            "confidence": round(confidence, 2),
            "url": url,
            "title": title,
            "honeypots_detected": honeypot_count,
            "honeypot_identifiers": honeypot_names,
            "finger_class": finger.__class__.__name__
        }
