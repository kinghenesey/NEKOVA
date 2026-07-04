"""
Phase 24 — Language Completeness II
Tests for: tuple-style destructuring, named/keyword arguments, const
bindings, spread syntax in list/dict literals, optional chaining
(?.), enums, and the Set type with union/intersection/difference.
"""
import unittest
import sys
import io
import re

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
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


class TestTupleDestructure(unittest.TestCase):
    def test_basic_tuple_destructure(self):
        out = run('let pair = [1, 2]\nlet (a, b) = pair\nshow a\nshow b\n')
        self.assertEqual(out, "1\n2")

    def test_multiple_return_values_via_divmod(self):
        out = run('let (q, r) = divmod(10, 3)\nshow q\nshow r\n')
        self.assertEqual(out, "3\n1")

    def test_tuple_destructure_with_rest(self):
        out = run(
            'let (first, ...rest) = [1, 2, 3, 4]\n'
            'show first\nshow rest\n'
        )
        self.assertEqual(out, "1\n[2, 3, 4]")

    def test_parenthesized_expressions_still_work(self):
        """'let (' must only mean destructuring; parenthesized
        expressions appear after '=', not right after 'let'."""
        out = run('let x = (1 + 2) * 3\nshow x\n')
        self.assertEqual(out, "9")


class TestKeywordArguments(unittest.TestCase):
    def test_both_keyword(self):
        out = run(
            'task greet(name, greeting="Hi"):\n'
            '    return greeting + " " + name\n'
            'show greet(name="Sam", greeting="Yo")\n'
        )
        self.assertEqual(out, "Yo Sam")

    def test_keyword_fills_gap_leaving_default(self):
        out = run(
            'task greet(name="World", greeting="Hello"):\n'
            '    return greeting + " " + name\n'
            'show greet(greeting="Hey")\n'
        )
        self.assertEqual(out, "Hey World")

    def test_mixed_positional_and_keyword(self):
        out = run(
            'task greet(name, greeting="Hi"):\n'
            '    return greeting + " " + name\n'
            'show greet("Sam", greeting="Yo")\n'
        )
        self.assertEqual(out, "Yo Sam")

    def test_typed_task_keyword_args(self):
        out = run(
            'task add(a: int, b: int) -> int:\n'
            '    return a + b\n'
            'show add(a=2, b=3)\n'
        )
        self.assertEqual(out, "5")

    def test_unknown_keyword_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('task greet(name):\n    return name\nshow greet(nam="Sam")\n')

    def test_duplicate_value_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run(
                'task greet(name):\n    return name\n'
                'show greet("Sam", name="Ada")\n'
            )


class TestConstBindings(unittest.TestCase):
    def test_basic_const(self):
        out = run('const MAX = 5\nshow MAX\n')
        self.assertEqual(out, "5")

    def test_reassign_const_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('const MAX = 5\nMAX = 10\nshow MAX\n')

    def test_redeclare_as_const_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('const MAX = 5\nconst MAX = 10\nshow MAX\n')

    def test_let_unaffected(self):
        out = run('let x = 5\nx = 10\nshow x\n')
        self.assertEqual(out, "10")

    def test_const_scoped_to_task(self):
        out = run(
            'task f():\n'
            '    const LOCAL = 1\n'
            '    return LOCAL\n'
            'show f()\nshow f()\n'
        )
        self.assertEqual(out, "1\n1")


class TestSpreadSyntax(unittest.TestCase):
    def test_list_spread(self):
        out = run('let a = [1,2]\nlet b = [3,4]\nshow [...a, ...b]\n')
        self.assertEqual(out, "[1, 2, 3, 4]")

    def test_list_spread_mixed(self):
        out = run('let a = [1,2]\nshow [0, ...a, 99]\n')
        self.assertEqual(out, "[0, 1, 2, 99]")

    def test_dict_spread(self):
        out = run('let a = {"x": 1}\nlet b = {"y": 2}\nshow {...a, ...b}\n')
        self.assertEqual(out, "{x: 1, y: 2}")

    def test_dict_spread_override(self):
        out = run(
            'let defaults = {"x": 1, "y": 2}\n'
            'show {...defaults, "y": 99}\n'
        )
        self.assertEqual(out, "{x: 1, y: 99}")

    def test_spread_non_list_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show [...5]\n')

    def test_spread_non_dict_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show {...5}\n')


