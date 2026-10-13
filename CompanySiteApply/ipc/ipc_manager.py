# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [IPC_MANAGER_INIT]
# Timestamp: 2026-10-12 19:55:00 +05:30
# Issue / Context: AG Brain IPC handshake bus for section-by-section question resolution.
#                  Scripts write questions → Brain answers → Scripts fill DOM.
# Changes Made: Created IPCManager with write_questions(), read_answers(), set_status(), reset().
#               Implements atomic JSON writes via safe_write_json pattern (GATE 6 compliant).
# Rationale: Decouples semantic answer resolution (AG Brain) from DOM actuation (scripts).
#            Enables section/subsection independence, conditional question rescans, and
#            surgical re-run of only failing subsections.
# Preventative Notes: Never let scripts populate questions[].answer — only AG Brain writes answers.
#                     Never cross-import this module into core/ — GATE 9 (subsystem isolation).
# ==============================================================================

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# IPC directory relative to this file's location (CompanySiteApply/ipc/)
_IPC_DIR = Path(__file__).parent
_IPC_FILE = _IPC_DIR / "section_question.json"
_IPC_ERROR_LOG = _IPC_DIR / "ipc_error.log"

# Status constants — never use raw strings in scripts; import from here
STATUS_IDLE = "IDLE"
STATUS_QUESTION_READY = "QUESTION_READY"
STATUS_ANSWER_REQUIRED = "ANSWER_REQUIRED"
STATUS_ANSWERED = "ANSWERED"
STATUS_DONE = "DONE"
STATUS_ERROR = "ERROR"

# Timeout seconds for script to wait for ANSWERED status from AG Brain
ANSWER_TIMEOUT_SECONDS = 120
# Poll interval seconds
POLL_INTERVAL_SECONDS = 1.5


