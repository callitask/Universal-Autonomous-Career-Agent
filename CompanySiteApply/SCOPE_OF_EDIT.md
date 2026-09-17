# CompanySiteApply: Scope of Edit & 100-Day Extensibility Contract

> **Subsystem Authority:** `F:\JOB AI AGENT\CompanySiteApply`  
> **Document Purpose:** Complete engineering guide for modifying existing ATS fingers or adding new company portal handlers even 100+ days into the future, without architectural regression or codebase pollution.

---

## 1. Subsystem Philosophy: The Arm & Swappable Fingers

Enterprise career websites do not follow a single uniform standard. Each Applicant Tracking System (ATS)—Workday, Oracle Cloud HCM, Greenhouse, Lever, SmartRecruiters, iCIMS, SuccessFactors, Ashby—implements distinct DOM components, custom data-binding frameworks (React, Oracle JET, Vue), multi-step wizard navigations, and anti-bot traps.

To prevent brittle monolithic scripts, this subsystem implements an **anatomical arm with modular fingers**:
- **The Arm (`ats_arm.py` / `ats_detector.py`)**: Central dispatcher. Handles browser CDP connections, platform detection, anti-bot honeypot detection, and lifecycle orchestration.
- **The Fingers (`CompanySiteApply/fingers/`)**: Self-contained platform adapters implementing `BaseATSFinger`.
- **The Parser Doctor (`CompanySiteApply/parser_doctor/`)**: Universal post-upload review healer that repairs text line-wrap breaks and education field inversions.

---

## 2. The 100-Day Rule: How to Add a New ATS Finger

Whenever you encounter a new enterprise ATS or custom corporate portal (even months from now), follow this strict 4-step protocol:

### Step 1: Live Tab Inspection
Open the target job application page in the debugging browser (CDP port 9222). Run:
```powershell
python CompanySiteApply/cli.py inspect
```
This automatically captures:
- Live URL patterns and page title
- Form control inventory (inputs, textareas, selects, buttons)
- Hidden anti-bot honeypots (`HoneypotGuard`)
- Snapshot JSON saved to `CompanySiteApply/inspections/<platform>/`

### Step 2: Create the Finger File
Create `CompanySiteApply/fingers/<platform_name>_finger.py` subclassing `BaseATSFinger`:

```python
# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: YYYY-MM-DD HH:MM:SS +05:30
# Issue / Context: Pluggable ATS finger for <Platform Name>.
# Changes Made: Implemented <PlatformName>Finger.
# Rationale: Standardizes <Platform Name> automation.
# Preventative Notes: Never fill honeypot fields.
# ==============================================================================

from typing import Any, Callable, Dict, List, Optional, Tuple
from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.utils.dom_helpers import DOMHelpers

class NewPlatformFinger(BaseATSFinger):
    @property
    def platform_name(self) -> str:
        return "new_platform_slug"

    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        # Inspect URL and page.locator() for platform hallmarks
        if "newplatform.com" in url:
            return True, 0.9, "NewPlatform Enterprise"
        return False, 0.0, "Unknown"

    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        return DOMHelpers.extract_form_schema(page)

    def fill_step(self, page: Any, candidate_data: Dict[str, Any], prompt_user_callback=None) -> Dict[str, Any]:
        # Implement field filling using DOMHelpers.set_input_value_native()
        return {"success": True}

    def advance_step(self, page: Any) -> Tuple[bool, str]:
        # Target the Next/Submit button
        return True, "Advanced"

    def is_complete(self, page: Any) -> Tuple[bool, str]:
        # Check confirmation message or URL
        return False, "In progress"
```

### Step 3: Register the Finger in `CompanySiteApply/fingers/__init__.py`
Import the new finger and add it to `FINGER_REGISTRY`:
```python
from CompanySiteApply.fingers.new_platform_finger import NewPlatformFinger

FINGER_REGISTRY = [
    OracleCloudFinger,
    WorkdayFinger,
    GreenhouseFinger,
    NewPlatformFinger,  # <-- Added here
    GenericAdaptiveFinger,  # Always last
]
```

### Step 4: Verify via Test Harness
Run `python CompanySiteApply/cli.py inspect` to confirm your new finger claims the active tab with high confidence score ($\ge 0.8$).

---

## 3. Scope of Edit: Permitted vs. Prohibited Modifications

### Permitted Modifications (Safe to Edit):
1. **Adding New Fingers**: Create new files in `CompanySiteApply/fingers/` following `BaseATSFinger`.
2. **Updating Existing Fingers**: Modifying selectors in `oracle_cloud_finger.py`, `workday_finger.py`, etc., when an ATS releases a DOM layout update.
3. **Enhancing Parser Doctor**: Adding new compound prefixes in `line_wrap_healer.py` or new institution/degree patterns in `education_healer.py`.
4. **Capturing Inspections**: Creating new snapshot JSON files under `CompanySiteApply/inspections/`.

### Strictly Prohibited (Never Do):
1. **Never Touch `core/`**: Do NOT edit `04_job_discovery.py`, `05_apply_jobs.py`, or `continuous_career_agent.py` for company site apply tasks.
2. **Never Hardcode Candidate Data (Guardrail P1)**: Zero candidate names, emails, phone numbers, CTCs, or cities in any `.py` file. All values must resolve dynamically from candidate config or interactive CLI prompts.
3. **Never Bypass Honeypots**: Never fill elements flagged by `HoneypotGuard.is_honeypot()`.
4. **Never Run Auto-Daemon for Company Sites**: Company site apply must remain on-demand / human-supervised.
5. **Never Use Raw `open("w")` on Shared Configs**: Use atomic save protocols if updating configs.

---

## 4. Parser Doctor: Repairing ATS Resume Parsing Quirks

### Issue 1: Line-Break Sentence Mutilation (Workday & Oracle)
- **Problem**: When a PDF resume is uploaded, words at line ends (right margin or page breaks) often lack spaces or contain hard `\n` linebreaks. ATS parsers treat each line break as a distinct bullet point or broken sentence fragment.
- **Repair**: `LineWrapHealer.heal_text()` detects lines ending without terminal punctuation (`. ! ?`) where the next line starts with lowercase or continuation tokens, merging them with a single space while strictly preserving bullet lists (`•`, `-`, numbered).

### Issue 2: Swapped School & Degree Fields
- **Problem**: ATS parsers frequently place degree strings (e.g. `"Bachelor of Technology"`) into the Institution field and University names into the Degree field.
- **Repair**: `EducationHealer.diagnose_and_heal_entry()` inspects field tokens against degree patterns (`bachelor`, `master`, `btech`, etc.) and institution patterns (`university`, `college`, `institute`), swapping inverted entries and aligning against candidate ground truth.
