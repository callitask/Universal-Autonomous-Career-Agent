# Agent Handover: JPMC Oracle Cloud HCM Autonomous Job Search & Application (Site: CX_1002)

## 1. Goal and Current Context
- **Candidate Profile:** Udaysagar Kandpal (`profiles/udaysagar_kandpal/candidate_config.json`, 10+ yrs Lead Java Architect / Backend / Microservices / AWS / Kafka).
- **Target Portal:** JPMorgan Chase Career Experience (`https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/`).
- **Live Active Requisition:** **Lead Software Engineer – Java (Job ID: `210774158`)**
  - **Business Unit:** Commercial & Investment Bank (CIB)
  - **Location:** Bengaluru, Platina Block-3, Outer Ring Road (560103)
  - **Match Score:** >95% (Exact alignment with Java 17, Spring Boot, IPC, Kafka, Distributed Systems, AI-Assisted Engineering).
- **Portal Status:** Currently navigated to **Section 4 Review** (`https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/210774158/apply/section/4`).
- **CRITICAL HUMAN GATE CONSTRAINT:** **NEVER CLICK SUBMIT.** All sections 1 to 4 are 100% completed with zero validation errors, new tailored cover letter uploaded, canonical LinkedIn link verified, Demographics set (`Asian`, `Male`, `No`), E-Signature filled (`Udaysagar Kandpal`), and the `SUBMIT` button enabled and **UNCLICKED**, ready for the user to manually review and submit in the CDP browser (`http://127.0.0.1:9222`).

---

## 2. Completed Steps & Empirical Verifications

### Step 1: Autonomous Search & Role Discovery (COMPLETED)
- Scraped open roles in Bengaluru using `CompanySiteApply/CompanyScraper/companies/jpmorgan/jpmorgan_scraper.py`.
- Filtered out requisition `210794073` (*Senior Lead Software Engineer - Java/Python*) which displayed `ALREADY APPLIED` on the portal card (submitted previously).
- Scored top unapplied roles against candidate context:
  - **Job ID `210774158` (Lead Software Engineer – Java):** Match score 98/100.
  - BU: Commercial & Investment Bank (CIB).
  - Technologies: Java 17+, Spring Boot, Low-Latency IPC, memory-mapped files, ring buffers, gRPC, Protobuf, PostgreSQL, CockroachDB, Kafka, responsible AI workflows.

### Step 2: Tailored Artifacts Generation (COMPLETED)
- Created dedicated application directory:
  `profiles/udaysagar_kandpal/APPLIED ON COMPANY WEBSITE/JPMorgan Chase/Lead_Software_Engineer_Java_210774158/`
- Generated artifacts adhering strictly to `docs/templates/PROFESSIONAL_COVER_LETTER_TEMPLATE.md`:
  - `Job_Description.md` & `job_description.json`
  - `Cover_Letter.txt`
  - `Cover_Letter.html` (Executive business typography, A4 1-page, NO tables, NO boxy cards)
  - `Udaysagar_Kandpal_Cover_Letter.pdf` (Rendered via Playwright Chromium PDF)
  - `Udaysagar_Kandpal_Resume.pdf` (Copied from validated master profile)

### Step 3: Application Flow Execution (Sections 1 to 4) (COMPLETED & VERIFIED)
- **Onboarding:** Handled Legal Disclaimer modal (`#applyFlowLegalDisclaimer` / `AGREE` button).
- **Section 1 (Personal Details):**
  - Title: Selected `Mr.`.
  - Candidate: `Udaysagar Kandpal`, `ukandpal2@gmail.com`, `+91 9654258060`.
  - Address: `103, SVR Pavithra, 12th Cross Road`, `Bengaluru`, `Karnataka`, `560100`, `India`.
  - Preferred Location: Handled interactive combobox, selected `86856-Platina Block 3` (matching the CIB office facility).
  - Pre-Advance audit: 0 errors. Clicked NEXT.
- **Section 2 (Application Questions):**
  - Are you at least 18 years of age? -> `Yes`
  - Legally authorized to work in this country? -> `Yes`
  - Require sponsorship for employment visa? -> `No`
  - Hold an Indian Passport? -> `Yes`
  - Citizenship or passport of country other than India? -> `No`
  - High School diploma (10+2), HSC or GED? -> `Yes`
  - Pre-Advance audit: 0 errors. Clicked NEXT.
- **Section 3 (Experience & Education):**
  - Confirmed all 10 experience and education cards intact with authentic bullet points (`• `).
  - Zero open forms, zero errors. Clicked NEXT.
