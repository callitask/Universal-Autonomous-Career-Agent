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
    args, _ = parser.parse_known_args()

    # Dynamic profile resolution via ProfileContext
    ctx = ProfileContext(args.profile, BASE)
    cfg_path = ctx.config_path
    resume_path = ctx.profile_path / "resume.md"

    print("\n" + "=" * 60, flush=True)
    print("  STEP 0: AI PROFILE ANALYZER", flush=True)
    print("=" * 60 + "\n", flush=True)

    if not resume_path.exists():
        log(f"[!] No resume found at {resume_path}. Skipping analysis.")
        return

    if not cfg_path.exists():
        log(f"[!] No config found at {cfg_path}. Skipping analysis.")
        return

    cfg = ctx.config
    current_keywords = cfg.get("target_jobs", {}).get("keywords", [])
    if current_keywords and not any("[KEYWORD" in k for k in current_keywords):
        log(f"[SKIP] Custom keywords already configured ({len(current_keywords)} roles). Retaining targeted profile.")
        return

    ai = AIClient(ctx)
    resume_text = resume_path.read_text(encoding="utf-8")
    
    prompt = f"""
Analyze this candidate resume and identify the top 5 relevant job titles and 3 high-impact search keywords matching their actual experience:
{resume_text}

Return ONLY valid JSON:
{{
  "recommended_titles": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
  "search_keywords": ["Keyword 1", "Keyword 2", "Keyword 3"]
}}
"""
    log("[BRAIN] Analyzing master resume to generate targeted job search strategy...")
    try:
        raw_resp = ai.generate_text(prompt=prompt, default_fallback="{}")
        
        # C5 Fix: Robust JSON isolation extracting the full outer dictionary block safely
        json_match = re.search(r'\{.*\}', raw_resp, re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)
        else:
            clean_text = re.sub(r'^```(?:json)?\s*', '', raw_resp.strip(), flags=re.IGNORECASE)
            clean_text = re.sub(r'\s*```$', '', clean_text).strip()
            
        data = json.loads(clean_text)
        kw = data.get("search_keywords", [])
        titles = data.get("recommended_titles", [])
        
        if kw:
            cfg.setdefault("target_jobs", {})["keywords"] = kw
            if titles:
                cfg.setdefault("target_jobs", {})["recommended_titles"] = titles
            
            # C4 Fix: Leverage ProfileContext atomic save
            ctx.save_config()
            log(f"[OK] Dynamic search keywords updated: {kw}")
            if titles:
                log(f"[OK] Dynamic recommended titles: {titles}")
        else:
            log("[!] No search keywords extracted from AI response.")
    except Exception as e:
        log(f"[!] AI analysis notice: {e}")

if __name__ == "__main__":
    analyze_profile()