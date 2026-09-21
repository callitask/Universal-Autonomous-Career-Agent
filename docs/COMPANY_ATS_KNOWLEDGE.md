# Enterprise ATS Engineering Reference: Oracle Cloud HCM & Universal Company Portals

> **Document Version:** 2.0 — Multi-Step Flow, Modal Healing, Nails Integration & Field Validation  
> **Last Updated:** 2026-09-21  
> **Authority:** Operational reference for CompanySiteApply fingers and nails.

This document serves as the permanent knowledge repository, reverse-engineering guide, and auto-healing runbook for enterprise ATS platforms (specifically Oracle Cloud HCM Candidate Experience and universal multi-step company application systems).

---

## 1. Portal Architecture & Multi-Step Flow

### Canonical Flow Structure
1. **Section 0: Email & Legal Disclaimer**
   - URL: `/apply/email`
   - Elements: Legal consent checkbox, email verification input, Next/Continue action button.
2. **Section 1: Contact & Personal Info**
   - URL: `/apply/section/1`
   - Elements: Title (`cx-select`), First/Last Name, Email, Phone, Country, Address lines, City, State, Postal Code.
3. **Section 2: Application Questions**
   - URL: `/apply/section/2`
   - Elements: Experience dropdowns, Notice Period pill selectors, Yes/No radio groups (Relatives, Prior applications).
4. **Section 3: Work & Education History**
   - URL: `/apply/section/3`
   - Elements: Timeline cards (`beautiful-timeline-item`), Degree selectors, Work descriptions with bullet points (`• `).
5. **Section 4: More About You / Supporting Documents**
   - URL: `/apply/section/4`
   - Elements:
     - Supporting Documents & URLs (Resume card, Cover letter upload dropzone `#attachment-upload-4`).
     - Skills pill collection (`apply-flow-profile-item-tile`, Date Achieved comboboxes).
     - Licenses and Certificates (Title, Issue/Expiration dates, Type pills).
     - Diversity & Demographics (Gender combobox, Date of Birth).
     - Citizenship & National Identifiers (Country combobox, Status pills).
     - E-Signature (Full Name input, Confirmation checkboxes, Submit action).

---

## 2. DOM Selectors & Component Specifications

| Component | Verified Selector | Interaction Protocol |
| :--- | :--- | :--- |
| **Apply Page Filter** | `url.includes('/apply/')` | Always filter browser pages to avoid background downloader tabs. |
| **Combobox Toggle** | `[id*="toggle-button"]` | Click toggle button to render overlay grid. |
| **Combobox Option** | `[role="gridcell"]` | Find element matching text exactly and click. |
| **Selection Pill** | `.cx-select-pill-section` | Click pill container; verify selection via `.cx-select-pill-section--selected`. |
| **Profile Card/Tile** | `.apply-flow-profile-item-tile`, `.beautiful-timeline-item` | Container representing an individual entry. |
| **Edit Icon** | `.apply-flow-profile-item-tile__edit-item-icon` | Hidden until hovered. Click via JS dispatch `el.click()`. |
| **Delete Icon** | `.apply-flow-profile-item-tile__delete-icon` | Hidden until hovered. Triggers confirmation dialog. |
| **Dialog Discard** | `button` with text `Discard` | Confirms card deletion. |
| **Cover Letter Input** | `input#attachment-upload-4` | Target hidden file input directly via `set_input_files()`. |
| **Active Edit Form** | `.apply-flow-profile-item-tile--active`, `.app-dialog` | Scoped container holding open inputs, pills, and Save/Cancel buttons. |
| **Save Action** | `button.save-btn`, button text `SAVE` | Commits changes and triggers in-DOM validation. |

---

## 3. Historical Traps, Issues Faced & Battle-Tested Fixes

### Trap 1: Multiple Tabs & Downloader Tab Hijacking
- **Symptom:** Scripts using `pages[0]` query an empty page or fail completely because `downloader` tab is at index 0.
- **Root Cause:** Oracle HCM opens an invisible or pop-under downloader tab during file imports.
- **Battle-Tested Fix:**
  ```python
  def get_apply_page(browser):
      for ctx in browser.contexts:
          for pg in ctx.pages:
              if '/apply/' in pg.url:
                  return pg
      raise RuntimeError('Application page not found')
  ```

