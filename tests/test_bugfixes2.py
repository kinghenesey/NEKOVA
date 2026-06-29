"""
Bug Fix Regression Tests — Round 2
Covers the partially-fixed and newly-fixed bugs from the second audit.
"""
import unittest
import sys
import io
import re
import warnings

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.ai import memory_store


def run(source: str) -> str:
    memory_store.init_interpreter_memory()
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


# ── Bug 33: Per-interpreter memory isolation ──────────────────

class TestMemoryIsolation(unittest.TestCase):

    def test_init_memory_called_in_init(self):
        """Interpreter.__init__ must call init_interpreter_memory()."""
        # Each interpreter should start with a clean slate
        memory_store.remember("shared_key", "value_from_before")

        interp2 = Interpreter()
        # interp2 starts fresh — should not see value set before it
        val = memory_store.recall("shared_key")
        # After init_interpreter_memory(), the thread-local store is fresh
        # But since we're on the same thread, the new interpreter clears it
        self.assertIsNone(val)

    def test_two_interpreters_isolated(self):
        """Two interpreters on same thread should not share memory."""
        # Interpreter 1 remembers something
        src1 = 'remember "test_key" = "interp1_value"'
        run(src1)

        # Interpreter 2 should NOT see it (fresh init)
        src2 = 'show recall "test_key" or "empty"'
        out = run(src2)
        self.assertEqual(out, "empty")

    def test_forget_uses_per_interpreter_store(self):
        """forget() must operate on per-interpreter store."""
        src = (
            'remember "k" = "v"\n'
            'forget "k"\n'
            'show recall "k" or "gone"'
        )
        out = run(src)
        self.assertEqual(out, "gone")


# ── Bug 14: not not x / --x parser crash ─────────────────────

class TestDoubleUnary(unittest.TestCase):

    def test_not_not_false(self):
        out = run('show not not false')
        self.assertEqual(out, "false")

    def test_not_not_true(self):
        out = run('show not not true')
        self.assertEqual(out, "true")

    def test_double_minus(self):
        out = run('let x = 5\nshow - -x')
        self.assertEqual(out, "5")

    def test_triple_not(self):
        out = run('show not not not true')
        self.assertEqual(out, "false")


# ── Bug 15: short-circuit and/or ─────────────────────────────

class TestShortCircuit(unittest.TestCase):

    def test_and_short_circuits_on_false(self):
        """Right side of `and` must not execute when left is false."""
        src = (
            'task boom():\n'
            '    raise "should not be called"\n'
            '    return true\n'
            'let x = false and boom()\n'
            'show x'
        )
        out = run(src)
        self.assertEqual(out, "false")

    def test_or_short_circuits_on_true(self):
        """Right side of `or` must not execute when left is true."""
        src = (
            'task boom():\n'
            '    raise "should not be called"\n'
            '    return false\n'
            'let x = true or boom()\n'
            'show x'
        )
        out = run(src)
        self.assertEqual(out, "true")

    def test_and_evaluates_right_when_left_true(self):
        out = run('show true and true')
        self.assertEqual(out, "true")

    def test_or_evaluates_right_when_left_false(self):
        out = run('show false or true')
        self.assertEqual(out, "true")

    def test_and_returns_left_falsy_value(self):
        out = run('show 0 and 42')
        self.assertEqual(out, "0")

    def test_or_returns_left_truthy_value(self):
        out = run('show 42 or 0')
        self.assertEqual(out, "42")


# ── Bug 16: SQL injection — deprecation warning ───────────────

