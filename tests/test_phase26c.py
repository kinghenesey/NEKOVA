"""
Phase 26c — AI-Native Differentiators III (v1.13.0)

Covers all six features:
  1. Typed AI output validation + re-prompt on failure
  2. Probabilistic testing (test ... repeat N times, expect at least K passes)
  3. Dollar-denominated think budgets + model fallback chains
  4. Deterministic AI-call replay (cassettes)
  5. Capability-scoped agent sandboxing
  6. Streaming as a first-class construct (think_stream)
"""
import unittest
import sys
import io
import os
import json
import shutil
import tempfile
import contextlib
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def run(source, filepath="<test>"):
    """Run NEKOVA source, capture and return stdout."""
    from nekova.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        Interpreter().execute(program, filepath=filepath)
    return buf.getvalue()


class FakeProvider:
    """Minimal controllable provider for tests that need specific,
    deterministic (non-mock-random) responses."""
    name = "fake"
    timeout = 30

    def __init__(self, responses=None, fail_first_n=0,
                 fail_always=False):
        self.model = None
        self.responses = list(responses or [])
        self.calls = []
        self.fail_first_n = fail_first_n
        self.fail_always = fail_always
        self._call_count = 0

    def ask(self, prompt):
        self.calls.append((self.model, prompt))
        self._call_count += 1
        if self.fail_always or self._call_count <= self.fail_first_n:
            raise RuntimeError(f"simulated failure #{self._call_count}")
        if self.responses:
            return self.responses.pop(0)
        return "default response"

    def stream_chunks(self, prompt):
        for word in ["hello", "from", "fake"]:
            yield word


# ── Feature 1: Typed AI output validation + re-prompt ──────────

class TestTypedAIValidation(unittest.TestCase):

    def test_mock_provider_produces_valid_shape_on_first_try(self):
        out = run(
            'shape User:\n'
            '    name str\n'
            '    age int\n\n'
            'let u = think "extract" as User\n'
            'show u\n'
        )
        self.assertIn("__shape__: User", out)
        self.assertIn("name:", out)
        self.assertIn("age:", out)

    def test_reprompt_on_missing_required_field_then_succeeds(self):
        fake = FakeProvider(responses=[
            json.dumps({"name": "Ada"}),               # missing age
            json.dumps({"name": "Ada", "age": 30}),     # valid
        ])
        src = (
            'shape User:\n'
            '    name str\n'
            '    age int\n\n'
            'let u = think "extract" as User\n'
            'show u\n'
        )
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(src)
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("age: 30", out)

    def test_exhausts_reprompts_and_raises_clear_error(self):
        fake = FakeProvider(responses=[
            json.dumps({"name": "Ada"}),
            json.dumps({"name": "Ada"}),
            json.dumps({"name": "Ada"}),
        ])
        src = (
            'shape User:\n'
            '    name str\n'
            '    age int\n\n'
            'let u = think "extract" as User\n'
            'show u\n'
        )
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(src)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 re-prompts
        self.assertIn("still didn't validate", out)
        self.assertIn("age", out)

    def test_optional_field_with_default_not_required(self):
        fake = FakeProvider(responses=[
            json.dumps({"name": "Ada"}),  # 'nickname' omitted, has default
        ])
        src = (
            'shape User:\n'
            '    name str\n'
            '    nickname str = "none"\n\n'
            'let u = think "extract" as User\n'
            'show u\n'
        )
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(src)
        self.assertEqual(len(fake.calls), 1)  # no re-prompt needed
        self.assertIn("__shape__: User", out)

    def test_validate_shape_fields_pure_function_missing(self):
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        errors = interp._validate_shape_fields(
            {"name": "Ada"}, [("name", "str", "x"), ("age", "int", None)]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("age", errors[0])

    def test_validate_shape_fields_pure_function_wrong_type(self):
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        errors = interp._validate_shape_fields(
            {"name": "Ada", "age": "thirty"},
            [("name", "str", "x"), ("age", "int", None)]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("age", errors[0])

    def test_validate_shape_fields_pure_function_clean(self):
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        errors = interp._validate_shape_fields(
            {"name": "Ada", "age": 30},
            [("name", "str", "x"), ("age", "int", None)]
        )
        self.assertEqual(errors, [])


# ── Feature 2: Probabilistic testing ────────────────────────────

class TestProbabilisticTesting(unittest.TestCase):

    def test_all_pass_meets_threshold(self):
        out = run(
            'test "always true" repeat 5 times, expect at least 5 passes:\n'
            '    expect 1 + 1 == 2\n'
        )
        self.assertIn("PASS", out)
        self.assertIn("5/5 runs", out)

    def test_all_fail_below_threshold(self):
        out = run(
            'test "always false" repeat 5 times, expect at least 3 passes:\n'
            '    expect 1 == 2\n'
        )
        self.assertIn("FAIL", out)
        self.assertIn("0/5 runs", out)

    def test_repeat_without_min_passes_defaults_to_all(self):
        out = run(
            'test "strict repeat" repeat 3 times:\n'
            '    expect 1 == 1\n'
        )
        self.assertIn("PASS", out)
        self.assertIn("3/3 runs, needed ≥3", out)

    def test_plain_test_block_unaffected(self):
        out = run(
            'test "plain":\n'
            '    expect 1 + 1 == 2\n'
            '    expect 2 + 2 == 4\n'
        )
        self.assertIn("PASS", out)
        self.assertIn("(2/2)", out)

    def test_mixed_pass_fail_within_threshold(self):
        # Deterministic mixed-outcome test via a counter variable
        # that changes behavior across runs isn't directly
        # expressible without state persisting across runs (each
        # run gets a fresh scope) — so this checks the arithmetic
        # boundary condition instead: exactly at the threshold.
        out = run(
            'test "boundary" repeat 4 times, expect at least 4 passes:\n'
            '    expect 2 * 2 == 4\n'
        )
        self.assertIn("4/4 runs, needed ≥4", out)
        self.assertIn("PASS", out)

    def test_cli_run_probabilistic_test_file(self):
        import subprocess
        path = tempfile.mktemp(suffix=".nk")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                'test "x" repeat 3 times, expect at least 2 passes:\n'
                '    expect 1 == 1\n'
            )
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "main.py"),
                 "run", path],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("3/3 runs", result.stdout)
        finally:
            os.remove(path)


