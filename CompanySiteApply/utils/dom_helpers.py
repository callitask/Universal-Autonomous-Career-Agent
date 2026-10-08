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
#
# [ENTRY #003]
# Term: [TRUSTED_COMBO_AND_FUZZY_MATCH]
# Timestamp: 2026-10-07 19:00:00 +05:30
# Issue / Context: JET combos ignored synthetic open gestures; exact-only matching failed gazetteer drift (Bangalore vs Bengaluru).
# Changes Made: match_option_score/pick_best_option pure scorer; location_aliases from platform_heuristics; select_jet_combo (skip-if-set, trusted mouse open, fuzzy+alias+AI pick, read-back verify).
# Rationale: Name drift resolved by score plus portal facts plus brain, never hardcoded cities.
# Preventative Notes: Never return success without read-back verification.
#
# [ENTRY #004]
# Term: [HUMAN_FLOW_COMBO]
# Timestamp: 2026-10-07 19:30:00 +05:30
# Issue / Context: Owner showed humans type-to-filter first and ask for alternate spellings when absent; routine opened-then-matched instead.
# Changes Made: select_jet_combo rewritten: per-want fragment typing, filtered-option fuzzy pick, ai_aliases secondary-names pass, click, read-back, type-commit fallback, honest failure.
# Rationale: Automation must mimic the human filtering flow, not fight the popup.
# Preventative Notes: Never skip the fragment-filter step; never accept an unverified value.
# [ENTRY #005]
# Term: [ERROR_DETECTION_HARDENING]
# Timestamp: 2026-10-08 18:37:00 +05:30
# Issue / Context: JPMC Oracle portal allowed advancing past Section 2 even with empty required combobox. Error detection missed .input-row--invalid.
# Changes Made: Added .input-row--invalid to FORM_ERROR_SELECTORS.
# Rationale: All ATS portal specific error classes must be centralized in the shared library so future nails/fingers don't miss them.
# Preventative Notes: Never advance without reading back required fields explicitly, even if error selectors return empty.
# ==============================================================================

import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


