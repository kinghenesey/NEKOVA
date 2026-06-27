"""
Phase 19 — NEKOVA Sandbox
Tests for: SandboxResult, SandboxEnvironment, run_sandboxed(),
           sandbox statement, resource limits, violation tracking
"""
import unittest
import sys
import io
import re

from nekova.sandbox import run_sandboxed, SandboxResult, SandboxEnvironment
from nekova.sandbox.environment import STRICT_ALLOWLIST, RELAXED_ALLOWLIST
from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.ai import memory_store as _mem_store


def run(source: str) -> str:
    _mem_store._memory.clear()
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


# ── SandboxResult ─────────────────────────────────────────────

class TestSandboxResult(unittest.TestCase):

    def test_default_values(self):
        r = SandboxResult()
        self.assertEqual(r.output, "")
        self.assertIsNone(r.error)
        self.assertTrue(r.safe)
        self.assertEqual(r.duration, 0.0)
        self.assertEqual(r.mode, "strict")
        self.assertEqual(r.violations, [])

    def test_ok_true_when_safe_no_error(self):
        r = SandboxResult(safe=True, error=None)
        self.assertTrue(r.ok)

    def test_ok_false_when_error(self):
        r = SandboxResult(safe=True, error="something went wrong")
        self.assertFalse(r.ok)

    def test_ok_false_when_not_safe(self):
        r = SandboxResult(safe=False, error=None)
        self.assertFalse(r.ok)

    def test_repr_ok(self):
        r = SandboxResult(output="hello", safe=True)
        self.assertIn("ok", repr(r))

    def test_repr_failed(self):
        r = SandboxResult(safe=False, error="blocked")
        self.assertIn("failed", repr(r))


# ── SandboxEnvironment ────────────────────────────────────────

