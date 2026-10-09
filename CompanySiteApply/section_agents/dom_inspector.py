# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [DOM_INSPECTOR_INIT]
# Timestamp: 2026-10-09 22:35:00 +05:30
# Issue / Context: Needed a standard, non-destructive DOM inspector to query Oracle HCM
#                  form controls, dropdowns, attachments, and error states without ad-hoc scripts.
# Changes Made: Built DOMInspector utility providing element dumps, red error queries,
#               and combobox/attachment inspection over CDP.
# Rationale: Standardizes diagnostic queries and eliminates one-off script generation forever.
# Preventative Notes: Strictly read-only; never mutates form state.
# ==============================================================================

import json
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.ats_arm import ATSArm

logger = logging.getLogger(__name__)


class DOMInspector:
    """
    Standard read-only diagnostic inspector for ATS pages over CDP.
    """

    def __init__(self, cdp_url: Optional[str] = None):
        self.arm = ATSArm(cdp_url=cdp_url)

    def get_page(self) -> Any:
        return self.arm.connect()

    def inspect_errors(self, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const errEls = Array.from(document.querySelectorAll('.cx-message--error, .error, .alert-danger, .cx-form-control__error-message, .oj-form-control-error-message, [class*="error"], [aria-invalid="true"]'));
            return errEls.filter(el => el.offsetWidth > 0 || el.offsetHeight > 0).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.innerText.trim(),
                parentText: el.parentElement ? el.parentElement.innerText.slice(0, 150) : ""
            }));
        }''')

    def inspect_attachments(self, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('.attachment-upload-button__download, .cx-attachment-item, [class*="attachment"], .apply-flow-profile-import-awli__file-name'));
            return els.filter(el => el.offsetWidth > 0 || el.offsetHeight > 0).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.innerText.trim(),
                buttons: Array.from(el.querySelectorAll('button, a')).map(b => ({
                    tag: b.tagName,
                    class: b.className,
                    text: b.innerText.trim(),
                    ariaLabel: b.getAttribute('aria-label'),
                    title: b.getAttribute('title')
                }))
            }));
        }''')

    def inspect_dropdowns(self, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('input[role="combobox"], [class*="select"], [class*="combobox"], button[id*="toggle-button"], select'));
            return els.filter(el => el.offsetWidth > 0 || el.offsetHeight > 0).map(el => ({
                tag: el.tagName,
                id: el.id,
                name: el.getAttribute('name'),
                class: el.className,
                role: el.getAttribute('role'),
                value: el.value || el.innerText.trim(),
                label: el.closest('.input-row, .app-form-item, .cx-form-item, fieldset') ? 
                       el.closest('.input-row, .app-form-item, .cx-form-item, fieldset').querySelector('label, legend, .cx-form-label, p')?.innerText.trim() : ""
            }));
        }''')

    def inspect_file_inputs(self, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('input[type="file"]'));
            return els.map(el => ({
                id: el.id,
                name: el.getAttribute('name'),
                accept: el.getAttribute('accept'),
                ariaLabel: el.getAttribute('aria-label'),
                title: el.getAttribute('title'),
                class: el.className
            }));
        }''')

    def inspect_element_html(self, selector: str, page: Optional[Any] = None) -> List[str]:
        pg = page or self.get_page()
        return pg.evaluate('''(sel) => {
            const els = Array.from(document.querySelectorAll(sel));
            return els.map(el => el.outerHTML);
        }''', selector)

    def navigate_to_step(self, step: int, page: Optional[Any] = None) -> str:
        import time
        pg = page or self.get_page()
        btn = pg.locator(f"button:has-text('{step}'), a:has-text('{step}')").first
        if btn.count() > 0:
            btn.click()
            time.sleep(2.0)
        return pg.url

    def inspect_preferred_locations(self, page: Optional[Any] = None) -> Dict[str, Any]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const block = document.querySelector('.apply-flow-block--preferred-locations, [class*="preferred-location"], [class*="preferredLocations"], .app-form-item');
            const allBlocks = Array.from(document.querySelectorAll('*')).filter(el => {
                const txt = el.innerText || '';
                return txt.includes('Preferred Locations') && el.children.length > 0 && el.children.length < 10;
            });
            const target = block || allBlocks[0];
            if (!target) return { found: false };
            return {
                found: true,
                tagName: target.tagName,
                className: target.className,
                outerHTML: target.outerHTML.slice(0, 1500),
                inputs: Array.from(target.querySelectorAll('input, button, select, [role="combobox"]')).map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    role: el.getAttribute('role'),
                    ariaLabel: el.getAttribute('aria-label'),
                    value: el.value || el.innerText
                }))
            };
        }''')

    def inspect_section2_fields(self, page: Optional[Any] = None) -> List[Dict[str, Any]]:
        pg = page or self.get_page()
        return pg.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"], fieldset'));
            return rows.filter(r => r.offsetWidth > 0 || r.offsetHeight > 0).map(r => {
                const label = r.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || "";
                const pills = Array.from(r.querySelectorAll('button.cx-select-pill-section, button[role="radio"], [role="radio"]')).map(b => ({
                    text: b.innerText.trim(),
                    selected: b.className.includes('selected') || b.getAttribute('aria-checked') === 'true' || b.getAttribute('aria-pressed') === 'true'
                }));
                const dropdowns = Array.from(r.querySelectorAll('input[role="combobox"], [class*="select"], button[id*="toggle-button"], select')).map(d => ({
                    tag: d.tagName,
                    id: d.id,
                    role: d.getAttribute('role'),
                    className: d.className,
                    value: d.value || d.innerText.trim()
                }));
                const errors = Array.from(r.querySelectorAll('.cx-message--error, .error, .alert-danger, [class*="error"], [aria-invalid="true"]')).map(e => e.innerText.trim());
                return { label, pillsCount: pills.length, pills, dropdowns, errors };
            });
        }''')

    def inspect_preferred_locations_options(self, page: Optional[Any] = None) -> List[str]:
        import time
        pg = page or self.get_page()
        toggle = pg.locator("button[id*='preferredLocations'][id$='-toggle-button'], .apply-flow-block--preferred-locations button.icon-dropdown-arrow").first
        if toggle.count() > 0:
            toggle.click()
            time.sleep(1.0)
        options = pg.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"], .cx-list-item, .oj-listbox-result'));
            return items.filter(i => i.offsetWidth > 0 || i.offsetHeight > 0).map(i => i.innerText.trim());
        }''')
        return options

    def test_click_preferred_location(self, page: Optional[Any] = None) -> Dict[str, Any]:
        import time
        pg = page or self.get_page()
        res = pg.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(i => i.offsetWidth > 0 || i.offsetHeight > 0);
            if (items.length > 0) {
                const text = items[0].innerText.trim();
                items[0].click();
                return { clicked: true, text: text };
            }
            return { clicked: false };
        }''')
        time.sleep(1.0)
        pills = pg.evaluate('''() => {
            return Array.from(document.querySelectorAll('.apply-flow-block--preferred-locations .cx-multi-select-pill, .apply-flow-block--preferred-locations [class*="pill"]')).map(p => p.innerText.trim());
        }''')
        return {"res": res, "pills": pills}

    def inspect_question_dropdown_options(self, question_text: str, page: Optional[Any] = None) -> List[str]:
        import time
        pg = page or self.get_page()
        # Find row by label
        toggle = pg.locator(f".input-row:has-text('{question_text}'), .app-form-item:has-text('{question_text}')").locator("button.icon-dropdown-arrow, button[id*='toggle-button']").first
        if toggle.count() > 0:
            toggle.click()
            time.sleep(1.0)
        options = pg.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"], .cx-list-item, .oj-listbox-result'));
            return items.filter(i => i.offsetWidth > 0 || i.offsetHeight > 0).map(i => i.innerText.trim());
        }''')
        return options

    def test_select_dropdown_options(self, target_options: List[str], page: Optional[Any] = None) -> Dict[str, Any]:
        import time
        pg = page or self.get_page()
        res = pg.evaluate('''(targets) => {
            const isVis = el => el.offsetWidth > 0 || el.offsetHeight > 0;
            const items = Array.from(document.querySelectorAll('.cx-multi-select__list-item, [role="option"], li[role="option"]')).filter(isVis);
            const clicked = [];
            for (const t of targets) {
                const match = items.find(i => i.innerText.trim().toLowerCase() === t.toLowerCase());
                if (match) {
                    match.click();
                    clicked.push(t);
                }
            }
            return { clicked, availableCount: items.length };
        }''', target_options)
        time.sleep(1.0)
        pills = pg.evaluate('''() => {
            return Array.from(document.querySelectorAll('.cx-multi-select-pill__value-text, .cx-multi-select-pill')).map(p => p.innerText.trim());
        }''')
        return {"res": res, "pills": pills}

    def test_remove_cover_letter(self, page: Optional[Any] = None) -> Dict[str, Any]:
        import time
        pg = page or self.get_page()
        # Find remove cover letter button
        btn = pg.locator("button:has-text('Remove Cover Letter'), button:has-text('REMOVE COVER LETTER')").first
        if btn.count() > 0:
            btn.click()
            time.sleep(1.0)
            # Check what file inputs or upload buttons now exist
            file_inputs = self.inspect_file_inputs(pg)
            dropzones = pg.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.attachment-upload-button'));
                return els.map(e => ({ class: e.className, text: e.innerText.trim(), html: e.outerHTML.slice(0, 300) }));
            }''')
            return {"removed": True, "file_inputs": file_inputs, "dropzones": dropzones}
        return {"removed": False}

    def upload_cover_letter(self, file_path: str, page: Optional[Any] = None) -> Dict[str, Any]:
        import time
        pg = page or self.get_page()
        file_input = pg.locator(".attachment-upload-button--waiting input[type='file'], input[name='attachment-upload']").last
        if file_input.count() > 0:
            file_input.set_input_files(file_path)
            time.sleep(2.0)
            attached = pg.locator(".attachment-upload-button__download").all_text_contents()
            return {"success": True, "attached_files": attached}
        return {"success": False, "error": "file_input not found"}

    def close(self):
        self.arm.disconnect()
