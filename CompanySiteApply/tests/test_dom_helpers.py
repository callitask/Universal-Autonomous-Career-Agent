# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST]
# Timestamp: 2026-10-07 17:00:00 +05:30
# Issue / Context: Shared DOMHelpers (schema scan, semantic locator, error guard,
#   step verification, resume resolver) need regression cover without a live browser.
# Changes Made: Stub page/locator doubles exercising collect_form_errors,
#   verify_step_advanced, find_field_by_label escaping, resolve_resume_file, and
#   static selector-hygiene assertions (no hashed classes in scan sets).
# Rationale: Future fingers/nails inherit these helpers; tests pin the contracts.
# Preventative Notes: Uses synthetic dummy data; zero candidate PII. Never add
#   live profile names, keys, or URLs here.
# ==============================================================================

import os
import re
import tempfile
import unittest

from CompanySiteApply.utils.dom_helpers import DOMHelpers


class _StubLocator:
    def __init__(self, texts=(), visible=True, count=None):
        self._texts = list(texts)
        self._visible = visible
        self._count = len(self._texts) if count is None else count

    def count(self):
        return self._count

    @property
    def first(self):
        return self

    def nth(self, i):
        stub = _StubLocator([self._texts[i]] if i < len(self._texts) else [])
        return stub

    def is_visible(self):
        return self._visible

    def is_disabled(self):
        return False

    def inner_text(self):
        return self._texts[0] if self._texts else ""

    def locator(self, _sel):
        return self


class _StubPage:
    def __init__(self, url="https://example.invalid/step/1", errors=(), body=""):
        self.url = url
        self._errors = list(errors)
        self._body = body
        self.locators = []

    def locator(self, sel):
        self.locators.append(sel)
        if "body" in sel:
            return _StubLocator([self._body])
        return _StubLocator(list(self._errors))


class TestDOMHelpers(unittest.TestCase):

    def test_selector_sets_have_no_hashed_classes(self):
        # CSS-module hashes look like css-1y8298 / styles_btn-secondary__2AsIP:
        # a hyphen segment starting with a digit, or a __ segment containing a
        # digit. Plain BEM (app-form-item__error) and framework classes
        # (oj-invalid, field-validation-error) must NOT trip this.
        hashed = re.compile(r"-[a-zA-Z]*\d[a-zA-Z0-9]{4,}|__[a-zA-Z0-9-]*[0-9][a-zA-Z0-9-]*")
        for sel in DOMHelpers.FORM_CONTROL_SELECTORS + DOMHelpers.FORM_ERROR_SELECTORS:
            self.assertIsNone(hashed.search(sel),
                              f"Hashed CSS-module class in shared selector: {sel}")
        joined = ",".join(DOMHelpers.FORM_CONTROL_SELECTORS)
        for token in ("combobox", "radiogroup", "oj-select-single", "oj-combobox-one",
                      "oj-input-date", "data-automation-id"):
            self.assertIn(token, joined)

    def test_collect_form_errors_aggregates_and_dedupes(self):
        page = _StubPage(errors=["Field is required", "Field is required", ""])
        errors = DOMHelpers.collect_form_errors(page, limit=5)
        self.assertEqual(errors, ["Field is required"])

    def test_verify_step_advanced_url_change_clean(self):
        page = _StubPage(url="https://example.invalid/step/2", errors=[])
        advanced, errors = DOMHelpers.verify_step_advanced(
            page, "https://example.invalid/step/1")
        self.assertTrue(advanced)
        self.assertEqual(errors, [])

    def test_verify_step_advanced_same_url_with_errors(self):
        page = _StubPage(url="https://example.invalid/step/1",
                         errors=["Select a value"])
        advanced, errors = DOMHelpers.verify_step_advanced(
            page, "https://example.invalid/step/1")
        self.assertFalse(advanced)
        self.assertIn("Select a value", errors)

    def test_verify_step_advanced_same_url_no_signal(self):
        page = _StubPage(url="https://example.invalid/step/1", errors=[])
        advanced, errors = DOMHelpers.verify_step_advanced(
            page, "https://example.invalid/step/1")
        self.assertFalse(advanced)
        self.assertTrue(errors)

    def test_verify_step_advanced_ok_marker(self):
        page = _StubPage(url="https://example.invalid/step/1", errors=[],
                         body="Thank you for applying. Reference 123.")
        advanced, errors = DOMHelpers.verify_step_advanced(
            page, "https://example.invalid/step/1",
            ok_markers=["thank you for applying"])
        self.assertTrue(advanced)
        self.assertEqual(errors, [])

    def test_find_field_by_label_escapes_quotes(self):
        page = _StubPage()
        self.assertIsNone(DOMHelpers.find_field_by_label(page, ""))
        DOMHelpers.find_field_by_label(page, "O'Brien's status")
        built = " ".join(page.locators)
        self.assertNotIn("O'Brien", built.replace("\\'", ""))
        self.assertIn("O\\'Brien", built)

    def test_find_field_by_label_none_when_hidden(self):
        class HiddenPage(_StubPage):
            def locator(self, sel):
                if sel.startswith("label"):
                    return _StubLocator(["Gender"], visible=False)
                return _StubLocator([])
        self.assertIsNone(DOMHelpers.find_field_by_label(HiddenPage(), "gender"))

    def test_resolve_resume_file_absolute_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "Tailored.pdf")
            with open(target, "w", encoding="utf-8") as f:
                f.write("dummy")
            self.assertEqual(
                DOMHelpers.resolve_resume_file({}, resume_path=target), target)
            self.assertIsNone(DOMHelpers.resolve_resume_file({}, resume_path=None))
            self.assertIsNone(
                DOMHelpers.resolve_resume_file({"candidate": {}}))
            self.assertIsNone(
                DOMHelpers.resolve_resume_file(
                    {}, resume_path=os.path.join(tmp, "nope.pdf")))


if __name__ == "__main__":
    unittest.main()
