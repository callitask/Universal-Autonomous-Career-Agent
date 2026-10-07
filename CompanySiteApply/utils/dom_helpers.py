# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-15 22:48:00 +05:30
# Issue / Context: Framework-safe DOM interaction utilities for enterprise ATS forms.
# Changes Made: Implemented DOMHelpers supporting React, Oracle JET, and Workday synthetic event trees.
# Rationale: Direct page.fill() often fails on complex enterprise ATSs (Oracle JET oj-*, Workday)
#            because framework data-binding relies on native input/change event dispatching.

# Preventative Notes: Always dispatch native Input and Change events; scope clicks carefully.
# [ENTRY #002]
# Term: [SHARED_EXTENSIBLE_CONTROLS_AND_GUARDS]
# Timestamp: 2026-10-07 17:10:00 +05:30
# Issue / Context: Schema scan saw native tags only (ARIA/JET/Workday widgets invisible); no shared error/step/resume/label-proximity helpers; frame embeds uninspectable.
# Changes Made: FORM_CONTROL_SELECTORS + FORM_ERROR_SELECTORS sets; extract_form_schema include_custom pass (HoneypotGuard-compatible keys); extract_schema_all_frames opt-in; find_field_by_label (H3-escaped); collect_form_errors; verify_step_advanced (URL-change + error gate, never auto-resubmits); resolve_resume_file.
# Rationale: Library-first so future fingers/nails/portals inherit behavior. Plain tag/role names only, never hashed classes.
# Preventative Notes: Never add hashed CSS-module classes to the shared sets (pinned by test_dom_helpers).
# ==============================================================================

import time
from typing import Any, Dict, List, Optional, Tuple


