# =============================================================
# NEKOVA — Phase 5A Tests: Error Display
# =============================================================

import sys
import os
import io
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.cli.error_display import (
    display_error, _clean, _did_you_mean,
    _extract_token, _extract_location, _quick_fix,
)


def capture(fn, *args, **kwargs) -> str:
    """Capture stdout from a function call."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


class TestCleanMessage(unittest.TestCase):
    def test_replaces_str_with_text(self):
        self.assertIn("text", _clean("'str' type"))

    def test_replaces_int_with_number(self):
        self.assertIn("number", _clean("'int' value"))

    def test_replaces_bool_with_boolean(self):
        self.assertIn("boolean", _clean("'bool' flag"))

    def test_replaces_nonetype_with_null(self):
        self.assertIn("null", _clean("'NoneType' object"))

    def test_newline_becomes_dash(self):
        result = _clean("error\n  detail")
        self.assertNotIn("\n", result)

    def test_truncates_very_long_message(self):
        long = "x" * 300
        self.assertLessEqual(len(_clean(long)), 203)


class TestExtractToken(unittest.TestCase):
    def test_extracts_quoted_name(self):
        self.assertEqual(_extract_token("Variable 'foo' not found"), "foo")

    def test_extracts_first_name(self):
        self.assertEqual(_extract_token("'bar' and 'baz'"), "bar")

    def test_returns_empty_on_no_match(self):
        self.assertEqual(_extract_token("no quotes here"), "")

    def test_ignores_non_identifier_quotes(self):
        # Numbers in quotes shouldn't match identifier pattern
        result = _extract_token("got '42'")
        self.assertEqual(result, "")


class TestExtractLocation(unittest.TestCase):
    def test_extracts_line_and_col(self):
        line, col = _extract_location("Line 5, Column 12: error")
        self.assertEqual(line, 5)
        self.assertEqual(col, 12)

    def test_extracts_line_only(self):
        line, col = _extract_location("Line 3: something")
        self.assertEqual(line, 3)
        self.assertEqual(col, 0)

    def test_returns_zeros_on_no_match(self):
        line, col = _extract_location("no location info")
        self.assertEqual(line, 0)
        self.assertEqual(col, 0)


class TestDidYouMean(unittest.TestCase):
    def test_finds_close_match(self):
        result = _did_you_mean("naem", ["name", "age", "city"])
        self.assertIn("name", result)

    def test_no_false_positives(self):
        result = _did_you_mean("xyz", ["name", "age", "city"])
        self.assertEqual(result, [])

    def test_returns_at_most_three(self):
        candidates = [f"var{i}" for i in range(20)]
        result = _did_you_mean("var1", candidates)
        self.assertLessEqual(len(result), 3)

    def test_empty_candidates(self):
        self.assertEqual(_did_you_mean("foo", []), [])

    def test_exact_match_returned(self):
        result = _did_you_mean("name", ["name", "age"])
        self.assertIn("name", result)


class TestQuickFix(unittest.TestCase):
    def test_nameerror_suggests_let(self):
        fix = _quick_fix("NameError", "Variable 'myvar' not found", 5, 0)
        self.assertIn("myvar", fix)
        self.assertIn("let", fix)

    def test_typeerror_strict_suggests_toml(self):
        fix = _quick_fix("TypeError", "strict_types error", 1, 0)
        self.assertIn("strict_types", fix)

    def test_typeerror_suggests_any(self):
        fix = _quick_fix("TypeError", "type mismatch", 1, 0)
        self.assertIn("any", fix)

    def test_zerodivision_suggests_guard(self):
        fix = _quick_fix("ZeroDivisionError", "division by zero", 1, 0)
        self.assertIn("divisor", fix)

    def test_unknown_error_returns_empty(self):
        fix = _quick_fix("UnknownError", "something", 1, 0)
        self.assertEqual(fix, "")


class TestDisplayError(unittest.TestCase):
    def _run(self, **kwargs):
        return capture(display_error, **kwargs)

    def test_outputs_error_code(self):
        out = self._run(error_type="NameError", message="'foo' not found")
        self.assertIn("E001", out)

    def test_outputs_error_title(self):
        out = self._run(error_type="NameError", message="'foo' not found")
        self.assertIn("Variable Not Found", out)

    def test_outputs_type_error_code(self):
        out = self._run(error_type="TypeError", message="type mismatch")
        self.assertIn("E004", out)

    def test_outputs_parse_error_code(self):
        out = self._run(error_type="ParseError", message="unexpected token")
        self.assertIn("E003", out)

    def test_shows_filepath_and_line(self):
        out = self._run(
            error_type="NameError",
            message="'x' not found",
            filepath="src/main.nk",
            line=7,
        )
        self.assertIn("main.nk", out)
        self.assertIn("7", out)

    def test_shows_source_context(self):
        source = "let x = 1\nshow unknown\nshow x"
        out = self._run(
            error_type="NameError",
            message="'unknown' not found",
            source=source,
            line=2,
        )
        self.assertIn("show unknown", out)

    def test_shows_caret_for_source(self):
        source = "let x = 1\nshow bad_var\n"
        out = self._run(
            error_type="NameError",
            message="'bad_var' not found",
            source=source,
            line=2,
        )
        self.assertIn("^", out)

    def test_shows_hint(self):
        out = self._run(error_type="TypeError", message="int not text")
        self.assertIn("💡", out)

    def test_did_you_mean_shown(self):
        out = self._run(
            error_type="NameError",
            message="Variable 'naem' not found",
            variables={"name": "Emmanuel", "age": 25},
        )
        self.assertIn("name", out)

    def test_did_you_mean_not_shown_for_unrelated(self):
        out = self._run(
            error_type="NameError",
            message="Variable 'xyz123' not found",
            variables={"name": "Emmanuel", "age": 25},
        )
        self.assertNotIn("Did you mean", out)

    def test_unknown_error_type_handled(self):
        out = self._run(error_type="WeirdError", message="something odd")
        self.assertIn("E000", out)
        self.assertIn("WeirdError", out)

    def test_zero_division_error(self):
        out = self._run(error_type="ZeroDivisionError", message="division by zero")
        self.assertIn("E006", out)
        self.assertIn("zero", out.lower())

    def test_recursion_error(self):
        out = self._run(error_type="RecursionError", message="max depth")
        self.assertIn("E010", out)

    def test_no_source_still_renders(self):
        # Should not crash when source is empty
        out = self._run(error_type="RuntimeError", message="boom")
        self.assertIn("E005", out)

    def test_quick_fix_rendered(self):
        out = self._run(
            error_type="NameError",
            message="Variable 'myvar' not found",
            line=3,
        )
        self.assertIn("🔧", out)
        self.assertIn("myvar", out)

    def test_output_contains_separator(self):
        out = self._run(error_type="NameError", message="'x' missing")
        self.assertIn("━", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)