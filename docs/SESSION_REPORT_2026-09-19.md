# Universal Autonomous Career Agent — Session Engineering Report
**Date:** 2026-09-19 | **Profile:** `anshika_garg` | **Report Author:** AG Brain (Antigravity 2.0)

---

## Executive Summary

This session resolved **three compounding failure modes** that caused the agent to apply for senior-level roles wildly outside the fresher-candidate's experience bracket (e.g., a 4–9 year Finance Consultant role for a 0.5-year candidate). All fixes were committed to `origin/main`. The session culminated in a **fundamental architectural redesign** — removing all keyword-based Python decision-making and routing all semantic job evaluation to the AG Brain via IPC.

---

## 1. The Incident That Started Everything

### What the User Saw
```
Finance Analyst Consultant Process Excellence [Albireo Recruiters]
4 - 9 years / 12-22 Lacs P.A.  → AGENT APPLIED TO THIS ROLE
```

A 0.5-year fresher was applied to a role requiring 4–9 years experience at ₹12–22 LPA. The user rightly escalated this as unacceptable.

### The 4-Factor Failure Chain (Root Cause Analysis)

| # | Factor | Detail |
|---|---|---|
| 1 | **Thin JD** | Naukri page rendered only ~16 lines of body text; "4–9 Yrs" was in card `exp_text` but **absent from the scraped `full_desc`** |
| 2 | **Experience gate gap** | `evaluate_job_match()` in `ai_client.py` ran a regex on `full_desc` for experience mentions — found 0 matches — silently awarded 8-point "no restriction" bonus |
| 3 | **Missing keyword** | `"Consultant"` was absent from `negative_keywords` list → title gate passed |
| 4 | **Score booster** | `max(total_score, 65)` applied when `skill_ratio ≥ 0.60` → final score boosted to 71 > threshold 65 → agent applied |

---

## 2. Fixes Applied — Three Layers

---

### Fix 1 — Negative Keywords Patch
**File:** `profiles/anshika_garg/candidate_config.json`

**What:** Added 6 missing entries to `target_jobs.negative_keywords`:
- `"Consultant"`, `"Senior Consultant"`, `"Associate Consultant"`
- `"Process Excellence"`, `"Finance Transformation"`, `"Finance Consultant"`

**Why:** Blocked the immediate Albireo-class title pattern from recurring.

**Limitation noted immediately:** This was a band-aid — stale keyword lists cannot catch all future senior title patterns. This realization directly led to Fix 3 (the architectural solution).

---

### Fix 2 — Guardrail C24: Card-Level Experience Band Gate
**File:** `core/04_job_discovery.py` (after salary floor gate, before deep scan)
**Git Commit:** `1a323e2`

#### The Problem It Solves
The existing experience check only ran against scraped JD body text. When JD body was sparse/thin (Albireo had only ~16 lines), the regex found no experience mentions and awarded an 8-point "no restriction" bonus — allowing senior roles to score above threshold.

Naukri's card-level `exp_text` field (e.g., `"4 - 9 Yrs"`) is always populated — it is set by the recruiter at job creation and is guaranteed to be present regardless of JD body quality.

#### What Was Added
```python
_card_exp_text = str(job.get("exp_text") or "").strip()
if _card_exp_text:
    _card_min_exp = float(parsed_range[0])
    _cand_actual_exp = float(cand.get("total_experience_years", 0))
    _max_exp_gap = config.get("target_jobs", {}).get("max_experience_gap_years", 2)
    if _card_min_exp > _cand_actual_exp + _max_exp_gap:
        → REJECT with status: "experience_gap_gated"
```

#### Key Design Principles
- **Zero hardcoded values** — all thresholds from `candidate_config.json`
- **Profile-agnostic** — uses `cand` object (already profile-scoped), works for any profile
- **Fires BEFORE deep scan** — saves browser time and AI tokens

#### Live Output Seen This Session (C24 working correctly)
```
-> Rejecting Over-Senior Job: Financial Planning Analyst @ Alaris [CARD EXP MIN: 5yr | CANDIDATE: 0.5yr | MAX GAP: +2yr]
-> Rejecting Over-Senior Job: Senior Analyst @ Evalueserve [CARD EXP MIN: 3yr | CANDIDATE: 0.5yr | MAX GAP: +2yr]
-> Rejecting Over-Senior Job: Financial Planning and Analysis @ Accenture [CARD EXP MIN: 5yr | CANDIDATE: 0.5yr | MAX GAP: +2yr]
```

---

### Fix 3 — G-BRAIN-01: AG Brain as Sole Job Evaluator (Architectural Redesign)
**File:** `core/04_job_discovery.py`
**Git Commit:** `18369ff`

#### The Problem (User Directive, 2026-09-19)
> "I do not want matching and rejecting based on keyword. AG Brain should be responsible. Python scripts are arms and legs doing their work but you the AG Brain are the main brain which analyses profile, tailors resume, verifies matches, reads JD/skills/exp and makes decisions. Python scripts simply perform what you ask them to do."

