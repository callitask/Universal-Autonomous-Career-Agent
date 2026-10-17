# SECTION IPC ARCHITECTURE — AG Brain-Gated Question Fill System
# Version: 1.1 | Created: 2026-10-12 | Amended: 2026-10-14 (structured-layout contract, §4 only) | Status: APPROVED FOR IMPLEMENTATION
# Scope: CompanySiteApply — Oracle Cloud HCM (JPMC CX_1002), extensible to Workday / Greenhouse

> [!IMPORTANT]
> **This document is the single source of truth for implementing the IPC-based section-filling redesign.**
> Read this file at session start before touching any code. Every design decision is recorded here.
> Implementation follows GATE 3: Report → Review → Manual Approval → Execution.

---

## 1. Problem Statement (Root Causes from Live Sessions)

| # | Bug | Root Cause | File Responsible |
|---|-----|------------|-----------------|
| 1 | Conditional questions not answered (e.g. "Years of work experience") | `BinaryQuestionSubAgent.heal()` scans questions visible at page load only. After binary pills are clicked, NEW conditional questions appear in the DOM — the agent never re-scans. | `binary_question_subagent.py` |
| 2 | Experience tiles in wrong chronological order | `reorder_experience_tiles()` in `JPMCNail` and `ExperienceSectionAgent` both use Knockout `parent.forms.sort()` with `startDate` string comparison. Oracle HCM's `startDate` observable may return `null` or a formatted string like `"03/2026"` — `localeCompare` on these gives unpredictable sort order. | `jpmc_nail.py` L524-536 |
| 3 | Terms & Conditions modal trap | `ApplyOrchestrator.run()` detects section by URL (`/section/1`) but the full-page agreement modal (`#applyFlowLegalDisclaimer`) blocks all form content. The orchestrator calls section mini-agents while the page is still overlaid by the modal. | `apply_orchestrator.py` L107-111 |
| 4 | Questions answered without AG Brain context | `BinaryQuestionSubAgent` and `TechnicalCompetencySubAgent` call `AIBrainResolver.resolve_question()` in real-time within the Playwright sync context. This limits the AG Brain's ability to read the full profile and IPC state before answering. | All section 2 sub-agents |

---

## 2. Core Design: Section IPC Protocol

### 2.1 The IPC File

**Template location (tracked):** `F:\JOB AI AGENT\CompanySiteApply\ipc\section_question.json`

**Active runtime location:** resolved via `CompanySiteApply/utils/runtime_paths.py:ipc_dir()` →
`F:\Operations JOB AI AGENT\ipc\section_question.json` (the Operations root,
env-overridable via `JOB_AGENT_OPERATIONS`). The in-repo path is the committed
**template fallback** only — live runtime state is never written into the git tree.

This file is the shared message bus between Python (Playwright browser scripts) and AG Brain (Antigravity 2.0 model).

```json
{
  "session_id": "<uuid4 generated at orchestrator start>",
  "job_id": "<job requisition ID, e.g. 210780039>",
  "profile": "<profile folder slug, e.g. first_last>",
  "section": "<section_1 | section_2 | section_3 | section_4>",
  "subsection": "<personal_details | preferred_location | binary_questions | competency_questions | conditional_questions | experience_tile_N | education_tile | documents | diversity | signature>",
  "page_number": 1,
  "status": "<IDLE | QUESTION_READY | ANSWER_REQUIRED | ANSWERED | ERROR>",
  "questions": [
    {
      "q_id": "<unique id, e.g. q_001>",
      "question_text": "Are you legally authorized to work in India?",
      "field_type": "<BINARY_PILL | RADIO_CHIP | RADIO_BUTTON | DROPDOWN | COMBOBOX | CHECKBOX | TEXT | TEXTAREA | FILE_UPLOAD>",
      "available_choices": ["Yes", "No"],
      "current_value": null,
      "is_conditional": false,
      "trigger_question": null,
      "trigger_value": null,
      "is_required": true,
      "answer": null,
      "answer_confidence": null,
      "answer_rationale": null
    }
  ],
  "script_done": false,
  "timestamp_written": "<ISO8601>",
  "timestamp_answered": null,
  "error": null
}
```

### 2.2 Status State Machine

