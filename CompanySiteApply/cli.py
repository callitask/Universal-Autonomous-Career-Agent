# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 23:02:00 +05:30
# Issue / Context: Interactive command-line interface for CompanySiteApply subsystem.
# Changes Made: Implemented CLI with inspect, heal, fill, and detect commands.
# Rationale: Provides human-in-the-loop and development inspection hooks for live ATS cracking.
# Preventative Notes: Never runs as an uncontrolled daemon; strictly on-demand. Zero candidate PII.
#
# [ENTRY #002]
# Term: [CDP_LITERAL_PURGE]
# Timestamp: 2026-09-26 12:00:00 +05:30
# Issue / Context: --cdp-url defaulted to a hardcoded localhost URL.
# Changes Made: Default is now None; ATSArm resolves via CDP_URL env.
# Rationale: Zero hardcoding; custom ports need no code edits.
# Preventative Notes: Never restore a literal CDP default here.
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


def cmd_heal_section(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        candidate_data = {}
        if args.config:
            p = Path(args.config)
            if p.exists():
                candidate_data = json.loads(p.read_text("utf-8"))
        print(f"Executing surgical heal on section '{args.section}'...")
        res = arm.heal_section(args.section, candidate_data)
        print("\nSection Heal Result:")
        print(json.dumps(res, indent=2))
    finally:
        arm.disconnect()


def cmd_audit_section(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        candidate_data = {}
        if args.config:
            p = Path(args.config)
            if p.exists():
                candidate_data = json.loads(p.read_text("utf-8"))
        print(f"Executing audit on section '{args.section}'...")
        res = arm.audit_section(args.section, candidate_data)
        print("\nSection Audit Result:")
        print(json.dumps(res, indent=2))
    finally:
        arm.disconnect()


def cmd_apply_flow(args):
    from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
    orchestrator = ApplyOrchestrator(cdp_url=args.cdp_url)
    candidate_data = {}
    if args.config:
        p = Path(args.config)
        if p.exists():
            candidate_data = json.loads(p.read_text("utf-8"))
    shot_dir = PROJECT_ROOT / "artifacts"
    print("Executing autonomous application pipeline via Section Mini-Agents...")
    res = orchestrator.run(candidate_data, screenshot_dir=shot_dir)
    print("\nPipeline Result:")
    print(json.dumps(res, indent=2))


def main():
    parser = argparse.ArgumentParser(description="CompanySiteApply - Enterprise ATS Multi-Finger Tool")
    parser.add_argument("--cdp-url", default=None, help="CDP connection endpoint (falls back to CDP_URL env var)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # apply-flow (Autonomous master pipeline)
    p_af = subparsers.add_parser("apply-flow", help="Autonomously execute end-to-end application lifecycle through Section Mini-Agents")
    p_af.add_argument("--config", required=True, help="Path to candidate config JSON")

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

def cmd_heal_subagent(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        candidate_data = {}
        if args.config:
            p = Path(args.config)
            if p.exists():
                candidate_data = json.loads(p.read_text("utf-8"))
        print(f"Executing surgical heal on sub-agent '{args.name}'...")
        res = arm.heal_subagent(args.name, candidate_data)
        print("\nSub-Agent Heal Result:")
        print(json.dumps(res, indent=2))
    finally:
        arm.disconnect()


def cmd_audit_subagent(args):
    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        candidate_data = {}
        if args.config:
            p = Path(args.config)
            if p.exists():
                candidate_data = json.loads(p.read_text("utf-8"))
        print(f"Executing audit on sub-agent '{args.name}'...")
        res = arm.audit_subagent(args.name, candidate_data)
        print("\nSub-Agent Audit Result:")
        print(json.dumps(res, indent=2))
    finally:
        arm.disconnect()


def cmd_list_subagents(args):
    from CompanySiteApply.section_agents import SectionAgentDispatcher
    dispatcher = SectionAgentDispatcher()
    print("\n" + "=" * 60)
    print("  REGISTERED HIERARCHICAL ATS MINI-AGENTS")
    print("=" * 60)
    print("\n[TOP-LEVEL SECTION COORDINATORS]:")
    for s in dispatcher.list_available_sections():
        print(f"  • {s}")
    print("\n[GRANULAR SURGICAL SUB-AGENTS]:")
    for sub in dispatcher.list_available_subagents():
        print(f"  • {sub}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CompanySiteApply - Enterprise ATS Multi-Finger Tool")
    parser.add_argument("--cdp-url", default=None, help="CDP connection endpoint (falls back to CDP_URL env var)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # apply-flow (with alias 'apply')
    p_af = subparsers.add_parser("apply-flow", aliases=["apply"], help="Autonomously execute end-to-end application lifecycle through Section Mini-Agents")
    p_af.add_argument("--config", required=True, help="Path to candidate config JSON")

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

    # heal-section
    p_hs = subparsers.add_parser("heal-section", help="Surgically heal a specific section via its dedicated mini-agent")
    p_hs.add_argument("--section", required=True, choices=["profile", "questionnaire", "education", "experience", "review"], help="Section name to heal")
    p_hs.add_argument("--config", help="Path to candidate config JSON")

    # audit-section
    p_as = subparsers.add_parser("audit-section", help="Audit a specific section via its dedicated mini-agent")
    p_as.add_argument("--section", required=True, choices=["profile", "questionnaire", "education", "experience", "review"], help="Section name to audit")
    p_as.add_argument("--config", help="Path to candidate config JSON")

    # heal-subagent
    p_hsub = subparsers.add_parser("heal-subagent", help="Surgically heal a granular sub-agent (e.g. preferred_location, dropdown_questions, documents)")
    p_hsub.add_argument("--name", required=True, help="Sub-agent name to heal")
    p_hsub.add_argument("--config", help="Path to candidate config JSON")

    # audit-subagent
    p_asub = subparsers.add_parser("audit-subagent", help="Audit a granular sub-agent")
    p_asub.add_argument("--name", required=True, help="Sub-agent name to audit")
    p_asub.add_argument("--config", help="Path to candidate config JSON")

    # list-subagents
    subparsers.add_parser("list-subagents", help="List all registered top-level sections and granular sub-agents")

    args = parser.parse_args()
    if args.command in ["apply-flow", "apply"]:
        cmd_apply_flow(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "detect":
        cmd_detect(args)
    elif args.command == "heal":
        cmd_heal(args)
    elif args.command == "fill":
        cmd_fill(args)
    elif args.command == "heal-section":
        cmd_heal_section(args)
    elif args.command == "audit-section":
        cmd_audit_section(args)
    elif args.command == "heal-subagent":
        cmd_heal_subagent(args)
    elif args.command == "audit-subagent":
        cmd_audit_subagent(args)
    elif args.command == "list-subagents":
        cmd_list_subagents(args)


if __name__ == "__main__":
    main()
