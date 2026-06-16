# =============================================================
# NEKOVA — Phase 5C Tests: CLI Args  (args.name, args.port)
# =============================================================

import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.cli.args_object import ArgsObject
from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str, script_args: dict = None) -> Interpreter:
    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter()
    from nekova.cli.args_object import ArgsObject
    interp.env["args"] = ArgsObject(script_args or {})
    interp.execute(ast)
    return interp


# ── ArgsObject unit tests ─────────────────────────────────────

class TestArgsObject(unittest.TestCase):

    def test_dot_access_existing_key(self):
        a = ArgsObject({"name": "Emmanuel"})
        self.assertEqual(a.name, "Emmanuel")

    def test_dot_access_missing_key_raises(self):
        a = ArgsObject({})
        with self.assertRaises(AttributeError):
            _ = a.missing

    def test_has_returns_true(self):
        a = ArgsObject({"debug": "true"})
        self.assertTrue(a.has("debug"))

    def test_has_returns_false(self):
        a = ArgsObject({})
        self.assertFalse(a.has("debug"))

    def test_get_returns_value(self):
        a = ArgsObject({"port": "8080"})
        self.assertEqual(a.get("port"), "8080")

    def test_get_returns_default(self):
        a = ArgsObject({})
        self.assertEqual(a.get("port", "3000"), "3000")

    def test_get_default_none(self):
        a = ArgsObject({})
        self.assertIsNone(a.get("missing"))

    def test_keys_returns_list(self):
        a = ArgsObject({"a": "1", "b": "2"})
        self.assertEqual(sorted(a.keys()), ["a", "b"])

    def test_all_returns_dict(self):
        data = {"name": "Em", "port": "8080"}
        a = ArgsObject(data)
        self.assertEqual(a.all(), data)

    def test_contains(self):
        a = ArgsObject({"x": "1"})
        self.assertIn("x", a)
        self.assertNotIn("y", a)

    def test_repr_with_args(self):
        a = ArgsObject({"name": "Em"})
        self.assertIn("name", repr(a))

    def test_repr_empty(self):
        a = ArgsObject({})
        self.assertEqual(repr(a), "Args()")

    def test_readonly_raises_on_set(self):
        a = ArgsObject({"x": "1"})
        with self.assertRaises(AttributeError):
            a.x = "new"

    def test_multiple_args(self):
        a = ArgsObject({"name": "Em", "port": "8080", "env": "prod"})
        self.assertEqual(a.name, "Em")
        self.assertEqual(a.port, "8080")
        self.assertEqual(a.env,  "prod")

    def test_boolean_flag_value(self):
        a = ArgsObject({"verbose": "true"})
        self.assertEqual(a.verbose, "true")


# ── Property access in NEKOVA scripts ────────────────────────

class TestPropertyAccessInScript(unittest.TestCase):

    def test_args_dot_name_in_script(self):
        src = 'let n: text = args.name\nshow n'
        i = run(src, {"name": "Emmanuel"})
        self.assertEqual(i.env["n"], "Emmanuel")

    def test_args_dot_port_in_script(self):
        src = 'let p: text = args.port'
        i = run(src, {"port": "8080"})
        self.assertEqual(i.env["p"], "8080")

    def test_args_in_fstring(self):
        src = 'show f"Hello {args.name}!"'
        # Should not raise
        run(src, {"name": "World"})

    def test_args_has_method_in_script(self):
        src = 'let has_debug: boolean = args.has("debug")'
        i = run(src, {"debug": "true"})
        self.assertTrue(i.env["has_debug"])

    def test_args_has_method_false(self):
        src = 'let has_debug: boolean = args.has("debug")'
        i = run(src, {})
        self.assertFalse(i.env["has_debug"])

    def test_args_get_with_default(self):
        src = 'let port: text = args.get("port", "3000")'
        i = run(src, {})
        self.assertEqual(i.env["port"], "3000")

    def test_args_get_returns_value(self):
        src = 'let port: text = args.get("port", "3000")'
        i = run(src, {"port": "9000"})
        self.assertEqual(i.env["port"], "9000")

    def test_default_args_object_exists(self):
        """args is always available even without CLI args."""
        src = 'let ok: boolean = args.has("x")'
        i = run(src, {})
        self.assertFalse(i.env["ok"])

    def test_args_keys_in_script(self):
        src = 'let k: list = args.keys()'
        i = run(src, {"name": "Em", "port": "80"})
        self.assertIn("name", i.env["k"])
        self.assertIn("port", i.env["k"])


# ── parse_args extracts script args ──────────────────────────

class TestParseArgsScriptArgs(unittest.TestCase):

    def _parse(self, argv):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from main import parse_args
        return parse_args(argv)

    def test_extracts_name_value(self):
        args = self._parse(["run", "app.nk", "--name", "Emmanuel"])
        self.assertEqual(args["script_args"].get("name"), "Emmanuel")

    def test_extracts_port_value(self):
        args = self._parse(["run", "app.nk", "--port", "8080"])
        self.assertEqual(args["script_args"].get("port"), "8080")

    def test_does_not_extract_debug(self):
        args = self._parse(["run", "app.nk", "--debug"])
        self.assertNotIn("debug", args["script_args"])
        self.assertTrue(args["debug"])

    def test_extracts_multiple_args(self):
        args = self._parse(["run", "app.nk", "--name", "Em", "--port", "80"])
        self.assertEqual(args["script_args"]["name"], "Em")
        self.assertEqual(args["script_args"]["port"], "80")

    def test_boolean_flag_no_value(self):
        args = self._parse(["run", "app.nk", "--verbose"])
        self.assertEqual(args["script_args"].get("verbose"), "true")

    def test_empty_script_args_by_default(self):
        args = self._parse(["run", "app.nk"])
        self.assertEqual(args["script_args"], {})

    def test_command_still_parsed(self):
        args = self._parse(["run", "app.nk", "--name", "Em"])
        self.assertEqual(args["command"], "run")
        self.assertEqual(args["arg"], "app.nk")


if __name__ == "__main__":
    unittest.main(verbosity=2)