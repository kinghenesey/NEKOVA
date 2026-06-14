# =============================================================
# NEKOVA — Phase 4 Tests
# =============================================================
# Covers: nekova new scaffold · nekova.toml → runner wiring
#         nekova build validation · nekova clean
# Run:  pytest tests/test_phase4.py -v
# =============================================================

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.cli.commands import cmd_new, cmd_build, cmd_clean
from nekova.toml_loader import parse_config, load_config, ConfigError


# ─────────────────────────────────────────────────────────────
# 1. nekova new — project scaffold
# ─────────────────────────────────────────────────────────────

class TestCmdNew(unittest.TestCase):

    def setUp(self):
        self.orig = os.getcwd()
        self.tmp  = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.orig)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_new_creates_directory(self):
        result = cmd_new("myapp")
        self.assertTrue(result)
        self.assertTrue(os.path.isdir("myapp"))

    def test_new_creates_src_main_nk(self):
        cmd_new("myapp")
        self.assertTrue(os.path.isfile("myapp/src/main.nk"))

    def test_new_creates_tests_dir(self):
        cmd_new("myapp")
        self.assertTrue(os.path.isdir("myapp/tests"))

    def test_new_creates_nekova_toml(self):
        cmd_new("myapp")
        self.assertTrue(os.path.isfile("myapp/nekova.toml"))

    def test_new_creates_readme(self):
        cmd_new("myapp")
        self.assertTrue(os.path.isfile("myapp/README.md"))

    def test_new_creates_gitignore(self):
        cmd_new("myapp")
        self.assertTrue(os.path.isfile("myapp/.gitignore"))

    def test_new_toml_has_project_name(self):
        cmd_new("myapp")
        toml_text = open("myapp/nekova.toml", encoding="utf-8").read()
        self.assertIn('name        = "myapp"', toml_text)

    def test_new_toml_has_entry(self):
        cmd_new("myapp")
        toml_text = open("myapp/nekova.toml", encoding="utf-8").read()
        self.assertIn('entry       = "src/main.nk"', toml_text)

    def test_new_toml_parseable(self):
        """The generated nekova.toml must be parseable (once entry exists)."""
        cmd_new("myapp")
        # parse_config expects entry file to exist — it does (src/main.nk)
        os.chdir("myapp")
        config = parse_config("nekova.toml")
        self.assertEqual(config.project.name, "myapp")
        self.assertEqual(config.project.version, "0.1.0")
        os.chdir("..")

    def test_new_toml_no_bom(self):
        cmd_new("myapp")
        raw = open("myapp/nekova.toml", "rb").read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "nekova.toml must not have BOM")

    def test_new_main_nk_no_bom(self):
        cmd_new("myapp")
        raw = open("myapp/src/main.nk", "rb").read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "main.nk must not have BOM")

    def test_new_main_nk_has_show(self):
        cmd_new("myapp")
        src = open("myapp/src/main.nk", encoding="utf-8").read()
        self.assertIn("show", src)

    def test_new_readme_has_project_name(self):
        cmd_new("myapp")
        readme = open("myapp/README.md", encoding="utf-8").read()
        self.assertIn("myapp", readme)

    def test_new_readme_has_nekova_run(self):
        cmd_new("myapp")
        readme = open("myapp/README.md", encoding="utf-8").read()
        self.assertIn("nekova run", readme)

    def test_new_fails_without_name(self):
        result = cmd_new("")
        self.assertFalse(result)

    def test_new_fails_on_existing_dir(self):
        os.makedirs("existing")
        result = cmd_new("existing")
        self.assertFalse(result)

    def test_new_hyphenated_name(self):
        result = cmd_new("my-cool-app")
        self.assertTrue(result)
        self.assertTrue(os.path.isfile("my-cool-app/nekova.toml"))

    def test_new_toml_has_ai_section(self):
        cmd_new("myapp")
        toml_text = open("myapp/nekova.toml", encoding="utf-8").read()
        self.assertIn("[ai]", toml_text)
        self.assertIn("model", toml_text)

    def test_new_toml_has_run_section(self):
        cmd_new("myapp")
        toml_text = open("myapp/nekova.toml", encoding="utf-8").read()
        self.assertIn("[run]", toml_text)
        self.assertIn("debug", toml_text)


# ─────────────────────────────────────────────────────────────
# 2. nekova.toml → runner: load_config on scaffolded project
# ─────────────────────────────────────────────────────────────

