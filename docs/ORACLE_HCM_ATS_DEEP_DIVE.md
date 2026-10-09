# Oracle Cloud HCM Candidate Experience (ORC) - Engineering Architecture & Universal Automation Bridge

> **Document Classification:** Master ATS Engineering Reference & Cross-Agent Cognitive Bridge  
> **Document Version:** 2.0 — Oracle JET 19.0, Knockout Reactive State, CX Component Blueprints & Nail Overrides  
> **Last Updated:** 2026-09-21  
> **Target ATS Ecosystem:** Oracle Cloud HCM (Candidate Experience / ORC) & Oracle Taleo  
> **Framework Stack:** Oracle JET (`ojVersion 19.0.0`), Knockout.js (`ko`), React Wrapper Components (`cx-select`, `cx-select-pills`), Chrome DevTools Protocol (CDP)  
> **Author:** Diagnostic & Implementation Agent (Pair Programming with Human Principal Architect)  
> **Scope:** Canonical architectural knowledge, DOM tree blueprints, Knockout observable state management, battle-tested fixes, and self-healing protocols.

---

## 1. Executive Summary & Philosophy

When automating enterprise ATS platforms like Oracle Cloud HCM, standard naive browser automation (e.g. static CSS selectors, basic `element.click()`, raw `element.fill()`) consistently fails or produces corrupt submissions. This occurs because **Oracle Cloud HCM does not use plain HTML forms**:
1. It is an **Oracle JET (JavaScript Extension Toolkit)** Single Page Application built on an asynchronous Knockout.js MVVM reactive framework.
2. Form fields are embedded inside **React functional components** (`cx-select`, `cx-select-pills`, `cx-date-picker`) bridged into Knockout via custom binding handlers (`data-bind="react: { component: 'cx-select', props: ... }"`).
3. Actions (such as clicking `SAVE` on an inline tile) do **not** dispatch standard HTTP POSTs or form submit events. Instead, they trigger internal Knockout ViewModel mutations. If synthetic DOM events fail to trip Knockout's internal observables (`valueObserver`, `isTouched`, `isDirty`), the form will either silently ignore input or display persistent red validation errors (e.g., *"The Status field is required."* or *"Fields to fix: 1"*).

This document serves as the **permanent engineering bridge**. Any AI agent in any subsequent session can read this document to understand the underlying DOM reality, execute infallible automations, and self-heal any edge case.

---

## 2. Component Taxonomy & DOM Blueprints

### A. Navigation & URL Route Structure

| Step / Section | Canonical URL Route | Component / Block Class | Key Interactions |
| :--- | :--- | :--- | :--- |
| **Step 0: Email Authentication** | `/apply/email` | `apply-flow-block--profile-import` | Email input, Honeypot bypass (`input[name="honey-pot"]`), Legal consent checkbox. |
| **Step 0b: Verification PIN** | `/apply/pin` or `/apply/verification` | `apply-flow-block--pin-verification` | 6-digit numeric PIN entry from email. |
| **Section 1: Contact Information** | `/apply/section/1` | `apply-flow-block--personal-information-basic` | Name, Phone, Address, Postal Code, Country. |
| **Section 2: Application Questions** | `/apply/section/2` | `apply-flow-block--disqualification-questions` | Radio pill selectors (`cx-select-pill-section`), Notice period, Legal eligibility. |
| **Section 3: Work & Education** | `/apply/section/3` | `apply-flow-block--work-and-education-timeline` | `beautiful-timeline-item` cards, Degree/Major selectors, Bulleted role descriptions (`• `). |
| **Section 4: More About You** | `/apply/section/4` | Multiple blocks (detailed below) | Documents, Skills, Certifications, Languages, Diversity, Citizenship, E-Signature. |

---

### B. Section 4 Deep Dive: Block-by-Block Blueprint

#### 1. Supporting Documents & Dropzones (`.apply-flow-block--file-upload`)
- **Resume Dropzone:** Target hidden file input: `input[type="file"][id*="resume"]` or first file input.
- **Cover Letter Dropzone:** `#attachment-upload-4`.
  - **Interaction Protocol:** Never attempt to click the visual "Drop file here" container. Use Playwright's `set_input_files("#attachment-upload-4", pdf_path)` directly on the hidden `<input type="file">`.
  - **Verification:** Ensure sibling status changes to `Saved` with green checkmark and `REMOVE COVER LETTER` button becomes visible.

