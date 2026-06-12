# =============================================================
# NEKOVA - Phase 6 Tests (Control Flow & Data Structures)
# =============================================================
# Run with: python tests/test_phase6.py
#
# Covers features that exist in the interpreter but were not
# yet covered by Phase 4 or Phase 5: while loops, for loops,
# try/catch error handling, and list/dict literals.

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """Helper - run NEKOVA source and capture printed output."""
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


class TestWhileLoops(unittest.TestCase):

    def test_while_basic(self):
        source = (
            'i = 0\n'
            'while i < 3:\n'
            '    show i\n'
            '    i = i + 1\n'
        )
        self.assertEqual(run(source), "0\n1\n2")

    def test_while_never_runs(self):
        source = (
            'i = 5\n'
            'while i < 3:\n'
            '    show i\n'
        )
        self.assertEqual(run(source), "")


class TestForLoops(unittest.TestCase):

    def test_for_over_list(self):
        source = (
            'items = ["a", "b", "c"]\n'
            'for item in items:\n'
            '    show item\n'
        )
        self.assertEqual(run(source), "a\nb\nc")

    def test_for_with_numbers(self):
        source = (
            'nums = [1, 2, 3]\n'
            'total = 0\n'
            'for n in nums:\n'
            '    total = total + n\n'
            'show total\n'
        )
        self.assertEqual(run(source), "6")


class TestTryCatch(unittest.TestCase):

    def test_try_no_error(self):
        source = (
            'try:\n'
            '    show "ok"\n'
            'catch err:\n'
            '    show "failed"\n'
        )
        self.assertEqual(run(source), "ok")

    def test_try_with_error(self):
        source = (
            'try:\n'
            '    x = 1 / 0\n'
            '    show "unreachable"\n'
            'catch err:\n'
            '    show "caught"\n'
        )
        self.assertEqual(run(source), "caught")


class TestListLiterals(unittest.TestCase):

    def test_list_index(self):
        source = (
            'items = [10, 20, 30]\n'
            'show items[1]\n'
        )
        self.assertEqual(run(source), "20")

    def test_list_length(self):
        source = (
            'items = [1, 2, 3, 4]\n'
            'show length(items)\n'
        )
        self.assertEqual(run(source), "4")


class TestDictLiterals(unittest.TestCase):

    def test_dict_access(self):
        source = (
            'person = {"name": "Emmanuel", "age": 25}\n'
            'show person["name"]\n'
        )
        self.assertEqual(run(source), "Emmanuel")


if __name__ == "__main__":
    unittest.main()