```
IDLE
  │
  ▼ (Script discovers page questions)
QUESTION_READY
  │
  ▼ (Script writes questions + sets status = ANSWER_REQUIRED)
ANSWER_REQUIRED
  │
  ▼ (AG Brain reads IPC, fills answer[], sets status = ANSWERED)
ANSWERED
  │
  ▼ (Script reads answers, fills DOM, sets status = IDLE for next subsection)
IDLE (next subsection begins)
```

- `ERROR` is set by either party when an exception occurs. The orchestrator reads this and dispatches the specific failing subsection's heal script again.
- `script_done: true` signals the script completed its DOM-fill pass and is ready for verification.

### 2.3 Timeout Contract

| Party | Timeout | Action on Expiry |
|-------|---------|-----------------|
| Script waiting for `ANSWERED` | 120 seconds | Set `status = ERROR`, log to `ipc/ipc_error.log`, halt subsection |
| AG Brain waiting for `ANSWER_REQUIRED` | Infinite (event-driven) | N/A — orchestrator triggers brain |
| Orchestrator polling IPC | Every 1.5 seconds | Read status; advance when `ANSWERED` |

---

## 3. Section → Subsection → Script Map

Every subsection has exactly one Python script. Scripts are **dumb actuators** — they:
1. Discover form fields in the DOM
2. Write question data to `section_question.json` + set `ANSWER_REQUIRED`
3. Wait for `ANSWERED`
4. Fill the DOM from `answer` field
5. Read back DOM values and verify
6. Report success/failure to the orchestrator via return value

Scripts NEVER make semantic decisions. AG Brain is the sole semantic agent.

### Section 1 (Profile)

| Subsection | Script | Inputs | Notes |
|-----------|--------|--------|-------|
| `personal_details` | `PersonalDetailsSubAgent` (no discrete script; deterministic) | candidate_data | Title, First/Last Name, Phone, Email, Address. Non-IPC (deterministic from profile). |
| `preferred_location` | `PreferredLocationSubAgent` (no discrete script; deterministic) | candidate_data | Preferred location pill. Non-IPC (deterministic). Uses `input[name='preferredLocations']` click → listbox. |
| **Modal pre-check** | Built into orchestrator `run()` | page | Detect `#applyFlowLegalDisclaimer` → click AGREE → wait 1s → confirm modal gone BEFORE calling any subsection. |

> [!NOTE]
> Section 1 subsections are purely profile-data driven (zero semantic ambiguity). They do NOT need IPC. They still use the audit/heal/verify pattern and return section result to the orchestrator.

### Section 2 (Questionnaire)

| Subsection | Script | Field Types |
|-----------|--------|-------------|
| `binary_questions` | `section_agents/scripts/s2_binary_questions.py` | BINARY_PILL |
| `competency_questions` | `section_agents/scripts/s2_competency_questions.py` | RADIO_CHIP, RADIO_PILL |
| `dropdown_questions` | `section_agents/scripts/s2_dropdown_questions.py` | DROPDOWN, COMBOBOX |
| `conditional_questions` | `section_agents/scripts/s2_conditional_questions.py` | ANY type (scanned AFTER all other subsections answered) |

**Conditional Question Protocol:**
After `binary_questions`, `competency_questions`, and `dropdown_questions` complete their first pass, the orchestrator calls a **conditional rescan**:
1. Re-scan all `.input-row, .app-form-item, [class*='question-block']` for visible elements with empty/unselected state.
2. Any newly visible required question that was NOT present in previous IPC passes is added to a new `conditional_questions` IPC cycle.
3. This ensures dynamically revealed questions (like "Years of work experience excluding internships") are never missed.
4. Conditional rescan repeats up to 4 passes (`max_passes = 4`) to handle nested conditional questions.

### Section 3 (Education & Experience)

| Subsection | Script | Notes |
|-----------|--------|-------|
| `education_tile` | `section_agents/scripts/s3_education_tile.py` | One education tile. Degree, Area of Study, Country from candidate_data. Non-IPC in effect: the `edu_degree_major` question is serialized through `IPCManager` (`write_questions` then `write_answers` back-to-back, since the answer is deterministic profile data) — a **sync fast-path**, not a brain round-trip. |
| `experience_tile_N` | `section_agents/scripts/s3_experience_tile.py` | Called N times (once per experience entry). N resolved from `candidate_data.work_experience` count. |
| `experience_ordering` | `section_agents/scripts/s3_experience_ordering.py` | Called AFTER all tiles filled. Enforces reverse-chronological sort via date parsing (see §4.1). |

