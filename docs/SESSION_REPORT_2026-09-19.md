# Universal Autonomous Career Agent
# Architecture Change Report — G-BRAIN-01 & Guardrail C24
**Document Type:** Engineering Architecture Report
**Date:** 2026-09-19
**Scope:** Core job discovery pipeline — decision-making architecture overhaul

---

## 1. Problem Statement

### What Was Wrong

The agent's job discovery pipeline used **Python keyword lists** to make all match/reject decisions on job cards before the AI ever saw them. This created two persistent failure classes:

#### Failure Class A — False Rejections (Blocking Good Jobs)
A job description containing the phrase `"manage the audits"` would be rejected by the pipeline because `"Manager"` existed in `negative_keywords`. Python matched the word stem, not the intent. The agent would silently skip a legitimate entry-level Audit role because one word in the JD happened to overlap with a seniority term in a list.

#### Failure Class B — False Acceptances (Passing Bad Jobs)
Senior roles with novel title patterns — ones not yet added to any keyword list — would pass through unchecked. No keyword list can be exhaustive. The moment a recruiter uses a slightly different phrasing (`"Finance Analyst Consultant"` instead of `"Senior Finance Analyst"`), the gate fails.

### The Fundamental Design Flaw
**Python was acting as the brain.** The keyword-matching code in `04_job_discovery.py` (`is_title_allowed()`, highlights keyword scan) was making semantic, contextual decisions about job relevance — decisions that require understanding, not pattern matching. A list of strings cannot understand that `"manage the audits"` ≠ `"Manager"`, or that a role titled `"Finance Analyst Consultant"` requires 4–9 years of experience.

---

## 2. Root Cause — The 4-Factor Failure Chain

Beyond keyword gating, a specific incident exposed a second structural gap:

```
FACTOR 1: Thin JD page
  Naukri job page rendered only ~16 lines of visible body text.
  The experience range (e.g., "4-9 Yrs") was in the card metadata
  but NOT reproduced in the scraped JD body text.
        ↓
FACTOR 2: Experience gate blind spot
  evaluate_job_match() ran a regex on full_desc for experience mentions.
  Found 0 matches (because the JD body was sparse).
  Silently awarded 8-point "no experience restriction" bonus.
        ↓
FACTOR 3: Keyword list gap
  The senior seniority indicator in the title was not in negative_keywords.
  is_title_allowed() returned True.
        ↓
FACTOR 4: Score booster fires
  Skill ratio ≥ 0.60 → max(total_score, 65) applied.
  Final score exceeded application threshold.
  Agent applied to a 4–9yr senior role for a fresher candidate.
```

---

## 3. Fixes Implemented — Three Layers

---

### Layer 1 — Guardrail C24: Card-Level Experience Band Gate
**File:** `core/04_job_discovery.py`
**Position:** After salary floor gate, before deep scan

#### What It Does
Reads experience requirements directly from the Naukri SRP card metadata (`exp_text` field, e.g., `"4 - 9 Yrs"`), which is **always populated by the recruiter at job creation** — independent of whether the JD page body renders fully or partially.

Before this fix, experience gating only ran against the scraped JD body text. If the JD body was thin/sparse, the gate found nothing and silently passed the job.

#### How It Works
```python
card_min_exp  = parsed from exp_text (e.g., "4 - 9 Yrs" → 4.0)
candidate_exp = config → candidate.total_experience_years
max_gap       = config → target_jobs.max_experience_gap_years

if card_min_exp > candidate_exp + max_gap:
    REJECT → status: "experience_gap_gated"
```

All values are read from `candidate_config.json` — **zero hardcoded thresholds**, fully profile-agnostic.

#### Principle
> Card metadata is ground truth. JD body text is unreliable. Always gate on card-level data first.

---

### Layer 2 — G-BRAIN-01: AG Brain as Sole Semantic Evaluator
**File:** `core/04_job_discovery.py`
**Commits:** `1a323e2`, `18369ff`

This is the architectural redesign. Full description in Section 4.

---

