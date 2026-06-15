# =============================================================
# NEKOVA — Phase 5B Tests: Type Enforcement
# =============================================================
# Tests for:
#   - Explicit type hint enforcement (always-on)
#   - strict_types=True: re-assignment type tracking
#   - strict_types=True: untyped re-assignment that changes type
#   - strict_types=False: permissive dynamic typing (default)
#   - Type registry across scopes
#   - All NEKOVA types: text, number, boolean, list, dict, any
# =============================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str, strict: bool = False):
    """Helper: lex → parse → interpret, return interpreter."""
    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter(strict_types=strict)
    interp.execute(ast)
    return interp


def run_raises(source: str, strict: bool = False):
    """Helper: expect a TypeError to be raised."""
    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter(strict_types=strict)
    interp.execute(ast)


# ─────────────────────────────────────────────────────────────
# 1. Explicit type hints — always enforced regardless of strict
# ─────────────────────────────────────────────────────────────

class TestExplicitTypeHints(unittest.TestCase):

    def test_text_hint_accepts_string(self):
        i = run('let name: text = "Emmanuel"')
        self.assertEqual(i.env["name"], "Emmanuel")

    def test_number_hint_accepts_int(self):
        i = run("let age: number = 25")
        self.assertEqual(i.env["age"], 25)

    def test_number_hint_accepts_float(self):
        i = run("let score: number = 9.5")
        self.assertAlmostEqual(i.env["score"], 9.5)

    def test_boolean_hint_accepts_true(self):
        i = run("let active: boolean = true")
        self.assertEqual(i.env["active"], True)

    def test_boolean_hint_accepts_false(self):
        i = run("let done: boolean = false")
        self.assertEqual(i.env["done"], False)

    def test_list_hint_accepts_list(self):
        i = run("let items: list = [1, 2, 3]")
        self.assertEqual(i.env["items"], [1, 2, 3])

    def test_any_hint_accepts_any_type(self):
        i = run('let val: any = "hello"')
        self.assertEqual(i.env["val"], "hello")

    def test_any_hint_accepts_number(self):
        i = run("let val: any = 42")
        self.assertEqual(i.env["val"], 42)

    def test_text_hint_rejects_number(self):
        with self.assertRaises(TypeError) as ctx:
            run_raises("let name: text = 42")
        self.assertIn("text", str(ctx.exception))
        self.assertIn("name", str(ctx.exception))

    def test_number_hint_rejects_string(self):
        with self.assertRaises(TypeError) as ctx:
            run_raises('let age: number = "old"')
        self.assertIn("number", str(ctx.exception))

    def test_boolean_hint_rejects_string(self):
        with self.assertRaises(TypeError):
            run_raises('let flag: boolean = "yes"')

    def test_boolean_hint_rejects_number(self):
        with self.assertRaises(TypeError):
            run_raises("let flag: boolean = 1")

    def test_list_hint_rejects_string(self):
        with self.assertRaises(TypeError):
            run_raises('let items: list = "oops"')

    def test_error_message_mentions_variable_name(self):
        with self.assertRaises(TypeError) as ctx:
            run_raises('let myvar: text = 99')
        self.assertIn("myvar", str(ctx.exception))

    def test_error_message_mentions_expected_type(self):
        with self.assertRaises(TypeError) as ctx:
            run_raises('let myvar: text = 99')
        self.assertIn("text", str(ctx.exception))

    def test_error_message_mentions_actual_type(self):
        with self.assertRaises(TypeError) as ctx:
            run_raises('let myvar: text = 99')
        self.assertIn("int", str(ctx.exception))


# ─────────────────────────────────────────────────────────────
# 2. Type registry — declared types are remembered
# ─────────────────────────────────────────────────────────────

class TestTypeRegistry(unittest.TestCase):

    def test_type_registered_on_declaration(self):
        i = run('let name: text = "Emmanuel"')
        self.assertEqual(i._type_registry.get("name"), "text")

    def test_number_registered(self):
        i = run("let age: number = 25")
        self.assertEqual(i._type_registry.get("age"), "number")

    def test_untyped_var_not_registered(self):
        i = run('x = "hello"')
        self.assertNotIn("x", i._type_registry)

    def test_any_hint_registered_as_any(self):
        i = run('let val: any = 42')
        self.assertEqual(i._type_registry.get("val"), "any")

    def test_multiple_vars_registered(self):
        src = 'let a: text = "x"\nlet b: number = 1\nlet c: boolean = true'
        i   = run(src)
        self.assertEqual(i._type_registry["a"], "text")
        self.assertEqual(i._type_registry["b"], "number")
        self.assertEqual(i._type_registry["c"], "boolean")


