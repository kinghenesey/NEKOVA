"""
Phase 18 — Standard Library in NEKOVA
Tests for .nk stdlib modules: math, string, file, date
"""
import unittest
import sys
import io
import re
import os
import tempfile

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.stdlib.nk_loader import clear_cache
from nekova.ai import memory_store as _mem_store


def run(source: str) -> str:
    _mem_store._memory.clear()
    clear_cache()
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    interp = Interpreter()
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        interp.run(ast)
    finally:
        sys.stdout = old
    return re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue()).strip()


# ── nk_loader ─────────────────────────────────────────────────

class TestNkLoader(unittest.TestCase):

    def test_math_nk_exists(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertTrue(has_nk_module("math"))

    def test_string_nk_exists(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertTrue(has_nk_module("string"))

    def test_file_nk_exists(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertTrue(has_nk_module("file"))

    def test_date_nk_exists(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertTrue(has_nk_module("date"))

    def test_unknown_module_false(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertFalse(has_nk_module("nonexistent"))

    def test_math_nk_exports(self):
        from nekova.stdlib.nk_loader import load_nk_module
        ns = load_nk_module("math")
        for name in ["clamp", "lerp", "factorial", "gcd", "is_even", "pi", "e"]:
            self.assertIn(name, ns, f"missing: {name}")

    def test_string_nk_exports(self):
        from nekova.stdlib.nk_loader import load_nk_module
        ns = load_nk_module("string")
        for name in ["pad_left", "pad_right", "truncate", "is_palindrome", "capitalize"]:
            self.assertIn(name, ns, f"missing: {name}")

    def test_load_module_merges_nk_and_python(self):
        """use math should have both Python (sqrt) and .nk (clamp) exports."""
        from nekova.stdlib import load_module
        ns = load_module("math")
        self.assertIn("sqrt", ns)    # from Python math_module.py
        self.assertIn("clamp", ns)   # from math.nk
        self.assertIn("pi", ns)      # from math.nk (overrides Python)

    def test_nk_priority_over_python(self):
        """math.nk's pi should be a float string from NEKOVA, not Python's float."""
        from nekova.stdlib import load_module
        ns = load_module("math")
        # pi is defined in math.nk as a let — it wins over Python math_module.py
        self.assertAlmostEqual(float(ns["pi"]), 3.14159, places=4)


# ── math.nk ───────────────────────────────────────────────────

class TestMathNk(unittest.TestCase):

    def test_pi_constant(self):
        out = run("use math\nshow pi")
        self.assertIn("3.14", out)

    def test_e_constant(self):
        out = run("use math\nshow e")
        self.assertIn("2.71", out)

    def test_clamp_below(self):
        out = run("use math\nshow clamp(-5, 0, 10)")
        self.assertEqual(out, "0")

    def test_clamp_above(self):
        out = run("use math\nshow clamp(15, 0, 10)")
        self.assertEqual(out, "10")

    def test_clamp_within(self):
        out = run("use math\nshow clamp(5, 0, 10)")
        self.assertEqual(out, "5")

    def test_lerp(self):
        out = run("use math\nshow lerp(0, 100, 0.5)")
        self.assertEqual(out, "50.0")

    def test_factorial_5(self):
        out = run("use math\nshow factorial(5)")
        self.assertEqual(out, "120")

    def test_factorial_0(self):
        out = run("use math\nshow factorial(0)")
        self.assertEqual(out, "1")

    def test_factorial_10(self):
        out = run("use math\nshow factorial(10)")
        self.assertEqual(out, "3628800")

    def test_fibonacci(self):
        out = run("use math\nshow fibonacci(10)")
        self.assertEqual(out, "55")

    def test_is_even_true(self):
        out = run("use math\nshow is_even(4)")
        self.assertEqual(out, "true")

    def test_is_even_false(self):
        out = run("use math\nshow is_even(7)")
        self.assertEqual(out, "false")

    def test_is_odd(self):
        out = run("use math\nshow is_odd(3)")
        self.assertEqual(out, "true")

    def test_gcd(self):
        out = run("use math\nshow gcd(12, 8)")
        self.assertEqual(out, "4")

    def test_lcm(self):
        out = run("use math\nshow lcm(4, 6)")
        self.assertEqual(out, "12")

    def test_sign_positive(self):
        out = run("use math\nshow sign(42)")
        self.assertEqual(out, "1")

    def test_sign_negative(self):
        out = run("use math\nshow sign(-7)")
        self.assertEqual(out, "-1")

    def test_sign_zero(self):
        out = run("use math\nshow sign(0)")
        self.assertEqual(out, "0")

    def test_average(self):
        out = run("use math\nshow average([1, 2, 3, 4, 5])")
        self.assertEqual(out, "3.0")

    def test_product(self):
        out = run("use math\nshow product([1, 2, 3, 4])")
        self.assertEqual(out, "24")

    def test_map_range(self):
        out = run("use math\nshow map_range(5, 0, 10, 0, 100)")
        self.assertEqual(out, "50.0")

    def test_sqrt_still_works(self):
        """Python math primitives still available via use math."""
        out = run("use math\nshow sqrt(16)")
        self.assertIn("4", out)

    def test_floor_still_works(self):
        out = run("use math\nshow floor(3.9)")
        self.assertEqual(out, "3")

    def test_ceil_still_works(self):
        out = run("use math\nshow ceil(3.1)")
        self.assertEqual(out, "4")


# ── string.nk ─────────────────────────────────────────────────

class TestStringNk(unittest.TestCase):

    def test_repeat(self):
        out = run('use string\nshow repeat("ha", 3)')
        self.assertEqual(out, "hahaha")

    def test_repeat_zero(self):
        out = run('use string\nshow repeat("x", 0)')
        self.assertEqual(out, "")

    def test_pad_left(self):
        out = run('use string\nshow "[" + pad_left("5", 4) + "]"')
        self.assertEqual(out, "[   5]")

    def test_pad_right(self):
        out = run('use string\nshow "[" + pad_right("hi", 5) + "]"')
        self.assertEqual(out, "[hi   ]")

    def test_pad_left_custom_char(self):
        out = run('use string\nshow "[" + pad_left("7", 3, "0") + "]"')
        self.assertEqual(out, "[007]")

    def test_truncate_long(self):
        out = run('use string\nshow truncate("Hello World", 5)')
        self.assertEqual(out, "Hello...")

    def test_truncate_short(self):
        out = run('use string\nshow truncate("Hi", 10)')
        self.assertEqual(out, "Hi")

    def test_is_empty_true(self):
        out = run('use string\nshow is_empty("")')
        self.assertEqual(out, "true")

    def test_is_empty_false(self):
        out = run('use string\nshow is_empty("x")')
        self.assertEqual(out, "false")

    def test_capitalize(self):
        out = run('use string\nshow capitalize("hello")')
        self.assertEqual(out, "Hello")

    def test_reverse(self):
        out = run('use string\nshow reverse("hello")')
        self.assertEqual(out, "olleh")

    def test_is_palindrome_true(self):
        out = run('use string\nshow is_palindrome("racecar")')
        self.assertEqual(out, "true")

    def test_is_palindrome_false(self):
        out = run('use string\nshow is_palindrome("hello")')
        self.assertEqual(out, "false")

    def test_starts_with_true(self):
        out = run('use string\nshow starts_with("hello", "hel")')
        self.assertEqual(out, "true")

    def test_starts_with_false(self):
        out = run('use string\nshow starts_with("hello", "world")')
        self.assertEqual(out, "false")

    def test_ends_with_true(self):
        out = run('use string\nshow ends_with("hello", "llo")')
        self.assertEqual(out, "true")

    def test_contains_true(self):
        out = run('use string\nshow contains("hello world", "world")')
        self.assertEqual(out, "true")

    def test_count_occurrences(self):
        # count_occurrences via split trick: split on 'a' gives 4 parts → 3 occurrences
        out = run('use string\nlet parts = "banana".split("a")\nshow len(parts) - 1')
        self.assertEqual(out, "3")


# ── file.nk ───────────────────────────────────────────────────

class TestFileNk(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Forward slashes prevent backslash escape issues in NEKOVA string literals
        raw = os.path.join(self.tmpdir, "test.txt")
        self.tmpfile = raw.replace("\\", "/")

    def test_write_and_read(self):
        src = (
            f'use file\n'
            f'write("{self.tmpfile}", "hello nekova")\n'
            f'let content = read("{self.tmpfile}")\n'
            f'show content'
        )
        out = run(src)
        self.assertEqual(out, "hello nekova")

    def test_exists_true(self):
        with open(self.tmpfile, "w") as f:
            f.write("x")
        out = run(f'use file\nshow exists("{self.tmpfile}")')
        self.assertEqual(out, "true")

    def test_exists_false(self):
        out = run('use file\nshow exists("/nonexistent/path/file.txt")')
        self.assertEqual(out, "false")

    def test_lines(self):
        with open(self.tmpfile, "w") as f:
            f.write("line1\nline2\nline3")
        src = (
            f'use file\n'
            f'let ls = lines("{self.tmpfile}")\n'
            f'show len(ls)'
        )
        out = run(src)
        self.assertEqual(out, "3")

    def test_append(self):
        src = (
            f'use file\n'
            f'write("{self.tmpfile}", "hello")\n'
            f'append("{self.tmpfile}", " world")\n'
            f'show read("{self.tmpfile}")'
        )
        out = run(src)
        self.assertEqual(out, "hello world")

    def test_line_count(self):
        with open(self.tmpfile, "w") as f:
            f.write("a\nb\nc\nd\ne")
        out = run(f'use file\nshow line_count("{self.tmpfile}")')
        self.assertEqual(out, "5")

    def test_delete(self):
        with open(self.tmpfile, "w") as f:
            f.write("x")
        self.assertTrue(os.path.exists(self.tmpfile))
        run(f'use file\ndelete("{self.tmpfile}")')
        self.assertFalse(os.path.exists(self.tmpfile))

    def test_copy(self):
        dest = os.path.join(self.tmpdir, "dest.txt").replace("\\", "/")
        out  = run(
            f'use file\n'
            f'write("{self.tmpfile}", "copy me")\n'
            f'copy("{self.tmpfile}", "{dest}")\n'
            f'show read("{dest}")'
        )
        self.assertEqual(out, "copy me")

# ── date.nk ───────────────────────────────────────────────────

class TestDateNk(unittest.TestCase):

    def test_today_format(self):
        out = run("use date\nshow today()")
        import re
        self.assertRegex(out, r"\d{4}-\d{2}-\d{2}")

    def test_now_format(self):
        out = run("use date\nshow now()")
        self.assertRegex(out, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_year(self):
        out = run('use date\nshow year("2025-06-26")')
        self.assertEqual(out, "2025")

    def test_month(self):
        out = run('use date\nshow month("2025-06-26")')
        self.assertEqual(out, "6")

    def test_day(self):
        out = run('use date\nshow day("2025-06-26")')
        self.assertEqual(out, "26")

    def test_add_days(self):
        out = run('use date\nshow add_days("2025-06-26", 7)')
        self.assertEqual(out, "2025-07-03")

    def test_diff_days(self):
        out = run('use date\nshow diff_days("2025-06-01", "2025-06-11")')
        self.assertEqual(out, "10")

    def test_is_weekend(self):
        out = run('use date\nshow is_weekend("2025-06-28")')  # Saturday
        self.assertEqual(out, "true")

    def test_is_weekday(self):
        out = run('use date\nshow is_weekday("2025-06-26")')  # Thursday
        self.assertEqual(out, "true")

    def test_day_of_week(self):
        out = run('use date\nshow day_of_week("2025-06-26")')
        self.assertEqual(out, "Thursday")

    def test_is_before(self):
        out = run('use date\nshow is_before("2025-01-01", "2025-12-31")')
        self.assertEqual(out, "true")

    def test_is_after(self):
        out = run('use date\nshow is_after("2025-12-31", "2025-01-01")')
        self.assertEqual(out, "true")

    def test_timestamp_is_int(self):
        out = run("use date\nshow timestamp() > 0")
        self.assertEqual(out, "true")

    def test_format_date(self):
        out = run('use date\nshow format("2025-06-26", "%B %d, %Y")')
        self.assertEqual(out, "June 26, 2025")


if __name__ == "__main__":
    unittest.main()