# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:59:00 +05:30
# Issue / Context: ATS Finger dynamic registry and factory.
# Changes Made: Implemented get_finger_for_page() to arbitrate and instantiate the optimal ATS finger.
# Rationale: Enables 100-day extensibility - new fingers are simply imported and added to FINGER_REGISTRY.
# Preventative Notes: Preserves generic finger as fallback.
# ==============================================================================

from typing import Any, List, Optional, Tuple

from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.fingers.oracle_cloud_finger import OracleCloudFinger
from CompanySiteApply.fingers.workday_finger import WorkdayFinger
from CompanySiteApply.fingers.greenhouse_finger import GreenhouseFinger
from CompanySiteApply.fingers.generic_finger import GenericAdaptiveFinger

# Registry of all specialized ATS fingers in evaluation order
FINGER_REGISTRY: List[type[BaseATSFinger]] = [
    OracleCloudFinger,
    WorkdayFinger,
    GreenhouseFinger,
    # Future fingers (Lever, SmartRecruiters, iCIMS, Ashby, BambooHR) plug in here!
    GenericAdaptiveFinger,  # Always last as fallback
]


def get_finger_for_page(page: Any) -> Tuple[BaseATSFinger, float, str]:
    """
    Evaluates all registered ATS fingers against the active page DOM and URL.
    Returns:
        (best_matching_finger_instance, confidence_score, detected_variant_description)
    """
    url = getattr(page, "url", "")
    best_finger_cls = GenericAdaptiveFinger
    best_score = 0.0
    best_variant = "Generic Fallback"

    for finger_cls in FINGER_REGISTRY:
        try:
            instance = finger_cls()
            matches, confidence, variant = instance.can_handle(page, url)
            if matches and confidence > best_score:
                best_finger_cls = finger_cls
                best_score = confidence
                best_variant = variant
                # If high-confidence match found, break early
                if confidence >= 0.8:
                    break
        except Exception:
            continue

    return best_finger_cls(), best_score, best_variant
