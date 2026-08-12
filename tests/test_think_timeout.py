# =============================================================
# NEKOVA — Think Timeout Tests
# =============================================================

import sys, os, time, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# === BaseProvider._with_timeout ===

class TestBaseProviderTimeout:
    def test_timeout_attr_default(self):
        from nekova.ai.providers.base import BaseProvider, DEFAULT_THINK_TIMEOUT
        class _P(BaseProvider):
            name = 'test'
            is_available = True
            def ask(self, p): return ''
            def summarize(self, t): return ''
            def generate(self, i): return ''
            def classify(self, t, l): return ''
        p = _P()
        assert p.timeout == DEFAULT_THINK_TIMEOUT
        assert p.timeout == 30

    def test_default_timeout_constant_is_30(self):
        from nekova.ai.providers.base import DEFAULT_THINK_TIMEOUT
        assert DEFAULT_THINK_TIMEOUT == 30

    def test_with_timeout_passes_through_on_success(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        result = p._with_timeout(lambda: 'ok')
        assert result == 'ok'

    def test_with_timeout_none_disables_timeout(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = None
        result = p._with_timeout(lambda: 'no_timeout')
        assert result == 'no_timeout'

    def test_with_timeout_raises_on_slow_call(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 0.1  # 100ms
        def slow():
            time.sleep(2)
            return 'never'
        with pytest.raises(RuntimeError) as exc:
            p._with_timeout(slow)
        assert 'timed out' in str(exc.value).lower()

    def test_timeout_error_message_mentions_seconds(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 0.1
        def slow():
            time.sleep(2)
        with pytest.raises(RuntimeError) as exc:
            p._with_timeout(slow)
        assert '0.1' in str(exc.value)

    def test_timeout_can_be_overridden_per_call(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 30  # high default
        result = p._with_timeout(lambda: 'fast', timeout=10)
        assert result == 'fast'

    def test_timeout_can_be_set_to_none(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = None
        result = p._with_timeout(lambda: 'no_limit')
        assert result == 'no_limit'


# === Mock provider uses _with_timeout ===

class TestMockProviderTimeout:
    def test_mock_has_raw_complete(self):
        from nekova.ai.providers.mock import MockProvider
        assert hasattr(MockProvider(), '_raw_complete')

    def test_mock_ask_returns_string(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        assert isinstance(p.ask('hello'), str)

    def test_mock_ask_times_out(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 0.1
        # Patch _raw_complete to be slow
        def slow(prompt):
            time.sleep(2)
            return 'never'
        p._raw_complete = slow
        with pytest.raises(RuntimeError) as exc:
            p.ask('test')
        assert 'timed out' in str(exc.value).lower()

    def test_mock_normal_ask_fast_enough(self):
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 5
        start = time.time()
        r = p.ask('hello')
        assert time.time() - start < 5
        assert isinstance(r, str)


# === think_engine.ask_structured timeout ===

class TestAskStructuredTimeout:
    def test_ask_structured_accepts_timeout_param(self):
        import inspect
        from nekova.ai.think_engine import ask_structured
        sig = inspect.signature(ask_structured)
        assert 'timeout' in sig.parameters

    def test_ask_structured_sets_provider_timeout(self):
        from nekova.ai.think_engine import ask_structured
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 30
        ask_structured(p, 'hello', 'text', timeout=15)
        assert p.timeout == 15

    def test_ask_structured_timeout_none_leaves_provider(self):
        from nekova.ai.think_engine import ask_structured
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        p.timeout = 30
        ask_structured(p, 'hello', 'text', timeout=None)
        assert p.timeout == 30  # unchanged

    def test_ask_structured_raises_on_slow_provider(self):
        from nekova.ai.think_engine import ask_structured
        from nekova.ai.providers.mock import MockProvider
        p = MockProvider()
        def slow(prompt):
            time.sleep(2)
            return 'never'
        p._raw_complete = slow
        with pytest.raises((RuntimeError, Exception)):
            ask_structured(p, 'test', 'text', timeout=0.1)


# === Interpreter _get_think_timeout ===

class TestInterpreterTimeout:
    def test_interpreter_has_get_think_timeout(self):
        from nekova.interpreter.interpreter import Interpreter
        assert hasattr(Interpreter(), '_get_think_timeout')

    def test_get_think_timeout_returns_float_or_none(self):
        from nekova.interpreter.interpreter import Interpreter
        t = Interpreter()._get_think_timeout()
        assert t is None or isinstance(t, float)

    def test_get_think_timeout_default_is_30(self):
        from nekova.interpreter.interpreter import Interpreter
        t = Interpreter()._get_think_timeout()
        # Without toml, should default to 30.0
        assert t == 30.0 or t is None


# === toml_loader think_timeout ===

class TestTomlTimeout:
    def test_toml_loader_has_think_timeout_field(self):
        from nekova.toml_loader import AIConfig
        import inspect
        src = inspect.getsource(AIConfig)
        assert 'think_timeout' in src

    def test_toml_think_timeout_default_is_30(self):
        from nekova.toml_loader import AIConfig
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(AIConfig)}
        assert 'think_timeout' in fields
        assert fields['think_timeout'].default == 30.0

    def test_timeout_zero_disables(self):
        # When think_timeout = 0 in toml, _get_think_timeout returns None
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        # Patch load_config to return timeout=0
        import unittest.mock as mock
        cfg_mock = mock.MagicMock()
        cfg_mock.ai.think_timeout = 0
        with mock.patch('nekova.toml_loader.load_config', return_value=cfg_mock):
            t = interp._get_think_timeout()
        assert t is None

    def test_timeout_positive_returns_float(self):
        from nekova.interpreter.interpreter import Interpreter
        import unittest.mock as mock
        interp = Interpreter()
        cfg_mock = mock.MagicMock()
        cfg_mock.ai.think_timeout = 60
        with mock.patch('nekova.toml_loader.load_config', return_value=cfg_mock):
            t = interp._get_think_timeout()
        assert t == 60.0

    def test_timeout_toml_none_config_returns_default(self):
        from nekova.interpreter.interpreter import Interpreter
        import unittest.mock as mock
        interp = Interpreter()
        with mock.patch('nekova.toml_loader.load_config', return_value=None):
            t = interp._get_think_timeout()
        assert t == 30.0

    def test_real_toml_ai_think_timeout_is_actually_applied(self):
        # End-to-end with a real parsed config (no mocking) — this is
        # the case that was silently broken: _get_think_timeout() read
        # cfg.think_timeout, but the field only ever existed at
        # cfg.ai.think_timeout, so [ai] think_timeout in nekova.toml
        # was never actually applied; it always fell through to the
        # hardcoded 30.0 default. A MagicMock-based test can't catch
        # this (it auto-creates whatever attribute you touch), so this
        # uses a real written-to-disk nekova.toml instead.
        import os, tempfile
        from nekova.interpreter.interpreter import Interpreter

        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "main.nk"), "w") as f:
                f.write('show "hi"\n')
            with open(os.path.join(d, "nekova.toml"), "w") as f:
                f.write(
                    "[project]\nname = 'x'\nentry = 'main.nk'\n"
                    "[ai]\nthink_timeout = 77\n"
                )
            original = os.getcwd()
            os.chdir(d)
            try:
                t = Interpreter()._get_think_timeout()
            finally:
                os.chdir(original)
            assert t == 77.0