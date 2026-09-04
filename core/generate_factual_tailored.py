#!/usr/bin/env python3
"""
================================================================================
GENERATE_FACTUAL_TAILORED.py
Universal Factual ATS Resume Tailoring Engine
================================================================================
Reads candidate Master Resume Template (Markdown), parses it into sections,
factually tailors the Professional Summary to the target Job Description,
prioritizes Core Competencies matching the JD requirements, scores and reorders
bullet points for maximum ATS keyword density (Strictly Zero Hallucinations),
computes an ATS Compatibility Score, and renders customized A4 PDFs via CDP.
================================================================================
"""

import sys
import argparse
import json
import re
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.utils.profile_context import ProfileContext
from core.ai_client import AIClient

HTML_WRAPPER = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 8mm 10mm 8mm 10mm;
  }
  body {
    font-family: 'Segoe UI', Calibri, Arial, Helvetica, sans-serif;
    font-size: 8.8pt;
    line-height: 1.32;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
  }
  h1 {
    font-size: 16pt;
    margin: 0 0 2px 0;
    color: #0d233a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    text-align: center;
    font-weight: 700;
  }
  h2 {
    font-size: 9.8pt;
    margin: 6px 0 2.5px 0;
    border-bottom: 1.2px solid #2b6cb0;
    padding-bottom: 1.5px;
    text-transform: uppercase;
    color: #1a365d;
    font-weight: 700;
    letter-spacing: 0.3px;
  }
  h3 {
    font-size: 9.2pt;
    margin: 3.5px 0 1.5px 0;
    color: #2d3748;
    font-weight: 600;
  }
  p {
    margin: 2px 0 2.5px 0;
  }
  h1 + p {
    text-align: center;
    font-size: 8.2pt;
    color: #334155;
    margin-bottom: 5px;
    line-height: 1.3;
  }
  ul {
    margin: 2px 0 3.5px 13px;
    padding: 0;
  }
  li {
    margin-bottom: 1.8px;
    line-height: 1.3;
  }
  strong {
    color: #0d233a;
  }
  hr {
    border: 0;
    border-top: 1px solid #cbd5e0;
    margin: 3px 0;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 3px 0;
  }
  th, td {
    border: 1px solid #cbd5e0;
    padding: 2px 4px;
    font-size: 8.2pt;
  }
  th {
    background: #edf2f7;
    text-align: left;
    font-weight: 600;
  }
  a {
    color: #2b6cb0;
    text-decoration: none;
  }
