"""
Bug-fix round — pre-Phase 23
Fixes surfaced during live testing of v1.9.5 (see analysis doc, Section A):

1. Recursion error mislabeling — NEKOVA now tracks its own call depth
   and reports the exact depth reached, instead of guessing "infinite
   recursion" from a bare Python RecursionError.
2. Mock AI responses now self-identify with a [MOCK] tag on every
   branch, not just some of them.
3. "5" + 3 now raises a clear type-mismatch error instead of silently
   coercing to "53".
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import (
    NEKOVARecursionError, NEKOVARuntimeError
)
from nekova.ai import memory_store as _mem_store


def run(source: str) -> str:
    """Run NEKOVA source and return captured stdout."""
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
    raw = buf.getvalue()
    return re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()


class TestRecursionDepthTracking(unittest.TestCase):
    def test_unbounded_recursion_raises_nekova_recursion_error(self):
        """A task with no base case should hit NEKOVA's own depth
        counter, not a bare Python RecursionError."""
        with self.assertRaises(NEKOVARecursionError) as ctx:
            run(
                'task f(n):\n'
                '    return f(n + 1)\n'
                'show f(1)\n'
            )
        self.assertEqual(ctx.exception.depth, Interpreter.MAX_CALL_DEPTH)
        self.assertEqual(ctx.exception.task_name, "f")

    def test_error_message_reports_exact_depth(self):
        with self.assertRaises(NEKOVARecursionError) as ctx:
            run(
                'task f(n):\n'
                '    return f(n + 1)\n'
                'show f(1)\n'
            )
        self.assertIn(str(Interpreter.MAX_CALL_DEPTH), str(ctx.exception))

    def test_legitimate_deep_recursion_under_limit_succeeds(self):
        """Recursion well under the depth limit must still work —
        this fix should never punish correct, bounded recursion."""
        out = run(
            'task fact(n):\n'
            '    if n <= 1:\n'
            '        return 1\n'
            '    return n * fact(n - 1)\n'
            'show fact(100)\n'
        )
        self.assertTrue(out.startswith("933262154439"))

    def test_call_depth_resets_between_independent_calls(self):
        """The depth counter must be decremented on return, so two
        separate bounded recursive calls in sequence don't
        accumulate toward the limit."""
        out = run(
            'task countdown(n):\n'
            '    if n <= 0:\n'
            '        return 0\n'
            '    return countdown(n - 1)\n'
            'show countdown(50)\n'
            'show countdown(50)\n'
            'show countdown(50)\n'
        )
        self.assertEqual(out, "0\n0\n0")


class TestMockAISelfIdentification(unittest.TestCase):
    """Every branch of MockProvider's canned responses must carry a
    [MOCK] tag so a mock reply can never be mistaken for a real one."""

    def setUp(self):
        from nekova.ai.providers.mock import MockProvider
        self.provider = MockProvider()

    def test_hello_branch_tagged(self):
        self.assertIn("[MOCK]", self.provider.ask("hello there"))

    def test_capital_nigeria_branch_tagged(self):
        self.assertIn(
            "[MOCK]", self.provider.ask("what is the capital of nigeria")
        )

    def test_capital_generic_branch_tagged(self):
        self.assertIn("[MOCK]", self.provider.ask("tell me about capitals"))

    def test_what_is_nekova_branch_tagged(self):
        self.assertIn("[MOCK]", self.provider.ask("what is NEKOVA"))

    def test_who_are_you_branch_tagged(self):
        self.assertIn("[MOCK]", self.provider.ask("who are you"))

    def test_weather_branch_tagged(self):
        self.assertIn("[MOCK]", self.provider.ask("what's the weather"))


class TestStringNumberTypeMismatch(unittest.TestCase):
    def test_string_plus_int_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show "5" + 3')

    def test_int_plus_string_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show 3 + "5"')

    def test_string_plus_float_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show "5" + 3.0')

    def test_string_plus_string_still_concatenates(self):
        out = run('show "a" + "b"')
        self.assertEqual(out, "ab")

    def test_numeric_addition_unaffected(self):
        out = run('show 2 + 3')
        self.assertEqual(out, "5")

    def test_string_plus_error_object_still_builds_message(self):
        """The deliberate 'caught: ' + error_object pattern (used for
        formatting exception objects in catch blocks) must keep
        working — only string+number is a hard error."""
        out = run(
            'try:\n'
            '    raise "oops"\n'
            'catch e:\n'
            '    show "caught: " + e'
        )
        self.assertEqual(out, "caught: oops")


if __name__ == "__main__":
    unittest.main()