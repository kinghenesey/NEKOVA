"""
Bug Fix Regression Tests — Round 6
Fixes for a second independent QA pass (18 bugs, see conversation
history), verified against the live repo before fixing. This file
covers the bugs that were genuinely new in that pass — the ones that
overlapped with the previous round (formatter, type hints,
compile/export, nekova test path, package, debugger, typo, sort/take
pipe) were already covered by test_bugfixes4.py/test_bugfixes5.py and
are not repeated here. Covers:

  1. (BUG-01) Every `import "file.nk"` crashed unconditionally with
     AttributeError: 'Interpreter' object has no attribute 'debug'.
     _exec_ImportStatement read self.debug to decide whether to print
     verbose import logging, but nothing ever set it. Now initialized
     to False in __init__.

  2. (BUG-02) db_insert's positional-only value parser silently stored
     the literal "key=value" text when a value happened to contain
     '=', corrupting every column. Now key=value syntax is properly
     recognized (matching db_update's existing WHERE-clause
     convention) alongside the documented positional form, and mixing
     both in one call is rejected with a clear error instead of
     guessed at. Separately: RuntimeError from stdlib modules (db,
     etc.) was never caught by the generic builtin-call handler, so
     malformed WHERE-clause syntax leaked a raw Python traceback
     instead of a clean NEKOVA error; and db_find("t", "") (empty
     filter) crashed instead of behaving like "all" (no filter),
     unlike db_delete/db_count which already handled that correctly.

  3. (BUG-08) Closures couldn't mutate a variable captured from an
     enclosing function's scope — only true globals (via explicit
     `global`) worked. Every bare reassignment wrote straight into
     the *current* scope via Environment.__setitem__/.set(), with no
     path that walked up to an existing binding in a parent scope —
     Environment.update() already existed and did exactly that walk,
     it just was never called. Fixed by giving AssignStatement an
     is_declaration flag (True for let/const, which must still always
     bind locally for correct shadowing; False for bare reassignment,
     which now uses .update()).

  4. (BUG-09) Plain (non-f-prefixed) string literals silently
     interpolated any {identifier} that happened to match an in-scope
     variable name, making f"..." meaningless (plain strings did the
     same substitution) and any brace-containing text (JSON, regex,
     set notation) unsafe by default. _exec_StringLiteral now returns
     the literal text verbatim; only real f-strings (FStringLiteral,
     parsed into proper expression nodes at parse time) interpolate.

  5. (BUG-15) voice_save hard-imports gtts with no fallback, but gtts
     was never declared as a dependency — guaranteed failure on a
     clean install. Same root cause as `nekova test` needing pytest,
     which also wasn't declared. Both added to pyproject.toml.
     Also found and fixed two more of the same bare-import class as
     the previous round's compile/export fix: nekova/web_ide/
     ide_server.py's `from formatter import NEKOVAFormatter` pointed
     at a root-level module that isn't even shipped in the installed
     wheel (and was called with the wrong API besides — source
     belongs in the constructor, not .format()), and nekova/compiler/
     vm.py's `from stdlib import load_module` was missing the
     `nekova.` prefix.

  6. (BUG-16/17) No --quiet/-q flag existed to suppress the ~12-line
     banner on every CLI invocation, and --help still referenced
     `python main.py <file>` despite a real `nekova` entry point.
"""
import unittest
import sys
import io
import os
import re
import sqlite3
import tempfile
import shutil
import subprocess

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.ai import memory_store
import nekova.database.db_module as db_module

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


# ── BUG-01: import crashes unconditionally ──────────────────────

class TestMultiFileImports(unittest.TestCase):

    def _write_project(self, tmpdir):
        with open(os.path.join(tmpdir, "utils.nk"), "w") as f:
            f.write(
                'task square(n: int) -> int:\n'
                '    return n * n\n'
                'let PI = 3.14159\n'
            )
        with open(os.path.join(tmpdir, "main.nk"), "w") as f:
            f.write(
                'import "utils.nk"\n'
                'show square(5)\n'
                'show PI\n'
            )

    def test_import_does_not_crash_with_attributeerror(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._write_project(tmpdir)
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "main.py"),
                 "run", "main.nk", "--quiet"],
                capture_output=True, text=True, cwd=tmpdir,
            )
            combined = result.stdout + result.stderr
            self.assertNotIn("has no attribute 'debug'", combined)
            self.assertIn("25", combined)
            self.assertIn("3.14159", combined)
        finally:
            shutil.rmtree(tmpdir)

    def test_interpreter_has_debug_attribute(self):
        interp = Interpreter()
        self.assertFalse(interp.debug)


