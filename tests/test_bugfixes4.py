"""
Bug Fix Regression Tests — Round 4
Bundled into Phase 26 without expanding its scope.

  Bug A: Keyword-argument ordering. _resolve_kwargs's gap-filling
         loop assumed node.kwargs.items() arrived in *declared*
         parameter order. Out-of-order call-site keywords (e.g.
         greet(greeting="Hi", name="World") for task greet(name,
         greeting)) caused later-declared parameters to get filled
         with their default instead of the not-yet-visited keyword
         value.
         Fix: sort node.kwargs.items() by names.index(kw_name)
         before the gap-filling loop runs.

  Bug B: No tuple-literal syntax. (1, 2) raised a parse error —
         the LPAREN branch of _parse_primary only ever returned the
         single inner expression, with no handling for a comma.
         Fix: a comma directly inside the parens now collects the
         remaining comma-separated elements and returns a new
         TupleLiteral node (immutable at runtime — a plain Python
         tuple), matching the precedent set by SetLiteral rather
         than overloading the existing mutable ListLiteral.
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.ai import memory_store


def run(source: str) -> str:
    memory_store.init_interpreter_memory()
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


# ── Bug A: Keyword-argument ordering ───────────────────────────

class TestKeywordArgumentOrdering(unittest.TestCase):

    def test_two_kwargs_reversed_order(self):
        src = (
            'task greet(name, greeting = "Hello"):\n'
            '    show greeting + ", " + name\n'
            'greet(greeting="Hi", name="World")\n'
        )
        self.assertEqual(run(src), "Hi, World")

    def test_mixed_positional_and_out_of_order_kwargs(self):
        src = (
            'task build(a, b = "B", c = "C", d = "D"):\n'
            '    show a + "-" + b + "-" + c + "-" + d\n'
            'build("A", d="D2", b="B2")\n'
        )
        self.assertEqual(run(src), "A-B2-C-D2")

    def test_out_of_order_kwargs_leave_gaps_filled_by_default(self):
        src = (
            'task build(a, b = "B", c = "C", d = "D"):\n'
            '    show a + "-" + b + "-" + c + "-" + d\n'
            'build(a="A2", c="C2")\n'
        )
        self.assertEqual(run(src), "A2-B-C2-D")

    def test_all_kwargs_reverse_declared_order(self):
        src = (
            'task build(a, b, c):\n'
            '    show a + b + c\n'
            'build(c="3", b="2", a="1")\n'
        )
        self.assertEqual(run(src), "123")

    def test_forward_order_still_works(self):
        """Regression guard: the common case shouldn't break."""
        src = (
            'task greet(name, greeting = "Hello"):\n'
            '    show greeting + ", " + name\n'
            'greet(name="World", greeting="Hi")\n'
        )
        self.assertEqual(run(src), "Hi, World")


# ── Bug B: Tuple literals ──────────────────────────────────────

class TestTupleLiterals(unittest.TestCase):

    def test_basic_tuple_literal(self):
        src = (
            'let pair = (1, 2)\n'
            'show pair\n'
        )
        self.assertEqual(run(src), "(1, 2)")

    def test_three_element_tuple(self):
        src = (
            'let t = (1, 2, 3)\n'
            'show t\n'
        )
        self.assertEqual(run(src), "(1, 2, 3)")

    def test_single_element_tuple_needs_trailing_comma(self):
        src = (
            'let solo = (5,)\n'
            'show solo\n'
        )
        self.assertEqual(run(src), "(5,)")

    def test_trailing_comma_multi_element(self):
        src = (
            'let t = (1, 2,)\n'
            'show t\n'
        )
        self.assertEqual(run(src), "(1, 2)")

    def test_plain_parens_still_a_grouped_expression(self):
        """A comma-less (expr) must still be plain grouping, not a
        1-tuple — this is what distinguishes (2 + 3) from (2,)."""
        src = (
            'let grouped = (2 + 3)\n'
            'show grouped\n'
        )
        self.assertEqual(run(src), "5")

    def test_tuple_destructuring(self):
        src = (
            'let pair = (1, 2)\n'
            'let [a, b] = pair\n'
            'show a\n'
            'show b\n'
        )
        self.assertEqual(run(src), "1\n2")

    def test_nested_tuple(self):
        src = (
            'let nested = (1, (2, 3))\n'
            'show nested\n'
        )
        self.assertEqual(run(src), "(1, (2, 3))")

    def test_tuple_is_immutable(self):
        tokens = Lexer(
            'let pair = (1, 2)\n'
            'pair[0] = 99\n'
        ).tokenize()
        ast = Parser(tokens).parse()
        interp = Interpreter()
        with self.assertRaises(NEKOVARuntimeError):
            interp.run(ast)

    def test_tuple_indexing(self):
        src = (
            'let pair = (10, 20)\n'
            'show pair[0]\n'
            'show pair[1]\n'
        )
        self.assertEqual(run(src), "10\n20")


if __name__ == "__main__":
    unittest.main()