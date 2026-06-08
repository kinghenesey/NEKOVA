# =============================================================
# NEKOVA — Phase 4 Tests (Interpreter)
# =============================================================
# Run with: python tests/test_phase4.py

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer
from parser.parser import Parser
from interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """
    Helper — run NEKOVA source and capture printed output.
    Returns everything that was printed as a string.
    """
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    # Capture stdout
    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


class TestVariables(unittest.TestCase):

    def test_string_variable(self):
        output = run('name = "Emmanuel"\nshow name')
        self.assertEqual(output, "Emmanuel")

    def test_integer_variable(self):
        output = run("age = 20\nshow age")
        self.assertEqual(output, "20")

    def test_float_variable(self):
        output = run("pi = 3.14\nshow pi")
        self.assertEqual(output, "3.14")

    def test_boolean_true(self):
        output = run("x = true\nshow x")
        self.assertEqual(output, "true")

    def test_boolean_false(self):
        output = run("x = false\nshow x")
        self.assertEqual(output, "false")

    def test_null(self):
        output = run("x = null\nshow x")
        self.assertEqual(output, "null")


class TestShowStatement(unittest.TestCase):

    def test_show_string(self):
        output = run('show "Hello NEKOVA"')
        self.assertEqual(output, "Hello NEKOVA")

    def test_show_integer(self):
        output = run("show 42")
        self.assertEqual(output, "42")

    def test_show_expression(self):
        output = run("show 2 + 3")
        self.assertEqual(output, "5")


class TestArithmetic(unittest.TestCase):

    def test_addition(self):
        output = run("show 10 + 5")
        self.assertEqual(output, "15")

    def test_subtraction(self):
        output = run("show 10 - 3")
        self.assertEqual(output, "7")

    def test_multiplication(self):
        output = run("show 4 * 3")
        self.assertEqual(output, "12")

    def test_division(self):
        output = run("show 10 / 2")
        self.assertEqual(output, "5.0")

    def test_modulo(self):
        output = run("show 10 % 3")
        self.assertEqual(output, "1")

    def test_power(self):
        output = run("show 2 ** 8")
        self.assertEqual(output, "256")


class TestStringConcatenation(unittest.TestCase):

    def test_concat_strings(self):
        output = run('show "Hello " + "NEKOVA"')
        self.assertEqual(output, "Hello NEKOVA")

    def test_concat_string_variable(self):
        output = run('name = "Emmanuel"\nshow "Hello " + name')
        self.assertEqual(output, "Hello Emmanuel")


class TestIfStatement(unittest.TestCase):

    def test_if_true(self):
        source = "if 10 > 5:\n    show \"yes\""
        output = run(source)
        self.assertEqual(output, "yes")

    def test_if_false(self):
        source = "if 10 > 20:\n    show \"yes\""
        output = run(source)
        self.assertEqual(output, "")

    def test_if_else_true(self):
        source = (
            "age = 20\n"
            "if age >= 18:\n"
            "    show \"adult\"\n"
            "else:\n"
            "    show \"minor\""
        )
        output = run(source)
        self.assertEqual(output, "adult")

    def test_if_else_false(self):
        source = (
            "age = 15\n"
            "if age >= 18:\n"
            "    show \"adult\"\n"
            "else:\n"
            "    show \"minor\""
        )
        output = run(source)
        self.assertEqual(output, "minor")


class TestRepeatStatement(unittest.TestCase):

    def test_repeat(self):
        source = "repeat 3:\n    show \"hi\""
        output = run(source)
        self.assertEqual(output, "hi\nhi\nhi")

    def test_repeat_once(self):
        source = "repeat 1:\n    show \"once\""
        output = run(source)
        self.assertEqual(output, "once")


class TestTaskStatement(unittest.TestCase):

    def test_simple_task(self):
        source = (
            "task greet(name):\n"
            "    show \"Hello \" + name\n"
            'greet("Emmanuel")'
        )
        output = run(source)
        self.assertEqual(output, "Hello Emmanuel")

    def test_task_return(self):
        source = (
            "task double(x):\n"
            "    return x * 2\n"
            "result = double(5)\n"
            "show result"
        )
        output = run(source)
        self.assertEqual(output, "10")

    def test_task_no_params(self):
        source = (
            "task say_hello():\n"
            "    show \"Hello!\"\n"
            "say_hello()"
        )
        output = run(source)
        self.assertEqual(output, "Hello!")


class TestBuiltins(unittest.TestCase):

    def test_length(self):
        output = run('show length("NEKOVA")')
        self.assertEqual(output, "4")

    def test_to_text(self):
        output = run("show to_text(42)")
        self.assertEqual(output, "42")


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 4 — Interpreter Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)