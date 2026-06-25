"""
Phase 15 — Stability Tests
RED:    in/not in, // floor div, range(), list slicing, exception objects,
        core builtins (len, str, int, abs, round, min, max, sum)
YELLOW: default params, raise, finally, f-string expressions,
        pass, assert, multi-arg show, is/is not, *args, ternary
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
    """Run NEKOVA source and return captured stdout."""
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


class TestInOperator(unittest.TestCase):
    def test_in_list(self):
        out = run('show 3 in [1, 2, 3]')
        self.assertEqual(out, "true")

    def test_not_in_list(self):
        out = run('show 5 not in [1, 2, 3]')
        self.assertEqual(out, "true")

    def test_in_string(self):
        out = run('show "ell" in "hello"')
        self.assertEqual(out, "true")

    def test_not_in_string(self):
        out = run('show "xyz" not in "hello"')
        self.assertEqual(out, "true")

    def test_in_for_loop(self):
        out = run(
            'let items = [1, 2, 3]\n'
            'if 2 in items:\n'
            '    show "found"'
        )
        self.assertEqual(out, "found")


class TestFloorDivision(unittest.TestCase):
    def test_basic_floor_div(self):
        out = run('show 7 // 2')
        self.assertEqual(out, "3")

    def test_floor_div_negative(self):
        out = run('show -7 // 2')
        self.assertEqual(out, "-4")

    def test_floor_div_assign(self):
        out = run('let x = 10 // 3\nshow x')
        self.assertEqual(out, "3")


class TestRangeBuiltin(unittest.TestCase):
    def test_range_one_arg(self):
        out = run(
            'let r = range(5)\n'
            'show r'
        )
        self.assertIn("0", out)
        self.assertIn("4", out)

    def test_range_two_args(self):
        out = run(
            'let total = 0\n'
            'for i in range(1, 4):\n'
            '    let total = total + i\n'
            'show total'
        )
        self.assertEqual(out, "6")

    def test_range_three_args(self):
        out = run(
            'let nums = range(0, 10, 2)\n'
            'show len(nums)'
        )
        self.assertEqual(out, "5")


class TestListSlicing(unittest.TestCase):
    def test_slice_start_stop(self):
        out = run('let x = [1, 2, 3, 4, 5]\nshow x[1:3]')
        self.assertIn("2", out)
        self.assertIn("3", out)

    def test_slice_from_start(self):
        out = run('let x = [10, 20, 30, 40]\nshow x[:2]')
        self.assertIn("10", out)
        self.assertIn("20", out)

    def test_slice_to_end(self):
        out = run('let x = [10, 20, 30, 40]\nshow x[2:]')
        self.assertIn("30", out)
        self.assertIn("40", out)

    def test_string_slice(self):
        out = run('let s = "hello"\nshow s[1:4]')
        self.assertEqual(out, "ell")


class TestCoreBuiltins(unittest.TestCase):
    def test_len(self):
        out = run('show len([1, 2, 3])')
        self.assertEqual(out, "3")

    def test_str(self):
        out = run('show str(42)')
        self.assertEqual(out, "42")

    def test_int(self):
        out = run('show int("10")')
        self.assertEqual(out, "10")

    def test_abs(self):
        out = run('show abs(-5)')
        self.assertEqual(out, "5")

    def test_round(self):
        out = run('show round(3.7)')
        self.assertIn(out, ["4", "4.0"])

    def test_min(self):
        out = run('show min(3, 1, 2)')
        self.assertEqual(out, "1")

    def test_max(self):
        out = run('show max(3, 1, 2)')
        self.assertEqual(out, "3")

    def test_sum(self):
        out = run('show sum([1, 2, 3, 4])')
        self.assertEqual(out, "10")

    def test_sorted_list(self):
        out = run('show sorted([3, 1, 2])')
        self.assertIn("1", out)

    def test_reversed_list(self):
        out = run('show reversed([1, 2, 3])')
        self.assertIn("3", out)


class TestExceptionObjects(unittest.TestCase):
    def test_catch_error_var(self):
        out = run(
            'try:\n'
            '    let x = 1 / 0\n'
            'catch err:\n'
            '    show "caught"'
        )
        self.assertEqual(out, "caught")

    def test_raise_and_catch(self):
        out = run(
            'try:\n'
            '    raise "custom error"\n'
            'catch e:\n'
            '    show e'
        )
        self.assertEqual(out, "custom error")


class TestDefaultParams(unittest.TestCase):
    def test_default_param_used(self):
        out = run(
            'task greet(name, greeting="Hello"):\n'
            '    show greeting + " " + name\n'
            'greet("World")'
        )
        self.assertEqual(out, "Hello World")

    def test_default_param_overridden(self):
        out = run(
            'task greet(name, greeting="Hello"):\n'
            '    show greeting + " " + name\n'
            'greet("World", "Hi")'
        )
        self.assertEqual(out, "Hi World")

    def test_multiple_defaults(self):
        out = run(
            'task add(a, b=10, c=5):\n'
            '    show a + b + c\n'
            'add(1)'
        )
        self.assertEqual(out, "16")


class TestRaise(unittest.TestCase):
    def test_raise_string(self):
        out = run(
            'try:\n'
            '    raise "oops"\n'
            'catch e:\n'
            '    show "caught: " + e'
        )
        self.assertEqual(out, "caught: oops")

    def test_raise_propagates(self):
        """Unhandled raise should surface as error."""
        from nekova.interpreter.exceptions import NEKOVARaiseError
        with self.assertRaises(NEKOVARaiseError):
            run('raise "uncaught"')


class TestFinally(unittest.TestCase):
    def test_finally_runs_on_success(self):
        out = run(
            'try:\n'
            '    show "try"\n'
            'catch e:\n'
            '    show "catch"\n'
            'finally:\n'
            '    show "finally"'
        )
        self.assertIn("try", out)
        self.assertIn("finally", out)
        self.assertNotIn("catch", out)

    def test_finally_runs_on_error(self):
        out = run(
            'try:\n'
            '    raise "err"\n'
            'catch e:\n'
            '    show "catch"\n'
            'finally:\n'
            '    show "finally"'
        )
        self.assertIn("catch", out)
        self.assertIn("finally", out)


class TestPass(unittest.TestCase):
    def test_pass_in_if(self):
        out = run(
            'if true:\n'
            '    pass\n'
            'show "done"'
        )
        self.assertEqual(out, "done")

    def test_pass_in_task(self):
        out = run(
            'task noop():\n'
            '    pass\n'
            'noop()\n'
            'show "ok"'
        )
        self.assertEqual(out, "ok")


class TestAssert(unittest.TestCase):
    def test_assert_passes(self):
        out = run(
            'assert 1 == 1\n'
            'show "passed"'
        )
        self.assertEqual(out, "passed")

    def test_assert_fails_with_message(self):
        from nekova.interpreter.exceptions import NEKOVAAssertionError
        with self.assertRaises(NEKOVAAssertionError):
            run('assert 1 == 2, "should fail"')

    def test_assert_caught(self):
        out = run(
            'try:\n'
            '    assert false, "bad"\n'
            'catch e:\n'
            '    show "assertion caught"'
        )
        self.assertEqual(out, "assertion caught")


class TestMultiArgShow(unittest.TestCase):
    def test_show_two_values(self):
        out = run('show "x =", 42')
        self.assertEqual(out, "x = 42")

    def test_show_three_values(self):
        out = run('show "a", "b", "c"')
        self.assertEqual(out, "a b c")


class TestIsIsNot(unittest.TestCase):
    def test_is_none(self):
        out = run('let x = null\nshow x is null')
        self.assertEqual(out, "true")

    def test_is_not_none(self):
        out = run('let x = 5\nshow x is not null')
        self.assertEqual(out, "true")


class TestVarargs(unittest.TestCase):
    def test_basic_varargs(self):
        out = run(
            'task mysum(*nums):\n'
            '    let total = 0\n'
            '    for n in nums:\n'
            '        let total = total + n\n'
            '    return total\n'
            'show mysum(1, 2, 3)'
        )
        self.assertEqual(out, "6")

    def test_varargs_empty(self):
        out = run(
            'task count(*items):\n'
            '    return len(items)\n'
            'show count()'
        )
        self.assertEqual(out, "0")

    def test_mixed_args_and_varargs(self):
        out = run(
            'task head_rest(first, *rest):\n'
            '    show first\n'
            '    show len(rest)\n'
            'head_rest("a", "b", "c")'
        )
        lines = out.split("\n")
        self.assertEqual(lines[0], "a")
        self.assertEqual(lines[1], "2")


class TestTernary(unittest.TestCase):
    def test_basic_ternary_true(self):
        out = run('show "yes" if true else "no"')
        self.assertEqual(out, "yes")

    def test_basic_ternary_false(self):
        out = run('show "yes" if false else "no"')
        self.assertEqual(out, "no")

    def test_ternary_in_expression(self):
        out = run(
            'let x = 10\n'
            'let label = "big" if x > 5 else "small"\n'
            'show label'
        )
        self.assertEqual(out, "big")

    def test_ternary_with_variables(self):
        out = run(
            'let a = 3\n'
            'let b = 7\n'
            'show a if a > b else b'
        )
        self.assertEqual(out, "7")


if __name__ == "__main__":
    unittest.main()