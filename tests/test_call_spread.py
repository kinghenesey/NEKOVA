"""
Call-site spread arguments — f(...args)

Found during a broad test-everything-in-the-language QA sweep: NEKOVA
had `*rest` on the parameter-declaration side and `[...a, ...b]` in
list/dict literals, but no way to forward a collected argument list
back out as separate arguments at a call site. GRAMMAR.md's own
call_args rule confirmed it (`expression { ',' expression }`), and
there was no apply()-style builtin either.

The practical consequence: a decorator's wrapper had to hardcode an
exact parameter count, so no decorator could work on functions of
differing arity. Every existing decorator test in test_phase17.py
hardcodes exactly one parameter name — the limitation was baked into
the test suite's own assumptions rather than being noticed.

'...expr' at a call site is the missing third piece, deliberately
reusing the spread syntax and the same SpreadElement node the list
and dict literals already use, rather than inventing a separate
mechanism.
"""
import io
import re
import sys
import unittest

REPO_ROOT = __import__("os").path.dirname(
    __import__("os").path.dirname(__import__("os").path.abspath(__file__))
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def run(source: str) -> str:
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


class TestBasicCallSpread(unittest.TestCase):

    def test_spread_list_into_call(self):
        out = run(
            'task add(a, b):\n'
            '    return a + b\n'
            'let nums = [2, 3]\n'
            'show add(...nums)\n'
        )
        self.assertEqual(out, "5")

    def test_spread_tuple_into_call(self):
        out = run(
            'task add(a, b):\n'
            '    return a + b\n'
            'let t = (7, 8)\n'
            'show add(...t)\n'
        )
        self.assertEqual(out, "15")

    def test_mixed_positional_and_spread(self):
        out = run(
            'task three(a, b, c):\n'
            '    return a + b + c\n'
            'let pair = [2, 3]\n'
            'show three(1, ...pair)\n'
        )
        self.assertEqual(out, "6")

    def test_empty_spread(self):
        out = run(
            'task noargs():\n'
            '    return "ok"\n'
            'let empty = []\n'
            'show noargs(...empty)\n'
        )
        self.assertEqual(out, "ok")

    def test_spread_into_builtin(self):
        out = run(
            'let nums = [3, 1, 2]\n'
            'show max(...nums)\n'
            'show min(...nums)\n'
        )
        self.assertEqual(out, "3\n1")

    def test_spread_into_method_call(self):
        """_exec_MethodCall evaluates its own args separately from
        _exec_CallExpression — both must expand spreads, hence the
        shared _eval_call_args helper."""
        out = run(
            'task pick(a, b):\n'
            '    return a + b\n'
            'let parts = ["x", "y"]\n'
            'show pick(...parts)\n'
        )
        self.assertEqual(out, "xy")


class TestSpreadEnablesGenericDecorators(unittest.TestCase):
    """The actual motivation: one decorator, any arity."""

    def test_one_decorator_wraps_different_arities(self):
        out = run(
            'task log_calls(fn):\n'
            '    task wrapper(*rest):\n'
            '        show "calling"\n'
            '        return fn(...rest)\n'
            '    return wrapper\n'
            '@log_calls\n'
            'task multiply(a, b):\n'
            '    return a * b\n'
            '@log_calls\n'
            'task greet(name):\n'
            '    return "Hello, " + name\n'
            'show multiply(4, 5)\n'
            'show greet("World")\n'
        )
        self.assertEqual(out, "calling\n20\ncalling\nHello, World")


class TestSpreadErrors(unittest.TestCase):

    def test_spreading_a_non_list_raises(self):
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run(
                'task f(a):\n'
                '    return a\n'
                'let x = 5\n'
                'show f(...x)\n'
            )
        self.assertIn("Cannot spread", str(ctx.exception))

    def test_spreading_a_string_raises(self):
        """A string is iterable in Python but isn't a list — spreading
        one should fail rather than silently explode into characters,
        matching how list-literal spread already behaves."""
        with self.assertRaises(NEKOVARuntimeError):
            run(
                'task f(a):\n'
                '    return a\n'
                'show f(..."abc")\n'
            )


class TestSelfHostedParserParity(unittest.TestCase):
    """parser.nk has two separate call-parsing paths (parse_call_args
    and finish_call) — both need spread, or one call form silently
    works and the other doesn't."""

    def test_spread_parses_identically_in_both_parsers(self):
        from nekova.parser.rehydrate import parse_self_hosted

        source = (
            'task add(a, b):\n'
            '    return a + b\n'
            'let nums = [2, 3]\n'
            'show add(...nums)\n'
        )

        def serialize(value):
            if hasattr(value, "__dict__"):
                out = {"type": type(value).__name__}
                for key, sub in vars(value).items():
                    if key == "line":
                        continue
                    out[key] = serialize(sub)
                return out
            if isinstance(value, dict):
                return {k: serialize(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [serialize(v) for v in value]
            return value

        py = Parser(Lexer(source).tokenize()).parse()
        nk = parse_self_hosted(source)
        self.assertEqual(serialize(py), serialize(nk))


if __name__ == "__main__":
    unittest.main()