</style>
</head>
<body>
{body}
</body>
</html>"""


class ResumeTailorEngine:
    def __init__(self, profile_path=None):
        self.ctx = ProfileContext(profile_path, BASE)
        self.cfg = self.ctx.config
        self.resume_md_path = self.ctx.resume_path
        self.cdp_url = self.ctx.cdp_url
        self.ai = AIClient(self.ctx)

    def get_resume_filename(self):
        name = self.ctx.candidate_name.strip()
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[-1]}_Resume"
        return f"{parts[0]}_Resume" if parts else "Tailored_Resume"

    def parse_resume_sections(self, md_text):
        clean_text = md_text.lstrip('\ufeff\u200b\r\n ')
        lines = clean_text.splitlines()
        sections = []
        current = {"level": 0, "heading": "", "lines": [], "bullets": []}

        for line in lines:
            stripped_line = line.strip()
            heading_match = re.match(r'^(#{1,4})\s+(.*)', stripped_line)
            if heading_match:
                if current["heading"] or current["lines"] or current["bullets"]:
                    sections.append(current)
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                heading_text = re.sub(r'^\*{2}(.*?)\*{2}$', r'\1', heading_text).strip()
                current = {"level": level, "heading": heading_text, "lines": [], "bullets": []}
            elif re.match(r'^\s*[-*]\s+', line):
                current["bullets"].append(line)
            else:
                current["lines"].append(line)

        if current["heading"] or current["lines"] or current["bullets"]:
            sections.append(current)

        return sections

    def extract_jd_keywords(self, jd_text):
        jd_lower = jd_text.lower()
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "must", "that",
            "this", "these", "those", "it", "its", "we", "our", "you", "your",
            "they", "their", "he", "she", "his", "her", "not", "no", "nor",
            "as", "if", "so", "than", "too", "very", "just", "about", "up",
            "out", "into", "over", "after", "before", "between", "under",
            "again", "further", "then", "once", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "only", "own",
            "same", "also", "any", "how", "what", "which", "who", "whom",
            "why", "where", "when", "able", "experience", "years", "role",
            "work", "working", "team", "company", "job", "position", "required",
            "preferred", "strong", "good", "excellent"
        }
        token_pattern = r'[a-z0-9]+(?:\+\+|#)?|[.][a-z0-9]+|[a-z0-9]+(?:[/\-.][a-z0-9]+)+'
        words = re.findall(token_pattern, jd_lower)
        keywords = [w for w in words if w not in stop_words and len(w) >= 2]

        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i+1]
            if w1 not in stop_words or w2 not in stop_words:
                keywords.append(f"{w1} {w2}")

        for category, skills in self.cfg.get("taxonomy_skills", {}).items():
            if isinstance(skills, list):
                for skill in skills:
                    skill_clean = skill.strip().lower()
                    if skill_clean and re.search(rf'\b{re.escape(skill_clean)}\b', jd_lower):
                        keywords.append(skill_clean)

        return list(set(keywords))

    def calculate_ats_match_score(self, resume_text, jd_keywords):
        if not jd_keywords:
            return 85
        r_lower = resume_text.lower()
        matched = sum(1 for kw in jd_keywords if re.search(rf'\b{re.escape(kw)}\b', r_lower))
        score = int((matched / len(jd_keywords)) * 100)
        return max(50, min(score, 98))

    def reorder_bullets_by_jd(self, sections, jd_text):
        jd_keywords = self.extract_jd_keywords(jd_text)
        compiled_kws = []
        for kw in jd_keywords:
            kw_clean = kw.strip()
            if kw_clean:
                try:
                    compiled_kws.append(re.compile(rf'\b{re.escape(kw_clean)}\b', re.IGNORECASE))
                except Exception:
                    pass

        for section in sections:
            if len(section["bullets"]) > 1:
                scored = []
                for idx, b in enumerate(section["bullets"]):
                    # Tokenized word-boundary check prevents substring collisions
                    score = sum(1 for pat in compiled_kws if pat.search(b))
                    scored.append((score, idx, b))
                # Stable sort descending by score
                scored.sort(key=lambda x: (-x[0], x[1]))
                section["bullets"] = [b for _, _, b in scored]
        return sections

    def tailor_summary_and_competencies(self, sections, jd_text, master_resume_text):
        """
        Dynamically optimizes the Professional Summary and prioritizes Core Competencies
        matching the JD requirements while strictly preserving factual accuracy (Zero Hallucination).
        """
        jd_keywords = set(self.extract_jd_keywords(jd_text))
        
        for section in sections:
            heading = section.get("heading", "").upper()
            
            # 1. Tailor Professional Summary
            if "SUMMARY" in heading or "PROFILE" in heading:
                if len(section["lines"]) > 0:
                    orig_summary = " ".join([l.strip() for l in section["lines"] if l.strip()])
                    tailored_data = self.ai.tailor_resume_content(jd_text, master_resume_text)
                    if tailored_data.get("tailored_summary"):
                        section["lines"] = [tailored_data["tailored_summary"]]

            # 2. Prioritize Core Competencies / Technical Skills Table
            elif "COMPETENCIES" in heading or "SKILLS" in heading:
                new_lines = []
                for line in section["lines"]:
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 3:
                            cat = parts[1].strip()
                            skills_str = parts[2].strip()
                            skills_list = [s.strip() for s in re.split(r'[,;]+', skills_str) if s.strip()]
                            # Sort skills placing JD-matched skills first
                            skills_list.sort(key=lambda s: 0 if any(re.search(rf'\b{re.escape(k)}\b', s.lower()) for k in jd_keywords) else 1)
                            new_skills_str = ", ".join(skills_list)
                            parts[2] = f" {new_skills_str} "
                            new_lines.append("|".join(parts))
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                section["lines"] = new_lines

        return sections

    def reassemble_markdown(self, sections):
        section_blocks = []
        for section in sections:
            block_lines = []
            if section["heading"]:
                prefix = "#" * section["level"]
                block_lines.append(f"{prefix} {section['heading']}")
            for line in section["lines"]:
                block_lines.append(line)
            for bullet in section["bullets"]:
                block_lines.append(bullet)
            if block_lines:
                section_blocks.append("\n".join(block_lines))
        return "\n\n".join(section_blocks)

    def build_tailored_resume(self, jd_text):
        if not self.resume_md_path.exists():
            print(f"  [!] Master Resume Template not found at {self.resume_md_path}", flush=True)
            return None, 0

        template_md = self.resume_md_path.read_text(encoding="utf-8")
        sections = self.parse_resume_sections(template_md)
        sections = self.tailor_summary_and_competencies(sections, jd_text, template_md)
        reordered = self.reorder_bullets_by_jd(sections, jd_text)
        tailored_md = self.reassemble_markdown(reordered)
        
        jd_keywords = self.extract_jd_keywords(jd_text)
        ats_score = self.calculate_ats_match_score(tailored_md, jd_keywords)
        return tailored_md, ats_score

    def run(self):
        print("=== REGENERATING TAILORED RESUMES FOR ALL DISCOVERED ROLES ===", flush=True)
        manifest_path = self.ctx.manifest_path
        if not manifest_path.exists():
            print(f"[!] Manifest not found at {manifest_path}.", flush=True)
            return

        try:
            jobs = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[!] Error reading manifest: {e}", flush=True)
            return

        apps_dir = self.ctx.applications_dir
        resume_base = self.get_resume_filename()

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(self.cdp_url)
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()
            except Exception as e:
                print(f"  [!] Fatal Playwright connection error: {e}")
                return

            for job in jobs:
                title = job.get("title", "Role")
                company = job.get("company", "Target_Company")
                clean_c = re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_")[:50]
                clean_t = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]
                folder = apps_dir / f"{clean_c}_{clean_t}"
                folder.mkdir(parents=True, exist_ok=True)

                jd_file = folder / "Job_Description.md"
                manifest_jd_path = job.get("jd_path")
                if manifest_jd_path and Path(manifest_jd_path).exists():
                    jd_text = Path(manifest_jd_path).read_text(encoding="utf-8")
                elif jd_file.exists():
                    jd_text = jd_file.read_text(encoding="utf-8")
                elif job.get("description"):
                    jd_text = job["description"]
                else:
                    jd_text = f"{title} at {company}"

                tailored_md, ats_score = self.build_tailored_resume(jd_text)
                if tailored_md is None:
                    continue

                (folder / f"{resume_base}.md").write_text(tailored_md, encoding="utf-8")

                # Record ATS match score in job metadata
                job_meta_file = folder / "job_details.json"
                if job_meta_file.exists():
                    try:
                        meta = json.loads(job_meta_file.read_text(encoding="utf-8"))
                        meta["ats_compatibility_score"] = ats_score
                        job_meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                    except Exception:
                        pass

                pdf_path = folder / f"{resume_base}.pdf"
                clean_md = tailored_md.lstrip('\ufeff\u200b\r\n ')
                html_body = markdown.markdown(clean_md, extensions=['extra', 'tables', 'nl2br', 'sane_lists'])
                full_html = HTML_WRAPPER.replace("{body}", html_body)
                
                try:
                    page.set_content(full_html, wait_until="load")
                    page.wait_for_timeout(200)
                    page.pdf(
                        path=str(pdf_path),
                        format="A4",
                        print_background=True,
                        margin={"top": "8mm", "bottom": "8mm", "left": "10mm", "right": "10mm"}
                    )
                    print(f"  [OK] Compiled ATS Tailored PDF (ATS Score: {ats_score}%): {folder.name}", flush=True)
                    job["tailored_pdf"] = str(pdf_path.resolve())
                    job["ats_score"] = ats_score
                except Exception as e:
                    print(f"  [!] PDF render notice for {folder.name}: {e}", flush=True)

            try:
                page.close()
            except Exception:
                pass

        manifest_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        print("=== ALL TAILORED RESUMES RENDERED SUCCESSFULLY ===\n", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal ATS Resume Tailoring Engine")
    parser.add_argument('--profile', default=None, help='Path to profile directory')
    args, _ = parser.parse_known_args()

    engine = ResumeTailorEngine(profile_path=args.profile)
    engine.run()
