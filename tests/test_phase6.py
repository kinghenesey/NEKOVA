# =============================================================
# NEKOVA — Phase 6 Tests: Classes & Objects
# =============================================================
# Run with: python -m pytest tests/test_phase6.py -v

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError


def run(source: str) -> str:
    """Helper — run NEKOVA source and capture printed output."""
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


# ------------------------------------------------------------------
# Basic class definition and instantiation
# ------------------------------------------------------------------

class TestClassDefinition(unittest.TestCase):

    def test_simple_class_no_init(self):
        src = (
            'object Point:\n'
            '    x: number\n'
            '    y: number\n'
            '\n'
            'let p = new Point(3, 7)\n'
            'show p.x\n'
            'show p.y\n'
        )
        self.assertEqual(run(src), '3\n7')

    def test_class_with_init(self):
        src = (
            'object Person:\n'
            '    name: text\n'
            '    age: number\n'
            '\n'
            '    init(name: text, age: number):\n'
            '        self.name = name\n'
            '        self.age = age\n'
            '\n'
            'let p = new Person("Emmanuel", 25)\n'
            'show p.name\n'
            'show p.age\n'
        )
        self.assertEqual(run(src), 'Emmanuel\n25')

    def test_class_with_method(self):
        src = (
            'object Greeter:\n'
            '    name: text\n'
            '\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '\n'
            '    func greet():\n'
            '        return "Hello!"\n'
            '\n'
            'let g = new Greeter("World")\n'
            'show g.greet()\n'
        )
        self.assertEqual(run(src), 'Hello!')

    def test_method_uses_self_attribute(self):
        src = (
            'object Person:\n'
            '    name: text\n'
            '\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '\n'
            '    func greet():\n'
            '        return "Hi, I\'m " + self.name\n'
            '\n'
            'let p = new Person("Emmanuel")\n'
            'show p.greet()\n'
        )
        self.assertEqual(run(src), "Hi, I'm Emmanuel")

    def test_multiple_instances_independent(self):
        src = (
            'object Box:\n'
            '    val: number\n'
            '    init(v: number):\n'
            '        self.val = v\n'
            '\n'
            'let a = new Box(10)\n'
            'let b = new Box(99)\n'
            'show a.val\n'
            'show b.val\n'
        )
        self.assertEqual(run(src), '10\n99')


# ------------------------------------------------------------------
# Mutating state via methods
# ------------------------------------------------------------------

class TestMutation(unittest.TestCase):

    def test_method_mutates_attribute(self):
        src = (
            'object Box:\n'
            '    val: number\n'
            '    init(v: number):\n'
            '        self.val = v\n'
            '    func double():\n'
            '        self.val = self.val * 2\n'
            '\n'
            'let b = new Box(5)\n'
            'b.double()\n'
            'show b.val\n'
        )
        self.assertEqual(run(src), '10')

    def test_counter_increment(self):
        src = (
            'object Counter:\n'
            '    count: number\n'
            '    init():\n'
            '        self.count = 0\n'
            '    func increment():\n'
            '        self.count = self.count + 1\n'
            '    func get():\n'
            '        return self.count\n'
            '\n'
            'let c = new Counter()\n'
            'c.increment()\n'
            'c.increment()\n'
            'c.increment()\n'
            'show c.get()\n'
        )
        self.assertEqual(run(src), '3')

    def test_method_with_argument(self):
        src = (
            'object Accumulator:\n'
            '    total: number\n'
            '    init():\n'
            '        self.total = 0\n'
            '    func add(n: number):\n'
            '        self.total = self.total + n\n'
            '\n'
            'let acc = new Accumulator()\n'
            'acc.add(5)\n'
            'acc.add(10)\n'
            'show acc.total\n'
        )
        self.assertEqual(run(src), '15')

    def test_method_returns_computed_value(self):
        src = (
            'object Circle:\n'
            '    radius: number\n'
            '    init(r: number):\n'
            '        self.radius = r\n'
            '    func area():\n'
            '        return self.radius * self.radius * 3\n'
            '\n'
            'let c = new Circle(4)\n'
            'show c.area()\n'
        )
        self.assertEqual(run(src), '48')


