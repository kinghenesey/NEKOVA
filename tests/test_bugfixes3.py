"""
Bug Fix Regression Tests — Round 3
Covers bugs found by Emmanuel while building game files in NEKOVA:

  Bug A: Blank lines inside indented blocks (if/elif/else/while/for/
         task/route) threw an "INDENT not defined here" style parse
         error.

  Bug B: Multi-line dict/list/call literals inside a block failed to
         parse, because the lexer emitted INDENT/DEDENT per physical
         line regardless of bracket depth, and the dict/list parsers
         only knew how to skip NEWLINE tokens between entries.

Root-cause fix: the lexer now tracks bracket depth (via
Lexer.bracket_depth) and suspends NEWLINE/INDENT/DEDENT emission
entirely while depth > 0 — i.e. while inside an unclosed (), [], or
{}. This is the standard "implicit line joining" behaviour used by
Python and fixes both bugs with a single change, since bug A's fix
(skipping blank lines) already existed but bug B was a case the old
per-line indent tracking still couldn't handle.
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
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


def parse_ok(source: str):
    """Tokenize + parse only; raises on failure."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# ── Bug A: Blank lines inside indented blocks ─────────────────

class TestBlankLinesInsideBlocks(unittest.TestCase):

    def test_blank_line_inside_if(self):
        src = (
            'if 1 == 1:\n'
            '    show "a"\n'
            '\n'
            '    show "b"\n'
        )
        parse_ok(src)

    def test_blank_line_inside_if_elif_else(self):
        src = (
            'x = 5\n'
            'if x == 1:\n'
            '    show "one"\n'
            '\n'
            'elif x == 5:\n'
            '    show "five"\n'
            '\n'
            'else:\n'
            '    show "other"\n'
            '\n'
        )
        self.assertEqual(run(src), "five")

    def test_blank_line_inside_while(self):
        src = (
            'i = 0\n'
            'while i < 3:\n'
            '    show i\n'
            '\n'
            '    i = i + 1\n'
        )
        self.assertEqual(run(src), "0\n1\n2")

    def test_blank_line_inside_for(self):
        src = (
            'for n in [1, 2, 3]:\n'
            '    show n\n'
            '\n'
            '    show "next"\n'
        )
        out = run(src)
        self.assertIn("1", out)
        self.assertIn("next", out)

    def test_blank_line_inside_task(self):
        src = (
            'task greet():\n'
            '    show "hello"\n'
            '\n'
            '    show "world"\n'
            'greet()\n'
        )
        self.assertEqual(run(src), "hello\nworld")

    def test_blank_line_first_line_of_block(self):
        """A blank line right after the ':' before any statement."""
        src = (
            'if true:\n'
            '\n'
            '    show "ok"\n'
        )
        self.assertEqual(run(src), "ok")

    def test_blank_line_before_dedent(self):
        """A blank line right before the block closes."""
        src = (
            'task greet():\n'
            '    show "hi"\n'
            '\n'
            'greet()\n'
            'show "after"\n'
        )
        self.assertEqual(run(src), "hi\nafter")

    def test_multiple_consecutive_blank_lines(self):
        src = (
            'task greet():\n'
            '    show "a"\n'
            '\n'
            '\n'
            '\n'
            '    show "b"\n'
            'greet()\n'
        )
        self.assertEqual(run(src), "a\nb")

    def test_blank_line_with_trailing_whitespace(self):
        """Blank line that still has spaces on it (common editor artifact)."""
        src = (
            'task greet():\n'
            '    show "a"\n'
            '    \n'
            '    show "b"\n'
            'greet()\n'
        )
        self.assertEqual(run(src), "a\nb")


# ── Bug B: Multi-line dict/list/call literals inside a block ──

class TestMultilineBracketsInsideBlocks(unittest.TestCase):

    def test_multiline_dict_in_task(self):
        src = (
            'task make():\n'
            '    result = {\n'
            '        status: "ok",\n'
            '        value: 42\n'
            '    }\n'
            '    show result["status"]\n'
            '    show result["value"]\n'
            'make()\n'
        )
        self.assertEqual(run(src), "ok\n42")

    def test_multiline_list_in_task(self):
        src = (
            'task make():\n'
            '    nums = [\n'
            '        1,\n'
            '        2,\n'
            '        3\n'
            '    ]\n'
            '    show nums\n'
            'make()\n'
        )
        self.assertEqual(run(src), "[1, 2, 3]")

    def test_multiline_call_args_in_task(self):
        src = (
            'task add(a, b):\n'
            '    return a + b\n'
            'task make():\n'
            '    result = add(\n'
            '        1,\n'
            '        2\n'
            '    )\n'
            '    show result\n'
            'make()\n'
        )
        self.assertEqual(run(src), "3")

    def test_nested_multiline_dict_and_list(self):
        src = (
            'task make():\n'
            '    data = {\n'
            '        outer: {\n'
            '            inner: [\n'
            '                1,\n'
            '                2\n'
            '            ]\n'
            '        },\n'
            '        flag: true\n'
            '    }\n'
            '    show data["outer"]["inner"]\n'
            'make()\n'
        )
        self.assertEqual(run(src), "[1, 2]")

    def test_multiline_dict_matches_single_line_equivalent(self):
        multi = (
            'task make():\n'
            '    result = {\n'
            '        status: "ok",\n'
            '        value: 42\n'
            '    }\n'
            '    show result\n'
            'make()\n'
        )
        single = (
            'task make():\n'
            '    result = {status: "ok", value: 42}\n'
            '    show result\n'
            'make()\n'
        )
        self.assertEqual(run(multi), run(single))

    def test_bracket_depth_resets_after_dict(self):
        """A block-indentation change right after a multiline dict
        must still be tracked correctly (bracket_depth must return
        to 0 once the closing brace is seen)."""
        src = (
            'task make():\n'
            '    result = {\n'
            '        status: "ok"\n'
            '    }\n'
            '    if result["status"] == "ok":\n'
            '        show "good"\n'
            '    else:\n'
            '        show "bad"\n'
            'make()\n'
        )
        self.assertEqual(run(src), "good")


if __name__ == "__main__":
    unittest.main()