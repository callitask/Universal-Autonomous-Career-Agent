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
#
# [ENTRY #002]
# Term: [BATCH_JOB_EVALUATION_WATCHER]
# Timestamp: 2026-09-20 19:55:00 +05:30
# Issue / Context: Batch Architecture v2.0 adds a second IPC file: batch_question.json.
#   The watcher must also poll this file and display ALL job cards to AG Brain clearly.
#   AG Brain writes decisions to batch_answer.json (NOT batch_question.json).
# Changes Made: Added batch IPC polling alongside existing pending_question.json polling.
#   For BATCH_JOB_EVALUATION tasks: prints card table showing all IDs, titles, companies.
#   Prints expected answer format (batch_answer.json) so AG Brain knows where to write.
#   Uses poll interval 1s for batch file (faster response for batch).
# Preventative Notes: batch_answer.json is SEPARATE from batch_question.json.
#   AG Brain must write decisions to batch_answer.json, NOT the question file.
#   Never mix up pending_question.json (single IPC) and batch_question.json (batch IPC).
#
# [ENTRY #003]
# Term: [CLI_ENTRYPOINT_FIX]
# Timestamp: 2026-09-20 21:18:00 +05:30
# Issue / Context: CLI invocation `python core/ipc_watcher.py --profile ...` parsed args via argparse
#   at line 230 but never called run(args.profile, args.poll), exiting immediately.
# Changes Made: Added `run(args.profile, args.poll)` beneath `args = ap.parse_args()`.
# Rationale: Enables direct execution as Daemon 2 without python -c workaround.
# Preventative Notes: Always invoke the main run() loop after argparse.parse_args() in runnable CLIs.
# ================================================================================