def _norm_token(text: str) -> str:
    """Lowercase alphanumeric token stream for name comparison."""
    return re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()


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
        ".input-row--invalid",
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

    #: Button texts that must NEVER be clicked by automation (destructive or
    #: dismissive controls). Checked case-insensitively against button text,
    #: aria-label, and class names before every scripted click.
    FORBIDDEN_BUTTON_TOKENS = (
        'clear', 'close', 'remove', 'dismiss', 'discard', 'cancel', 'back',
    )

    @staticmethod
    def safe_click_button(page: Any, allow_texts: List[str],
                          scope_css: Optional[str] = None) -> Tuple[bool, str]:
        """
        Clicks a button ONLY when its visible text is on the allowlist and
        carries no forbidden token (clear/X/close/remove/dismiss/back/
        discard/cancel). Bare 'x'/'x' single-letter buttons never qualify.
        Returns (True, clicked_text) or (False, reason). This is the ONLY
        sanctioned way to click wizard/navigation buttons.
        """
        allow = [str(a).strip().lower() for a in (allow_texts or [])
                 if str(a).strip()]
        if not allow:
            return False, 'empty-allowlist'
        try:
            found = page.evaluate("""(args) => {
                const [allowList, scopeCss, forbidden] = args;
                const root = scopeCss
                    ? (document.querySelector(scopeCss) || document) : document;
                const norm = s => (s || '').trim().toLowerCase();
                const cands = Array.from(root.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]'))
                    .filter(el => el.offsetWidth > 0 && !el.disabled
                        && el.getAttribute('aria-disabled') !== 'true');
                for (const el of cands) {
                    const text = norm(el.innerText || el.value || '');
                    if (!text || text.length === 1) continue;
                    if (forbidden.some(f => text.includes(f))) continue;
                    const cls = norm(el.className) + ' '
                        + norm(el.getAttribute('aria-label') || '');
                    if (forbidden.some(f => f.length > 2 && cls.includes(f))) continue;
                    if (allowList.some(a => text === a || text.startsWith(a + ' '))) {
                        el.scrollIntoView({block: 'center'});
                        el.click();
                        return text.slice(0, 40);
                    }
                }
                return null;
            }""", [allow, scope_css,
                    list(DOMHelpers.FORBIDDEN_BUTTON_TOKENS)])
            if found:
                return True, 'clicked:' + str(found)
            return False, 'no-allowed-button-visible'
        except Exception as e:
            return False, 'err:' + str(e).splitlines()[0][:120]

    @staticmethod
    def match_option_score(want: str, candidate: str) -> int:
        """
        Pure name-similarity score (0-100) between a wanted value and one
        visible option. Handles official-spelling drift (Bangalore vs
        Bengaluru, Karnataka) without hardcoding any city: exact 100,
        option-starts-with-want 85, want-first-token inside option 70,
        strongest shared-token overlap 40-60, else 0.
        """
        w, c = _norm_token(want), _norm_token(candidate)
        if not w or not c:
            return 0
        if w == c:
            return 100
        if c == w or c.startswith(w + ' '):
            return 85
        w_first = w.split(' ')[0]
        if w_first and w_first in c.split(' '):
            return 70
        w_set, c_set = set(w.split(' ')), set(c.split(' '))
        overlap = w_set & c_set - {'and', 'the', 'of', 'de', 'la'}
        if overlap:
            return 40 + min(20, 10 * len(overlap))
        return 0

    @staticmethod
    def pick_best_option(wants: List[str], options: List[str],
                         threshold: int = 60) -> Optional[str]:
        """
        Picks the visible option best matching the ordered want list
        (profile's own spellings first). Returns None when nothing clears
        the threshold so the caller defers to AI or the operator.
        """
        best, best_score = None, 0
        for want in wants:
            for opt in options:
                score = DOMHelpers.match_option_score(want, opt)
                # Earlier wants (profile-primary spellings) win ties.
                if score > best_score and score >= threshold:
                    best, best_score = opt, score
            if best_score >= 85:
                break
        return best

    @staticmethod
    def location_aliases() -> Dict[str, List[str]]:
        """
        Portal gazetteer facts from core/knowledge/platform_heuristics.json
        (official spellings portals use, e.g. Bengaluru). Platform knowledge,
        not candidate data — safe to ship; extend the JSON, never this code.
        """
        try:
            import json
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent.parent
            data = json.loads(
                (root / 'core' / 'knowledge' / 'platform_heuristics.json'
                 ).read_text(encoding='utf-8'))
            aliases = (data.get('platforms', {}).get('oracle_hcm', {})
                       .get('location_aliases', {}))
            return dict(aliases) if isinstance(aliases, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def select_jet_combo(page: Any, input_name: str, wants: List[str],
                         ai_resolver: Optional[Callable[[List[str]], Optional[str]]] = None,
                         ai_aliases: Optional[Callable[[str, str, List[str]], List[str]]] = None,
                         field_label: str = '',
                         timeout_ms: int = 8000,
                         verbose: bool = False) -> Tuple[bool, str]:
        """
        Human-flow JET/CX combobox routine with persistence verification:
        1. skip-if-set (read back the live value first);
        2. per spelling: focus, clear, type the first few letters ONLY
           (never full text — the portal filters on fragments), read the
           filtered options, fuzzy-pick with gazetteer aliases expanded;
        3. no confident pick -> AI secondary-names pass;
        4. keyboard-select (ArrowDown highlights the first option, Enter
           commits) with mouse-click fallback; clear/X controls excluded;
        5. settle polling + read-back proof; honest failure otherwise.
        The AI always receives field label + wanted value + visible options.
        Returns (True, value) only when the value demonstrably stuck.
        """
        import time as _t

        def _log(msg):
            if verbose:
                print(f'[select_jet_combo:{input_name}] {msg}', flush=True)
        wants = [str(w) for w in (wants or []) if str(w).strip()]
        if not wants:
            return False, 'no-want-values'

        def _read():
            try:
                return page.evaluate(
                    "(nm) => { const i = document.querySelector("
                    "`[name=\"${nm}\"]`);"
                    " return i ? (i.value || '') : 'missing'; }", input_name)
            except Exception as e:
                print('[_read exception]', e)
                return 'missing'

        def _combo_parts():
            # Mapped anatomy (CX bespoke combobox, verified live 2026-10-07):
            # input[role=combobox][aria-controls=<id>-listbox] +
            # toggle button[aria-controls=<same>] + listbox#<id>. IDs are
            # per-render (city-44-*) so they are READ from aria-controls,
            # never hardcoded. No JET/jQuery/KO involved.
            try:
                return page.evaluate("""(nm) => {
                    const input = document.querySelector(`[name=\"${nm}\"]`);
                    if (!input) return null;
                    const lb = input.getAttribute('aria-controls') || '';
                    const cont = input.closest(
                        '.cx-select-container, .input-row, '
                        + '.oj-form-layout-element') || input.parentElement;
                    let tog = null;
                    if (lb) {
                        tog = cont.querySelector(
                            '[aria-controls="' + lb + '"]');
                    }
                    if (!tog) {
                        tog = cont.querySelector(
                            'button, [role="button"], .icon-dropdown-arrow, '
                            + '[id$="-toggle-button"]');
                    }
                    return {listbox: lb || null,
                            toggleText:
                                (tog ? (tog.id || tog.className || '?') : null)
                                .toString().slice(0, 60)};
                }""", input_name)
            except Exception:
                return None

        def _visible_options(listbox_id=None):
            try:
                sel = ('#' + listbox_id + ' [role="option"], '
                       '#' + listbox_id + ' [role="gridcell"], '
                       '#' + listbox_id + ' li') if listbox_id else (
                    '[role="listbox"] [role="option"], '
                    '[role="listbox"] [role="gridcell"], '
                    '.cx-select__list-item, .cx-select-list-item')
                return page.evaluate("""(sel) => Array.from(
                    document.querySelectorAll(sel))
                    .filter(el => el.offsetWidth > 0
                        && !/clear|close|remove|dismiss/i.test(
                            (el.className || '') + ' '
                            + (el.getAttribute('aria-label') || ''))
                        && !/^[x×]$/i.test((el.innerText || '').trim()))
                    .map(el => (el.innerText || '').trim()).filter(Boolean)""",
                    sel)
            except Exception:
                return []

        def _expanded(want):
            out = [want]
            for key, vals in DOMHelpers.location_aliases().items():
                if DOMHelpers.match_option_score(want, key) >= 70:
                    out.extend([v for v in vals if v not in out])
            return out

        def _click_pick(pick):
            try:
                ok = page.evaluate("""(t) => {
                    const norm = s => (s || '').trim().toLowerCase();
                    const items = Array.from(document.querySelectorAll(
                        '[role="option"], [role="gridcell"], '
                        + '.cx-select__list-item, .cx-select-list-item'))
                        .filter(el => el.offsetWidth > 0
                            && norm(el.innerText) === norm(t)
                            && !/clear|close|remove|dismiss/i.test(
                                (el.className || '') + ' '
                                + (el.getAttribute('aria-label') || '')));
                    if (items.length) { items[0].click(); return true; }
                    return false;
                }""", pick)
                _t.sleep(0.8)
                try:
                    page.keyboard.press('Escape')
                except Exception:
                    pass
                return bool(ok)
            except Exception:
                return False

        def _confirmed(expanded):
            final = _read()
            return (final.strip() and final != 'missing' and any(
                DOMHelpers.match_option_score(w, final) >= 70
                for w in expanded))

        def _confirmed_retry(expanded, tries=3):
            # Re-renders briefly detach the input; a single read can catch
            # 'missing' while the typed value is actually committing.
            for _ in range(tries):
                if _confirmed(expanded):
                    return True
                _t.sleep(1.0)
            return _confirmed(expanded)

        def _visible_pills():
            try:
                return page.evaluate("""() => Array.from(
                    document.querySelectorAll(
                        '.cx-multi-select-pill, [class*="multi-select-pill"]'))
                    .filter(el => el.offsetWidth > 0)
                    .map(el => (el.innerText || '').trim())
                    .filter(Boolean)""")
            except Exception:
                return []

        def _pill_settled(expanded):
            for pill in _visible_pills():
                if any(DOMHelpers.match_option_score(w, pill) >= 70
                       for w in expanded):
                    return True
            return False

        try:
            cur = _read()
            if cur and cur != 'missing':
                for w in wants:
                    if DOMHelpers.match_option_score(w, cur) >= 70:
                        return True, 'already-set:' + cur[:40]
            # Multi-select: a matching visible pill means done (the input is
            # destroyed on selection, so input reads stay 'missing').
            for want in wants:
                if any(DOMHelpers.match_option_score(want, pill) >= 70
                       for pill in _visible_pills()):
                    return True, 'already-set-pill'
            for want in wants:
                expanded = _expanded(want)
                parts = _combo_parts()
                listbox_id = (parts or {}).get('listbox')
                # Mapped open first: real mouse on the toggle that shares the
                # input's aria-controls id (trusted event; synthetic ones are
                # ignored by this component).
                if parts:
                    try:
                        pt = page.evaluate("""(nm) => {
                            const input = document.querySelector(
                                `[name=\"${nm}\"]`);
                            const lb = input.getAttribute('aria-controls');
                            const cont = input.closest(
                                '.cx-select-container, .input-row, '
                                + '.oj-form-layout-element')
                                || input.parentElement;
                            const tog = (lb && cont.querySelector(
                                '[aria-controls="' + lb + '"]'))
                                || cont.querySelector(
                                    'button, [role="button"], '
                                    + '.icon-dropdown-arrow');
                            if (!tog) return null;
                            tog.scrollIntoView({block: 'center'});
                            const r = tog.getBoundingClientRect();
                            if (r.width <= 0) return null;
                            return [r.x + r.width / 2, r.y + r.height / 2];
                        }""", input_name)
                        if pt:
                            page.mouse.click(pt[0], pt[1])
                            _t.sleep(1.0)
                    except Exception:
                        pass
                # Focus + wait: some dropdowns pre-show their list with no
                # typing at all. Analyze BEFORE typing anything — typing
                # first would filter away the answer we need.
                try:
                    page.evaluate("""(nm) => {
                        const i = document.querySelector(`[name=\"${nm}\"]`);
                        i.scrollIntoView({block: 'center'});
                        i.focus();
                        i.click();
                    }""", input_name)
                    _t.sleep(1.2)
                except Exception:
                    pass
                options = _visible_options(listbox_id)
                _log(f"preshown options={len(options)}")
                pick = None
                SMALL_SET = 6
                if options and len(options) <= SMALL_SET:
                    # Small safe set: analyze first. Fuzzy, else the full
                    # list goes to the brain — no typing involved.
                    pick = DOMHelpers.pick_best_option(expanded, options)
                    if pick is not None:
                        _log(f'pick-preshown={pick}')
                    elif ai_resolver is not None:
                        try:
                            cand_pick = ai_resolver(options)
                        except Exception:
                            cand_pick = None
                        if cand_pick and cand_pick in options:
                            pick = cand_pick
                            _log(f'pick-ai-full={pick}')
                if pick is None:
                    # Big list or nothing shown: type-to-filter, one fragment
                    # pass per spelling (profile spelling can filter OUT the
                    # portal spelling, so every spelling gets its own pass).
                    spell_tried = []
                    for spell in expanded:
                        frag = spell.split(',')[0].strip()[:4]
                        if not frag or frag in spell_tried:
                            continue
                        spell_tried.append(frag)
                        try:
                            page.evaluate("""(nm) => {
                                const i = document.querySelector(
                                    `[name=\"${nm}\"]`);
                                i.scrollIntoView({block: 'center'});
                                i.focus();
                            }""", input_name)
                            _t.sleep(0.4)
                            page.keyboard.press('Control+A')
                            page.keyboard.press('Backspace')
                            _t.sleep(0.2)
                            page.keyboard.type(frag, delay=50)
                            _t.sleep(1.2)
                        except Exception:
                            continue
                        options = _visible_options(listbox_id)
                        _log(f"frag='{frag}' options={len(options)}")
                        pick = DOMHelpers.pick_best_option(expanded, options)
                        if pick is not None:
                            _log(f'pick={pick}')
                            break
                # Human step 2: exact answer absent -> AI secondary names.
                # Runs even when the filter returned nothing: the fragment
                # itself may be the wrong spelling. Each alternate is TYPED
                # and re-matched, exactly like the human would.
                if pick is None and ai_aliases is not None:
                    try:
                        alternates = ai_aliases(
                            field_label or input_name, want,
                            options[:25]) or []
                    except Exception:
                        alternates = []
                    _log(f'alternates={alternates}')
                    for alt in alternates:
                        alt = str(alt).strip()
                        if not alt or alt in expanded:
                            continue
                        expanded.append(alt)
                        try:
                            page.evaluate("""(nm) => {
                                const i = document.querySelector(
                                    `[name=\"${nm}\"]`);
                                i.scrollIntoView({block: 'center'});
                                i.focus();
                            }""", input_name)
                            _t.sleep(0.4)
                            page.keyboard.press('Control+A')
                            page.keyboard.press('Backspace')
                            _t.sleep(0.2)
                            page.keyboard.type(
                                alt.split(',')[0].strip()[:6], delay=50)
                            _t.sleep(1.2)
                        except Exception:
                            continue
                        options = _visible_options(listbox_id)
                        pick = DOMHelpers.pick_best_option([alt], options)
                        if pick is None:
                            pick = DOMHelpers.pick_best_option(
                                expanded, options)
                        if pick is not None:
                            _log(f'pick-alias={pick}')
                            break
                if pick is None and ai_resolver is not None and options:
                    try:
                        cand_pick = ai_resolver(options)
                    except Exception:
                        cand_pick = None
                    if cand_pick and cand_pick in options:
                        pick = cand_pick
                # Keyboard select (primary): ArrowDown moves the highlight
                # from the input (never the clear-X button) onto the first
                # filtered option; Enter commits it. No mouse coordinates,
                # so there is nothing for focus to land wrongly on.
                def _keyboard_pick(pick):
                    try:
                        page.keyboard.press('ArrowDown')
                        _t.sleep(0.8)
                    except Exception:
                        return False
                    try:
                        active = page.evaluate("""(nm) => {
                            const input = document.querySelector(
                                `[name=\"${nm}\"]`);
                            const ad = input.getAttribute('aria-activedescendant');
                            const el = ad ? document.getElementById(ad) : null;
                            const norm = s => (s || '').trim().toLowerCase();
                            if (el && el.offsetWidth > 0) {
                                return {highlighted:
                                    (el.innerText || '').trim().slice(0, 60)};
                            }
                            return {highlighted: null};
                        }""", input_name)
                    except Exception:
                        return False
                    hl = (active or {}).get('highlighted')
                    if hl and DOMHelpers.match_option_score(pick, hl) >= 85:
                        try:
                            page.keyboard.press('Enter')
                            _t.sleep(1.0)
                            return True
                        except Exception:
                            return False
                    return False

                if pick is None:
                    try:
                        page.keyboard.press('Escape')
                    except Exception:
                        pass
                    continue
                if not _keyboard_pick(pick):
                    _log('keyboard-pick-failed; mouse fallback')
                    if not _click_pick(pick):
                        try:
                            page.keyboard.press('Escape')
                        except Exception:
                            pass
                        continue
                _log(f'pick-clicked:{pick[:40]}')
                # Settle + commit: dispatch model events and blur WITHOUT Tab
                # (Tab walks focus onto the adjacent clear-X button on CX
                # combos and a subsequent keypress can wipe the value).
                try:
                    page.evaluate("""(nm) => {
                        const i = document.querySelector(`[name=\"${nm}\"]`);
                        i.dispatchEvent(new Event('input', {bubbles: true}));
                        i.dispatchEvent(new Event('change', {bubbles: true}));
                        i.dispatchEvent(new Event('blur', {bubbles: true}));
                    }""", input_name)
                except Exception:
                    pass
                settled = False
                last = ''
                # Server round-trips can delay the commit well past the
                # click; poll generously instead of rushing to retype (which
                # used to overwrite good portal selections with raw text).
                # The component may also DESTROY and recreate the input on
                # commit ('missing' reads); keep polling through that.
                miss_streak = 0
                for _ in range(15):
                    _t.sleep(1.0)
                    last = _read()
                    _log(f'settle-read={last!r:.40}')
                    if last == 'missing':
                        miss_streak += 1
                        if miss_streak > 8:
                            break
                        continue
                    miss_streak = 0
                    if last.strip() and any(
                            DOMHelpers.match_option_score(w, last) >= 70
                            for w in expanded):
                        if last == _read():
                            settled = True
                            break
                if settled:
                    return True, 'selected:' + last.strip()[:40]
                # Missing-input settle: the node may have been recreated with
                # the committed value after our last poll; one final check.
                final_check = _read()
                if final_check.strip() and final_check != 'missing' and any(
                        DOMHelpers.match_option_score(w, final_check) >= 70
                        for w in expanded):
                    return True, 'selected-late:' + final_check.strip()[:40]
                _log(f'settle-failed last={last!r:.40}')
            # Last resort: full-text type + blur commit per want, using the
            # portal spelling when one was picked (never raw over good picks).
            # Every spelling is tried: the raw profile text may itself be
            # rejected while the gazetteer spelling commits cleanly.
            for want in wants:
                expanded = _expanded(want)
                type_text = want
                for w in expanded:
                    if DOMHelpers.match_option_score(w, _read()) >= 85:
                        type_text = w
                        break
                for text in ([type_text] +
                             [w for w in expanded if w != type_text]):
                    try:
                        page.evaluate("""(args) => {
                            const [nm, val] = args;
                            const i = document.querySelector(`[name=\"${nm}\"]`);
                            i.scrollIntoView({block: 'center'});
                            i.focus();
                        }""", [input_name, text])
                        _t.sleep(0.4)
                        page.keyboard.press('Control+A')
                        page.keyboard.press('Backspace')
                        _t.sleep(0.2)
                        page.keyboard.type(text, delay=40)
                        _t.sleep(1.0)
                        page.evaluate("""(nm) => {
                            const i = document.querySelector(`[name=\"${nm}\"]`);
                            i.dispatchEvent(new Event('change', {bubbles: true}));
                            i.dispatchEvent(new Event('blur', {bubbles: true}));
                        }""", input_name)
                        _t.sleep(0.8)
                    except Exception:
                        continue
                    if _confirmed_retry(_expanded(want)):
                        return True, 'type-committed:' + _read().strip()[:40]
                try:
                    page.keyboard.press('Escape')
                except Exception:
                    pass
            return False, 'no-option-confirmed'
        except Exception as e:
            return False, 'err:' + str(e).splitlines()[0][:120]


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
                        el = loc.nth(i)
                        if not el.is_visible():
                            continue
                        txt = (el.inner_text() or "").strip()
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
