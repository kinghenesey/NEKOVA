"""
Bug Fix Regression Tests — Round 7

Covers a fresh QA pass done after Phase 26 shipped. Verified against
the live repo before fixing (see conversation history) -- two of the
six reported items turned out to already be fixed (the --quiet flag,
one of the two docsite changelog gaps had recurred), and the
single-line-body issue turned out to be a pre-existing bug that
predates Phase 26 entirely (confirmed by testing the actual 1.10.0
release commit directly), not a regression from the parser work in
this repo. Covers:

  1. filter()/map() with a *typed* task predicate crashed with "too
     many values to unpack (expected 3)". _invoke_callable routed
     every task through _call_task, which unpacks params as 3-tuples
     (name, default, is_vararg) -- correct for plain TaskStatement,
     but TypedTaskStatement's params are 4-tuples (name, type_hint,
     default, is_vararg). Now dispatches typed tasks to
     _call_typed_task instead.

     Investigating this surfaced a much bigger, separate bug: ANY
     builtin function called with keyword-argument syntax silently
     dropped every keyword. The builtin-dispatch branch in
     _exec_CallExpression called `callee(*args)` -- positional args
     only -- and returned before node.kwargs was ever even looked
     at. sorted(x, key=fn), round(x, n=2), enumerate(x, start=1) all
     silently ignored their keyword argument. Fixed by evaluating and
     passing node.kwargs through as **kwargs. sorted()'s key= also
     needed its own fix on top of that, since Python's real sorted()
     calls key(item) directly and a NEKOVA task isn't callable that
     way -- routed through _invoke_callable too.

  2. Single-line block bodies (`task add(a, b): return a + b`,
     `if true: show "yes"`, etc.) didn't parse at all -- confirmed
     NOT a Phase 26 regression by testing the actual 1.10.0 commit,
     which fails identically. _parse_block() and the separately
     duplicated _parse_block_with_docstring() and _parse_prompt_body()
     all unconditionally required a real INDENT token. Fixed all
     three to recognize "content directly follows the ':', no
     NEWLINE" as an inline single-statement body.

  3. `nekova test` printed "Some tests failed" and exited nonzero
     when zero tests were collected (pytest exit code 5) -- treated
     the same as real failures (exit code 1). Fixed to report "No
     tests found" and exit 0.

  4. `nekova compile`'s success message had a mojibake arrow
     character (double-encoded UTF-8) instead of a real "→". Same
     exact corrupted byte sequence also found and fixed in
     notebook.py and CHANGELOG.md.
"""
import unittest
import sys
import io
import os
import re
import tempfile
import shutil
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def _run_nekova(args, cwd, env_extra=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "main.py")] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd, env=env,
    )


# ── Bug 1: filter/map/sorted with typed tasks + builtin kwargs ──

class TestTypedTaskPredicates(unittest.TestCase):

    def test_filter_with_typed_task_predicate(self):
        src = (
            'task gt3(x: int) -> bool:\n'
            '    return x > 3\n'
            'show [5, 3, 8, 1, 9, 2] |> filter(gt3)\n'
        )
        self.assertEqual(run(src), "[5, 8, 9]")

    def test_map_with_typed_task(self):
        src = (
            'task double(x: int) -> int:\n'
            '    return x * 2\n'
            'show [1, 2, 3] |> map(double)\n'
        )
        self.assertEqual(run(src), "[2, 4, 6]")

    def test_filter_with_plain_untyped_task_still_works(self):
        src = (
            'task is_big(x):\n'
            '    return x > 2\n'
            'let data = [5, 3, 1, 4]\n'
            'show data |> filter(is_big)\n'
        )
        self.assertEqual(run(src), "[5, 3, 4]")


class TestBuiltinKeywordArguments(unittest.TestCase):

    def test_round_with_keyword_argument(self):
        self.assertEqual(run("show round(3.14159, n=2)\n"), "3.14")

    def test_enumerate_with_start_keyword(self):
        src = 'show enumerate(["a", "b", "c"], start=1)\n'
        self.assertEqual(run(src), '[(1, a), (2, b), (3, c)]')

    def test_sorted_with_key_builtin_function(self):
        # A trivial non-task key, to isolate "kwargs reach the
        # builtin at all" from the separate task-callable fix below.
        src = 'show sorted([3, 1, 2], reverse=true)\n'
        self.assertEqual(run(src), "[3, 2, 1]")

    def test_sorted_with_task_as_key(self):
        src = (
            'task neg(x: int) -> int:\n'
            '    return 0 - x\n'
            'let data = [3, 1, 4, 1, 5]\n'
            'show sorted(data, key=neg)\n'
        )
        self.assertEqual(run(src), "[5, 4, 3, 1, 1]")


# ── Bug 2: single-line block bodies ──────────────────────────

