# =============================================================
# NEKOVA — Phase 6 Tests: Classes and Objects
# =============================================================

import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.nekova_class import NEKOVAClass, NEKOVAInstance


def run(source: str) -> Interpreter:
    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter()
    interp.execute(ast)
    return interp


def run_val(source: str, var: str):
    return run(source).env[var]


# ─────────────────────────────────────────────────────────────
# 1. Class definition and registration
# ─────────────────────────────────────────────────────────────

class TestClassDefinition(unittest.TestCase):

    def test_class_registered_in_env(self):
        i = run('object Dog:\n    name: text\n')
        self.assertIn("Dog", i.env)

    def test_class_is_nekova_class(self):
        i = run('object Dog:\n    name: text\n')
        self.assertIsInstance(i.env["Dog"], NEKOVAClass)

    def test_class_name_stored(self):
        i = run('object Cat:\n    name: text\n')
        self.assertEqual(i.env["Cat"].name, "Cat")

    def test_fields_registered(self):
        src = 'object Person:\n    name: text\n    age: number\n'
        i = run(src)
        fields = dict(i.env["Person"].fields)
        self.assertIn("name", fields)
        self.assertIn("age", fields)

    def test_field_type_hint_stored(self):
        src = 'object Person:\n    name: text\n'
        i = run(src)
        fields = dict(i.env["Person"].fields)
        self.assertEqual(fields["name"], "text")

    def test_method_registered(self):
        src = (
            'object Greeter:\n'
            '    func hello():\n'
            '        return "hi"\n'
        )
        i = run(src)
        self.assertIn("hello", i.env["Greeter"].methods)

    def test_multiple_methods(self):
        src = (
            'object Calc:\n'
            '    func add():\n'
            '        return 1\n'
            '    func sub():\n'
            '        return 2\n'
        )
        i = run(src)
        self.assertIn("add", i.env["Calc"].methods)
        self.assertIn("sub", i.env["Calc"].methods)

    def test_class_repr(self):
        i = run('object Foo:\n    x: number\n')
        self.assertIn("Foo", repr(i.env["Foo"]))


# ─────────────────────────────────────────────────────────────
# 2. Instantiation with new
# ─────────────────────────────────────────────────────────────

class TestNewInstance(unittest.TestCase):

    def test_new_creates_instance(self):
        src = (
            'object Box:\n'
            '    width: number\n'
            '    init(width: number):\n'
            '        self.width = width\n'
            'let b = new Box(10)\n'
        )
        i = run(src)
        self.assertIsInstance(i.env["b"], NEKOVAInstance)

    def test_init_sets_attributes(self):
        src = (
            'object Point:\n'
            '    x: number\n'
            '    y: number\n'
            '    init(x: number, y: number):\n'
            '        self.x = x\n'
            '        self.y = y\n'
            'let p = new Point(3, 4)\n'
        )
        i = run(src)
        self.assertEqual(i.env["p"].get_attr("x"), 3)
        self.assertEqual(i.env["p"].get_attr("y"), 4)

    def test_new_no_init_positional(self):
        src = (
            'object Tag:\n'
            '    label: text\n'
            'let t = new Tag("urgent")\n'
        )
        i = run(src)
        self.assertEqual(i.env["t"].get_attr("label"), "urgent")

    def test_instance_class_reference(self):
        src = (
            'object Car:\n'
            '    brand: text\n'
            '    init(brand: text):\n'
            '        self.brand = brand\n'
            'let c = new Car("Toyota")\n'
        )
        i = run(src)
        self.assertEqual(i.env["c"]._class.name, "Car")

    def test_undefined_class_raises(self):
        with self.assertRaises(Exception):
            run('let x = new Ghost()\n')

    def test_instance_repr_contains_class_name(self):
        src = (
            'object Widget:\n'
            '    color: text\n'
            '    init(color: text):\n'
            '        self.color = color\n'
            'let w = new Widget("red")\n'
        )
        i = run(src)
        self.assertIn("Widget", repr(i.env["w"]))


# ─────────────────────────────────────────────────────────────
# 3. Property access on instances
# ─────────────────────────────────────────────────────────────

class TestPropertyAccess(unittest.TestCase):

    def _person(self):
        return (
            'object Person:\n'
            '    name: text\n'
            '    age: number\n'
            '    init(name: text, age: number):\n'
            '        self.name = name\n'
            '        self.age = age\n'
        )

    def test_read_text_property(self):
        src = self._person() + 'let p = new Person("Em", 25)\nlet n = p.name\n'
        self.assertEqual(run_val(src, "n"), "Em")

    def test_read_number_property(self):
        src = self._person() + 'let p = new Person("Em", 25)\nlet a = p.age\n'
        self.assertEqual(run_val(src, "a"), 25)

    def test_property_in_fstring(self):
        src = (
            self._person() +
            'let p = new Person("Emmanuel", 25)\n'
            'let msg = f"Hello {p.name}"\n'
        )
        self.assertEqual(run_val(src, "msg"), "Hello Emmanuel")

    def test_missing_property_raises(self):
        src = self._person() + 'let p = new Person("Em", 25)\nlet x = p.missing\n'
        with self.assertRaises(Exception):
            run(src)


# ─────────────────────────────────────────────────────────────
# 4. Method calls on instances
# ─────────────────────────────────────────────────────────────

