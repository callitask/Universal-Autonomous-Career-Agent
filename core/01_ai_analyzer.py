"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT
File: core/01_ai_analyzer.py
================================================================================
Enterprise Profile Analyzer
- 100% Config-Driven: General across any profile domain.
- Fully integrates with Universal AIClient for Antigravity 2.0 failover.
- Uses atomic file operations to prevent config corruption.
================================================================================
"""
import sys
import os
import json
import re
import argparse
from pathlib import Path

# Force standard output to UTF-8 and line-buffering
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.utils.profile_context import ProfileContext
from core.ai_client import AIClient

def log(msg: str):
    print(f"[AI ANALYZER] {msg}", flush=True)

def analyze_profile():
    parser = argparse.ArgumentParser(description="Universal Profile AI Analyzer")
    parser.add_argument('--profile', default=None, help='Path to candidate profile directory')
    parser.add_argument('--force', action='store_true', help='Force full re-synthesis of cognitive profile')
    args, _ = parser.parse_known_args()

    # Dynamic profile resolution via ProfileContext
    ctx = ProfileContext(args.profile, BASE)
    cfg_path = ctx.config_path
    resume_path = ctx.profile_path / "resume.md"

    print("\n" + "=" * 60, flush=True)
    print("  STEP 0: AI PROFILE ANALYZER & COGNITIVE SYNTHESIZER", flush=True)
    print("=" * 60 + "\n", flush=True)

    if not resume_path.exists():
        log(f"[!] No resume found at {resume_path}. Skipping analysis.")
        return

    if not cfg_path.exists():
        log(f"[!] No config found at {cfg_path}. Skipping analysis.")
        return

    cfg = ctx.config
    current_keywords = cfg.get("target_jobs", {}).get("keywords", [])
    has_placeholder_keywords = (not current_keywords) or any("[KEYWORD" in str(k) for k in current_keywords)

    ai = AIClient(ctx)
    resume_text = resume_path.read_text(encoding="utf-8")

    log("[BRAIN] Engaging Cognitive Profile Synthesizer to analyze human background & skill sets...")
    try:
        cog_profile = ai.synthesize_cognitive_profile(force_refresh=args.force)
        domain = cog_profile.get("candidate_domain", "Unspecified Domain")
        seniority = cog_profile.get("seniority_level", "Professional")
        years = cog_profile.get("years_of_experience", 0)
        core_skills = cog_profile.get("core_domain_skills", [])
        cycles = cog_profile.get("search_cycles", [])
        incomp_v = cog_profile.get("incompatible_verticals", {})

        log(f"[OK] Cognitive Profile Model Synthesized:")
        log(f"     Domain:               {domain}")
        log(f"     Seniority Level:      {seniority}")
        log(f"     Experience:           {years} years")
        log(f"     Core Domain Skills:   {len(core_skills)} skills identified")
        log(f"     Multi-Cycle Queues:   {len(cycles)} search cycles generated")
        log(f"     Incompatible Verts:   {len(incomp_v)} domains filtered")

        # If configuration needs search keywords or user requested --force
        if has_placeholder_keywords or args.force:
            # Flatten cycle 1 designations as primary target keywords if needed
            cycle_titles = cycles[0] if cycles and isinstance(cycles[0], list) else []
            recommended_titles = cog_profile.get("recommended_titles", cycle_titles)
            
            # If search keywords not in cognitive profile, ask AIClient for focused search keywords
            search_kw = cog_profile.get("search_keywords", [])
            if not search_kw and cycle_titles:
                search_kw = cycle_titles[:5]
            
            if not search_kw:
                prompt = f"""Analyze this candidate resume and identify the top 5 relevant job titles and 3 high-impact search keywords matching their actual experience:
{resume_text[:3000]}

Return ONLY valid JSON:
{{
  "recommended_titles": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
  "search_keywords": ["Keyword 1", "Keyword 2", "Keyword 3"]
}}"""
                raw_resp = ai.generate_text(prompt=prompt, default_fallback="{}")
                json_match = re.search(r'\{.*\}', raw_resp, re.DOTALL)
                if json_match:
                    clean_text = json_match.group(0)
                else:
                    clean_text = re.sub(r'^```(?:json)?\s*', '', raw_resp.strip(), flags=re.IGNORECASE)
                    clean_text = re.sub(r'\s*```$', '', clean_text).strip()
                parsed = json.loads(clean_text)
                search_kw = parsed.get("search_keywords", [])
                recommended_titles = parsed.get("recommended_titles", [])

            if search_kw:
                cfg.setdefault("target_jobs", {})["keywords"] = search_kw
                if recommended_titles:
                    cfg.setdefault("target_jobs", {})["recommended_titles"] = recommended_titles
                
                # Atomic save
                ctx.save_config()
                log(f"[OK] Dynamic search keywords updated: {search_kw}")
                if recommended_titles:
                    log(f"[OK] Dynamic recommended titles: {recommended_titles}")
        else:
            log(f"[SKIP] Custom keywords already configured ({len(current_keywords)} roles). Retaining targeted profile.")

    except Exception as e:
        log(f"[!] AI profile analysis notice: {e}")

if __name__ == "__main__":
    analyze_profile()