# ── BUG-02: database bugs ────────────────────────────────────────

class TestDatabaseBugs(unittest.TestCase):

    def _fresh_db(self):
        tmpdir = tempfile.mkdtemp()
        # Forward slashes even on Windows: this path gets embedded
        # directly into a NEKOVA string literal below (db_connect
        # "{dbpath}"), and NEKOVA's own string lexer processes
        # backslash escapes the same way Python's does. A raw Windows
        # temp path like ...\Temp\tmp1234 turned \t into an actual
        # tab character once lexed, corrupting the path entirely.
        # sqlite3 (and Windows itself) both accept forward slashes
        # in paths just fine, so this sidesteps the problem rather
        # than trying to double-escape backslashes instead.
        dbpath = os.path.join(tmpdir, "t.db").replace(os.sep, "/")
        return tmpdir, dbpath

    def _cleanup(self, tmpdir):
        """
        Close the DB connection before removing the temp dir it lives
        in. On Linux, shutil.rmtree(tmpdir) alone was fine even with
        the sqlite3 file still open — POSIX allows unlinking a file
        that's still open, the data just stays around until the last
        handle closes. Windows enforces the opposite: a file with an
        open handle can't be deleted at all, so rmtree raised
        PermissionError there every time, on every one of these
        tests, none of which ever explicitly closed the connection.
        """
        db_module._db_close()
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_insert_key_value_syntax_stores_real_values(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT, age INTEGER")\n'
                'db_insert("t", "name=Alice, age=30")\n'
            )
            run(src)
            rows = sqlite3.connect(dbpath).execute(
                "SELECT * FROM t").fetchall()
            self.assertEqual(rows, [(1, "Alice", 30)])
        finally:
            self._cleanup(tmpdir)

    def test_insert_positional_syntax_still_works(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT, age INTEGER")\n'
                'db_insert("t", "Bob, 25")\n'
            )
            run(src)
            rows = sqlite3.connect(dbpath).execute(
                "SELECT * FROM t").fetchall()
            self.assertEqual(rows, [(1, "Bob", 25)])
        finally:
            self._cleanup(tmpdir)

    def test_insert_mixed_syntax_rejected_not_corrupted(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT, age INTEGER")\n'
                'db_insert("t", "name=Carol, 40")\n'
            )
            with self.assertRaises(NEKOVARuntimeError):
                run(src)
        finally:
            self._cleanup(tmpdir)

    def test_find_empty_filter_means_all_not_a_crash(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT")\n'
                'db_insert("t", "name=Alice")\n'
                'show db_find("t", "")\n'
            )
            output = run(src)
            self.assertIn("Alice", output)
        finally:
            self._cleanup(tmpdir)

    def test_bad_where_clause_raises_clean_nekova_error_not_traceback(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT, age INTEGER")\n'
                'db_insert("t", "name=Alice, age=30")\n'
                'db_update("t", "age=31", "name=Alice")\n'
            )
            with self.assertRaises(NEKOVARuntimeError):
                run(src)
        finally:
            self._cleanup(tmpdir)

    def test_documented_update_syntax_works(self):
        tmpdir, dbpath = self._fresh_db()
        try:
            src = (
                'use database\n'
                f'db_connect("{dbpath}")\n'
                'db_create("t", "name TEXT, age INTEGER")\n'
                'db_insert("t", "name=Alice, age=30")\n'
                "db_update(\"t\", \"age = 31\", \"name = 'Alice'\")\n"
                'show db_find("t", "all")\n'
            )
            output = run(src)
            self.assertIn("31", output)
        finally:
            self._cleanup(tmpdir)


# ── BUG-08: closures can't mutate enclosing scope ────────────────

