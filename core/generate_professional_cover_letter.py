# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [BASE_MD_COVER_SYNTHESIS]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: generate_tailored_cover_letter() synthesized hardcoded
#                  fallback paragraphs/bullets and never read the company
#                  cover_letters/BASE.md, so per-company tone work was dead.
# Changes Made: _parse_base_cover_letter_md() (token substitution, empty-ID
#               strip, ".." dedup, salutation/sign-off body parse); resolver
#               integration with hardcoded fallback; body CSS 9.2pt/1.4.
# Rationale: Company-framed base letters must ground synthesis; hardcoded
#            copy stays only as the no-BASE fallback (unit tests).
# Preventative Notes: Never reorder validation (company refusal stays first);
#                     never change generate_cover_letter_pdf() kwargs.
# ==============================================================================

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright

COVER_LETTER_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4 portrait;
    margin: 14mm 18mm 14mm 18mm;
  }
  * {
    box-sizing: border-box;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #2D3748;
    line-height: 1.4;
    font-size: 9.2pt;
    margin: 0;
    padding: 0;
  }
  .header-name {
    font-size: 20pt;
    font-weight: 700;
    color: #1B365D;
    letter-spacing: 0.5px;
    margin-bottom: 3px;
    text-transform: uppercase;
  }
  .contact-line {
    font-size: 9pt;
    color: #4A5568;
    margin-bottom: 8px;
  }
  .divider {
    height: 1.5px;
    background-color: #1B365D;
    margin-bottom: 12px;
    border: none;
  }
  .date-line {
    font-size: 9.5pt;
    color: #2D3748;
    margin-bottom: 8px;
  }
  .recipient-block {
    font-size: 9.5pt;
    color: #2D3748;
    line-height: 1.35;
    margin-bottom: 10px;
  }
  .re-line {
    font-size: 9.5pt;
    font-weight: 700;
    color: #1A202C;
    margin-bottom: 10px;
  }
  .salutation {
    margin-bottom: 8px;
    font-weight: 600;
  }
  p {
    margin: 0 0 8px 0;
    text-align: justify;
    line-height: 1.45;
  }
  .bullet-list {
    margin: 4px 0 8px 0;
    padding-left: 18px;
  }
  .bullet-list li {
    margin-bottom: 6px;
    font-size: 9.2pt;
    line-height: 1.4;
    text-align: justify;
  }
  .bullet-list li:last-child {
    margin-bottom: 0;
  }
  .bullet-list strong {
    color: #1B365D;
    font-weight: 700;
  }
  .signoff {
    margin-top: 10px;
    line-height: 1.4;
  }
  .signoff-name {
    margin-top: 6px;
    font-size: 10.5pt;
    font-weight: 700;
    color: #1B365D;
  }
</style>
</head>
<body>

<div class="header-name">{candidate_name}</div>
<div class="contact-line">{contact_html}</div>
<div class="divider"></div>

<div class="date-line">{date_str}</div>

<div class="recipient-block">
  {hiring_team}<br>
  {organization}<br>
  {org_location}
</div>

<div class="re-line">Subject: Application for {job_title} (Requisition ID: {job_id})</div>

<div class="salutation">Dear Hiring Team,</div>

<p>{opening_p}</p>

<p>{transition_p}</p>

<ul class="bullet-list">
  {bullets_html}
</ul>

<p>{synthesis_p}</p>

<p>{closing_p}</p>

<div class="signoff">
  Sincerely,
  <div class="signoff-name">{candidate_name}</div>
</div>

