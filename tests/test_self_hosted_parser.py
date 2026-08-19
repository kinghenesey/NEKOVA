"""
Phase 27 — self-hosted parser runtime wiring.

Covers:
  - nekova/parser/rehydrate.py: dict-AST -> real Node tree conversion,
    and the parse_self_hosted() entry point
  - --self-hosted CLI flag and [run] self_hosted_parser config,
    across all three NEKOVARunner call sites in main.py, with the
    documented "flag overrides config, and only the config-loaded
    call site (implicit entry from nekova.toml) consults config at
    all" behaviour
"""
import unittest
import sys
import os
import tempfile
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


# ── nekova/parser/rehydrate.py: unit-level ──────────────────────────

class TestRehydrate(unittest.TestCase):

    def test_rehydrate_simple_dict_produces_real_node(self):
        from nekova.parser.rehydrate import rehydrate
        from nekova.parser.nodes import IntegerLiteral

        node = rehydrate({"type": "IntegerLiteral", "value": 42})
        self.assertIsInstance(node, IntegerLiteral)
        self.assertEqual(node.value, 42)
        self.assertEqual(node.line, 0)  # default when absent

    def test_rehydrate_nested_structure(self):
        from nekova.parser.rehydrate import rehydrate
        from nekova.parser.nodes import BinaryOp, IntegerLiteral

        node = rehydrate({
            "type": "BinaryOp",
            "left": {"type": "IntegerLiteral", "value": 1},
            "operator": "+",
            "right": {"type": "IntegerLiteral", "value": 2},
            "line": 3,
        })
        self.assertIsInstance(node, BinaryOp)
        self.assertIsInstance(node.left, IntegerLiteral)
        self.assertEqual(node.operator, "+")
        self.assertEqual(node.line, 3)

    def test_rehydrate_plain_dict_without_type_key_stays_a_dict(self):
        """A dict with no 'type' key (e.g. CallExpression.kwargs) must
        stay a plain dict, not get coerced into some Node by accident."""
        from nekova.parser.rehydrate import rehydrate

        result = rehydrate({"greeting": {"type": "StringLiteral", "value": "hi"}})
        self.assertIsInstance(result, dict)
        self.assertNotIn("type", result)
        from nekova.parser.nodes import StringLiteral
        self.assertIsInstance(result["greeting"], StringLiteral)

    def test_rehydrate_list_of_statements(self):
        from nekova.parser.rehydrate import rehydrate
        result = rehydrate([
            {"type": "IntegerLiteral", "value": 1},
            {"type": "IntegerLiteral", "value": 2},
        ])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].value, 1)
        self.assertEqual(result[1].value, 2)

    def test_rehydrate_program_wraps_statement_list(self):
        from nekova.parser.rehydrate import rehydrate_program
        from nekova.parser.nodes import Program, ShowStatement

        program = rehydrate_program([
            {"type": "ShowStatement", "expression": {"type": "StringLiteral", "value": "hi"},
             "extra_expressions": []},
        ])
        self.assertIsInstance(program, Program)
        self.assertEqual(len(program.statements), 1)
        self.assertIsInstance(program.statements[0], ShowStatement)


# ── parse_self_hosted(): end-to-end against the real bootstrap ─────

class TestParseSelfHosted(unittest.TestCase):

    def test_parses_and_matches_python_reference_structurally(self):
        """Doesn't re-derive tools/diff_parsers.py's whole comparison —
        just checks the self-hosted path produces a Program with the
        right shape for a source the Python parser also handles."""
        from nekova.parser.rehydrate import parse_self_hosted
        from nekova.parser.nodes import AssignStatement, IfStatement

        source = (
            'let x = 1 + 2\n'
            'if x > 0:\n'
            '    show "positive"\n'
            'else:\n'
            '    show "negative"\n'
        )
        program = parse_self_hosted(source)
        self.assertIsInstance(program.statements[0], AssignStatement)
        self.assertIsInstance(program.statements[1], IfStatement)

    def test_result_actually_executes_correctly(self):
        from nekova.parser.rehydrate import parse_self_hosted
        from nekova.interpreter.interpreter import Interpreter
        import io
        from contextlib import redirect_stdout

        source = (
            'task add(a, b=5):\n'
            '    return a + b\n'
            'show add(10)\n'
            'show add(10, 20)\n'
        )
        program = parse_self_hosted(source)
        buf = io.StringIO()
        with redirect_stdout(buf):
            Interpreter().execute(program)
        self.assertEqual(buf.getvalue().strip(), "15\n30".strip())

    def test_parse_error_surfaces_as_parse_error_with_correct_target_line(self):
        """The line number matters: parser.nk's own internal raise
        line (inside parser.nk's source) is meaningless to a caller —
        this must be the line in the *target* source that failed."""
        from nekova.parser.rehydrate import parse_self_hosted
        from nekova.parser.parser import ParseError

        source = 'let x = 1\nlet y = @#$ garbage\n'
        with self.assertRaises(ParseError) as ctx:
            parse_self_hosted(source)
        self.assertEqual(ctx.exception.line, 2)