class TestClosureMutation(unittest.TestCase):

    def test_counter_factory_increments_correctly(self):
        src = (
            'task make_counter():\n'
            '    let count = 0\n'
            '    task increment():\n'
            '        count = count + 1\n'
            '        return count\n'
            '    return increment\n'
            'let counter = make_counter()\n'
            'show counter()\n'
            'show counter()\n'
            'show counter()\n'
        )
        self.assertEqual(run(src), "1\n2\n3")

    def test_let_still_shadows_outer_variable(self):
        """A `let` with the same name as an outer variable must still
        create a fresh local binding (shadow), not mutate the outer
        one — is_declaration=True must always use .set(), never
        .update()."""
        src = (
            'let x = 1\n'
            'task foo():\n'
            '    let x = 2\n'
            '    show x\n'
            'foo()\n'
            'show x\n'
        )
        self.assertEqual(run(src), "2\n1")

    def test_global_keyword_still_works(self):
        src = (
            'let count = 0\n'
            'task increment():\n'
            '    global count\n'
            '    count = count + 1\n'
            '    return count\n'
            'show increment()\n'
            'show increment()\n'
            'show increment()\n'
        )
        self.assertEqual(run(src), "1\n2\n3")

    def test_reassignment_to_undeclared_name_creates_it_locally(self):
        """A bare reassignment to a name that doesn't exist anywhere
        should still work (falls back to creating it), matching
        Environment.update()'s documented fallback behavior."""
        src = (
            'task foo():\n'
            '    y = 5\n'
            '    show y\n'
            'foo()\n'
        )
        self.assertEqual(run(src), "5")


# ── BUG-09: plain strings silently interpolating ─────────────────

class TestStringInterpolation(unittest.TestCase):

    def test_plain_string_does_not_interpolate(self):
        src = (
            'let name = "World"\n'
            'show "just some {curly braces} text with {name} in it"\n'
        )
        self.assertEqual(
            run(src),
            "just some {curly braces} text with {name} in it")

    def test_fstring_still_interpolates(self):
        src = (
            'let name = "World"\n'
            'show f"Hello {name}!"\n'
        )
        self.assertEqual(run(src), "Hello World!")

    def test_plain_string_with_json_like_braces_is_safe(self):
        src = 'show "{\\"key\\": \\"value\\"}"\n'
        output = run(src)
        self.assertIn("key", output)
        self.assertIn("value", output)


# ── BUG-15 + related: dependency declarations and bare imports ──

class TestDependenciesAndImports(unittest.TestCase):

    def test_gtts_declared_in_pyproject(self):
        with open(os.path.join(REPO_ROOT, "pyproject.toml"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("gtts", content)

    def test_pytest_declared_in_pyproject(self):
        with open(os.path.join(REPO_ROOT, "pyproject.toml"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("pytest", content)

    def test_vm_module_imports_cleanly(self):
        from nekova.compiler.vm import VirtualMachine  # must not raise
        self.assertTrue(VirtualMachine)

    def test_ide_server_imports_cleanly(self):
        import nekova.web_ide.ide_server  # must not raise
        self.assertTrue(nekova.web_ide.ide_server)

    def test_ide_server_no_longer_references_root_formatter(self):
        path = os.path.join(REPO_ROOT, "nekova", "web_ide",
                             "ide_server.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # The actual old (buggy) import statement, not just any
        # mention of the phrase (which now also appears in an
        # explanatory comment about why it was fixed).
        self.assertNotIn("from formatter import NEKOVAFormatter", content)
        self.assertIn("from nekova.cli.formatter import fmt_source", content)


# ── BUG-16/17: --quiet flag and stale help text ──────────────────

class TestCliQuietFlagAndHelpText(unittest.TestCase):

    def test_quiet_flag_suppresses_banner(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "q.nk")
            with open(path, "w") as f:
                f.write('show "hi"\n')
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "main.py"),
                 "run", "q.nk", "--quiet"],
                capture_output=True, text=True, cwd=tmpdir,
            )
            combined = result.stdout + result.stderr
            self.assertNotIn("SYNEKCOT", combined)
            self.assertIn("hi", combined)
        finally:
            shutil.rmtree(tmpdir)

    def test_help_text_no_longer_says_python_main_py(self):
        with open(os.path.join(REPO_ROOT, "main.py"), encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("python main.py", content)


if __name__ == "__main__":
    unittest.main()