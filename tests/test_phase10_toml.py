# tests/test_phase10_toml.py
# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — nekova.toml config loader tests
# Run with:  pytest tests\test_phase10_toml.py -v
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import pytest
import tempfile
import textwrap
from unittest.mock import patch

from nekova.toml_loader import (
    NekovaConfig,
    ProjectConfig,
    AIConfig,
    DependenciesConfig,
    RunConfig,
    ConfigError,
    load_config,
    parse_config,
    _find_config,
    _build_config,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def write_toml(directory: str, content: str) -> str:
    """Write nekova.toml into *directory*, return its path."""
    path = os.path.join(directory, "nekova.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
    return path


def write_entry(directory: str, filename: str = "main.nk"):
    """Create a dummy entry .nk file so path validation passes."""
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        f.write('show "hello"\n')
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 1. DataClass defaults
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaults:
    def test_project_defaults(self):
        p = ProjectConfig()
        assert p.name    == "unnamed"
        assert p.version == "0.1.0"
        assert p.entry   == "main.nk"
        assert p.author  == ""

    def test_ai_defaults(self):
        a = AIConfig()
        assert a.model   == "claude"
        assert a.api_key == ""

    def test_dependencies_defaults(self):
        d = DependenciesConfig()
        assert d.packages == []

    def test_run_defaults(self):
        r = RunConfig()
        assert r.strict_types is False
        assert r.show_imports is False
        assert r.debug        is False

    def test_nekova_config_defaults(self):
        c = NekovaConfig()
        assert isinstance(c.project,      ProjectConfig)
        assert isinstance(c.ai,           AIConfig)
        assert isinstance(c.dependencies, DependenciesConfig)
        assert isinstance(c.run,          RunConfig)
        assert c.root_dir == ""


# ─────────────────────────────────────────────────────────────────────────────
# 2. entry_path property
# ─────────────────────────────────────────────────────────────────────────────

class TestEntryPath:
    def test_entry_path_joins_root(self):
        c = NekovaConfig()
        c.root_dir = "/some/project"
        c.project.entry = "main.nk"
        assert c.entry_path == os.path.join("/some/project", "main.nk")

    def test_entry_path_custom_file(self):
        c = NekovaConfig()
        c.root_dir = "/proj"
        c.project.entry = "app.nk"
        assert c.entry_path.endswith("app.nk")


# ─────────────────────────────────────────────────────────────────────────────
# 3. _find_config — directory traversal
# ─────────────────────────────────────────────────────────────────────────────

class TestFindConfig:
    def test_finds_in_same_directory(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_toml(d, "[project]\nname = 'test'")
            assert _find_config(d) == path

    def test_finds_in_parent_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            child = os.path.join(parent, "subdir")
            os.makedirs(child)
            path = write_toml(parent, "[project]\nname = 'test'")
            assert _find_config(child) == path

    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            # No nekova.toml anywhere
            result = _find_config(d)
            # It may find one further up in CI — just check type
            assert result is None or result.endswith("nekova.toml")

    def test_finds_nested_two_levels_up(self):
        with tempfile.TemporaryDirectory() as root:
            deep = os.path.join(root, "a", "b")
            os.makedirs(deep)
            path = write_toml(root, "[project]\nname = 'root'")
            assert _find_config(deep) == path


# ─────────────────────────────────────────────────────────────────────────────
# 4. parse_config — valid TOML
# ─────────────────────────────────────────────────────────────────────────────

class TestParseConfigValid:
    def test_minimal_config(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """
                [project]
                name = "hello"
                entry = "main.nk"
            """)
            cfg = parse_config(path)
            assert cfg.project.name == "hello"

    def test_full_config(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d, "app.nk")
            path = write_toml(d, """
                [project]
                name = "my-app"
                version = "1.0.0"
                author = "Emmanuel"
                description = "Test app"
                entry = "app.nk"

                [ai]
                model = "mock"
                api_key = "test-key"

                [dependencies]
                packages = ["nekova-utils"]

                [run]
                strict_types = true
                show_imports = true
                debug = true
            """)
            cfg = parse_config(path)
            assert cfg.project.name        == "my-app"
            assert cfg.project.version     == "1.0.0"
            assert cfg.project.author      == "Emmanuel"
            assert cfg.project.description == "Test app"
            assert cfg.project.entry       == "app.nk"
            assert cfg.ai.model            == "mock"
            assert cfg.ai.api_key          == "test-key"
            assert cfg.dependencies.packages == ["nekova-utils"]
            assert cfg.run.strict_types    is True
            assert cfg.run.show_imports    is True
            assert cfg.run.debug           is True

    def test_empty_toml_uses_all_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_toml(d, "")
            with pytest.warns(UserWarning):
                cfg = parse_config(path)
            assert cfg.project.name  == "unnamed"
            assert cfg.ai.model      == "claude"
            assert cfg.run.debug     is False

    def test_root_dir_is_set(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname = 'x'\nentry = 'main.nk'")
            cfg = parse_config(path)
            assert cfg.root_dir == os.path.abspath(d)

    def test_bom_stripped(self):
        """Files saved on Windows with BOM should parse correctly."""
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            toml_path = os.path.join(d, "nekova.toml")
            content = b'\xef\xbb\xbf[project]\nname = "bom-test"\nentry = "main.nk"\n'
            with open(toml_path, "wb") as f:
                f.write(content)
            cfg = parse_config(toml_path)
            assert cfg.project.name == "bom-test"

    def test_missing_section_gets_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname = 'no-ai'\nentry = 'main.nk'\n")
            cfg = parse_config(path)
            assert cfg.ai.model == "claude"     # default
            assert cfg.run.debug is False       # default


# ─────────────────────────────────────────────────────────────────────────────
# 5. parse_config — invalid TOML / validation errors
# ─────────────────────────────────────────────────────────────────────────────

class TestParseConfigInvalid:
    def test_bad_toml_syntax_raises_config_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_toml(d, "[[[[not valid toml")
            with pytest.raises(ConfigError, match="syntax error"):
                parse_config(path)

    def test_invalid_model_raises_config_error(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """
                [project]
                name = "x"
                entry = "main.nk"
                [ai]
                model = "grok"
            """)
            with pytest.raises(ConfigError, match="not recognised"):
                parse_config(path)

    def test_packages_not_list_raises(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, """
                [project]
                name = "x"
                entry = "main.nk"
                [dependencies]
                packages = "not-a-list"
            """)
            with pytest.raises(ConfigError, match="list"):
                parse_config(path)

    def test_name_wrong_type_raises(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname = 123\n")
            with pytest.raises(ConfigError, match="string"):
                parse_config(path)

    def test_debug_wrong_type_raises(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[run]\ndebug = 'yes'\n")
            with pytest.raises(ConfigError, match="true or false"):
                parse_config(path)


# ─────────────────────────────────────────────────────────────────────────────
# 6. AI model options
# ─────────────────────────────────────────────────────────────────────────────

class TestAIModelOptions:
    @pytest.mark.parametrize("model", ["claude", "gemini", "openai", "mock"])
    def test_all_valid_models_accepted(self, model):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, f"""
                [project]
                name = "x"
                entry = "main.nk"
                [ai]
                model = "{model}"
            """)
            cfg = parse_config(path)
            assert cfg.ai.model == model

    def test_api_key_falls_back_to_env(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[ai]\nmodel='claude'\n")
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
                cfg = parse_config(path)
            assert cfg.ai.api_key == "env-key"

    def test_toml_api_key_takes_priority_over_env(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[ai]\nmodel='claude'\napi_key='toml-key'\n")
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
                cfg = parse_config(path)
            assert cfg.ai.api_key == "toml-key"

    def test_empty_api_key_with_no_env(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n")
            env = {k: v for k, v in os.environ.items()
                   if k not in ("ANTHROPIC_API_KEY","GEMINI_API_KEY","OPENAI_API_KEY")}
            with patch.dict(os.environ, env, clear=True):
                cfg = parse_config(path)
            assert cfg.ai.api_key == ""


# ─────────────────────────────────────────────────────────────────────────────
# 7. load_config — directory search
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_returns_none_when_no_toml(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("os.getcwd", return_value=d):
                # Override _find_config to only search d (avoid finding repo toml)
                with patch("nekova.toml_loader._find_config", return_value=None):
                    result = load_config(d)
            assert result is None

    def test_loads_from_explicit_directory(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            write_toml(d, "[project]\nname = 'explicit'\nentry = 'main.nk'\n")
            cfg = load_config(d)
            assert cfg is not None
            assert cfg.project.name == "explicit"

    def test_loads_from_parent_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            child = os.path.join(parent, "src")
            os.makedirs(child)
            write_entry(parent)
            write_toml(parent, "[project]\nname = 'parent-proj'\nentry = 'main.nk'\n")
            cfg = load_config(child)
            assert cfg.project.name == "parent-proj"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Dependencies
# ─────────────────────────────────────────────────────────────────────────────

class TestDependencies:
    def test_empty_packages(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[dependencies]\npackages=[]\n")
            cfg = parse_config(path)
            assert cfg.dependencies.packages == []

    def test_multiple_packages(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, '[project]\nname="x"\nentry="main.nk"\n[dependencies]\npackages=["nekova-utils","nekova-http"]\n')
            cfg = parse_config(path)
            assert "nekova-utils" in cfg.dependencies.packages
            assert "nekova-http"  in cfg.dependencies.packages
            assert len(cfg.dependencies.packages) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 9. Run flags
# ─────────────────────────────────────────────────────────────────────────────

class TestRunFlags:
    def test_all_false_by_default(self):
        r = RunConfig()
        assert not any([r.strict_types, r.show_imports, r.debug])

    def test_strict_types_true(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[run]\nstrict_types=true\n")
            cfg = parse_config(path)
            assert cfg.run.strict_types is True
            assert cfg.run.debug        is False

    def test_debug_true(self):
        with tempfile.TemporaryDirectory() as d:
            write_entry(d)
            path = write_toml(d, "[project]\nname='x'\nentry='main.nk'\n[run]\ndebug=true\n")
            cfg = parse_config(path)
            assert cfg.run.debug is True