class TestSingleLineBlockBodies(unittest.TestCase):

    def test_single_line_typed_task(self):
        src = (
            'task add(a: int, b: int) -> int: return a + b\n'
            'show add(2, 3)\n'
        )
        self.assertEqual(run(src), "5")

    def test_single_line_untyped_task(self):
        src = (
            'task add(a, b): return a + b\n'
            'show add(2, 3)\n'
        )
        self.assertEqual(run(src), "5")

    def test_single_line_if(self):
        self.assertEqual(run('if true: show "yes"\n'), "yes")

    def test_single_line_while(self):
        src = 'let i = 0\nwhile i < 3: i = i + 1\nshow i\n'
        self.assertEqual(run(src), "3")

    def test_single_line_for(self):
        src = 'for x in [1, 2, 3]: show x\n'
        self.assertEqual(run(src), "1\n2\n3")

    def test_single_line_try_catch(self):
        src = 'try: show "ok"\ncatch e: show "caught"\n'
        self.assertEqual(run(src), "ok")

    def test_single_line_method_in_class(self):
        src = (
            'class Point:\n'
            '    init(x, y):\n'
            '        self.x = x\n'
            '        self.y = y\n'
            '    func total(): return self.x + self.y\n'
            'let p = new Point(3, 4)\n'
            'show p.total()\n'
        )
        self.assertEqual(run(src), "7")

    def test_single_line_async_task(self):
        src = (
            'async task double(x): return x * 2\n'
            'show await double(5)\n'
        )
        self.assertEqual(run(src), "10")

    def test_single_line_prompt(self):
        src = (
            'prompt greet(name): "Hello, {name}!"\n'
            'show greet(name="World")\n'
        )
        result = run(src)
        self.assertIn("Hello, World!", result)

    def test_multiline_task_still_works(self):
        """Regression guard: the fix must not break the normal
        multi-line form."""
        src = (
            'task add(a, b):\n'
            '    return a + b\n'
            'show add(2, 3)\n'
        )
        self.assertEqual(run(src), "5")

    def test_multiline_with_docstring_still_works(self):
        src = (
            'task greet(name):\n'
            '    """Greets someone."""\n'
            '    show "Hello, " + name\n'
            'greet("World")\n'
        )
        self.assertEqual(run(src), "Hello, World")

    def test_multiline_if_else_still_works(self):
        src = (
            'if false:\n'
            '    show "no"\n'
            'else:\n'
            '    show "yes"\n'
        )
        self.assertEqual(run(src), "yes")


# ── Bug 3: nekova test with zero tests collected ─────────────

class TestNekovaTestZeroTests(unittest.TestCase):

    def test_zero_tests_exits_zero_not_one(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "tests"))
            with open(os.path.join(tmpdir, "tests", ".gitkeep"), "w") as f:
                f.write("")
            result = _run_nekova(["test", "--quiet"], cwd=tmpdir)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn("Some tests failed", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_zero_tests_reports_no_tests_found(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "tests"))
            with open(os.path.join(tmpdir, "tests", ".gitkeep"), "w") as f:
                f.write("")
            result = _run_nekova(["test", "--quiet"], cwd=tmpdir)
            self.assertIn("No tests found", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_passing_tests_still_exit_zero(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "tests"))
            with open(os.path.join(tmpdir, "tests", "test_x.py"), "w") as f:
                f.write("def test_ok():\n    assert True\n")
            result = _run_nekova(["test", "--quiet"], cwd=tmpdir)
            self.assertEqual(result.returncode, 0)
            self.assertIn("All tests passed", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_failing_tests_still_exit_nonzero(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "tests"))
            with open(os.path.join(tmpdir, "tests", "test_x.py"), "w") as f:
                f.write("def test_fail():\n    assert False\n")
            result = _run_nekova(["test", "--quiet"], cwd=tmpdir)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Some tests failed", result.stdout + result.stderr)
        finally:
            shutil.rmtree(tmpdir)


# ── Bug 4: compile mojibake arrow ────────────────────────────

class TestCompileMojibakeFix(unittest.TestCase):

    def test_compile_success_message_has_real_arrow(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write('show 1 + 1\n')
            result = _run_nekova(["compile", "f.nk", "--quiet"], cwd=tmpdir)
            self.assertIn("Compiled \u2192", result.stdout)
            self.assertNotIn("\u00c3\u00a2", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_no_mojibake_arrow_bytes_remain_in_source(self):
        mojibake = b"\xc3\xa2\xe2\x80\xa0\xe2\x80\x99"
        for fname in ("main.py", "notebook.py"):
            path = os.path.join(REPO_ROOT, fname)
            with open(path, "rb") as f:
                data = f.read()
            self.assertNotIn(mojibake, data, f"{fname} still has the mojibake arrow")


if __name__ == "__main__":
    unittest.main()