# ─────────────────────────────────────────────────────────────
# 3. strict_types = False (default) — permissive
# ─────────────────────────────────────────────────────────────

class TestPermissiveMode(unittest.TestCase):

    def test_can_reassign_different_type(self):
        src = 'let x: text = "hello"\nx = 42'
        # Without strict, the re-assignment is allowed but raises because
        # we still honour the explicit hint on first declaration? No —
        # the re-assignment has NO hint so it's just a plain assignment.
        # This should succeed in permissive mode.
        i = run(src, strict=False)
        self.assertEqual(i.env["x"], 42)

    def test_can_change_type_freely(self):
        src = 'x = 1\nx = "now a string"\nx = true'
        i = run(src, strict=False)
        self.assertEqual(i.env["x"], True)

    def test_no_type_registry_effect_without_strict(self):
        src = 'let name: text = "Em"\nname = 999'
        i = run(src, strict=False)
        self.assertEqual(i.env["name"], 999)


# ─────────────────────────────────────────────────────────────
# 4. strict_types = True — type tracking enforced
# ─────────────────────────────────────────────────────────────

class TestStrictMode(unittest.TestCase):

    def test_same_type_reassignment_ok(self):
        src = 'let name: text = "Emmanuel"\nname = "King"'
        i = run(src, strict=True)
        self.assertEqual(i.env["name"], "King")

    def test_number_reassignment_ok(self):
        src = "let age: number = 25\nage = 30"
        i = run(src, strict=True)
        self.assertEqual(i.env["age"], 30)

    def test_reassignment_wrong_type_raises(self):
        src = 'let name: text = "Emmanuel"\nname = 42'
        with self.assertRaises(TypeError) as ctx:
            run_raises(src, strict=True)
        self.assertIn("name", str(ctx.exception))
        self.assertIn("text", str(ctx.exception))

    def test_boolean_reassigned_as_number_raises(self):
        src = "let flag: boolean = true\nflag = 1"
        with self.assertRaises(TypeError):
            run_raises(src, strict=True)

    def test_untyped_var_type_change_raises(self):
        src = "x = 42\nx = true"
        with self.assertRaises(TypeError) as ctx:
            run_raises(src, strict=True)
        self.assertIn("x", str(ctx.exception))

    def test_untyped_var_same_type_ok(self):
        src = "x = 42\nx = 99"
        i = run(src, strict=True)
        self.assertEqual(i.env["x"], 99)

    def test_untyped_string_then_string_ok(self):
        src = 'x = "hello"\nx = "world"'
        i = run(src, strict=True)
        self.assertEqual(i.env["x"], "world")

    def test_any_typed_var_allows_any_reassignment(self):
        src = 'let val: any = 1\nval = "now text"\nval = true'
        i = run(src, strict=True)
        self.assertEqual(i.env["val"], True)

    def test_strict_error_message_mentions_strict_tip(self):
        src = 'let name: text = "Em"\nname = 99'
        with self.assertRaises(TypeError) as ctx:
            run_raises(src, strict=True)
        msg = str(ctx.exception)
        self.assertTrue(
            "strict" in msg.lower() or "declared" in msg.lower(),
            f"Expected strict-mode guidance in message, got: {msg}"
        )

    def test_multiple_vars_independent(self):
        src = (
            'let a: text = "hello"\n'
            'let b: number = 1\n'
            'a = "world"\n'       # ok — text → text
            'b = 99\n'            # ok — number → number
        )
        i = run(src, strict=True)
        self.assertEqual(i.env["a"], "world")
        self.assertEqual(i.env["b"], 99)


# ─────────────────────────────────────────────────────────────
# 5. Interpreter default is non-strict
# ─────────────────────────────────────────────────────────────

class TestInterpreterDefaults(unittest.TestCase):

    def test_default_is_not_strict(self):
        i = Interpreter()
        self.assertFalse(i.strict_types)

    def test_strict_true_sets_flag(self):
        i = Interpreter(strict_types=True)
        self.assertTrue(i.strict_types)

    def test_type_registry_starts_empty(self):
        i = Interpreter()
        self.assertEqual(i._type_registry, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)