### Trap 2: Playwright Hover Visibility Timeout on Edit/Delete Icons
- **Symptom:** `playwright._impl._errors.TimeoutError: ElementHandle.click: Timeout 30000ms exceeded. Element is not visible.`
- **Root Cause:** Action buttons (`.edit-item-icon`, `.delete-icon`) are hidden via CSS opacity/display until mouseover occurs on parent card.
- **Battle-Tested Fix:**
  Dispatch click directly in the browser JavaScript runtime:
  ```python
  await page.evaluate('(el) => el.click()', edit_btn)
  ```
  Or scroll into view and trigger hover prior to clicking.

### Trap 3: Licenses & Certificates "Fields to fix: 1"
- **Symptom:** Badge displays `Fields to fix: 1`. Opening card displays red text: `The License or Certificate field is required.`
- **Root Cause:** Resume auto-parser imports the certificate name and expiration date, but fails to select whether the entry is a "Certificate" or "License".
- **Battle-Tested Fix:**
  1. Open edit form via `.apply-flow-profile-item-tile__edit-item-icon`.
  2. Inspect `.cx-select-pill-section`.
  3. Dispatch click on pill containing `Certificate`.
  4. Dispatch click on `button.save-btn` (labeled `SAVE`).
  5. Verify `Fields to fix` badge is removed.

### Trap 4: Skills Lacking Achievement Dates
- **Symptom:** Skills imported by resume parser contain only skill text, lacking `Date Achieved`.
- **Root Cause:** Parser populates skill name input but skips optional date fields.
- **Battle-Tested Fix:**
  For each skill tile:
  1. Click edit icon.
  2. If year input is empty, click toggle `[id*="month-dateAchieved"][id*="toggle"]` and pick Month from `[role="gridcell"]`.
  3. Click day toggle and select Day (e.g. `15`).
  4. Click year toggle and select Year (5+ years of experience, e.g. `2019`, `2020`, `2021`).
  5. Click `SAVE`.

### Trap 5: Duplicate Experience Cards from Auto-Import
- **Symptom:** Identical employer and title imported twice (e.g. Cognizant Senior Associate).
- **Root Cause:** Resume parser imports primary card, while portal pre-fills draft card.
- **Battle-Tested Fix:**
  Compare composite key `(company.lower(), title.lower(), dates.lower())`. If duplicate identified, click delete icon and confirm by clicking `Discard`.

### Trap 6: Citizenship Status Required Error
- **Symptom:** Form shows `The Status field is required.` under Citizenship.
- **Root Cause:** Country is set to `Indian`, but `Status` pill (`Active` / `Expired`) is unselected.
- **Battle-Tested Fix:**
  Click the `Active` pill (`.cx-select-pill-section`), then click `SAVE`.

### Trap 7: Session Inactivity Timeout
- **Symptom:** After 15 minutes of inactivity, user is redirected to `/jobs`.
- **Battle-Tested Fix:**
  Direct URL navigation directly back to active section:
  `https://iaagiz.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/bristlecone-careers/job/{job_id}/apply/section/{section_num}`.

### Trap 8: Section 3 Experience & Education Native Parser Truncation
- **Symptom:** Experience cards display blank Employer Country, blank Employer City, unselected Internal pill, and unbulleted/truncated achievements. Education card shows missing Degree ("The Degree field is required. (1 issue)").
- **Root Cause:** Oracle Cloud HCM resume parser natively discards country, city, and achievements formatting, and fails to map degrees into custom Knockout comboboxes.
- **Battle-Tested Fix:**
  1. Iterate over every single tile using JS evaluate click on `.apply-flow-profile-item-tile__edit-item-icon`.
  2. For Education: select Degree via keyboard `ArrowDown`+`Enter` on `[id^='contentItemId']`, set Country to India, and set Area of Study.
  3. For each Experience: set Country to India (using `[role='gridcell']:text-is('India')` exact match), populate City, select Internal `No` via `.cx-select-pill-section`, and populate Achievements textarea with clean, structured bullet points (`• `) from the candidate's master resume.
  4. Click `button.save-btn` / `button:has-text('Save')` and wait for the form to save cleanly.

---

## 4. Reusable Dynamic Error Detection & Auto-Healing Protocol

Before attempting any form submission, the agent must run the **Universal Error Scanner**:

```javascript
// Universal Oracle HCM In-Page Error Scanner
function scanFormErrors() {
    const errors = [];
    // 1. Check all invalid input rows
    document.querySelectorAll('.input-row--invalid, .cx-select--invalid, [aria-invalid="true"]').forEach(el => {
        errors.push({
            type: 'invalid_row',
            id: el.id,
            text: el.innerText.trim().replace(/\n/g, ' ')
        });
    });
    // 2. Check profile item tiles with fix badges
    document.querySelectorAll('.apply-flow-profile-item-tile').forEach(t => {
        if (t.innerText.includes('Fields to fix')) {
            errors.push({
                type: 'tile_error',
                id: t.id,
                text: t.innerText.trim().replace(/\n/g, ' -- ')
            });
        }
    });
    return errors;
}
```