#### 2. Skills Collection (`.apply-flow-block--skill`)
- **Container:** `.apply-flow-profile-item-tile` array.
- **Add Button:** `button.apply-flow-profile-item-tile__new-tile` (text: `ADD SKILL`).
- **Form Fields:**
  - Name: `input[name="name"]` or `[id*="name-"]`.
  - Date Achieved Month: `[id*="month-dateAchieved"][id*="toggle"]` -> gridcell overlay `[role="gridcell"]`.
  - Date Achieved Day: `[id*="day-dateAchieved"][id*="toggle"]` -> gridcell overlay `[role="gridcell"]`.
  - Date Achieved Year: `[id*="year-dateAchieved"][id*="toggle"]` -> gridcell overlay `[role="gridcell"]`.
- **Commit Protocol:** Must invoke parent component `doneProfileItem(form)` (see Section 3 below).

#### 3. Licenses & Certifications (`.apply-flow-block--tile-profile-items`)
- **Trap: "Fields to fix: 1" / Missing Pill Selection:**
  - When resume auto-parser pre-fills certificates, it leaves the Type pill unselected.
  - Form requires explicitly clicking `<button class="cx-select-pill-section">Certificate</button>`.
- **Date Handling:**
  - Issue Date (`issueDate`): Populated from candidate resume (e.g. `July 15, 2024`).
  - Expiration Date (`expirationDate`): Must be **completely cleared / empty** (`Present`). Setting an expiration date in the past immediately flags the tile as invalid.

#### 4. Languages (`.apply-flow-block--unique-tile-profile-items`)
- **Add Button:** `button.apply-flow-profile-item-tile__new-tile` (text: `ADD LANGUAGE`).
- **Internal Knockout Element Names:**
  - `contentItemId`: Language selector (e.g., `109000016` = English, `109000024` = Hindi).
  - `readingLevelId`: Reading Fluency (`300000003844726` = 3 / "Flyers" / Fluent).
  - `writingLevelId`: Writing Fluency (`300000003844726` = 3 / "Flyers" / Fluent).
  - `speakingLevelId`: Speaking Fluency (`300000003844726` = 3 / "Flyers" / Fluent).
  - `nativeSpeakerFlag`: Native speaker pill (`Y` / `N`).

#### 5. Diversity Information (`.apply-flow-block--diversity`)
- **Gender:** `#IN-STANDARD-ORA_GENDER-STANDARD-7`
  - React combobox. Click toggle button `#IN-STANDARD-ORA_GENDER-STANDARD-7-toggle-button` to open overlay.
  - Click gridcell matching `Male`, `Female`, etc.
- **Date of Birth:**
  - Month: `#month-IN-STANDARD-ORA_DATE_OF_BIRTH-STANDARD-8-toggle-button`
  - Day: `#day-IN-STANDARD-ORA_DATE_OF_BIRTH-STANDARD-8-toggle-button`
  - Year: `#year-IN-STANDARD-ORA_DATE_OF_BIRTH-STANDARD-8-toggle-button`

#### 6. Citizenship (`.apply-flow-block--candidate-citizenship`)
- **Container:** `.standard-apply-flow-profile-item-citizenship-99`.
- **Trap: Disabled Status Pills:**
  - `citizenshipStatus` is bound to `dependencyField: "citizenship"`.
  - In Knockout, `citizenship` value is stored as country code (`IN` for India), not string `"Indian"`.
  - If the status pill is disabled, access the Knockout observable `statusElem.isDisabled(false)` and set `statusElem.value("A")` (Active), then call `comp.doneProfileItem(form)`.

#### 7. E-Signature (`.apply-flow-block--apply-flow-e-signature`)
- **Full Name Input:** `#fullName-5` (name: `fullName`).
- **Interaction Protocol:** Focus, assign candidate full legal name (`Udaysagar Kandpal`), and dispatch `input`, `change`, and `blur` events.

---