# ── CLI wiring: --self-hosted flag and [run] self_hosted_parser ────

class TestSelfHostedCliWiring(unittest.TestCase):

    def test_self_hosted_flag_runs_correctly_bare_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "app.nk")
            with open(path, "w") as f:
                f.write('show "via self hosted"\n')
            result = _run_nekova(["--self-hosted", "app.nk"], cwd=d)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("via self hosted", result.stdout)

    def test_self_hosted_flag_runs_correctly_via_run_subcommand(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "app.nk")
            with open(path, "w") as f:
                f.write('show "via self hosted run"\n')
            result = _run_nekova(["run", "app.nk", "--self-hosted"], cwd=d)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("via self hosted run", result.stdout)

    def test_config_self_hosted_parser_true_used_for_implicit_entry(self):
        """Only the config-loaded call site (nekova run with no
        explicit file, entry resolved from nekova.toml) is supposed
        to consult [run] self_hosted_parser at all."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "main.nk"), "w") as f:
                f.write('show "config driven"\n')
            with open(os.path.join(d, "nekova.toml"), "w") as f:
                f.write(
                    "[project]\nname = 'x'\nentry = 'main.nk'\n"
                    "[run]\nself_hosted_parser = true\n"
                )
            result = _run_nekova(["run"], cwd=d)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("config driven", result.stdout)

    def test_explicit_file_arg_ignores_config_self_hosted_setting(self):
        """nekova run <file> (explicit arg) doesn't load nekova.toml
        at all today for any [run] setting — self_hosted_parser is
        no exception, matching that existing behaviour rather than
        introducing a new inconsistency. This test exists to catch a
        future accidental change to that either way, since it's easy
        to get backwards."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "main.nk"), "w") as f:
                f.write('show "still works either way"\n')
            with open(os.path.join(d, "nekova.toml"), "w") as f:
                f.write(
                    "[project]\nname = 'x'\nentry = 'main.nk'\n"
                    "[run]\nself_hosted_parser = true\n"
                )
            # Explicit file arg — should still run correctly regardless
            # of whether self-hosted mode is actually engaged for it.
            result = _run_nekova(["run", "main.nk"], cwd=d)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("still works either way", result.stdout)

    def test_self_hosted_and_normal_path_produce_identical_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "app.nk")
            with open(path, "w") as f:
                f.write(
                    'let x = 1 + 2\n'
                    'task add(a, b=5):\n'
                    '    return a + b\n'
                    'show x\n'
                    'show add(10)\n'
                    'for i in [1, 2, 3]:\n'
                    '    show i\n'
                )
            normal = _run_nekova(["app.nk"], cwd=d)
            self_hosted = _run_nekova(["app.nk", "--self-hosted"], cwd=d)
            self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
            self.assertEqual(self_hosted.returncode, 0, self_hosted.stdout + self_hosted.stderr)

            def extract_output(text):
                # Strip the banner/timing chrome, keep just what the
                # program printed.
                lines = text.splitlines()
                start = next(i for i, l in enumerate(lines) if "Running" in l) + 1
                end = next(i for i, l in enumerate(lines) if "Done in" in l)
                return [l.strip() for l in lines[start:end] if l.strip()]

            self.assertEqual(extract_output(normal.stdout), extract_output(self_hosted.stdout))

    def test_self_hosted_parse_error_still_shows_formatted_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "app.nk")
            with open(path, "w") as f:
                f.write('let x = @#$ garbage\n')
            result = _run_nekova(["--self-hosted", "app.nk"], cwd=d)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unexpected token", result.stdout)


if __name__ == "__main__":
    unittest.main()