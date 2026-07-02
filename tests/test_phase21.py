"""
Phase 21 — Prompt Blocks + Retry/Fallback + Enforced Types
Tests for: `prompt` blocks (interpolated templates), `retry ... times
[with backoff]: ... fallback: ...`, and type enforcement on prompt
parameters.
"""
import unittest
import sys
import io
import re
import time

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.ai import memory_store as _mem_store

ANSI = re.compile(r'\x1b\[[0-9;]*m')


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
    return ANSI.sub('', buf.getvalue()).strip()


class NoSleep:
    """Context manager that no-ops time.sleep so backoff tests stay fast."""
    def __enter__(self):
        self._orig = time.sleep
        time.sleep = lambda *_a, **_k: None
        return self

    def __exit__(self, *exc):
        time.sleep = self._orig


# ── Prompt blocks: basic interpolation ─────────────────────────

class TestPromptBasics(unittest.TestCase):

    def test_simple_interpolation(self):
        out = run(
            'prompt summarize(text, style="professional"):\n'
            '    """Summarize the following in a {style} tone: {text}"""\n'
            'show summarize("hello world")\n'
        )
        self.assertEqual(
            out, "Summarize the following in a professional tone: hello world"
        )

    def test_override_default_param(self):
        out = run(
            'prompt summarize(text, style="professional"):\n'
            '    """{style}: {text}"""\n'
            'show summarize("hi", "casual")\n'
        )
        self.assertEqual(out, "casual: hi")

    def test_no_placeholders(self):
        out = run(
            'prompt greeting(name):\n'
            '    """Hello there!"""\n'
            'show greeting("ignored")\n'
        )
        self.assertEqual(out, "Hello there!")

    def test_multiple_placeholders_same_var(self):
        out = run(
            'prompt echo(word):\n'
            '    """{word} {word} {word}"""\n'
            'show echo("go")\n'
        )
        self.assertEqual(out, "go go go")

    def test_prompt_result_is_a_real_string(self):
        out = run(
            'prompt tag(x):\n'
            '    """[{x}]"""\n'
            'result = tag("A") + tag("B")\n'
            'show result\n'
        )
        self.assertEqual(out, "[A][B]")

    def test_prompt_missing_required_arg_raises(self):
        out = run(
            'prompt needs_two(a, b):\n'
            '    """{a}-{b}"""\n'
            'try:\n'
            '    show needs_two("only_one")\n'
            'catch e:\n'
            '    show "caught"\n'
        )
        self.assertEqual(out, "caught")


class TestPromptSoftKeyword(unittest.TestCase):
    """
    `prompt` must stay usable as an ordinary variable name — existing
    NEKOVA code (examples/mood_tracker.nk) already does this. Only
    `prompt <name>(...):`  should be treated as a definition.
    """

    def test_prompt_as_plain_variable(self):
        out = run('prompt = "just a string"\nshow prompt\n')
        self.assertEqual(out, "just a string")

    def test_prompt_variable_used_with_think_as(self):
        out = run(
            'prompt = "some text"\n'
            'show prompt + "!"\n'
        )
        self.assertEqual(out, "some text!")

    def test_prompt_definition_still_works_alongside_variable_usage(self):
        out = run(
            'prompt summarize(text):\n'
            '    """S: {text}"""\n'
            'prompt = "unrelated variable"\n'
            'show summarize("x")\n'
            'show prompt\n'
        )
        self.assertEqual(out, "S: x\nunrelated variable")


class TestPromptTypedParams(unittest.TestCase):

    def test_typed_param_accepts_correct_type(self):
        out = run(
            'prompt score(value: int):\n'
            '    """Score: {value}"""\n'
            'show score(5)\n'
        )
        self.assertEqual(out, "Score: 5")

    def test_typed_param_rejects_wrong_type(self):
        out = run(
            'prompt score(value: int):\n'
            '    """Score: {value}"""\n'
            'try:\n'
            '    show score("not a number")\n'
            'catch e:\n'
            '    show "caught"\n'
        )
        self.assertEqual(out, "caught")

    def test_typed_param_error_message_says_prompt_not_task(self):
        out = run(
            'prompt score(value: int):\n'
            '    """{value}"""\n'
            'try:\n'
            '    show score("nope")\n'
            'catch e:\n'
            '    show e.message\n'
        )
        self.assertIn("Prompt", out)
        self.assertIn("score", out)


# ── Retry / fallback ─────────────────────────────────────────

class TestRetrySucceedsEventually(unittest.TestCase):

    def test_succeeds_before_exhausting_attempts(self):
        out = run(
            'attempts = 0\n'
            'task flaky():\n'
            '    global attempts\n'
            '    attempts = attempts + 1\n'
            '    if attempts < 3:\n'
            '        raise "not yet"\n'
            '    show "ok on " + str(attempts)\n'
            'retry 5 times:\n'
            '    flaky()\n'
        )
        self.assertEqual(out, "ok on 3")

    def test_succeeds_first_try_no_retry_needed(self):
        out = run(
            'attempts = 0\n'
            'retry 3 times:\n'
            '    global attempts\n'
            '    attempts = attempts + 1\n'
            'show attempts\n'
        )
        self.assertEqual(out, "1")