class TestSandboxEnvironment(unittest.TestCase):

    def _make_env(self, mode="strict"):
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        return SandboxEnvironment(parent=interp.globals, mode=mode)

    def test_strict_allowlist_nonempty(self):
        self.assertIn("len", STRICT_ALLOWLIST)
        self.assertIn("str", STRICT_ALLOWLIST)
        self.assertIn("range", STRICT_ALLOWLIST)

    def test_relaxed_superset_of_strict(self):
        self.assertTrue(STRICT_ALLOWLIST.issubset(RELAXED_ALLOWLIST))

    def test_relaxed_adds_file_read(self):
        self.assertIn("file_read", RELAXED_ALLOWLIST)
        self.assertNotIn("file_read", STRICT_ALLOWLIST)

    def test_blocks_always_blocked_names(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        env = self._make_env("strict")
        with self.assertRaises(NEKOVARuntimeError):
            env.get("eval")

    def test_blocks_exec(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        env = self._make_env("strict")
        with self.assertRaises(NEKOVARuntimeError):
            env.get("exec")

    def test_records_violation(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        env = self._make_env("strict")
        try:
            env.get("eval")
        except NEKOVARuntimeError:
            pass
        self.assertEqual(len(env.violations), 1)
        self.assertEqual(env.violations[0]["operation"], "eval")

    def test_allows_safe_names(self):
        env = self._make_env("strict")
        # len is always available — should not raise
        val = env.get("len")
        self.assertIsNotNone(val)

    def test_set_always_works(self):
        env = self._make_env("strict")
        env.set("myvar", 42)
        self.assertEqual(env.get("myvar"), 42)


# ── run_sandboxed() ───────────────────────────────────────────

class TestRunSandboxed(unittest.TestCase):

    def test_basic_computation(self):
        r = run_sandboxed("show 1 + 1")
        self.assertEqual(r.output.strip(), "2")
        self.assertTrue(r.ok)

    def test_returns_sandboxresult(self):
        r = run_sandboxed("show 42")
        self.assertIsInstance(r, SandboxResult)

    def test_mode_stored(self):
        r = run_sandboxed("show 1", mode="relaxed")
        self.assertEqual(r.mode, "relaxed")

    def test_output_captured(self):
        r = run_sandboxed('show "hello"\nshow "world"')
        self.assertIn("hello", r.output)
        self.assertIn("world", r.output)

    def test_duration_measured(self):
        r = run_sandboxed("show 1")
        self.assertGreaterEqual(r.duration, 0)  # Windows timer may return 0.0 for fast runs
        self.assertLess(r.duration, 5)

    def test_syntax_error_caught(self):
        r = run_sandboxed("this is not valid !!!@@@")
        self.assertFalse(r.ok)
        self.assertIsNotNone(r.error)

    def test_runtime_error_caught(self):
        r = run_sandboxed("show undefined_variable_xyz")
        self.assertFalse(r.ok)
        self.assertIsNotNone(r.error)

    def test_math_works(self):
        r = run_sandboxed("""
let x = 10
let y = 20
show x + y
show x * y
""")
        self.assertIn("30", r.output)
        self.assertIn("200", r.output)
        self.assertTrue(r.ok)

    def test_string_ops_work(self):
        r = run_sandboxed('let s = "hello"\nshow len(s)\nshow s.upper()')
        self.assertIn("5", r.output)
        self.assertIn("HELLO", r.output)
        self.assertTrue(r.ok)

    def test_list_ops_work(self):
        r = run_sandboxed("""
let nums = [1, 2, 3, 4, 5]
show len(nums)
show sum(nums)
""")
        self.assertIn("5", r.output)
        self.assertIn("15", r.output)
        self.assertTrue(r.ok)

    def test_loops_work(self):
        r = run_sandboxed("""
let total = 0
for i in range(5):
    let total = total + i
show total
""")
        self.assertEqual(r.output.strip(), "10")
        self.assertTrue(r.ok)

    def test_tasks_work(self):
        r = run_sandboxed("""
task double(x):
    return x * 2
show double(21)
""")
        self.assertEqual(r.output.strip(), "42")
        self.assertTrue(r.ok)

    def test_conditionals_work(self):
        r = run_sandboxed("""
let x = 10
if x > 5:
    show "big"
else:
    show "small"
""")
        self.assertEqual(r.output.strip(), "big")
        self.assertTrue(r.ok)

    def test_infinite_loop_contained(self):
        """Infinite loop should be stopped by iteration limit."""
        r = run_sandboxed("""
let i = 0
while true:
    let i = i + 1
""", limits={"max_time": 5})
        # Either timed out or caught by iteration guard
        self.assertFalse(r.ok)

    def test_file_blocked_strict(self):
        """File operations should be blocked in strict mode."""
        r = run_sandboxed("""
let content = file_read("nekova.toml")
show content
""", mode="strict")
        # Should fail — either parse error, runtime error, or violation
        self.assertFalse(r.ok)

    def test_strict_blocks_open(self):
        """Python's open() is blocked in strict mode."""
        r = run_sandboxed("""
let f = open("nekova.toml")
""", mode="strict")
        self.assertFalse(r.ok)

    def test_output_size_limit(self):
        """Output exceeding max_output should be truncated."""
        r = run_sandboxed("""
let i = 0
while i < 100:
    show "x" * 100
    let i = i + 1
""", limits={"max_output": 100, "max_time": 10})
        self.assertLessEqual(len(r.output), 200)  # some tolerance

    def test_relaxed_mode_label(self):
        r = run_sandboxed("show 1", mode="relaxed")
        self.assertEqual(r.mode, "relaxed")

    def test_multiple_outputs(self):
        r = run_sandboxed('show 1\nshow 2\nshow 3')
        lines = r.output.strip().split("\n")
        self.assertEqual(lines, ["1", "2", "3"])

    def test_use_math_in_sandbox(self):
        r = run_sandboxed("""
use math
show clamp(15, 0, 10)
show factorial(5)
""")
        self.assertIn("10", r.output)
        self.assertIn("120", r.output)
        self.assertTrue(r.ok)


# ── sandbox statement ─────────────────────────────────────────

class TestSandboxStatement(unittest.TestCase):

    def test_sandbox_strict_parses(self):
        src = 'sandbox strict:\n    show 1 + 1'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import SandboxStatement
        self.assertIsInstance(ast.statements[0], SandboxStatement)
        self.assertEqual(ast.statements[0].mode, "strict")

    def test_sandbox_relaxed_parses(self):
        src = 'sandbox relaxed:\n    show "hello"'
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        from nekova.parser.nodes import SandboxStatement
        self.assertIsInstance(ast.statements[0], SandboxStatement)
        self.assertEqual(ast.statements[0].mode, "relaxed")

    def test_sandbox_strict_runs(self):
        out = run('sandbox strict:\n    show 2 + 2')
        self.assertIn("4", out)

    def test_sandbox_relaxed_runs(self):
        out = run('sandbox relaxed:\n    show "safe"')
        self.assertIn("safe", out)

    def test_sandbox_result_stored(self):
        out = run(
            'sandbox strict:\n'
            '    show 42\n'
            'show sandbox_result["mode"]'
        )
        self.assertIn("strict", out)

    def test_sandbox_captures_output(self):
        out = run(
            'sandbox strict:\n'
            '    show "inside sandbox"\n'
            'show sandbox_result["output"]'
        )
        self.assertIn("inside sandbox", out)

    def test_sandbox_status_printed(self):
        out = run('sandbox strict:\n    show 1')
        # Should print [sandbox:strict] status line
        self.assertIn("sandbox", out.lower())

    def test_sandbox_body_executes(self):
        out = run(
            'sandbox strict:\n'
            '    let x = 10\n'
            '    let y = 20\n'
            '    show x + y'
        )
        self.assertIn("30", out)

    def test_sandbox_run_builtin(self):
        out = run(
            'let result = sandbox_run("show 99")\n'
            'show result["output"]'
        )
        self.assertIn("99", out)

    def test_sandbox_run_error_captured(self):
        out = run(
            'let result = sandbox_run("show undefined_xyz")\n'
            'show result["error"] is not null'
        )
        self.assertIn("true", out)


if __name__ == "__main__":
    unittest.main()