"""
Bug Fix Regression Tests — Round 5
Fixes for bugs found by an independent review pass, verified against
the live repo before fixing (see conversation history). Covers:

  1. formatter.py `_fix_indentation` corrupted valid code — any indent
     under 4 spaces floor-divided to 0, deleting the block entirely.
     Rewritten to track nesting depth with a stack instead of
     rounding each line's raw space count in isolation.

  2. Type hints for str/bool/float were unenforced in practice:
     _check_type tried `py_type(val)` for every hint, but str(),
     bool(), float() almost never raise, and even when a coercion DID
     happen, the result was returned and discarded by the caller.
     Now strict per-type checking with the one safe coercion
     (int -> float widening).

  3. `nekova compile` / `nekova export` / `nekova ide` all raised
     "No module named 'lexer'" (and 'parser', 'interpreter',
     'compiler') from bare imports missing the `nekova.` package
     prefix. Also, once those imports were fixed, two more bugs
     surfaced in the transpiler itself: task params were joined as
     raw tuples instead of formatted Python parameter syntax, and
     call-site keyword arguments were dropped entirely.

  4. `nekova test` resolved its search root from the installed
     package's __file__ location instead of the user's cwd, so it
     could never find a scaffolded project's own tests/ folder.

  5. `nekova package` used the wrong source-file extension (.NEKOVA
     instead of .nk, so it never found any source files), wrote its
     output relative to the invoking shell's cwd instead of the
     target project directory, and never actually read a real
     project's nekova.toml (only a NEKOVA.json that scaffolded
     projects don't create), so name/version always fell back to
     generic defaults.

  6. debugger.py had literal '?' characters baked into several
     messages and its section borders, not a Unicode rendering
     failure — replaced with appropriate icons.

  7. The "variable not found" quick-fix hint read "Add before before
     use" when no line number was available, from the fallback string
     itself containing "before use" being wrapped in "Add before {loc}".

  8. `sort()` existed only as a list *method*, not a bare pipeable
     global (unlike map/filter), so `data |> sort()` failed with
     "Variable 'sort' does not exist" despite the README's documented
     pipe example showing it chained. `take()` didn't exist as a
     global at all. Separately, map/filter's own parameter order
     (function, data) was backwards for how the pipe operator always
     calls things (piped value first) — fixed to (data, function).
"""
import unittest
import sys
import io
import os
import re
import tempfile
import shutil

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
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


# ── Bug 1: Formatter indentation corruption ────────────────────

class TestFormatterIndentation(unittest.TestCase):

    def setUp(self):
        import formatter as formatter_mod
        self.Formatter = formatter_mod.NEKOVAFormatter
        self.fmt = self.Formatter("")

    def test_three_space_indent_not_collapsed_to_zero(self):
        """The original corruption bug: any indent under 4 spaces
        used to floor-divide to 0, deleting the block entirely."""
        lines = ["task foo():", "   return 1"]
        result = self.fmt._fix_indentation(lines)
        self.assertEqual(result[1], "    return 1")
        self.assertTrue(result[1].startswith("    "))

    def test_already_four_space_indent_unaffected(self):
        lines = ["task foo():", "    return 1"]
        result = self.fmt._fix_indentation(lines)
        self.assertEqual(result[1], "    return 1")

    def test_nested_two_space_indent_preserves_depth(self):
        """Per-line absolute-space rounding used to merge separate
        nesting levels together when raw widths coincided (e.g. a
        2-space file's level-2 has the same raw width as a 4-space
        file's level-1)."""
        lines = [
            "task outer():",
            "  if x > 0:",
            "    return x",
            "  return 0",
        ]
        result = self.fmt._fix_indentation(lines)
        self.assertEqual(result[0], "task outer():")
        self.assertEqual(result[1], "    if x > 0:")
        self.assertEqual(result[2], "        return x")
        self.assertEqual(result[3], "    return 0")

    def test_formatted_file_still_runs(self):
        """End-to-end: format a 3-space-indented file and confirm it
        still executes correctly afterward."""
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("task foo(a, b):\n   return a + b\nshow foo(2, 3)\n")
            from formatter import format_file
            format_file(path)
            with open(path) as f:
                content = f.read()
            self.assertIn("    return a + b", content)
            tokens = Lexer(content).tokenize()
            ast = Parser(tokens).parse()  # must not raise
            interp = Interpreter()
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                interp.run(ast)
            finally:
                sys.stdout = old
            self.assertEqual(buf.getvalue().strip(), "5")
        finally:
            shutil.rmtree(tmpdir)