### Layer 3 — Self-Healing Documentation
- `AI CONTEXT ENTRY #011` in code header: C24 rationale + preventative notes for future agent sessions
- `AI CONTEXT ENTRY #012` in code header: G-BRAIN-01 rationale + hard prohibition on re-introducing keyword gates
- `SCAR_TISSUE.md` (2 new entries): Permanent violation log — any future agent reads these before touching the pipeline
- `ACTIVE_CONSTRAINT_BLOCK.md GATE 11`: Hard rule — cannot be overridden without explicit user approval

---

## 4. Architecture Before vs. After

---

### BEFORE — Python Keyword-Gate Architecture (Removed)

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY PIPELINE (OLD)                      │
└─────────────────────────────────────────────────────────────────┘

  Naukri SRP Page Scraped
  [card_1, card_2, card_3, ... card_N]
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  is_title_allowed()  ← PYTHON KEYWORD GATE            │
  │                                                       │
  │  ① Negative keyword rejection (C6)                    │
  │     → for neg in negative_keywords:                   │
  │         if neg in title.lower(): return False         │
  │  ② Incompatible vertical gate                         │
  │     → for marker in incompatible_verticals:           │
  │         if marker in title: return False              │
  │  ③ Positive stem/prefix match                         │
  │     → if no positive target matches: return False     │
  │  ④ Tier 2B: arbitrate_card_fit() via ai_client        │
  │                                                       │
  │  PROBLEM: Stale lists. "manage" = False. Novel        │
  │  senior titles = True. Semantic nuance: ZERO.         │
  └───────────────────────────────────────────────────────┘
          │
          │  (Most jobs killed here by Python. Many wrongly.)
          ▼
  Salary Floor Gate (numeric — correct)
          │
          ▼
  Deep Scan JD Page
          │
          ▼
  ┌────────────────────────────────────────────────────┐
  │  Highlights keyword scan (3b) ← PYTHON GATE        │
  │  → for neg in negative_keywords:                   │
  │      if neg in highlight_text: REJECT              │
  │  PROBLEM: Same keyword issues, in JD highlights.   │
  └────────────────────────────────────────────────────┘
          │
          ▼
  evaluate_job_match() ← Gemini API scoring
          │
          ▼
  Apply / Skip
```

**What made decisions:** Python `if/else` keyword matching + regex.
**Problems:**
- `"manage the audits"` → blocked (Manager in neg_keywords)
- Novel senior title → passed (not in any list)
- New recruiters using different phrasing → unpredictable results
- List maintenance burden grows forever
- No learning — same mistakes repeated

---

### AFTER — AG Brain Sole Evaluator Architecture (Active)

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY PIPELINE (NEW)                      │
│                    G-BRAIN-01 ACTIVE                            │
└─────────────────────────────────────────────────────────────────┘

  Naukri SRP Page Scraped
  [card_1, card_2, card_3, ... card_N]
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  OBJECTIVE NUMERIC GATES (Python — allowed)           │
  │                                                       │
  │  ① Negative Companies Gate                            │
  │     Exact identity match against company blacklist.   │
  │     Not semantic. "Accenture" == "Accenture". Safe.   │
  │                                                       │
  │  ② Salary Floor Gate                                  │
  │     max_offered_lpa < min_target_ctc_floor → reject   │
  │     Pure numeric. No interpretation needed.           │
  │                                                       │
  │  ③ C24 Exp Band Gate                                  │
  │     card_min_exp > candidate_exp + max_gap → reject   │
  │     Pure numeric. Card metadata is ground truth.      │
  └───────────────────────────────────────────────────────┘
          │
          │  (Only objective gates. No semantic decisions in Python.)
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  JOB_CARD_EVALUATION IPC → AG Brain                   │
  │                                                       │
  │  Python writes to pending_question.json:              │
  │  {                                                    │
  │    task_type: "JOB_CARD_EVALUATION",                  │
  │    candidate_summary: {                               │
  │      total_experience_years, seniority_level,         │
  │      domain, active_search_titles,                    │
  │      advisory_avoid_terms  ← hints, not hard rules    │
  │    },                                                 │
  │    card: {                                            │
  │      title, company, exp_text,                        │
  │      salary, skills, posted                           │
  │    }                                                  │
  │  }                                                    │
  │                                                       │
  │  AG Brain evaluates:                                  │
  │  → Seniority: Is exp_text bracket right for level?   │
  │  → Domain: Finance/Accounting/Analytics?              │
  │  → Title Level: Junior/Analyst/Exec vs Sr/Mgr/Dir?   │
  │  → Contextual: "manage" as verb ≠ "Manager" role      │
  │                                                       │
  │  AG Brain responds:                                   │
  │  {"decision": "DEEP_SCAN" | "SKIP", "reason": "..."}  │
  │                                                       │
  │  SLA: 90 seconds. Timeout → conservative SKIP.        │
  └───────────────────────────────────────────────────────┘
          │
          ├── SKIP → Ledger: ag_brain_card_skipped + reason
          │
          └── DEEP_SCAN ↓
          ▼
  Deep Scan JD Page (full text + highlights + skills + specs)
  [Highlights sent to AG Brain as part of full JD — not Python-gated]
          │
          ▼
  evaluate_job_match() ← Gemini API scoring on full JD
  + RESUME_TAILORING IPC → AG Brain (existing, unchanged)
          │
          ▼
  score ≥ threshold → Apply / Save_External
  score < threshold → low_score
```

