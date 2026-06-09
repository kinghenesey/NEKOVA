# =============================================================
# NEKOVA — Phase 5 Tests (Standard Library)
# =============================================================
# Run with: python tests/test_phase5.py

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer
from parser.parser import Parser
from interpreter.interpreter import Interpreter


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


class TestMathModule(unittest.TestCase):

    def test_sqrt(self):
        output = run("use math\nshow sqrt(16)")
        self.assertEqual(output, "4.0")

    def test_floor(self):
        output = run("use math\nshow floor(3.9)")
        self.assertEqual(output, "3")

    def test_ceil(self):
        output = run("use math\nshow ceil(3.1)")
        self.assertEqual(output, "4")

    def test_abs(self):
        output = run("use math\nshow abs(-5)")
        self.assertEqual(output, "5")

    def test_pi(self):
        output = run("use math\nshow round(pi)")
        self.assertEqual(output, "3")

    def test_min(self):
        output = run("use math\nshow min(3, 1, 2)")
        self.assertEqual(output, "1")

    def test_max(self):
        output = run("use math\nshow max(3, 1, 2)")
        self.assertEqual(output, "3")


class TestTextModule(unittest.TestCase):

    def test_upper(self):
        output = run('use text\nshow upper("hello")')
        self.assertEqual(output, "HELLO")

    def test_lower(self):
        output = run('use text\nshow lower("NEKOVA")')
        self.assertEqual(output, "nekova")

    def test_trim(self):
        output = run('use text\nshow trim("  hello  ")')
        self.assertEqual(output, "hello")

    def test_replace(self):
        output = run('use text\nshow replace("Hello World", "World", "NEKOVA")')
        self.assertEqual(output, "Hello NEKOVA")

    def test_contains_true(self):
        output = run('use text\nshow contains("NEKOVA Language", "NEKOVA")')
        self.assertEqual(output, "true")

    def test_reverse(self):
        output = run('use text\nshow reverse("NEKOVA")')
        self.assertEqual(output, "NOIA")

    def test_length(self):
        output = run('use text\nshow length("NEKOVA")')
        self.assertEqual(output, "4")


class TestFilesModule(unittest.TestCase):

    def test_write_and_read(self):
        source = (
            'use files\n'
            'write_file("test_output.txt", "Hello NEKOVA")\n'
            'content = read_file("test_output.txt")\n'
            'show content'
        )
        output = run(source)
        self.assertEqual(output, "Hello NEKOVA")
        if os.path.exists("test_output.txt"):
            os.remove("test_output.txt")

    def test_file_exists_true(self):
        with open("temp_test.txt", "w") as f:
            f.write("test")
        output = run('use files\nshow file_exists("temp_test.txt")')
        self.assertEqual(output, "true")
        os.remove("temp_test.txt")

    def test_file_exists_false(self):
        output = run('use files\nshow file_exists("no_such_file.txt")')
        self.assertEqual(output, "false")


class TestDatetimeModule(unittest.TestCase):

    def test_today_format(self):
        output = run("use datetime\nshow today()")
        parts = output.split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[0]), 4)

    def test_year(self):
        output = run("use datetime\nshow year()")
        self.assertTrue(output.isdigit())
        self.assertEqual(len(output), 4)

    def test_month(self):
        output = run("use datetime\nshow month()")
        self.assertTrue(1 <= int(output) <= 12)

    def test_day(self):
        output = run("use datetime\nshow day()")
        self.assertTrue(1 <= int(output) <= 31)


class TestCollectionsModule(unittest.TestCase):

    def test_make_list(self):
        output = run("use collections\nitems = make_list(1, 2, 3)\nshow list_length(items)")
        self.assertEqual(output, "3")

    def test_list_get(self):
        output = run("use collections\nitems = make_list(10, 20, 30)\nshow list_get(items, 0)")
        self.assertEqual(output, "10")

    def test_list_last(self):
        output = run("use collections\nitems = make_list(1, 2, 3)\nshow list_last(items)")
        self.assertEqual(output, "3")

    def test_list_has_true(self):
        output = run("use collections\nitems = make_list(1, 2, 3)\nshow list_has(items, 2)")
        self.assertEqual(output, "true")

    def test_list_join(self):
        output = run('use collections\nitems = make_list(1, 2, 3)\nshow list_join(items, "-")')
        self.assertEqual(output, "1-2-3")

    def test_list_reverse(self):
        output = run("use collections\nitems = make_list(1, 2, 3)\nshow list_reverse(items)")
        self.assertEqual(output, "[3, 2, 1]")

    def test_make_range(self):
        output = run("use collections\nitems = make_range(1, 4)\nshow list_join(items, \",\")")
        self.assertEqual(output, "1,2,3")


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 5 — Stdlib Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)