# ── Bug 2: Type hint enforcement ───────────────────────────────

class TestTypeHintEnforcement(unittest.TestCase):

    def test_str_hint_rejects_int(self):
        src = (
            'task s(n: str) -> str:\n'
            '    return n\n'
            'show s(42)\n'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_bool_hint_rejects_string(self):
        src = (
            'task b(f: bool) -> bool:\n'
            '    return f\n'
            'show b("yes")\n'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_float_hint_rejects_string(self):
        src = (
            'task f(x: float) -> float:\n'
            '    return x\n'
            'show f("hi")\n'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_int_hint_still_rejects_string(self):
        src = (
            'task i(x: int) -> int:\n'
            '    return x\n'
            'show i("hello")\n'
        )
        with self.assertRaises(NEKOVARuntimeError):
            run(src)

    def test_correct_types_still_pass(self):
        src = (
            'task s(n: str) -> str:\n'
            '    return n\n'
            'show s("hi")\n'
        )
        self.assertEqual(run(src), "hi")

    def test_int_to_float_widening_allowed(self):
        """The one intentional coercion: an int literal passed where
        a float is expected."""
        src = (
            'task f(x: float) -> float:\n'
            '    return x\n'
            'show f(5)\n'
        )
        self.assertEqual(run(src), "5.0")


# ── Bug 3: compile/export imports + transpiler ─────────────────

class TestCompileExportImports(unittest.TestCase):

    def test_exporter_imports_cleanly(self):
        from nekova.deploy.exporter import Exporter  # must not raise ImportError
        self.assertTrue(Exporter)

    def test_llvm_backend_imports_cleanly(self):
        from nekova.compiler.llvm_backend import LLVMCompiler
        self.assertTrue(LLVMCompiler)

    def test_transpiler_formats_params_correctly(self):
        from nekova.compiler.transpiler import NEKOVATranspiler
        source = (
            'task build(a, b = "B", c = "C", d = "D"):\n'
            '    show a + "-" + b + "-" + c + "-" + d\n'
            'build("A", d="D2", b="B2")\n'
            'build(a="A2", c="C2")\n'
        )
        t = NEKOVATranspiler()
        tmpdir = tempfile.mkdtemp()
        try:
            out_path = os.path.join(tmpdir, "out.py")
            t.compile(source, out_path)  # must not raise TypeError
            py_code = "\n".join(t.output_lines)
            self.assertIn("def build(a, b=", py_code)
        finally:
            shutil.rmtree(tmpdir)

    def test_transpiler_preserves_call_site_kwargs(self):
        """Previously kwargs were dropped entirely during
        transpilation, e.g. build(a="A2", c="C2") became build()."""
        from nekova.compiler.transpiler import NEKOVATranspiler
        source = (
            'task build(a, b = "B"):\n'
            '    show a + b\n'
            'build(a="X", b="Y")\n'
        )
        t = NEKOVATranspiler()
        tmpdir = tempfile.mkdtemp()
        try:
            out_path = os.path.join(tmpdir, "out.py")
            t.compile(source, out_path)
            py_code = "\n".join(t.output_lines)
            self.assertIn('a=', py_code.split("build(")[-1])
            self.assertIn('b=', py_code.split("build(")[-1])
        finally:
            shutil.rmtree(tmpdir)


# ── Bug 4: `nekova test` cwd resolution ─────────────────────────

class TestNekovaTestCwd(unittest.TestCase):

    def test_missing_tests_dir_gives_clear_error_not_crash(self):
        from nekova.cli.commands import cmd_test
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = cmd_test()
            self.assertFalse(result)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)

    def test_finds_tests_dir_in_cwd_not_package_dir(self):
        from nekova.cli.commands import cmd_test
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(tests_dir)
            with open(os.path.join(tests_dir, "test_dummy.py"), "w") as f:
                f.write("def test_ok():\n    assert True\n")
            os.chdir(tmpdir)
            result = cmd_test()
            self.assertTrue(result)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)


# ── Bug 5: Packager ─────────────────────────────────────────────

class TestPackager(unittest.TestCase):

    def _make_project(self, tmpdir, name="myproj"):
        proj = os.path.join(tmpdir, name)
        os.makedirs(os.path.join(proj, "src"))
        with open(os.path.join(proj, "nekova.toml"), "w") as f:
            f.write(
                '[project]\n'
                f'name = "{name}"\n'
                'version = "2.3.4"\n'
                'entry = "src/main.nk"\n'
            )
        with open(os.path.join(proj, "src", "main.nk"), "w") as f:
            f.write('show "hi"\n')
        return proj

    def test_finds_nk_source_files(self):
        from nekova.deploy.packager import Packager
        tmpdir = tempfile.mkdtemp()
        try:
            proj = self._make_project(tmpdir)
            pkg = Packager(proj)
            files = pkg._find_NEKOVA_files()
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith("main.nk"))
        finally:
            shutil.rmtree(tmpdir)

    def test_reads_real_project_name_and_version_from_toml(self):
        from nekova.deploy.packager import Packager
        tmpdir = tempfile.mkdtemp()
        try:
            proj = self._make_project(tmpdir)
            pkg = Packager(proj)
            self.assertEqual(pkg.name, "myproj")
            self.assertEqual(pkg.version, "2.3.4")
        finally:
            shutil.rmtree(tmpdir)

    def test_output_lands_inside_target_project_not_cwd(self):
        from nekova.deploy.packager import Packager
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            proj = self._make_project(tmpdir, "otherproj")
            elsewhere = os.path.join(tmpdir, "elsewhere")
            os.makedirs(elsewhere)
            os.chdir(elsewhere)
            pkg = Packager(proj)
            pkg_path = pkg.build("dist")
            self.assertTrue(pkg_path.startswith(proj))
            self.assertFalse(
                os.path.exists(os.path.join(elsewhere, "dist")))
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)

    def test_package_contains_source_files(self):
        import zipfile
        from nekova.deploy.packager import Packager
        tmpdir = tempfile.mkdtemp()
        try:
            proj = self._make_project(tmpdir)
            pkg = Packager(proj)
            pkg_path = pkg.build("dist")
            with zipfile.ZipFile(pkg_path) as zf:
                names = zf.namelist()
            self.assertTrue(any(n.endswith("main.nk") for n in names))
        finally:
            shutil.rmtree(tmpdir)