---

## 5. Artifact & File Organization Standards

When applying to any company website:
1. **Directory Structure**:
   ```
   profiles/{profile_name}/APPLIED ON COMPANY WEBSITE/{Company_Name}/{Job_Role_Name}/
   ├── answers.json                           # Full machine-readable record of form answers
   ├── {Candidate_Name}_Resume.pdf            # Exact tailored resume submitted
   ├── cover_letter.md                        # Master Markdown source of cover letter
   └── {Candidate_Name}_Cover_Letter.pdf      # Typeset PDF submitted to portal
   ```
2. **Profile Template Standards**:
   - Master generic templates live at `profiles/default_user/cover_letter_template.md`.
   - Candidate-specific base cover letters live at `profiles/{profile_name}/cover_letter.md`.
   - Core automation scripts must strictly consume from config and profile files without hardcoding names, companies, or answers.

---

## 6. Architecture: ATS Fingers vs Company Nails

### Separation of Concerns
1. **`core/`**: Handles job portal engines (Naukri, LinkedIn, etc.).
2. **`CompanySiteApply/`**: Handles direct enterprise career site applications.

### Platform Fingers & Company Nails
- **Fingers (`CompanySiteApply/fingers/`)**: Standard platform engines (e.g. `OracleCloudFinger`, `WorkdayFinger`, `GreenhouseFinger`). These encapsulate generic platform mechanics: JET inputs, Knockout bindings, honeypot evasion, multi-step navigation, and file uploads.
- **Nails (`CompanySiteApply/nails/`)**: Company-specific variations and overrides (e.g. `JPMCNail`, `BristleconeNail`). These encapsulate company-curated questions, custom demographic surveys (e.g. India Uniformed forces), experience tier options, and unique layout traits.

---

## 7. Strategic Resume Tailoring Architecture

Tailoring for enterprise roles is strictly governed by [`STRATEGIC_RESUME_TAILORING.md`](./STRATEGIC_RESUME_TAILORING.md):
1. **Strategy Over Blind Copy-Paste**: Never blindly stuff raw JD sentences into the resume. Analyze the JD archetype and align verified candidate achievements.
2. **Dual-Identity Principle**: Balance Senior Leadership (30-40 candidate interviews, team management, credentials, full older role depth) with Modern Hands-On AI Velocity (GitHub Copilot, prompt engineering, unit test synthesis).
3. **Zero Truncation**: Never collapse older roles (Navyug, Adobe, IBM) or internships into single vague bullets.
4. **Strict 2-Page Format**: Compile to exact 2-page A4 PDF (`6mm 10mm` margins, `8.3pt` font, `1.26` line height) without page overflow.

---

## 8. Mandatory Section 1 Resume Upload & Page-by-Page Audit Protocol

### A. Non-Negotiable Flow Gate
When applying on company ATS portals (such as Oracle Cloud HCM `CX_1001`), the agent must **never** assume pre-filled data or skip Section 1:
1. **Resume Upload First**: Immediately upload the tailored 2-page resume PDF on Section 1 (`input.apply-flow-profile-import-awli__file-upload`).
2. **Await Parse Banner**: Wait for `.apply-flow-profile-import-awli__success-message:has-text("Profile successfully imported.")`.
3. **Sequential Page Verification**:
   - **Section 1 (Personal)**: Verify Title (`Mr.`), Name, Phone, Address, Official City (`Bengaluru, Karnataka`), PIN (`560100`), LinkedIn URL.
   - **Section 2 (Questions)**: Disqualification questions + multiselect comboboxes via synthetic mouse events.
   - **Section 3 (Timeline)**: Audit and heal all 10 tiles. Heal missing Degree (`Bachelor's Degree`, `July 2015`, `India`, `Computer Science & Engineering`). For all 9 experience tiles, ensure Country (`India`), City (`Bangalore`/`Noida`/`Delhi`), Non-Internal (`No`), and bulleted achievements (`• `).
   - **Section 4 (Review & Supporting Docs)**: Verify Resume and Cover Letter have green checkmarks (`REMOVE` button visible). Verify Demographics and E-Signature.
4. **Mandatory Review Gate**: STOP on Section 4. Save `submission_review_page.png` and `answers.json`. Do NOT click `SUBMIT`.