**What makes decisions:** AG Brain (Antigravity 2.0) — reads full context, understands semantics.
**What Python does:** Collects data, writes IPC payloads, reads responses, executes instructions.

---

## 5. The G-BRAIN-01 Principle (Formal Definition)

```
PRINCIPLE — G-BRAIN-01 (AG Brain Sole Evaluator)
Effective: 2026-09-19
Stored in: ACTIVE_CONSTRAINT_BLOCK.md GATE 11, AI CONTEXT ENTRY #012

  Python scripts are the ARMS AND LEGS of the agent.
  AG Brain (Antigravity 2.0) is the SOLE BRAIN.

  Python MAY:
    • Apply objective numeric gates (salary floor, exp band)
    • Match exact company identity against blacklist
    • Deduplicate URLs and composite keys
    • Route based on AG Brain's returned decision
    • Actuate browser actions as instructed

  Python MUST NOT:
    • Match job titles against keyword lists to accept/reject
    • Match JD/highlights text against keyword lists to accept/reject
    • Make any semantic judgment about domain fit, seniority, or relevance
    • Call is_title_allowed() or any replacement semantic gate
    • Use negative_keywords or positive_keywords as execution logic

  negative_keywords and positive_keywords in candidate_config.json
  are ADVISORY CONTEXT passed to AG Brain — not Python execution rules.
```

---

## 6. What Changed in Each File

### `core/04_job_discovery.py`
| Element | Change |
|---|---|
| `is_title_allowed()` function body | Marked `DEPRECATED — G-BRAIN-01 (2026-09-19)`. Dead code. Not called. |
| `is_title_allowed()` call in card loop | **Removed.** Replaced with `JOB_CARD_EVALUATION` IPC block. |
| Highlights keyword scan (block 3b) | **Removed.** Replaced with deprecation comment. AG Brain reads highlights as part of full JD. |
| C24 exp band gate | **Added** after salary floor gate. Numeric-only, profile-agnostic. |
| `JOB_CARD_EVALUATION` IPC block | **Added** after numeric gates. Writes card data + candidate summary to IPC, polls for AG Brain decision, routes. |
| AI CONTEXT header | **Entry #011** (C24 rationale), **Entry #012** (G-BRAIN-01 rationale + hard prohibition) |

### `.agents/rules/SCAR_TISSUE.md`
Two new violation entries appended (permanent memory):
```
[2026-09-19] THIN-JD EXPERIENCE BAND FALSE POSITIVE
  → Never trust JD body text alone for experience gating.
  → Naukri card exp_text is ground truth. C24 must always fire first.

[2026-09-19] KEYWORD-GATE ARCHITECTURE CAUSES FALSE POSITIVES AND FALSE NEGATIVES
  → Python keyword matching for semantic decisions is permanently deprecated.
  → Never re-introduce keyword gates in Python under any circumstance.
```

