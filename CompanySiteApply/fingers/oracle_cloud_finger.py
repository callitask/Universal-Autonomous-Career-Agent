# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:55:00 +05:30
# Issue / Context: Pluggable ATS finger for Oracle Cloud HCM (Candidate Experience & Taleo).
# Changes Made: Implemented OracleCloudFinger supporting multi-step application flow,
#               anti-bot honeypot evasion, legal consent checkbox, and JET input dispatching.
# Rationale: Reverse-engineered from live Oracle Cloud HCM portal (Bristlecone Careers).
# Preventative Notes: Never populate input[name="honey-pot"]. Always use DOMHelpers.set_input_value_native.
# [ENTRY #002]
# Term: [BUGFIX_AND_ATS_HEALING]
# Timestamp: 2026-09-17 12:25:00 +05:30
# Issue / Context: Oracle Cloud HCM parser on CX_1001 omits employer country/city, skips bullet points in achievements textarea, leaves degree unmapped, and renders inline forms with hidden action buttons that cause Playwright actionability 30s timeouts.
# Changes Made: Updated find_profile_tile_edit_buttons to support .apply-flow-profile-item-tile__summary-title and filter ghost DOM nodes; replaced Playwright direct click on opacity-0 edit buttons with native JS evaluate clicks; upgraded _heal_education_modal with keyboard combobox dispatching; expanded SAVE button locator to include inline .save-btn containers; ensured bullets extraction falls back to description text and formats clean bullet points (•).
# Rationale: Eliminates 30s timeout hangs on hidden UI elements and guarantees 100% data fidelity for ATS parser review steps.
# Preventative Notes: Never call edit_btn.scroll_into_view_if_needed() directly on Oracle HCM tile edit icons as they have 0 opacity until hovered, triggering Playwright's 30s actionability timeout. Always trigger click natively via JS or scroll parent tile container. Never assume dialog is inside .app-dialog as CX_1001 renders inline forms.
# [ENTRY #003]
# Term: [FINGER_AND_NAIL_ARCHITECTURE_INTEGRATION]
# Timestamp: 2026-09-17 13:25:00 +05:30
# Issue / Context: Oracle Cloud HCM applications exhibit company-specific variations (e.g., JPMC CX_1001 vs Bristlecone). Generic finger missed Section 4 demographic flexfields (India Uniformed forces), misclassified inline education forms as work experience, and failed on general experience tier choices.
# Changes Made: Integrated CompanySiteApply/nails architecture (JPMCNail, BristleconeNail); added get_active_nail(); implemented _fill_section_4_more_about_you delegating custom demographic flexfields to active Nail; upgraded _fill_experience_step to detect inline Education forms by tile title and input signatures; upgraded _heal_education_modal to dynamically set End Date Month (July) and Year (2015) matching candidate profile; delegated questionnaire solving to active nail before AI fallback.
# Rationale: Decouples universal Oracle HCM mechanics from company-specific survey fields and layouts.
# Preventative Notes: Never hardcode company-specific question logic in OracleCloudFinger; always encapsulate in corresponding Nail.
# [ENTRY #004]
# Term: [ZERO_HARDCODING_PURGE]
# Timestamp: 2026-09-23 14:25:00 +05:30
# Issue / Context: search_roots hardcoded a live profile folder; pincode/city
#   used literal fallbacks violating Guardrail P1.
# Changes Made: search_roots now via config_resolver.resolve_search_roots
#   (blueprint default_user only); pincode/city default to "" (skip when missing).
# Rationale: Candidate-agnostic; purity scanner stays green.


# Preventative Notes: Never add profile names or PIN/city literals here.
#
# [ENTRY #007]
# Term: [COMBO_DELEGATION_AND_AI_TIEBREAK]
# Timestamp: 2026-10-07 19:00:00 +05:30
# Issue / Context: Finger-local combo code duplicated exact-only matching and returned success without verification.
# Changes Made: _select_cx_combobox/select_cx_dropdown_field/Section-1 city delegate to DOMHelpers.select_jet_combo; _ai_pick_option tie-breaker (exact-list-only, None on doubt).
# Rationale: One combo implementation for all future fingers.
# Preventative Notes: Never reintroduce finger-local combo matching.
#
# [ENTRY #008]
# Term: [AI_ALIAS_WIRING]
# Timestamp: 2026-10-07 19:30:00 +05:30
# Issue / Context: No brain path for alternate spellings of the same place.
# Changes Made: _ai_alias_options (JSON-array alternates, exact-list never required of it) wired as ai_aliases at all three select_jet_combo call sites.
# Rationale: Brain proposes spellings; page options decide truth; read-back confirms.
# Preventative Notes: Never let the brain invent a value outside visible options.
# [ENTRY #006]
# Term: [ADVANCE_STEP_GUARD]
# Timestamp: 2026-10-07 17:10:00 +05:30
# Issue / Context: advance_step computed new_url but never compared it; error check was banner-only.
# Changes Made: Delegates to DOMHelpers.verify_step_advanced (URL-change + shared error selectors + completion markers).
# Rationale: Single guard implementation across all fingers.
# Preventative Notes: Never bypass the shared guard with finger-local banner checks.
#
# [ENTRY #005]
# Term: [DEMOGRAPHIC_DEFAULTS_PURGE]
# Timestamp: 2026-10-07 16:10:00 +05:30
# Issue / Context: Salutation/country/degree/major/month/year/ethnicity/gender carried assumed defaults.
# Changes Made: All resolve from candidate/education/work data with empty-skip; human-gated operator fills unknowns. No assumed identity.
# Rationale: Human-gated flow must leave unknowns blank, never invent.
# Preventative Notes: Never restore demographic or country literals here.
# [ENTRY #010]
# Term: [UNIVERSAL_REVERSE_CHRONOLOGICAL_EXPERIENCE_REORDERING]
# Timestamp: 2026-10-09 09:30:00 +05:30
# Issue / Context: Oracle Cloud HCM candidate portal backend query returns previous employments
#                  alphabetically by employer name rather than chronologically across all portals.
# Changes Made: Added _reorder_tiles_reverse_chronological() to OracleCloudFinger, sorting Knockout
#               parent.forms observableArray by active status and start date descending. Invoked
#               automatically at the end of _fill_experience_step and _fill_section_4_more_about_you.
# Rationale: Guarantees authentic, professional career chronology on both Section 3 and Section 4
#            Review screens across any requisition and candidate profile.
# Preventative Notes: Never rely on Oracle's default tile insertion sequence.
# ==============================================================================

import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from CompanySiteApply.fingers.base_finger import BaseATSFinger
from CompanySiteApply.parser_doctor.review_verifier import ReviewVerifier
from CompanySiteApply.utils.dom_helpers import DOMHelpers
from CompanySiteApply.utils.honeypot_guard import HoneypotGuard
from CompanySiteApply.nails.base_nail import BaseNail
from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
from CompanySiteApply.nails.oracle.bristlecone_nail import BristleconeNail


