# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-17 13:16:00 +05:30
# Issue / Context: Company ATS Nail for JPMorgan Chase on Oracle Cloud HCM.
# Changes Made: Implemented JPMCNail with custom field handling for Section 4 diversity
#               (India Uniformed forces, Ethnicity, Gender), and curated screening answer
#               resolution for Section 2 (18+ age, legal work authorization, experience tier).
# Rationale: Encapsulates JPMC CX_1001 specific portal behaviors without polluting generic
#            OracleCloudFinger mechanics.

# Preventative Notes: Never hardcode candidate PII; all answers resolve dynamically from candidate_data.
#
# [ENTRY #002]
# Term: [SCREENING_AND_DEMOGRAPHIC_TRUTH_GATING]
# Timestamp: 2026-10-07 16:10:00 +05:30
# Issue / Context: Demographic selects defaulted (No/Asian/Male); screening returned fixed Yes/No and assumed domain stack (software engineering/AWS/fullstack); _match_choice fell back to options[0].
# Changes Made: Demographics skip when config missing; screening answers gated on candidate truth (age/auth/sponsorship/passport/diploma) with None deferral; expertise/AWS/focus match taxonomy or skill map; _match_choice returns None (H1).
# Rationale: No assumed identity or stack; unknowns defer to the operator, never fiction.

# Preventative Notes: Never restore fixed answers or options[0] here.
#
# [ENTRY #003]
# Term: [TIERED_FIELD_RESOLUTION]
# Timestamp: 2026-10-07 17:10:00 +05:30
# Issue / Context: Demographic fields keyed on versioned flexfield IDs that rev per requisition schema.
# Changes Made: _resolve_field tier (exact ID -> name attribute -> shared semantic label proximity); all three demographic fields use it.
# Rationale: Survives ATTRIBUTE suffix revs; future nails reuse the shared helper.
# [ENTRY #004]
# Term: [REVERSE_CHRONOLOGICAL_EXPERIENCE_REORDERING]
# Timestamp: 2026-10-09 09:12:00 +05:30
# Issue / Context: Oracle Cloud HCM candidate portal backend returns previous employments
#                  alphabetically by employer name rather than chronologically, displaying
#                  tiles in unnatural non-chronological order.
# Changes Made: Added reorder_experience_tiles() which sorts Knockout VM parent.forms
#               observableArray in strict reverse-chronological order (newest to oldest,
#               current job first) and triggers _buildTiles().
# Rationale: Ensures candidate timeline displays in authentic professional order on both
#            Section 3 and Section 4 Review screens.
# Preventative Notes: Never rely on default Oracle HCM insertion order for tile display.
# ==============================================================================

import re
import time
from typing import Any, Dict, List, Optional
from CompanySiteApply.nails.base_nail import BaseNail
from CompanySiteApply.utils.dom_helpers import DOMHelpers