# ── Feature 3a: Dollar budgets ──────────────────────────────────

class TestDollarBudgets(unittest.TestCase):

    def test_money_literal_lexes_and_parses(self):
        from nekova.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("$0.01").tokenize()
        money_tokens = [t for t in tokens if t.type == TokenType.MONEY]
        self.assertEqual(len(money_tokens), 1)
        self.assertAlmostEqual(money_tokens[0].value, 0.01)

    def test_dollar_budget_generous_passes(self):
        out = run('think "hi" as text with budget: $10.00\nshow "ok"\n')
        self.assertIn("ok", out)

    def test_dollar_budget_tiny_raises(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run(
                'think "hello there, how are you today" as text '
                'with budget: $0.0000001\n'
            )
        self.assertIn("exceeded its cost budget", str(ctx.exception))

    def test_token_budget_still_works_unaffected(self):
        out = run('think "hi" as text with budget: 10000\nshow "ok"\n')
        self.assertIn("ok", out)

    def test_token_budget_tiny_raises_token_message_not_cost(self):
        from nekova.interpreter.exceptions import NEKOVARuntimeError
        with self.assertRaises(NEKOVARuntimeError) as ctx:
            run(
                'think "hello there, how are you today, my friend" as text '
                'with budget: 1\n'
            )
        msg = str(ctx.exception)
        self.assertIn("exceeded its token budget", msg)
        self.assertNotIn("exceeded its cost budget", msg)

    def test_dollar_amount_marker_class(self):
        from nekova.interpreter.interpreter import _DollarAmount
        d = _DollarAmount(0.01)
        self.assertIsInstance(d, float)
        self.assertEqual(d, 0.01)


# ── Feature 3b: Model fallback chains ───────────────────────────

class TestModelFallbackChain(unittest.TestCase):

    def test_first_model_succeeds_no_fallback_needed(self):
        fake = FakeProvider(responses=["ok"])
        src = 'think "hi" as text using ["model-a", "model-b"]\n'
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            run(src)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][0], "model-a")

    def test_falls_back_to_second_model_on_failure(self):
        fake = FakeProvider(fail_first_n=3, responses=[])
        # fail_first_n=3 covers model-a's 3 attempts (1 + 2 retries)
        fake.fail_always = False

        call_log = []
        original_ask = fake.ask
        def tracking_ask(prompt):
            call_log.append(fake.model)
            if fake.model == "model-a":
                raise RuntimeError("model-a down")
            return "response from model-b"
        fake.ask = tracking_ask

        src = 'think "hi" as text using ["model-a", "model-b"]\n'
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(src)
        self.assertIn("model-b", call_log)
        self.assertTrue(all(m == "model-a" for m in call_log[:-1]))

    def test_all_models_fail_raises(self):
        fake = FakeProvider(fail_always=True)
        src = 'think "hi" as text using ["model-a", "model-b"]\n'
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(src)
        self.assertIn("think error", out)

    def test_single_model_string_unaffected(self):
        fake = FakeProvider(responses=["ok"])
        src = 'think "hi" as text using "just-one-model"\n'
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            run(src)
        self.assertEqual(fake.calls[0][0], "just-one-model")

    def test_real_providers_respect_model_override(self):
        """The pre-existing gap this phase fixed: real providers
        used to hardcode self.MODEL, ignoring 'using' entirely."""
        import inspect
        from nekova.ai.providers import anthropic, openai, gemini
        for mod in (anthropic, openai, gemini):
            source = inspect.getsource(mod)
            self.assertIn("self.model or self.MODEL", source)


