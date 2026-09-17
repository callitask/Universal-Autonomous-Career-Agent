# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:51:00 +05:30
# Issue / Context: ATS parser sentence split and margin wrap healing.
# Changes Made: Implemented LineWrapHealer to detect and repair broken line-wrap sentences in textareas.
# Rationale: Workday and Oracle parsers treat PDF margin line-breaks as hard sentence splits,
#            breaking sentences into fragments or splitting words without spaces.
# Preventative Notes: Preserves authentic bullet points (•, -, numbered lists) and real paragraph boundaries.
# ==============================================================================

import re
from typing import List, Tuple


class LineWrapHealer:
    """
    Detects and repairs line-wrap anomalies in text extracted by ATS parsers (Workday, Oracle, etc.).
    """

    # Characters that denote explicit bullet points
    BULLET_PREFIX_REGEX = re.compile(r"^\s*([•\*\-–—▪▫►✔\u2022\u25cf\u25cb\u25aa]|\d+[\.\)])\s+")

    # Endings that strongly signal continuation rather than sentence termination
    CONTINUATION_ENDINGS = (
        ",", ";", ":", "-", "–", "—", "/", "\\",
        "and", "or", "with", "by", "for", "to", "in", "on", "at", "from", "into", "of",
        "the", "a", "an", "that", "which", "including", "using", "through", "across",
        "as", "well", "via"
    )

    @classmethod
    def heal_text(cls, text: str) -> str:
        """
        Takes raw text populated in an ATS experience description and repairs
        accidental margin line-breaks while preserving legitimate bullet points and paragraphs.
        """
        if not text or not text.strip():
            return text

        lines = [line.rstrip() for line in text.splitlines()]
        if len(lines) <= 1:
            return text

        healed_lines: List[str] = []
        i = 0

        while i < len(lines):
            current_line = lines[i]

            # If current line is empty, preserve paragraph break
            if not current_line.strip():
                healed_lines.append("")
                i += 1
                continue

            # Look ahead to see if subsequent lines are wrapped continuations
            while i + 1 < len(lines):
                next_line = lines[i + 1]

                # If next line is empty, it's a real paragraph break - stop merging
                if not next_line.strip():
                    break

                # If next line explicitly starts with a bullet or number, it's a distinct item
                if cls.BULLET_PREFIX_REGEX.match(next_line):
                    break

                # Evaluate whether next_line is a continuation of current_line
                is_continuation, merge_type = cls._evaluate_continuation(current_line, next_line)
                if is_continuation:
                    current_line = cls._merge_lines(current_line, next_line, merge_type)
                    i += 1
                else:
                    break

            healed_lines.append(current_line)
            i += 1

        return "\n".join(healed_lines)

    @classmethod
    def _evaluate_continuation(cls, prev: str, nxt: str) -> Tuple[bool, str]:
        """
        Determines whether `nxt` is a soft line-wrap continuation of `prev`.
        Returns (is_continuation, merge_type):
          merge_type: 'hyphen' (strip hyphen, join without space),
                      'space' (join with single space)
        """
        prev_clean = prev.strip()
        nxt_clean = nxt.strip()

        if not prev_clean or not nxt_clean:
            return False, "none"

        # Case 1: Word hyphenated at end of line (e.g. "cloud-\nnative" vs "devel-\nopment")
        if prev_clean.endswith("-") and not prev_clean.endswith("--"):
            if re.match(r"^[a-z]", nxt_clean):
                # Check if the token before hyphen is an intentional compound prefix
                token_before_hyphen = prev_clean[:-1].split()[-1].lower() if prev_clean[:-1].split() else ""
                compound_prefixes = {
                    "cloud", "cross", "multi", "real", "high", "low", "full", "open",
                    "event", "large", "client", "server", "front", "back", "end", "state",
                    "object", "domain", "data", "test", "peer", "lead", "sub"
                }
                if token_before_hyphen in compound_prefixes:
                    return True, "keep_hyphen"
                return True, "strip_hyphen"

        # Case 2: Prev line ends with explicit continuation token (comma, conjunction, preposition)
        last_word = prev_clean.split()[-1].lower() if prev_clean.split() else ""
        if prev_clean.endswith((",", ";", "/")) or last_word in cls.CONTINUATION_ENDINGS:
            return True, "space"

        # Case 3: Prev line does NOT end with sentence-ending punctuation (. ! ?)
        # and next line starts with lowercase letter or number/symbol continuation
        has_terminal_punct = prev_clean.endswith((".", "!", "?"))
        starts_with_lower = bool(re.match(r"^[a-z]", nxt_clean))

        if not has_terminal_punct and starts_with_lower:
            return True, "space"

        # Case 4: Prev line does NOT end with terminal punctuation, and length suggests mid-column margin wrap (>45 chars)
        if not has_terminal_punct and len(prev_clean) > 50 and not prev_clean.endswith(":"):
            first_word_next = nxt_clean.split()[0] if nxt_clean.split() else ""
            common_continuation_words = {"to", "for", "with", "and", "or", "in", "on", "at", "by", "from", "as", "via"}
            if first_word_next.lower() in common_continuation_words:
                return True, "space"

        return False, "none"

    @staticmethod
    def _merge_lines(prev: str, nxt: str, merge_type: str) -> str:
        """
        Merges two lines based on detected wrap type.
        """
        prev_stripped = prev.rstrip()
        nxt_stripped = nxt.lstrip()

        if merge_type == "strip_hyphen":
            # Remove trailing hyphen and join directly (e.g. devel- + opment -> development)
            return prev_stripped[:-1] + nxt_stripped
        elif merge_type == "keep_hyphen":
            # Preserve compound hyphen (e.g. cloud- + native -> cloud-native)
            return prev_stripped + nxt_stripped
        else:
            # Join with a single space
            return f"{prev_stripped} {nxt_stripped}"