- **Section 4 (More About You & Documents):**
  - **Cover Letter Replacement:** Removed obsolete cover letter (`REMOVE COVER LETTER`), confirmed dialog, and uploaded fresh tailored `Udaysagar_Kandpal_Cover_Letter.pdf`. Verified active document with green checkmark.
  - **Resume:** Confirmed `Udaysagar_Kandpal_Resume.pdf` with green checkmark.
  - **LinkedIn Link:** Verified canonical URL `https://www.linkedin.com/in/udaykandpal` (no truncation).
  - **Diversity / Demographics:** Set Ethnicity to `Asian`, Gender to `Male`, Military Status to `No` using exact gridcell selection.
  - **E-Signature:** Populated `Udaysagar Kandpal`.
  - **Final Audit:** Total validation errors = 0.
  - **Human Gate:** `SUBMIT` button visible, enabled, and **UNCLICKED**.
  - **Verification Screenshot:** Saved to artifacts directory: `section4_final_verified_210774158.png`.

---

## 3. Engineering Traps Solved & Documented in `docs/ORACLE_HCM_ATS_DEEP_DIVE.md`
1. **Trap 11: Application Entry Legal Disclaimer:** Handled `#applyFlowLegalDisclaimer` / `AGREE` button to unblock Section 1 initialization.
2. **Trap 12: Section 1 Dependent Dropdowns & Preferred Location Autocomplete Binding:** Interactively query combobox items for facility directory options (e.g. `86856-Platina Block 3`).
3. **Trap 13: Section 4 Demographic Dropdown Scope Collision:** Avoided broad `.includes('asian')` queries that accidentally hit the parent question block. Used exact text matching `=== 'Asian'` on `[role="gridcell"], [role="option"]`.
4. **Trap 14: Job Search Tile Deduplication & `ALREADY APPLIED` Flag Inspection:** Automatically detected and skipped requisition tiles marked with `ALREADY APPLIED`.
6. **Trap 26: Section 3 Education Modal School Field Autocomplete:** Handled asynchronous JET combobox dropdown selection for institution (`Jaypee Institute of Information Technology (JIIT)`) to trip Knockout observable and activate the SAVE button.
7. **Trap 27: Fresh Cover Letter Header Standard:** Standardized from `RE:` to `Subject: Application for [Job Title] (Requisition ID: [Job ID])`.
8. **Trap 28: Hierarchical Anatomical Component Architecture:** Decoupled execution into `PageBone` -> `SectionSurface` -> `FormMatrix` -> `FieldCell` so micro-healing on one section (Education) never resets or touches sibling sections (9 reverse-chronological experience tiles).

---

## 4. Operational Playbook for Future Chats & New Companies

### Q1: In layman's terms, what is the workflow when starting the agent in a new chat for new jobs at JPMC?
1. **Search & Score:** Scrapes available jobs on the active JPMC portal, skips any tile marked `ALREADY APPLIED`, and scores job descriptions against candidate context (>90% match).
2. **Artifact Generation:** Generates tailored, factual cover letter (`Subject: Application for ...`) and compiles PDF.
3. **Anatomical Section-Wise Filling:**
   - **Page 1 (Profile Bone):** Personal info, verified Bangalore address, Preferred Location combobox pill.
   - **Page 2 (Questionnaire Bone):** Multi-pass cascading question solver (Years of experience $\ge 5$, AWS Expert, Java Backend, Java/Python skill pills).
   - **Page 3 (Timeline Bone):**
     - Surgically audits Education modal: selects Degree, School autocomplete, dates, country, major, and clicks SAVE.
     - Surgically audits Experience tiles: ensures Country, City, `Internal: No`, bulleted achievements (`• `), and enforces reverse-chronological sorting.
   - **Page 4 (Review Bone):** Attaches fresh cover letter PDF, verifies LinkedIn URL, fills demographics/military flexfields, types full E-Signature.
4. **Strict Human Gate:** Halts on Section 4 with SUBMIT active and **UNCLICKED**.

### Q2: What should the user type in a new chat to run this with complete knowledge?
> *"Apply on company site for JPMC Career Portal using active profile [Profile Name]. Follow the Hierarchical Anatomical Component Architecture in CompanySiteApply/anatomy and all traps documented in docs/ORACLE_HCM_ATS_DEEP_DIVE.md (Traps 11 through 28). Ensure zero errors, reverse-chronological experience order, and halt at Section 4 before clicking SUBMIT."*

### Q3: When developing for a new company site, how do we inform the agent of past traps?
1. **Direct the agent to `docs/ORACLE_HCM_ATS_DEEP_DIVE.md`:** This file contains 28 battle-tested traps and blueprints.
2. **Require Anatomical Modularity:** Instruct the agent to implement a `CompanySiteApply/nails/<company_name>_nail.py` and attach to the appropriate ATS finger (`OracleCloudFinger`, `WorkdayFinger`, `GreenhouseFinger`).
3. **Enforce Isolated Micro-Healing:** Mandate that if an audit fails during execution, the agent must heal only the failing `SectionSurface`/`FormMatrix` using `SurgicalAuditor`, never re-running the entire application.

