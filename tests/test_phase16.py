"""
Phase 16 — Standout Features
Tests for: speak, listen, every, test/expect, imagine, shape, watch
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.ai import memory_store as _mem_store


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
    raw = buf.getvalue()
    return re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()


def run_interp(source: str):
    """Run and return (output, interpreter) so we can inspect state."""
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
    return re.sub(r'\x1b\[[0-9;]*m', '', raw).strip(), interp


# ── speak ─────────────────────────────────────────────────────

class TestSpeak(unittest.TestCase):
    def test_speak_parses(self):
        """speak statement parses without error."""
        tokens = Lexer('speak "Hello"').tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import SpeakStatement
        self.assertIsInstance(ast.statements[0], SpeakStatement)

    def test_speak_returns_text(self):
        """speak returns the spoken text (fallback to print)."""
        out = run('speak "Hello NEKOVA"')
        # In test env, falls back to [speak] prefix or direct TTS
        self.assertIn("Hello NEKOVA", out)

    def test_speak_with_variable(self):
        out = run('let msg = "greetings"\nspeak msg')
        self.assertIn("greetings", out)

    def test_speak_with_expression(self):
        out = run('let name = "Emmanuel"\nspeak "Hello " + name')
        self.assertIn("Hello Emmanuel", out)


# ── listen ────────────────────────────────────────────────────

class TestListen(unittest.TestCase):
    def test_listen_parses(self):
        """listen parses as an expression."""
        tokens = Lexer('let x = listen').tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import AssignStatement, ListenExpression
        node = ast.statements[0]
        self.assertIsInstance(node, AssignStatement)
        self.assertIsInstance(node.value, ListenExpression)

    def test_listen_with_prompt_parses(self):
        tokens = Lexer('let x = listen "Say your name"').tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import AssignStatement, ListenExpression
        node = ast.statements[0]
        self.assertIsInstance(node.value, ListenExpression)
        self.assertIsNotNone(node.value.prompt)


# ── every ─────────────────────────────────────────────────────

class TestEvery(unittest.TestCase):
    def test_every_parses(self):
        """every block parses correctly."""
        src = 'every 1 s 2 times:\n    show "tick"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import EveryStatement
        self.assertIsInstance(ast.statements[0], EveryStatement)

    def test_every_runs_n_times(self):
        """every N s X times runs body X times."""
        # Use 0s interval so it runs without delay
        src = 'every 0 s 3 times:\n    show "tick"'
        out = run(src)
        self.assertEqual(out.count("tick"), 3)

    def test_every_unit_stored(self):
        src = 'every 5 m 1 times:\n    show "done"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.statements[0]
        self.assertEqual(node.interval_unit, "m")

    def test_every_max_runs_stored(self):
        src = 'every 1 s 2 times:\n    show "x"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.statements[0]
        self.assertEqual(int(node.max_runs), 2)


# ── test / expect ─────────────────────────────────────────────

class TestTestExpect(unittest.TestCase):
    def test_test_block_parses(self):
        src = 'test "adds":\n    expect 1 + 1 == 2'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import TestBlock
        self.assertIsInstance(ast.statements[0], TestBlock)
        self.assertEqual(ast.statements[0].label, "adds")

    def test_expect_parses(self):
        src = 'test "x":\n    expect true'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import ExpectStatement
        body = ast.statements[0].body
        self.assertIsInstance(body[0], ExpectStatement)

    def test_passing_test(self):
        src = 'test "math":\n    expect 2 + 2 == 4'
        out = run(src)
        self.assertIn("PASS", out)
        self.assertIn("math", out)

    def test_failing_test(self):
        src = 'test "wrong":\n    expect 1 == 2'
        out = run(src)
        self.assertIn("FAIL", out)
        self.assertIn("wrong", out)

    def test_multiple_expects(self):
        src = (
            'test "arithmetic":\n'
            '    expect 1 + 1 == 2\n'
            '    expect 10 - 3 == 7\n'
            '    expect 4 * 4 == 16'
        )
        out = run(src)
        self.assertIn("PASS", out)
        self.assertIn("3/3", out)

    def test_mixed_pass_fail(self):
        src = (
            'test "mixed":\n'
            '    expect 1 == 1\n'
            '    expect 1 == 2\n'
            '    expect 3 == 3'
        )
        out = run(src)
        self.assertIn("FAIL", out)
        self.assertIn("2/3", out)

    def test_test_with_task(self):
        src = (
            'task add(a, b):\n'
            '    return a + b\n'
            'test "add function":\n'
            '    expect add(1, 2) == 3\n'
            '    expect add(0, 0) == 0\n'
            '    expect add(-1, 1) == 0'
        )
        out = run(src)
        self.assertIn("PASS", out)
        self.assertIn("3/3", out)

    def test_multiple_test_blocks(self):
        src = (
            'test "first":\n'
            '    expect true\n'
            'test "second":\n'
            '    expect 1 == 1'
        )
        out = run(src)
        self.assertIn("first", out)
        self.assertIn("second", out)
        self.assertEqual(out.count("PASS"), 2)

    def test_totals_tracked(self):
        src = (
            'test "a":\n    expect true\n'
            'test "b":\n    expect false'
        )
        _, interp = run_interp(src)
        totals = getattr(interp, "_test_totals", {})
        self.assertEqual(totals.get("passed", 0), 1)
        self.assertEqual(totals.get("failed", 0), 1)


# ── imagine ───────────────────────────────────────────────────

class TestImagine(unittest.TestCase):
    def test_imagine_parses(self):
        src = 'imagine "a red fox"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import ImagineStatement
        self.assertIsInstance(ast.statements[0], ImagineStatement)

    def test_imagine_as_url_parses(self):
        src = 'imagine "sunset" as url'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.statements[0]
        self.assertEqual(node.result_format, "url")

    def test_imagine_as_path_parses(self):
        src = 'imagine "cat" as path'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        self.assertEqual(ast.statements[0].result_format, "path")

    def test_imagine_returns_url(self):
        """Without API key, returns mock URL."""
        src = 'let img = imagine "red fox"'
        _, interp = run_interp(src)
        img = interp.env.get("img")
        self.assertIsInstance(img, str)
        self.assertIn("red", img.replace("+", " "))

    def test_imagine_as_expression(self):
        src = 'let url = imagine "blue sky" as url\nshow url'
        out = run(src)
        self.assertIn("blue", out.replace("+", " "))


# ── shape ─────────────────────────────────────────────────────

class TestShape(unittest.TestCase):
    def test_shape_parses(self):
        src = 'shape User:\n    name str\n    age int'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import ShapeDefinition
        self.assertIsInstance(ast.statements[0], ShapeDefinition)
        self.assertEqual(ast.statements[0].name, "User")

    def test_shape_fields(self):
        src = 'shape Point:\n    x int\n    y int'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.statements[0]
        self.assertEqual(len(node.fields), 2)
        self.assertEqual(node.fields[0][0], "x")
        self.assertEqual(node.fields[1][0], "y")

    def test_shape_creates_constructor(self):
        src = (
            'shape User:\n'
            '    name str\n'
            '    age int\n'
            'let u = User("Alice", 30)\n'
            'show u["name"]'
        )
        out = run(src)
        self.assertEqual(out, "Alice")

    def test_shape_type_coercion(self):
        src = (
            'shape Box:\n'
            '    width int\n'
            '    height int\n'
            'let b = Box("10", "20")\n'
            'show b["width"] + b["height"]'
        )
        out = run(src)
        self.assertEqual(out, "30")

    def test_shape_default_field(self):
        src = (
            'shape Config:\n'
            '    host str\n'
            '    port int = 8080\n'
            'let c = Config("localhost")\n'
            'show c["port"]'
        )
        out = run(src)
        self.assertEqual(out, "8080")

    def test_shape_shape_marker(self):
        """shape instances have __shape__ key."""
        src = (
            'shape Tag:\n'
            '    label str\n'
            'let t = Tag("news")\n'
            'show t["__shape__"]'
        )
        out = run(src)
        self.assertEqual(out, "Tag")

    def test_shape_missing_required_field(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        src = (
            'shape Item:\n'
            '    name str\n'
            '    price float\n'
            'let i = Item("phone")'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_multiple_shapes(self):
        src = (
            'shape Point:\n'
            '    x int\n'
            '    y int\n'
            'shape Circle:\n'
            '    cx int\n'
            '    cy int\n'
            '    radius float\n'
            'let p = Point(3, 4)\n'
            'let c = Circle(0, 0, 5)\n'
            'show p["x"]\n'
            'show c["radius"]'
        )
        out = run(src)
        lines = out.split("\n")
        self.assertEqual(lines[0], "3")
        self.assertEqual(lines[1], "5.0")


# ── watch ─────────────────────────────────────────────────────

class TestWatch(unittest.TestCase):
    def test_watch_parses_file(self):
        src = 'watch "config.toml":\n    show "changed"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import WatchStatement
        node = ast.statements[0]
        self.assertIsInstance(node, WatchStatement)
        self.assertTrue(node.is_file)

    def test_watch_parses_variable(self):
        src = 'let x = 0\nwatch x:\n    show "changed"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import WatchStatement
        node = ast.statements[1]
        self.assertIsInstance(node, WatchStatement)
        self.assertFalse(node.is_file)


if __name__ == "__main__":
    unittest.main()