# ── Feature 4: Cassette record/replay ───────────────────────────

class TestCassetteRecordReplay(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cassette_path = os.path.join(self.tmpdir, "cassette.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        from nekova.ai.providers import disable_cassette
        disable_cassette()

    def test_record_then_replay_matches(self):
        from nekova.ai.providers import (
            enable_cassette_recording, enable_cassette_replay,
            disable_cassette,
        )
        fake = FakeProvider(responses=["the real answer"])
        fake.is_available = True
        fake.name = "fake"

        # Patch the PROVIDERS list get_provider() iterates — it
        # holds direct class references captured at import time, so
        # patching the MockProvider module attribute alone wouldn't
        # actually change what the auto-detect loop constructs.
        with patch("nekova.ai.providers.PROVIDERS", [lambda: fake]):
            enable_cassette_recording(self.cassette_path)
            out1 = run('let r = think "a question" as text\nshow r\n')
            disable_cassette()

        self.assertTrue(os.path.isfile(self.cassette_path))
        with open(self.cassette_path) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertIn("the real answer", out1)

        # Replay should NOT touch the real (fake) provider at all —
        # patch it to something that would crash if ever called.
        def _boom(*a, **kw):
            raise AssertionError("real provider called during replay")
        broken = type("Broken", (), {
            "ask": _boom, "model": None, "timeout": 30,
            "is_available": True, "name": "broken",
        })

        with patch("nekova.ai.providers.PROVIDERS", [lambda: broken()]):
            enable_cassette_replay(self.cassette_path)
            out2 = run('let r = think "a question" as text\nshow r\n')
            disable_cassette()

        self.assertIn("the real answer", out2)

    def test_replay_miss_raises_clear_error(self):
        from nekova.ai.providers import enable_cassette_replay, disable_cassette
        with open(self.cassette_path, "w") as f:
            json.dump({}, f)

        fake = FakeProvider()
        fake.is_available = True
        fake.name = "fake"
        with patch("nekova.ai.providers.PROVIDERS", [lambda: fake]):
            enable_cassette_replay(self.cassette_path)
            out = run('think "never recorded" as text\n')
            disable_cassette()

        self.assertIn("No recorded AI response", out)

    def test_cassette_miss_does_not_retry(self):
        """A cassette miss is deterministic — retrying wastes time
        and can't ever succeed, so it should fail on the first
        attempt rather than going through backoff retries."""
        from nekova.ai.providers import enable_cassette_replay, disable_cassette
        with open(self.cassette_path, "w") as f:
            json.dump({}, f)

        fake = FakeProvider()
        fake.is_available = True
        fake.name = "fake"
        with patch("nekova.ai.providers.PROVIDERS", [lambda: fake]):
            enable_cassette_replay(self.cassette_path)
            import time
            start = time.time()
            run('think "never recorded" as text\n')
            elapsed = time.time() - start
            disable_cassette()
        # Backoff delays are 0.3s + 0.6s = 0.9s if retried; a fast
        # fail should be well under that.
        self.assertLess(elapsed, 0.5)

    def test_cassette_disabled_by_default(self):
        fake = FakeProvider(responses=["normal response"])
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run('let r = think "x" as text\nshow r\n')
        self.assertIn("normal response", out)
        self.assertFalse(os.path.isfile(self.cassette_path))

    def test_cli_record_then_replay(self):
        import subprocess
        path = tempfile.mktemp(suffix=".nk")
        with open(path, "w", encoding="utf-8") as f:
            f.write('let r = think "capital of France" as text\nshow r\n')
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            r1 = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "main.py"),
                 "run", path, "--record-ai", self.cassette_path, "--quiet"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env,
            )
            self.assertEqual(r1.returncode, 0)
            self.assertTrue(os.path.isfile(self.cassette_path))

            r2 = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "main.py"),
                 "run", path, "--replay-ai", self.cassette_path, "--quiet"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env,
            )
            self.assertEqual(r2.returncode, 0)
            # Both runs' AI-generated line should match exactly —
            # timing footer lines differ run to run, so compare only
            # the actual AI response line rather than full stdout.
            def _ai_line(stdout):
                lines = [l for l in stdout.splitlines()
                        if l and "Done in" not in l
                        and "Running" not in l]
                return lines
            self.assertEqual(_ai_line(r1.stdout), _ai_line(r2.stdout))
        finally:
            os.remove(path)