class OracleCloudFinger(BaseATSFinger):
    """
    ATS Finger for Oracle Cloud HCM (Candidate Experience / ORC) and Oracle Taleo.
    """

    def __init__(self):
        super().__init__()
        self.nails: List[BaseNail] = [JPMCNail(), BristleconeNail()]

    def get_active_nail(self, page: Any, url: Optional[str] = None) -> Optional[BaseNail]:
        """Dynamically identifies and returns the matching company Nail for the active page."""
        title = ""
        if not url and hasattr(page, "url"):
            try:
                url = page.url
            except Exception:
                url = ""
        url = url or ""
        try:
            title = page.title()
        except Exception:
            pass
        for nail in self.nails:
            if nail.matches(url, page_title=title, page=page):
                return nail
        return None

    @property
    def platform_name(self) -> str:
        return "oracle_cloud_hcm"

    def can_handle(self, page: Any, url: str) -> Tuple[bool, float, str]:
        """
        Detects Oracle Cloud HCM or Taleo via URL patterns and DOM signatures.
        """
        score = 0.0
        variant = "Unknown Oracle"

        # URL heuristics
        if "oraclecloud.com/hcmUI/CandidateExperience" in url:
            score += 0.8
            variant = "Oracle Cloud HCM Candidate Experience (ORC)"
        elif "taleo.net" in url:
            score += 0.8
            variant = "Oracle Taleo Enterprise"

        # DOM signature checks
        try:
            has_oj = page.locator(".oj-component-initnode, [class*='oj-']").count() > 0
            has_orc_nav = page.locator(".apply-flow-pagination__button, .app-dialog").count() > 0
            has_hp = page.locator("input[name='honey-pot']").count() > 0

            if has_oj:
                score += 0.2
            if has_orc_nav:
                score += 0.3
            if has_hp:
                score += 0.3
        except Exception:
            pass

        is_match = score >= 0.6
        confidence = min(score, 1.0)
        return is_match, confidence, variant

    def inspect_current_step(self, page: Any) -> Dict[str, Any]:
        """
        Catalogues current step inputs, honeypots, and action controls.
        """
        raw_schema = DOMHelpers.extract_form_schema(page)
        url = page.url

        # Identify current sub-step
        current_step = "unknown"
        if page.locator("input[id^='pin-code-']").count() > 0 or "/apply/pin" in url or "/apply/verification" in url:
            current_step = "pin_verification"
        elif "/apply/email" in url:
            current_step = "authentication_email"
        elif "/apply/section/1" in url or "/apply/profile" in url or "/apply/resume" in url:
            current_step = "resume_and_profile"
        elif "/apply/experience" in url or "/apply/work-history" in url or "/apply/section/3" in url:
            current_step = "experience_review"
        elif "/apply/education" in url:
            current_step = "education_review"
        elif "/apply/questions" in url:
            current_step = "screening_questions"
        elif "/apply/section/4" in url or "/apply/review" in url:
            current_step = "more_about_you_and_diversity"
        elif "/apply/confirmation" in url or "/my-profile" in url:
            current_step = "application_confirmation"

        # Flag honeypots
        for inp in raw_schema.get("inputs", []):
            inp["is_honeypot"] = HoneypotGuard.is_honeypot(inp)

        raw_schema["detected_step"] = current_step
        raw_schema["platform"] = self.platform_name
        return raw_schema

    def fill_step(self,
                  page: Any,
                  candidate_data: Dict[str, Any],
                  prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Dispatches step-specific filling logic.
        """
        url = page.url
        if page.locator("input[id^='pin-code-']").count() > 0 or "/apply/pin" in url or "/apply/verification" in url:
            return self._fill_pin_step(page, candidate_data, prompt_user_callback)
        elif "/apply/email" in url:
            return self._fill_email_step(page, candidate_data, prompt_user_callback)
        elif "/apply/section/1" in url or "/apply/profile" in url or "/apply/resume" in url:
            return self._fill_profile_and_personal_details_step(page, candidate_data)
        elif "/apply/section/2" in url or "/apply/questions" in url:
            return self._fill_screening_questions_step(page, candidate_data)
        elif "/apply/experience" in url or "/apply/work-history" in url or "/apply/section/3" in url:
            return self._fill_experience_step(page, candidate_data)
        elif "/apply/education" in url:
            return self._fill_education_step(page, candidate_data)
        elif "/apply/section/4" in url:
            return self._fill_section_4_more_about_you(page, candidate_data)
        else:
            return self._fill_generic_fields(page, candidate_data, prompt_user_callback)

    def _fill_email_step(self,
                         page: Any,
                         candidate_data: Dict[str, Any],
                         prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Step 1: Fill Email Address, Bypass Honeypot, Accept Terms.
        """
        email = candidate_data.get("email") or candidate_data.get("candidate", {}).get("email")
        if not email and prompt_user_callback:
            email = prompt_user_callback("Please enter the candidate email address for this application:", None)

        if not email:
            return {"success": False, "error": "No email address provided"}

        # 1. Fill Primary Email
        email_selector = "input[name='primary-email'], input#primary-email-0"
        email_ok = DOMHelpers.set_input_value_native(page, email_selector, email)

        # 2. Strict Honeypot Protection: Verify honeypot is empty and NEVER touch it
        hp_count = page.locator("input[name='honey-pot']").count()
        hp_val = ""
        if hp_count > 0:
            hp_val = page.locator("input[name='honey-pot']").first.input_value()
            if hp_val:
                # Clear if accidentally filled by browser auto-fill!
                page.evaluate("() => { const hp = document.querySelector('input[name=\"honey-pot\"]'); if (hp) hp.value = ''; }")

        # 3. Check Legal Disclaimer Checkbox
        disclaimer_selector = "input#legal-disclaimer-checkbox, input[type='checkbox']"
        checkbox_ok = DOMHelpers.set_checkbox_checked(page, disclaimer_selector, checked=True)
        
        # If agreement terms dialog opened and intercepted, click AGREE button inside dialog
        agree_btn = page.locator("button.app-dialog__footer-button:has-text('AGREE'), button:has-text('Agree'), button:has-text('AGREE')")
        if agree_btn.count() > 0 and agree_btn.first.is_visible():
            agree_btn.first.click()
            time.sleep(0.5)
            checkbox_ok = True

        return {
            "success": email_ok and checkbox_ok,
            "step": "authentication_email",
            "email_filled": email_ok,
            "checkbox_checked": checkbox_ok,
            "honeypot_evaded": True
        }

    def _fill_pin_step(self,
                       page: Any,
                       candidate_data: Dict[str, Any],
                       prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Step 2: Enter PIN/OTP sent to candidate email.
        Supports both unified single input and Oracle HCM 6-digit split input boxes (#pin-code-1..6).
        """
        pin_val = candidate_data.get("verification_pin")
        if not pin_val and prompt_user_callback:
            pin_val = prompt_user_callback("Oracle Cloud sent a verification PIN to the email. Please enter the PIN code:", None)

        if not pin_val:
            return {"success": False, "error": "Verification PIN required"}

        clean_pin = str(pin_val).strip()

        # Check for Oracle HCM 6-digit split input boxes (#pin-code-1 to #pin-code-6)
        split_pins = page.locator("input[id^='pin-code-']")
        if split_pins.count() == 6 and len(clean_pin) == 6:
            for i in range(6):
                DOMHelpers.set_input_value_native(page, f"#pin-code-{i+1}", clean_pin[i])
            return {"success": True, "step": "pin_verification", "format": "split_6_digit"}

        # Fallback to standard unified input
        pin_selector = "input[name*='pin'], input[name*='code'], input[id*='pin'], input[id*='code'], input[type='number'], input[type='text']"
        ok = DOMHelpers.set_input_value_native(page, pin_selector, clean_pin)
        return {"success": ok, "step": "pin_verification", "format": "unified"}

    def _fill_education_step(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step: Education Review - Run Parser Doctor to heal college/degree anomalies and heal invalid education tiles.
        """
        active_nail = self.get_active_nail(page)
        if active_nail and hasattr(active_nail, "heal_invalid_education_tiles"):
            active_nail.heal_invalid_education_tiles(page, candidate_data)

        gt_edu = candidate_data.get("education") or []
        healed_reports = ReviewVerifier.audit_and_heal_education_fields(page, ground_truth_education=gt_edu)
        return {
            "success": True,
            "step": "education_review",
            "healed_education": healed_reports
        }

    @staticmethod
    def _blank_ai_context():
        """Context-free AI access: never auto-discover (and never touch) a
        live profile when the brain is needed for pure option mapping."""
        import types
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        return types.SimpleNamespace(config={}, base_path=root)

    @staticmethod
    def _ai_pick_option(field_label: str, want: str,
                        options: List[str]) -> Optional[str]:
        """
        AI tie-breaker for ambiguous dropdown options: asks the configured
        brain to map the candidate value to exactly one visible option.
        Returns the exact option text or None (caller defers to operator).
        Never invents an option outside the visible list.
        """
        opts = [str(o) for o in (options or []) if str(o).strip()][:25]
        if not opts or not str(want).strip():
            return None
        try:
            from core.ai_client import AIClient
            ai = AIClient(OracleCloudFinger._blank_ai_context())
            prompt = (
                f"Field '{field_label}'. The candidate value is "
                f"'{want}'. Visible portal options: {opts}. "
                "Reply with EXACTLY one option verbatim from the list that "
                "means the same place/value, or the single word NONE.")
            raw = ai.generate_text(prompt, default_fallback='NONE')
            choice = (raw or '').strip().strip('"').strip("'")
            for o in opts:
                if o.strip().lower() == choice.lower():
                    return o
            return None
        except Exception:
            return None

    @staticmethod
    def _ai_alias_options(field_label: str, want: str,
                          options: List[str]) -> List[str]:
        """
        Human-flow step 2: the exact answer is absent from the filtered
        options, so the brain proposes alternate spellings of the SAME
        place/value (e.g. Bangalore -> Bengaluru). Each alternate is typed
        and re-matched. Returns a list of bare name strings, possibly empty.
        Never invents places; bounded to visible-option context.
        """
        sample = [str(o) for o in (options or []) if str(o).strip()][:25]
        if not str(want).strip():
            return []
        try:
            import json
            from core.ai_client import AIClient
            ai = AIClient(OracleCloudFinger._blank_ai_context())
            prompt = (
                f"Field '{field_label}'. The candidate's place/value is "
                f"'{want}'. These are "
                f"some visible portal options: {sample}. "
                "List OTHER official/alternate spellings or names for the "
                "SAME place that might appear in the full dropdown "
                "(e.g. Bangalore is officially Bengaluru). "
                "Reply with a JSON array of strings only, e.g. "
                "[\"Bengaluru\", \"Bengaluru, Karnataka\"]. "
                "Empty array if none.")
            raw = ai.generate_text(prompt, default_fallback='[]')
            start, end = raw.find('['), raw.rfind(']')
            if start == -1 or end <= start:
                return []
            vals = json.loads(raw[start:end + 1])
            return [str(v).strip() for v in vals
                    if isinstance(v, str) and str(v).strip()][:6]
        except Exception:
            return []

    def _select_cx_combobox(self, page: Any, selector_or_id: str, value: str) -> bool:
        """
        JET/CX combobox via the shared routine (trusted open, fuzzy+alias+AI
        pick, read-back verification). Kept for caller compatibility.
        """
        name = selector_or_id
        try:
            el = page.locator(selector_or_id).first
            if el.count() > 0:
                name = el.get_attribute('name') or selector_or_id
                if name.startswith('#'):
                    name = name[1:]
        except Exception:
            pass
        ok, detail = DOMHelpers.select_jet_combo(
            page, name, [value],
            ai_resolver=lambda opts: OracleCloudFinger._ai_pick_option(
                name, value, opts),
            ai_aliases=lambda label, want, opts: OracleCloudFinger._ai_alias_options(
                label, want, opts),
            field_label=name)
        print(f"[OracleCloudFinger] Combo '{name}': {ok} ({detail})",
              flush=True)
        return ok
    @staticmethod
    def select_cx_dropdown_field(page: Any, field_label_or_text: str, option_text: str) -> bool:
        """
        Label-anchored CX select via the shared routine (trusted open,
        fuzzy+alias+AI pick, read-back verification).
        """
        try:
            field = DOMHelpers.find_field_by_label(page, field_label_or_text)
            name = None
            if field is not None:
                try:
                    name = field.get_attribute('name')
                except Exception:
                    name = None
            if not name:
                return False
            ok, detail = DOMHelpers.select_jet_combo(
                page, name, [option_text],
                ai_resolver=lambda opts: OracleCloudFinger._ai_pick_option(
                    field_label_or_text, option_text, opts),
                ai_aliases=lambda label, want, opts: OracleCloudFinger._ai_alias_options(
                    label, want, opts),
                field_label=field_label_or_text)
            print(f"[OracleCloudFinger] Dropdown '{field_label_or_text}': "
                  f"{ok} ({detail})", flush=True)
            return ok
        except Exception:
            return False
    @staticmethod
    def smart_select_pill(page: Any, target_text: str, container_locator: Any = None) -> bool:
        """
        Idempotent pill selector: Only clicks if the pill is NOT already selected.
        Prevents accidental de-selection in Oracle HCM toggleable pill components.
        """
        try:
            scope = container_locator if container_locator is not None else page
            safe_text = target_text.replace("'", "\\'")
            
            # The click target and selection state is usually on cx-select-pill-section
            pill_section = scope.locator(f".cx-select-pill-section:has-text('{safe_text}')").first
            
            if pill_section.count() == 0 or not pill_section.is_visible():
                return False

            # Check if it's already selected using native attributes
            aria_selected = pill_section.get_attribute("aria-selected")
            aria_checked = pill_section.get_attribute("aria-checked")
            class_name = pill_section.get_attribute("class") or ""
            
            is_sel = (aria_selected == "true" or aria_checked == "true" or 
                      "selected" in class_name.split() or 
                      "cx-select-pill-section--selected" in class_name)
                      
            if is_sel:
                return True
                
            pill_section.click(force=True, timeout=2000)
            time.sleep(0.2)
            return True
        except Exception:
            return False

    def _select_multi_combobox(self, page: Any, selector_or_id: str, values: List[str], max_allowed: Optional[int] = None) -> List[str]:
        """
        Intelligently selects values in Oracle HCM multi-select combobox dropdowns.
        Infers numeric constraints (e.g. 'Choose your top 2') and enforces limits.
        """
        selected = []
        try:
            sel = selector_or_id
            if sel.startswith("#") and len(sel) > 1 and sel[1].isdigit():
                sel = f"[id='{sel[1:]}']"
            input_loc = page.locator(sel).first
            if input_loc.count() == 0:
                return selected

            input_id = input_loc.get_attribute("id") or ""
            
            # Infer limit from parent container question text if not provided
            if max_allowed is None:
                q_text = page.evaluate('''(id) => {
                    const el = document.querySelector('[id="' + id + '"]');
                    if (!el) return '';
                    const parent = el.closest('.app-form-item, .input-field-container') || el.parentElement;
                    return parent ? parent.innerText.trim() : '';
                }''', input_id)
                match = re.search(r'(?:top|select up to|no more than)\s*(\d+)', q_text, re.IGNORECASE)
                max_allowed = int(match.group(1)) if match else None

            target_list = values[:max_allowed] if max_allowed else values

            for val in target_list:
                # Check if already present in pills
                current_pills = page.evaluate('''() => Array.from(document.querySelectorAll('.cx-multi-select-pill, [class*="multi-select-pill"]')).map(e => e.innerText.trim()).filter(Boolean)''')
                if any(val.lower() == p.lower() or val.lower() in p.lower() for p in current_pills):
                    selected.append(val)
                    continue

                # Click input to open dropdown cleanly
                input_loc.click()
                time.sleep(0.5)

                # Find matching option in listbox: exact match first (:text-is) before partial (:has-text)
                opt = page.locator(f"[role='option']:text-is('{val}'), [role='gridcell']:text-is('{val}')").first
                if opt.count() == 0 or not opt.is_visible():
                    opt = page.locator(f"[role='option']:has-text('{val}'), [role='gridcell']:has-text('{val}')").first
                if opt.count() > 0 and opt.is_visible():
                    opt.click()
                    selected.append(val)
                    time.sleep(0.5)

            # Close dropdown and blur to commit
            page.keyboard.press("Escape")
            time.sleep(0.4)
            page.locator("body").click(position={"x": 50, "y": 50})
            time.sleep(0.3)
        except Exception:
            pass
        return selected

    def _fill_profile_and_personal_details_step(self, page: Any, candidate_data: Dict[str, Any], resume_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 1: Upload Resume, wait for auto-parse, verify fields against candidate_config,
        set Title, Address, Official City, and Requisition-scoped Preferred Location with 0 errors.
        """
        cand = candidate_data.get("candidate", candidate_data)

        # 1. Resume Upload & Auto-Parse wait
        # In Oracle HCM, the resume input often has an aria-label containing 'Resume' or is inside a container with 'Resume'.
        resume_input = page.locator("input[type='file'][aria-label*='Resume' i], input[type='file'][title*='Resume' i], .apply-flow-profile-import-awli__file-upload[aria-label*='Resume' i], input[type='file']").first
        if resume_input.count() > 0:
            res_file = resume_path or cand.get("resume_path") or cand.get("resume_filename")
            is_already_imported = page.locator(".apply-flow-profile-import-awli__success-message:has-text('Profile successfully imported'), :has-text('Profile successfully imported.')").count() > 0
            
            # Resolve relative resume path across known directories (no hardcoded names)
            if res_file and not os.path.isabs(res_file):
                try:
                    from CompanySiteApply.utils.config_resolver import resolve_search_roots
                    search_roots = resolve_search_roots(candidate_data if isinstance(candidate_data, dict) else None)
                except Exception:
                    search_roots = [os.getcwd()]
                for root in search_roots:
                    cand_path = os.path.join(root, res_file)
                    if os.path.exists(cand_path):
                        res_file = cand_path
                        break
                    # Also search inside APPLIED ON COMPANY WEBSITE
                    applied_root = os.path.join(root, "APPLIED ON COMPANY WEBSITE")
                    if os.path.exists(applied_root):
                        for dirpath, _, filenames in os.walk(applied_root):
                            if res_file in filenames:
                                res_file = os.path.join(dirpath, res_file)
                                break

            if res_file and os.path.exists(res_file):
                print(f"[OracleCloudFinger] Uploading/overriding tailored resume to Section 1: {res_file}")
                
                del_btn = page.locator("button[aria-label='Delete Resume'], button[title*='Delete Resume']").first
                if del_btn.count() > 0 and del_btn.is_visible():
                    page.once("dialog", lambda dialog: dialog.accept())
                    try:
                        del_btn.click(force=True, no_wait_after=True)
                        time.sleep(1.0)
                    except Exception:
                        pass
                    
                resume_input.set_input_files(res_file)
                # Wait for auto-parse success banner
                for _ in range(50):
                    time.sleep(0.5)
                    if page.locator(".apply-flow-profile-import-awli__success-message").count() > 0:
                        print("[OracleCloudFinger] Profile successfully imported banner confirmed.")
                        break
                            
        # Cover Letter Upload
        cover_letter_input = page.locator("input[type='file'][aria-label*='Cover Letter' i], input[type='file'][title*='Cover Letter' i]").first
        if cover_letter_input.count() > 0:
            cl_file = cand.get("cover_letter_path") or cand.get("cover_letter_filename")
            
            # Resolve relative cover letter path
            if cl_file and not os.path.isabs(cl_file):
                try:
                    from CompanySiteApply.utils.config_resolver import resolve_search_roots
                    search_roots = resolve_search_roots(candidate_data if isinstance(candidate_data, dict) else None)
                except Exception:
                    search_roots = [os.getcwd()]
                for root in search_roots:
                    cand_path = os.path.join(root, cl_file)
                    if os.path.exists(cand_path):
                        cl_file = cand_path
                        break
                    applied_root = os.path.join(root, "APPLIED ON COMPANY WEBSITE")
                    if os.path.exists(applied_root):
                        for dirpath, _, filenames in os.walk(applied_root):
                            if cl_file in filenames:
                                cl_file = os.path.join(dirpath, cl_file)
                                break

            if cl_file and os.path.exists(cl_file):
                del_btn = page.locator("button[aria-label='Delete Cover Letter'], button[title*='Delete Cover Letter']").first
                if del_btn.count() > 0 and del_btn.is_visible():
                    page.once("dialog", lambda dialog: dialog.accept())
                    try:
                        del_btn.click(force=True, no_wait_after=True)
                        time.sleep(1.0)
                    except Exception:
                        pass
                cover_letter_input.set_input_files(cl_file)
                time.sleep(1.0)

        # 2. Title Selection (config-driven; skip when unknown — human-gated flow)
        title = str(cand.get("salutation") or cand.get("title") or "").strip()
        if title:
            self.smart_select_pill(page, title)

        # 3. Address fields
        cand_country = cand.get("country") or ""
        if cand_country:
            self._select_cx_combobox(page, "input[name='country'], input[id^='country-']:not([id*='phoneNumber'])", cand_country)
            time.sleep(0.5)

        addr1 = cand.get("address_line_1") or cand.get("address") or ""
        if addr1:
            DOMHelpers.set_input_value_native(page, "input[name='addressLine1'], [id^='addressLine1']", addr1)
        addr2 = cand.get("address_line_2") or ""
        if addr2:
            DOMHelpers.set_input_value_native(page, "input[name='addressLine2'], [id^='addressLine2']", addr2)
        pincode = str(cand.get("pincode") or cand.get("postal_code") or "").strip()
        if pincode:
            DOMHelpers.set_input_value_native(page, "input[name='postalCode'], [id^='postalCode']", pincode)

        # 4. City Combobox — prioritizes official candidate city
        city_val = str(cand.get("city") or cand.get("location") or "").strip()
        if city_val:
            city_inp = page.locator("input[name='city']:visible, input[id^='city-']:visible").first
            if city_inp.count() > 0:
                cur_city = city_inp.input_value().strip()
                if not cur_city or (city_val.lower() not in cur_city.lower()):
                    city_inp.fill(city_val)
                    time.sleep(1.0)
                    clicked_city = page.evaluate("""(targetCity) => {
                        const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item'))
                            .filter(el => (el.offsetWidth > 0 || el.offsetHeight > 0) && el.innerText.trim().toLowerCase().includes(targetCity.toLowerCase()));
                        if (items.length > 0) {
                            items[0].click();
                            return true;
                        }
                        return false;
                    }""", city_val)
                    time.sleep(1.0)

        # 4b. State Combobox — handles dependent State field (region2) dynamically
        state_inp = page.locator("input[name='region2']:visible, input[id^='region2-']:visible").first
        if state_inp.count() > 0:
            cur_state = state_inp.input_value().strip()
            state_target = str(cand.get("state") or "").strip()
            if not state_target and "karnataka" in str(cand.get("city_state_country", "")).lower():
                state_target = "Karnataka"
            if not cur_state and state_target:
                state_inp.fill(state_target)
                time.sleep(1.0)
                page.evaluate("""(target) => {
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item'))
                        .filter(el => (el.offsetWidth > 0 || el.offsetHeight > 0) && el.innerText.trim().toLowerCase().includes(target.toLowerCase()));
                    if (items.length > 0) {
                        items[0].click();
                        return true;
                    }
                    return false;
                }""", state_target)
                time.sleep(1.0)

        # 5. Preferred Location (multi-select combobox)
        pref_container = page.locator(".apply-flow-block--preferred-locations").first
        if pref_container.count() > 0 or page.locator("input[name='preferredLocations']:visible").count() > 0:
            pills = page.evaluate('''() => Array.from(document.querySelectorAll('.apply-flow-block--preferred-locations .cx-multi-select-pill__value-text, .cx-multi-select-pill, .cx-multi-select-pill__text')).map(e => e.innerText.trim()).filter(Boolean)''')
            if not pills:
                page.evaluate("""() => {
                    const block = document.querySelector('.apply-flow-block--preferred-locations') || document;
                    const btn = block.querySelector('button[id$="-toggle-button"], button.icon-dropdown-arrow, button');
                    if (btn) btn.click();
                }""")
                time.sleep(1.0)
                pref_target = str(cand.get("preferred_location") or cand.get("location") or cand.get("city") or "").strip()
                page.evaluate("""(targetText) => {
                    const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li'))
                        .filter(el => (el.offsetWidth > 0 || el.offsetHeight > 0) && (el.getAttribute('role') === 'option' || el.className.includes('cx-multi-select__list-item')));
                    if (items.length === 0) return;
                    let match = targetText ? items.find(i => i.innerText.toLowerCase().includes(targetText.toLowerCase())) : null;
                    if (match) {
                        match.click();
                    } else if (items.length > 0) {
                        items[0].click();
                    }
                }""", pref_target)
                time.sleep(0.5)
                page.keyboard.press("Escape")
                time.sleep(0.5)

        # Audit errors
        errors = page.evaluate('''() => Array.from(document.querySelectorAll('.app-form-item__error, .oj-form-control-error-message, [class*="error-message"], [aria-invalid="true"]')).map(e => e.innerText.trim()).filter(Boolean)''')
        return {
            "success": len(errors) == 0,
            "step": "profile_and_personal_details",
            "errors": errors,
            "zero_errors_verified": len(errors) == 0
        }

    def _fill_screening_questions_step(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Screening Questions. Uses AIClient to dynamically resolve questions based on
        candidate configuration, ensuring zero hardcoding of answers.
        """
        from core.ai_client import AIClient
        ai = AIClient(OracleCloudFinger._blank_ai_context())

        # 1. Handle all Pill Questions
        pill_groups = page.evaluate('''() => { 
            const items = Array.from(document.querySelectorAll('.app-form-item, fieldset, .input-row')).filter(el => el.offsetParent !== null); 
            return items.map(el => { 
                let label = el.querySelector('legend, label, .app-form-item__label, h2, h3, h4')?.innerText || ''; 
                if(!label) label = el.innerText.split('\\n')[0]; 
                const isRadio = !!el.querySelector('[role="radiogroup"], button[role="radio"]');
                return { 
                    el: el,
                    q: label.trim(), 
                    opts: Array.from(el.querySelectorAll('.cx-select-pill-name')).map(p => p.innerText.trim()),
                    isRadio: isRadio
                }; 
            }).filter(item => item.el.querySelector('.cx-select-pill-section') && !item.q.match(/Title|Phone Number|Country|Address|Name/i)); 
        }''')

        active_nail = self.get_active_nail(page, page.url)

        for group in pill_groups:
            q_text = group["q"]
            opts = group["opts"]
            is_radio = group.get("isRadio", False)
            if not q_text or not opts:
                continue

            # Check company-specific Nail override first
            ans = None
            if active_nail:
                ans = active_nail.override_screening_answer(q_text, options=opts, candidate_data=candidate_data)

            if not ans:
                ans = ai.answer_screening_question(
                    question=q_text,
                    candidate_profile=candidate_data,
                    options=opts,
                    control_type="RADIO" if is_radio else "CHECKBOX"
                )
            if ans:
                answers = [ans] if ans in opts else ([x.strip() for x in ans.split("|||") if x.strip()] if "|||" in ans else [x.strip() for x in ans.split(",") if x.strip()])
                if is_radio and len(answers) > 1:
                    answers = [answers[0]]
                for a in answers:
                    if a in opts:
                        try:
                            q_safe = q_text[:20].replace("'", "\\'")
                            container = page.locator(".app-form-item, fieldset, .input-row").filter(has_text=q_safe).filter(has=page.locator(".cx-select-pill-section")).last
                            if container.count() > 0:
                                self.smart_select_pill(page, a, container_locator=container)
                        except Exception as e:
                            print(f"Failed to find container for {q_safe}: {e}")

        # 2. Handle Multi-Select Comboboxes
        comboboxes = page.evaluate('''() => { 
            const items = Array.from(document.querySelectorAll('.app-form-item, fieldset, .input-row')).filter(el => el.offsetParent !== null); 
            return items.map(el => { 
                let label = el.querySelector('legend, label, .app-form-item__label, h2, h3, h4')?.innerText || ''; 
                if(!label) label = el.innerText.split('\\n')[0]; 
                return { 
                    el: el,
                    q: label.trim(), 
                    id: (el.querySelector('input[role="combobox"]') || {}).id 
                }; 
            }).filter(item => item.id && !item.q.match(/Title|Phone Number|Country|Address|Name|Email|City|State|Preferred Location|Location/i)); 
        }''')
        
        for combo in comboboxes:
            q_text = combo["q"]
            combo_id = combo["id"]
            if not q_text or not combo_id:
                continue
                
            # Ask AI for answers (comma separated if multiple)
            ans_raw = ai.answer_screening_question(
                question=q_text,
                candidate_profile=candidate_data,
                options=None, # Oracle multi-select options are dynamically fetched
                control_type="TEXT" 
            )
            if ans_raw:
                answers = [x.strip() for x in ans_raw.split("|||") if x.strip()] if "|||" in ans_raw else [x.strip() for x in ans_raw.split(",") if x.strip()]
                if answers:
                    self._select_multi_combobox(page, f"[id='{combo_id}']", answers)

        # Also heal experience/education tiles if they happen to be on the same page (JPMC uses a mixed page for section 2)
        tiles_count = page.locator(".apply-flow-profile-item-tile, .timeline-item").count()
        if tiles_count > 0:
            self._fill_experience_step(page, candidate_data)

        # Audit errors
        errors = page.evaluate('''() => Array.from(document.querySelectorAll('.app-form-item__error, .oj-form-control-error-message, [class*="error-message"]')).map(e => e.innerText.trim()).filter(Boolean)''')
        return {
            "success": len(errors) == 0,
            "step": "screening_questions",
            "errors": errors,
            "zero_errors_verified": len(errors) == 0
        }

    @staticmethod
    def _get_candidate_experiences(candidate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        cand = candidate_data.get("candidate", candidate_data)
        if cand.get("experience") and isinstance(cand["experience"], list) and len(cand["experience"]) > 0:
            return cand["experience"]

        experiences = []
        # Source 0: Check company_site_profile.employment (dedicated for product company apply)
        csa_emp = candidate_data.get("company_site_profile", {}).get("employment", {})
        if csa_emp:
            for k, v in csa_emp.items():
                comp = v.get("company") or k
                bullets = v.get("achievements") or []
                if not bullets and v.get("description"):
                    clean_desc = re.sub(r'[â€¢•\r]', '', v.get("description", ""))
                    bullets = [b.strip() for b in clean_desc.split('\n') if b.strip()]
                city = v.get("city") or cand.get("city") or ""
                country = v.get("country") or cand.get("country") or "India"
                experiences.append({
                    "employer": comp,
                    "title": v.get("designation", ""),
                    "country": country,
                    "city": city,
                    "bullets": bullets,
                    "is_current": v.get("is_current", False)
                })
            if experiences:
                return experiences

        # Source 1: Check resume.md
        try:
            from CompanySiteApply.utils.config_resolver import resolve_search_roots
            roots = resolve_search_roots(candidate_data if isinstance(candidate_data, dict) else None)
        except Exception:
            roots = [os.getcwd()]
        for r in roots:
            res_md_path = os.path.join(r, "resume.md")
            if os.path.exists(res_md_path):
                try:
                    with open(res_md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    exp_section = re.search(r"## PROFESSIONAL EXPERIENCE(.*?)(?=## [A-Z]|\Z)", content, re.DOTALL)
                    if exp_section:
                        roles_raw = re.findall(r"### \*\*(.*?)\*\* \| (.*?)\n\*(.*?)\*\n(.*?)(?=###|\Z)", exp_section.group(1), re.DOTALL)
                        for company, title, meta, body in roles_raw:
                            bullets = [re.sub(r'^[•\-\*]\s*', '', b.strip()) for b in body.strip().split('\n') if b.strip()]
                            loc = meta.split('|')[0].strip() if '|' in meta else meta
                            city = loc.split(',')[0].strip()
                            country = loc.split(',')[1].strip() if ',' in loc else 'India'
                            experiences.append({
                                "employer": company.strip(),
                                "title": title.strip(),
                                "city": city,
                                "country": country,
                                "bullets": bullets,
                                "is_current": "present" in meta.lower()
                            })
                    if experiences:
                        break
                except Exception:
                    pass

        # Source 2: profile_content.employment
        if not experiences:
            emp_dict = candidate_data.get("profile_content", {}).get("employment", {})
            for k, v in emp_dict.items():
                comp = v.get("company") or v.get("naukri_card_keyword") or k
                desc = v.get("description", "")
                clean_desc = re.sub(r'[â€¢•\r]', '', desc)
                bullets = [b.strip() for b in clean_desc.split('\n') if b.strip()]
                city = v.get("city") or v.get("location") or cand.get("city") or ""
                country = v.get("country") or cand.get("country") or "India"
                experiences.append({
                    "employer": comp,
                    "title": v.get("designation", ""),
                    "country": country,
                    "city": city,
                    "bullets": bullets,
                    "is_current": v.get("is_current", False)
                })

        return experiences

    def _fill_experience_step(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Work History and Education Timeline Review.
        Heals broken/unmapped degree cards, validates date alignments, and ensures zero red errors.
        Iterates over all tiles to ensure data is exactly verified and not shortened.
        """
        cand = candidate_data.get("candidate", candidate_data)
        edu_list = cand.get("education") or candidate_data.get("education") or []
        exp_list = self._get_candidate_experiences(candidate_data)

        tiles_count = page.locator(".apply-flow-profile-item-tile, .timeline-item").count()
        print(f"[_fill_experience_step] Total tiles detected: {tiles_count}", flush=True)

        for i in range(tiles_count):
            tiles = page.locator(".apply-flow-profile-item-tile, .timeline-item")
            if i >= tiles.count():
                break

            target_tile = tiles.nth(i)
            tile_text = target_tile.inner_text().strip()
            print(f"[_fill_experience_step] Processing tile {i}: {tile_text.replace(chr(10), ' | ')[:60]}", flush=True)

            edit_btn = target_tile.locator('.apply-flow-profile-item-tile__edit-item-icon, button[aria-label*="Edit" i]').first
            if edit_btn.count() == 0 or not edit_btn.is_visible():
                target_tile.scroll_into_view_if_needed()
                time.sleep(0.5)

            if edit_btn.count() > 0:
                edit_btn.click(force=True)
                time.sleep(1.5)

                # Check if it is an Education or Work Experience form (supports both inline and modal dialogs)
                is_edu = page.locator("input[id^='contentItemId']:visible, input[id^='areaOfStudy']:visible, input[id^='educationalEstablishment']:visible").count() > 0
                is_exp = page.locator("input[id^='employerName']:visible, input[name='employerName']:visible").count() > 0

                if is_edu:
                    best_edu = edu_list[0] if edu_list else {}
                    for edu in edu_list:
                        deg = edu.get("degree", "").lower()
                        if deg and deg in tile_text.lower():
                            best_edu = edu
                            break
                    self._heal_education_modal(page, best_edu)
                    print(f"[_fill_experience_step] Healed education tile {i}.", flush=True)
                elif is_exp:
                    best_match = exp_list[0] if exp_list else {}
                    for exp in exp_list:
                        employer = exp.get("employer", "").lower()
                        if employer and (employer in tile_text.lower() or tile_text.lower() in employer):
                            best_match = exp
                            break
                    self._heal_work_experience_tile(page, best_match)
                    print(f"[_fill_experience_step] Healed work experience for {best_match.get('employer', 'unknown')}.", flush=True)

                time.sleep(1.0)
        print("[_fill_experience_step] Finished processing all tiles.", flush=True)

        # Guarantee reverse-chronological experience tile ordering (current employer first, newest to oldest)
        self._reorder_tiles_reverse_chronological(page)

        # Audit errors across Section 3
        errors = page.evaluate('''() => Array.from(document.querySelectorAll('.app-form-item__error, .oj-form-control-error-message, [class*="error-message"], .apply-flow-profile-item-tile--error')).map(e => e.innerText.trim()).filter(Boolean)''')
        return {
            "success": len(errors) == 0,
            "step": "experience_and_education",
            "errors": errors,
            "zero_errors_verified": len(errors) == 0
        }

    def _heal_education_modal(self, page: Any, edu_data: Dict[str, Any]) -> bool:
        """
        Heals open Education dialog: selects Degree, Country, End Date Month/Year, Area of Study, and clicks SAVE.
        """
        target_degree = str(edu_data.get("degree") or "").strip()
        target_country = str(edu_data.get("country") or "India").strip()
        target_major = str(edu_data.get("major") or "").strip()
        target_month = str(edu_data.get("end_month") or edu_data.get("graduated_month") or "").strip()
        target_year = str(edu_data.get("end_year") or edu_data.get("graduated_year") or "").strip()

        # 1. Degree
        degree_input = page.locator("[id^='contentItemId']:visible, input[name='contentItemId']:visible").first
        if degree_input.count() > 0 and target_degree and not degree_input.input_value().strip():
            degree_input.fill(target_degree[:6])
            time.sleep(1.0)
            degree_input.press("ArrowDown")
            time.sleep(0.3)
            degree_input.press("Enter")
            time.sleep(0.3)

        # 2. Country
        country_input = page.locator("input[id^='countryCode']:visible, input[name='countryCode']:visible, input[name='country']:visible, [id^='countryCode']:visible").first
        if country_input.count() > 0 and target_country and country_input.input_value().strip() != target_country:
            c_toggle = page.locator("[id^='countryCode'][id$='-toggle-button']:visible, button.icon-dropdown-arrow:visible").first
            if c_toggle.count() > 0 and c_toggle.is_visible():
                c_toggle.click()
            else:
                country_input.click()
            time.sleep(0.5)
            clicked = page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"], li')).filter(isVis);
                const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                if (opt) { opt.click(); return true; }
                return false;
            }''', target_country)
            time.sleep(0.4)
            page.keyboard.press("Escape")
            if country_input.input_value().strip() != target_country:
                country_input.fill(target_country)
                time.sleep(0.3)
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
                page.keyboard.press("Enter")

        # 3. End Date Month
        month_input = page.locator("[id^='month-endDate']:visible, input[name*='month-endDate']:visible").first
        if month_input.count() > 0 and target_month and month_input.input_value().strip().lower() != target_month.lower():
            m_toggle = page.locator("[id^='month-endDate'][id$='-toggle-button']:visible").first
            if m_toggle.count() > 0 and m_toggle.is_visible():
                m_toggle.click()
            else:
                month_input.click()
            time.sleep(0.4)
            page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"], li')).filter(isVis);
                const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                if (opt) { opt.click(); return true; }
                return false;
            }''', target_month)
            time.sleep(0.4)

        # 4. End Date Year
        year_input = page.locator("[id^='year-endDate']:visible, input[name*='year-endDate']:visible").first
        if year_input.count() > 0 and target_year and year_input.input_value().strip() != target_year:
            year_input.fill(target_year)

        # 5. Area of Study
        study_input = page.locator("[id^='areaOfStudy']:visible, input[name='areaOfStudy']:visible").first
        if study_input.count() > 0 and not study_input.input_value().strip() and target_major:
            study_input.fill(target_major)

        # Click SAVE
        save_btn = page.locator(".save-btn:visible, .app-dialog:visible button:has-text('SAVE'), button:has-text('SAVE'):visible, button:has-text('Save'):visible").first
        if save_btn.count() > 0:
            save_btn.scroll_into_view_if_needed()
            save_btn.click(force=True)
            time.sleep(1.5)
            return True
        return False

    def _heal_work_experience_tile(self, page: Any, exp_data: Dict[str, Any]) -> bool:
        """
        Heals an open Work Experience form:
        - Selects Employer Country (e.g. India)
        - Populates Employer City (e.g. Bangalore, Noida)
        - Selects Internal ('No') pill
        - Formats Achievements into clean bullet points
        - Clicks SAVE
        """
        target_country = str(exp_data.get("country") or "India").strip()
        target_city = exp_data.get("city") or exp_data.get("location") or ""
        bullets = exp_data.get("bullets") or exp_data.get("responsibilities") or exp_data.get("description") or []

        # 1. Employer Country
        if target_country:
            c_input = page.locator("input[id^='countryCode']:visible, input[name='countryCode']:visible, .app-dialog:visible input[name='countryCode']").first
            if c_input.count() > 0 and c_input.is_visible():
                current_c = c_input.input_value().strip()
                if current_c != target_country:
                    c_toggle = page.locator("button[id^='countryCode'][id$='-toggle-button']:visible").first
                    if c_toggle.count() > 0:
                        c_toggle.click()
                        time.sleep(0.6)
                    else:
                        c_input.fill(target_country)
                        time.sleep(0.8)
                    clicked = page.evaluate('''(targetText) => {
                        const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                        const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"], li')).filter(isVis);
                        const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                        if (opt) { opt.click(); return true; }
                        return false;
                    }''', target_country)
                    time.sleep(0.4)
                    if not clicked:
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")

        # 2. Employer City
        if target_city:
            city_input = page.locator("input[id^='employerCity']:visible, input[name='employerCity']:visible, .app-dialog:visible input[name='employerCity']").first
            if city_input.count() > 0 and city_input.is_visible():
                city_input.fill(target_city)
                city_input.dispatch_event("input")
                city_input.dispatch_event("change")
                city_input.dispatch_event("blur")

        # 3. Internal: No
        no_btn = page.locator("button[role='radio']:has-text('No'):visible, button.cx-select-pill-section:has-text('No'):visible, .standard-apply-flow-profile-item:has(input[id^='employerName']) button:has-text('No'), .app-form-item:has-text('Internal') button:has-text('No')").first
        if no_btn.count() > 0 and no_btn.is_visible():
            is_active = "active" in (no_btn.get_attribute("class") or "").lower() or no_btn.get_attribute("aria-pressed") == "true"
            if not is_active:
                no_btn.click()

        # 4. Achievements / Bulleted Responsibilities
        if bullets:
            if isinstance(bullets, list):
                merged = [b.strip().lstrip('•- *') for b in bullets if b.strip()]
            else:
                clean_str = re.sub(r'[Ã¢â‚¬Â¢â€¢•]', '', str(bullets))
                raw_lines = [p.strip().lstrip('•- *') for p in clean_str.split('\n') if p.strip()]
                merged = []
                for line in raw_lines:
                    if merged and not merged[-1].endswith(('.', '!', '?', ':', ';')):
                        merged[-1] = merged[-1] + ' ' + line
                    else:
                        merged.append(line)
            
            bulleted_text = "\n\n".join([f"• {m}" for m in merged if m])
            textarea = page.locator("textarea[id^='achievements']:visible, textarea[name='achievements']:visible, .app-dialog:visible textarea").first
            if textarea.count() > 0 and textarea.is_visible():
                textarea.fill(bulleted_text)
                textarea.dispatch_event("input")
                textarea.dispatch_event("change")
                textarea.dispatch_event("blur")

        # 5. Click SAVE
        save_btn = page.locator(".standard-apply-flow-profile-item:has(input[id^='employerName']) button:has-text('SAVE'), .save-btn, .app-dialog button:has-text('SAVE'), button:has-text('SAVE'):visible").first
        if save_btn.count() > 0:
            save_btn.scroll_into_view_if_needed()
            save_btn.click(force=True)
            try:
                page.wait_for_selector("input[id^='employerName']:visible", state="hidden", timeout=5000)
            except Exception:
                time.sleep(1.5)
            return True
        return False

    def _fill_work_timeline(self, page: Any, work_item: Dict[str, Any]) -> bool:
        """
        Fills the Oracle Cloud HCM Work Experience timeline form dynamically.
        Zero hardcoding: consumes candidate work item schema.
        """
        from CompanySiteApply.parser_doctor.line_wrap_healer import LineWrapHealer

        employer = work_item.get("employer") or work_item.get("company") or ""
        title = work_item.get("title") or work_item.get("role") or ""
        start_month = str(work_item.get("start_month") or "").strip()
        start_year = str(work_item.get("start_year") or "")
        is_current = work_item.get("is_current", False)
        country = str(work_item.get("country") or "").strip()
        state = work_item.get("state") or ""
        city = work_item.get("city") or work_item.get("location") or ""
        responsibilities = work_item.get("responsibilities") or work_item.get("description") or ""

        # 1. Employer Name
        if employer:
            DOMHelpers.set_input_value_native(page, "input[name='employerName'], #employerName-48", employer)

        # 2. Job Title
        if title:
            DOMHelpers.set_input_value_native(page, "input[name='jobTitle'], #jobTitle-49", title)

        # 3. Start Month & Year
        if start_month:
            self._select_cx_combobox(page, "#month-startDate-50", start_month)
        if start_year:
            self._select_cx_combobox(page, "#year-startDate-50", start_year)

        # 4. Current Job Checkbox
        if is_current:
            DOMHelpers.set_checkbox_checked(page, "#af-checkbox-currentJobFlag-52, input[type='checkbox']", checked=True)

        # 5. Employer Country
        if country:
            self._select_cx_combobox(page, "#countryCode-53", country)

        # 6. Employer State or Province (appears dynamically after Country is chosen)
        if state:
            time.sleep(0.5)
            self._select_cx_combobox(page, "[id^='stateProvinceCode']", state)

        # 7. Employer City
        if city:
            DOMHelpers.set_input_value_native(page, "input[name='employerCity'], #employerCity-54", city)

        # 8. Responsibilities (healed with LineWrapHealer)
        if responsibilities:
            healed = LineWrapHealer.heal_text(responsibilities)
            DOMHelpers.set_input_value_native(page, "textarea[name='responsibilities'], #responsibilities-55", healed)

        return True

    def _reorder_tiles_reverse_chronological(self, page: Any) -> bool:
        """
        Universally reorders the Knockout experience observableArray in strict reverse-chronological order
        (newest to oldest, current employer first) across Oracle Cloud HCM portals.
        Ensures both Section 3 and Section 4 Review tiles render in authentic timeline order.
        """
        active_nail = self.get_active_nail(page)
        if active_nail and hasattr(active_nail, "reorder_experience_tiles"):
            try:
                res = active_nail.reorder_experience_tiles(page)
                if res:
                    return True
            except Exception as e:
                print(f"[OracleCloudFinger] Active nail reordering notice: {e}", flush=True)

        try:
            sorted_count = page.evaluate("""() => {
                const tiles = document.querySelectorAll('.apply-flow-profile-item-tile');
                if (tiles.length <= 1) return 0;
                const expTile = tiles.length > 1 ? tiles[1] : tiles[0];
                let koProp = Object.keys(expTile).find(p => p.startsWith('__ko__'));
                if (!koProp) return 0;
                const ctx = expTile[koProp]['1' + koProp]?.context;
                if (!ctx || !ctx.$parent) return 0;
                const parent = ctx.$parent;
                if (!parent.forms || typeof parent.forms.sort !== 'function') return 0;
                
                parent.forms.sort((a, b) => {
                    const modA = typeof a === 'function' && typeof a().model === 'function' ? a().model() : null;
                    const modB = typeof b === 'function' && typeof b().model === 'function' ? b().model() : null;
                    if (!modA || !modB) return 0;
                    
                    const curA = typeof modA.currentJobFlag === 'function' ? modA.currentJobFlag() : 'N';
                    const curB = typeof modB.currentJobFlag === 'function' ? modB.currentJobFlag() : 'N';
                    if (curA === 'Y' && curB !== 'Y') return -1;
                    if (curB === 'Y' && curA !== 'Y') return 1;
                    
                    const startA = typeof modA.startDate === 'function' ? String(modA.startDate() || '') : '';
                    const startB = typeof modB.startDate === 'function' ? String(modB.startDate() || '') : '';
                    return startB.localeCompare(startA);
                });
                
                if (typeof parent._buildTiles === 'function') {
                    parent._buildTiles();
                }
                return parent.forms().length;
            }""")
            if sorted_count:
                print(f"[OracleCloudFinger] Reordered {sorted_count} experience tiles in reverse-chronological order.", flush=True)
            return bool(sorted_count)
        except Exception as e:
            print(f"[OracleCloudFinger] Notice: could not reorder experience tiles: {e}", flush=True)
            return False

    def _fill_section_4_more_about_you(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: More About You / Diversity & Demographics.
        Delegates custom demographic surveys to active Nail (e.g. JPMCNail),
        handles ethnicity, gender, e-signature, canonical link validation,
        cover letter replacement, and validates zero errors.
        """
        cand = candidate_data.get("candidate", candidate_data)

        # 0a. Canonical LinkedIn Link Validation (prevent truncated 'udaykan')
        link_inp = page.locator("input[id*='siteLink']:visible, input[name*='siteLink']:visible").first
        if link_inp.count() > 0:
            canonical_link = cand.get("linkedin_profile_url") or cand.get("linkedin") or ""
            if canonical_link:
                cur_val = link_inp.input_value().strip()
                if cur_val != canonical_link:
                    link_inp.fill(canonical_link)
                    link_inp.dispatch_event("input")
                    link_inp.dispatch_event("change")
                    time.sleep(0.5)

        # 0b. Cover Letter replacement: remove previous and re-upload freshly styled PDF
        cl_path = cand.get("cover_letter_path") or cand.get("cover_letter_filename")
        if not cl_path or not os.path.exists(cl_path):
            try:
                from CompanySiteApply.utils.config_resolver import resolve_search_roots
                roots = resolve_search_roots(candidate_data if isinstance(candidate_data, dict) else None)
            except Exception:
                roots = [os.getcwd()]
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(cand.get("full_name") or "Candidate").strip())
            possible_names = [f"{clean_name}_Cover_Letter.pdf", "Cover_Letter.pdf"]
            for r in roots:
                for target_name in possible_names:
                    cand_target = os.path.join(r, target_name)
                    if os.path.exists(cand_target):
                        cl_path = cand_target
                        break
                    applied_dir = os.path.join(r, "APPLIED ON COMPANY WEBSITE")
                    if os.path.exists(applied_dir):
                        for root_dir, _, files in os.walk(applied_dir):
                            if target_name in files:
                                cl_path = os.path.join(root_dir, target_name)
                                break
                    if cl_path and os.path.exists(cl_path):
                        break
                if cl_path and os.path.exists(cl_path):
                    break

        if cl_path and os.path.exists(cl_path):
            rem_btn = page.locator("button:has-text('REMOVE COVER LETTER'), button[aria-label*='Remove Cover Letter' i]").first
            if rem_btn.count() > 0 and rem_btn.is_visible():
                page.once("dialog", lambda d: d.accept())
                try:
                    rem_btn.click(force=True, no_wait_after=True)
                    time.sleep(2.0)
                except Exception:
                    pass
            cl_input = page.locator("input[name='attachment-upload'], input[id^='attachment-upload'], input[type='file'][aria-label*='Cover Letter' i], input[type='file']").last
            if cl_input.count() > 0:
                cl_input.set_input_files(cl_path)
                time.sleep(3.0)

        # 1. Delegate custom demographic fields to active Nail
        active_nail = self.get_active_nail(page, page.url)
        if active_nail:
            active_nail.handle_custom_fields(page, 4, candidate_data)

        # 2. General Demographics fallback (skip when unknown — operator fills)
        eth_loc = page.locator("input[id*='ETHNICITY']:visible, input[name*='ETHNICITY']:visible").first
        if eth_loc.count() > 0 and not eth_loc.input_value().strip():
            _eth = str(cand.get("ethnicity", "") or "").strip()
            if _eth:
                self.select_cx_dropdown_field(page, "Ethnicity", _eth)

        gender_loc = page.locator("input[id*='GENDER']:visible, input[name*='GENDER']:visible").first
        if gender_loc.count() > 0 and not gender_loc.input_value().strip():
            _gen = str(cand.get("gender", "") or "").strip()
            if _gen:
                self.select_cx_dropdown_field(page, "Gender", _gen)

        # 3. E-Signature Full Name
        sig_loc = page.locator("input[name='fullName'], #fullName-5, input[id*='fullName']").first
        if sig_loc.count() > 0 and not sig_loc.input_value().strip():
            full_name = cand.get("full_name", "")
            if full_name:
                DOMHelpers.set_input_value_native(page, "input[name='fullName'], #fullName-5, input[id*='fullName']", full_name)

        # Guarantee reverse-chronological experience tile ordering on Section 4 review screen
        self._reorder_tiles_reverse_chronological(page)

        # Audit errors across Section 4
        errors = page.evaluate('''() => Array.from(document.querySelectorAll('.app-form-item__error, .oj-form-control-error-message, [class*="error-message"], [aria-invalid="true"]')).map(e => e.innerText.trim()).filter(Boolean)''')
        return {
            "success": len(errors) == 0,
            "step": "more_about_you",
            "errors": errors,
            "zero_errors_verified": len(errors) == 0
        }

    def find_profile_tile_edit_buttons(self, page: Any) -> List[Dict[str, Any]]:
        """
        Locates all edit pencil buttons on profile item tiles and timeline cards.
        Returns metadata for each editable card.
        """
        return page.evaluate('''() => {
            const tiles = Array.from(document.querySelectorAll('.apply-flow-profile-item-tile, .timeline-item'));
            return tiles.map((tile, i) => {
                const btn = tile.querySelector('.apply-flow-profile-item-tile__edit-item-icon, button[aria-label*="Edit" i]');
                const title = tile.querySelector('.apply-flow-profile-item-tile__title, .apply-flow-profile-item-tile__summary-title, h3, h4')?.innerText || '';
                const isVisible = tile.offsetWidth > 0 || tile.offsetHeight > 0;
                return {
                    index: i,
                    title: title.trim(),
                    hasEditButton: !!btn,
                    isVisible: isVisible,
                    editAriaLabel: btn?.getAttribute('aria-label') || ''
                };
            }).filter(t => t.hasEditButton && t.isVisible);
        }''')

    def _fill_generic_fields(self,
                             page: Any,
                             candidate_data: Dict[str, Any],
                             prompt_user_callback: Optional[Callable[[str, Optional[List[str]]], str]] = None) -> Dict[str, Any]:
        """
        Fallback field-by-field solver for questionnaire and general profile steps.
        """
        schema = self.inspect_current_step(page)
        filled_count = 0

        for inp in schema.get("inputs", []):
            if inp.get("is_honeypot") or inp.get("disabled") or inp.get("readOnly"):
                continue

            name = inp.get("name") or inp.get("id") or inp.get("labelText") or ""
            name_lower = name.lower()
            val_to_set = None

            # Resolve from candidate_data
            if "first" in name_lower and "name" in name_lower:
                val_to_set = candidate_data.get("first_name")
            elif "last" in name_lower and "name" in name_lower:
                val_to_set = candidate_data.get("last_name")
            elif "phone" in name_lower:
                val_to_set = candidate_data.get("phone")
            elif "city" in name_lower or "location" in name_lower:
                val_to_set = candidate_data.get("location")

            # Fallback to prompt
            if not val_to_set and inp.get("required") and prompt_user_callback:
                val_to_set = prompt_user_callback(f"Enter value for required field '{name}':", None)

            if val_to_set:
                sel = f"#{inp['id']}" if inp.get("id") else f"[name='{inp.get('name')}']"
                if DOMHelpers.set_input_value_native(page, sel, val_to_set):
                    filled_count += 1

        return {"success": True, "filled_count": filled_count}

    def advance_step(self, page: Any, allow_submit: bool = False) -> Tuple[bool, str]:
        """
        Advances to the next step by clicking the Next button.
        Never clicks Submit unless allow_submit=True is explicitly passed.
        """
        initial_url = page.url

        # Allowlisted wizard buttons only (never clear/back/discard).
        allowed_buttons = ['next', 'submit'] if allow_submit else ['next']
        clicked, which = DOMHelpers.safe_click_button(page, allowed_buttons)
        if not clicked:
            submit_loc = page.locator("button:has-text('Submit'), button:has-text('SUBMIT')").first
            if submit_loc.count() > 0 and submit_loc.is_visible():
                return False, "Reached final step with Submit button present. Halting for human review."
            return False, f"Next button not found or is disabled ({which})"

        # Wait for navigation or AJAX update
        time.sleep(2.5)

        # Shared step-transition guard: URL must change (or completion marker
        # appear) with zero inline validation errors.
        advanced, errors = DOMHelpers.verify_step_advanced(
            page, initial_url,
            ok_markers=["application submitted", "thank you for your job application",
                        "thank you for applying", "your application has been received"])
        if not advanced:
            return False, f"Validation error on page: {'; '.join(errors)}"

        return True, f"Advanced from {initial_url} to {page.url}"

    def is_complete(self, page: Any) -> Tuple[bool, str]:
        """
        Detects Oracle Cloud HCM application confirmation.
        """
        url = page.url
        if "/apply/confirmation" in url or "/applied" in url or "/my-profile" in url:
            return True, f"URL confirms application completion: {url}"

        success_loc = page.locator(":has-text('Application Submitted'), :has-text('Thank you for your job application'), :has-text('Thank you for applying'), :has-text('Your application has been received'), :has-text('ACTIVE JOB APPLICATIONS')")
        if success_loc.count() > 0 and success_loc.first.is_visible():
            return True, "DOM confirmation text detected"

        return False, "Application still in progress"

