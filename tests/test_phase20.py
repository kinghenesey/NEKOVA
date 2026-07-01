"""
Phase 20 — Self-Hosting: lexer.nk
Verifies that nekova/stdlib/nk/lexer.nk (the NEKOVA lexer written
in NEKOVA) produces exactly the same token stream as the Python
reference lexer (nekova/lexer/lexer.py) across a wide range of
NEKOVA programs — including the two bugs Emmanuel found while
building game files (blank lines inside blocks, and multi-line
dict/list/call literals inside a block).
"""
import unittest
import sys
import io
import os
import re
import tempfile

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.stdlib.nk_loader import clear_cache
from nekova.ai import memory_store as _mem_store

ANSI = re.compile(r'\x1b\[[0-9;]*m')


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
    return ANSI.sub('', buf.getvalue()).strip()


def python_lex_lines(source: str):
    """Reference token stream from the Python lexer, as TYPE|value lines."""
    toks = Lexer(source).tokenize()
    lines = []
    for t in toks:
        v = str(t.value).replace("\n", "\\n").replace("\t", "\\t")
        lines.append(f"{t.type.name}|{v}")
    return lines


def nekova_lex_lines(source: str):
    """
    Token stream from the self-hosted lexer.nk, as TYPE|value lines,
    produced by running lexer.nk's tokenize() through the interpreter
    (via a small harness that reads the source-under-test from a temp
    file, since NEKOVA programs run through the normal file-based
    interpreter path).
    """
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".nk", delete=False, encoding="utf-8") as f:
        f.write(source)
        path = f.name

    try:
        # Escape the path for embedding in a NEKOVA string literal
        escaped_path = path.replace("\\", "\\\\")
        harness = (
            'use lexer\n'
            f'src = file_read("{escaped_path}")\n'
            'tokens = tokenize(src)\n'
            'for t in tokens:\n'
            '    v = str(t["value"])\n'
            '    v = v.replace("\\n", "\\\\n")\n'
            '    v = v.replace("\\t", "\\\\t")\n'
            '    show t["type"] + "|" + v\n'
        )
        out = run(harness)
        return [l for l in out.splitlines() if re.match(r'^[A-Z_]+\|', l)]
    finally:
        os.unlink(path)


def assert_parity(test_case, source):
    """Assert lexer.nk and the Python lexer agree on this source."""
    expected = python_lex_lines(source)
    actual = nekova_lex_lines(source)
    test_case.assertEqual(expected, actual)


class TestLexerNkExists(unittest.TestCase):

    def test_lexer_nk_module_exists(self):
        from nekova.stdlib.nk_loader import has_nk_module
        self.assertTrue(has_nk_module("lexer"))

    def test_tokenize_is_exported(self):
        from nekova.stdlib.nk_loader import load_nk_module
        clear_cache()
        ns = load_nk_module("lexer")
        self.assertIn("tokenize", ns)


class TestLexerNkBasics(unittest.TestCase):

    def test_simple_expression(self):
        assert_parity(self, 'show 1 + 2\n')

    def test_operators(self):
        assert_parity(self, (
            'show 1 == 2\n'
            'show 1 != 2\n'
            'show 1 <= 2\n'
            'show 1 >= 2\n'
            'show 2 ** 3\n'
            'show 7 // 2\n'
            'x = 1\n'
            'x += 1\n'
            'x -= 1\n'
            'x *= 2\n'
            'x /= 2\n'
        ))

    def test_strings_with_escapes(self):
        assert_parity(self, 'show "hello\\nworld"\nshow \'single\\tquoted\'\n')

    def test_fstring(self):
        assert_parity(self, 'name = "world"\nshow f"Hello {name}!"\n')

    def test_triple_quoted_string(self):
        assert_parity(self, 's = """line1\nline2"""\nshow s\n')

    def test_comments(self):
        assert_parity(self, '# a comment\nshow 1  # trailing comment\n')

    def test_numbers_all_forms(self):
        assert_parity(self, (
            'show 42\n'
            'show 3.14\n'
            'show 0xFF\n'
            'show 1_000_000\n'
            'show 1.5e-3\n'
            'show 1e5\n'
        ))

    def test_dict_index_assignment(self):
        assert_parity(self, 'd = {"x": 1}\nd["x"] = 2\nshow d["x"]\n')

    def test_match_range(self):
        assert_parity(self, (
            'c = "5"\n'
            'match c:\n'
            '    when "0".."9":\n'
            '        show "digit"\n'
            '    when other:\n'
            '        show "other"\n'
        ))


