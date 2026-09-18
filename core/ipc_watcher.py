# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# [ENTRY #001]
# Term: [IPC_WATCHER_AG_BRAIN_NATIVE]
# Timestamp: 2026-09-17 21:15:00 +05:30
# Issue / Context: IPC resolver incorrectly tried to call external Gemini API.
#   Architecture states: AG Brain (Antigravity 2.0) IS the intelligence.
#   No external API calls needed. The watcher is a pure signal relay.
# Changes Made: Watcher polls pending_question.json every 2s. On PENDING,
#   prints a loud structured block to stdout for AG Brain to read.
#   AG Brain reads task log, generates answer, writes it back via tool call.
#   Zero API calls. Zero hardcoding. Pure IPC relay.
# Preventative Notes: Never call external AI APIs from this script.
#   This script has zero intelligence - it is a signal relay only.
# ================================================================================

"""
IPC WATCHER - AG Brain Signal Relay
====================================
Polls pending_question.json every 2 seconds.
When PENDING detected: prints loud structured block to stdout.
AG Brain (running in Antigravity 2.0) reads it, generates answer,
writes answer back to pending_question.json via run_command tool.

NO external API calls. NO hardcoded data. Pure relay.

Usage:
    python core/ipc_watcher.py --profile profiles/TARGET_PROFILE
"""

import os, sys, json, time, argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def ts():
    return datetime.now().strftime('%H:%M:%S')


def print_pending_block(data: dict):
    """Print a loud, structured, clearly-parseable block for AG Brain to action."""
    sep = "=" * 72
    q   = data.get('question', '')
    typ = data.get('task_type', 'QUESTIONNAIRE')
    ctrl= data.get('control_type', 'TEXT')
    opts= data.get('options') or []
    mc  = data.get('max_characters')
    prompt = data.get('prompt', '')

    print(sep, flush=True)
    print(f"[IPC-WATCHER {ts()}] *** AG BRAIN ACTION REQUIRED ***", flush=True)
    print(sep, flush=True)
    print(f"TASK_TYPE    : {typ}", flush=True)
    print(f"CONTROL_TYPE : {ctrl}", flush=True)
    if mc:
        print(f"MAX_CHARS    : {mc}", flush=True)
    print(f"QUESTION     : {q}", flush=True)
    if opts:
        print(f"OPTIONS      : {json.dumps(opts)}", flush=True)
    if typ == 'RESUME_TAILORING':
        print(f"PROMPT_SNIPPET: {prompt[:400].strip()}...", flush=True)
    else:
        print(f"FULL_PROMPT  : {prompt[:600].strip()}", flush=True)
    print(sep, flush=True)
    print(f">> AG Brain: Write answer to pending_question.json -> 'answer' key", flush=True)
    print(sep, flush=True)


def run(profile_dir: str, poll: float = 2.0):
    profile_path = BASE_DIR / profile_dir
    cfg_path     = profile_path / 'candidate_config.json'
    ipc_path     = profile_path / 'output' / 'pending_question.json'

    if not cfg_path.exists():
        print(f"[IPC-WATCHER] FATAL: No candidate_config.json at {cfg_path}", flush=True)
        sys.exit(1)

    cfg  = json.loads(cfg_path.read_text(encoding='utf-8'))
    name = cfg.get('candidate', {}).get('full_name', profile_dir)

    print("=" * 72, flush=True)
    print(f"[IPC-WATCHER {ts()}] STARTED | Profile: {name}", flush=True)
    print(f"[IPC-WATCHER {ts()}] Watching: {ipc_path}", flush=True)
    print(f"[IPC-WATCHER {ts()}] Poll: every {poll}s | AG Brain is the intelligence", flush=True)
    print("=" * 72, flush=True)

    last_printed_ts = None  # avoid spamming same question repeatedly
    wait_count      = 0

    while True:
        try:
            if ipc_path.exists():
                try:
                    data = json.loads(ipc_path.read_text(encoding='utf-8'))
                except Exception:
                    time.sleep(poll)
                    continue

                status = data.get('status', '')
                ipc_ts = data.get('timestamp', '')

                if status == 'PENDING':
                    # Only print the block once per unique question (by timestamp)
                    if ipc_ts != last_printed_ts:
                        print_pending_block(data)
                        last_printed_ts = ipc_ts
                        wait_count = 0
                    else:
                        wait_count += 1
                        # Re-print reminder every 10 polls (~20s) so AG Brain doesn't miss it
                        if wait_count % 10 == 0:
                            elapsed = int(wait_count * poll)
                            print(f"[IPC-WATCHER {ts()}] Still PENDING ({elapsed}s elapsed) - AG Brain, please answer!", flush=True)

                elif status == 'ANSWERED':
                    if ipc_ts == last_printed_ts:
                        ans_preview = str(data.get('answer', ''))[:80]
                        print(f"[IPC-WATCHER {ts()}] ANSWERED - '{ans_preview}'", flush=True)
                        last_printed_ts = None  # reset for next question
                        wait_count = 0

            time.sleep(poll)

        except KeyboardInterrupt:
            print(f"\n[IPC-WATCHER {ts()}] Stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"[IPC-WATCHER {ts()}] Error: {e}", flush=True)
            time.sleep(poll)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='IPC Watcher - AG Brain Signal Relay')
    ap.add_argument('--profile', required=True, help='Profile dir (e.g. profiles/TARGET_PROFILE)')
    ap.add_argument('--poll', type=float, default=2.0, help='Poll interval seconds (default: 2.0)')
    args = ap.parse_args()
    run(args.profile, args.poll)
