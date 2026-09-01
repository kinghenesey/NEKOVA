"""
Phase 28 — Agent System + Unified Schema (schema keyword, part 1)

Tests for the `schema` keyword's first two pillars:
  1. Object type   — Person(name="Alice", age=30)
  2. AI parser     — think "..." as Person

`schema` is deliberately a separate keyword/registry from `shape`
(see SchemaDefinition's docstring in nodes.py) — it uses the
text/number/boolean/list/dict/any vocabulary that `think ... as
schema {...}` (Phase 9) already validates against, rather than
shape's str/int/float/bool names. Structurally, `_exec_SchemaDefinition`
mirrors `_exec_ShapeDefinition`, and `think ... as <SchemaName>` reuses
the exact same lookup/coercion/re-prompt path that `think ... as
<ShapeName>` (Phase 25) already had — extended to also check the new
schema registry.

This file also covers a bug found and fixed alongside this work:
`shape`'s own constructor only ever accepted positional arguments —
User(name="Alice", age=30) failed with "unexpected keyword argument
'name'" even though NEKOVA's call syntax supports keyword arguments
generally. Fixed with the same pattern applied to schema's constructor
from the start.
"""
import io
import re
import sys
import unittest

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


class TestSchemaAsObjectType(unittest.TestCase):
    def test_positional_construction(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            '    age:  number\n'
            'let p = Person("Alice", 30)\n'
            'show p["name"]\n'
            'show p["age"]\n'
        )
        self.assertEqual(out, "Alice\n30.0")

    def test_keyword_construction(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            '    age:  number\n'
            'let p = Person(name="Bob", age=25)\n'
            'show p["name"]\n'
            'show p["age"]\n'
        )
        self.assertEqual(out, "Bob\n25.0")

    def test_result_tagged_with_schema_name(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            'let p = Person(name="Ada")\n'
            'show p["__schema__"]\n'
        )
        self.assertEqual(out, "Person")

    def test_missing_required_field_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run(
                'schema Person:\n'
                '    name: text\n'
                '    age:  number\n'
                'let p = Person(name="Ada")\n'
            )

    def test_default_value_used_when_omitted(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            '    note: text = "none"\n'
            'let p = Person(name="Ada")\n'
            'show p["note"]\n'
        )
        self.assertEqual(out, "none")

    def test_boolean_field_coercion(self):
        out = run(
            'schema Flag:\n'
            '    active: boolean\n'
            'let f = Flag(active=1)\n'
            'show f["active"]\n'
        )
        self.assertEqual(out, "true")

    def test_schema_as_ordinary_variable_still_works(self):
        """'schema' is a soft keyword — using it as a plain variable
        name must keep working, exactly like 'prompt' does."""
        out = run('let schema = 5\nshow schema\n')
        self.assertEqual(out, "5")


class TestSchemaAsAIParser(unittest.TestCase):
    def test_basic_schema_extraction(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            '    age:  number\n'
            'let p = think "extract from: Ada, 30" as Person\n'
            'show p["name"]\n'
            'show p["age"]\n'
        )
        self.assertEqual(out, "mock_name\n42.0")

    def test_schema_lookup_is_case_insensitive(self):
        out = run(
            'schema Order:\n'
            '    id: number\n'
            'let o = think "extract" as Order\n'
            'show type_of(o)\n'
        )
        self.assertEqual(out, "dict")

    def test_result_tagged_with_schema_name(self):
        out = run(
            'schema Person:\n'
            '    name: text\n'
            'let p = think "extract" as Person\n'
            'show p["__schema__"]\n'
        )
        self.assertEqual(out, "Person")

    def test_shape_takes_precedence_on_name_collision(self):
        """If a shape and schema share a name, the shape (which came
        first historically) wins — documented, deterministic
        tie-break rather than undefined behavior."""
        out = run(
            'shape Thing:\n'
            '    label str\n'
            'schema Thing:\n'
            '    label: text\n'
            'let t = think "extract" as Thing\n'
            'show t["__shape__"]\n'
        )
        self.assertEqual(out, "Thing")


class TestSchemaAsDBTable(unittest.TestCase):
    """The DB-table pillar: db_create_from_schema() reads a schema's
    fields directly off its constructor (via the
    __nekova_schema_fields__ attribute _exec_SchemaDefinition
    attaches) and builds the table without the caller having to
    spell out column types by hand."""

    def test_creates_table_from_schema_fields(self):
        out = run(
            'use database\n'
            'schema Person:\n'
            '    name: text\n'
            '    age:  number\n'
            'db_connect(":memory:")\n'
            'db_create_from_schema(Person, "people")\n'
            'db_insert("people", "Alice, 30")\n'
            'let rows = db_find("people", "all")\n'
            'show rows\n'
        )
        self.assertIn("Alice", out)
        self.assertIn("30", out)

    def test_boolean_field_maps_to_boolean_column(self):
        out = run(
            'use database\n'
            'schema Flag:\n'
            '    active: boolean\n'
            'db_connect(":memory:")\n'
            'db_create_from_schema(Flag, "flags")\n'
            'show db_exists("flags")\n'
        )
        self.assertTrue(out.endswith("true"))

    def test_non_schema_argument_raises_clear_error(self):
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run(
                'use database\n'
                'db_connect(":memory:")\n'
                'db_create_from_schema("not_a_schema", "people")\n'
            )
        self.assertIn("expects a `schema`", str(ctx.exception))


class TestShapeKeywordArgumentFix(unittest.TestCase):
    """Regression test for the shape-constructor bug found while
    building schema: keyword-argument construction was completely
    broken for `shape`, not just partially."""

    def test_shape_keyword_construction_works(self):
        out = run(
            'shape User:\n'
            '    name str\n'
            '    age  int\n'
            'let u = User(name="Bob", age=25)\n'
            'show u["name"]\n'
            'show u["age"]\n'
        )
        self.assertEqual(out, "Bob\n25")

    def test_shape_positional_construction_still_works(self):
        out = run(
            'shape User:\n'
            '    name str\n'
            '    age  int\n'
            'let u = User("Alice", 30)\n'
            'show u["name"]\n'
            'show u["age"]\n'
        )
        self.assertEqual(out, "Alice\n30")


if __name__ == "__main__":
    unittest.main()