Two failure classes from keyword-based Python gating:

1. **False Rejections**: JD text contains `"manage the audits"` → Python sees `"manage"` → matches `"Manager"` in `negative_keywords` → **blocks a legitimate entry-level Audit Executive role**

2. **False Acceptances**: A senior role with a novel title combination not yet added to any keyword list → **passes through unchecked** → agent applies

---

## 3. Before vs. After Architecture

### BEFORE — Keyword-Gate Architecture (Legacy, Removed)

```
SRP Cards Scraped
       ↓
[Python] is_title_allowed()                  ◄── REMOVED
  ├─ Negative keyword rejection (C6)
  ├─ Incompatible vertical gate
  ├─ Positive stem/prefix match
  └─ ai_client.arbitrate_card_fit()
       ↓ (jobs silently killed by stale keyword lists)
[Python] Salary Floor Gate
       ↓
[Python] C24 Exp Band Gate
       ↓
[Python] Highlights keyword scan (3b)        ◄── REMOVED
       ↓
[Python] Deep Scan JD page
       ↓
[Gemini API] evaluate_job_match() → score
       ↓
Apply / Skip / Save
```

**Root problems:**
- `negative_keywords` list is static and stale — can never cover all senior titles
- `positive_keywords` list misses legitimate roles with unfamiliar titles
- `"manage"` as verb in JD body = false rejection
- Novel senior title patterns not in any list = false acceptance
- Python makes semantic judgements it cannot reliably make

---

### AFTER — AG Brain Sole Evaluator (G-BRAIN-01, Active)

```
SRP Cards Scraped
       ↓
[Python] Negative Companies Gate             ← KEPT (exact identity, not semantic)
       ↓
[Python] Salary Floor Gate                   ← KEPT (objective numeric)
       ↓
[Python] C24 Exp Band Gate                   ← KEPT (objective numeric, card metadata)
       ↓
[IPC → AG Brain] JOB_CARD_EVALUATION
  Python writes: {title, company, exp_text, salary, card_skills,
                  candidate profile summary, advisory_avoid_terms}
  AG Brain evaluates: seniority, domain fit, level appropriateness
  AG Brain returns: {"decision": "DEEP_SCAN" | "SKIP", "reason": "..."}
       ↓
  SKIP → ledger: ag_brain_card_skipped | reason logged
  DEEP_SCAN → proceed ↓
       ↓
[Python] Deep Scan JD page (full text + highlights + skills + specs)
       ↓
[Gemini API] evaluate_job_match() → match score
  + [IPC → AG Brain] RESUME_TAILORING (existing, unchanged)
       ↓
score ≥ threshold → Apply / Save_External
score < threshold → Skip: low_score
```

**Why this is better:**

| Scenario | Old Behavior | New Behavior |
|---|---|---|
| JD says "manage the audits" | BLOCKED (Manager in neg_keywords) | AG Brain reads full context → DEEP_SCAN if entry-level |
| Novel senior title not in keyword list | PASSED (not in any list) | AG Brain reads exp_text + title → SKIP |
| Legitimate role with unfamiliar title | BLOCKED (stem mismatch) | AG Brain evaluates domain + level → DEEP_SCAN |
| Stale keyword list misses a pattern | FALSE ACCEPTANCE | AG Brain is context-aware, not list-bound |

---

## 4. What Python May and May Not Do — G-BRAIN-01 Rules

| Gate | Python Allowed? | Reason |
|---|---|---|
| Salary floor (numeric) | ✅ YES | Pure numeric comparison |
| C24 exp band (numeric) | ✅ YES | Ground-truth card metadata |
| Negative companies (exact match) | ✅ YES | Identity match, not semantic |
| URL/key deduplication | ✅ YES | Pure hash lookup |
| Title keyword matching | ❌ NO | Semantic → AG Brain via IPC |
| Highlights keyword gate | ❌ NO | Semantic → AG Brain via IPC |
| Domain/vertical gating | ❌ NO | Semantic → AG Brain via IPC |
| `is_title_allowed()` function call | ❌ NO | DEPRECATED — dead code |

---

## 5. New IPC Task Type: JOB_CARD_EVALUATION

**Python writes to `pending_question.json`:**
```json
{
  "status": "PENDING",
  "task_type": "JOB_CARD_EVALUATION",
  "prompt": {
    "candidate_summary": {
      "total_experience_years": 0.5,
      "seniority_level": "Fresher / Entry Level",
      "domain": "Finance",
      "active_search_titles": ["Financial Analyst", "FP&A Analyst", ...],
      "advisory_avoid_terms": ["Manager", "Senior", "Consultant", ...]
    },
    "card": {
      "title": "Financial Analyst",
      "company": "XYZ Corp",
      "exp_text": "0-2 Yrs",
      "salary": "3-6 Lacs PA",
      "skills": ["Excel", "Financial Modeling"],
      "posted": "2 days ago"
    }
  }
}
```

