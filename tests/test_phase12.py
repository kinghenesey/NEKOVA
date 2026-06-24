# =============================================================
# NEKOVA — Phase 12 Tests
# =============================================================
# 12A: nekova new --template  (templates.py)
# 12B: REPL improvements      (repl.py)
# 12C: --watch mode           (watcher.py)
# 12D: version 1.3.1          (config.py / pyproject.toml)
# =============================================================

import os
import sys
import shutil
import tempfile
import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# =============================================================
# 12D — Version check  (run first — no side effects)
# =============================================================

class TestVersion:
    def test_version_is_1_3_0(self):
        from nekova.config import NEKOVA_VERSION
        assert NEKOVA_VERSION == "1.3.1"

    def test_codename_unchanged(self):
        from nekova.config import NEKOVA_CODENAME
        assert NEKOVA_CODENAME == "Genesis"

    def test_changelog_exists(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        assert os.path.isfile(path), "CHANGELOG.md not found"

    def test_changelog_mentions_1_3_0(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "1.3.1" in text

    def test_pyproject_version(self):
        path = os.path.join(ROOT, "pyproject.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert 'version = "1.3.1"' in text


# =============================================================
# 12A — Templates
# =============================================================

class TestTemplateModule:
    """Unit-test templates.py without touching the filesystem."""

    def test_list_templates_returns_four(self):
        from nekova.cli.templates import list_templates
        tpls = list_templates()
        assert len(tpls) == 4

    def test_template_names(self):
        from nekova.cli.templates import list_templates
        names = [n for n, _ in list_templates()]
        assert set(names) == {"default", "web", "ai", "fullstack"}

    def test_templates_dict_has_correct_keys(self):
        from nekova.cli.templates import TEMPLATES
        assert "default" in TEMPLATES
        assert "web" in TEMPLATES
        assert "ai" in TEMPLATES
        assert "fullstack" in TEMPLATES

    def test_default_template_has_main_nk(self):
        from nekova.cli.templates import TEMPLATES
        assert "src/main.nk" in TEMPLATES["default"]

    def test_web_template_has_routes(self):
        from nekova.cli.templates import TEMPLATES
        assert "src/routes/api.nk" in TEMPLATES["web"]

    def test_ai_template_has_agent(self):
        from nekova.cli.templates import TEMPLATES
        assert "src/agent.nk" in TEMPLATES["ai"]

    def test_fullstack_has_db_and_ai(self):
        from nekova.cli.templates import TEMPLATES
        assert "src/db.nk" in TEMPLATES["fullstack"]
        assert "src/ai.nk" in TEMPLATES["fullstack"]

    def test_all_templates_have_nekova_toml(self):
        from nekova.cli.templates import TEMPLATES
        for name, files in TEMPLATES.items():
            assert "nekova.toml" in files, f"{name} missing nekova.toml"

    def test_all_templates_have_readme(self):
        from nekova.cli.templates import TEMPLATES
        for name, files in TEMPLATES.items():
            assert "README.md" in files, f"{name} missing README.md"

    def test_all_templates_have_gitignore(self):
        from nekova.cli.templates import TEMPLATES
        for name, files in TEMPLATES.items():
            assert ".gitignore" in files, f"{name} missing .gitignore"

    def test_web_main_nk_contains_route(self):
        from nekova.cli.templates import TEMPLATES
        assert "route GET" in TEMPLATES["web"]["src/main.nk"]

    def test_ai_main_nk_contains_think(self):
        from nekova.cli.templates import TEMPLATES
        assert "think" in TEMPLATES["ai"]["src/main.nk"]

    def test_fullstack_main_nk_has_all_features(self):
        from nekova.cli.templates import TEMPLATES
        content = TEMPLATES["fullstack"]["src/main.nk"]
        assert "route" in content
        assert "think" in content
        assert "connect" in content

    def test_scaffold_invalid_template_returns_false(self):
        from nekova.cli.templates import scaffold_project
        with tempfile.TemporaryDirectory() as tmp:
            original = os.getcwd()
            os.chdir(tmp)
            try:
                result = scaffold_project("testproj", "nonexistent")
                assert result is False
            finally:
                os.chdir(original)

    def test_scaffold_description_for_all_templates(self):
        from nekova.cli.templates import TEMPLATE_DESCRIPTIONS
        for name in ("default", "web", "ai", "fullstack"):
            assert name in TEMPLATE_DESCRIPTIONS
            assert len(TEMPLATE_DESCRIPTIONS[name]) > 5


class TestScaffoldFilesystem:
    """Test scaffold_project actually writes files."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.original = os.getcwd()
        os.chdir(self.tmp)

    def teardown_method(self):
        os.chdir(self.original)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _scaffold(self, name, template="default"):
        from nekova.cli.templates import scaffold_project
        return scaffold_project(name, template)

    def test_default_creates_main_nk(self):
        assert self._scaffold("myapp") is True
        assert os.path.isfile("myapp/src/main.nk")

    def test_default_creates_nekova_toml(self):
        self._scaffold("myapp2")
        assert os.path.isfile("myapp2/nekova.toml")

    def test_default_creates_readme(self):
        self._scaffold("myapp3")
        assert os.path.isfile("myapp3/README.md")

    def test_web_creates_api_routes(self):
        self._scaffold("webapp", "web")
        assert os.path.isfile("webapp/src/routes/api.nk")

    def test_web_creates_env_example(self):
        self._scaffold("webapp2", "web")
        assert os.path.isfile("webapp2/.env.example")

    def test_ai_creates_agent(self):
        self._scaffold("aiapp", "ai")
        assert os.path.isfile("aiapp/src/agent.nk")

    def test_fullstack_creates_db_nk(self):
        self._scaffold("fsapp", "fullstack")
        assert os.path.isfile("fsapp/src/db.nk")

    def test_fullstack_creates_ai_nk(self):
        self._scaffold("fsapp2", "fullstack")
        assert os.path.isfile("fsapp2/src/ai.nk")

    def test_main_nk_contains_project_name(self):
        self._scaffold("myproject", "default")
        with open("myproject/src/main.nk", encoding="utf-8") as f:
            text = f.read()
        assert "myproject" in text

    def test_toml_contains_project_name(self):
        self._scaffold("tomltest", "web")
        with open("tomltest/nekova.toml", encoding="utf-8") as f:
            text = f.read()
        assert "tomltest" in text

    def test_main_nk_contains_nekova_version(self):
        self._scaffold("vtest", "ai")
        with open("vtest/src/main.nk", encoding="utf-8") as f:
            text = f.read()
        assert "1.3.1" in text

    def test_files_are_utf8_without_bom(self):
        self._scaffold("bomtest", "fullstack")
        for fpath in ["bomtest/src/main.nk", "bomtest/nekova.toml"]:
            with open(fpath, "rb") as f:
                raw = f.read()
            assert not raw.startswith(b"\xef\xbb\xbf"), f"{fpath} has BOM"


class TestCmdNewTemplate:
    """Test cmd_new with --template argument."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.original = os.getcwd()
        os.chdir(self.tmp)

    def teardown_method(self):
        os.chdir(self.original)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cmd_new_default(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("proj_default")
        assert result is True
        assert os.path.isfile("proj_default/src/main.nk")

    def test_cmd_new_web(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("proj_web", template="web")
        assert result is True
        assert os.path.isfile("proj_web/src/routes/api.nk")

    def test_cmd_new_ai(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("proj_ai", template="ai")
        assert result is True
        assert os.path.isfile("proj_ai/src/agent.nk")

    def test_cmd_new_fullstack(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("proj_fs", template="fullstack")
        assert result is True
        assert os.path.isfile("proj_fs/src/db.nk")
        assert os.path.isfile("proj_fs/src/ai.nk")

    def test_cmd_new_invalid_template_returns_false(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("proj_bad", template="doesnotexist")
        assert result is False

    def test_cmd_new_existing_dir_returns_false(self):
        from nekova.cli.commands import cmd_new
        os.makedirs("existing_proj")
        result = cmd_new("existing_proj")
        assert result is False

    def test_cmd_new_no_name_returns_false(self):
        from nekova.cli.commands import cmd_new
        result = cmd_new("")
        assert result is False


# =============================================================
# 12B — REPL improvements
# =============================================================

class TestREPLImports:
    """Verify REPL module loads and exposes expected API."""

    def test_repl_imports(self):
        import repl  # noqa: F401

    def test_repl_class_exists(self):
        from repl import REPL
        assert REPL is not None

    def test_repl_has_start(self):
        from repl import REPL
        assert hasattr(REPL, "start")

    def test_repl_has_history(self):
        from repl import REPL
        r = REPL()
        assert hasattr(r, "history")
        assert isinstance(r.history, list)

    def test_repl_has_readline_attr(self):
        from repl import REPL
        r = REPL()
        assert hasattr(r, "_readline")

    def test_history_file_constant(self):
        import repl
        assert hasattr(repl, "HISTORY_FILE")
        assert repl.HISTORY_FILE.endswith(".nekova_history")

    def test_max_history_constant(self):
        import repl
        assert hasattr(repl, "MAX_HISTORY")
        assert repl.MAX_HISTORY >= 100

    def test_setup_readline_callable(self):
        import repl
        assert callable(repl._setup_readline)

    def test_save_history_callable(self):
        import repl
        assert callable(repl._save_history)
        # Should not raise when readline_mod is None
        repl._save_history(None)


class TestREPLQmarkCommands:
    """Verify ?-prefixed command handling."""

    def setup_method(self):
        from repl import REPL
        self.repl = REPL()

    def test_help_command(self, capsys):
        result = self.repl._handle_command("help")
        assert result is True

    def test_qmark_help(self, capsys):
        result = self.repl._handle_command("?help")
        assert result is True

    def test_qmark_alone_shows_help(self, capsys):
        result = self.repl._handle_command("?")
        assert result is True

    def test_qmark_vars(self, capsys):
        result = self.repl._handle_command("?vars")
        assert result is True

    def test_qmark_history(self, capsys):
        result = self.repl._handle_command("?history")
        assert result is True

    def test_qmark_version(self, capsys):
        result = self.repl._handle_command("?version")
        assert result is True
        out = capsys.readouterr().out
        assert "1.3.1" in out

    def test_qmark_templates(self, capsys):
        result = self.repl._handle_command("?templates")
        assert result is True
        out = capsys.readouterr().out
        assert "web" in out
        assert "ai" in out
        assert "fullstack" in out

    def test_templates_command(self, capsys):
        result = self.repl._handle_command("templates")
        assert result is True

    def test_reset_clears_history(self):
        self.repl.history = ["show 1", "show 2"]
        self.repl._handle_command("reset")
        assert self.repl.history == []

    def test_version_command(self, capsys):
        self.repl._handle_command("version")
        out = capsys.readouterr().out
        assert "1.3.1" in out

    def test_exit_commands(self):
        for cmd in ("exit", "quit", "q", ":q"):
            r = REPL_no_exit()
            result = r._handle_command_safe(cmd)
            assert result is True

    def test_unknown_command_returns_false(self):
        result = self.repl._handle_command("notacommand")
        assert result is False


class REPLNoExit:
    """Thin REPL wrapper that prevents sys.exit during tests."""
    def __init__(self):
        from repl import REPL
        self.repl = REPL()

    def _handle_command_safe(self, cmd):
        self.repl.running = True
        try:
            return self.repl._handle_command(cmd)
        except SystemExit:
            return True

def REPL_no_exit():
    return REPLNoExit()


class TestREPLHistory:
    def test_history_appended_after_execute(self):
        from repl import REPL
        r = REPL()
        r._execute('x = 42')
        assert len(r.history) == 1
        assert r.history[0] == 'x = 42'

    def test_history_multiple_commands(self):
        from repl import REPL
        r = REPL()
        r._execute('a = 1')
        r._execute('b = 2')
        assert len(r.history) == 2

    def test_print_history_empty(self, capsys):
        from repl import REPL
        r = REPL()
        r._print_history()
        out = capsys.readouterr().out
        assert "No history" in out

    def test_print_history_shows_entries(self, capsys):
        from repl import REPL
        r = REPL()
        r.history = ["show 1", "show 2", "x = 3"]
        r._print_history()
        out = capsys.readouterr().out
        assert "show 1" in out


class TestREPLExecute:
    def test_execute_assignment(self):
        from repl import REPL
        r = REPL()
        r._execute('myvar = 99')
        val = r.interpreter.env.get('myvar')
        assert val == 99

    def test_execute_error_doesnt_crash(self, capsys):
        from repl import REPL
        r = REPL()
        # Bad syntax — should print error, not raise
        r._execute('!!invalid!!')
        out = capsys.readouterr().out
        assert len(r.history) == 0  # not appended on error


# =============================================================
# 12C — Watcher module
# =============================================================

class TestWatcherModule:
    """Verify watcher.py imports and exposes expected API."""

    def test_watcher_imports(self):
        import watcher  # noqa: F401

    def test_watch_callable(self):
        from watcher import watch
        assert callable(watch)

    def test_run_file_callable(self):
        from watcher import _run_file
        assert callable(_run_file)

    def test_separator_callable(self):
        from watcher import _separator
        assert callable(_separator)

    def test_timestamp_callable(self):
        from watcher import _timestamp
        import re
        ts = _timestamp()
        assert re.match(r"\d{2}:\d{2}:\d{2}", ts)

    def test_separator_output(self, capsys):
        from watcher import _separator
        _separator("test")
        out = capsys.readouterr().out
        assert "test" in out

    def test_separator_no_label(self, capsys):
        from watcher import _separator
        _separator()
        out = capsys.readouterr().out
        assert out.strip() != ""

    def test_watch_nonexistent_file_exits(self):
        from watcher import watch
        with pytest.raises(SystemExit) as exc:
            watch("/nonexistent/path/file.nk")
        assert exc.value.code == 1

    def test_polling_watcher_callable(self):
        from watcher import _watch_with_polling
        assert callable(_watch_with_polling)

    def test_watchdog_watcher_callable(self):
        from watcher import _watch_with_watchdog
        assert callable(_watch_with_watchdog)


# =============================================================
# 12 integration — parse_args
# =============================================================

class TestMainParseArgs:
    """Verify main.py parse_args handles new Phase 12 flags."""

    def _parse(self, argv):
        # Import main as a module properly
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        # Save and restore sys.argv to avoid side effects
        old_argv = sys.argv[:]
        sys.argv = ["nekova"] + list(argv)
        try:
            import importlib
            import main as _main_mod
            importlib.reload(_main_mod)
            return _main_mod.parse_args(argv)
        finally:
            sys.argv = old_argv

    def test_watch_flag(self):
        args = self._parse(["run", "app.nk", "--watch"])
        assert args["watch"] is True

    def test_no_watch_flag(self):
        args = self._parse(["run", "app.nk"])
        assert args["watch"] is False

    def test_template_flag(self):
        args = self._parse(["new", "myapp", "--template", "web"])
        assert args["template"] == "web"

    def test_template_default(self):
        args = self._parse(["new", "myapp"])
        assert args["template"] == "default"

    def test_watch_subcommand(self):
        args = self._parse(["watch", "app.nk"])
        assert args["command"] == "watch"
        assert args["arg"] == "app.nk"