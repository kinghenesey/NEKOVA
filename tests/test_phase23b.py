"""
Phase 23b — Correctness & Trust Part 2
Tests for: bad-indentation-depth detection (expected vs. actual level),
and the raw-Python-exception audit on builtin calls (int, float, len,
range, sum, etc. no longer leak Python tracebacks to the user).
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer, LexerError
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.ai import memory_store as _mem_store

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def run(source: str) -> str:
    _mem_store._memory.clear()
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
    return ANSI.sub('', buf.getvalue()).strip()


class TestIndentationDepthDetection(unittest.TestCase):
    def test_dedent_not_matching_any_level_raises(self):
        src = (
            "task f():\n"
            "    if true:\n"
            "        show 1\n"
            "      show 2\n"  # 6 spaces — matches neither 0 nor 4
        )
        with self.assertRaises(LexerError) as ctx:
            Lexer(src).tokenize()
        msg = str(ctx.exception)
        self.assertIn("6", msg)
        self.assertIn("0, 4", msg)

    def test_valid_dedent_to_existing_level_still_works(self):
        out = run(
            "task f():\n"
            "    if true:\n"
            "        show 1\n"
            "    show 2\n"
            "f()\n"
        )
        self.assertEqual(out, "1\n2")

    def test_consistent_indentation_throughout_program_unaffected(self):
        out = run(
            "task fact(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * fact(n - 1)\n"
            "show fact(5)\n"
        )
        self.assertEqual(out, "120")


class TestBuiltinExceptionAudit(unittest.TestCase):
    """Builtins that wrap Python functions (int, float, len, range, sum,
    ...) must never let a raw Python exception/traceback escape to the
    user — every failure becomes a clean NEKOVARuntimeError."""

    def test_int_conversion_failure_is_clean(self):
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run('show int("abc")\n')
        msg = str(ctx.exception)
        self.assertIn("int()", msg)
        self.assertNotIn("Traceback", msg)

    def test_float_conversion_failure_is_clean(self):
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run('show float("xyz")\n')
        msg = str(ctx.exception)
        self.assertIn("float()", msg)

    def test_len_on_wrong_type_is_clean(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show len(5)\n')

    def test_range_with_bad_arg_is_clean(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show range("a")\n')

    def test_sum_on_non_iterable_is_clean(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show sum(5)\n')

    def test_valid_int_conversion_unaffected(self):
        out = run('show int("42")\n')
        self.assertEqual(out, "42")

    def test_valid_builtin_calls_unaffected(self):
        out = run(
            'show len([1,2,3])\n'
            'show range(3)\n'
            'show sum([1,2,3])\n'
        )
        self.assertEqual(out, "3\n[0, 1, 2]\n6")


if __name__ == "__main__":
    unittest.main()