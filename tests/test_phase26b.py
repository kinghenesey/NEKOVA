"""
Phase 26b — Education Layer (v1.12.0)

Covers: nekova explain, nekova learn, nekova translate,
nekova classroom, nekova help / in-REPL glossary, the
--simple-errors flag, and the two new proactive checker warnings
(W010, W011).
"""
import unittest
import sys
import io
import os
import shutil
import tempfile
import subprocess
import contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _run_nekova(args, cwd=None, env_extra=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "main.py")] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd or REPO_ROOT, env=env,
    )


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Glossary ──────────────────────────────────────────────────

class TestGlossary(unittest.TestCase):

    def test_known_topic_returns_summary_and_example(self):
        from nekova.cli.glossary import format_topic
        out = format_topic("think")
        self.assertIn("AI-native", out)
        self.assertIn("Example:", out)

    def test_unknown_topic_suggests_near_misses(self):
        from nekova.cli.glossary import format_topic
        out = format_topic("tihnk")
        self.assertIn("No glossary entry", out)
        self.assertIn("think", out)

    def test_aliases_resolve_to_real_entries(self):
        from nekova.cli.glossary import get_topic
        self.assertIsNotNone(get_topic("function"))
        self.assertIsNotNone(get_topic("print"))
        self.assertEqual(get_topic("function"), get_topic("task"))

    def test_case_insensitive(self):
        from nekova.cli.glossary import get_topic
        self.assertEqual(get_topic("THINK"), get_topic("think"))

    def test_list_topics_nonempty_and_sorted(self):
        from nekova.cli.glossary import list_topics
        topics = list_topics()
        self.assertGreater(len(topics), 10)
        self.assertEqual(topics, sorted(topics))

    def test_cli_help_no_topic_lists_everything(self):
        result = _run_nekova(["help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Glossary", result.stdout)

    def test_cli_help_with_topic(self):
        result = _run_nekova(["help", "task"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("task", result.stdout.lower())

    def test_repl_help_topic_lookup(self):
        from repl import REPL
        r = REPL()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handled = r._handle_command("help think")
        self.assertTrue(handled)
        self.assertIn("AI-native", buf.getvalue())

    def test_repl_bare_help_still_shows_repl_help(self):
        from repl import REPL
        r = REPL()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handled = r._handle_command("help")
        self.assertTrue(handled)
        # The REPL's own help screen, not a glossary entry.
        self.assertIn("Commands", buf.getvalue())


# ── nekova explain ────────────────────────────────────────────

class TestExplain(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_name_error_explanation(self):
        from nekova.cli.explain import explain_error
        text = explain_error("NameError", "Undefined variable 'y'.", 2,
                              use_ai=False)
        self.assertIn("y", text)
        self.assertIn("let", text)

    def test_zero_division_explanation(self):
        from nekova.cli.explain import explain_error
        text = explain_error("ZeroDivisionError",
                              "Cannot divide by zero.", 3, use_ai=False)
        self.assertIn("divide", text.lower())

    def test_recursion_error_explanation(self):
        from nekova.cli.explain import explain_error
        text = explain_error("RecursionError",
                              "Maximum recursion depth exceeded.", 0,
                              use_ai=False)
        self.assertIn("base case", text.lower())

    def test_unknown_error_type_falls_back_gracefully(self):
        from nekova.cli.explain import explain_error
        text = explain_error("SomeWeirdError", "huh", 0, use_ai=False)
        self.assertTrue(len(text) > 0)

    def test_ai_addition_never_raises_even_without_provider(self):
        from nekova.cli.explain import explain_error
        # use_ai=True exercises the mock-provider path; must not raise.
        text = explain_error("NameError", "Undefined variable 'z'.", 1,
                              use_ai=True)
        self.assertIn("z", text)

    def test_cmd_explain_on_clean_file_reports_no_error(self):
        from nekova.cli.explain import cmd_explain
        path = os.path.join(self.tmpdir, "clean.nk")
        _write(path, 'show "all good"\n')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = cmd_explain(path, use_ai=False)
        self.assertTrue(ok)
        self.assertIn("ran without error", buf.getvalue())

    def test_cmd_explain_on_broken_file(self):
        from nekova.cli.explain import cmd_explain
        path = os.path.join(self.tmpdir, "broken.nk")
        _write(path, "let x = 5\nshow y\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = cmd_explain(path, use_ai=False)
        self.assertTrue(ok)
        out = buf.getvalue()
        self.assertIn("Explaining", out)
        self.assertIn("y", out)

    def test_cmd_explain_missing_file(self):
        from nekova.cli.explain import cmd_explain
        ok = cmd_explain(os.path.join(self.tmpdir, "nope.nk"), use_ai=False)
        self.assertFalse(ok)

    def test_cli_explain_subcommand(self):
        path = os.path.join(self.tmpdir, "broken.nk")
        _write(path, "let x = 5\nshow y\n")
        result = _run_nekova(["explain", path, "--no-ai"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Explaining", result.stdout)

    def test_cli_explain_no_arg_errors(self):
        result = _run_nekova(["explain"])
        self.assertNotEqual(result.returncode, 0)


# ── --simple-errors ───────────────────────────────────────────

class TestSimpleErrors(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simple_mode_omits_error_code(self):
        from nekova.cli.error_display import display_error
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_error("NameError", "Undefined variable 'y'.",
                          source="let x = 5\nshow y\n", filepath="t.nk",
                          line=2, simple=True)
        out = buf.getvalue()
        self.assertNotIn("E0", out)
        self.assertNotIn("-->", out)

    def test_normal_mode_still_has_error_code(self):
        from nekova.cli.error_display import display_error
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_error("NameError", "Undefined variable 'y'.",
                          source="let x = 5\nshow y\n", filepath="t.nk",
                          line=2, simple=False)
        out = buf.getvalue()
        self.assertIn("E0", out)

    def test_cli_run_with_simple_errors_flag(self):
        path = os.path.join(self.tmpdir, "broken.nk")
        _write(path, "let x = 5\nshow y\n")
        result = _run_nekova(["run", path, "--simple-errors"])
        self.assertNotIn("E00", result.stdout)
        self.assertIn("y", result.stdout)

    def test_cli_run_without_flag_unaffected(self):
        path = os.path.join(self.tmpdir, "broken.nk")
        _write(path, "let x = 5\nshow y\n")
        result = _run_nekova(["run", path])
        self.assertIn("E0", result.stdout)


# ── nekova translate ──────────────────────────────────────────

class TestTranslate(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_simple_assignment_and_print(self):
        from nekova.cli.translate import translate_source
        nk, warnings = translate_source('x = 5\nprint(x)\n')
        self.assertIn("let x = 5", nk)
        self.assertIn("show x", nk)

    def test_reassignment_omits_second_let(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source("x = 1\nx = 2\n")
        self.assertEqual(nk.count("let x"), 1)

    def test_function_becomes_task(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source(
            "def add(a, b):\n    return a + b\n"
        )
        self.assertIn("task add(a, b):", nk)
        self.assertIn("return (a + b)", nk)

    def test_if_elif_else(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source(
            "if n > 0:\n    x = 1\nelif n < 0:\n    x = 2\n"
            "else:\n    x = 3\n"
        )
        self.assertIn("if n > 0:", nk)
        self.assertIn("elif n < 0:", nk)
        self.assertIn("else:", nk)

    def test_print_multiple_args_becomes_fstring(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source('print("i is", i)\n')
        self.assertIn('f"i is {i}"', nk)

    def test_boolean_and_none_literals_translated(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source("x = True\ny = False\nz = None\n")
        self.assertIn("let x = true", nk)
        self.assertIn("let y = false", nk)
        self.assertIn("let z = null", nk)

    def test_fstring_translated(self):
        from nekova.cli.translate import translate_source
        nk, _ = translate_source('name = "Ada"\nprint(f"hi {name}")\n')
        self.assertIn('f"hi {name}"', nk)

    def test_import_flagged_not_silently_dropped(self):
        from nekova.cli.translate import translate_source
        nk, warnings = translate_source("import os\n")
        self.assertIn("TODO(translate)", nk)

    def test_unsupported_construct_flagged_with_reason(self):
        from nekova.cli.translate import translate_source
        nk, warnings = translate_source("x = [i for i in range(3)]\n")
        self.assertIn("TODO(translate)", nk)

    def test_translated_output_actually_runs(self):
        """The whole point: translated code must execute correctly
        against the real interpreter, not just look plausible."""
        from nekova.cli.translate import translate_source
        from nekova.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.interpreter.interpreter import Interpreter

        py_source = (
            "def double(x):\n"
            "    return x * 2\n"
            "print(double(21))\n"
        )
        nk, _ = translate_source(py_source)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tokens = Lexer(nk).tokenize()
            program = Parser(tokens).parse()
            Interpreter().execute(program, filepath="<test>")
        self.assertEqual(buf.getvalue().strip(), "42")

    def test_invalid_python_reports_error(self):
        from nekova.cli.translate import translate_source
        with self.assertRaises(SyntaxError):
            translate_source("def broken(:\n")

    def test_cmd_translate_writes_nk_file(self):
        from nekova.cli.translate import cmd_translate
        path = os.path.join(self.tmpdir, "script.py")
        _write(path, "x = 1\nprint(x)\n")
        ok = cmd_translate(path)
        self.assertTrue(ok)
        out_path = os.path.join(self.tmpdir, "script.nk")
        self.assertTrue(os.path.isfile(out_path))
        with open(out_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("let x = 1", content)

    def test_cli_translate_subcommand(self):
        path = os.path.join(self.tmpdir, "script.py")
        _write(path, "x = 1\nprint(x)\n")
        result = _run_nekova(["translate", path])
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmpdir, "script.nk")))


# ── nekova learn ──────────────────────────────────────────────

class TestLearn(unittest.TestCase):

    def test_lesson1_correct_answer_passes(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(LESSONS[0], "let age = 25")
        self.assertTrue(passed)
        self.assertEqual(error, "")

    def test_lesson1_wrong_value_fails(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(LESSONS[0], "let age = 99")
        self.assertFalse(passed)

    def test_lesson2_show_checks_output(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(
            LESSONS[1], 'show "Hello, NEKOVA!"')
        self.assertTrue(passed)
        self.assertIn("Hello, NEKOVA!", output)

    def test_lesson3_conditional_has_n_predefined(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(
            LESSONS[2], 'if n > 5: show "big"')
        self.assertTrue(passed)

    def test_lesson4_task_definition_and_call(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(
            LESSONS[3], "task double(x): return x * 2")
        self.assertTrue(passed)

    def test_lesson5_think_call(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(
            LESSONS[4], 'think "hello" as text')
        self.assertTrue(passed)

    def test_malformed_code_fails_gracefully_not_crash(self):
        from nekova.cli.learn import LESSONS, run_lesson
        passed, output, error = run_lesson(LESSONS[0], "let age = ")
        self.assertFalse(passed)
        self.assertNotEqual(error, "")

    def test_full_tutorial_all_correct(self):
        from nekova.cli.learn import cmd_learn
        answers = iter([
            "let age = 25",
            'show "Hello, NEKOVA!"',
            'if n > 5: show "big"',
            "task double(x): return x * 2",
            'think "hello" as text',
        ])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             unittest_mock_input(answers):
            cmd_learn()
        self.assertIn("5/5 lessons solved", buf.getvalue())

    def test_tutorial_stops_cleanly_on_eof(self):
        from nekova.cli.learn import cmd_learn

        def _raise_eof(prompt=""):
            raise EOFError()

        buf = io.StringIO()
        import builtins
        original_input = builtins.input
        builtins.input = _raise_eof
        try:
            with contextlib.redirect_stdout(buf):
                cmd_learn()
        finally:
            builtins.input = original_input
        self.assertIn("Stopping tutorial", buf.getvalue())

    def test_cli_learn_subcommand_runs_without_crashing_on_eof(self):
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "main.py"), "learn"],
            input="", capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(result.returncode, 0)


def unittest_mock_input(answer_iterator):
    """Context manager that patches builtins.input() to pull from
    an iterator, for driving cmd_learn()'s interactive loop in tests
    without a real terminal."""
    import builtins

    class _Patch:
        def __enter__(self):
            self._original = builtins.input
            builtins.input = lambda prompt="": next(answer_iterator)
            return self

        def __exit__(self, *exc):
            builtins.input = self._original

    return _Patch()


# ── nekova classroom ──────────────────────────────────────────

class TestClassroom(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.students_dir = os.path.join(self.tmpdir, "students")
        os.makedirs(self.students_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _solution(self, content):
        _write(os.path.join(self.tmpdir, "solution.nk"), content)

    def _student(self, name, content):
        _write(os.path.join(self.students_dir, f"{name}.nk"), content)

    def test_matching_submission_passes(self):
        from nekova.cli.classroom import grade_directory
        self._solution('show "hi"\n')
        self._student("alice", 'show "hi"\n')
        report = grade_directory(self.tmpdir)
        self.assertTrue(report["results"][0]["passed"])

    def test_wrong_output_fails(self):
        from nekova.cli.classroom import grade_directory
        self._solution('show "hi"\n')
        self._student("bob", 'show "bye"\n')
        report = grade_directory(self.tmpdir)
        self.assertFalse(report["results"][0]["passed"])

    def test_runtime_error_marked_crashed_not_passed(self):
        from nekova.cli.classroom import grade_directory
        self._solution('show "hi"\n')
        self._student("carol", "show undefined_var\n")
        report = grade_directory(self.tmpdir)
        r = report["results"][0]
        self.assertFalse(r["passed"])
        self.assertTrue(r["crashed"])

    def test_expected_txt_used_when_no_solution(self):
        from nekova.cli.classroom import grade_directory
        _write(os.path.join(self.tmpdir, "expected.txt"), "hi\n")
        self._student("dave", 'show "hi"\n')
        report = grade_directory(self.tmpdir)
        self.assertEqual(report["expected_source"], "expected.txt")
        self.assertTrue(report["results"][0]["passed"])

    def test_missing_expectation_raises(self):
        from nekova.cli.classroom import grade_directory
        self._student("eve", 'show "hi"\n')
        with self.assertRaises(ValueError):
            grade_directory(self.tmpdir)

    def test_missing_directory_raises(self):
        from nekova.cli.classroom import grade_directory
        with self.assertRaises(FileNotFoundError):
            grade_directory(os.path.join(self.tmpdir, "nope"))

    def test_trailing_whitespace_normalized(self):
        from nekova.cli.classroom import grade_directory
        self._solution('show "hi"\n')
        self._student("frank", 'show "hi"   \n')
        report = grade_directory(self.tmpdir)
        self.assertTrue(report["results"][0]["passed"])

    def test_flat_directory_without_students_subfolder(self):
        from nekova.cli.classroom import grade_directory
        shutil.rmtree(self.students_dir)
        self._solution('show "hi"\n')
        _write(os.path.join(self.tmpdir, "grace.nk"), 'show "hi"\n')
        report = grade_directory(self.tmpdir)
        names = [r["name"] for r in report["results"]]
        self.assertIn("grace", names)
        self.assertNotIn("solution", names)

    def test_cmd_classroom_prints_report(self):
        from nekova.cli.classroom import cmd_classroom
        self._solution('show "hi"\n')
        self._student("alice", 'show "hi"\n')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = cmd_classroom(self.tmpdir)
        self.assertTrue(ok)
        self.assertIn("1/1 passed", buf.getvalue())

    def test_cli_classroom_subcommand(self):
        self._solution('show "hi"\n')
        self._student("alice", 'show "hi"\n')
        result = _run_nekova(["classroom", self.tmpdir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("1/1 passed", result.stdout)


# ── Checker: W010 / W011 ──────────────────────────────────────

class TestCheckerProactiveMistakes(unittest.TestCase):

    def test_w010_boolean_comparison_flagged(self):
        from nekova.cli.checker import check_source
        issues = check_source(
            'let x = true\nif x == true:\n    show "yes"\n'
        )
        codes = [i.code for i in issues]
        self.assertIn("W010", codes)

    def test_w010_not_flagged_for_normal_comparison(self):
        from nekova.cli.checker import check_source
        issues = check_source(
            'let x = 5\nif x == 5:\n    show "yes"\n'
        )
        codes = [i.code for i in issues]
        self.assertNotIn("W010", codes)

    def test_w011_float_equality_flagged(self):
        from nekova.cli.checker import check_source
        issues = check_source(
            'let pi = 3.14\nif pi == 3.14:\n    show "yes"\n'
        )
        codes = [i.code for i in issues]
        self.assertIn("W011", codes)

    def test_w011_not_flagged_for_integers(self):
        from nekova.cli.checker import check_source
        issues = check_source(
            'let x = 3\nif x == 3:\n    show "yes"\n'
        )
        codes = [i.code for i in issues]
        self.assertNotIn("W011", codes)

    def test_w010_has_correct_line_number(self):
        from nekova.cli.checker import check_source
        issues = check_source(
            'let x = true\nlet y = 1\nif x == true:\n    show "yes"\n'
        )
        w010 = [i for i in issues if i.code == "W010"][0]
        self.assertEqual(w010.line, 3)


# ── Debugger: ASCII call-stack rendering ───────────────────────

class TestDebuggerCallStack(unittest.TestCase):

    def test_empty_stack_message(self):
        from debugger import render_call_stack_ascii
        out = render_call_stack_ascii([])
        self.assertIn("top level", out)

    def test_single_frame_has_no_dangling_connector(self):
        from debugger import render_call_stack_ascii
        out = render_call_stack_ascii(["main"])
        self.assertIn("main", out)
        self.assertIn("current", out)
        # A single frame's box should close cleanly on its own
        # bottom line, not trail off with a connector to nothing.
        last_line = out.splitlines()[-1]
        self.assertTrue(last_line.strip().endswith("┘"))
        self.assertNotIn("┬", last_line)

    def test_multi_frame_stack_shows_all_frames_innermost_first(self):
        from debugger import render_call_stack_ascii
        out = render_call_stack_ascii(["main", "compute(x=5)", "helper(y=3)"])
        # Innermost (last-called) frame is marked current and appears
        # before the outer frames in the rendered top-to-bottom order.
        self.assertIn("helper(y=3)", out)
        self.assertIn("compute(x=5)", out)
        self.assertIn("main", out)
        current_idx = out.index("← current")
        helper_idx = out.index("helper(y=3)")
        main_idx = out.index("main")
        self.assertLess(helper_idx, main_idx)
        self.assertGreater(current_idx, helper_idx)

    def test_box_width_accommodates_longest_frame_name(self):
        from debugger import render_call_stack_ascii
        out = render_call_stack_ascii(["a", "a_very_long_frame_name(x, y, z)"])
        # Every box-drawing line should be at least as wide as the
        # longest frame's label, or the label would be clipped.
        longest = len("a_very_long_frame_name(x, y, z)")
        box_lines = [l for l in out.splitlines() if "┌" in l or "└" in l]
        for line in box_lines:
            self.assertGreaterEqual(len(line.strip()), longest)

    def test_debugger_uses_renderer(self):
        from debugger import Debugger, render_call_stack_ascii
        import inspect
        source = inspect.getsource(Debugger._display_call_stack)
        self.assertIn("render_call_stack_ascii", source)


if __name__ == "__main__":
    unittest.main()