### `.agents/rules/ACTIVE_CONSTRAINT_BLOCK.md`
```
GATE 11 — AG BRAIN SOLE EVALUATOR (G-BRAIN-01)
Python must NOT make keyword-based semantic match/reject decisions.
ALLOWED: salary floor gate, C24 exp band gate, negative_companies.
PROHIBITED: is_title_allowed(), negative_keywords matching, highlights scan.
Violation = breach of G-BRAIN-01. Requires user approval to override.
```

### `docs/ARCHITECTURE_REFERENCE.md`
- Version bumped v5.0 → v5.1
- Pipeline sequence diagram updated with C24 position
- G-BRAIN-01 IPC flow documented

---

## 7. IPC Task Type Reference (All Types Now Active)

| Task Type | Triggered By | AG Brain Does | Python Does With Response |
|---|---|---|---|
| `JOB_CARD_EVALUATION` | Every card passing numeric gates | Evaluates title/exp/domain holistically. Returns DEEP_SCAN or SKIP + reason | Routes: SKIP → ledger, DEEP_SCAN → open JD page |
| `RESUME_TAILORING` | Match confirmed, before apply | Writes tailored summary + prioritized skills for the specific JD | Uses output to generate tailored resume file |
| `QUESTIONNAIRE` | Application form has questions | Reads JD + profile, answers each question factually | Types answers into form fields |

---

## 8. Decision Authority Table (Complete)

| Decision | Who Decides | Method |
|---|---|---|
| Is salary above floor? | Python | Numeric comparison |
| Is experience within candidate range? | Python (C24) | Numeric comparison on card metadata |
| Is company blacklisted? | Python | Exact string identity match |
| Is this URL already processed? | Python | Hash set lookup |
| Is this job title appropriate for candidate level? | **AG Brain** | IPC: JOB_CARD_EVALUATION |
| Is this job domain relevant? | **AG Brain** | IPC: JOB_CARD_EVALUATION |
| Is this role senior/managerial? | **AG Brain** | IPC: JOB_CARD_EVALUATION |
| Does JD content match candidate skills? | **AG Brain / Gemini** | evaluate_job_match() |
| How to tailor the resume for this JD? | **AG Brain** | IPC: RESUME_TAILORING |
| How to answer application form questions? | **AG Brain** | IPC: QUESTIONNAIRE |

---

## 9. Why This Architecture is More Resilient

| Scenario | Old Architecture | New Architecture |
|---|---|---|
| Recruiter uses "manage" as a verb in JD | **FALSE REJECT** (keyword match) | [PASS] AG Brain understands context |
| Novel senior title not in keyword list | **FALSE ACCEPT** | [PASS] AG Brain reads exp_text + title holistically |
| New job type emerges in market | Requires keyword list update | [PASS] AG Brain handles without config change |
| Keyword list grows stale | Silent degradation | [PASS] No impact — Python doesn't use lists for decisions |
| Candidate profile changes | Keyword lists need re-tuning | [PASS] AG Brain reads profile dynamically each eval |
| Agent brain session changes (new AG Brain) | Repeats keyword mistakes | [PASS] SCAR_TISSUE + AI CONTEXT ENTRY #012 prevent regression |

---

## 10. Git Commits

| Commit | Message | Key Changes |
|---|---|---|
| `1a323e2` | `fix(C24): Card-Level Experience Band Gating` | C24 gate added, negative keywords patch, SCAR_TISSUE entry 1, ARCHITECTURE_REFERENCE v5.1, README |
| `18369ff` | `feat(G-BRAIN-01): AG Brain Sole Evaluator` | `is_title_allowed()` call removed, highlights gate removed, JOB_CARD_EVALUATION IPC added, GATE 11, ENTRY #012, SCAR_TISSUE entry 2 |
| `f86846e` | `docs: Add SESSION_REPORT_2026-09-19` | Previous report (with candidate-specific details) |
