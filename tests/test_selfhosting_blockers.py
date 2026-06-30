# =============================================================
# NEKOVA Tests — Self-hosting Blocker Fixes
# Covers:
#   1. Number literals: scientific notation, hex, underscore sep
#   2. dict[key] = value  (index assignment)
#   3. match character/number ranges  (when 'a'..'z':)
# =============================================================
import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """Helper — run NEKOVA source and capture printed output."""
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


class TestNumberLiterals(unittest.TestCase):
    """Bug 31 / uncle fix: 1e5, 0xFF, 1_000_000 all failed."""

    # ── integers ──────────────────────────────────────────────
    def test_plain_integer(self):
        self.assertEqual(run("show 42"), "42")

    def test_plain_float(self):
        self.assertEqual(run("show 3.14"), "3.14")

    # ── underscore separators ──────────────────────────────────
    def test_underscore_integer(self):
        self.assertEqual(run("show 1_000"), "1000")

    def test_underscore_large(self):
        self.assertEqual(run("show 1_000_000"), "1000000")

    def test_underscore_float(self):
        self.assertEqual(run("show 1_234.567_8"), "1234.5678")

    # ── hex literals ───────────────────────────────────────────
    def test_hex_zero(self):
        self.assertEqual(run("show 0x0"), "0")

    def test_hex_ff(self):
        self.assertEqual(run("show 0xFF"), "255")

    def test_hex_uppercase(self):
        self.assertEqual(run("show 0XFF"), "255")

    def test_hex_deadbeef(self):
        self.assertEqual(run("show 0xDEADBEEF"), "3735928559")

    def test_hex_mixed_case(self):
        self.assertEqual(run("show 0xDeAdBeEf"), "3735928559")

    # ── scientific notation ────────────────────────────────────
    def test_sci_e0(self):
        self.assertEqual(run("show 1e0"), "1.0")

    def test_sci_e5(self):
        self.assertEqual(run("show 1e5"), "100000.0")

    def test_sci_uppercase_E(self):
        self.assertEqual(run("show 1E5"), "100000.0")

    def test_sci_plus_exponent(self):
        self.assertEqual(run("show 1e+3"), "1000.0")

    def test_sci_negative_exponent(self):
        self.assertEqual(run("show 1.5e-3"), "0.0015")

    def test_sci_float_base(self):
        self.assertEqual(run("show 2.5e2"), "250.0")

    def test_sci_large(self):
        self.assertEqual(run("show 1E10"), "10000000000.0")

    # ── used in arithmetic ─────────────────────────────────────
    def test_hex_in_arithmetic(self):
        self.assertEqual(run("show 0xFF + 1"), "256")

    def test_sci_in_arithmetic(self):
        self.assertEqual(run("show 1e3 + 500.0"), "1500.0")

    def test_underscore_in_arithmetic(self):
        self.assertEqual(run("show 1_000 * 2"), "2000")

    # ── stored in variables ────────────────────────────────────
    def test_hex_in_variable(self):
        self.assertEqual(run("let x = 0xFF\nshow x"), "255")

    def test_sci_in_variable(self):
        self.assertEqual(run("let x = 1e5\nshow x"), "100000.0")

    def test_underscore_in_variable(self):
        self.assertEqual(run("let x = 1_000_000\nshow x"), "1000000")


