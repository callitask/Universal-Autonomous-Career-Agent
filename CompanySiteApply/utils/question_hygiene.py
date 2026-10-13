# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [QUESTION_HYGIENE_INIT]
# Timestamp: 2026-10-13 15:30:00 +05:30
# Issue / Context: Scanners fall back to a row's first innerText line when no
#                  label element is found. That line can be an OPTION pill's
#                  own text ("No Prior Experience"), which the brain then
#                  answers with itself and clicks — flipping a correct
#                  single-select pick (incident 210788242).
# Changes Made: drop_option_titled_questions() removes any scanned question
#               whose text matches one of its own available choices.
# Rationale: A question that IS one of its options is scanner garbage, never
#            a real question. Dropping beats mis-answering.
# Preventative Notes: Never invent titles ("Unknown ... Question") to fill
#                     the gap — skip the row and let the audit flag it.
# ==============================================================================

"""Scanner-output hygiene for Section 2 question serialization."""

from __future__ import annotations

from typing import Any, Dict, List


def drop_option_titled_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop scanned questions whose text matches one of their own choices."""
    clean: List[Dict[str, Any]] = []
    for q in questions:
        text = str(q.get("question_text") or "").strip()
        choices = [str(c).strip().lower() for c in (q.get("available_choices") or [])]
        if text and text.lower() in choices:
            continue
        if not text or text.lower().startswith("unknown"):
            continue
        clean.append(q)
    return clean
