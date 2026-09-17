# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 23:02:00 +05:30
# Issue / Context: Interactive command-line interface for CompanySiteApply subsystem.
# Changes Made: Implemented CLI with inspect, heal, fill, and detect commands.
# Rationale: Provides human-in-the-loop and development inspection hooks for live ATS cracking.
# Preventative Notes: Never runs as an uncontrolled daemon; strictly on-demand. Zero candidate PII.
# ==============================================================================

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from CompanySiteApply.ats_arm import ATSArm


def prompt_terminal_user(prompt_text: str, options: list = None) -> str:
    """Fallback interactive prompt for terminal execution."""
    print(f"\n[CompanySiteApply INPUT REQUIRED] {prompt_text}")
    if options:
        print(f"Options: {', '.join(options)}")
    try:
        val = input(">> ").strip()
        return val
    except EOFError:
        return ""


def cmd_inspect(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        print(f"Connecting to CDP at {args.cdp_url}...")
        result = arm.inspect_active_tab(save_snapshot=True)
        det = result["detection"]
        print("\n" + "=" * 60)
        print("  ATS PLATFORM INSPECTION REPORT")
        print("=" * 60)
        print(f"  Platform Detected : {det['platform_name'].upper()}")
        print(f"  Variant           : {det['platform_variant']}")
        print(f"  Confidence Score  : {det['confidence']}")
        print(f"  Page Title        : {det['title']}")
        print(f"  Current URL       : {det['url']}")
        print(f"  Detected Step     : {result['step_schema'].get('detected_step')}")
        print(f"  Honeypots Detected: {det['honeypots_detected']} {det['honeypot_identifiers']}")
        print(f"  Snapshot Saved To : {result.get('saved_snapshot_path')}")
        print("=" * 60)
        
        inputs = result["step_schema"].get("inputs", [])
        print(f"\nFound {len(inputs)} form controls on page:")
        for idx, inp in enumerate(inputs):
            hp_flag = " [HONEYPOT TRAP - DO NOT FILL!]" if inp.get("is_honeypot") else ""
            req_flag = " (Required)" if inp.get("required") else ""
            print(f"  [{idx+1}] {inp['tagName'].upper()}:{inp['type']} | name='{inp['name']}' id='{inp['id']}' label='{inp['labelText']}'{req_flag}{hp_flag}")
            
    finally:
        arm.disconnect()


def cmd_detect(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        from CompanySiteApply.ats_detector import ATSDetector
        det = ATSDetector.detect_platform(page)
        print(json.dumps(det, indent=2))
    finally:
        arm.disconnect()


def cmd_heal(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        print(f"Running Parser Doctor on active page at {args.cdp_url}...")
        result = arm.heal_active_page()
        print("\nParser Doctor Results:")
        print(json.dumps(result, indent=2))
    finally:
        arm.disconnect()


def cmd_fill(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        candidate_data = {}
        if args.config:
            p = Path(args.config)
            if p.exists():
                candidate_data = json.loads(p.read_text("utf-8"))
        elif args.email:
            candidate_data["email"] = args.email

        print(f"Executing step fill on active tab...")
        res = arm.fill_and_advance(candidate_data, prompt_callback=prompt_terminal_user)
        print("\nStep Execution Result:")
        print(json.dumps(res, indent=2))
    finally:
        arm.disconnect()


def main():
    parser = argparse.ArgumentParser(description="CompanySiteApply - Enterprise ATS Multi-Finger Tool")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP connection endpoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect
    p_insp = subparsers.add_parser("inspect", help="Deeply inspect active tab, detect ATS, flag honeypots, save schema")
    
    # detect
    p_det = subparsers.add_parser("detect", help="Quick print of detected ATS platform and confidence")

    # heal
    p_heal = subparsers.add_parser("heal", help="Run Parser Doctor to heal broken line wraps and education anomalies")

    # fill
    p_fill = subparsers.add_parser("fill", help="Fill active step and advance")
    p_fill.add_argument("--email", help="Candidate email for email step")
    p_fill.add_argument("--config", help="Path to candidate config JSON")

    args = parser.parse_args()
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "detect":
        cmd_detect(args)
    elif args.command == "heal":
        cmd_heal(args)
    elif args.command == "fill":
        cmd_fill(args)


if __name__ == "__main__":
    main()
