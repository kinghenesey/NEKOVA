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
        with self.assertRaises(LexerError):
            tokenize("@")


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 2 — Lexer Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)