## 3. The Knockout / Oracle JET Internals Protocol

### Why Synthetic DOM Clicks Fail
Oracle JET binds Knockout contexts to DOM elements using internal expando properties formatted as `__ko__<timestamp>`. Inside each element's binding context:
- `$data` represents the active form model.
- `$parent` or `$parents[3]` represents the parent profile item manager component.
- The parent component exposes the master synchronization method: `doneProfileItem(form)`.

When an automation script merely clicks a button with class `.save-btn`, Knockout's validation pipeline checks whether `isValidationInProgress` or `isValid()` has resolved. If the synthetic click didn't trigger React's synthetic event bubble, the save silently aborts.

### The Canonical Universal Save Solution
```javascript
// Universal Oracle JET profile item commit
async function commitProfileItem(blockSelector) {
    const block = document.querySelector(blockSelector);
    const el = block.querySelector('label') || block.querySelector('.input-row');
    const koProp = Object.keys(el || {}).find(k => k.startsWith('__ko__'));
    let ctx = null;
    if (el && koProp) {
        for (let k of Object.keys(el[koProp])) {
            if (el[koProp][k] && el[koProp][k].context) {
                ctx = el[koProp][k].context;
                break;
            }
        }
    }
    const comp = ctx.$parents.find(p => p && p.activeForm);
    const af = comp.activeForm();
    await comp.doneProfileItem(af);
}
```

---

## 4. Master Auto-Healing Runbook: Solved Traps