class TestMethodCalls(unittest.TestCase):

    def _greeter(self):
        return (
            'object Greeter:\n'
            '    name: text\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func greet():\n'
            '        return f"Hello, {self.name}!"\n'
            '    func shout():\n'
            '        return f"HEY {self.name}!"\n'
        )

    def test_method_returns_value(self):
        src = self._greeter() + 'let g = new Greeter("World")\nlet r = g.greet()\n'
        self.assertEqual(run_val(src, "r"), "Hello, World!")

    def test_method_with_params(self):
        src = (
            'object Adder:\n'
            '    base: number\n'
            '    init(base: number):\n'
            '        self.base = base\n'
            '    func add(n: number):\n'
            '        return self.base + n\n'
            'let a = new Adder(10)\n'
            'let result = a.add(5)\n'
        )
        self.assertEqual(run_val(src, "result"), 15)

    def test_method_modifies_self(self):
        src = (
            'object Counter:\n'
            '    count: number\n'
            '    init():\n'
            '        self.count = 0\n'
            '    func increment():\n'
            '        self.count = self.count + 1\n'
            'let c = new Counter()\n'
            'c.increment()\n'
            'c.increment()\n'
            'let val = c.count\n'
        )
        self.assertEqual(run_val(src, "val"), 2)

    def test_undefined_method_raises(self):
        src = (
            'object Foo:\n'
            '    x: number\n'
            '    init(x: number):\n'
            '        self.x = x\n'
            'let f = new Foo(1)\n'
            'f.nonexistent()\n'
        )
        with self.assertRaises(Exception):
            run(src)


# ─────────────────────────────────────────────────────────────
# 5. Inheritance
# ─────────────────────────────────────────────────────────────

class TestInheritance(unittest.TestCase):

    def _animal(self):
        return (
            'object Animal:\n'
            '    name: text\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func speak():\n'
            '        return "..."\n'
            '    func describe():\n'
            '        return f"I am {self.name}"\n'
        )

    def test_child_class_registered(self):
        src = (
            self._animal() +
            'object Dog extends Animal:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
        )
        i = run(src)
        self.assertIn("Dog", i.env)

    def test_child_parent_reference(self):
        src = (
            self._animal() +
            'object Dog extends Animal:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
        )
        i = run(src)
        self.assertIsNotNone(i.env["Dog"].parent)
        self.assertEqual(i.env["Dog"].parent.name, "Animal")

    def test_child_inherits_parent_method(self):
        src = (
            self._animal() +
            'object Dog extends Animal:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            'let d = new Dog("Rex")\n'
            'let desc = d.describe()\n'
        )
        self.assertEqual(run_val(src, "desc"), "I am Rex")

    def test_child_overrides_method(self):
        src = (
            self._animal() +
            'object Dog extends Animal:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func speak():\n'
            '        return "Woof!"\n'
            'let d = new Dog("Rex")\n'
            'let sound = d.speak()\n'
        )
        self.assertEqual(run_val(src, "sound"), "Woof!")

    def test_parent_method_unchanged(self):
        src = (
            self._animal() +
            'object Dog extends Animal:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
            '    func speak():\n'
            '        return "Woof!"\n'
            'let a = new Animal("Generic")\n'
            'let sound = a.speak()\n'
        )
        self.assertEqual(run_val(src, "sound"), "...")

    def test_undefined_parent_raises(self):
        src = (
            'object Poodle extends Dog:\n'
            '    init(name: text):\n'
            '        self.name = name\n'
        )
        with self.assertRaises(Exception):
            run(src)


# ─────────────────────────────────────────────────────────────
# 6. NEKOVAClass / NEKOVAInstance unit tests
# ─────────────────────────────────────────────────────────────

class TestNEKOVAClassUnit(unittest.TestCase):

    def _make_class(self, name="Foo", fields=None, methods=None, parent=None):
        from nekova.interpreter.nekova_class import NEKOVAClass
        return NEKOVAClass(
            name=name,
            fields=fields or [("x", "number")],
            init_params=[],
            init_body=[],
            methods=methods or {},
            parent=parent,
        )

    def test_get_method_found(self):
        from nekova.parser.nodes import MethodDefinition
        m = MethodDefinition("greet", [], [])
        klass = self._make_class(methods={"greet": m})
        self.assertIsNotNone(klass.get_method("greet"))

    def test_get_method_not_found(self):
        klass = self._make_class()
        self.assertIsNone(klass.get_method("missing"))

    def test_get_method_from_parent(self):
        from nekova.parser.nodes import MethodDefinition
        m = MethodDefinition("greet", [], [])
        parent = self._make_class(name="Base", methods={"greet": m})
        child  = self._make_class(name="Child", parent=parent)
        self.assertIsNotNone(child.get_method("greet"))

    def test_instance_initialises_fields(self):
        klass    = self._make_class(fields=[("x", "number"), ("y", "text")])
        instance = NEKOVAInstance(klass)
        self.assertIsNone(instance.get_attr("x"))
        self.assertIsNone(instance.get_attr("y"))

    def test_instance_set_and_get_attr(self):
        klass    = self._make_class(fields=[("x", "number")])
        instance = NEKOVAInstance(klass)
        instance.set_attr("x", 42)
        self.assertEqual(instance.get_attr("x"), 42)

    def test_instance_missing_attr_raises(self):
        klass    = self._make_class(fields=[("x", "number")])
        instance = NEKOVAInstance(klass)
        with self.assertRaises(AttributeError):
            instance.get_attr("missing")

    def test_instance_has_attr_true(self):
        klass    = self._make_class(fields=[("x", "number")])
        instance = NEKOVAInstance(klass)
        # x is initialised to None on construction
        self.assertIsNone(instance.get_attr("x"))

    def test_instance_has_attr_false(self):
        klass    = self._make_class(fields=[("x", "number")])
        instance = NEKOVAInstance(klass)
        with self.assertRaises((AttributeError, KeyError, Exception)):
            instance.get_attr("missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)