# Company Portal Page-Loop Protocol & JPMC CX_1001 Case Study

> **Document Version:** 1.0 — Standing Order (never overruled)
> **Last Updated:** 2026-10-07
> **Authority:** Owner-mandated operating protocol for every company-site
> application run and every future portal integration. Preload this file
> before writing or editing any finger, nail, scraper, or shared helper.
> Companion rule: WORKSPACE_RULES.md Directive 10.

---

## 1. The Universal Page Loop (every page, every portal, no exceptions)

For each wizard page, in order, with zero hardcoded field lists (forms vary
even between requisitions of the same company):

1. **DISCOVER** — extract every field, upload, pill group, and button live
   from the DOM (`extract_form_schema` + ARIA/custom-control scan). Never
   assume a field exists or is absent.
2. **VERIFY CURRENT STATE** — read back every live value, every pill
   selection state, every attachment presence, every invalid flag and inline
   error. Snapshot first; this is the ground truth, not the plan.
3. **FILL / UPLOAD / CORRECT** — for each gap versus the profile: set text
   fields, resolve combos (fragment-filter → fuzzy/alias/AI → keyboard
   select → read-back proof), click pills by exact scoped text, attach
   required files. Correct wrong values; do not only fill empties.
4. **RE-VERIFY** — re-read everything from step 2. Red errors, wrong
   selections, missing uploads, wiped values: fix and loop back to step 2
   (max 3 passes). Route each residual explicitly: deterministic retry with
   a different strategy → AI adjudication → human operator. Never advance
   with known-red fields.
5. **ADVANCE ONLY WHEN CLEAN** — click NEXT/SUBMIT exclusively through the
   button allowlist (`safe_click_button`). Verify the step actually changed
   (URL/marker + zero errors).
6. **REPEAT** — the new page starts again at step 1 (pre-verification:
   resume imports pre-fill values that must be verified, not trusted).

### Session scenarios (checked at page 1 before anything else)

- **(a) Fresh:** nothing filled, nothing uploaded — full fill + upload.
- **(b) Partial autosave:** some values held, some wiped — audit first,
  repair only gaps, re-verify survivors (a held value can still be wrong).
- **(c) Intact:** everything present — verify all, correct wrong ones,
  advance. Never skip verification because "it looks done".

---

## 2. JPMC Oracle CX_1001 Instantiation (job 210787954, proven 2026-10-07)

Flow: `/job/<id>` → APPLY NOW → `/apply/email` (email + terms ACCEPT +
NEXT → OTP, human enters code) → `/apply/section/1` → … → `/apply/section/4`
(STOP before SUBMIT; capture review + answers.json; human approves submit).

- Section 1: resume upload → parse banner text differs from docs; success =
  attachment row with Remove button + zero errors. Parser fills name, email,
  phone, LinkedIn; human fills/audits Title, address, PIN, City, State,
  Country, signature.
- Demographic flexfield IDs rev per requisition (`...-ATTRIBUTE16-8` became
  `-9` mid-run): resolve exact ID → name attribute → semantic label, in
  that order. Zero-size inputs are normal here.
- Screening pills are `role="radio"` buttons: verify via `aria-checked`,
  never `aria-pressed`/class names. Click by exact scoped text (unscoped
  `:has-text('Mr.')` matched a container and hit Doctor).
- Experience tier answers from `total_experience_years` (highest tier ≤
  experience); persist `requires_sponsorship`-class truths to
  `candidate.requires_sponsorship` + `ats_answers` + `auto_learned_truths`
  the first time a human confirms them.

---

## 3. Component Anatomy Discovered (CX bespoke combobox — NOT Oracle JET)

No JET/jQuery/Knockout present. Each combo is:
`input[role=combobox][aria-controls=<id>-listbox]` + toggle
`button[aria-controls=<same-id>]` + `ul/div` listbox. The ids re-render
(`city-44-*`), so they are READ from `aria-controls` at runtime, never
stored. Zero-size inputs reject Playwright visibility-gated actions; the
working gestures are: real mouse on the mapped toggle, fragment typing
with real keystrokes, ArrowDown + Enter, native-setter + event chain.

---

## 4. Failure Log (every trap hit, so future portals skip them)

1. Advancing on URL-change without per-field persistence checks (red fields
   carried forward). Fix: step advances only on clean re-verification.
2. Unscoped `:has-text` clicks landing on containers/Doctor. Fix: exact-text
   match scoped to the question container.
3. `ControlOrMeta+A` is not a valid Playwright key (silently wrong).
   Fix: `Control+A` on Windows; `Meta+A` on macOS.
4. Single-fragment filtering: profile spelling `Bang…` filters OUT portal
   spelling `Beng…`. Fix: one fragment pass per spelling + alias list.
5. Clicking the clear-X control as an "option"; Tab walking focus onto X.
   Fix: clear/close/remove/dismiss/X exclusion in every option query,
   allowlisted wizard buttons only, blur-dispatch instead of Tab.
6. Re-render wipes (email, city, pills): values die on navigation/modal
   churn. Fix: settle polling, final read-back, re-verify after every
   render; unsubmitted section answers do not survive Back.
7. Type-commit overwriting good portal selections with raw text.
   Fix: settle first; fallbacks may only type the portal spelling.
8. Contextless `AIClient()` auto-discovers an arbitrary live profile.
   Fix: blank non-discovering context for pure option-mapping calls.
9. Duplicate multi-select pills from repeated clicks. Fix: pill-presence
   check = already-set; dedupe pass before advancing.
10. AI alias calls without visible options context return generics.
    Fix: always send field label + want + visible option sample.
11. Shell one-liners that open a file for write before reading it emptied
    two source files mid-session (recovered from git). Fix: file tools or
    explicit read-then-write scripts only.

12. Conditional dynamic questions appearing after selections (e.g., sub-specialization after primary expertise). Fix: Re-scan entire form for new fields after filling any major combobox or pill group.
13. Required fields (like `[aria-required="true"]`) missing validation errors but allowing page advance (non-blocking). Fix: `FORM_ERROR_SELECTORS` hardened with `.input-row--invalid`, and strict local assertion of required attributes before clicking Next.
14. Trusting ATS pre-filled data without deep verification (e.g., ATS guessing "December" for a graduation year, or missing employer cities). Fix: Always open every "completed" tile, read all fields, and cross-reference with `candidate_config.json` before accepting.
15. Submitting generic cover letters because the agent blindly pulled the static `Cover letter` string from `candidate_config.json`'s `screening_heuristics`. Fix: The agent must ALWAYS dynamically generate a role-specific Cover Letter based on the actual Job Description and save it to the application tracking folder before filling the form.

---

## 5. Standing Rules for Future Portal Work (binds all sessions)

- Preload this file + `SCOPE_OF_EDIT.md` before any new finger/nail/scraper.
- **Application Tracking & Tailoring:** Before applying, the agent MUST create a folder at `CompanySiteApply/<Company_Name>/<Role_Name>/`. It must generate a dynamically tailored Cover Letter (and tailored Resume notes) optimized for that specific JD and save them there alongside a `Tailoring_Audit.md` file. Never paste generic cover letters.
- Shared-first: portal-wide fixes go in `dom_helpers.py`/shared libs with
  regression tests; per-company files carry selectors + truth-gating only.
- No hardcoded field lists, city names, IDs, model names, or profile paths.
- Every fill ends in DOM read-back proof; every advance ends in the shared
  step guard; every residual is classified (retry/AI/operator), never
  silently carried forward.
- Temp probe scripts are deleted the same session; the tree stays clean.
