# tests/test_max_loop_iterations.py
# ─────────────────────────────────────────────────────────────────────────────
# Phase 27 — configurable while-loop safety cap (nekova.toml [run]
# max_loop_iterations). Added after self-hosted parsing of large .nk
# files (parser.nk parsing its own ~2400-line source) hit the
# previously-hardcoded 10000-iteration cap in lexer.nk's tokenize()
# loop — a legitimate large finite computation, not a runaway bug.
# Run with:  pytest tests\test_max_loop_iterations.py -v
# ─────────────────────────────────────────────────────────────────────────────

import os
import tempfile
import textwrap
import pytest

from nekova.toml_loader import RunConfig, ConfigError, parse_config


def write_toml(directory: str, content: str) -> str:
    path = os.path.join(directory, "nekova.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
    return path


def write_entry(directory: str, filename: str = "main.nk"):
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        f.write('show "hello"\n')
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 1. RunConfig / TOML parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxLoopIterationsConfig:
    def test_default_is_10000(self):
        r = RunConfig()
        assert r.max_loop_iterations == 10000

    def test_reads_raised_value_from_toml(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = 2000000
            """)
            cfg = parse_config(path)
            assert cfg.run.max_loop_iterations == 2000000

    def test_zero_is_valid_disables_cap(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = 0
            """)
            cfg = parse_config(path)
            assert cfg.run.max_loop_iterations == 0

    def test_missing_key_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[run]\nstrict_types=true\n")
            cfg = parse_config(path)
            assert cfg.run.max_loop_iterations == 10000

    def test_negative_value_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = -5
            """)
            with pytest.raises(ConfigError):
                parse_config(path)

    def test_non_integer_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = "lots"
            """)
            with pytest.raises(ConfigError):
                parse_config(path)

    def test_bool_rejected_even_though_bool_is_a_python_int_subclass(self):
        # Guards against `max_loop_iterations = true` silently becoming 1
        # (bool is technically an int subclass in Python).
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = true
            """)
            with pytest.raises(ConfigError):
                parse_config(path)

    def test_float_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = 1000.5
            """)
            with pytest.raises(ConfigError):
                parse_config(path)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Interpreter integration
# ─────────────────────────────────────────────────────────────────────────────

class TestInterpreterMaxLoopIterations:
    def _run_in(self, tmp_dir: str, source: str):
        """Run NEKOVA source with CWD set to tmp_dir, so load_config()
        picks up whatever nekova.toml (if any) lives there."""
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.interpreter.interpreter import Interpreter

        original = os.getcwd()
        os.chdir(tmp_dir)
        try:
            tokens = Lexer(source).tokenize()
            program = Parser(tokens).parse()
            interp = Interpreter()
            interp.execute(program)
        finally:
            os.chdir(original)

    def test_default_cap_stops_runaway_loop(self):
        with tempfile.TemporaryDirectory() as d:
            with pytest.raises(Exception, match="While loop ran too many times"):
                self._run_in(d, "let x = 1\nwhile true:\n    x = x + 1\n")

    def test_raised_cap_allows_larger_finite_loop(self):
        with tempfile.TemporaryDirectory() as d:
            write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = 20000
            """)
            # A loop that runs 15000 times — would exceed the default
            # 10000 cap but is comfortably under the raised 20000 one,
            # and terminates on its own regardless of the cap.
            self._run_in(d, textwrap.dedent("""\
                let x = 0
                while x < 15000:
                    x = x + 1
                show x
            """))
            # No exception raised == pass.

    def test_zero_disables_cap_entirely(self):
        with tempfile.TemporaryDirectory() as d:
            write_toml(d, """\
                [project]
                name = "x"
                entry = "main.nk"
                [run]
                max_loop_iterations = 0
            """)
            # 25000 iterations — well past the default cap, disabled here.
            self._run_in(d, textwrap.dedent("""\
                let x = 0
                while x < 25000:
                    x = x + 1
                show x
            """))

    def test_get_max_loop_iterations_is_cached_per_instance(self):
        """load_config() is uncached I/O; the interpreter should only
        call it once per instance, not once per while-loop execution."""
        from nekova.interpreter.interpreter import Interpreter

        call_count = {"n": 0}

        interp = Interpreter()

        import nekova.toml_loader as toml_loader
        original_load_config = toml_loader.load_config

        def counting_load_config(*a, **kw):
            call_count["n"] += 1
            return original_load_config(*a, **kw)

        toml_loader.load_config = counting_load_config
        try:
            for _ in range(5):
                interp._get_max_loop_iterations()
        finally:
            toml_loader.load_config = original_load_config

        assert call_count["n"] == 1