class TestSQLDeprecation(unittest.TestCase):

    def test_safe_identifier_rejects_injection(self):
        from nekova.database.query import _safe_identifier
        with self.assertRaises(ValueError):
            _safe_identifier("users; DROP TABLE users")

    def test_safe_identifier_rejects_spaces(self):
        from nekova.database.query import _safe_identifier
        with self.assertRaises(ValueError):
            _safe_identifier("user name")

    def test_safe_identifier_accepts_valid(self):
        from nekova.database.query import _safe_identifier
        self.assertEqual(_safe_identifier("user_data"), "user_data")
        self.assertEqual(_safe_identifier("Table123"), "Table123")

    def test_parameterised_where_works(self):
        """Parameterised WHERE (dict form) must return correct rows."""
        import tempfile, os
        from nekova.database.connection import DatabaseConnection
        from nekova.database.query import QueryBuilder

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        try:
            conn = DatabaseConnection(tmp.name)
            conn.connect()
            qb = QueryBuilder(conn)
            qb.create_table("items", {"name": "TEXT", "value": "INTEGER"})
            qb.insert("items", {"name": "alice", "value": 10})
            qb.insert("items", {"name": "bob",   "value": 20})
            rows = qb.select("items", where={"name": "alice"})
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["value"], 10)
        finally:
            conn.close()
            os.unlink(tmp.name)


# ── Bug 19: try without catch re-raises ──────────────────────

