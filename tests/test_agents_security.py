"""
Agent system security regression tests.

The "calculate" tool in agents_module.py used to be a raw
`eval(expr)` call. agent_runner.py's _run_with_tools() hands every
registered tool the agent's full plan text automatically — no LLM
decision or filtering in between — so a "calculate" tool on an agent
run with attacker-influenced input was a direct code-execution path.

Confirmed exploitable in isolation: eval() on a crafted expression
string does execute arbitrary Python (see
test_raw_eval_would_have_been_exploitable, which exercises Python's
built-in eval() directly, not NEKOVA code, purely to document why the
fix below was necessary).

Fixed by replacing eval() with _safe_calculate(), an AST-walking
evaluator that only ever recurses into numeric constants and a fixed
whitelist of arithmetic operators (+ - * / // % **, unary +/-).
Anything else — Name, Call, Attribute, Subscript, Import, lambdas,
comprehensions, literally anything that isn't a number or one of
those operators — is rejected with ValueError before evaluation ever
touches it.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from nekova.ai.agents_module import (
    _safe_calculate, _agent_create, _agent_tool, _agent_run, _agents,
)


class TestSafeCalculateLegitimateMath(unittest.TestCase):
    """The fix must not break any real arithmetic use of the tool."""

    def test_addition(self):
        self.assertEqual(_safe_calculate("2 + 3"), "5")

    def test_operator_precedence(self):
        self.assertEqual(_safe_calculate("2 + 3 * 4"), "14")

    def test_parentheses(self):
        self.assertEqual(_safe_calculate("(2 + 3) * 4"), "20")

    def test_caret_as_power(self):
        # The tool has always translated ^ to ** for calculator-style input.
        self.assertEqual(_safe_calculate("2^10"), "1024")

    def test_float_division(self):
        self.assertEqual(_safe_calculate("10 / 4"), "2.5")

    def test_floor_division(self):
        self.assertEqual(_safe_calculate("10 // 3"), "3")

    def test_modulo(self):
        self.assertEqual(_safe_calculate("10 % 3"), "1")

    def test_unary_minus(self):
        self.assertEqual(_safe_calculate("-5 + 3"), "-2")

    def test_negative_float(self):
        self.assertEqual(_safe_calculate("-2.5 * 2"), "-5.0")

    def test_division_by_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            _safe_calculate("1 / 0")


class TestSafeCalculateBlocksInjection(unittest.TestCase):
    """
    Every one of these previously ran as real Python via eval(). All
    of them must now raise ValueError with no side effect whatsoever.
    """

    EXPLOIT_EXPRESSIONS = [
        "__import__('os').system('touch /tmp/nekova_pwn_test')",
        "open('/etc/passwd').read()",
        "().__class__.__bases__[0].__subclasses__()",
        "exec(\"import os\")",
        "[x for x in range(10)]",
        "lambda: 1",
        "2; import os",
        "globals()",
        "__builtins__",
        "(1).__class__",
    ]

    def test_all_known_exploits_raise_value_error(self):
        marker = "/tmp/nekova_pwn_test"
        if os.path.exists(marker):
            os.remove(marker)
        try:
            for expr in self.EXPLOIT_EXPRESSIONS:
                with self.assertRaises(
                    ValueError, msg=f"did not block: {expr!r}"
                ):
                    _safe_calculate(expr)
            self.assertFalse(
                os.path.exists(marker),
                "exploit executed — a side effect leaked through",
            )
        finally:
            if os.path.exists(marker):
                os.remove(marker)

    def test_huge_exponent_is_rejected_not_computed(self):
        # 9**9**9**9 is "just arithmetic" but would hang / exhaust
        # memory if actually computed. Must be rejected, not attempted.
        with self.assertRaises(ValueError):
            _safe_calculate("9**9**9**9")

    def test_boolean_literal_rejected(self):
        # isinstance(True, int) is True in Python — explicitly guarded
        # against so 'calculate' can't be used to smuggle bools through
        # as numbers.
        with self.assertRaises(ValueError):
            _safe_calculate("True")

    def test_syntactically_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            _safe_calculate("2 +* 3")


class TestAgentRunEndToEndDoesNotExecute(unittest.TestCase):
    """
    Full path through the real, documented entry point: agent_create
    -> agent_tool -> agent_run. This is the actual reachable surface
    from NEKOVA source code (`use agents`); Agent.use_tool() exists in
    agent.py but is not wired into agents_module.load(), so it is not
    reachable from a NEKOVA program today — still worth guarding
    against via the eval() removal itself, since that reachability is
    an accident of the current wiring, not a designed boundary.
    """

    def setUp(self):
        _agents.clear()

    def test_calculate_tool_via_agent_run_does_not_execute(self):
        marker = "/tmp/nekova_pwn_test_e2e"
        if os.path.exists(marker):
            os.remove(marker)

        _agent_create("sec_test_bot", "test agent")
        _agent_tool("sec_test_bot", "calculate", "does math")
        _agent_run(
            "sec_test_bot",
            f"__import__('os').system('touch {marker}')",
        )

        self.assertFalse(
            os.path.exists(marker),
            "agent_run() reached real code execution",
        )
        if os.path.exists(marker):
            os.remove(marker)


if __name__ == "__main__":
    unittest.main()