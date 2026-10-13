"""
CompanySiteApply IPC package — AG Brain ↔ Section Script message bus.
Import IPCManager and helpers from this package.
"""
from CompanySiteApply.ipc.ipc_manager import (
    IPCManager,
    new_session_id,
    get_effective_session_id,
    build_question,
    STATUS_IDLE,
    STATUS_QUESTION_READY,
    STATUS_ANSWER_REQUIRED,
    STATUS_ANSWERED,
    STATUS_DONE,
    STATUS_ERROR,
)

__all__ = [
    "IPCManager",
    "new_session_id",
    "get_effective_session_id",
    "build_question",
    "STATUS_IDLE",
    "STATUS_QUESTION_READY",
    "STATUS_ANSWER_REQUIRED",
    "STATUS_ANSWERED",
    "STATUS_DONE",
    "STATUS_ERROR",
]
