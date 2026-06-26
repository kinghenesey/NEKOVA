"""
Phase 17 — Power User Layer
Tests for: generators/yield, decorators/@, error types, typed tasks
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
    return re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue()).strip()


def run_interp(source: str):
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
    return re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue()).strip(), interp


# ── Generators / yield ────────────────────────────────────────

class TestGenerators(unittest.TestCase):

    def test_yield_parses(self):
        src = 'task gen():\n    yield 1'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import YieldStatement
        body = ast.statements[0].body
        self.assertIsInstance(body[0], YieldStatement)

    def test_simple_generator(self):
        src = (
            'task nums():\n'
            '    yield 1\n'
            '    yield 2\n'
            '    yield 3\n'
            'for n in nums():\n'
            '    show n'
        )
        out = run(src)
        self.assertEqual(out, "1\n2\n3")

    def test_generator_with_while(self):
        src = (
            'task count(n: int):\n'
            '    let i = 0\n'
            '    while i < n:\n'
            '        yield i\n'
            '        let i = i + 1\n'
            'for x in count(4):\n'
            '    show x'
        )
        out = run(src)
        self.assertEqual(out, "0\n1\n2\n3")

    def test_generator_collect_to_list(self):
        src = (
            'task squares(n: int):\n'
            '    let i = 1\n'
            '    while i <= n:\n'
            '        yield i * i\n'
            '        let i = i + 1\n'
            'let result = []\n'
            'for s in squares(4):\n'
            '    result.append(s)\n'
            'show len(result)'
        )
        out = run(src)
        self.assertEqual(out, "4")

    def test_generator_sum(self):
        src = (
            'task range_gen(n: int):\n'
            '    let i = 0\n'
            '    while i < n:\n'
            '        yield i\n'
            '        let i = i + 1\n'
            'let total = 0\n'
            'for v in range_gen(5):\n'
            '    let total = total + v\n'
            'show total'
        )
        out = run(src)
        self.assertEqual(out, "10")

    def test_generator_with_condition(self):
        src = (
            'task evens(n: int):\n'
            '    let i = 0\n'
            '    while i < n:\n'
            '        if i % 2 == 0:\n'
            '            yield i\n'
            '        let i = i + 1\n'
            'for e in evens(6):\n'
            '    show e'
        )
        out = run(src)
        self.assertEqual(out, "0\n2\n4")

    def test_yield_none(self):
        src = (
            'task gen():\n'
            '    yield\n'
            '    yield\n'
            'let count = 0\n'
            'for _ in gen():\n'
            '    let count = count + 1\n'
            'show count'
        )
        out = run(src)
        self.assertEqual(out, "2")

    def test_generator_is_iterable(self):
        src = (
            'task letters():\n'
            '    yield "a"\n'
            '    yield "b"\n'
            '    yield "c"\n'
            'let result = ""\n'
            'for ch in letters():\n'
            '    let result = result + ch\n'
            'show result'
        )
        out = run(src)
        self.assertEqual(out, "abc")


# ── Decorators ────────────────────────────────────────────────

class TestDecorators(unittest.TestCase):

    def test_decorator_parses(self):
        src = '@memoize\ntask fib(n):\n    return n'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import DecoratorStatement
        self.assertIsInstance(ast.statements[0], DecoratorStatement)

    def test_basic_decorator(self):
        src = (
            'task uppercase(fn):\n'
            '    task wrapper(x):\n'
            '        return fn(x) + "!"\n'
            '    return wrapper\n'
            '@uppercase\n'
            'task greet(name):\n'
            '    return "Hello " + name\n'
            'show greet("Emmanuel")'
        )
        out = run(src)
        self.assertEqual(out, "Hello Emmanuel!")

    def test_decorator_with_args(self):
        src = (
            'task repeat(n):\n'
            '    task decorator(fn):\n'
            '        task wrapper(x):\n'
            '            let result = ""\n'
            '            let i = 0\n'
            '            while i < n:\n'
            '                let result = result + fn(x)\n'
            '                let i = i + 1\n'
            '            return result\n'
            '        return wrapper\n'
            '    return decorator\n'
            '@repeat(3)\n'
            'task stamp(s):\n'
            '    return s\n'
            'show stamp("*")'
        )
        out = run(src)
        self.assertEqual(out, "***")

    def test_memoize_decorator(self):
        """Built-in memoize pattern via decorator — tracks call count."""
        src = (
            'let call_count = 0\n'
            'task counted(fn):\n'
            '    task wrapper(n):\n'
            '        let call_count = call_count + 1\n'
            '        return fn(n)\n'
            '    return wrapper\n'
            '@counted\n'
            'task double(n):\n'
            '    return n * 2\n'
            'show double(5)\n'
            'show double(10)'
        )
        out = run(src)
        lines = out.split("\n")
        self.assertEqual(lines[0], "10")
        self.assertEqual(lines[1], "20")

    def test_decorator_preserves_name(self):
        src = (
            'task identity(fn):\n'
            '    return fn\n'
            '@identity\n'
            'task add(a, b):\n'
            '    return a + b\n'
            'show add(2, 3)'
        )
        out = run(src)
        self.assertEqual(out, "5")


# ── Error Types ───────────────────────────────────────────────

class TestErrorTypes(unittest.TestCase):

    def test_error_def_parses(self):
        src = 'error NetworkError:\n    message str\n    code int'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import ErrorDefinition
        self.assertIsInstance(ast.statements[0], ErrorDefinition)
        self.assertEqual(ast.statements[0].name, "NetworkError")

    def test_error_constructor(self):
        src = (
            'error NetworkError:\n'
            '    message str\n'
            '    code int\n'
            'let e = NetworkError("timeout", 408)\n'
            'show e["message"]'
        )
        out = run(src)
        self.assertEqual(out, "timeout")

    def test_error_default_field(self):
        src = (
            'error AppError:\n'
            '    message str\n'
            '    code int = 500\n'
            'let e = AppError("server error")\n'
            'show e["code"]'
        )
        out = run(src)
        self.assertEqual(out, "500")

    def test_error_type_marker(self):
        src = (
            'error AuthError:\n'
            '    message str\n'
            'let e = AuthError("unauthorized")\n'
            'show e["__error__"]'
        )
        out = run(src)
        self.assertEqual(out, "AuthError")

    def test_raise_error_object(self):
        src = (
            'error ValidationError:\n'
            '    message str\n'
            '    field str\n'
            'try:\n'
            '    raise ValidationError("required", "email")\n'
            'catch e:\n'
            '    show e["message"]'
        )
        out = run(src)
        self.assertEqual(out, "required")

    def test_multiple_error_types(self):
        src = (
            'error NotFoundError:\n'
            '    message str\n'
            'error ServerError:\n'
            '    message str\n'
            '    code int = 500\n'
            'let e1 = NotFoundError("not found")\n'
            'let e2 = ServerError("crash")\n'
            'show e1["__error__"]\n'
            'show e2["__error__"]'
        )
        out = run(src)
        lines = out.split("\n")
        self.assertEqual(lines[0], "NotFoundError")
        self.assertEqual(lines[1], "ServerError")


# ── Typed Tasks ───────────────────────────────────────────────

class TestTypedTasks(unittest.TestCase):

    def test_typed_task_parses(self):
        src = 'task add(a: int, b: int) -> int:\n    return a + b'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import TypedTaskStatement
        node = ast.statements[0]
        self.assertIsInstance(node, TypedTaskStatement)
        self.assertEqual(node.return_type, "int")

    def test_typed_params_parsed(self):
        src = 'task greet(name: str, times: int):\n    return name'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.statements[0]
        from nekova.parser.nodes import TypedTaskStatement
        self.assertIsInstance(node, TypedTaskStatement)
        self.assertEqual(node.params[0][1], "str")
        self.assertEqual(node.params[1][1], "int")

    def test_typed_task_runs(self):
        src = (
            'task add(a: int, b: int) -> int:\n'
            '    return a + b\n'
            'show add(3, 4)'
        )
        out = run(src)
        self.assertEqual(out, "7")

    def test_typed_task_string_param(self):
        src = (
            'task greet(name: str) -> str:\n'
            '    return "Hello " + name\n'
            'show greet("Emmanuel")'
        )
        out = run(src)
        self.assertEqual(out, "Hello Emmanuel")

    def test_typed_task_with_default(self):
        src = (
            'task greet(name: str, greeting: str = "Hi") -> str:\n'
            '    return greeting + " " + name\n'
            'show greet("World")'
        )
        out = run(src)
        self.assertEqual(out, "Hi World")

    def test_type_error_enforced(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        src = (
            'task double(n: int) -> int:\n'
            '    return n * 2\n'
            'show double("hello")'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_return_type_annotation_only(self):
        src = (
            'task pi() -> float:\n'
            '    return 3.14159\n'
            'show pi()'
        )
        out = run(src)
        self.assertIn("3.14159", out)


# ── class keyword (alias for object) ─────────────────────────

class TestClassKeyword(unittest.TestCase):

    def test_class_parses(self):
        src = 'class Point:\n    x: int\n    y: int\n    init(x: int, y: int):\n        self.x = x\n        self.y = y'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import ClassDefinition
        self.assertIsInstance(ast.statements[0], ClassDefinition)

    def test_class_instantiation(self):
        src = (
            'class Animal:\n'
            '    name: str\n'
            '    init(name: str):\n'
            '        self.name = name\n'
            '    func speak():\n'
            '        return self.name + " speaks"\n'
            'let a = new Animal("Dog")\n'
            'show a.speak()'
        )
        out = run(src)
        self.assertEqual(out, "Dog speaks")

    def test_class_inheritance(self):
        src = (
            'class Vehicle:\n'
            '    speed: int\n'
            '    init(speed: int):\n'
            '        self.speed = speed\n'
            '    func describe():\n'
            '        return "speed: " + str(self.speed)\n'
            'class Car extends Vehicle:\n'
            '    init(speed: int):\n'
            '        self.speed = speed\n'
            '    func honk():\n'
            '        return "Beep!"\n'
            'let c = new Car(120)\n'
            'show c.describe()\n'
            'show c.honk()'
        )
        out = run(src)
        lines = out.split("\n")
        self.assertEqual(lines[0], "speed: 120")
        self.assertEqual(lines[1], "Beep!")


if __name__ == "__main__":
    unittest.main()