# ── Feature 5: Capability-scoped sandbox ────────────────────────

class TestCapabilityScopedSandbox(unittest.TestCase):

    def test_allowed_call_succeeds(self):
        out = run(
            'task search_web(q): return "results: " + q\n'
            'sandbox strict allow: [search_web]:\n'
            '    let r = search_web("x")\n'
            '    show r\n'
        )
        self.assertIn("results: x", out)

    def test_disallowed_call_blocked(self):
        out = run(
            'task search_web(q): return "ok"\n'
            'task delete_all(): return "gone"\n'
            'sandbox strict allow: [search_web]:\n'
            '    let d = delete_all()\n'
            '    show d\n'
        )
        self.assertIn("Blocked", out)
        self.assertIn("delete_all", out)
        self.assertNotIn("gone", out)

    def test_builtins_unrestricted_inside_capability_sandbox(self):
        out = run(
            'task search_web(q): return q\n'
            'sandbox strict allow: [search_web]:\n'
            '    let n = len([1, 2, 3])\n'
            '    show n\n'
        )
        self.assertIn("3", out)
        self.assertIn("safe", out)

    def test_no_allow_list_means_unrestricted_task_calls(self):
        out = run(
            'task greet(): return "hi"\n'
            'sandbox relaxed:\n'
            '    let g = greet()\n'
            '    show g\n'
        )
        self.assertIn("hi", out)

    def test_nested_sandboxes_intersect_allow_lists(self):
        out = run(
            'task a(): return "a"\n'
            'task b(): return "b"\n'
            'sandbox strict allow: [a, b]:\n'
            '    sandbox strict allow: [a]:\n'
            '        let x = a()\n'
            '        show x\n'
            '        let y = b()\n'
            '        show y\n'
        )
        self.assertIn("a", out)
        self.assertIn("Blocked", out)

    def test_empty_allow_list_blocks_everything(self):
        out = run(
            'task greet(): return "hi"\n'
            'sandbox strict allow: []:\n'
            '    let g = greet()\n'
            '    show g\n'
        )
        self.assertIn("Blocked", out)


# ── Feature 6: Streaming ─────────────────────────────────────────

class TestStreaming(unittest.TestCase):

    def test_think_stream_yields_multiple_chunks(self):
        fake = FakeProvider()
        with patch("nekova.ai.providers.get_provider", return_value=fake):
            out = run(
                'for chunk in think_stream("hi"):\n'
                '    show chunk\n'
            )
        lines = [l for l in out.strip().splitlines() if l]
        self.assertGreater(len(lines), 1)

    def test_streaming_is_actually_lazy(self):
        pulled = []
        def gen(prompt):
            for w in ["a", "b", "c", "d", "e"]:
                pulled.append(w)
                yield w
        fake = FakeProvider()
        fake.stream_chunks = gen

        with patch("nekova.ai.providers.get_provider", return_value=fake):
            run(
                'let count = 0\n'
                'for chunk in think_stream("x"):\n'
                '    count = count + 1\n'
                '    if count == 2:\n'
                '        break\n'
            )
        self.assertEqual(pulled, ["a", "b"])

    def test_default_stream_chunks_splits_on_words(self):
        from nekova.ai.providers.base import BaseProvider

        class Dummy(BaseProvider):
            def ask(self, prompt): return "one two three"
            def summarize(self, text): return ""
            def generate(self, instruction): return ""
            def classify(self, text, labels): return ""
            @property
            def name(self): return "dummy"
            @property
            def is_available(self): return True

        d = Dummy()
        chunks = list(d.stream_chunks("x"))
        self.assertEqual("".join(chunks), "one two three")
        self.assertEqual(len(chunks), 3)

    def test_regular_generator_tasks_unaffected(self):
        """The existing yield-based NEKOVA generator behavior must
        stay exactly as it was — this phase's laziness change is
        scoped to think_stream only, not broadened to __next__ in
        general (that was tried and reverted)."""
        out = run(
            'task gen():\n'
            '    yield 1\n'
            '    yield 2\n'
            'let count = 0\n'
            'for _ in gen():\n'
            '    let count = count + 1\n'
            'show count\n'
        )
        self.assertIn("2", out)

    def test_stream_chunks_marker_type(self):
        from nekova.interpreter.interpreter import _NEKOVAStreamChunks
        def gen():
            yield "x"
        wrapped = _NEKOVAStreamChunks(gen())
        self.assertEqual(next(wrapped), "x")


if __name__ == "__main__":
    unittest.main()