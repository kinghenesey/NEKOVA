"""
Phase 22 — Observability + Testing + Pipe Operator
Tests for: `observe "label" [with tags {...}]:` tracing blocks,
`mock think as <value>` (scoped to the enclosing test block), and
the `|>` pipe operator.
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
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


# ── observe ──────────────────────────────────────────────────

class TestObserveBasics(unittest.TestCase):

    def test_body_executes_normally(self):
        out = run(
            'observe "quick check":\n'
            '    show "doing work"\n'
        )
        self.assertIn("doing work", out)

    def test_prints_label(self):
        out = run(
            'observe "my trace label":\n'
            '    show "x"\n'
        )
        self.assertIn("my trace label", out)

    def test_prints_completion_line(self):
        out = run(
            'observe "x":\n'
            '    show "y"\n'
        )
        self.assertIn("completed", out.lower())

    def test_with_tags(self):
        out = run(
            'observe "pipeline run" with tags {user: 42, env: "prod"}:\n'
            '    show "processing"\n'
        )
        self.assertIn("user", out)
        self.assertIn("42", out)
        self.assertIn("prod", out)

    def test_without_tags_no_braces_printed(self):
        out = run(
            'observe "no tags here":\n'
            '    show "ok"\n'
        )
        self.assertNotIn("{}", out)

    def test_variables_set_inside_body_are_visible_after(self):
        out = run(
            'observe "sets a var":\n'
            '    x = 42\n'
            'show x\n'
        )
        self.assertIn("42", out)

    def test_error_inside_observe_propagates(self):
        out = run(
            'try:\n'
            '    observe "will fail":\n'
            '        raise "boom"\n'
            'catch e:\n'
            '    show "caught: " + e.message\n'
        )
        self.assertIn("caught: boom", out)

    def test_error_inside_observe_logs_failure(self):
        out = run(
            'try:\n'
            '    observe "will fail":\n'
            '        raise "boom"\n'
            'catch e:\n'
            '    show "done"\n'
        )
        self.assertIn("failed", out.lower())

    def test_nested_observe(self):
        out = run(
            'observe "outer":\n'
            '    observe "inner":\n'
            '        show "deep"\n'
        )
        self.assertIn("outer", out)
        self.assertIn("inner", out)
        self.assertIn("deep", out)


# ── mock ─────────────────────────────────────────────────────

class TestMockThink(unittest.TestCase):

    def test_mock_short_circuits_think(self):
        out = run(
            'test "uses mock":\n'
            '    mock think as "sports"\n'
            '    result = think "classify this" as text\n'
            '    expect result == "sports"\n'
        )
        self.assertIn("PASS", out)

    def test_mock_short_circuits_think_as_task(self):
        out = run(
            'task classify(text):\n'
            '    return think "classify: " + text as text\n'
            'test "classifier":\n'
            '    mock think as "sports"\n'
            '    expect classify("anything") == "sports"\n'
        )
        self.assertIn("PASS", out)

    def test_mock_scoped_to_its_test_only(self):
        # A second test block without `mock` must NOT see the
        # previous test's mocked value.
        out = run(
            'test "with mock":\n'
            '    mock think as "mocked-value"\n'
            '    expect (think "x" as text) == "mocked-value"\n'
            'test "without mock":\n'
            '    result = think "x" as text\n'
            '    expect result != "mocked-value"\n'
        )
        self.assertNotIn("✗ FAIL", out)

    def test_mock_unsupported_target_raises(self):
        out = run(
            'try:\n'
            '    mock something_else as "x"\n'
            'catch e:\n'
            '    show "caught"\n'
        )
        self.assertEqual(out, "caught")

    def test_mock_value_can_be_non_string(self):
        out = run(
            'test "numeric mock":\n'
            '    mock think as 42\n'
            '    result = think "x" as text\n'
            '    expect result == 42\n'
        )
        self.assertIn("PASS", out)


# ── pipe operator ────────────────────────────────────────────

class TestPipeOperator(unittest.TestCase):

    def test_single_pipe_into_call_with_no_args(self):
        out = run(
            'task double(x):\n'
            '    return x * 2\n'
            'show 5 |> double()\n'
        )
        self.assertEqual(out, "10")

    def test_chained_pipes(self):
        out = run(
            'task double(x):\n'
            '    return x * 2\n'
            'task add_ten(x):\n'
            '    return x + 10\n'
            'show 5 |> double() |> add_ten()\n'
        )
        self.assertEqual(out, "20")

    def test_pipe_into_call_with_existing_args(self):
        # piped value becomes the FIRST positional argument
        out = run(
            'task greet(name, greeting):\n'
            '    return greeting + ", " + name\n'
            'show "World" |> greet("Hello")\n'
        )
        self.assertEqual(out, "Hello, World")

    def test_pipe_into_bare_task_name(self):
        out = run(
            'task increment(x):\n'
            '    return x + 1\n'
            'show 5 |> increment\n'
        )
        self.assertEqual(out, "6")

    def test_pipe_with_lists(self):
        out = run(
            'task filter_even(lst):\n'
            '    out = []\n'
            '    for x in lst:\n'
            '        if x % 2 == 0:\n'
            '            out.append(x)\n'
            '    return out\n'
            'task total(lst):\n'
            '    s = 0\n'
            '    for x in lst:\n'
            '        s = s + x\n'
            '    return s\n'
            'show [1, 2, 3, 4, 5] |> filter_even() |> total()\n'
        )
        self.assertEqual(out, "6")

    def test_pipe_result_usable_in_expression(self):
        out = run(
            'task double(x):\n'
            '    return x * 2\n'
            'result = (5 |> double()) + 1\n'
            'show result\n'
        )
        self.assertEqual(out, "11")

    def test_pipe_into_non_call_non_identifier_raises_parse_error(self):
        from nekova.parser.parser import ParseError
        with self.assertRaises(ParseError):
            tokens = Lexer('show 5 |> 3\n').tokenize()
            Parser(tokens).parse()


if __name__ == "__main__":
    unittest.main()