class TestOptionalChaining(unittest.TestCase):
    def test_property_access_on_present_value(self):
        out = run(
            'let user = {"name": "Sam", "email": "s@x.com"}\n'
            'show user?.email\n'
        )
        self.assertEqual(out, "s@x.com")

    def test_property_access_on_null_short_circuits(self):
        out = run('let user = null\nshow user?.email\n')
        self.assertEqual(out, "null")

    def test_method_call_on_null_short_circuits(self):
        out = run('let user = null\nshow user?.upper()\n')
        self.assertEqual(out, "null")

    def test_method_call_on_present_value(self):
        out = run('let name = "sam"\nshow name?.upper()\n')
        self.assertEqual(out, "SAM")

    def test_chained_optional_on_null(self):
        out = run('let user = null\nshow user?.profile?.email\n')
        self.assertEqual(out, "null")

    def test_non_optional_dot_after_null_still_raises(self):
        """Only an explicit ?. short-circuits — a plain '.' after a
        null result from an earlier ?. still raises, matching how
        optional chaining works in other languages."""
        with self.assertRaises(Exception):
            run('let user = null\nshow user?.profile.email\n')


class TestEnums(unittest.TestCase):
    def test_member_access(self):
        out = run(
            'enum Status: PENDING, ACTIVE, DONE\n'
            'show Status.ACTIVE\n'
        )
        self.assertEqual(out, "ACTIVE")

    def test_member_equality(self):
        out = run(
            'enum Status: PENDING, ACTIVE, DONE\n'
            'let s = Status.ACTIVE\n'
            'if s == "ACTIVE":\n'
            '    show "is active"\n'
        )
        self.assertEqual(out, "is active")

    def test_enum_in_task_logic(self):
        out = run(
            'enum Status: PENDING, ACTIVE, DONE\n'
            'task describe(s):\n'
            '    if s == Status.DONE:\n'
            '        return "finished"\n'
            '    return "not finished"\n'
            'show describe(Status.DONE)\n'
            'show describe(Status.PENDING)\n'
        )
        self.assertEqual(out, "finished\nnot finished")


class TestSetType(unittest.TestCase):
    def test_basic_set_literal(self):
        out = run('show {1, 2, 3}\n')
        self.assertEqual(out, "{1, 2, 3}")

    def test_set_deduplicates(self):
        out = run('let s = {1, 2, 2, 3, 1}\nshow s\n')
        self.assertEqual(out, "{1, 2, 3}")

    def test_empty_braces_still_dict(self):
        """{} must stay an empty dict — the existing convention —
        not become an ambiguous empty set."""
        out = run('let d = {}\nshow type_of(d)\n')
        self.assertEqual(out, "dict")

    def test_dict_with_colons_unaffected(self):
        out = run('show {"a": 1, "b": 2}\n')
        self.assertEqual(out, "{a: 1, b: 2}")

    def test_multiline_dict_unaffected(self):
        out = run('let d = {\n    "a": 1,\n    "b": 2\n}\nshow d\n')
        self.assertEqual(out, "{a: 1, b: 2}")

    def test_set_union(self):
        out = run('let a = {1,2,3}\nlet b = {3,4,5}\nshow set_union(a, b)\n')
        self.assertEqual(out, "{1, 2, 3, 4, 5}")

    def test_set_intersection(self):
        out = run('let a = {1,2,3}\nlet b = {2,3,4}\nshow set_intersection(a, b)\n')
        self.assertEqual(out, "{2, 3}")

    def test_set_difference(self):
        out = run('let a = {1,2,3}\nlet b = {2,3}\nshow set_difference(a, b)\n')
        self.assertEqual(out, "{1}")

    def test_set_of_strings(self):
        out = run('show {"a", "b", "c"}\n')
        self.assertEqual(out, "{a, b, c}")

    def test_unhashable_element_raises_clean_error(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('show {[1, 2], [3, 4]}\n')


if __name__ == "__main__":
    unittest.main()