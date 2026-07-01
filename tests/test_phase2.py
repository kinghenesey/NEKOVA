# =============================================================
# NEKOVA — Phase 2 Tests (Lexer)
# =============================================================
# Run with: python tests/test_phase2.py

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer, LexerError
from nekova.lexer.token_types import TokenType


def tokenize(source: str):
    """Helper — tokenize source and return token list."""
    return Lexer(source).tokenize()


def types(source: str):
    """Helper — return just the token types as a list."""
    return [t.type for t in tokenize(source)]


class TestLiterals(unittest.TestCase):

    def test_integer(self):
        tokens = tokenize("42")
        self.assertEqual(tokens[0].type,  TokenType.INTEGER)
        self.assertEqual(tokens[0].value, 42)

    def test_float(self):
        tokens = tokenize("3.14")
        self.assertEqual(tokens[0].type,  TokenType.FLOAT)
        self.assertEqual(tokens[0].value, 3.14)

    def test_string_double_quote(self):
        tokens = tokenize('"Hello"')
        self.assertEqual(tokens[0].type,  TokenType.STRING)
        self.assertEqual(tokens[0].value, "Hello")

    def test_string_single_quote(self):
        tokens = tokenize("'World'")
        self.assertEqual(tokens[0].type,  TokenType.STRING)
        self.assertEqual(tokens[0].value, "World")

    def test_boolean_true(self):
        tokens = tokenize("true")
        self.assertEqual(tokens[0].type,  TokenType.BOOLEAN)
        self.assertEqual(tokens[0].value, True)

    def test_boolean_false(self):
        tokens = tokenize("false")
        self.assertEqual(tokens[0].type,  TokenType.BOOLEAN)
        self.assertEqual(tokens[0].value, False)

    def test_null(self):
        tokens = tokenize("null")
        self.assertEqual(tokens[0].type,  TokenType.NULL)
        self.assertEqual(tokens[0].value, None)


class TestKeywords(unittest.TestCase):

    def test_show(self):
        self.assertIn(TokenType.SHOW, types("show"))

    def test_if(self):
        self.assertIn(TokenType.IF, types("if"))

    def test_else(self):
        self.assertIn(TokenType.ELSE, types("else"))

    def test_repeat(self):
        self.assertIn(TokenType.REPEAT, types("repeat"))

    def test_task(self):
        self.assertIn(TokenType.TASK, types("task"))

    def test_use(self):
        self.assertIn(TokenType.USE, types("use"))


class TestOperators(unittest.TestCase):

    def test_plus(self):
        self.assertIn(TokenType.PLUS, types("+"))

    def test_minus(self):
        self.assertIn(TokenType.MINUS, types("-"))

    def test_equals(self):
        self.assertIn(TokenType.EQUALS, types("=="))

    def test_not_equals(self):
        self.assertIn(TokenType.NOT_EQUALS, types("!="))

    def test_less_eq(self):
        self.assertIn(TokenType.LESS_EQ, types("<="))

    def test_greater_eq(self):
        self.assertIn(TokenType.GREATER_EQ, types(">="))

    def test_power(self):
        self.assertIn(TokenType.POWER, types("**"))

    def test_assign(self):
        self.assertIn(TokenType.ASSIGN, types("="))


class TestFullLines(unittest.TestCase):

    def test_show_string(self):
        t = types('show "Hello"')
        self.assertIn(TokenType.SHOW,   t)
        self.assertIn(TokenType.STRING, t)

    def test_variable_assignment(self):
        t = types('name = "Emmanuel"')
        self.assertIn(TokenType.IDENTIFIER, t)
        self.assertIn(TokenType.ASSIGN,     t)
        self.assertIn(TokenType.STRING,     t)

    def test_if_statement(self):
        t = types("if age >= 18:")
        self.assertIn(TokenType.IF,         t)
        self.assertIn(TokenType.IDENTIFIER, t)
        self.assertIn(TokenType.GREATER_EQ, t)
        self.assertIn(TokenType.INTEGER,    t)
        self.assertIn(TokenType.COLON,      t)

    def test_comment_ignored(self):
        t = types("# this is a comment")
        # Only EOF should be produced
        self.assertEqual(t, [TokenType.EOF])

    def test_eof_always_present(self):
        t = types("")
        self.assertIn(TokenType.EOF, t)


class TestErrors(unittest.TestCase):

    def test_unclosed_string(self):
        with self.assertRaises(LexerError):
            tokenize('"Hello')

    def test_unknown_character(self):
        # @ is now a valid token (decorator syntax) — use a truly unknown char
        with self.assertRaises(LexerError):
            tokenize("~")


class TestBlankLinesInBlocks(unittest.TestCase):
    """
    Blank lines inside indented blocks must not emit spurious
    INDENT or DEDENT tokens. This was a real bug: a blank line
    between two statements inside a task/if/for would produce an
    'Unexpected token INDENT' parse error.
    """

    def _no_spurious_indent(self, tokens):
        """
        Assert that no INDENT token appears where it shouldn't:
        i.e. no INDENT directly preceded by a NEWLINE at the
        same depth (a blank line artefact).
        """
        types = [t.type for t in tokens]
        for i, tt in enumerate(types):
            if tt == TokenType.INDENT and i > 0:
                # INDENT after a NEWLINE that followed another NEWLINE
                # is a blank-line artefact
                if types[i - 1] == TokenType.NEWLINE and i >= 2 and \
                        types[i - 2] == TokenType.NEWLINE:
                    self.fail(
                        "Spurious INDENT after blank line detected "
                        f"at token index {i}: {types[max(0,i-3):i+3]}"
                    )

    def test_blank_line_in_task_body_no_indent_token(self):
        src = "task greet(name):\n    let x = 1\n\n    show x\n"
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        # After the blank line there must not be an INDENT
        # (there's already one at the start of the task body)
        indent_count = types.count(TokenType.INDENT)
        self.assertEqual(indent_count, 1,
            f"Expected 1 INDENT (task body open), got {indent_count}")

    def test_blank_line_in_if_body(self):
        src = "if true:\n    show \"a\"\n\n    show \"b\"\n"
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        self.assertEqual(types.count(TokenType.INDENT), 1)
        self.assertEqual(types.count(TokenType.DEDENT), 1)

    def test_blank_line_in_for_body(self):
        src = "for i in [1, 2]:\n    show i\n\n    show i\n"
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        self.assertEqual(types.count(TokenType.INDENT), 1)

    def test_multiple_consecutive_blank_lines(self):
        src = "task foo():\n    let x = 1\n\n\n\n    show x\n"
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        self.assertEqual(types.count(TokenType.INDENT), 1)

    def test_blank_line_between_nested_blocks(self):
        src = (
            "task outer():\n"
            "    if true:\n"
            "        show \"hi\"\n"
            "\n"
            "        show \"bye\"\n"
        )
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        # Two INDENTs: outer task body + inner if body
        self.assertEqual(types.count(TokenType.INDENT), 2)

    def test_comment_line_inside_block_not_spurious(self):
        src = "task foo():\n    let x = 1\n    # a comment\n    show x\n"
        tokens = tokenize(src)
        types = [t.type for t in tokens]
        self.assertEqual(types.count(TokenType.INDENT), 1)

    def test_blank_line_at_end_of_file_no_error(self):
        src = "show 1\n\n"
        tokens = tokenize(src)
        self.assertIn(TokenType.EOF, [t.type for t in tokens])


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 2 — Lexer Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)