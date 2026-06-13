# =============================================================
# NEKOVA Phase 9 Tests — Multi-file Modules & F-Strings
# =============================================================

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(code, current_file=None):
    """Helper — tokenize, parse, execute, return interpreter."""
    interp = Interpreter()
    if current_file:
        interp._current_file = current_file
    tokens  = Lexer(code).tokenize()
    program = Parser(tokens).parse()
    interp.execute(program)
    return interp


class TestFStrings(unittest.TestCase):

    def test_basic_fstring(self):
        interp = run('name = "Emmanuel"\nresult = f"Hello {name}!"')
        self.assertEqual(interp.env.get("result"), "Hello Emmanuel!")

    def test_fstring_expression(self):
        interp = run('a = 10\nb = 5\nresult = f"Sum: {a + b}"')
        self.assertEqual(interp.env.get("result"), "Sum: 15")

    def test_fstring_multiple_vars(self):
        interp = run('x = "NEKOVA"\ny = "forge"\nresult = f"{x} connected {y}"')
        self.assertEqual(interp.env.get("result"), "NEKOVA connected forge")

    def test_fstring_math(self):
        interp = run('n = 7\nresult = f"Square: {n * n}"')
        self.assertEqual(interp.env.get("result"), "Square: 49")

    def test_fstring_nested_in_show(self):
        """f-strings work inside show statements."""
        # Just verify it doesn't crash
        run('lang = "NEKOVA"\nshow f"Welcome to {lang}!"')

    def test_fstring_with_number_result(self):
        interp = run('result = f"Pi is about {3 + 0}"')
        self.assertIn("3", interp.env.get("result"))


class TestMultiFileModules(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory with test .nk files."""
        self.tmpdir = tempfile.mkdtemp()

        # Create a utils module
        utils_code = '''
PI = 3.14159

task greet(name):
    return f"Hello {name}!"

task add(a, b):
    return a + b

task square(n):
    return n * n
'''
        self.utils_path = os.path.join(self.tmpdir, "utils.nk")
        with open(self.utils_path, "w") as f:
            f.write(utils_code)

        # Create a math module
        math_code = '''
task multiply(a, b):
    return a * b

task power(base, exp):
    result = 1
    repeat exp:
        result = result * base
    return result
'''
        self.math_path = os.path.join(self.tmpdir, "mathlib.nk")
        with open(self.math_path, "w") as f:
            f.write(math_code)

    def _run_with_dir(self, code):
        """Run code with tmpdir as the current file location."""
        main_path = os.path.join(self.tmpdir, "main.nk")
        interp = Interpreter()
        interp._current_file = main_path
        tokens  = Lexer(code).tokenize()
        program = Parser(tokens).parse()
        interp.execute(program)
        return interp

    def test_star_import(self):
        """import 'utils.nk' brings all names into scope."""
        interp = self._run_with_dir('import "utils.nk"')
        # PI should be available
        self.assertAlmostEqual(float(interp.env.get("PI")), 3.14159)

    def test_named_import_single(self):
        """import add from 'utils.nk' brings only add."""
        interp = self._run_with_dir(
            'import add from "utils.nk"\nresult = add(3, 4)')
        self.assertEqual(interp.env.get("result"), 7)

    def test_named_import_multiple(self):
        """import greet, square from 'utils.nk'."""
        interp = self._run_with_dir(
            'import greet, square from "utils.nk"\n'
            'msg = greet("World")\n'
            'sq = square(5)'
        )
        self.assertEqual(interp.env.get("msg"), "Hello World!")
        self.assertEqual(interp.env.get("sq"), 25)

    def test_auto_nk_extension(self):
        """import 'utils' (no extension) auto-adds .nk."""
        interp = self._run_with_dir('import "utils"\nresult = add(1, 2)')
        self.assertEqual(interp.env.get("result"), 3)

    def test_circular_import_prevention(self):
        """Importing the same file twice doesn't re-execute it."""
        interp = self._run_with_dir(
            'import "utils.nk"\nimport "utils.nk"\nresult = add(1, 1)')
        self.assertEqual(interp.env.get("result"), 2)

    def test_import_named_not_found_raises(self):
        """Importing a non-existent name raises RuntimeError."""
        with self.assertRaises(Exception):
            self._run_with_dir('import nonexistent from "utils.nk"')

    def test_import_file_not_found_raises(self):
        """Importing a non-existent file raises RuntimeError."""
        with self.assertRaises(Exception):
            self._run_with_dir('import "doesnotexist.nk"')


if __name__ == "__main__":
    unittest.main()