class IPCManager:
    """
    IPC Message Bus between Playwright section scripts and AG Brain (Antigravity 2.0).

    Usage by a script:
        ipc = IPCManager(session_id, job_id, profile, "section_2", "binary_questions")
        ipc.write_questions([{...}, {...}])          # Writes + sets ANSWER_REQUIRED
        answers = ipc.wait_for_answers()             # Blocks until AG Brain responds
        ipc.mark_done()                              # Sets script_done=True, status=IDLE

    Usage by AG Brain (orchestrator):
        ipc = IPCManager.from_file()
        data = ipc.read()
        # Populate data["questions"][i]["answer"] for each question
        ipc.write_raw(data, status=STATUS_ANSWERED)
    """

    def __init__(
        self,
        session_id: str,
        job_id: str,
        profile: str,
        section: str,
        subsection: str,
        page_number: int = 1,
    ):
        self.session_id = session_id
        self.job_id = job_id
        self.profile = profile
        self.section = section
        self.subsection = subsection
        self.page_number = page_number

    # ------------------------------------------------------------------
    # SCRIPT-SIDE METHODS (called by Playwright actuator scripts)
    # ------------------------------------------------------------------

    def write_questions(self, questions: List[Dict[str, Any]]) -> None:
        """
        Script writes discovered questions to IPC and sets status=ANSWER_REQUIRED.
        AG Brain will read this and populate answers.

        Each question dict must contain:
            q_id (str): unique ID e.g. "q_001"
            question_text (str): verbatim form question
            field_type (str): one of BINARY_PILL | RADIO_CHIP | RADIO_BUTTON |
                              DROPDOWN | COMBOBOX | CHECKBOX | TEXT | TEXTAREA | FILE_UPLOAD
            available_choices (list): option texts available on the DOM (empty for TEXT/TEXTAREA)
            current_value: current DOM value or None
            is_conditional (bool): True if this question appeared after other answers
            trigger_question (str|None): question_text that triggered this one
            trigger_value (str|None): value selected that triggered this one
            is_required (bool): True if field is marked required in the DOM
        """
        payload = self._build_payload(questions, status=STATUS_ANSWER_REQUIRED)
        self._atomic_write(payload)
        logger.info(
            f"[IPCManager] Wrote {len(questions)} question(s) for "
            f"{self.section}/{self.subsection} — status=ANSWER_REQUIRED"
        )

    def wait_for_answers(self, timeout: int = ANSWER_TIMEOUT_SECONDS) -> List[Dict[str, Any]]:
        """
        Blocks until AG Brain sets status=ANSWERED or timeout expires.
        Returns the list of question dicts (now with .answer populated).
        Raises TimeoutError on expiry.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self._safe_read()
            if data and data.get("status") == STATUS_ANSWERED:
                logger.info(
                    f"[IPCManager] Answers received for {self.section}/{self.subsection}."
                )
                return data.get("questions", [])
            time.sleep(POLL_INTERVAL_SECONDS)

        # Timeout — write error state
        self._write_error(f"Timeout after {timeout}s waiting for ANSWERED status.")
        raise TimeoutError(
            f"[IPCManager] AG Brain did not answer within {timeout}s "
            f"for {self.section}/{self.subsection}."
        )

    def mark_done(self) -> None:
        """Script signals fill pass is complete. Sets script_done=True, status=IDLE."""
        data = self._safe_read() or {}
        data["script_done"] = True
        data["status"] = STATUS_IDLE
        self._atomic_write(data)
        logger.info(f"[IPCManager] Marked subsection {self.subsection} as done.")

    def reset(self) -> None:
        """Resets IPC to IDLE state. Call at start of each new subsection."""
        payload = self._build_payload([], status=STATUS_IDLE)
        payload["script_done"] = False
        payload["error"] = None
        payload["timestamp_answered"] = None
        self._atomic_write(payload)
        logger.debug(f"[IPCManager] Reset for {self.section}/{self.subsection}.")

    # ------------------------------------------------------------------
    # AG BRAIN-SIDE METHODS (called by orchestrator / AIBrainResolver)
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls) -> "IPCManager":
        """
        Create an IPCManager instance from the current IPC file.
        Used by AG Brain to read the active session's context.
        """
        data = cls._static_read()
        inst = cls(
            session_id=data.get("session_id", ""),
            job_id=data.get("job_id", ""),
            profile=data.get("profile", ""),
            section=data.get("section", ""),
            subsection=data.get("subsection", ""),
            page_number=data.get("page_number", 1),
        )
        return inst

    def read(self) -> Optional[Dict[str, Any]]:
        """Read current IPC state. Used by AG Brain to get questions to answer."""
        return self._safe_read()

    def write_answers(self, answered_questions: List[Dict[str, Any]]) -> None:
        """
        AG Brain populates answers and sets status=ANSWERED.
        answered_questions: same list as from read(), with .answer filled in.
        """
        data = self._safe_read() or self._build_payload([], STATUS_IDLE)
        data["questions"] = answered_questions
        data["status"] = STATUS_ANSWERED
        data["timestamp_answered"] = datetime.now(timezone.utc).isoformat()
        self._atomic_write(data)
        logger.info(
            f"[IPCManager] AG Brain wrote answers for {data.get('section')}/{data.get('subsection')}."
        )

    def write_raw(self, data: Dict[str, Any], status: Optional[str] = None) -> None:
        """Write arbitrary IPC payload. Optionally override status."""
        if status:
            data["status"] = status
        self._atomic_write(data)

    # ------------------------------------------------------------------
    # STATUS HELPERS
    # ------------------------------------------------------------------

    def get_status(self) -> str:
        data = self._safe_read()
        return data.get("status", STATUS_IDLE) if data else STATUS_IDLE

    def is_answer_required(self) -> bool:
        return self.get_status() == STATUS_ANSWER_REQUIRED

    def is_answered(self) -> bool:
        return self.get_status() == STATUS_ANSWERED

    def is_error(self) -> bool:
        return self.get_status() == STATUS_ERROR

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _build_payload(self, questions: List[Dict[str, Any]], status: str) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "job_id": self.job_id,
            "profile": self.profile,
            "section": self.section,
            "subsection": self.subsection,
            "page_number": self.page_number,
            "status": status,
            "questions": questions,
            "script_done": False,
            "timestamp_written": datetime.now(timezone.utc).isoformat(),
            "timestamp_answered": None,
            "error": None,
        }

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """Atomic JSON write — writes to .tmp then renames to avoid partial reads."""
        tmp_path = _IPC_FILE.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            tmp_path.replace(_IPC_FILE)
        except Exception as e:
            logger.error(f"[IPCManager] Write error: {e}")
            _IPC_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _IPC_ERROR_LOG.open("a", encoding="utf-8") as f:
                f.write(f"[{datetime.now(timezone.utc).isoformat()}] WRITE_ERROR: {e}\n")
            raise

    def _write_error(self, message: str) -> None:
        data = self._safe_read() or self._build_payload([], STATUS_IDLE)
        data["status"] = STATUS_ERROR
        data["error"] = message
        self._atomic_write(data)
        _IPC_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _IPC_ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {self.section}/{self.subsection}: {message}\n")

    def _safe_read(self) -> Optional[Dict[str, Any]]:
        return self._static_read()

    @staticmethod
    def _static_read() -> Optional[Dict[str, Any]]:
        try:
            if not _IPC_FILE.exists():
                return None
            return json.loads(_IPC_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


def new_session_id() -> str:
    """Generate a fresh session UUID for use at orchestrator startup."""
    return str(uuid.uuid4())


def get_effective_session_id(candidate_data: Optional[Dict[str, Any]], explicit: Optional[str] = None) -> str:
    """
    Resolve the IPC session id with orchestrator correlation.

    Priority: explicit arg > candidate_data["_ipc_session_id"] > candidate_data["session_id"] > fallback.
    Orchestrator.run() injects _ipc_session_id into candidate_data so every
    downstream script shares one session instead of per-script sess_* placeholders.
    """
    if explicit:
        return explicit
    if isinstance(candidate_data, dict):
        for key in ("_ipc_session_id", "session_id", "ipc_session_id"):
            val = candidate_data.get(key)
            if val:
                return str(val)
    return ""


def build_question(
    q_id: str,
    question_text: str,
    field_type: str,
    available_choices: Optional[List[str]] = None,
    current_value: Any = None,
    is_conditional: bool = False,
    trigger_question: Optional[str] = None,
    trigger_value: Optional[str] = None,
    is_required: bool = True,
) -> Dict[str, Any]:
    """
    Helper to build a well-formed question dict for write_questions().
    Enforces the canonical IPC schema — use this in all scripts.

    field_type values:
        BINARY_PILL       — Yes/No pill buttons (2 options)
        RADIO_CHIP        — Multi-option chip group (3+ options, single select)
        RADIO_PILL        — Alias for RADIO_CHIP (competency pills)
        RADIO_BUTTON      — Standard <input type=radio> group
        DROPDOWN          — <select> or Oracle JET oj-select-single (single select)
        DROPDOWN_MULTI    — Multi-select combobox (choose N)
        COMBOBOX          — Oracle JET oj-combobox (type-ahead with listbox)
        CHECKBOX          — <input type=checkbox> (boolean / multi)
        TEXT              — <input type=text> (free text)
        TEXTAREA          — <textarea> (multi-line free text)
        FILE_UPLOAD       — File attachment input
        REVIEW_READBACK   — Structured DOM readback dict (visual verifier only)
    """
    return {
        "q_id": q_id,
        "question_text": question_text,
        "field_type": field_type,
        "available_choices": available_choices or [],
        "current_value": current_value,
        "is_conditional": is_conditional,
        "trigger_question": trigger_question,
        "trigger_value": trigger_value,
        "is_required": is_required,
        "answer": None,
        "answer_confidence": None,
        "answer_rationale": None,
    }
