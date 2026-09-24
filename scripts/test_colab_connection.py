"""
Colab GPU Gateway Connection Diagnostic
========================================
Tests connectivity to the OpenAI-compatible Colab API gateway (Ollama + Cloudflare tunnel).

Reads credentials EXCLUSIVELY from the global `colab_credentials.json` at the repo root.
This file is git-ignored and applies to ALL profiles. Never put credentials in candidate configs.

Usage:
    python scripts/test_colab_connection.py
    python scripts/test_colab_connection.py --profile profiles/default_user

Requirements:
    pip install openai

colab_credentials.json schema:
    {
      "engine_enabled": true,
      "colab_base_url": "https://<tunnel>.trycloudflare.com/v1",
      "colab_api_key": "sk-colab-...",
      "colab_model": ""
    }

Notes:
    - Update colab_base_url each Colab session (Cloudflare tunnel URL changes on restart).
    - Set engine_enabled=false to test AG Brain IPC mode without disabling the file.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path

# ── Bootstrap project root onto sys.path ──────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Verify openai SDK is installed ────────────────────────────────────────────
try:
    import openai
except ImportError:
    print("[DIAGNOSTIC] ERROR: 'openai' package not installed.")
    print("             Run: pip install openai")
    sys.exit(1)


def run_diagnostic(profile_dir_str: str | None = None) -> None:
    creds_path = _PROJECT_ROOT / "colab_credentials.json"

    print(f"\n{'=' * 65}")
    print(f"  Colab GPU Gateway — Connection Diagnostic")
    print(f"{'=' * 65}")
    print(f"  Credentials file: {creds_path}")
    print(f"{'=' * 65}\n")

    # ── Load global credentials ────────────────────────────────────────────────
    if not creds_path.exists():
        print("[DIAGNOSTIC] ERROR: colab_credentials.json not found at repo root.")
        print(f"             Expected: {creds_path}")
        print("             Create this file (it is git-ignored) with the schema documented above.")
        sys.exit(1)

    try:
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[DIAGNOSTIC] ERROR: Could not parse colab_credentials.json: {e}")
        sys.exit(1)

    # ── MASTER GATE CHECK ──────────────────────────────────────────────────────
    engine_enabled = bool(creds.get("engine_enabled", True))
    colab_base_url = str(creds.get("colab_base_url", "") or "").strip()
    colab_api_key  = str(creds.get("colab_api_key", "") or "").strip()
    colab_model_cfg = str(creds.get("colab_model", "") or "").strip()

    print(f"[STEP 1] colab_credentials.json loaded:")
    print(f"         engine_enabled  = {engine_enabled}")
    print(f"         colab_base_url  = {colab_base_url or '(not set)'}")
    masked_key = ('*' * min(8, len(colab_api_key))) + ('...' if len(colab_api_key) > 8 else '') if colab_api_key else '(not set)'
    print(f"         colab_api_key   = {masked_key} ({len(colab_api_key)} chars)")
    print(f"         colab_model     = {colab_model_cfg or '(auto-discover)'}")
    print()

    if not engine_enabled:
        print("[DIAGNOSTIC] NOTICE: engine_enabled=false in colab_credentials.json.")
        print("             The Colab engine is intentionally disabled. AG Brain IPC mode is active.")
        print("             Set engine_enabled=true to re-enable the Colab GPU gateway.")
        print()
        print(f"{'=' * 65}")
        print(f"  ⚠️  ENGINE DISABLED — AG Brain IPC is the active LLM engine")
        print(f"{'=' * 65}\n")
        sys.exit(0)

    if not colab_base_url or colab_base_url.startswith("["):
        print("[DIAGNOSTIC] ERROR: colab_base_url is not configured (still placeholder or empty).")
        print("             Update colab_credentials.json[\"colab_base_url\"] with your live tunnel URL.")
        sys.exit(1)

    if not colab_api_key or colab_api_key.startswith("["):
        print("[DIAGNOSTIC] ERROR: colab_api_key is not configured (still placeholder or empty).")
        print("             Update colab_credentials.json[\"colab_api_key\"] with your Colab API key.")
        sys.exit(1)

    # ── Instantiate OpenAI client (reads from global creds — zero hardcoding) ──
    # Diagnostic uses finite 120s timeout so a dead tunnel fails fast; production
    # ai_client keeps timeout=None for 30-80s GPU inference (ENTRY #022).
    print("[STEP 2] Initializing OpenAI-compatible client (timeout=120s diagnostic)...")
    client = openai.OpenAI(
        base_url=colab_base_url,
        api_key=colab_api_key,
        timeout=120.0
    )
    print("         Client initialized successfully.\n")

    # ── Auto-discover models ───────────────────────────────────────────────────
    print("[STEP 3] Auto-discovering available models...")
    discovered_model = None
    try:
        t0 = time.time()
        models_resp = client.models.list()
        latency_ms = int((time.time() - t0) * 1000)
        model_ids = [m.id for m in models_resp.data if getattr(m, "id", None)]
        if model_ids:
            discovered_model = model_ids[0]
            print(f"         Available models ({latency_ms}ms):")
            for mid in model_ids:
                print(f"           - {mid}")
        else:
            print("         WARNING: No models returned by models.list()")
    except Exception as e:
        print(f"         ERROR during model discovery: {e}")

    active_model = discovered_model or colab_model_cfg or None
    if not active_model:
        print("\n[DIAGNOSTIC] ERROR: Could not discover any model. Is the Colab cell still running?")
        print("             Also check if the tunnel URL has changed since the last session.")
        sys.exit(1)

    print(f"\n         Active model selected: {active_model}\n")

    # ── Send a timed test completion ───────────────────────────────────────────
    test_prompt = "Explain gravity in one sentence. Be concise."
    print(f"[STEP 4] Sending test prompt: '{test_prompt}'")
    print(f"         Model: {active_model}")
    print("         Waiting for response (timeout=None — GPU inference may take 10-60s)...\n")

    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model=active_model,
            messages=[{"role": "user", "content": test_prompt}],
            temperature=0.3
        )
        elapsed_s = time.time() - t0
        response_text = ""
        if resp.choices and resp.choices[0].message.content:
            response_text = resp.choices[0].message.content.strip()

        print(f"         Latency:  {elapsed_s:.2f}s")
        print(f"         Response: {response_text[:300]}")
        print()
        print(f"{'=' * 65}")
        print(f"  ✅  DIAGNOSTIC PASSED — Colab GPU gateway is OPERATIONAL")
        print(f"      Model:   {active_model}")
        print(f"      URL:     {colab_base_url}")
        print(f"      Latency: {elapsed_s:.2f}s")
        print(f"{'=' * 65}\n")

    except Exception as e:
        print(f"         ERROR during test completion: {e}")
        print()
        print(f"{'=' * 65}")
        print(f"  ❌  DIAGNOSTIC FAILED — Could not complete test inference")
        print(f"      Error: {e}")
        print(f"      Check: Is the Colab cell still running? Is the tunnel URL current?")
        print(f"{'=' * 65}\n")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diagnose Colab GPU Gateway connectivity for the Universal Career Agent."
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Optional: Path to candidate profile (not used for credentials — kept for CLI consistency)."
    )
    args = parser.parse_args()
    run_diagnostic(profile_dir_str=args.profile)