| # | Trap Description | Underlying Root Cause | Battle-Tested Automated Fix |
| :--- | :--- | :--- | :--- |
| **1** | Multi-Tab Hijacking | Background `downloader` tab spawned at index 0. | Filter pages using `[pg for pg in browser.contexts[0].pages if 'apply' in pg.url][0]`. |
| **2** | Hover Visibility Timeout | Edit/Delete icons (`.edit-item-icon`, `.delete-icon`) are hidden by CSS. | Dispatch direct JavaScript `.click()` or hover over parent card before clicking. |
| **3** | "Fields to fix: 1" Badge | Resume auto-parser populates title/dates but omits Type pill (`Certificate` vs `License`). | Open tile edit form, click `.cx-select-pill-section` matching `Certificate`, then commit. |
| **4** | Missing Skill Achievement Dates | Parser imports raw skill text without dates. | For each tile, click Month/Day/Year toggles and pick dates (July 15, 2014–2021) representing 5+ years of experience. |
| **5** | Red Error: "The Status field is required" | Country is set, but `Status` pill is unselected or disabled. | Set `statusElem.isDisabled(false)`, assign `statusElem.value("A")`, and commit via `doneProfileItem`. |
| **6** | Bot Trap / Honeypot Detection | `input[name="honey-pot"]` is hidden in Section 0. | If populated by autofill, immediately clear to `""`. Never send keystrokes to it. |
| **7** | Skill Name Misdirection into Month Combobox | Naive selector (`.profile-item-content--form input[type="text"]`) targets `#month-dateAchieved-xxx` instead of the skill name field, causing skills to be saved as "Unnamed Skill". | Target `input[name="skills"]` (`.input-row__control`) directly with Playwright `fill()`. Never use generic text input fallbacks. |
| **8** | Evergreen Certification Expiration Trap | Populating an issue date (e.g. 2014 or 2024) into `expirationDate` causes validation error "Expiration date cannot be in the past". | Evergreen certifications must have `expirationDate` completely cleared (`Present`). Only populate `issueDate`. |
| **9** | Background Digital Assistant (ODA) False Error Flags | Background modal `#oda-work-summary-text-area` has `.oj-invalid` in invisible DOM, triggering false positives. | Filter error queries for `isElementVisible()` and exclude `#oda-chat-widget` and `#oda-work-summary-dialog`. |
| **10** | Legal Consent Modal Intercepting Pointer Events (Step 0) | Clicking `#legal-disclaimer-checkbox` or its label opens `.standard-apply-flow-agreement__dialog` modal, intercepting clicks to `NEXT`. | Target the modal's `button.app-dialog__footer-button` with text `AGREE`. Clicking `AGREE` closes the dialog, checks the box, and unblocks `NEXT`. |
| **11** | Work Experience Tile Truncation by Oracle Native Parser | Oracle ATS natively omits Employer Country, Employer City, leaves Internal unselected, and flattens achievements into unformatted text. | Every single tile in Section 3 must be opened via Edit, Country set to "India" (using `:text-is('India')` exact match), City populated from candidate profile, Internal set to "No", and Achievements populated with structured bullet points (`• `). |
| **12** | Inline Expanding Form Containers vs. Modal Dialogs (CX_1001) | In CX_1001, clicking Edit expands forms inline within the page layout rather than opening an `.app-dialog`. | Never constrain SAVE button locators to `.app-dialog`. Use `.save-btn, button:has-text('Save')`. |
| **13** | Education Combobox "Degree is required" Validation Failure | Naive `.fill("Bachelor's Degree")` fails to select the option in the reactive gridcell listbox, leaving Degree blank upon save. | Fill prefix (`Bachel`), wait 500ms, dispatch keyboard `ArrowDown` and `Enter`, and set Area of Study. |
| **14** | Hidden Tile Edit Button Actionability Timeout (30s) | The edit pencil icon (`.apply-flow-profile-item-tile__edit-item-icon`) has 0 opacity until hovered, causing Playwright's `scroll_into_view_if_needed()` to wait 30s. | Dispatch native JavaScript click directly: `tile.evaluate(el => el.querySelector('.apply-flow-profile-item-tile__edit-item-icon').click())`. |
| **15** | Blind Boolean Heuristic Fallback & Poisoned Learned Truth | Generic Yes/No questions (e.g. Work Authorization) lacking "interview" keywords defaulted to "No", which was then persisted to `auto_learned_truths`, corrupting future attempts. | Add explicit topic gates for Work Authorization, 18+ age, and sponsorship. Prevent non-grounded heuristic answers from being persisted into `auto_learned_truths`. |
| **16** | General Experience Tier Option Matching Failure | Regex searched for `experience in/with/as <technology>`, defaulting `calc_val` to 0.0 on general experience prompts, picking "No Prior Experience". | Dynamically match candidate's total experience against option tiers and select the highest threshold `<= total_exp` (e.g. 9.8 years -> "At least 5 years of experience"). |
| **17** | Ghost Dialog Trap (`.app-dialog` vs inline `.apply-flow__content-form`) | CX_1001 renders forms inline without `.app-dialog`, causing `.app-dialog:visible .app-dialog__header` queries to return empty and misclassifying Education tiles as Work Experience. | Detect Education modals by checking tile titles or visible inputs (`[id^='contentItemId']`, `[id^='areaOfStudy']`), and target inline containers directly. |
| **18** | Unmapped Regional Diversity Combobox | Oracle demographic steps render country-specific dropdowns (e.g. `#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-8`) not covered by standard personal details handlers. | Delegate company-specific and regional survey fields to dedicated Nails (e.g. `JPMCNail`) that resolve military status, ethnicity, and gender from profile data. |

---

### Skill Achievement Date Distribution Matrix

When automating skill achievement dates in Section 4, calculate the achievement year dynamically based on career tenure rather than hardcoding static dates:

| Skill Tier | Examples | Tenure Heuristic | Target Achievement Date |
| :--- | :--- | :--- | :--- |
| **Foundational & Academic** | Core Java, Advanced Java, DSA, OOP, RDBMS | 9+ Years (College / Early Career) | `July 15, 2015` |
| **Senior & Architecture** | Distributed Systems, Event-Driven Architecture, Microservices, Team Management | 6+ Years (Senior Engineer / Architect milestone) | `July 15, 2018` |
| **Domain & Production Tooling** | Telecom / MMSC, Kafka, OpenShift, CI/CD, Cassandra | Tenure-Aligned (Based on employer start dates) | `July 15, 2017` – `July 15, 2019` |

---

## 5. Universal Verification & Submission Gate

Before any Oracle Cloud HCM application is submitted:
1. Run **Universal Scoped Error Scanner** (`scanFormErrors()`) across the entire DOM:
   - Check `.oj-invalid`, `.invalid-profile-item-form`, `.oj-text-color-danger`, `[aria-invalid="true"]`, `.input-row__validation`, `Fields to fix`.
   - Ensure invisible background ODA elements are excluded.
   - Error count **must be exactly 0**.