# ── Bug 6: Debugger literal '?' characters ──────────────────────

class TestDebuggerNoLiteralQuestionMarks(unittest.TestCase):

    def test_no_bare_question_mark_border_or_icons_in_source(self):
        with open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "debugger.py"),
            encoding="utf-8"
        ) as f:
            src = f.read()
        self.assertNotIn("'?' * width", src)
        self.assertNotIn('f"? ', src)
        self.assertNotIn('f"  ? ', src)


# ── Bug 7: "before before use" typo ─────────────────────────────

class TestQuickFixTypo(unittest.TestCase):

    def test_no_line_number_reads_correctly(self):
        from nekova.cli.error_display import _quick_fix
        msg = _quick_fix("NameError", "Variable 'x' does not exist.", 0, 0)
        self.assertNotIn("before before", msg)
        self.assertIn("Add before use:", msg)

    def test_with_line_number_still_works(self):
        from nekova.cli.error_display import _quick_fix
        msg = _quick_fix("NameError", "Variable 'x' does not exist.", 5, 2)
        self.assertNotIn("before before", msg)
        self.assertIn("Add before line 5:", msg)


# ── Bug 8: sort()/take() pipeable, map/filter arg order ────────

class TestPipeableBuiltins(unittest.TestCase):

    def test_sort_pipeable(self):
        src = (
            'let data = [5, 3, 1, 4]\n'
            'let result = data |> sort()\n'
            'show result\n'
        )
        self.assertEqual(run(src), "[1, 3, 4, 5]")

    def test_take_pipeable(self):
        src = (
            'let data = [5, 3, 1, 4]\n'
            'let result = data |> sort() |> take(2)\n'
            'show result\n'
        )
        self.assertEqual(run(src), "[1, 3]")

    def test_filter_pipeable_with_task_predicate(self):
        src = (
            'task is_big(x):\n'
            '    return x > 2\n'
            'let data = [5, 3, 1, 4]\n'
            'let result = data |> filter(is_big)\n'
            'show result\n'
        )
        self.assertEqual(run(src), "[5, 3, 4]")

    def test_map_pipeable_with_task(self):
        src = (
            'task double(x):\n'
            '    return x * 2\n'
            'let data = [1, 2, 3]\n'
            'let result = data |> map(double)\n'
            'show result\n'
        )
        self.assertEqual(run(src), "[2, 4, 6]")

    def test_full_documented_pipe_chain(self):
        src = (
            'task is_big(x):\n'
            '    return x > 2\n'
            'let data = [5, 3, 1, 4]\n'
            'let result = data |> filter(is_big) |> sort() |> take(2)\n'
            'show result\n'
        )
        self.assertEqual(run(src), "[3, 4]")