**AG Brain writes back to `answer` key:**
```json
{"decision": "DEEP_SCAN", "reason": "Entry-level Finance Analyst, 0-2yr bracket fits fresher. Domain aligned."}
```
or:
```json
{"decision": "SKIP", "reason": "Senior Manager title, 6yr+ implied — exceeds fresher candidate by far."}
```

**SLA:** 90 seconds | **Timeout:** conservative SKIP

---

## 6. Complete File Change Log

| File | Change Type | What Changed |
|---|---|---|
| `profiles/anshika_garg/candidate_config.json` | EDIT | Added 6 negative keywords |
| `core/04_job_discovery.py` | EDIT | C24 gate; removed `is_title_allowed()` call; removed highlights gate; added `JOB_CARD_EVALUATION` IPC block; marked `is_title_allowed()` DEPRECATED; AI CONTEXT ENTRY #011 and #012 |
| `.agents/rules/SCAR_TISSUE.md` | APPEND | Two new violation entries |
| `.agents/rules/ACTIVE_CONSTRAINT_BLOCK.md` | APPEND | GATE 11 (G-BRAIN-01) |
| `docs/ARCHITECTURE_REFERENCE.md` | EDIT | v5.0 → v5.1, C24 in pipeline diagram |
| `README.md` | EDIT | C24 guardrail bullet added |
| `docs/SESSION_REPORT_2026-09-19.md` | NEW | This file |

---

## 7. Self-Healing and Learning Mechanisms

### Permanent Memory — SCAR_TISSUE.md
```
[2026-09-19] THIN-JD EXPERIENCE BAND FALSE POSITIVE → SENIOR ROLE APPLICATION
  → Never trust JD body text alone for experience gating.
  → Naukri card exp_text is ground truth. C24 must always fire first.

[2026-09-19] KEYWORD-GATE ARCHITECTURE CAUSES FALSE POSITIVES AND FALSE NEGATIVES
  → Never re-introduce keyword-based semantic gating in Python.
  → Python = data collector + actuator. AG Brain = sole semantic evaluator.
```

### Hard Gate — ACTIVE_CONSTRAINT_BLOCK.md GATE 11
```
GATE 11 — AG BRAIN SOLE EVALUATOR (G-BRAIN-01)
Python must NOT make keyword-based semantic match/reject decisions.
All such decisions route to AG Brain via IPC (JOB_CARD_EVALUATION).
```

### In-Code AI CONTEXT Headers (ENTRY #011, #012)
Future AG Brain agents loading `04_job_discovery.py` will see:
- ENTRY #011: C24 rationale — "Never rely solely on JD body text for exp gating"
- ENTRY #012: G-BRAIN-01 rationale — "NEVER re-introduce keyword gating in Python"

---

## 8. Git History This Session

```
18369ff  feat(G-BRAIN-01): AG Brain Sole Evaluator — remove all Python keyword gates
1a323e2  fix(C24): Card-Level Experience Band Gating — blocks over-senior roles at SRP card
```

Both pushed to `origin/main` (GitHub: callitask/Universal-Autonomous-Career-Agent).

---

## 9. Applications Submitted This Session

| Time | Role | Company | Score | Method |
|---|---|---|---|---|
| 15:23:09 IST | Audit Executive – Stock Audit | Hindco Recruitment (CA Firm) | 81% | APPLIED_1CLICK ✅ |

---

## 10. Current Agent State (As of Report Generation)

| Component | Status | Notes |
|---|---|---|
| Daemon 1 (Discovery + Apply) | ⚠️ RESTARTING | Cancelled during server restart |
| Daemon 2 (IPC Watcher) | ⚠️ RESTARTING | Cancelled during server restart |
| Daemon 3 (Cron Heartbeat) | ✅ ACTIVE | task-167 running |
| Chrome CDP (port 9222) | ✅ CONFIRMED earlier | Needs re-check if error |
| G-BRAIN-01 | ✅ LIVE | In code, committed, pushed |
| Guardrail C24 | ✅ LIVE | In code, committed, pushed |
| Git Remote | ✅ UP TO DATE | `origin/main` @ `18369ff` |

---

## 11. How Future AG Brain Sessions Should Handle JOB_CARD_EVALUATION

When `pending_question.json` contains `task_type: "JOB_CARD_EVALUATION"`, evaluate:

1. **Seniority**: Does `exp_text` bracket fit 0-2yr for this candidate? (0.5yr + max_gap 2yr = max 2.5yr min exp allowed)
2. **Domain**: Is it Finance / Accounting / Analytics? Not IT, HR, Operations, Legal?
3. **Level**: Is it Junior / Analyst / Executive / Associate? Not Senior / Manager / Director / Head / VP / Partner?
4. **Advisory terms**: Are `advisory_avoid_terms` present in the title in a **seniority capacity** (not as verbs or modifiers)?

Return `DEEP_SCAN` if all 4 are positive. Return `SKIP` with clear reason otherwise.
Write answer as: `data['answer'] = json.dumps({"decision": "DEEP_SCAN"|"SKIP", "reason": "..."})`