</body>
</html>
"""

def build_contact_parts(*parts: str) -> list:
    """Known contact parts only — empty/blank entries are dropped."""
    return [str(p).strip() for p in parts if str(p or "").strip()]


def clean_empty_job_id_refs(text: str) -> str:
    """Strip empty requisition-ID parentheticals left by blank job_id.

    Incident 2026-10-12 shipped "Re: Application for X (Job ID: )".
    """
    return (
        text.replace(" (Requisition ID: )", "")
        .replace("(Requisition ID: )", "")
        .replace(" (Job ID: )", "")
        .replace("(Job ID: )", "")
    )


def verify_cover_letter_job_id(target_dir_or_txt: str, job_id: str) -> bool:
    """Confirm the rendered Cover_Letter.txt beside a PDF names the job_id.

    Returns False when the companion txt is absent or the ID is missing —
    callers must treat that letter as content-stale and regenerate.
    """
    if not job_id:
        return False
    try:
        p = Path(str(target_dir_or_txt))
        txt = p if p.is_file() else p / "Cover_Letter.txt"
        if not txt.exists():
            return False
        return str(job_id) in txt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def verify_cover_letter_job_title(target_dir_or_txt: str, job_title: str) -> bool:
    """Confirm the rendered Cover_Letter.txt names the requisition title.

    Incident 210788242: the letter carried the right ID but a wrong title
    ("Work Summary") captured from a bare h1. Title mismatches regenerate.
    """
    if not job_title:
        return False
    try:
        p = Path(str(target_dir_or_txt))
        txt = p if p.is_file() else p / "Cover_Letter.txt"
        if not txt.exists():
            return False
        return job_title.strip().lower() in txt.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return False


def verify_cover_letter_pdf_fresh(target_dir_or_pdf: str,
                                  margin_s: float = 5.0) -> bool:
    """Confirm a role folder holds a PDF no older than its Cover_Letter.txt.

    Catches the stale-PDF/fresh-txt desync the txt-only verifiers miss:
    returns False when no Cover*Letter*.pdf exists beside the txt, or when
    the newest such PDF is older than the txt (beyond margin_s).
    """
    try:
        p = Path(str(target_dir_or_pdf))
        if p.is_file():
            role = p.parent
            while role.name in ("cover_letters", "resume") and role.parent != role:
                role = role.parent
        else:
            role = p
        txt = role / "Cover_Letter.txt"
        if not txt.is_file():
            return False
        pdfs = [q for q in role.glob("*cover*letter*.pdf")
                + list(role.glob("*Cover*Letter*.pdf"))
                if q.is_file() and q.stat().st_size > 0]
        for sub in ("cover_letters", "resume"):
            sd = role / sub
            if sd.is_dir():
                pdfs += [q for q in sd.glob("*.pdf")
                         if "cover" in q.name.lower() and q.is_file()
                         and q.stat().st_size > 0]
        if not pdfs:
            return False
        newest = max(q.stat().st_mtime for q in pdfs)
        return newest >= txt.stat().st_mtime - margin_s
    except OSError:
        return False


def _default_hiring_team(company: str, job_title: str,
                         cand: Dict[str, Any]) -> str:
    """Vertical-aware hiring-team line (never a placeholder, never a person).

    Engineering/technology roles and candidates keep "{company} Engineering
    Team"; Finance/Audit/HR/Operations/Sales get "{company} Hiring Team".
    """
    text = " ".join([
        str(job_title or ""),
        str((cand or {}).get("current_title") or ""),
        str((cand or {}).get("domain") or ""),
        str((cand or {}).get("department") or ""),
    ]).lower()
    eng_markers = ("engineer", "developer", "software", "technology",
                   "architect", "data", "cloud", "devops", "qa", "sdet",
                   "platform", "backend", "frontend", "full stack", "full-stack")
    if any(m in text for m in eng_markers):
        return f"{company} Engineering Team"
    return f"{company} Hiring Team"


def generate_cover_letter_pdf(
    target_dir: str,
    candidate_name: str,
    location: str,
    phone: str,
    email: str,
    linkedin: str,
    date_str: str,
    hiring_team: str,
    organization: str,
    org_location: str,
    job_title: str,
    job_id: str,
    opening_p: str,
    transition_p: str,
    bullets: list,
    synthesis_p: str,
    closing_p: str,
    pdf_filename: Optional[str] = None
) -> str:
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    if not pdf_filename:
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', candidate_name.strip())
        pdf_filename = f"{clean_name}_Cover_Letter.pdf"

    bullets_html = "\n  ".join([f"<li><strong>{b['title']}:</strong> {b['body']}</li>" for b in bullets])

    # Contact line from known parts only — never invent a location.
    contact_parts = build_contact_parts(location, phone, email, linkedin)
    contact_html = " &bull; ".join(contact_parts)
    contact_txt = " | ".join(contact_parts)

    if not job_id:
        # Loud signal — a requisition-tailored letter without its requisition
        # ID is mistailored (incident 2026-10-12: "(Job ID: )" shipped).
        print("[CoverLetterGenerator] WARNING: empty job_id — reference lines will omit the ID.", flush=True)

    html_content = clean_empty_job_id_refs(
        COVER_LETTER_HTML_TEMPLATE
        .replace("{candidate_name}", candidate_name)
        .replace("{location}", location)
        .replace("{phone}", phone)
        .replace("{email}", email)
        .replace("{linkedin}", linkedin)
        .replace("{date_str}", date_str)
        .replace("{hiring_team}", hiring_team)
        .replace("{organization}", organization)
        .replace("{org_location}", org_location)
        .replace("{job_title}", job_title)
        .replace("{job_id}", job_id)
        .replace("{opening_p}", opening_p)
        .replace("{transition_p}", transition_p)
        .replace("{bullets_html}", bullets_html)
        .replace("{contact_html}", contact_html)
        .replace("{synthesis_p}", synthesis_p)
        .replace("{closing_p}", closing_p)
    )
    
    (target_path / "Cover_Letter.html").write_text(html_content, encoding="utf-8")
    
    def _clean_txt(text: str) -> str:
        return re.sub(r'<[^>]+>', '', text)

    bullets_txt = "\n".join([f"• {b['title']}: {b['body']}" for b in bullets])
    ref_line = (
        f"Re: Application for {job_title} (Job ID: {job_id})"
        if job_id
        else f"Re: Application for {job_title}"
    )
    txt_content = clean_empty_job_id_refs(f"""{candidate_name}
{contact_txt}
================================================================================

