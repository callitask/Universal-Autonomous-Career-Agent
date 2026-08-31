#!/usr/bin/env python3
"""
================================================================================
GENERATE_FACTUAL_TAILORED.py
Universal Template-Driven ATS Resume Tailoring Engine
================================================================================
Reads the user's Master Resume Template (Markdown), parses it into sections,
scores bullet points against each Job Description's keywords, reorders the
most relevant bullets to the top of each section, and renders a customized
A4 PDF via Playwright/Chromium CDP.

Optimized to reuse a single CDP browser connection for the entire batch.
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
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.utils.profile_context import ProfileContext

HTML_WRAPPER = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 10mm 12mm 10mm 12mm;
  }
  body {
    font-family: 'Segoe UI', Calibri, Arial, Helvetica, sans-serif;
    font-size: 9pt;
    line-height: 1.34;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
  }
  h1 {
    font-size: 17pt;
    margin: 0 0 3px 0;
    color: #0d233a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    text-align: center;
    font-weight: 700;
  }
  h2 {
    font-size: 10pt;
    margin: 7px 0 3px 0;
    border-bottom: 1.2px solid #2b6cb0;
    padding-bottom: 1.5px;
    text-transform: uppercase;
    color: #1a365d;
    font-weight: 700;
    letter-spacing: 0.3px;
  }
  h3 {
    font-size: 9.5pt;
    margin: 4px 0 2px 0;
    color: #2d3748;
    font-weight: 600;
  }
  p {
    margin: 2px 0 3px 0;
  }
  h1 + p {
    text-align: center;
    font-size: 8.5pt;
    color: #334155;
    margin-bottom: 6px;
    line-height: 1.35;
  }
  ul {
    margin: 2px 0 4px 14px;
    padding: 0;
  }
  li {
    margin-bottom: 2px;
    line-height: 1.32;
  }
  strong {
    color: #0d233a;
  }
  hr {
    border: 0;
    border-top: 1px solid #cbd5e0;
    margin: 4px 0;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 4px 0;
  }
  th, td {
    border: 1px solid #cbd5e0;
    padding: 2.5px 5px;
    font-size: 8.5pt;
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
        words = re.findall(r'[a-z][a-z\-]+', jd_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        for i in range(len(words) - 1):
            if words[i] not in stop_words or words[i+1] not in stop_words:
                keywords.append(f"{words[i]} {words[i+1]}")

        for category, skills in self.cfg.get("taxonomy_skills", {}).items():
            if isinstance(skills, list):
                for skill in skills:
                    # M2 Fix: Use word boundary to avoid false substring injection
                    if re.search(rf'\b{re.escape(skill.lower())}\b', jd_lower):
                        keywords.append(skill.lower())

        return list(set(keywords))

    def reorder_bullets_by_jd(self, sections, jd_text):
        jd_keywords = self.extract_jd_keywords(jd_text)
        for section in sections:
            if len(section["bullets"]) > 1:
                scored = []
                for b in section["bullets"]:
                    b_lower = b.lower()
                    score = sum(1 for kw in jd_keywords if kw in b_lower)
                    scored.append((score, b))
                scored.sort(key=lambda x: x[0], reverse=True)
                section["bullets"] = [b for _, b in scored]
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
            return None

        template_md = self.resume_md_path.read_text(encoding="utf-8")
        sections = self.parse_resume_sections(template_md)
        reordered = self.reorder_bullets_by_jd(sections, jd_text)
        return self.reassemble_markdown(reordered)

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

        # H10 Fix: Establish single CDP connection for the entire batch
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
                jd_text = jd_file.read_text(encoding="utf-8") if jd_file.exists() else f"{title} at {company}"

                tailored_md = self.build_tailored_resume(jd_text)
                if tailored_md is None:
                    continue

                (folder / f"{resume_base}.md").write_text(tailored_md, encoding="utf-8")

                pdf_path = folder / f"{resume_base}.pdf"
                
                # Render via active page
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
                    print(f"  [OK] Compiled PDF: {folder.name}", flush=True)
                    job["tailored_pdf"] = str(pdf_path.resolve())
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
    # M11 Fix: Do not default to a hardcoded path. Force ProfileContext dynamic resolution.
    parser.add_argument('--profile', default=None, help='Path to profile directory')
    args, _ = parser.parse_known_args()

    engine = ResumeTailorEngine(profile_path=args.profile)
    engine.run()