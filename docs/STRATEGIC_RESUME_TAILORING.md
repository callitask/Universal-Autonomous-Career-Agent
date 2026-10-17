# STRATEGIC RESUME TAILORING ARCHITECTURE & COMPILATION GOVERNANCE
# Version: 1.2 | Upgraded: 2026-10-17 | Universal Autonomous Career Agent

---

## 1. Core Philosophy: Strategy Over Blind Keyword Stuffing

Resume tailoring is **NOT** blindly copying and pasting lines, buzzwords, or verbatim requirement sentences from the Job Description into the candidate's resume. 

Blind copy-pasting causes two catastrophic failure modes:
1. **Semantic ATS Downgrades**: Modern ATS engines (Oracle HCM, Workday, Greenhouse with integrated semantic AI) flag verbatim JD phrasing as artificially stuffed or low-relevance spam.
2. **Hiring Manager Rejection**: Senior Engineering Directors and Hiring Managers immediately spot generic, keyword-stuffed resumes that lack authentic operational nuance, resulting in instant pre-interview rejections.

**True Tailoring is Strategic Re-Alignment**:
* Identifying the target role's **Architectural Archetype** (e.g. Distributed Systems Lead, Enterprise Integration Architect, Cloud Modernization Lead).
* Aligning the candidate's **authentic, verifiable work history** to demonstrate exact technical domain depth, architectural scale, and high-velocity delivery in those specific focus areas.
* Never inventing fake credentials, never exaggerating timelines, and never stripping foundational career evidence.

**Zero-Omission Guarantee:** tailoring reorders, highlights, and re-frames existing bullets only — it never drops, truncates, or merges them. Every build runs `_enforce_content_preservation()` (`core/generate_factual_tailored.py`): on the non-reframe path it diffs output bullets against the master resume and loudly logs + restores anything missing (identical text preserved); on the AI-reframe path it enforces count equality plus numbers/tech-token validation and logs count drift without restoring reworded text. Forensically verified: no bullet is ever silently dropped.

**AI Bullet Reframing (brain proposes, Python disposes):** each employment role's bullets are sent to the AI brain (`ai_client.reframe_role_bullets`), which rewrites them weaving JD terminology where truthfully applicable — same count, same order, same facts. Python then validates per role before accepting: (a) bullet count equality (nothing skipped), (b) every number already existed in the originals (no invented metrics), (c) every distinctive tech token exists in the master resume or the JD (no new stack → interview-safe). Any violation keeps the original bullets untouched. Newly introduced Capitalized words are logged to terminal for owner audit. Returned sentences are normalized back to bullet markers (models strip them). Skipped silently when no API brain exists (offline runs keep originals, never stall). Toggle per profile via `target_jobs.resume_bullet_reframing`: `true` = always reframe, `false`/`fast` = summary+skills reorder only, `"auto"` (default) = reframe only in pure AG Brain/IPC mode and stay fast on Gemini/Colab API runs (volume-safe: no ~10-minute per-job rewrite grind).

---

## 2. The Dual-Identity Architectural Balance

For Senior, Lead, Staff, and Principal engineering roles (such as JPMorgan Chase *Senior Lead Software Engineer*), the resume must project a unified **Dual-Identity**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE UNIFIED DUAL-IDENTITY TALENT PROFILE                        │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│   PILLAR 1: ARCHITECTURAL LEADERSHIP     │    PILLAR 2: MODERN HANDS-ON AI VELOCITY    │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ • Quantifiable Leadership Metrics        │ • Dedicated AI-Assisted Tooling Category    │
│   (e.g., 30-40 candidate interviews,    │   (GitHub Copilot, Prompt Engineering,      │
│    20-engineer cross-functional teams)   │    Unit Test Synthesis, AI-Augmented SDLC)  │
│ • Full Depth in Earlier Career Roles     │ • Modern Hands-On Engineering Delivery      │
│   (Foundational backend, query tuning)   │   (Java 17/21, Spring Boot, Kafka, AWS)     │
│ • Granular Timeline Continuity           │ • AI-Augmented Quality Engineering          │
│   (Split internship records: IRCTC, NEC) │   (Accelerated test cycles, automated mocks)│
│ • Verifiable Certification Credential IDs│ • Continuous Cloud Delivery                 │
│   (Infosys Security & Privacy IDs)       │   (OpenShift, Zero-downtime CI/CD)          │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

### The Non-Negotiables:
1. **Never sacrifice Pillar 1 for Pillar 2**: Do not trim or collapse older roles (e.g. Navyug Infosolutions, Adobe, IBM), recruitment metrics, or governance responsibilities just to mention modern buzzwords.
2. **Never sacrifice Pillar 2 for Pillar 1**: Do not present a purely theoretical manager profile. Modern tech leaders must demonstrate active adoption of developer productivity tools (GitHub Copilot, automated test synthesis).

---

## 3. The 4 Golden Rules of Resume Tailoring

### Rule 1: Zero Truncation of Verified Career History
* **Older Roles**: Earlier career stages (Navyug Infosolutions, Adobe, IBM) provide proof of algorithmic and systems foundations. They must never be collapsed into a single vague line.
* **Internships**: Split distinct internships (e.g., IRCTC vs. NEC Technologies) with full context (Java EE web modules, SDLC participation, CMS/LMS architecture).
* **Credential IDs**: Always preserve explicit certification verification numbers (e.g. `Credential ID: X3RROAJSN6`).