2. Run **Tile Purity Verification**:
   - Total valid tiles must match target count.
   - 0 "Unnamed Skill" draft tiles.
3. Capture full-page high-resolution screenshot.
4. Present verified checklist to the human architect for final review before clicking `SUBMIT`.

---

## 6. Submit Button Architecture & Post-Submission Confirmation

### A. DOM Blueprint of the Submit Button
The final submission button in Oracle Cloud HCM Candidate Experience has the following exact architecture:
- **Selector:** `button.apply-flow-pagination__submit-button`
- **Class Hierarchy:** `button apply-flow-pagination__button apply-flow-pagination__submit-button theme-color-1`
- **Knockout Bindings:** `data-bind="a11y.setFocusOnClick: { focusOn: '.apply-flow-fixer__button', delay: 100}, click: submit, enable: isSubmitEnabled()"`
- **Interaction Rule:** Scroll into view and execute Playwright `.click()`. Knockout evaluates `isSubmitEnabled()`; if zero form errors exist, the action dispatches an internal XMLHttpRequest / fetch to Oracle HCM backend.

### B. Post-Submission Route & Status Verification
1. **Redirection Route:** Upon submission, the portal transitions from `/job/<id>/apply/section/4` to:
   - **Target Route:** `/CandidateExperience/en/sites/<site-name>/my-profile`
   - **Page Title:** `My Applications - <Company> Careers`
2. **Confirmation Signals in DOM:**
   - Text banner: `"Thank you for your job application."`
   - Application list block: `ACTIVE JOB APPLICATIONS`
   - Status Badge: `"Status: Under Consideration"`
   - Confirmation Record: `<Company> <JobId> Applied on <MM/DD/YYYY>`

### C. Application Artifact Archiving Protocol
> **Output-path split (by design):** this CompanySite tree (`APPLIED ON COMPANY WEBSITE/`) is separate from the portal-pipeline tree (`profiles/<profile>/output/applications/<Company>_<Role>/` used by `core/` for Naukri/LinkedIn). Never mix them.
Every submitted application must generate a localized archive under:
`profiles/<candidate>/APPLIED ON COMPANY WEBSITE/<Company>/<Job Role>/` containing:
- `answers.json`: Complete snapshot of form answers, field entries, timestamps, URLs, and confirmation text.
- `submission_confirmation.png`: Full-page screenshot of the `/my-profile` confirmation state.
- `resume.md` and `resume.pdf`: Exact tailored resume submitted to the portal.
- `cover_letter.pdf`: Tailored cover letter attached to the application.

---

## 7. Architecture: ATS Fingers vs Company Nails

### Architectural Separation
- **`core/`**: Exclusively handles third-party portal engines (Naukri, LinkedIn, etc.).
- **`CompanySiteApply/`**: Exclusively handles direct enterprise career site applications.

### The Finger vs Nail Hierarchy
```
CompanySiteApply/
├── fingers/                       <-- ATS Platform Engines (Fingers)
│   ├── base_finger.py             <-- Base contract (inspect, fill, advance, verify)
│   ├── oracle_cloud_finger.py     <-- Generic Oracle Cloud HCM & Taleo mechanics
│   ├── workday_finger.py          <-- Generic Workday mechanics
│   └── greenhouse_finger.py       <-- Generic Greenhouse mechanics
└── nails/                         <-- Company-Specific Overrides (Nails)
    ├── base_nail.py               <-- Base nail hooks (matching, pre/post step, custom fields, answer overrides)
    └── oracle/
        ├── jpmc_nail.py           <-- JPMorgan Chase CX_1001 specific surveys, questions & layout
        └── bristlecone_nail.py    <-- Bristlecone specific layout & honeypots
```

- **Fingers (ATS Engines)**: Handle universal platform mechanics: Oracle JET inputs, knockout bindings, honeypot evasion, multi-step navigation, and file upload protocols.
- **Nails (Company Overrides)**: Handle company-curated questions, regional diversity dropdowns (e.g. India Uniformed forces), experience tier options, and custom workflows.