**Experience Tile IPC Flow (per tile):**
1. Script opens tile N's edit form.
2. Reads all visible fields: `employerName`, `jobTitle`, `startDate`, `endDate`, `currentJobFlag`, `countryCode`, `employerCity`, `isInternalEmployee`, `achievements` textarea.
3. Writes to IPC with `subsection = "experience_tile_N"` and `status = ANSWER_REQUIRED`.
4. AG Brain reads IPC, matches tile to correct entry in `candidate_data.work_experience` (by employer name fuzzy match), and provides all field answers including bullet-formatted `achievements` text.
5. Script fills fields from IPC answer. Clicks SAVE. Waits for modal close (`.apply-flow-profile-item-tile:visible` count stable).

### Section 4 (Review)

| Subsection | Script | Notes |
|-----------|--------|-------|
| `resume_upload` | `section_agents/scripts/s4_resume_upload.py` | Independent: check if resume uploaded → if missing/stale → upload the exact role file `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/<Stem>_Resume.pdf` (fixed name, no job-id suffix; exact role path first, glob legacy fallback only). |
| `cover_letter_upload` | `section_agents/scripts/s4_cover_letter_upload.py` | Independent: check if cover letter uploaded → if stale (not this session's job) → REMOVE → upload the exact role file `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/<Stem>_Cover_Letter.pdf` (fixed name, no job-id suffix; exact role path first — never `*{jobid}*cover*letter*` globs or `candidates[0]` picks). |
| `diversity` | `DiversitySubAgent` (no discrete script) | India Uniformed Forces, Ethnicity, Gender. Non-IPC (deterministic). |
| `signature` | `SignatureSubAgent` (no discrete script) | E-Signature full name. Non-IPC (deterministic). |
| `linkedin_url` | `JPMCNail` LinkedIn normalization (inline, no discrete script) | Verify LinkedIn link not truncated by Oracle resume parser. Non-IPC. |
| `visual_verify` | `VisualVerifierSubAgent` (no discrete script) | Full-page screenshot → saved to `artifacts/` (Operations root) + structured DOM readback with `ORDER_UNVERIFIED` pre-submit gate. |

**Document Upload Independence Rule (structured-layout contract, 2026-10-14; tailoring gate 2026-10-15):**
- Inputs (profile-agnostic): `profiles/<slug>/company_site_apply/<Slug>/` (root `README.md`-only + `resumes/BASE.md` + `cover_letters/BASE.md`).
- Outputs: `profiles/<slug>/APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/` with FIXED `<Stem>_Resume.pdf` / `<Stem>_Cover_Letter.pdf` (Stem = Title-Cased profile slug, e.g. `first_last` → `First_Last`) mirrored flat AND inside `resume/` + `cover_letters/` subfolders, plus role `Cover_Letter.txt`/`.html`. No job-id filename suffixes — multiple jobs per company and same-title different-IDs coexist by folder, not by filename.
- `resume_upload` and `cover_letter_upload` are callable independently (both accept `--job-id`).
- Each checks its own state BEFORE acting:
  - Resume: `[data-automation-id*='resume'], input[type='file'][accept*='pdf']` — check `.attachment-upload-button--filled` state.
  - Cover letter: same pattern but keyed on `[data-automation-id*='cover']`.
- DOM display filenames are NEVER trusted (every requisition shares the fixed name): every run executes **remove-if-filled + upload + verify** — role-folder `Cover_Letter.txt` must pass Job-ID + title checks for the active `job_id`, the role PDF must exist and satisfy `pdf.st_mtime >= txt.st_mtime - 5.0`, and the upload is credited only to the active `(_ipc_session_id, job_id)` via `_fresh_cover_uploaded`.
- If Stage 4 tailoring failed (`_tailoring_failed` / `_skip_document_upload`): remove any stale draft, upload NOTHING, and return `REVIEW_BLOCKED` (`blocked_reason: TAILORING_BLOCKED`, `skip_retry: True`) with the missing document + fix command — while diversity, signature, and visual verification still complete in the same pass.
- If both are stale, scripts run sequentially (cover letter first, then resume — because cover letter removal can trigger page re-renders).
- Session freshness flag `_fresh_cover_uploaded` and `_fresh_resume_uploaded` are stored in IPC `session_id` context.

---

## 4. Critical Fixes Required Before IPC Redesign

### 4.1 Experience Tile Ordering Fix

**Root Cause:** `startDate` observable in Oracle HCM Knockout VM stores dates as localized strings (`"03/2026"`, `"September 2021"`) or epoch milliseconds. `localeCompare` on mixed formats gives undefined ordering.

**Correct Fix — DOM Text Date Parsing:**
Instead of relying on Knockout VM observable values, extract date text directly from the rendered tile's visible text, parse to a sortable integer (YYYYMM), and sort tile DOM nodes by swapping.

```javascript
// In s3_experience_ordering.py page.evaluate()
() => {
    function parseTileDate(tile) {
        // Tile renders: "JobTitle\nCompany\nMM/YYYY – MM/YYYY" or "...– Present"
        const text = tile.innerText || '';
        // Match patterns: "03/2026", "06/2014", "Present"
        const matches = text.match(/(\d{2})\/(\d{4})/g) || [];
        if (!matches.length) return 0;
        // First match = start date, last match = end date (or "Present" = 999999)
        const toSortable = (s) => {
            const [mm, yyyy] = s.split('/');
            return parseInt(yyyy) * 100 + parseInt(mm);
        };
        const isPresent = /present/i.test(text);
        if (isPresent) return 999999;  // Current job always sorts first
        return toSortable(matches[matches.length - 1]);  // Sort by end date desc
    }

    const tileList = document.querySelector('.apply-flow-profile-item-tile-list, .profile-item-list');
    if (!tileList) return 0;
    const tiles = Array.from(tileList.querySelectorAll('.apply-flow-profile-item-tile'))
        .filter(t => !/bachelor|master|degree|education/i.test(t.innerText));
    
    tiles.sort((a, b) => parseTileDate(b) - parseTileDate(a));
    tiles.forEach(t => tileList.appendChild(t));  // Re-insert in sorted order
    return tiles.length;
}
```

> [!WARNING]
> The Knockout VM `parent.forms.sort()` approach in `jpmc_nail.py` and `experience_section_agent.py` is UNRELIABLE — `startDate()` observable returns inconsistent formats. The DOM text re-insertion approach above is the empirically correct fix. After implementation, update SCAR_TISSUE.md.

### 4.2 Terms & Conditions Modal Fix

**Location:** `apply_orchestrator.py` `run()` loop, BEFORE the `while` loop enters any section handler.

**Code to add at top of while loop (line 108 in current file):**
```python
# --- MODAL PRE-CHECK: Dismiss full-page legal agreement before section dispatch ---
modal = page.locator("#applyFlowLegalDisclaimer, .apply-flow-full-page-agreement, [class*='legal-disclaimer']")
if modal.count() > 0 and modal.first.is_visible():
    logger.info("[ApplyOrchestrator] Terms modal detected. Clicking AGREE...")
    agree_btn = page.locator("button:has-text('AGREE'), button:has-text('Agree'), button:has-text('I Agree')")
    if agree_btn.count() > 0:
        agree_btn.first.click()
        time.sleep(1.5)
        page.wait_for_selector("#applyFlowLegalDisclaimer", state="detached", timeout=5000)
    logger.info("[ApplyOrchestrator] Terms modal dismissed.")
    continue  # Re-detect section AFTER modal is gone
```

### 4.3 Conditional Question Rescan

> Superseded proposal (kept for history): the sketch below was replaced at build
> time. As implemented: `QuestionnaireSectionAgent.heal()` runs 4 passes
> (`max_passes = 4`) — binary → competency → dropdown → `heal_conditional_questions`
> — with discover-all → single batch IPC write → resolve-all → single answer
> write → actuate-all, plus dispatcher cascade re-heals (max 3).

**Location:** `questionnaire_section_agent.py` or `apply_orchestrator.py` Section 2 handler.

After all fixed Section 2 sub-agents complete, the orchestrator must:
```python
MAX_CONDITIONAL_PASSES = 3
for _ in range(MAX_CONDITIONAL_PASSES):
    cond_ipc = self.dispatcher.scan_and_write_conditional_questions(page, candidate_data)
    if not cond_ipc.get("found_new_questions"):
        break
    # AG Brain answers → script fills → verify
    self.dispatcher.evaluate_and_heal_subsection("conditional_questions", page, candidate_data)
```

---

## 5. IPC File Management Rules

1. **One active IPC file at a time** — orchestrator clears/resets `section_question.json` at the START of each subsection.
2. **Atomic writes** — scripts write the full JSON in one `json.dump()` call (not incremental). Use `guard.safe_write_json()` per GATE 6.
3. **Never hardcode in IPC** — `questions[].answer` is always set by AG Brain reading from profile. Scripts NEVER pre-populate `answer`.
4. **IPC reset on error** — if `status = ERROR` for >180 seconds, orchestrator writes `status = IDLE` and re-runs only the failing subsection.
5. **IPC files are NOT committed to git** — add `CompanySiteApply/ipc/*.json` to `.gitignore`.

---

## 6. Verification Protocol (Per Subsection)

After each subsection's `heal()` completes:

1. **DOM Read-Back Verification**: Script reads back every filled field value from the DOM and compares against the `answer` in IPC. Mismatches → flag as `verification_failed`.
2. **AG Brain Structured Verification** (Section 4 review): `VisualVerifierSubAgent` extracts the structured DOM readback dict (experience/education tiles, documents) and enforces the `ORDER_UNVERIFIED` pre-submit gate. This is NOT a screenshot — it's a structured data check.
3. **Full-Page Screenshot** (Section 4 only): `VisualVerifierSubAgent` captures the complete Section 4 review page before the human gate.
4. **Advance Gate**: Orchestrator calls `self.advance(page)` ONLY when ALL subsections of the current section report `verified = True`.

**Selective Subsection Re-Run:**
If verification fails for `experience_tile_3` (out of 9), the orchestrator calls ONLY `s3_experience_tile.py --tile-index 3` and retries up to 3 times before flagging for human review.

---

## 7. Implementation Sequence (Approved Build Order)

> [!IMPORTANT]
> **Gate 3 Active.** No code may be written until this document is reviewed and approval is given for each phase. Each phase is a separate manual approval gate.

### Phase 0 — IPC Infrastructure (PREREQUISITE)
- [x] Create `CompanySiteApply/ipc/` directory
- [x] Create `CompanySiteApply/ipc/section_question.json` (empty template)
- [x] Create `CompanySiteApply/ipc/ipc_manager.py` — utility class: `write_questions()`, `write_answers()`, `read()`, `get_status()`, `wait_for_answers()`, `mark_done()`, `reset()`
- [x] Add `CompanySiteApply/ipc/*.json` to `.gitignore`

### Phase 1 — Modal Fix (CRITICAL BUG, HIGH PRIORITY)
- [x] Edit `apply_orchestrator.py`: Add Terms & Conditions modal pre-check at top of `while` loop (§4.2)
- [x] Add SCAR_TISSUE.md entry for modal trap fix

### Phase 2 — Experience Ordering Fix (CONFIRMED BUG)
- [x] Create `section_agents/scripts/s3_experience_ordering.py` — DOM text date parsing sort (§4.1)
- [x] Update `ExperienceSectionAgent._reorder_tiles_reverse_chronological()` to call new script
- [x] Update `JPMCNail.reorder_experience_tiles()` to use DOM text sort instead of Knockout VM sort
- [x] Add SCAR_TISSUE.md entry for ordering fix

### Phase 3 — Conditional Question Rescan (CONFIRMED BUG)
- [x] Create `section_agents/scripts/s2_conditional_questions.py` — DOM rescan for newly visible required questions
- [x] Update `questionnaire_section_agent.py` `heal()` to call conditional rescan after first pass
- [x] IPC integration: conditional question answers go through full `ANSWER_REQUIRED → ANSWERED` cycle

### Phase 4 — Section 2 IPC Integration
- [x] Create `section_agents/scripts/s2_binary_questions.py` — write to IPC, wait for ANSWERED, fill DOM
- [x] Create `section_agents/scripts/s2_competency_questions.py`
- [x] Create `section_agents/scripts/s2_dropdown_questions.py`
- [x] Update `BinaryQuestionSubAgent` and `TechnicalCompetencySubAgent` to delegate to scripts via `IPCManager`

### Phase 5 — Section 3 IPC Integration
- [x] Create `section_agents/scripts/s3_experience_tile.py` (parametrized by `--tile-index N`)
- [x] Create `section_agents/scripts/s3_education_tile.py`
- [x] Update `ExperienceSectionAgent.heal()` to iterate tiles via the new script

### Phase 6 — Section 4 Document Independence
- [x] Create `section_agents/scripts/s4_resume_upload.py` (independent; checks own state)
- [x] Create `section_agents/scripts/s4_cover_letter_upload.py` (independent; stale → remove → upload)
- [x] Refactor `documents_subagent.py` to delegate to these two scripts
- [x] Session freshness flags stored in IPC `session_id` context (not in-memory class vars)

### Phase 7 — Verification & Visual Gate
- [x] Update `visual_verifier_subagent.py` — send structured DOM readback dict to AG Brain for confirmation
- [x] Full-page screenshot on Section 4 only

---

## 8. Files To Modify (Pre-Approved Touch List)

| File | Change Type | Phase |
|------|-------------|-------|
| `apply_orchestrator.py` | Edit: modal pre-check | 1 |
| `jpmc_nail.py` | Edit: replace `reorder_experience_tiles()` sort logic | 2 |
| `experience_section_agent.py` | Edit: replace `_reorder_tiles_reverse_chronological()` | 2 |
| `questionnaire_section_agent.py` | Edit: add conditional rescan loop | 3 |
| `section_agents/sub_agents/binary_question_subagent.py` | Edit: delegate to IPC scripts | 4 |
| `section_agents/sub_agents/technical_competency_subagent.py` | Edit: delegate to IPC scripts | 4 |
| `section_agents/sub_agents/documents_subagent.py` | Edit: split into two independent script calls | 6 |
| `section_agents/sub_agents/visual_verifier_subagent.py` | Edit: structured data verification + screenshot | 7 |
| `.gitignore` | Edit: add `ipc/*.json` | 0 |

**New Files (all in `section_agents/scripts/`):**
- `s2_binary_questions.py`
- `s2_competency_questions.py`
- `s2_dropdown_questions.py`
- `s2_conditional_questions.py`
- `s3_experience_tile.py`
- `s3_education_tile.py`
- `s3_experience_ordering.py`
- `s4_resume_upload.py`
- `s4_cover_letter_upload.py`
- `CompanySiteApply/ipc/ipc_manager.py`
- `CompanySiteApply/ipc/section_question.json` (template)

---

## 9. Zero-Hardcoding Invariants (Must Hold Throughout)

1. **All candidate PII** resolves from `candidate_data` passed by `ApplyOrchestrator` — never literals in scripts.
2. **All question answers** are set by AG Brain from IPC — never hardcoded in scripts.
3. **All file paths** (cover letter PDF, resume PDF) resolve from `candidate_data.cover_letter_path` / `candidate_data.resume_path`.
4. **Tile count** resolved from `len(candidate_data.candidate.work_experience)` — never hardcoded as 9.
5. **Section detection** is URL-based + DOM confirmation — never hardcoded section names as string literals in dispatch logic.

---

## 10. Relation to Existing IPC Pattern

The new `section_question.json` IPC file is **analogous to** the existing `pending_question.json` and `batch_question.json` files used in the Naukri subsystem (`core/`), but **separate** per GATE 9 (subsystem isolation).

| Existing (Naukri core, under `profiles/<profile>/output/`) | New (CompanySiteApply) |
|------------------------|------------------------|
| `pending_question.json` | `CompanySiteApply/ipc/section_question.json` |
| `batch_question.json` (+ `batch_answer.json`) | `CompanySiteApply/ipc/batch_section_question.json` (future) |
| `AIClient.answer_screening_question()` | `AIBrainResolver.answer_ipc_file()` (async-brain bridge) |
| `ipc_auto_resolver.py` | `IPCManager` in `CompanySiteApply/ipc/ipc_manager.py` |

Zero cross-imports between subsystems.

---

## 11. Resumption Instructions (For Token-Exhausted Sessions)

If this session ends before full implementation:

1. Re-read `ACTIVE_CONSTRAINT_BLOCK.md` + `SCAR_TISSUE.md` (mandatory).
2. Check which Phase (§7) was last completed — grep for `# Phase N COMPLETE` comments in modified files.
3. Resume from the next uncompleted phase.
4. Before writing any code: run `python -m unittest discover -s CompanySiteApply/tests` — all 193 must pass (plus 15 cover-letter-id tests in `tests/`, 10 knowledge tests).
5. After each phase: run tests again. Regression = stop and investigate before continuing.
6. This document is the canonical spec. Do not deviate without updating it first.

---

## 12. Principal Verification Addendum (2026-10-12 — codebase audit, 75/75 tests passing)

Verified against live code (no vector/graph dependency). All 7 phases exist as claimed:
Phase 0 `ipc_manager.py` (atomic `.tmp`→replace), Phase 1 modal pre-check (top of `run()` loop with `continue`),
Phase 2 `s3_experience_ordering.py` (numeric `YYYY*100+MM`, `Present=99999999`, KO+DOM dual layer, `jpmc_nail.py` delegates),
Phase 3 conditional rescan (4-pass loop in `questionnaire_section_agent.py` + `s2_conditional_questions.py`),
Phases 4–6 nine discrete scripts with sub-agent delegation, Phase 7 visual verifier (structured readback + human gate, never submits).

Flaws found and fixed in this pass (see git diff):
1. **Session correlation broken** — orchestrator minted `session_id` but never passed it down; every script fell back to `sess_*` placeholders. Fixed: orchestrator injects `_ipc_session_id` into `candidate_data`; all scripts/sub-agents resolve via `get_effective_session_id()`.
2. **IPC handshake was sync-only loopback** — `wait_for_answers()` had zero callers; scripts resolved in-process. Documented honestly as sync fast-path; added `AIBrainResolver.answer_ipc_file()` + `STATUS_DONE`/`get_effective_session_id()` so an external brain can drive the true `ANSWER_REQUIRED → ANSWERED` switch.
3. **DocumentsSubAgent double actuation** — delegated to `s4_*` scripts AND repeated the same remove/upload inline (double `set_input_files`). Removed inline block; delegation is now the single path.
4. **Invented fallback data** — `India`/`Bengaluru`/`Lead Software Engineer`/`Bachelor's Degree`/`Computer Science` literals violated zero-hardcoding. Replaced with profile-grounded values + `ACTION_REQUIRED` deferral when truth is absent.
5. **Conditional scanner blind spots** — DROPDOWN pushed with `available_choices=[]` (brain cannot answer), CHECKBOX/TEXT/TEXTAREA unhandled, dropdown actuation missing. Fixed: option fetch via toggle open, new CHECKBOX/TEXT branches, Python-side dropdown/checkbox/text applicators.
6. **Dropdown IPC overwrite** — per-question `write_questions()` clobbered earlier questions. Refactored to discover-all → single batch write → resolve-all → single answer write → actuate-all.
7. **Experience tile stale indices** — fixed `range(tiles_count)` enumerated stale handles after SAVE re-renders; now re-queries DOM per tile, bounded by candidate truth count.
8. **Stale runtime state** — reset `section_question.json` to neutral IDLE; cleaned 20 project `__pycache__` dirs. Root `*.py` entry scripts are tracked files (not garbage) — left untouched. Test-generated `Sarah_Connor` blueprint PDFs are re-polluted by every test run (pre-existing harness issue, noted not fixed).

Remaining known limitations (not fixed, by design/scope):
- Sync fast-path still couples brain+DOM in one process; true cross-process use requires the caller to opt into `wait_for_answers()` + external `answer_ipc_file()` loop.
- Single IPC file = one active subsection at a time; history lives in `screening_answers.json`, not in IPC.
- `s3_education_tile.py` covers degree/major/country only; school/month/year handled by `EducationSectionAgent` inline fallback (intentional superset, runs only when script defers).