class TestLexerNkBugFixParity(unittest.TestCase):
    """
    The two bugs Emmanuel hit building game files: blank lines inside
    blocks, and multi-line dict/list/call literals inside a block.
    lexer.nk must handle both exactly like the Python lexer does.
    """

    def test_blank_line_inside_task(self):
        assert_parity(self, (
            'task greet():\n'
            '    show "a"\n'
            '\n'
            '    show "b"\n'
            'greet()\n'
        ))

    def test_blank_line_inside_if_elif_else(self):
        assert_parity(self, (
            'x = 5\n'
            'if x == 1:\n'
            '    show "one"\n'
            '\n'
            'elif x == 5:\n'
            '    show "five"\n'
            '\n'
            'else:\n'
            '    show "other"\n'
        ))

    def test_blank_line_inside_while(self):
        assert_parity(self, (
            'i = 0\n'
            'while i < 3:\n'
            '    show i\n'
            '\n'
            '    i = i + 1\n'
        ))

    def test_blank_line_inside_for(self):
        assert_parity(self, (
            'for n in [1, 2, 3]:\n'
            '    show n\n'
            '\n'
            '    show "next"\n'
        ))

    def test_multiline_dict_in_task(self):
        assert_parity(self, (
            'task make():\n'
            '    result = {\n'
            '        status: "ok",\n'
            '        value: 42\n'
            '    }\n'
            '    show result\n'
            'make()\n'
        ))

    def test_multiline_list_in_task(self):
        assert_parity(self, (
            'task make():\n'
            '    nums = [\n'
            '        1,\n'
            '        2,\n'
            '        3\n'
            '    ]\n'
            '    show nums\n'
            'make()\n'
        ))

    def test_multiline_call_args(self):
        assert_parity(self, (
            'task add(a, b):\n'
            '    return a + b\n'
            'result = add(\n'
            '    1,\n'
            '    2\n'
            ')\n'
            'show result\n'
        ))

    def test_nested_multiline_dict_and_list(self):
        assert_parity(self, (
            'task make():\n'
            '    data = {\n'
            '        outer: {\n'
            '            inner: [\n'
            '                1,\n'
            '                2\n'
            '            ]\n'
            '        }\n'
            '    }\n'
            '    show data\n'
            'make()\n'
        ))


class TestLexerNkRealPrograms(unittest.TestCase):
    """Run lexer.nk against real, full-sized NEKOVA programs already
    in the repo — the strongest signal of self-hosting readiness."""

    def _assert_file_parity(self, relative_path):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(repo_root, relative_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert_parity(self, source)

    def test_phase3_demo(self):
        self._assert_file_parity("examples/phase3_demo.nk")

    def test_mood_tracker(self):
        self._assert_file_parity("examples/mood_tracker.nk")

    def test_stdlib_math_nk(self):
        self._assert_file_parity("nekova/stdlib/nk/math.nk")

    def test_stdlib_string_nk(self):
        self._assert_file_parity("nekova/stdlib/nk/string.nk")

    def test_stdlib_date_nk(self):
        self._assert_file_parity("nekova/stdlib/nk/date.nk")

    def test_stdlib_file_nk(self):
        self._assert_file_parity("nekova/stdlib/nk/file.nk")


if __name__ == "__main__":
    unittest.main()