class TestTomlLoaderIntegration(unittest.TestCase):

    def setUp(self):
        self.orig = os.getcwd()
        self.tmp  = tempfile.mkdtemp()
        os.chdir(self.tmp)
        cmd_new("demo")
        os.chdir("demo")

    def tearDown(self):
        os.chdir(self.orig)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_config_finds_toml(self):
        config = load_config()
        self.assertIsNotNone(config)

    def test_load_config_project_name(self):
        config = load_config()
        self.assertEqual(config.project.name, "demo")

    def test_load_config_entry_path_exists(self):
        config = load_config()
        self.assertTrue(os.path.isfile(config.entry_path))

    def test_load_config_run_defaults(self):
        config = load_config()
        self.assertFalse(config.run.debug)
        self.assertFalse(config.run.strict_types)
        self.assertFalse(config.run.show_imports)

    def test_load_config_ai_defaults(self):
        config = load_config()
        self.assertEqual(config.ai.model, "claude")

    def test_load_config_from_subdir(self):
        """load_config should walk upward to find nekova.toml."""
        os.makedirs("src/deep", exist_ok=True)
        os.chdir("src/deep")
        config = load_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.project.name, "demo")

    def test_parse_config_run_debug_flag(self):
        """Manually set debug = true and verify it parses."""
        toml = open("nekova.toml", encoding="utf-8").read()
        toml = toml.replace("debug        = false", "debug        = true")
        open("nekova.toml", "w", encoding="utf-8").write(toml)
        config = parse_config("nekova.toml")
        self.assertTrue(config.run.debug)

    def test_parse_config_strict_types_flag(self):
        toml = open("nekova.toml", encoding="utf-8").read()
        toml = toml.replace("strict_types = false", "strict_types = true")
        open("nekova.toml", "w", encoding="utf-8").write(toml)
        config = parse_config("nekova.toml")
        self.assertTrue(config.run.strict_types)

    def test_missing_entry_warns(self):
        """parse_config issues a warning when entry file is absent."""
        import warnings
        os.remove("src/main.nk")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            parse_config("nekova.toml")
        msgs = [str(x.message) for x in w]
        self.assertTrue(
            any("entry" in m.lower() or "src/main.nk" in m for m in msgs),
            f"Expected missing-entry warning, got: {msgs}"
        )


# ─────────────────────────────────────────────────────────────
# 3. nekova build — lex + parse validation
# ─────────────────────────────────────────────────────────────

class TestCmdBuild(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _nk(self, name, src):
        path = os.path.join(self.tmp, name)
        open(path, "w", encoding="utf-8").write(src)
        return path

    def test_build_valid_file(self):
        path = self._nk("valid.nk", 'show "Hello!"')
        self.assertTrue(cmd_build(path))

    def test_build_valid_with_vars(self):
        src = 'let x: number = 42\nshow f"x is {x}"'
        path = self._nk("vars.nk", src)
        self.assertTrue(cmd_build(path))

    def test_build_valid_async(self):
        src = (
            'async func greet(name: text):\n'
            '    show f"Hi {name}!"\n'
            '\n'
            'show "done"\n'
        )
        path = self._nk("async.nk", src)
        self.assertTrue(cmd_build(path))

    def test_build_missing_file(self):
        self.assertFalse(cmd_build("/nonexistent/file.nk"))

    def test_build_no_path(self):
        self.assertFalse(cmd_build(""))

    def test_build_returns_bool(self):
        path = self._nk("t.nk", "show 1")
        result = cmd_build(path)
        self.assertIsInstance(result, bool)

    def test_build_multiline(self):
        src = '\n'.join([
            'let a: number = 1',
            'let b: number = 2',
            'let c: number = a + b',
            'show c',
        ])
        path = self._nk("multi.nk", src)
        self.assertTrue(cmd_build(path))

    def test_build_imports(self):
        src = 'import math from "nekova/stdlib/math.nk"\nshow "ok"'
        path = self._nk("imp.nk", src)
        # build only lexes+parses — import resolution happens at runtime
        self.assertTrue(cmd_build(path))


# ─────────────────────────────────────────────────────────────
# 4. nekova clean
# ─────────────────────────────────────────────────────────────

class TestCmdClean(unittest.TestCase):

    def setUp(self):
        self.orig = os.getcwd()
        self.tmp  = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.orig)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_removes_pycache(self):
        os.makedirs("pkg/__pycache__")
        open("pkg/__pycache__/mod.cpython-312.pyc", "w").close()
        cmd_clean()
        self.assertFalse(os.path.exists("pkg/__pycache__"))

    def test_clean_removes_pyc(self):
        open("stale.pyc", "w").close()
        cmd_clean()
        self.assertFalse(os.path.exists("stale.pyc"))

    def test_clean_returns_none(self):
        result = cmd_clean()
        self.assertIsNone(result)

    def test_clean_safe_on_empty_dir(self):
        # Should not crash on an empty directory
        cmd_clean()

    def test_clean_preserves_nk_files(self):
        open("app.nk", "w").write('show "hi"')
        cmd_clean()
        self.assertTrue(os.path.exists("app.nk"))


if __name__ == "__main__":
    unittest.main(verbosity=2)