# ------------------------------------------------------------------
# Inheritance
# ------------------------------------------------------------------

class TestInheritance(unittest.TestCase):

    def test_child_inherits_fields(self):
        src = (
            'object Animal:\n'
            '    name: text\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '\n'
            'object Dog extends Animal:\n'
            '    func speak():\n'
            '        return "Woof!"\n'
            '\n'
            'let d = new Dog("Rex")\n'
            'show d.name\n'
        )
        self.assertEqual(run(src), 'Rex')

    def test_child_inherits_parent_method(self):
        src = (
            'object Animal:\n'
            '    name: text\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func describe():\n'
            '        return "I am " + self.name\n'
            '\n'
            'object Cat extends Animal:\n'
            '    func speak():\n'
            '        return "Meow!"\n'
            '\n'
            'let c = new Cat("Whiskers")\n'
            'show c.describe()\n'
            'show c.speak()\n'
        )
        self.assertEqual(run(src), 'I am Whiskers\nMeow!')

    def test_child_overrides_parent_method(self):
        src = (
            'object Animal:\n'
            '    name: text\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func speak():\n'
            '        return "..."\n'
            '\n'
            'object Dog extends Animal:\n'
            '    func speak():\n'
            '        return "Woof!"\n'
            '\n'
            'let d = new Dog("Rex")\n'
            'show d.speak()\n'
        )
        self.assertEqual(run(src), 'Woof!')

    def test_multiple_children(self):
        src = (
            'object Shape:\n'
            '    color: text\n'
            '    init(color: text):\n'
            '        self.color = color\n'
            '    func kind():\n'
            '        return "shape"\n'
            '\n'
            'object Circle extends Shape:\n'
            '    func kind():\n'
            '        return "circle"\n'
            '\n'
            'object Square extends Shape:\n'
            '    func kind():\n'
            '        return "square"\n'
            '\n'
            'let ci = new Circle("red")\n'
            'let sq = new Square("blue")\n'
            'show ci.color\n'
            'show ci.kind()\n'
            'show sq.color\n'
            'show sq.kind()\n'
        )
        self.assertEqual(run(src), 'red\ncircle\nblue\nsquare')


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_method_result_assigned_to_variable(self):
        src = (
            'object Math:\n'
            '    func double(n: number):\n'
            '        return n * 2\n'
            '\n'
            'let m = new Math()\n'
            'let result = m.double(6)\n'
            'show result\n'
        )
        self.assertEqual(run(src), '12')

    def test_class_used_in_condition(self):
        src = (
            'object Flag:\n'
            '    val: number\n'
            '    init(v: number):\n'
            '        self.val = v\n'
            '    func is_positive():\n'
            '        return self.val > 0\n'
            '\n'
            'let f = new Flag(5)\n'
            'if f.is_positive():\n'
            '    show "yes"\n'
            'else:\n'
            '    show "no"\n'
        )
        self.assertEqual(run(src), 'yes')

    def test_undefined_class_raises(self):
        src = 'let x = new Ghost()\n'
        with self.assertRaises(Exception):
            run(src)

    def test_undefined_method_raises(self):
        src = (
            'object Empty:\n'
            '    val: number\n'
            '\n'
            'let e = new Empty(1)\n'
            'e.nonexistent()\n'
        )
        with self.assertRaises(Exception):
            run(src)

    def test_dynamic_attribute_set_in_method(self):
        src = (
            'object Store:\n'
            '    func setup():\n'
            '        self.data = "ready"\n'
            '\n'
            'let s = new Store()\n'
            's.setup()\n'
            'show s.data\n'
        )
        self.assertEqual(run(src), 'ready')


if __name__ == '__main__':
    unittest.main()