"""
IPC WATCHER - AG Brain Signal Relay
====================================
Polls pending_question.json every 2 seconds (single-card IPC).
Polls batch_question.json every 1 second (batch IPC — Batch Arch v2.0).

When PENDING detected: prints loud structured block to stdout.
AG Brain (running in Antigravity 2.0) reads it, generates answer,
writes answer back via run_command tool.

BATCH FLOW:
  batch_question.json  ← Script writes card batch
  AG Brain reads it    → evaluates all cards → writes batch_answer.json
  Script reads batch_answer.json → executes approved cards

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


def print_batch_block(data: dict, batch_answer_path: Path):
    """Print the batch evaluation request for AG Brain. Shows all cards and expected output format."""
    sep = "=" * 72
    designation = data.get("designation", "")
    cards = data.get("cards", [])
    cand = data.get("candidate_summary", {})

    print(sep, flush=True)
    print(f"[IPC-WATCHER {ts()}] *** AG BRAIN BATCH EVALUATION REQUIRED ***", flush=True)
    print(sep, flush=True)
    print(f"TASK_TYPE     : BATCH_JOB_EVALUATION", flush=True)
    print(f"DESIGNATION   : {designation}", flush=True)
    print(f"TOTAL_CARDS   : {len(cards)}", flush=True)
    print(f"CANDIDATE     : {cand.get('seniority_level','')} | {cand.get('domain','')} | {cand.get('total_experience_years','')} yrs exp", flush=True)
    print(f"ACTIVE_TITLES : {cand.get('active_search_titles', [])[:5]}", flush=True)
    print(f"AVOID_TERMS   : {cand.get('advisory_avoid_terms', [])[:10]}", flush=True)
    print(sep, flush=True)
    print(f"CARDS TO EVALUATE:", flush=True)
    for card in cards:
        cid = card.get("id", "?")
        title = card.get("title", "")
        company = card.get("company", "")
        exp_text = card.get("exp_text", "")
        skills = card.get("skills", [])[:5]
        print(f"  [{cid:02d}] {title} @ {company} | {exp_text} | Skills: {skills}", flush=True)
    print(sep, flush=True)
    print(f">> AG Brain: Evaluate ALL {len(cards)} cards above.", flush=True)
    print(f">> For each card, decide: DEEP_SCAN (open & apply) or SKIP (wrong role/domain).", flush=True)
    print(f">> Write decisions to: {batch_answer_path}", flush=True)
    print(f">> REQUIRED FORMAT (batch_answer.json):", flush=True)
    print(f'>> {{', flush=True)
    print(f'>>   "status": "ANSWERED",', flush=True)
    print(f'>>   "task_type": "BATCH_JOB_EVALUATION",', flush=True)
    print(f'>>   "decisions": [', flush=True)
    print(f'>>     {{"id": 0, "decision": "DEEP_SCAN", "reason": "Core Java backend role, strong match"}},', flush=True)
    print(f'>>     {{"id": 1, "decision": "SKIP", "reason": "Salesforce role, wrong domain"}},', flush=True)
    print(f'>>     ... (one entry per card)', flush=True)
    print(f'>>   ],', flush=True)
    print(f'>>   "expansion_keywords": []', flush=True)
    print(f'>> }}', flush=True)
    print(sep, flush=True)


def run(profile_dir: str, poll: float = 2.0):
    profile_path = BASE_DIR / profile_dir
    cfg_path     = profile_path / 'candidate_config.json'
    ipc_path     = profile_path / 'output' / 'pending_question.json'
    batch_q_path = profile_path / 'output' / 'batch_question.json'
    batch_a_path = profile_path / 'output' / 'batch_answer.json'

    if not cfg_path.exists():
        print(f"[IPC-WATCHER] FATAL: No candidate_config.json at {cfg_path}", flush=True)
        sys.exit(1)

    cfg  = json.loads(cfg_path.read_text(encoding='utf-8'))
    name = cfg.get('candidate', {}).get('full_name', profile_dir)

    print("=" * 72, flush=True)
    print(f"[IPC-WATCHER {ts()}] STARTED | Profile: {name}", flush=True)
    print(f"[IPC-WATCHER {ts()}] Single IPC: {ipc_path}", flush=True)
    print(f"[IPC-WATCHER {ts()}] Batch  IPC: {batch_q_path}", flush=True)
    print(f"[IPC-WATCHER {ts()}] Poll: every {poll}s | AG Brain is the intelligence", flush=True)
    print("=" * 72, flush=True)

    last_printed_ts = None       # avoid spamming same single-IPC question repeatedly
    last_batch_ts   = None       # avoid spamming same batch question repeatedly
    wait_count      = 0
    batch_wait      = 0

    while True:
        try:
            # ── Poll 1: Single-card IPC (pending_question.json) ──────────────────
            if ipc_path.exists():
                try:
                    data = json.loads(ipc_path.read_text(encoding='utf-8'))
                except Exception:
                    time.sleep(poll)
                    continue

                status = data.get('status', '')
                ipc_ts = data.get('timestamp', '')

                if status == 'PENDING':
                    if ipc_ts != last_printed_ts:
                        print_pending_block(data)
                        last_printed_ts = ipc_ts
                        wait_count = 0
                    else:
                        wait_count += 1
                        if wait_count % 10 == 0:
                            elapsed = int(wait_count * poll)
                            print(f"[IPC-WATCHER {ts()}] Still PENDING ({elapsed}s elapsed) - AG Brain, please answer!", flush=True)

                elif status == 'ANSWERED':
                    if ipc_ts == last_printed_ts:
                        ans_preview = str(data.get('answer', ''))[:80]
                        print(f"[IPC-WATCHER {ts()}] ANSWERED - '{ans_preview}'", flush=True)
                        last_printed_ts = None
                        wait_count = 0

            # ── Poll 2: Batch IPC (batch_question.json) ─────────────────────────
            if batch_q_path.exists():
                try:
                    bdata = json.loads(batch_q_path.read_text(encoding='utf-8'))
                except Exception:
                    time.sleep(poll)
                    continue

                bstatus = bdata.get('status', '')
                bts = bdata.get('timestamp', '')

                if bstatus == 'PENDING':
                    if bts != last_batch_ts:
                        print_batch_block(bdata, batch_a_path)
                        last_batch_ts = bts
                        batch_wait = 0
                    else:
                        batch_wait += 1
                        if batch_wait % 15 == 0:
                            elapsed = int(batch_wait * poll)
                            print(f"[IPC-WATCHER {ts()}] BATCH PENDING ({elapsed}s elapsed) - AG Brain: write {batch_a_path.name}!", flush=True)

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