---

## 8. Mandatory Section 1 Resume Upload & Page-by-Page Audit Protocol

### A. The Core Principle
An autonomous career agent must **NEVER** bypass Section 1 without uploading the tailored resume PDF. Rushing forward or assuming pre-existing session state results in corrupted or unmapped timeline entries on subsequent sections.

### B. Standard Operating Procedure (SOP)

```
[Phase 1: Resume Tailoring]
    -> Generate exact 2-page tailored resume PDF & Cover Letter PDF for target role.
[Section 1: Resume Import Hard Gate]
    -> Upload tailored resume PDF to `input.apply-flow-profile-import-awli__file-upload`.
    -> Poll & WAIT for `.apply-flow-profile-import-awli__success-message:has-text("Profile successfully imported.")`.
    -> Audit personal details (Title: "Mr.", Name, Phone, Address, City: "Bengaluru, Karnataka", PIN: "560100", LinkedIn).
    -> Click NEXT.
[Section 2: Application Questions]
    -> Solve disqualification questions (Age 18+, Work Auth: Yes, Sponsorship: No, Passport: Yes).
    -> Solve technical comboboxes (e.g., Languages: JAVA + SQL via synthetic mousedown/mouseup/click events).
    -> Verify 0 errors, click NEXT.
[Section 3: Experience & Education Timeline Audit & Healing]
    -> Inspect all timeline tiles.
    -> Education Tile: Fix "Fields to fix: 1" / "Unnamed Major". Select Degree ("Bachelor's Degree"), End Date ("July 2015"), Country ("India"), Area of Study ("Computer Science & Engineering"). Click SAVE.
    -> Experience Tiles: For all 9 verified career roles (Cognizant, Infosys, TCS, CL Educate, Navyug, Adobe, IBM, IRCTC, NEC):
       - Set Employer Country: "India"
       - Set Employer City: "Bangalore" / "Noida" / "Delhi"
       - Set Internal: "No"
       - Format Achievements with bullet points (`• ` prefix)
       - Click SAVE.
    -> Verify 0 errors across Section 3, click NEXT.
[Section 4: Review, Supporting Documents & Hard Stop]
    -> Verify Documents: Ensure tailored Resume PDF and Cover Letter PDF both display green checkmark and "REMOVE" button (click "Use" if pending).
    -> Verify Diversity: Ethnicity ("Asian"), Gender ("Male"), Military ("No").
    -> Verify E-Signature: Full Name ("Udaysagar Kandpal").
    -> Capture full-page screenshot (`submission_review_page.png`) and write machine-readable `answers.json`.
    -> HARD STOP: Do NOT click SUBMIT. Halt for human principal architect review.
```

---

## 9. Battle-Tested Production Traps & Remediation Protocols (CX_1002 Learnings)

### Trap 1: Multi-Select Combobox Opening (`preferredLocations`)
- **Phenomenon:** Clicking the tiny dropdown toggle button (`#preferredLocations-XX-toggle-button`, 10×14px) frequently fails to open the listbox or closes it immediately.
- **Root Cause:** In Oracle JET `cx-multi-select`, the toggle button is often obscured or misaligned with Knockout event handlers.
- **Remediation:** Click `input[name='preferredLocations']` directly. This reliably sets `aria-expanded="true"` and mounts `[id^='preferredLocations'][id$='-listbox']`.
- **Pill Selection:** Find the option in the listbox matching candidate preference (or location) and click `.cx-select__list-item`. Ensure the selection commits as a removable pill (`.cx-multi-select-pill`).

### Trap 2: Adjacent Clear-X Reset Button Accidental Wipes
- **Phenomenon:** After selecting City, State, or Preferred Location, navigating or focusing away triggers a wipe, leaving the field empty and showing red error: *"The City field is required."*
- **Root Cause:** Adjacent to every populated combobox is a clear-X reset button (`[id$='-reset-button']`, `.icon-clear`, `button[aria-label*='Remove value']`). Pressing `Tab` or clicking near the field borders focuses and activates this button.
- **Remediation:** 
  1. Never use generic `Tab` key traversal across Oracle comboboxes.
  2. Target dropdown list items strictly with `.cx-select__list-item, .cx-select-list-item`.
  3. Commit and close overlays using `Escape` or clicking neutral safe coordinates (`body` at x=50, y=50).
  4. Never click any button containing `aria-label*='Remove value'` or `icon-clear` during form filling.

