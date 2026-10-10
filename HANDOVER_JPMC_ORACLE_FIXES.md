# Handover: Enterprise ATS & Company Site Autonomous Application Subsystem

> **Status:** Fully Integrated, Tested (66 Unit Tests Passing), and Production-Ready  
> **Architecture:** 6-Stage Autonomous Lifecycle, Cognitive Sub-Agent Dispatch, Dynamic Brain Q&A, and Stale Document Healing  
> **Key Constraint:** **STRICT HUMAN SUBMISSION GATE (Never click SUBMIT on Section 4).**

---

## 1. System Overview

The Company Site Apply subsystem (`CompanySiteApply/`) provides 100% config-driven, autonomous application execution directly on corporate career portals (such as JPMorgan Chase on Oracle Cloud HCM).

### Zero-Hardcoding Guarantee:
- Zero candidate PII (names, emails, phones, addresses) is hardcoded in Python code.
- Zero assumptions regarding candidate vertical, skills, or experience years (works uniformly for Software Engineering, Internal Audit, Finance, Operations, Talent Acquisition, etc.).
- All candidate data resolves dynamically from `profiles/<profile_name>/candidate_config.json` and master `resume.md`.

---

## 2. The 6 Chronological Stages

```
[Stage 1: Comprehend Profile] 
  → Ingests candidate config, master resume, and skills taxonomy dynamically.
[Stage 2: Portal Search] 
  → Dispatches JPMorganScraper using candidate's target keywords & preferred locations.
  → Prunes roles already applied via DOM tile inspection or processed_ledger.json.
[Stage 3: Cognitive Match Evaluation] 
  → Scrapes full JD and evaluates factual fit (0-100) via CognitiveJobMatcher.
  → Ranks unapplied candidate roles and selects the top-scoring requisition.
[Stage 4: Document Tailoring] 
  → Generates bespoke, ATS-compliant cover letter PDF matching exact job_id and title.
[Stage 5: Section Mini-Agent Dispatch (Form Apply)] 
  → Navigates to target application URL (/job/<id>/apply).
  → Coordinates Section 1 -> Section 2 -> Section 3 -> Section 4 with pre-audit, surgical micro-heal, and post-audit.
[Stage 6: Visual Audit & Human Submission Gate] 
  → Captures high-res verification screenshot.
  → Records application in profiles/<profile>/output/processed_ledger.json.
  → Strictly halts before clicking SUBMIT for human review.
```

---

## 3. Engineering Solutions & Solved Traps

1. **Pre-Uploaded Stale Document Retention:** Oracle Cloud HCM retains draft attachments across applications. `DocumentsSubAgent` evaluates session freshness (`_fresh_cover_uploaded`). If a document was not uploaded in the active session for the active requisition, it is flagged as `PRE_UPLOADED_STALE`, removed, and replaced with the role's fresh tailored PDF.
2. **Reverse-Chronological Experience Ordering:** JET resume parser often shuffles work history tiles out of order. `ExperienceSubAgent` and `JPMCNail` dynamically parse dates and enforce strict reverse-chronological ordering (most recent first).
3. **Screening Questionnaire Intelligence:** `AIBrainResolver` acts as the cognitive brain for screening forms, dynamically mapping candidate credentials to dropdowns, multi-select comboboxes, competency pills, and binary declarations with zero bad fallbacks.
4. **Hierarchical Section Dispatch:** `evaluate_and_heal_section` isolates failures. If Section 1 Preferred Location fails, only `PreferredLocationSubAgent.heal()` runs; Personal Details is untouched and never re-clicked.
5. **Human Submission Gate:** Submission is strictly human-gated. The agent prepares everything, verifies green checkmarks, enables the Submit button, captures full-page screenshot proof, and alerts the user.

---

## 4. Operational Playbook for New Chats

### How to Start the Agent in a Fresh Chat:
Simply instruct Antigravity:
> *"Run the autonomous company site application agent for profile [profile_name] on JPMC career portal. Follow the 6-stage lifecycle in CompanySiteApply/autonomous_job_agent.py, ensure all sub-agents execute with zero hardcoding, and halt at Section 4 before clicking SUBMIT."*

### Command-Line Execution:
```powershell
# Run full autonomous lifecycle
.venv\Scripts\python run_universal_apply.py --autonomous --profile <profile_name>

# Run active tab application (for forms already open)
.venv\Scripts\python run_universal_apply.py --profile <profile_name>

# Run test suite
.venv\Scripts\python -m unittest discover -s CompanySiteApply/tests
```