class DOMHelpers:
    """
    Robust DOM helper methods for modern Single-Page ATS Applications (Oracle JET, React, Angular).
    Shared library: all fingers and nails resolve controls, errors, files, and step
    transitions through these helpers so future platforms inherit the same behavior.
    """

    # Extensible control discovery set: native tags first, then ARIA widgets,
    # Oracle JET web components, and Workday automation hooks. Plain tag/role
    # names only — never hashed CSS-module classes (they rotate per deploy).
    FORM_CONTROL_SELECTORS = [
        'input:not([type="hidden"])',
        'textarea',
        'select',
        '[role="combobox"]',
        '[role="listbox"]',
        '[role="radiogroup"]',
        '[role="radio"]',
        '[role="checkbox"]',
        '[role="switch"]',
        'oj-select-single',
        'oj-combobox-one',
        'oj-input-date',
        'oj-radioset',
        'oj-checkboxset',
        '[data-automation-id]',
    ]

    # Inline validation signals across Oracle JET, Workday, Greenhouse, generic.
    FORM_ERROR_SELECTORS = [
        ".oj-invalid",
        "[aria-invalid='true']",
        ".oj-form-control-error-message",
        ".app-form-item__error",
        "[class*='error-message']",
        ".field-validation-error",
        ".help-block-error",
        "[data-automation-id*='error']",
    ]

    @staticmethod
    def set_input_value_native(page: Any, selector: str, value: str, timeout_ms: int = 5000) -> bool:
        """
        Safely sets value into an input or textarea using native property setter and dispatches
        synthetic events so React / Oracle JET internal models update correctly.
        """
        try:
            page.wait_for_selector(selector, timeout=timeout_ms, state="visible")
            locator = page.locator(selector)
            locator.scroll_into_view_if_needed()
            locator.click()

            # Execute native property setter and event dispatch in page context
            page.evaluate("""({sel, val}) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                
                // Focus element
                el.focus();
                
                // Use native HTMLInputElement / HTMLTextAreaElement value setter to bypass framework wrappers
                const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                if (nativeSetter) {
                    nativeSetter.call(el, val);
                } else {
                    el.value = val;
                }
                
                // Dispatch full synthetic event chain
                el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true, cancelable: true }));
                return true;
            }""", {"sel": selector, "val": value})
            return True
        except Exception as e:
            # Fallback to standard Playwright fill
            try:
                page.locator(selector).fill(value, timeout=2000)
                return True
            except Exception:
                return False

    @staticmethod
    def set_checkbox_checked(page: Any, selector: str, checked: bool = True, timeout_ms: int = 5000) -> bool:
        """
        Checks or unchecks a checkbox safely. If the native checkbox is hidden behind a custom
        label/styled span (common in Oracle JET and Workday), clicks the parent or associated label.
        """
        try:
            locator = page.locator(selector)
            is_checked = locator.is_checked()
            if is_checked == checked:
                return True

            # Attempt standard check
            try:
                if checked:
                    locator.check(force=True, timeout=2000)
                else:
                    locator.uncheck(force=True, timeout=2000)
                return True
            except Exception:
                pass

            # Fallback: JavaScript direct click & event dispatch
            page.evaluate("""({sel, shouldCheck}) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                
                // If wrapped by label, click label
                const label = el.closest('label') || document.querySelector(`label[for="${el.id}"]`);
                if (label) {
                    label.click();
                    return true;
                }
                
                el.checked = shouldCheck;
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('click', { bubbles: true }));
                return true;
            }""", {"sel": selector, "shouldCheck": checked})
            return True
        except Exception:
            return False

    @staticmethod
    def extract_form_schema(page: Any, include_custom: bool = True) -> Dict[str, Any]:
        """
        Inspects the active page DOM and returns a comprehensive structured catalog
        of all inputs, textareas, selects, radio groups, checkboxes, honeypots, and buttons.
        Custom ARIA / web-component controls are appended with the same dict keys
        (plus `role` and `isCustomComponent`) so HoneypotGuard keeps working.
        """
        script = """(args) => {
            const includeCustom = args && args[0];
            const extraSelectors = (args && args[1]) || [];
            const results = {
                title: document.title,
                url: window.location.href,
                headings: [],
                inputs: [],
                buttons: []
            };

            // Headings
            document.querySelectorAll('h1, h2, h3, [role="heading"]').forEach(h => {
                const txt = h.innerText?.trim();
                if (txt) results.headings.push(txt);
            });

            const pushControl = (el, idx, isCustom) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const isVisible = style.display !== 'none' &&
                                  style.visibility !== 'hidden' &&
                                  style.opacity !== '0' &&
                                  rect.width > 0 && rect.height > 0;

                // Find associated label text
                let labelText = '';
                if (el.getAttribute('aria-labelledby')) {
                    const lblEl = document.getElementById(el.getAttribute('aria-labelledby'));
                    if (lblEl) labelText = lblEl.innerText?.trim();
                }
                if (!labelText && el.id) {
                    const l = document.querySelector(`label[for="${el.id}"]`);
                    if (l) labelText = l.innerText?.trim();
                }
                if (!labelText) {
                    const parentLabel = el.closest('label');
                    if (parentLabel) labelText = parentLabel.innerText?.trim();
                }
                if (!labelText) {
                    const container = el.closest('.oj-form-layout-element, .form-group, .field-container, fieldset');
                    const hdr = container?.querySelector('label, .oj-label, .field-label, legend');
                    if (hdr) labelText = hdr.innerText?.trim();
                }
                if (!labelText) {
                    labelText = el.getAttribute('aria-label') || el.placeholder || '';
                }

                results.inputs.push({
                    index: idx,
                    tagName: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    type: el.getAttribute('type') || (el.tagName.toLowerCase() === 'textarea' ? 'textarea' : 'text'),
                    name: el.getAttribute('name') || '',
                    id: el.getAttribute('id') || '',
                    className: el.className || '',
                    placeholder: el.placeholder || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    labelText: labelText,
                    value: el.value || '',
                    checked: el.checked || false,
                    required: el.required || el.getAttribute('aria-required') === 'true' || el.classList.contains('oj-required'),
                    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                    readOnly: el.readOnly || false,
                    isVisible: isVisible,
                    isCustomComponent: isCustom || el.tagName.toLowerCase().startsWith('oj-'),
                    styleSnippet: `display:${style.display}; visibility:${style.visibility}; opacity:${style.opacity}`
                });
            };

            // Native form controls (unchanged behavior)
            const native = document.querySelectorAll('input, textarea, select');
            native.forEach((el, idx) => pushControl(el, idx, false));

            // Custom ARIA / web-component controls (additive; skipped when already captured)
            if (includeCustom) {
                const seen = new Set(Array.from(native));
                let idx = native.length;
                document.querySelectorAll(extraSelectors.join(',')).forEach((el) => {
                    if (seen.has(el)) return;
                    if (el.tagName.toLowerCase() === 'input' || el.tagName.toLowerCase() === 'textarea' || el.tagName.toLowerCase() === 'select') return;
                    seen.add(el);
                    pushControl(el, idx++, true);
                });
            }

            // Buttons
            document.querySelectorAll('button, input[type="submit"], input[type="button"], a.button, [role="button"]').forEach((b, idx) => {
                const style = window.getComputedStyle(b);
                const rect = b.getBoundingClientRect();
                const isVisible = style.display !== 'none' &&
                                  style.visibility !== 'hidden' &&
                                  rect.width > 0 && rect.height > 0;
                results.buttons.push({
                    index: idx,
                    text: b.innerText?.trim() || b.getAttribute('aria-label') || b.value || '',
                    type: b.getAttribute('type') || '',
                    className: b.className || '',
                    disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
                    isVisible: isVisible
                });
            });

            return results;
        }"""
        try:
            custom_selectors = [s for s in DOMHelpers.FORM_CONTROL_SELECTORS
                                if s not in ('input:not([type="hidden"])', 'textarea', 'select')]
            return page.evaluate(script, [include_custom, custom_selectors])
        except Exception as e:
            return {"error": str(e), "url": getattr(page, "url", "")}

    @staticmethod
    def extract_schema_all_frames(page: Any, include_custom: bool = True) -> List[Dict[str, Any]]:
        """
        Opt-in multi-frame inspection for portals embedding application boards in
        <iframe>s. Returns one schema per accessible frame (main frame first).
        Fill/advance paths stay single-frame unless a caller opts in.
        """
        schemas: List[Dict[str, Any]] = []
        try:
            frames = getattr(page, "frames", []) or []
        except Exception:
            frames = []
        if not frames:
            schemas.append(DOMHelpers.extract_form_schema(page, include_custom))
            return schemas
        for frame in frames:
            try:
                schema = DOMHelpers.extract_form_schema(frame, include_custom)
                schema["frame_url"] = getattr(frame, "url", "")
                schemas.append(schema)
            except Exception:
                continue
        return schemas

    @staticmethod
    def find_field_by_label(page: Any, label_pattern: str,
                            field_css: str = "input, [role='combobox'], oj-select-single, select") -> Any:
        """
        Semantic proximity locator: finds a visible label matching the pattern,
        then resolves the control inside its form container. Survives dynamic ID
        suffix revs (e.g. ATTRIBUTE16-8 -> ATTRIBUTE16-9) that break hardcoded IDs.
        Returns a Playwright locator or None. Single quotes in the pattern are
        escaped per the H3 selector rule.
        """
        if not label_pattern:
            return None
        safe = str(label_pattern).replace("'", "\\'")
        label_loc = page.locator(
            f"label:has-text('{safe}'), .oj-label:has-text('{safe}'), legend:has-text('{safe}')"
        ).first
        try:
            if label_loc.count() == 0 or not label_loc.is_visible():
                return None
            container = label_loc.locator(
                "xpath=ancestor::*[contains(@class, 'oj-form-layout-element') "
                "or contains(@class, 'form-group') or contains(@class, 'field-container') "
                "or self::fieldset or self::div][1]"
            )
            field = container.locator(field_css).first
            if field.count() > 0 and field.is_visible():
                return field
        except Exception:
            return None
        return None

    @staticmethod
    def collect_form_errors(page: Any, limit: int = 5) -> List[str]:
        """
        Aggregates visible inline validation messages across portal frameworks.
        Read-only; safe to call after any step advance.
        """
        detected: List[str] = []
        for sel in DOMHelpers.FORM_ERROR_SELECTORS:
            try:
                loc = page.locator(sel)
                if loc.count() == 0:
                    continue
                for i in range(min(loc.count(), limit)):
                    try:
                        txt = (loc.nth(i).inner_text() or "").strip()
                    except Exception:
                        continue
                    if txt and txt not in detected:
                        detected.append(txt)
                    if len(detected) >= limit:
                        return detected
            except Exception:
                continue
        return detected

    @staticmethod
    def verify_step_advanced(page: Any, before_url: str,
                             ok_markers: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Step-transition guard shared by all fingers: True only when the step
        actually changed (URL differs or a completion marker appeared) AND no
        inline validation errors are present. Never auto-retries submission —
        callers return (False, errors) so the human-gated operator intervenes.
        """
        errors = DOMHelpers.collect_form_errors(page)
        try:
            after_url = page.url
        except Exception:
            after_url = before_url
        if ok_markers:
            try:
                body_text = (page.locator("body").first.inner_text() or "").lower()
                if any(m.lower() in body_text for m in ok_markers):
                    return True, []
            except Exception:
                pass
        if after_url != before_url:
            return (len(errors) == 0), errors
        if errors:
            return False, errors
        return False, ["Step did not advance and no validation message was found"]

    @staticmethod
    def resolve_resume_file(candidate_data: Optional[Dict[str, Any]] = None,
                            resume_path: Optional[str] = None) -> Optional[str]:
        """
        Shared resume-file resolver: explicit path -> candidate resume keys ->
        search roots (profile dir, blueprint, repo root, cwd) including the
        per-profile applications archive. Returns an absolute path or None so
        callers prompt the operator instead of inventing a file.
        """
        import os
        cand = {}
        if isinstance(candidate_data, dict):
            cand = candidate_data.get("candidate", candidate_data)
            if not isinstance(cand, dict):
                cand = {}
        res_file = resume_path or cand.get("resume_path") or cand.get("resume_filename")
        if not res_file:
            return None
        res_file = str(res_file)
        if os.path.isabs(res_file):
            return res_file if os.path.exists(res_file) else None
        try:
            from CompanySiteApply.utils.config_resolver import resolve_search_roots
            search_roots = resolve_search_roots(candidate_data if isinstance(candidate_data, dict) else None)
        except Exception:
            search_roots = [os.getcwd()]
        for root in search_roots:
            cand_path = os.path.join(root, res_file)
            if os.path.exists(cand_path):
                return cand_path
            applied_root = os.path.join(root, "APPLIED ON COMPANY WEBSITE")
            if os.path.exists(applied_root):
                for dirpath, _, filenames in os.walk(applied_root):
                    if res_file in filenames:
                        return os.path.join(dirpath, res_file)
        return None