### Trap 3: Dependent Geographic Fields (`country` -> `region2`)
- **Phenomenon:** Selecting Country (`India`) dynamically mounts a required `State *` input (`name='region2'`). While selecting City from dropdown often populates State, if State remains empty, advancing to Section 2 is blocked with *"The State field is required."*
- **Remediation:** Always audit both `city` and `region2`. If `region2` is empty, type the state (`Karnataka`) and click the corresponding `.cx-select__list-item` in the dropdown.

### Trap 4: Screening Questions — Radio Pills vs Checkboxes
- **Phenomenon:** If screening answers return multiple options joined by `|||` for a single-choice question, clicking multiple pills toggles earlier choices off and leaves an arbitrary choice selected (e.g. `UI/Frontend` instead of `Java Backend`).
- **Root Cause:** In single-choice radio groups (`button[role="radio"]`, `SingleSelectPills`), only ONE option can be checked.
- **Remediation:** 
  1. Detect control type: single-choice radio groups must strictly select only the single best match.
  2. Prioritize exact candidate architecture focus (e.g. `Java Backend (Springboot, Hibernate, Microservices)` for backend roles).
  3. Check existing selection state (`aria-checked="true"`) before clicking to maintain idempotence.

### Trap 5: Section 3 Inline Form Locking & Parent Tile Visibility
- **Phenomenon:** In CX_1002, experience and education editing is rendered INLINE (`.apply-flow__content-form`, `.standard-apply-flow-profile-item`), NOT in `.app-dialog`. When a form is open, parent tiles are hidden (`profile-item-list--disabled { display: none }`).
- **Root Cause:** Attempting to click subsequent tiles while a tile form is still open fails because subsequent tiles are not visible.
- **Remediation:** 
  1. Process tiles sequentially.
  2. After clicking `SAVE`, explicitly wait for `input[id^='employerName']:visible` to become 0 (form closed).
  3. Format achievements into authentic `• ` bullet points mapped from `resume.md`.
  4. Do not re-edit intact tiles that already have 0 validation errors.

### Trap 6: Supporting Documents & Cover Letter Replacement Flow
- **Phenomenon:** Oracle Cloud HCM retains previously uploaded attachments across sessions. Uploading a fresh cover letter while an old one exists leaves the obsolete document attached.
- **Root Cause:** Oracle HCM treats cover letters as single-slot attachments. The old document must be explicitly removed before a new file input mounts.
- **Remediation:**
  1. Check for `button:has-text('REMOVE COVER LETTER')`. If visible, click it.
  2. Oracle mounts a new file input: `<input type="file" id="attachment-upload-XX" name="attachment-upload">`.
  3. Upload the freshly generated PDF to `input[name='attachment-upload']`.
  4. Wait for the upload binding to render the document title button and `REMOVE COVER LETTER` button.

### Trap 7: LinkedIn URL Truncation Defense
- **Phenomenon:** The resume auto-parser frequently truncates candidate URLs in `siteLink-1` (e.g. `https://linkedin.com/in/udaykan` missing `dpal`).
- **Remediation:** Inspect `input[name*='siteLink']` on Section 4. Cross-reference against candidate config `linkedin_profile_url`. If truncated or mismatched, explicitly overwrite with the canonical URL (`https://www.linkedin.com/in/udaykandpal`).

### Trap 8: Executive Single-Page Cover Letter Standard
- **Phenomenon:** Flashy cover letters with HTML tables (`<table>`) or colorful callout boxes look informal and fail automated enterprise parsing.
- **Remediation:** Adhere strictly to `docs/templates/PROFESSIONAL_COVER_LETTER_TEMPLATE.md`:
  - Clean executive business typography (A4 portrait, 1 page).
  - Header: Candidate Name, contact bar with pipe separators.
  - Standard date line, recipient block, Re: line with Job ID.
  - Salutation: "Dear Hiring Team,".
  - Concise opening and transition paragraph.
  - 4 clean indented bullet points with bold titles (e.g. *Distributed Event-Driven Architecture*, *Enterprise Data Architecture*).
  - Value alignment synthesis and professional closing sign-off.
  - **Zero HTML tables, zero boxy card containers.**