# ── Bug 9: Postfix .method() generalized to composite literals ──

class TestPostfixOnCompositeLiterals(unittest.TestCase):

    def test_method_call_on_list_literal(self):
        src = 'show [3, 1, 2].sort()\n'
        self.assertEqual(run(src), "[1, 2, 3]")

    def test_method_call_on_dict_literal(self):
        src = 'show {"a": 1, "b": 2}.keys()\n'
        self.assertEqual(run(src), "[a, b]")

    def test_variable_based_method_call_still_works(self):
        """Regression guard: don't break the pre-existing path."""
        src = (
            'let lst = [3, 1, 2]\n'
            'show lst.sort()\n'
        )
        self.assertEqual(run(src), "[1, 2, 3]")

    def test_index_after_grouped_expression_still_works(self):
        src = 'show (1 + 2)\n'
        self.assertEqual(run(src), "3")


# ── Bug 10: README flagship example (every blocking, think silent) ──

class TestEveryDoesNotBlock(unittest.TestCase):

    def test_infinite_every_does_not_block_subsequent_statements(self):
        """Previously `every N s:` (infinite form) started a real
        background thread but then immediately called t.join() on it
        anyway, blocking the calling script forever."""
        import threading
        src = (
            'every 5 s:\n'
            '    show "tick"\n'
            'show "reached after every"\n'
        )
        result = {}

        def target():
            result["output"] = run(src)

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout=5)
        self.assertFalse(t.is_alive(),
                          "run() did not return — every still blocks")
        self.assertIn("reached after every", result.get("output", ""))


class TestThinkAsStandaloneOutput(unittest.TestCase):

    def test_standalone_think_as_prints_something(self):
        """A bare `think "..." as text` with no assignment previously
        printed nothing at all, even in mock mode."""
        src = 'think "hello" as text\nshow "after"\n'
        output = run(src)
        lines = output.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)
        self.assertIn("after", output)

    def test_captured_think_as_stays_silent(self):
        """Captured usage should NOT print a banner — that's the
        normal case for programmatic/structured extraction, and is
        what the pre-existing test suite already relies on."""
        src = 'let x = think "hello" as text\nshow x\n'
        output = run(src)
        # Exactly one line of output: the captured value via show,
        # no separate "think" banner line before it.
        self.assertEqual(len(output.strip().split("\n")), 1)


if __name__ == "__main__":
    unittest.main()