### Rule 2: Strict 2-Page A4 Budget
Resumes for experienced professionals (8–12+ years) must be **exactly 2 pages** — never 1 page (too thin/lossy), never 3 pages (recruiter drop-off):
* **Page Size**: Standard A4.
* **Margins**: Exact `6mm 10mm 6mm 10mm`.
* **Typography**: Clean system font stack (`Segoe UI`, `Calibri`, `Helvetica`, `Arial`) with base size `8.3pt` and `1.26` line height.
* **Single-Line Contact Header**: The header mirrors the master resume's contact lines verbatim on **one single line** directly below the candidate's name (e.g. `**Phone:** +91-... | **Email:** ... | **LinkedIn:** ...`). Location renders only when the master contact block carries it — never injected by the renderer. In CSS, style with `white-space: nowrap;` and `8.0pt` to conserve vertical height and prevent multi-line header clutter.
* **Vertical Spacing**: Section header margins `4.5px 0 2px 0` with `1.2px` solid divider line. Compact list item spacing (`1.2px`).

### Rule 3: Authentic Semantic Framing
When tailoring for specific job focus areas (e.g. Kafka, AWS, Cassandra):
* Highlight existing candidate achievements involving event-driven patterns, streaming architectures, distributed caches, and NoSQL databases.
* Frame responsibilities using strong, active engineering verbs (*Architected*, *Engineered*, *Spearheaded*, *Orchestrated*, *Refactored*, *Deployed*).

### Rule 4: Isolated & Structured Output Storage
> **Output-path split (by design):** portal-pipeline roles (Naukri/LinkedIn via `core/`) write to `profiles/<profile>/output/applications/<Company>_<Role>/`; direct company-site applications (via `CompanySiteApply/`) write below. Never mix the two trees.
Every tailored resume must be saved strictly in the official company application folder:
```
profiles/<profile_name>/APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/
├── <Stem>_Resume.pdf                     # Exact tailored 2-page PDF (FIXED name, mirrored in resume/)
├── <Stem>_Cover_Letter.pdf               # Tailored Cover Letter (FIXED name, mirrored in cover_letters/)
├── Cover_Letter.txt / Cover_Letter.html  # Role-specific companions (Job ID + title verified)
```

---

## 4. The 5-Phase End-to-End Application Workflow

```
[Phase 1: Ingest & Deconstruct JD]
    │  Extract Requisition ID, Core Tech Stack, Architectural Domain, Leadership Scope
    ▼
[Phase 2: Formulate Tailoring Strategy]
    │  Identify key themes (e.g. Kafka event streaming + Cassandra persistence + Copilot velocity)
    │  Verify zero loss of candidate leadership metrics, older history, or credentials
    ▼
[Phase 3: Compile & Verify 2-Page PDF]
    │  Render HTML via Playwright Chromium print-to-PDF
    │  Verify PDF page count == 2 (Zero overflow)
    ▼
[Phase 4: Portal Application & Auto-Parse Audit]
    │  Upload tailored PDF to Step 1
    │  Inspect each subsequent section (Sections 1 to 4)
    │  Open every editable modal -> compare values against candidate truth -> heal mismatches
    ▼
[Phase 5: Section 4 Document Attachment & Review Gate]
    │  Attach tailored Resume and Cover Letter
    │  Audit 0 validation errors
    │  STOP at Section 4 without clicking final Submit until human review
```

---

## 6. CompanySiteApply Stage 4 — `BASE.md`-Driven Role-Resume Tailoring

The ATS flow applies the same factual-tailoring doctrine deterministically,
per role, with no brain round-trip:

1. **Resolve the base** — `resolve_base_resume_md(profile_dir, company_name)`
   (`CompanySiteApply/utils/company_workspace.py`) walks 4 tiers:
   `company_site_apply/<Slug>/resumes/BASE.md` →
   `company_site_apply/<legacy>/resumes/BASE.md` →
   `company_site_apply/resume.md` → `profile_dir/resume.md`.
   Seeding is 3-tier and **never overwrites** a hand-written base
   (`_is_real_base_md()` rejects `[FIRSTNAME LASTNAME]`, `[FULL NAME]`, and
   `{{FULL_NAME}}`).
2. **Tailor + compile** — `tailor_and_compile_role_resume(..., allow_ipc=False)`
   (`core/generate_factual_tailored.py`) tailors the resolved base into
   `<role_dir>/resume.md` and compiles `<Stem>_Resume.pdf`.
   `allow_ipc=False` keeps the standalone compiler off the IPC brain — the ATS
   run already holds full context, so re-querying AG Brain would add latency
   without adding truth.
3. **Strip audit markers** — `_strip_html_comments()` removes `<!-- ... -->`
   annotation comments before PDF rendering so internal markers never reach the
   employer-facing artifact.
4. **Fallback is explicit** — a master-PDF copy happens **only** when no
   `BASE.md` resolves or compilation fails; it is never a silent default.
5. **Cover letter, same base discipline** —
   `_parse_base_cover_letter_md()` substitutes the `BASE.md` placeholder set
   (including alternate spellings `[Exact Job Title]`, `[Company]`,
   `[Company Location]`), parses `- `/`* `/`• ` bullets into `(title, body)`
   tuples, and emits `Cover_Letter.md`. Company-framed prose reaches the PDF
   untouched; boilerplate synthesis runs only when no `BASE.md` resolved.
6. **Section 3 bullet grounding** — `load_role_bullets_for_employer()`
   (`CompanySiteApply/utils/experience_matcher.py`) sources `Achievements`
   bullets from `<Role>_<jobid>/resume.md` → company `resumes/BASE.md` →
   master `resume.md`, while city/country/dates stay pinned to the structured
   `company_site_profile.employment` / `work_experience` records. Bullets come
   from markdown; the factual spine never does.