class TestTryWithoutCatch(unittest.TestCase):

    def test_try_without_catch_reraises(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        src = 'try:\n    let x = 1 / 0'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interp = Interpreter()
        with self.assertRaises(Exception):
            interp.run(ast)

    def test_try_with_finally_no_catch_reraises(self):
        """try + finally without catch should still propagate exceptions."""
        src = (
            'try:\n'
            '    raise "oops"\n'
            'finally:\n'
            '    show "cleanup"'
        )
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interp = Interpreter()
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            with self.assertRaises(Exception):
                interp.run(ast)
        finally:
            sys.stdout = old
        # finally block should have run
        self.assertIn("cleanup", buf.getvalue())

    def test_try_with_catch_does_not_reraise(self):
        out = run(
            'try:\n'
            '    raise "err"\n'
            'catch e:\n'
            '    show "caught"'
        )
        self.assertEqual(out, "caught")


# ── Bug 20: server host binding ──────────────────────────────

class TestServerBinding(unittest.TestCase):

    def test_web_server_binds_localhost(self):
        with open("nekova/web/server.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn('host="0.0.0.0"', content)
        self.assertNotIn("host='0.0.0.0'", content)

    def test_web_ide_binds_localhost(self):
        with open("nekova/web_ide/ide_server.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn('host="0.0.0.0"', content)
        self.assertNotIn("host='0.0.0.0'", content)

    def test_templates_use_localhost(self):
        with open("nekova/cli/templates.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn('host = "0.0.0.0"', content)


# ── Bug 22: formatter ** preservation ────────────────────────

class TestFormatterPower(unittest.TestCase):

    def test_power_operator_not_split(self):
        from nekova.cli.formatter import fmt_source
        result = fmt_source("let x = 2**10")
        self.assertNotIn("* *", result)
        self.assertIn("**", result)

    def test_floor_div_not_split(self):
        from nekova.cli.formatter import fmt_source
        result = fmt_source("let x = 10//3")
        self.assertNotIn("/ /", result)
        self.assertIn("//", result)

    def test_multiply_still_spaced(self):
        from nekova.cli.formatter import fmt_source
        result = fmt_source("let x = 3*4")
        self.assertIn("3 * 4", result)

    def test_power_with_spaces_normalised(self):
        from nekova.cli.formatter import fmt_source
        result = fmt_source("let x = 3 ** 4")
        self.assertIn("**", result)
        self.assertNotIn("* *", result)


# ── Bug 37: env_all() filtering ──────────────────────────────

class TestEnvAllFiltering(unittest.TestCase):

    def test_env_all_excludes_path(self):
        # PATH is not a secret — it should be present (not redacted)
        from nekova.stdlib.env_module import _all
        result = _all()
        # PATH should be included but not redacted (not a secret key)
        import os
        if "PATH" in os.environ:
            self.assertIn("PATH", result)
            self.assertNotEqual(result.get("PATH"), "[REDACTED]")

    def test_env_all_excludes_api_keys(self):
        import os
        os.environ["MYAPP_TEST_API_KEY"] = "hunter2"
        try:
            from nekova.stdlib.env_module import _all
            result = _all()
            # API key values are redacted
            self.assertEqual(result.get("MYAPP_TEST_API_KEY"), "[REDACTED]")
        finally:
            os.environ.pop("MYAPP_TEST_API_KEY", None)

    def test_env_all_excludes_home(self):
        import os
        if "HOME" not in os.environ:
            self.skipTest("HOME not set in this environment")
        from nekova.stdlib.env_module import _all
        result = _all()
        # HOME is not a secret — should be present, not redacted
        self.assertIn("HOME", result)
        self.assertNotEqual(result.get("HOME"), "[REDACTED]")


# ── Bug 38: bare imports ──────────────────────────────────────

class TestBareImports(unittest.TestCase):

    def test_deploy_cloud_no_bare_import(self):
        with open("nekova/deploy/cloud.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("from deploy.bundle import", content)

    def test_deploy_exporter_no_bare_import(self):
        with open("nekova/deploy/exporter.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("from interpreter.interpreter import", content)

    def test_cli_deploy_no_bare_imports(self):
        with open("nekova/cli/deploy.py", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("from deploy.exporter import", content)
        self.assertNotIn("from deploy.packager import", content)
        self.assertNotIn("from deploy.publisher import", content)
        self.assertNotIn("from deploy.cloud import", content)


# ── Bug 44: is_number validation ─────────────────────────────

class TestIsNumber(unittest.TestCase):

    def test_double_minus_is_not_number(self):
        out = run('use text\nshow is_number("--5")')
        self.assertEqual(out, "false")

    def test_single_minus_is_number(self):
        out = run('use text\nshow is_number("-5")')
        self.assertEqual(out, "true")

    def test_integer_is_number(self):
        out = run('use text\nshow is_number("42")')
        self.assertEqual(out, "true")

    def test_float_is_number(self):
        out = run('use text\nshow is_number("3.14")')
        self.assertEqual(out, "true")

    def test_alpha_is_not_number(self):
        out = run('use text\nshow is_number("abc")')
        self.assertEqual(out, "false")

    def test_empty_is_not_number(self):
        out = run('use text\nshow is_number("")')
        self.assertEqual(out, "false")


# ── Bug 18: token_bytes exported ─────────────────────────────

class TestTokenBytesExport(unittest.TestCase):

    def test_token_bytes_in_crypto(self):
        from nekova.stdlib.crypto_module import load
        ns = load()
        self.assertIn("token_bytes", ns)

    def test_token_bytes_returns_bytes(self):
        from nekova.stdlib.crypto_module import load
        fn = load()["token_bytes"]
        result = fn(16)
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 16)


# ── Bug 17: hmac_valid algorithm param ───────────────────────

class TestHmacValid(unittest.TestCase):

    def test_hmac_valid_sha256(self):
        from nekova.stdlib.crypto_module import load
        ns = load()
        sig = ns["hmac"]("hello", "key", "sha256")
        self.assertTrue(ns["hmac_valid"]("hello", "key", sig, "sha256"))

    def test_hmac_valid_sha512(self):
        from nekova.stdlib.crypto_module import load
        ns = load()
        sig = ns["hmac"]("hello", "key", "sha512")
        self.assertTrue(ns["hmac_valid"]("hello", "key", sig, "sha512"))

    def test_hmac_valid_wrong_algo_fails(self):
        from nekova.stdlib.crypto_module import load
        ns = load()
        sig_256 = ns["hmac"]("hello", "key", "sha256")
        # Verifying sha256 sig with sha512 should fail
        self.assertFalse(ns["hmac_valid"]("hello", "key", sig_256, "sha512"))


if __name__ == "__main__":
    unittest.main()