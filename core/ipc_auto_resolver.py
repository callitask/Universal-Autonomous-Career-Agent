# ================================================================================
# AI CONTEXT & CHANGE LOG
# ================================================================================
# [ENTRY #001]
# Term: [IPC_AUTO_RESOLVER_INITIAL]
# Timestamp: 2026-09-17 21:10:00 +05:30
# Issue / Context: AG Brain (chat window) could not autonomously monitor and answer
#   pending_question.json IPC requests in real-time — it only acted when spoken to.
#   30-second timeouts caused IPC to expire before the brain responded.
# Changes Made: Created standalone ipc_auto_resolver.py daemon that polls
#   pending_question.json every 2 seconds. Uses the same Gemini API client as
#   ai_client.py. Handles RESUME_TAILORING and QUESTIONNAIRE task types.
#   Runs as a background process in Antigravity 2.0 alongside the main career agent.
# Rationale: Eliminates IPC timeout failures. Makes AG Brain truly autonomous.
# Preventative Notes: Never hardcode candidate data. Always load from ProfileContext.
#
# [ENTRY #002]
# Term: [SECRETS_OUT_OF_PROFILES]
# Timestamp: 2026-10-07 16:00:00 +05:30
# Issue / Context: build_client read GEMINI key/model from candidate_config.json,
#   making per-profile files secret carriers.
# Changes Made: Secrets resolve ONLY from GEMINI_API_KEY/GEMINI_MODEL env or
#   global gemini_credentials.json (api_keys/model/fallback_models); profile is
#   never consulted. Fatal message updated to name both sources.
# Rationale: Single secure secrets source; matches test_colab_connection policy.
# Preventative Notes: Never re-add cfg candidate key/model reads here.
# ================================================================================

import os, sys, json, time, argparse, traceback
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from google import genai as genai_new
    HAS_GENAI_NEW = True
except ImportError:
    HAS_GENAI_NEW = False

try:
    import google.generativeai as genai_legacy
    HAS_GENAI_LEGACY = True
except ImportError:
    HAS_GENAI_LEGACY = False


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[IPC {ts}] {msg}", flush=True)


def build_client(cfg):
    # SECURITY: secrets resolve ONLY from gemini_credentials.json (global,
    # git-ignored) or environment. candidate_config.json is never consulted.
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip()
    if not api_key or not model:
        try:
            creds_path = BASE_DIR / "gemini_credentials.json"
            if creds_path.exists():
                creds = json.loads(creds_path.read_text(encoding="utf-8"))
                keys = creds.get("api_keys", []) or []
                if not api_key and keys:
                    api_key = str(keys[0]).strip()
                if not api_key and creds.get("api_key", "").strip():
                    api_key = str(creds.get("api_key", "")).strip()
                if not model and str(creds.get("model", "")).strip():
                    model = str(creds.get("model", "")).strip()
                if not model and (creds.get("fallback_models", []) or []):
                    model = str(creds.get("fallback_models", [])[0]).strip()
        except Exception as e:
            log(f"gemini_credentials.json read failed: {e}")
    if not api_key or not model:
        return None, None
    if HAS_GENAI_NEW:
        try:
            return genai_new.Client(api_key=api_key), model
        except Exception as e:
            log(f"google-genai init failed: {e}")
    if HAS_GENAI_LEGACY:
        try:
            genai_legacy.configure(api_key=api_key)
            return genai_legacy.GenerativeModel(model), model
        except Exception as e:
            log(f"legacy genai init failed: {e}")
    return None, None


def call_gemini(client, model, prompt):
    if HAS_GENAI_NEW and hasattr(client, 'models'):
        return client.models.generate_content(model=model, contents=prompt).text.strip()
    return client.generate_content(prompt).text.strip()


def clean_json(text):
    t = text.strip()
    if t.startswith("`"):
        t = "\n".join(l for l in t.split("\n") if not l.strip().startswith("`")).strip()
    return t


def resolve(ipc_path, client, model):
    data = json.loads(ipc_path.read_text(encoding='utf-8'))
    if data.get('status') != 'PENDING':
        return False

    task     = data.get('task_type', 'QUESTIONNAIRE')
    prompt   = data.get('prompt', data.get('question', ''))
    options  = data.get('options') or []
    ctrl     = data.get('control_type', 'TEXT')

    log(f"PENDING [{task}] | {prompt[:100].strip()}...")

    if task == 'RESUME_TAILORING':
        raw = call_gemini(client, model, prompt)
        raw = clean_json(raw)
        try:
            parsed = json.loads(raw)
            if "tailored_summary" not in parsed:
                raise ValueError("missing key")
            answer = json.dumps(parsed, ensure_ascii=False)
        except Exception:
            answer = json.dumps({"tailored_summary": raw[:500], "prioritized_skills": []})
        log(f"RESOLVED RESUME_TAILORING (chars={len(answer)})")
    else:
        if options:
            inst = f"Question: {prompt}\nOptions: {json.dumps(options)}\nReturn ONLY the exact matching option text."
        else:
            inst = f"Question: {prompt}\nReturn a clean factual answer only. If numeric, return just the number."
        raw = call_gemini(client, model, inst).strip()
        answer = raw
        if options:
            rl = raw.lower()
            match = next((o for o in options if o.lower() == rl or o.lower() in rl), None)
            answer = match if match else options[0]
        log(f"RESOLVED [{ctrl}] -> '{answer}'")

    data['answer']      = answer
    data['status']      = 'ANSWERED'
    data['resolved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['resolved_by'] = 'ipc_auto_resolver'
    ipc_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    log(f"Written -> {ipc_path.name} [ANSWERED]")
    return True


def run(profile_dir="profiles/TARGET_PROFILE", poll=2.0):
    profile_path = BASE_DIR / profile_dir
    cfg = json.loads((profile_path / 'candidate_config.json').read_text(encoding='utf-8'))
    ipc_path = profile_path / 'output' / 'pending_question.json'
    name = cfg.get('candidate', {}).get('full_name', profile_dir)

    log(f"=== IPC AUTO-RESOLVER STARTED | {name} | poll={poll}s ===")
    client, model = build_client(cfg)
    if not client:
        log("FATAL: No Gemini client. Set GEMINI_API_KEY + GEMINI_MODEL in environment or configure gemini_credentials.json.")
        sys.exit(1)
    log(f"Gemini ready | model={model} | watching {ipc_path}")

    count = 0
    while True:
        try:
            if ipc_path.exists():
                if resolve(ipc_path, client, model):
                    count += 1
                    log(f"[STATS] Resolved this session: {count}")
            time.sleep(poll)
        except KeyboardInterrupt:
            log(f"Stopped. Total resolved: {count}")
            break
        except Exception as e:
            log(f"Error: {e}")
            traceback.print_exc()
            time.sleep(poll)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--poll', type=float, default=2.0)
    args = ap.parse_args()
    run(args.profile, args.poll)