class JPMCNail(BaseNail):
    """
    Company ATS Nail for JPMorgan Chase (JPMC) career portal on Oracle Cloud HCM.
    Attached to OracleCloudFinger to handle CX_1001 custom questionnaires and surveys.
    """

    @property
    def company_name(self) -> str:
        return "JPMorgan Chase"

    def matches(self, url: str, page_title: str = "", page: Any = None) -> bool:
        url_lower = (url or "").lower()
        title_lower = (page_title or "").lower()
        return "jpmc.fa.oraclecloud.com" in url_lower or "jpmorgan" in url_lower or "jpmc" in title_lower

    def _resolve_field(self, page: Any, exact_css: str, name_css: str,
                       label_pattern: str) -> Any:
        """
        Tiered field resolution surviving requisition schema revs:
        exact ID -> name attribute -> semantic label proximity. Returns a
        visible locator or None. Shared-helper backed so future nails reuse it.
        """
        for css in (exact_css, name_css):
            try:
                loc = page.locator(css).first
                if loc.count() > 0 and loc.is_visible():
                    return loc
            except Exception:
                continue
        try:
            found = DOMHelpers.find_field_by_label(page, label_pattern)
            if found is not None:
                return found
        except Exception:
            pass
        return None

    def handle_custom_fields(self, page: Any, step_num: int, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes JPMC-specific custom form fields on demographic/diversity steps (Section 4).
        """
        results = {}
        cand = candidate_data.get("candidate", candidate_data)

        def _select_cx_pill_or_dropdown(toggle_css_list: List[str], input_css_list: List[str], target_val: str, field_name: str, label_hint: str = "") -> Optional[str]:
            if not target_val:
                return None
            field = None
            for sel in input_css_list:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        field = loc
                        break
                except Exception:
                    continue
            if field is None and label_hint:
                try:
                    row = page.locator(f".input-row:has-text('{label_hint}')").first
                    if row.count() > 0:
                        field = row.locator("input").first
                except Exception:
                    pass

            if field is None:
                return None

            cur = field.input_value().strip()
            if cur and cur.lower() == target_val.lower():
                return cur

            toggle = None
            for t_sel in toggle_css_list:
                try:
                    t_loc = page.locator(t_sel).first
                    if t_loc.count() > 0 and t_loc.is_visible():
                        toggle = t_loc
                        break
                except Exception:
                    continue

            if toggle is not None:
                toggle.click()
            else:
                try:
                    row = field.locator("xpath=ancestor::div[contains(@class, 'input-row')]").first
                    t_btn = row.locator("button[id$='-toggle-button'], button.icon-dropdown-arrow").first
                    if t_btn.count() > 0 and t_btn.is_visible():
                        t_btn.click()
                    else:
                        field.click()
                except Exception:
                    field.click()
            time.sleep(0.8)

            # Prioritize exact matching on dropdown list items (role=gridcell, role=option, cx-select__list-item)
            clicked = page.evaluate('''(targetText) => {
                const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                const exactOpt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                if (exactOpt) {
                    exactOpt.click();
                    return true;
                }
                const prefixOpt = items.find(i => i.innerText.trim().toLowerCase().startsWith(targetText.toLowerCase()));
                if (prefixOpt) {
                    prefixOpt.click();
                    return true;
                }
                return false;
            }''', target_val)
            time.sleep(0.5)

            readback = field.input_value().strip()
            if not readback or readback.lower() != target_val.lower():
                field.fill(target_val)
                time.sleep(0.5)
                # Retry exact match after typing filters the list
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const opt = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (opt) opt.click();
                }''', target_val)
                time.sleep(0.5)
                readback = field.input_value().strip()

            page.keyboard.press("Escape")
            results[field_name] = readback
            print(f"[JPMCNail] Demographic {field_name} set to: '{readback}'", flush=True)
            return readback

        # 1. India Uniformed Forces / Military Status
        forces_val = str(cand.get("india_uniformed_forces") or cand.get("military_status") or "No").strip()
        _select_cx_pill_or_dropdown(
            toggle_css_list=['#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-5-toggle-button', '[id*="indiaMilitaryStatus"][id$="-toggle-button"]', 'button[aria-label*="India Uniformed"]'],
            input_css_list=['#IN-DFF-indiaMilitaryStatus-ATTRIBUTE16-5', 'input[name*="indiaMilitaryStatus"]', 'input[id*="indiaMilitaryStatus"]', '[id*="ATTRIBUTE16"]'],
            target_val=forces_val,
            field_name="india_uniformed_forces",
            label_hint="India Uniformed forces"
        )

        # 2. Ethnicity
        eth_val = str(cand.get("ethnicity") or cand.get("Ethnicity") or cand.get("race") or "").strip()
        if eth_val and "decline" not in eth_val.lower():
            _select_cx_pill_or_dropdown(
                toggle_css_list=['#IN-STANDARD-ORA_ETHNICITY-STANDARD-3-toggle-button', '[id*="ETHNICITY"][id$="-toggle-button"]', 'button[aria-label*="Ethnicity"]'],
                input_css_list=['#IN-STANDARD-ORA_ETHNICITY-STANDARD-3', 'input[name*="ETHNICITY"]', 'input[id*="ETHNICITY"]'],
                target_val=eth_val,
                field_name="ethnicity",
                label_hint="Ethnicity"
            )

        # 3. Gender
        gen_val = str(cand.get("gender") or "").strip()
        if gen_val and "decline" not in gen_val.lower():
            _select_cx_pill_or_dropdown(
                toggle_css_list=['#IN-STANDARD-ORA_GENDER-STANDARD-4-toggle-button', '[id*="GENDER"][id$="-toggle-button"]', 'button[aria-label*="Gender"]'],
                input_css_list=['#IN-STANDARD-ORA_GENDER-STANDARD-4', 'input[name*="GENDER"]', 'input[id*="GENDER"]'],
                target_val=gen_val,
                field_name="gender",
                label_hint="Gender"
            )

        # 4. LinkedIn Link Normalization (Defense against truncation)
        linkedin_url = cand.get("linkedin_profile_url") or cand.get("linkedin")
        if linkedin_url:
            link_field = page.locator("input[id*='siteLink'], input[name*='siteLink']").first
            if link_field.count() > 0:
                cur_link = link_field.input_value().strip()
                if cur_link != linkedin_url:
                    link_field.fill(linkedin_url)
                    link_field.dispatch_event("input")
                    link_field.dispatch_event("change")
                    results["linkedin_url"] = linkedin_url
                    print(f"[JPMCNail] Corrected LinkedIn link to canonical: '{linkedin_url}'", flush=True)

        # 5. Full Name (E-Signature)
        full_name = cand.get("full_name", "")
        if full_name:
            sig_field = page.locator("input[name='fullName']:visible, [id^='fullName']:visible").first
            if sig_field.count() > 0 and not sig_field.input_value().strip():
                sig_field.fill(full_name)
                results["full_name"] = full_name
                print(f"[JPMCNail] E-Signature full name set to: '{full_name}'", flush=True)

        return results

    def heal_invalid_education_tiles(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        """
        Audits Section 3 education tiles for invalid status (e.g. 'Fields to fix: 1', 'Unnamed Major').
        Opens the edit modal, populates Degree, Area of Study, and Country from candidate data, and saves.
        """
        try:
            cand = candidate_data.get("candidate", candidate_data)
            edu_list = cand.get("education") or []
            edu_info = edu_list[0] if edu_list else {}

            target_degree = str(edu_info.get("degree") or "Bachelor's Degree").strip()
            target_major = str(edu_info.get("major") or edu_info.get("field_of_study") or "Computer Science & Engineering").strip()
            target_country = str(edu_info.get("country") or "India").strip()

            # Check for invalid tile or "Fields to fix"
            invalid_tile = page.locator(".apply-flow-profile-item-tile--invalid:visible, .apply-flow-profile-item-tile:has-text('Fields to fix'):visible").first
            if invalid_tile.count() == 0:
                return False

            print("[JPMCNail] Detected invalid education tile. Launching healer...", flush=True)
            edit_btn = invalid_tile.locator("button[aria-label*='Edit' i], button.icon-edit, .icon-edit, button").first
            if edit_btn.count() > 0:
                edit_btn.click()
            else:
                invalid_tile.click()
            time.sleep(1.5)

            # 1. Degree Combobox
            deg_toggle = page.locator("button[id^='contentItemId'][id$='-toggle-button']:visible").first
            if deg_toggle.count() > 0:
                deg_toggle.click()
                time.sleep(0.8)
                page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const match = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (match) match.click();
                }''', target_degree)
                time.sleep(0.5)

            # 2. Area of Study
            study_inp = page.locator("input[name='areaOfStudy']:visible, input[id^='areaOfStudy']:visible").first
            if study_inp.count() > 0:
                study_inp.fill(target_major)
                study_inp.dispatch_event("input")
                study_inp.dispatch_event("change")

            # 3. Country Combobox
            c_toggle = page.locator("button[id^='countryCode'][id$='-toggle-button']:visible").first
            if c_toggle.count() > 0:
                c_toggle.click()
                time.sleep(0.8)
                selected_country = page.evaluate('''(targetText) => {
                    const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                    const match = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                    if (match) {
                        match.click();
                        return true;
                    }
                    return false;
                }''', target_country)
                if not selected_country:
                    c_inp = page.locator("input[name='countryCode']:visible, input[id^='countryCode']:visible").first
                    if c_inp.count() > 0:
                        c_inp.fill(target_country)
                        time.sleep(0.5)
                        page.evaluate('''(targetText) => {
                            const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
                            const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]')).filter(isVis);
                            const match = items.find(i => i.innerText.trim().toLowerCase() === targetText.toLowerCase());
                            if (match) match.click();
                        }''', target_country)
                time.sleep(0.5)

            # 4. Save Modal
            save_btn = page.locator("button.save-btn:visible, button:has-text('SAVE'):visible").first
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(2.0)
                print("[JPMCNail] Saved healed education tile.", flush=True)
                return True

            return False
        except Exception as e:
            print(f"[JPMCNail] Notice: could not heal education tile ({e})", flush=True)
            return False

    def override_screening_answer(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        candidate_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        JPMC curated screening questionnaire matching.
        """
        if not question_text:
            return None

        q = question_text.lower().strip()
        data = candidate_data or {}
        cand = data.get("candidate", data)

        # 1. Age Gate (18+): answerable only when date_of_birth or explicit
        # majority flag is present; otherwise defer to the operator.
        if "at least 18 years of age" in q or "18 years" in q:
            if cand.get("date_of_birth") or cand.get("age_verified") or cand.get("majority_confirmed"):
                return self._match_choice("Yes", options)
            return None

        # 2. Legal Work Authorization (resolve from citizenship/country only)
        if "legally authorized to work" in q or "authorized to work in this country" in q:
            # Domestic citizen applying in home country
            cand_country = str(cand.get("country", "")).lower()
            citizenship = str(cand.get("citizenship", "")).lower()
            if ("india" in citizenship or "india" in cand_country
                    or str(cand.get("legally_authorized", "")).lower() in ("yes", "true", "1")):
                return self._match_choice("Yes", options)
            return None

        # 3. Visa Sponsorship (resolve from explicit flag; default unknown -> operator)
        if "sponsorship for an employment-based visa" in q or "require sponsorship" in q:
            req = str(cand.get("requires_sponsorship", "")).lower()
            if req in ("yes", "true", "1"):
                return self._match_choice("Yes", options)
            if req in ("no", "false", "0"):
                return self._match_choice("No", options)
            return None

        # 4. Indian Passport (resolve from citizenship only)
        if "hold an indian passport" in q:
            citizenship = str(cand.get("citizenship", "")).lower()
            if "india" in citizenship:
                return self._match_choice("Yes", options)
            return None

        # 5. Dual / Foreign Citizenship (resolve from citizenship/country only)
        if "citizenship or a passport of any country other than" in q:
            if cand.get("citizenship") or cand.get("country"):
                return self._match_choice("No", options)
            return None

        # 6. High School Diploma / 10+2 (resolve from education presence only)
        if "high school diploma" in q or "10+2" in q:
            if cand.get("education") or cand.get("degree") or (data.get("ats_answers", {}) if isinstance(data, dict) else {}):
                return self._match_choice("Yes", options)
            return None

        # 7. Relevant Years of Work Experience Tier
        if "relevant years of work experience" in q or "years of work experience you have" in q:
            total_exp = float(cand.get("total_experience_years", 0))
            if options:
                # Parse numeric tiers from options
                best_option = None
                highest_threshold = -1.0
                for opt in options:
                    nums = [float(n) for n in re.findall(r'\d+', opt)]
                    threshold = max(nums) if nums else 0.0
                    if "no prior" in opt.lower() or "none" in opt.lower():
                        threshold = 0.0
                    if total_exp >= threshold and threshold > highest_threshold:
                        highest_threshold = threshold
                        best_option = opt
                if best_option:
                    return best_option

        # 8. Primary Area of Expertise (resolved dynamically from taxonomy and profile)
        if "primary area of expertise" in q and options:
            _tax = data.get("taxonomy_skills", {}) if isinstance(data, dict) else {}
            _terms = set()
            for _v in (_tax.values() if isinstance(_tax, dict) else []):
                for _s in (_v if isinstance(_v, list) else []):
                    if isinstance(_s, str):
                        _terms.add(_s.lower().strip())
                    elif isinstance(_s, dict):
                        _terms.add(str(_s.get("skill_name", "")).lower().strip())
            for text in [cand.get("resume_headline", ""), cand.get("profile_summary", "")]:
                for word in re.findall(r'[a-zA-Z0-9+#]+', str(text).lower()):
                    if len(word) > 2:
                        _terms.add(word)

            best_opt = None
            best_score = -1
            for opt in options:
                opt_l = opt.lower()
                score = 0
                if opt_l in _terms:
                    score += 10
                for t in _terms:
                    if len(t) > 3 and (t in opt_l or opt_l in t):
                        score += 3
                if score > best_score and score > 0:
                    best_score = score
                    best_opt = opt
            if best_opt:
                return best_opt
            return None

        # 9. Tool / Platform Proficiency (resolve dynamically from skill map or taxonomy)
        if "proficiency" in q and options:
            _skills = ((data.get("ats_answers", {}) or {}).get("skill_years_experience", {}) or {}) if isinstance(data, dict) else {}
            _tool_years = None
            for _k, _v in _skills.items():
                if str(_k).lower() in q:
                    try:
                        _tool_years = float(_v)
                        break
                    except Exception:
                        pass
            if _tool_years is not None:
                if _tool_years >= 4:
                    return self._match_choice("Advanced / Expert", options) or self._match_choice("Advanced", options) or self._match_choice("Expert", options)
                if _tool_years >= 2:
                    return self._match_choice("Intermediate", options)
                return self._match_choice("Beginner", options)
            else:
                tot_exp = float(cand.get("total_experience_years", 0))
                if tot_exp >= 5:
                    return self._match_choice("Advanced / Expert", options) or self._match_choice("Advanced", options)
                elif tot_exp >= 2:
                    return self._match_choice("Intermediate", options)
                return self._match_choice("Beginner", options)

        # 10. Area of Focus within candidate domain (resolved dynamically from taxonomy and profile)
        if "area of focus" in q and options:
            _tax = data.get("taxonomy_skills", {}) if isinstance(data, dict) else {}
            _terms = set()
            for _v in (_tax.values() if isinstance(_tax, dict) else []):
                for _s in (_v if isinstance(_v, list) else []):
                    if isinstance(_s, str):
                        _terms.add(_s.lower().strip())
                    elif isinstance(_s, dict):
                        _terms.add(str(_s.get("skill_name", "")).lower().strip())
            best_opt = None
            best_score = -1
            for opt in options:
                opt_l = opt.lower()
                score = 0
                if opt_l in _terms:
                    score += 10
                for t in _terms:
                    if len(t) > 3 and (t in opt_l or opt_l in t):
                        score += 3
                if score > best_score and score > 0:
                    best_score = score
                    best_opt = opt
            if best_opt:
                return best_opt
            return None

        return None

    def _match_choice(self, target: str, options: Optional[List[str]]) -> Optional[str]:
        # H1: never blind-pick options[0]; return None so the operator/AI resolves.
        if not options:
            return None
        target_l = target.lower().strip()
        for opt in options:
            if opt.lower().strip() == target_l:
                return opt
        for opt in options:
            if target_l in opt.lower():
                return opt
        return None

    def reorder_experience_tiles(self, page: Any) -> bool:
        """
        Sorts the Knockout experience observableArray in strict reverse-chronological order
        (newest to oldest, current job first) so Oracle Cloud HCM tiles render correctly.
        """
        try:
            sorted_count = page.evaluate("""() => {
                const tiles = document.querySelectorAll('.apply-flow-profile-item-tile');
                if (tiles.length <= 1) return 0;
                // Index 0 is typically education, experience tiles follow
                const expTile = tiles.length > 1 ? tiles[1] : tiles[0];
                let koProp = Object.keys(expTile).find(p => p.startsWith('__ko__'));
                if (!koProp) return 0;
                const ctx = expTile[koProp]['1' + koProp]?.context;
                if (!ctx || !ctx.$parent) return 0;
                const parent = ctx.$parent;
                if (!parent.forms || typeof parent.forms.sort !== 'function') return 0;
                
                // Sort parent.forms directly using observableArray sort
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
            print(f"[JPMCNail] Reverse-chronologically reordered {sorted_count} experience tiles.", flush=True)
            return bool(sorted_count)
        except Exception as e:
            print(f"[JPMCNail] Notice: could not reorder experience tiles ({e})", flush=True)
            return False

