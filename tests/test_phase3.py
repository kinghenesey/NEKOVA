# =============================================================
# NEKOVA — Phase 3 Tests (Parser)
# =============================================================
# Run with: python tests/test_phase3.py

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser, ParseError
from nekova.parser.nodes import (
    Program, AssignStatement, ShowStatement, IfStatement,
    RepeatStatement, TaskStatement, ReturnStatement,
    UseStatement, CallExpression, BinaryOp, Identifier,
    IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, UnaryOp
)


def parse(source: str) -> Program:
    """Helper — lex and parse source, return Program node."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


class TestLiterals(unittest.TestCase):

    def test_integer(self):
        program = parse("x = 42")
        node = program.statements[0]
        self.assertIsInstance(node, AssignStatement)
        self.assertIsInstance(node.value, IntegerLiteral)
        self.assertEqual(node.value.value, 42)

    def test_float(self):
        program = parse("x = 3.14")
        node = program.statements[0]
        self.assertIsInstance(node.value, FloatLiteral)
        self.assertEqual(node.value.value, 3.14)

    def test_string(self):
        program = parse('x = "hello"')
        node = program.statements[0]
        self.assertIsInstance(node.value, StringLiteral)
        self.assertEqual(node.value.value, "hello")

    def test_boolean_true(self):
        program = parse("x = true")
        node = program.statements[0]
        self.assertIsInstance(node.value, BooleanLiteral)
        self.assertEqual(node.value.value, True)

    def test_boolean_false(self):
        program = parse("x = false")
        node = program.statements[0]
        self.assertIsInstance(node.value, BooleanLiteral)
        self.assertEqual(node.value.value, False)

    def test_null(self):
        program = parse("x = null")
        node = program.statements[0]
        self.assertIsInstance(node.value, NullLiteral)


class TestAssignment(unittest.TestCase):

    def test_simple_assign(self):
        program = parse('name = "Emmanuel"')
        node = program.statements[0]
        self.assertIsInstance(node, AssignStatement)
        self.assertEqual(node.name, "name")

    def test_integer_assign(self):
        program = parse("age = 20")
        node = program.statements[0]
        self.assertIsInstance(node, AssignStatement)
        self.assertEqual(node.name, "age")


class TestShowStatement(unittest.TestCase):

    def test_show_string(self):
        program = parse('show "Hello"')
        node = program.statements[0]
        self.assertIsInstance(node, ShowStatement)
        self.assertIsInstance(node.expression, StringLiteral)

    def test_show_identifier(self):
        program = parse("show name")
        node = program.statements[0]
        self.assertIsInstance(node, ShowStatement)
        self.assertIsInstance(node.expression, Identifier)


class TestBinaryOp(unittest.TestCase):

    def test_addition(self):
        program = parse("x = 1 + 2")
        op = program.statements[0].value
        self.assertIsInstance(op, BinaryOp)
        self.assertEqual(op.operator, "+")

    def test_comparison(self):
        program = parse("x = age >= 18")
        op = program.statements[0].value
        self.assertIsInstance(op, BinaryOp)
        self.assertEqual(op.operator, ">=")

    def test_equality(self):
        program = parse('x = name == "NEKOVA"')
        op = program.statements[0].value
        self.assertIsInstance(op, BinaryOp)
        self.assertEqual(op.operator, "==")


class TestIfStatement(unittest.TestCase):

    def test_simple_if(self):
        source = "if age >= 18:\n    show \"Adult\""
        program = parse(source)
        node = program.statements[0]
        self.assertIsInstance(node, IfStatement)
        self.assertIsInstance(node.condition, BinaryOp)
        self.assertEqual(len(node.then_body), 1)
        self.assertEqual(len(node.else_body), 0)

    def test_if_else(self):
        source = (
            "if age >= 18:\n"
            "    show \"Adult\"\n"
            "else:\n"
            "    show \"Minor\""
        )
        program = parse(source)
        node = program.statements[0]
        self.assertIsInstance(node, IfStatement)
        self.assertEqual(len(node.then_body), 1)
        self.assertEqual(len(node.else_body), 1)


class TestRepeatStatement(unittest.TestCase):

    def test_repeat(self):
        source = "repeat 3:\n    show \"Hello\""
        program = parse(source)
        node = program.statements[0]
        self.assertIsInstance(node, RepeatStatement)
        self.assertIsInstance(node.count, IntegerLiteral)
        self.assertEqual(node.count.value, 3)
        self.assertEqual(len(node.body), 1)


class TestTaskStatement(unittest.TestCase):

    def test_simple_task(self):
        source = "task greet(name):\n    show name"
        program = parse(source)
        node = program.statements[0]
        self.assertIsInstance(node, TaskStatement)
        self.assertEqual(node.name, "greet")
        self.assertEqual(node.params, ["name"])
        self.assertEqual(len(node.body), 1)

    def test_task_no_params(self):
        source = "task hello():\n    show \"Hi\""
        program = parse(source)
        node = program.statements[0]
        self.assertIsInstance(node, TaskStatement)
        self.assertEqual(node.params, [])


class TestUseStatement(unittest.TestCase):

    def test_use(self):
        program = parse("use math")
        node = program.statements[0]
        self.assertIsInstance(node, UseStatement)
        self.assertEqual(node.module, "math")


class TestCallExpression(unittest.TestCase):

    def test_call_with_arg(self):
        program = parse('greet("Emmanuel")')
        node = program.statements[0]
        self.assertIsInstance(node, CallExpression)
        self.assertEqual(node.name, "greet")
        self.assertEqual(len(node.args), 1)

    def test_call_no_args(self):
        program = parse("hello()")
        node = program.statements[0]
        self.assertIsInstance(node, CallExpression)
        self.assertEqual(node.args, [])


class TestMultipleStatements(unittest.TestCase):

    def test_multiple_statements(self):
        source = 'name = "Emmanuel"\nage = 20\nshow name'
        program = parse(source)
        self.assertEqual(len(program.statements), 3)
        self.assertIsInstance(program.statements[0], AssignStatement)
        self.assertIsInstance(program.statements[1], AssignStatement)
        self.assertIsInstance(program.statements[2], ShowStatement)


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 3 — Parser Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)