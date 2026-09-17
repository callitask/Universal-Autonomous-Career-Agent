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
# ==============================================================================

import time
from typing import Any, Dict, List, Optional


class DOMHelpers:
    """
    Robust DOM helper methods for modern Single-Page ATS Applications (Oracle JET, React, Angular).
    """

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
    def extract_form_schema(page: Any) -> Dict[str, Any]:
        """
        Inspects the active page DOM and returns a comprehensive structured catalog
        of all inputs, textareas, selects, radio groups, checkboxes, honeypots, and buttons.
        """
        script = """() => {
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

            // Form controls
            const controls = document.querySelectorAll('input, textarea, select');
            controls.forEach((el, idx) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const isVisible = style.display !== 'none' && 
                                  style.visibility !== 'hidden' && 
                                  style.opacity !== '0' && 
                                  rect.width > 0 && rect.height > 0;
                
                // Find associated label text
                let labelText = '';
                if (el.id) {
                    const l = document.querySelector(`label[for="${el.id}"]`);
                    if (l) labelText = l.innerText?.trim();
                }
                if (!labelText) {
                    const parentLabel = el.closest('label');
                    if (parentLabel) labelText = parentLabel.innerText?.trim();
                }
                if (!labelText) {
                    labelText = el.getAttribute('aria-label') || el.placeholder || '';
                }

                results.inputs.push({
                    index: idx,
                    tagName: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || (el.tagName.toLowerCase() === 'textarea' ? 'textarea' : 'text'),
                    name: el.getAttribute('name') || '',
                    id: el.getAttribute('id') || '',
                    className: el.className || '',
                    placeholder: el.placeholder || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    labelText: labelText,
                    value: el.value || '',
                    checked: el.checked || false,
                    required: el.required || el.getAttribute('aria-required') === 'true',
                    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                    readOnly: el.readOnly || false,
                    isVisible: isVisible,
                    styleSnippet: `display:${style.display}; visibility:${style.visibility}; opacity:${style.opacity}`
                });
            });

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
            return page.evaluate(script)
        except Exception as e:
            return {"error": str(e), "url": getattr(page, "url", "")}