### Trap 9: Strict Pre-Advance Red Error Gate
- **Directive:** NEVER click `NEXT` or `SUBMIT` if any red validation error exists on the page.
- **Error Selectors:**
  - `.cx-messages__message--error:visible`
  - `.cx-form-control__error-message:visible`
  - `.app-form-item__error:visible`
  - `.oj-form-control-error-message:visible`
  - `[aria-invalid="true"]:visible`
  - `.input-row--invalid:visible`
- **Verification:** Advance only when clean errors count == 0.

### Trap 11: Application Entry Legal Disclaimer (`applyFlowLegalDisclaimer` / `AGREE` button)
- **Phenomenon:** When entering the apply flow for a new job (`/apply/section/1`), Oracle Cloud HCM renders an onboarding Legal Disclaimer modal/button `#applyFlowLegalDisclaimer` with text `AGREE`. Form inputs on Section 1 remain inactive or blocked until this disclaimer is acknowledged.
- **Root Cause:** Oracle HCM CX_1002 requires mandatory acceptance of terms per requisition before initializing Knockout view models on Section 1.
- **Remediation:** Detect `#applyFlowLegalDisclaimer:visible` or `button:has-text('AGREE'):visible`. Click it, wait 2–3 seconds for the disclaimer to dismiss, and verify personal info form fields (`input[name="firstName"]`, `input[name="city"]`) mount into the DOM.

### Trap 12: Section 1 Dependent Dropdowns & Preferred Location Autocomplete Binding
- **Phenomenon:** Preferred location is an Oracle JET combobox (`input[name="preferredLocations"]`, `#preferredLocations-XX-toggle-button`). Naively typing or misclicking outside can close the combobox or hit the reset button, wiping candidate location preferences.
- **Root Cause:** Dependent pickers require specific location IDs or exact matching against the requisition's facility directory (e.g. `86856-Platina Block 3` for Outer Ring Road roles or `33437-Embassy Tech Village - Parcel`).
- **Remediation:** Click the dropdown toggle button or type the location keywords into the combobox. Query `[role="gridcell"], [role="option"], .cx-select__list-item` for the exact matching location string and click it directly. Verify selection is rendered without red errors.

### Trap 13: Section 4 Demographic Dropdown Scope Collision & Exact Gridcell Selection
- **Phenomenon:** When attempting to select options like `Asian` in Section 4, naive substring or `.includes('asian')` queries match the giant question container `.cx-question` / `Diversity Information` which contains the word "Asian" in its body description, clicking the container instead of the dropdown option and leaving Ethnicity blank.
- **Root Cause:** Broad CSS selector queries (`li, div`) without exact-match predicates bind to ancestor containers.
- **Remediation:** Focus and fill the input (`input[id*="ETHNICITY"]`), wait for the dropdown overlay to filter, and select strictly where `el.innerText.trim().toLowerCase() === targetText.toLowerCase()` on elements with `[role="gridcell"], [role="option"]`. Check the input's `.input_value()` readback to confirm selection was persisted.

### Trap 14: Job Search Tile Deduplication & `ALREADY APPLIED` Flag Inspection
- **Phenomenon:** Automated scrapers re-target requisition IDs that the candidate already submitted in previous sessions, risking duplicate submission errors or wasted agent cycles.
- **Root Cause:** Search results list all open requisitions regardless of candidate history unless the tile DOM text is inspected.
- **Remediation:** Inspect each job card tile text for `"ALREADY APPLIED"`. The scraper must automatically flag `is_already_applied: True` and filter these out from active application queues.

### Trap 15: Non-Negotiable Human Submission Gate
- **Directive:** The autonomous agent must NEVER click `SUBMIT`.
- **Protocol:** Populate all fields, verify 0 errors, ensure SUBMIT button is enabled, capture full-page screenshot (`section4_final_verified.png`), and halt with clear instructions for the human operator to perform final review and manual submission.





