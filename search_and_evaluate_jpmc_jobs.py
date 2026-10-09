import asyncio
import json
import os
import re
from typing import Optional, Dict, List, Any
from pathlib import Path
from playwright.async_api import async_playwright
from CompanySiteApply.CompanyScraper.companies.jpmorgan.jpmorgan_scraper import JPMorganScraper

REPO_ROOT = Path(__file__).resolve().parent

def load_candidate_context(profile_name: Optional[str] = None):
    profile = profile_name or os.environ.get("CANDIDATE_PROFILE", "udaysagar_kandpal")
    cfg_path = REPO_ROOT / "profiles" / profile / "candidate_config.json"
    if not cfg_path.exists():
        cfg_path = REPO_ROOT / "profiles" / "default_user" / "candidate_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    resume_path = REPO_ROOT / "profiles" / profile / "resume.md"
    resume_text = ""
    if resume_path.exists():
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
    return cfg, resume_text

def score_job_match(job_details: dict, candidate_cfg: dict, resume_text: str) -> dict:
    cand = candidate_cfg.get("candidate", candidate_cfg)
    title = job_details.get("title", "")
    desc = job_details.get("full_text", "") or job_details.get("description", "")
    
    score = 0
    reasons = []
    
    # 1. Seniority / Experience fit
    title_lower = title.lower()
    if any(k in title_lower for k in ["lead", "principal", "architect", "staff", "senior"]):
        score += 25
        reasons.append("Seniority tier match (Lead/Principal/Senior role for 10+ yrs experience)")
    elif "engineer iii" in title_lower:
        score += 20
        reasons.append("Seniority tier match (Engineer III)")
    elif "engineer ii" in title_lower:
        score += 10
        reasons.append("Lower seniority level (Engineer II)")

    # 2. Core Tech Stack Match
    tech_keywords = {
        "Java": 15,
        "Spring Boot": 15,
        "Microservices": 10,
        "Kafka": 10,
        "AWS": 10,
        "Distributed Systems": 10,
        "Low-Latency": 5,
        "IPC": 5
    }
    
    matched_tech = []
    for tech, pts in tech_keywords.items():
        if re.search(r'\b' + re.escape(tech) + r'\b', desc, re.IGNORECASE) or re.search(r'\b' + re.escape(tech) + r'\b', title, re.IGNORECASE):
            score += pts
            matched_tech.append(tech)
            
    reasons.append(f"Matched Technologies: {', '.join(matched_tech)}")
    
    # 3. Location match
    loc = job_details.get("location", "") or desc
    if "bengaluru" in loc.lower() or "bangalore" in loc.lower():
        score += 10
        reasons.append("Location match: Bengaluru, India")
        
    final_score = min(score, 100)
    return {
        "score": final_score,
        "matched_tech": matched_tech,
        "reasons": reasons
    }

async def main():
    cfg, resume_text = load_candidate_context()
    scraper = JPMorganScraper()
    
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        page = b.contexts[0].pages[0]
        
        print("=== Searching JPMC Career Site (CX_1002) ===")
        # Search for Java in Bengaluru
        raw_jobs = await scraper.search_jobs(page, keyword="Java", location="Bengaluru")
        print(f"Found {len(raw_jobs)} total job cards.")
        
        # Filter out ALREADY APPLIED jobs
        eligible_jobs = [j for j in raw_jobs if not j.get("is_already_applied")]
        applied_jobs = [j for j in raw_jobs if j.get("is_already_applied")]
        
        print(f"Skipping {len(applied_jobs)} previously applied jobs:")
        for aj in applied_jobs:
            print(f"  - [ALREADY APPLIED] {aj['title']} (ID: {aj['job_id']})")
            
        print(f"\nEvaluating {len(eligible_jobs)} unapplied roles...")
        
        scored_jobs = []
        for j in eligible_jobs[:6]:
            print(f"\nInspecting Job ID {j['job_id']}: {j['title']}...")
            details = await scraper.scrape_job_details(page, j['job_id'])
            eval_res = score_job_match(details, cfg, resume_text)
            print(f"  -> Score: {eval_res['score']}/100")
            scored_jobs.append({
                "job_id": j['job_id'],
                "title": details.get("title") or j['title'],
                "location": details.get("location") or j['location'],
                "score": eval_res['score'],
                "reasons": eval_res['reasons'],
                "details": details
            })
            
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        
        print("\n=== RANKED MATCH RESULTS ===")
        for i, sj in enumerate(scored_jobs):
            print(f"[{i+1}] {sj['title']} (ID: {sj['job_id']}) — Score: {sj['score']}/100")
            for r in sj['reasons']:
                print(f"    • {r}")
                
        # Save results to inspection json
        out_file = r"F:\JOB AI AGENT\jpmc_job_matches.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(scored_jobs, f, indent=2)
        print(f"\nSaved match report to: {out_file}")

if __name__ == '__main__':
    asyncio.run(main())