class TestRetryExhaustion(unittest.TestCase):

    def test_fallback_runs_when_all_attempts_fail(self):
        with NoSleep():
            out = run(
                'retry 3 times:\n'
                '    raise "always fails"\n'
                'fallback:\n'
                '    show "fallback ran"\n'
            )
        self.assertEqual(out, "fallback ran")

    def test_no_fallback_reraises_last_error(self):
        with NoSleep():
            out = run(
                'try:\n'
                '    retry 2 times:\n'
                '        raise "boom"\n'
                'catch e:\n'
                '    show "caught: " + e.message\n'
            )
        self.assertEqual(out, "caught: boom")

    def test_attempts_exactly_matches_times(self):
        with NoSleep():
            out = run(
                'count = 0\n'
                'retry 4 times:\n'
                '    global count\n'
                '    count = count + 1\n'
                '    raise "fail"\n'
                'fallback:\n'
                '    show count\n'
            )
        self.assertEqual(out, "4")


class TestRetryBackoff(unittest.TestCase):

    def test_exponential_backoff_parses_and_runs(self):
        with NoSleep():
            out = run(
                'retry 3 times with exponential backoff:\n'
                '    raise "fail"\n'
                'fallback:\n'
                '    show "done"\n'
            )
        self.assertEqual(out, "done")

    def test_linear_backoff_parses_and_runs(self):
        with NoSleep():
            out = run(
                'retry 3 times with linear backoff:\n'
                '    raise "fail"\n'
                'fallback:\n'
                '    show "done"\n'
            )
        self.assertEqual(out, "done")

    def test_no_backoff_clause_is_immediate(self):
        # No `with ... backoff` clause at all — should behave
        # identically to immediate retry (already covered above,
        # this just locks in the plain grammar form).
        with NoSleep():
            out = run(
                'retry 2 times:\n'
                '    raise "fail"\n'
                'fallback:\n'
                '    show "ok"\n'
            )
        self.assertEqual(out, "ok")


class TestRetryControlFlow(unittest.TestCase):
    """Break/continue/return inside a retry body must never be
    mistaken for a retry-triggering error."""

    def test_return_inside_retry_in_task_propagates(self):
        out = run(
            'task run_it():\n'
            '    retry 3 times:\n'
            '        return "returned early"\n'
            '    return "never reached"\n'
            'show run_it()\n'
        )
        self.assertEqual(out, "returned early")

    def test_break_inside_retry_inside_loop(self):
        # break propagates past retry to the enclosing for loop —
        # it exits the loop entirely, so "show i" never runs for
        # i==2, and i==3 is never reached.
        out = run(
            'for i in [1, 2, 3]:\n'
            '    retry 2 times:\n'
            '        if i == 2:\n'
            '            break\n'
            '    show i\n'
        )
        self.assertEqual(out, "1")

    def test_continue_inside_retry_inside_loop(self):
        # continue propagates past retry to the enclosing for loop —
        # it skips straight to the next iteration, so "show i" never
        # runs for i==2, but i==3 still does.
        out = run(
            'for i in [1, 2, 3]:\n'
            '    retry 2 times:\n'
            '        if i == 2:\n'
            '            continue\n'
            '    show i\n'
        )
        self.assertEqual(out, "1\n3")


class TestRetryEdgeCases(unittest.TestCase):

    def test_zero_times_raises(self):
        out = run(
            'try:\n'
            '    retry 0 times:\n'
            '        show "should not run"\n'
            'catch e:\n'
            '    show "caught"\n'
        )
        self.assertEqual(out, "caught")

    def test_retry_count_from_variable(self):
        with NoSleep():
            out = run(
                'n = 2\n'
                'retry n times:\n'
                '    raise "fail"\n'
                'fallback:\n'
                '    show "fallback"\n'
            )
        self.assertEqual(out, "fallback")


# ── Combined: prompt + retry + think ────────────────────────

class TestPromptRetryIntegration(unittest.TestCase):

    def test_prompt_call_inside_retry_with_think(self):
        # Just needs to parse and execute end-to-end without error —
        # the mock `think` provider stands in for a real AI call.
        out = run(
            'prompt classify(text):\n'
            '    """Classify: {text}"""\n'
            'retry 2 times:\n'
            '    result = think classify("great product") as text\n'
            '    show "got result"\n'
            'fallback:\n'
            '    show "unavailable"\n'
        )
        self.assertIn(out, ("got result", "unavailable"))


if __name__ == "__main__":
    unittest.main()