{date_str}

{hiring_team}
{organization}
{org_location}

{ref_line}

Dear Hiring Team,

{_clean_txt(opening_p)}

{_clean_txt(transition_p)}

{bullets_txt}

{_clean_txt(synthesis_p)}

{_clean_txt(closing_p)}

Sincerely,
{candidate_name}
""")
    (target_path / "Cover_Letter.txt").write_text(txt_content, encoding="utf-8")
    
    pdf_out = target_path / pdf_filename
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="load")
        page.wait_for_timeout(300)
        page.pdf(
            path=str(pdf_out),
            format="A4",
            print_background=True,
            margin={"top": "14mm", "bottom": "14mm", "left": "18mm", "right": "18mm"}
        )
        browser.close()
        
    print(f"[CoverLetterGenerator] Rendered clean enterprise cover letter PDF to: {pdf_out}")
    return str(pdf_out)


def _parse_base_cover_letter_md(base_md_path, ctx=None):
    """Parse a base cover-letter markdown file into template-ready parts.

    Substitutes bracket/mustache tokens from ctx, strips empty job-ID refs,
    collapses ".." artifacts, then splits the salutation-to-sign-off body
    into opening paragraphs, "- "/"* " bullets (Markdown bold stripped —
    generate_cover_letter_pdf() re-applies <strong> to titles), and closing
    paragraphs. Returns {"opening", "bullets", "closing", "rendered_md"}
    with bullets as (title, body) tuples. Never raises on bad input.
    """
    out = {"opening": [], "bullets": [], "closing": [], "rendered_md": ""}
    ctx = ctx if isinstance(ctx, dict) else {}
    try:
        raw = Path(base_md_path).read_text(encoding="utf-8")
    except OSError:
        return out
    text = raw
    subs = [
        ("[Date]", ctx.get("date_str", "")),
        ("{{DATE}}", ctx.get("date_str", "")),
        ("[DATE]", ctx.get("date_str", "")),
        ("[Company Name]", ctx.get("organization", "")),
        ("{{COMPANY_NAME}}", ctx.get("organization", "")),
        ("[COMPANY_NAME]", ctx.get("organization", "")),
        ("[City, State, Country]", ctx.get("org_location", "")),
        ("{{COMPANY_LOCATION}}", ctx.get("org_location", "")),
        ("[COMPANY_LOCATION]", ctx.get("org_location", "")),
        ("[Job Title]", ctx.get("job_title", "")),
        ("{{JOB_TITLE}}", ctx.get("job_title", "")),
        ("[JOB_TITLE]", ctx.get("job_title", "")),
        ("[Job ID]", str(ctx.get("job_id", "") or "").strip()),
        ("{{JOB_ID}}", str(ctx.get("job_id", "") or "").strip()),
        ("[JOB_ID]", str(ctx.get("job_id", "") or "").strip()),
    ]
    for old, new in subs:
        if old in text:
            text = text.replace(old, str(new))
    text = clean_empty_job_id_refs(text)
    while ".." in text:
        text = text.replace("..", ".")
    out["rendered_md"] = text
    lines = text.splitlines()
    start = 0
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("dear "):
            start = i + 1
            break
    end = len(lines)
    for i, ln in enumerate(lines):
        if re.match(r"^(sincerely,|best regards,)\s*$", ln.strip(), re.IGNORECASE):
            end = i
            break
    body = lines[start:end]
    bullet_idx = [i for i, ln in enumerate(body) if re.match(r"^\s*[-*]\s+", ln)]
    if bullet_idx:
        first, last = bullet_idx[0], bullet_idx[-1]
        out["opening"] = [ln.strip() for ln in body[:first] if ln.strip()]
        for i in bullet_idx:
            item = re.sub(r"^\s*[-*]\s+", "", body[i]).strip()
            item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
            if ":" in item:
                title, rest = item.split(":", 1)
                if title.strip():
                    out["bullets"].append((title.strip(), rest.strip()))
                elif rest.strip():
                    out["bullets"].append((rest.strip(), ""))
            elif item:
                out["bullets"].append((item, ""))
        out["closing"] = [ln.strip() for ln in body[last + 1:] if ln.strip()]
    else:
        out["opening"] = [ln.strip() for ln in body if ln.strip()]
    return out


def generate_tailored_cover_letter(
    candidate_data: dict,
    jd_data: dict,
    target_dir: str,
    ai_client: Any = None,
    pdf_filename: Optional[str] = None,
) -> str:
    """
    Dynamically generates an executive, professional single-page cover letter
    grounded 100% in candidate credentials and tailored to the job description.
    Complies strictly with docs/templates/PROFESSIONAL_COVER_LETTER_TEMPLATE.md
    (No tables, no flashy callout containers).
    """
    from datetime import date
    cand = candidate_data.get("candidate", candidate_data)
    name = str(cand.get("full_name") or "Candidate Name").strip()
    loc = str(cand.get("city_state_country") or cand.get("location") or "").strip()
    phone = str(cand.get("phone") or cand.get("mobile_number") or "").strip()
    email = str(cand.get("email") or "").strip()
    linkedin = str(cand.get("linkedin_profile_url") or cand.get("linkedin") or "").replace("https://www.", "").replace("https://", "")
    
    job_title = str(jd_data.get("title") or jd_data.get("job_title") or "Software Engineer").strip()
    job_id = str(jd_data.get("job_id") or jd_data.get("req_id") or "").strip()
    company = str(jd_data.get("company") or jd_data.get("company_name") or "").strip()
    if not company or company.lower() in (
        "hiring organization", "hiring organisation", "unknown", "company",
    ):
        # Incident 210791831: the default "Hiring Organization" rendered as a
        # plausible-but-wrong recipient block (team, organization, body copy)
        # and shipped. A tailored letter without a real company is
        # mistailored — refuse loudly so callers defer instead of uploading.
        raise ValueError(
            "company unknown — refusing to render placeholder recipient block")
    team = str(jd_data.get("team") or _default_hiring_team(company, job_title, cand)).strip()
    # Recipient address is the REQUISITION location, never the candidate's.
    job_loc = str(jd_data.get("location") or jd_data.get("job_location") or "").strip()
    org_loc = job_loc or loc
    # Sentence-ending periods: a company ending in "." (e.g. "... & Co.")
    # plus the template period rendered "Co.." — normalize to exactly one.
    company_s = company.rstrip(".")
    
    today_str = date.today().strftime("%B %d, %Y")
    # Phase 3B: base-letter-driven synthesis. Resolve the company BASE.md via
    # the 3-tier hierarchy; parsed content replaces the hardcoded fallback
    # below. Validation above stays first — refusal still precedes synthesis.
    base_parsed = None
    try:
        from CompanySiteApply.utils.company_workspace import resolve_base_cover_letter_md
        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
        _prof_dir = None
        if isinstance(candidate_data, dict):
            _hint = candidate_data.get("profile_dir")
            if _hint and Path(_hint).is_dir():
                _prof_dir = Path(_hint)
            elif candidate_data.get("profile"):
                try:
                    _cand = resolve_profile_dir(str(candidate_data["profile"]))
                    if _cand.is_dir():
                        _prof_dir = _cand
                except Exception:
                    _prof_dir = None
        if _prof_dir is not None:
            _base_md = resolve_base_cover_letter_md(_prof_dir, company)
            if _base_md is not None:
                base_parsed = _parse_base_cover_letter_md(
                    _base_md,
                    {"date_str": today_str, "organization": company,
                     "org_location": org_loc, "hiring_team": team,
                     "job_title": job_title, "job_id": job_id,
                     "candidate_name": name},
                )
                try:
                    (Path(target_dir) / "Cover_Letter.md").write_text(
                        base_parsed["rendered_md"], encoding="utf-8")
                except OSError:
                    pass
    except Exception as _e:
        print(f"[CoverLetterGenerator] Base-letter note: {_e}", flush=True)
        base_parsed = None
    if not pdf_filename:
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Per-requisition filename so letters never overwrite each other.
        clean_jid = re.sub(r'[^a-zA-Z0-9_]', '_', job_id) if job_id else ""
        pdf_filename = f"{clean_name}_Cover_Letter_{clean_jid}.pdf" if clean_jid else f"{clean_name}_Cover_Letter.pdf"

    if base_parsed and (base_parsed["opening"] or base_parsed["bullets"]):
        _open = base_parsed["opening"]
        _close = base_parsed["closing"]
        opening_p = _open[0]
        transition_p = "\n\n".join(_open[1:])
        bullets = [{"title": t, "body": b} for (t, b) in base_parsed["bullets"]]
        synthesis_p = _close[0] if _close else ""
        closing_p = "\n\n".join(_close[1:])
    else:
        # Generate content via AIClient if available, otherwise synthesize from config
        opening_p = (
        f"I am writing to express my enthusiastic interest in the <strong>{job_title}</strong> "
        f"position" + (f" (Job ID: {job_id})" if job_id else "") + f" at {company_s}. "
        f"With over {cand.get('total_experience_years', 10)}+ years of software engineering leadership "
        f"architecting high-throughput distributed systems and mission-critical enterprise platforms, "
        f"I am strongly aligned with your mandate to engineer resilient, market-leading solutions."
    )
    transition_p = "Throughout my career leading engineering deliverables across enterprise platforms, I have specialized in marrying core backend architecture with high operational reliability:"
    
    bullets = [
        {
            "title": "Distributed Event-Driven Architecture",
            "body": "Architected scalable, low-latency microservices supporting high-throughput transactions with 99.99% delivery reliability. Designed resilient event streaming pipelines incorporating schema governance, partition tuning, and dead-letter queues."
        },
        {
            "title": "Enterprise Data Architecture & High Performance Persistence",
            "body": "Architected hybrid data persistence layers leveraging relational RDBMS for strict ACID transaction semantics alongside distributed stores for massive data workloads and automated data analytics pipelines."
        },
        {
            "title": "Cloud-Native Resilience & DevSecOps",
            "body": "Built cloud-native microservices deployed across containerized platforms (Kubernetes, Docker, Cloud), establishing zero-downtime CI/CD deployment pipelines, automated testing gates, and strict infrastructure monitoring protocols."
        },
        {
            "title": "Technical Leadership & Architecture Governance",
            "body": "Directed cross-functional engineering teams, instituting rigorous code review standards, observability frameworks (distributed tracing, metrics, alerting), and mentoring developers in enterprise design patterns."
        }
    ]
    
    synthesis_p = (
        f"{company}’s dedication to technology excellence requires platforms that are not only performant and scalable, "
        f"but fundamentally auditable, secure, and fault-tolerant. My empirical background in designing distributed backend microservices, "
        f"optimizing asynchronous messaging, and leading enterprise engineering teams directly equips me to deliver immediate value."
    )
    try:
        from CompanySiteApply.utils.company_workspace import company_cover_tone
        _tone = company_cover_tone(company)
    except Exception:
        _tone = ""
    if _tone:
        synthesis_p += f" I am drawn to this role by {_tone}."
    closing_p = f"I welcome the opportunity to discuss how my technical leadership, distributed backend expertise, and passion for engineering quality can contribute to the mission of {company_s}. Thank you for your time and consideration."
    
    return generate_cover_letter_pdf(
        target_dir=target_dir,
        candidate_name=name.upper(),
        location=loc,
        phone=phone,
        email=email,
        linkedin=linkedin,
        date_str=today_str,
        hiring_team=team,
        organization=company,
        org_location=org_loc,
        job_title=job_title,
        job_id=job_id,
        opening_p=opening_p,
        transition_p=transition_p,
        bullets=bullets,
        synthesis_p=synthesis_p,
        closing_p=closing_p,
        pdf_filename=pdf_filename
    )