class TestIndexAssignment(unittest.TestCase):
    """Self-hosting blocker 1: dict[key] = value was a parse error."""

    # ── dict string keys ───────────────────────────────────────
    def test_dict_assign_new_key(self):
        src = 'let d = {}\nd["x"] = 99\nshow d["x"]'
        self.assertEqual(run(src), "99")

    def test_dict_assign_overwrite(self):
        src = 'let d = {name: "old"}\nd["name"] = "new"\nshow d["name"]'
        self.assertEqual(run(src), "new")

    def test_dict_assign_multiple_keys(self):
        src = ('let d = {}\n'
               'd["a"] = 1\n'
               'd["b"] = 2\n'
               'd["c"] = 3\n'
               'show d["a"]\n'
               'show d["b"]\n'
               'show d["c"]')
        self.assertEqual(run(src), "1\n2\n3")

    def test_dict_assign_string_value(self):
        src = 'let d = {}\nd["lang"] = "NEKOVA"\nshow d["lang"]'
        self.assertEqual(run(src), "NEKOVA")

    def test_dict_assign_list_value(self):
        src = 'let d = {}\nd["items"] = [1, 2, 3]\nshow d["items"][1]'
        self.assertEqual(run(src), "2")

    def test_dict_assign_inside_task(self):
        src = ('task fill(d):\n'
               '    d["x"] = 10\n'
               'let d = {}\n'
               'fill(d)\n'
               'show d["x"]')
        self.assertEqual(run(src), "10")

    # ── list index assignment ──────────────────────────────────
    def test_list_assign_first(self):
        src = 'let items = [1, 2, 3]\nitems[0] = 99\nshow items[0]'
        self.assertEqual(run(src), "99")

    def test_list_assign_last(self):
        src = 'let items = [1, 2, 3]\nitems[2] = 99\nshow items[2]'
        self.assertEqual(run(src), "99")

    def test_list_assign_middle(self):
        src = 'let items = [10, 20, 30]\nitems[1] = 50\nshow items[1]'
        self.assertEqual(run(src), "50")

    def test_list_assign_preserves_others(self):
        src = 'let items = [1, 2, 3]\nitems[1] = 99\nshow items[0]\nshow items[2]'
        self.assertEqual(run(src), "1\n3")

    # ── chained index assignment ───────────────────────────────
    def test_nested_dict_assign(self):
        src = ('let d = {}\n'
               'd["x"] = {}\n'
               'd["x"]["y"] = 42\n'
               'show d["x"]["y"]')
        self.assertEqual(run(src), "42")

    def test_list_of_dicts(self):
        src = ('let rows = [{}, {}, {}]\n'
               'rows[1]["name"] = "NEKOVA"\n'
               'show rows[1]["name"]')
        self.assertEqual(run(src), "NEKOVA")

    # ── error cases ────────────────────────────────────────────
    def test_list_out_of_range(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        src = 'let items = [1, 2, 3]\nitems[9] = 99'
        tokens      = Lexer(src).tokenize()
        program     = Parser(tokens).parse()
        interpreter = Interpreter()
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            interpreter.execute(program)
        self.assertIn("out of range", str(ctx.exception).lower())

    def test_dict_existing_key_in_check(self):
        src = 'let d = {}\nd["x"] = 1\nshow "x" in d'
        self.assertEqual(run(src), "true")


class TestMatchRanges(unittest.TestCase):
    """Self-hosting blocker 3: when 'a'..'z' / when 0..9 was a parse error."""

    # ── character ranges ───────────────────────────────────────
    def test_lowercase_match(self):
        src = ('match "m":\n'
               '    when "a".."z": show "lower"\n'
               '    else: show "other"')
        self.assertEqual(run(src), "lower")

    def test_uppercase_match(self):
        src = ('match "M":\n'
               '    when "A".."Z": show "upper"\n'
               '    else: show "other"')
        self.assertEqual(run(src), "upper")

    def test_digit_match(self):
        src = ('match "5":\n'
               '    when "0".."9": show "digit"\n'
               '    else: show "other"')
        self.assertEqual(run(src), "digit")

    def test_boundary_low(self):
        src = ('match "a":\n'
               '    when "a".."z": show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "yes")

    def test_boundary_high(self):
        src = ('match "z":\n'
               '    when "a".."z": show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "yes")

    def test_outside_range(self):
        src = ('match "!":\n'
               '    when "a".."z": show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "no")

    def test_multiple_char_ranges(self):
        src = ('task classify(c):\n'
               '    match c:\n'
               '        when "a".."z": return "lower"\n'
               '        when "A".."Z": return "upper"\n'
               '        when "0".."9": return "digit"\n'
               '        else: return "other"\n'
               'show classify("m")\n'
               'show classify("M")\n'
               'show classify("5")\n'
               'show classify("!")')
        self.assertEqual(run(src), "lower\nupper\ndigit\nother")

    # ── numeric ranges ─────────────────────────────────────────
    def test_number_range_low(self):
        src = ('match 3:\n'
               '    when 1..5: show "low"\n'
               '    else: show "other"')
        self.assertEqual(run(src), "low")

    def test_number_range_boundary_low(self):
        src = ('match 1:\n'
               '    when 1..5: show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "yes")

    def test_number_range_boundary_high(self):
        src = ('match 5:\n'
               '    when 1..5: show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "yes")

    def test_number_range_outside(self):
        src = ('match 0:\n'
               '    when 1..5: show "yes"\n'
               '    else: show "no"')
        self.assertEqual(run(src), "no")

    def test_multiple_numeric_ranges(self):
        src = ('task grade(score):\n'
               '    match score:\n'
               '        when 90..100: return "A"\n'
               '        when 80..89: return "B"\n'
               '        when 70..79: return "C"\n'
               '        else: return "F"\n'
               'show grade(95)\n'
               'show grade(85)\n'
               'show grade(75)\n'
               'show grade(50)')
        self.assertEqual(run(src), "A\nB\nC\nF")

    def test_range_with_hex_literals(self):
        src = ('match 0x0F:\n'
               '    when 0x00..0x0F: show "low-byte"\n'
               '    when 0x10..0xFF: show "high-byte"\n'
               '    else: show "out"')
        self.assertEqual(run(src), "low-byte")

    def test_range_first_arm_wins(self):
        """Ranges are checked in order; first match wins."""
        src = ('match 5:\n'
               '    when 1..10: show "first"\n'
               '    when 5..5:  show "second"\n'
               '    else:       show "else"')
        self.assertEqual(run(src), "first")

    def test_range_combined_with_value_arms(self):
        src = ('match 7:\n'
               '    when 0: show "zero"\n'
               '    when 1..5: show "low"\n'
               '    when 6..10: show "mid"\n'
               '    else: show "high"')
        self.assertEqual(run(src), "mid")

    def test_range_in_task(self):
        src = ('task band(n):\n'
               '    match n:\n'
               '        when 0..33:  return "low"\n'
               '        when 34..66: return "mid"\n'
               '        when 67..100: return "high"\n'
               '        else: return "out"\n'
               'show band(0)\n'
               'show band(33)\n'
               'show band(34)\n'
               'show band(100)\n'
               'show band(101)')
        self.assertEqual(run(src), "low\nlow\nmid\nhigh\nout")


if __name__ == "__main__":
    unittest.main()