"""
Phase 26 — Developer Experience (remaining CLI/tooling items)

Covers the second half of Phase 26, after the LSP pieces
(test_phase26_lsp.py): nekova fmt --diff, the interactive nekova new
wizard, nekova.lock, the --why flag, expect_snapshot(...) snapshot
testing, and .env.example scaffolding for the default template.
"""
import unittest
import sys
import io
import os
import re
import json
import tempfile
import shutil
import subprocess
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_nekova(args, cwd, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "main.py")] + args,
        capture_output=True, text=True, cwd=cwd, env=env,
    )


# ── nekova fmt --diff ─────────────────────────────────────────

class TestFmtDiff(unittest.TestCase):

    def test_diff_does_not_modify_the_file(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            original = "task foo( a:int,b:int )->int:\n   return a+b\n"
            with open(path, "w") as f:
                f.write(original)
            _run_nekova(["fmt", "f.nk", "--diff", "--quiet"], cwd=tmpdir)
            with open(path) as f:
                self.assertEqual(f.read(), original)
        finally:
            shutil.rmtree(tmpdir)

    def test_diff_output_shows_unified_diff_markers(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("show 1+1\n")
            result = _run_nekova(["fmt", "f.nk", "--diff", "--quiet"], cwd=tmpdir)
            self.assertIn("@@", result.stdout)
            self.assertIn("-show 1+1", result.stdout)
            self.assertIn("+show 1 + 1", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_diff_on_unchanged_file_shows_nothing(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("show 1 + 1\n")
            result = _run_nekova(["fmt", "f.nk", "--diff", "--quiet"], cwd=tmpdir)
            self.assertNotIn("@@", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_diff_on_directory_reports_count(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "a.nk"), "w") as f:
                f.write("show 1+1\n")
            with open(os.path.join(tmpdir, "b.nk"), "w") as f:
                f.write("show 1 + 1\n")
            result = _run_nekova(["fmt", ".", "--diff", "--quiet"], cwd=tmpdir)
            self.assertIn("1 file(s) would be reformatted", result.stdout)
            self.assertIn("of 2 total", result.stdout)
        finally:
            shutil.rmtree(tmpdir)


# ── Interactive `nekova new` wizard ──────────────────────────────

class TestNewWizard(unittest.TestCase):

    def test_wizard_creates_project_with_chosen_template(self):
        from nekova.cli.commands import cmd_new
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            inputs = iter(["wizproj", "2", "Jane Doe", "A cool app"])
            with patch("builtins.input", lambda *a: next(inputs)):
                result = cmd_new(None)
            self.assertTrue(result)
            self.assertTrue(os.path.isdir("wizproj"))
            with open("wizproj/nekova.toml") as f:
                content = f.read()
            self.assertIn('author      = "Jane Doe"', content)
            self.assertIn('description = "A cool app"', content)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)

    def test_wizard_default_template_on_empty_choice(self):
        from nekova.cli.commands import cmd_new
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            inputs = iter(["defaultproj", "", "", ""])
            with patch("builtins.input", lambda *a: next(inputs)):
                result = cmd_new(None)
            self.assertTrue(result)
            with open("defaultproj/nekova.toml") as f:
                content = f.read()
            self.assertIn('description = "A NEKOVA project"', content)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)

    def test_wizard_cancels_on_empty_name(self):
        from nekova.cli.commands import cmd_new
        with patch("builtins.input", return_value=""):
            result = cmd_new(None)
        self.assertFalse(result)

    def test_non_interactive_usage_unaffected(self):
        """Passing a name directly must never trigger the wizard or
        call input() at all."""
        from nekova.cli.commands import cmd_new
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            with patch("builtins.input", side_effect=AssertionError(
                    "input() should not be called")):
                result = cmd_new("directproj", template="ai")
            self.assertTrue(result)
            with open("directproj/nekova.toml") as f:
                content = f.read()
            self.assertIn('author      = ""', content)
            self.assertIn('description = "A NEKOVA AI application"', content)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)


# ── .env.example scaffolding ──────────────────────────────────

class TestEnvExampleScaffolding(unittest.TestCase):

    def test_default_template_includes_env_example(self):
        from nekova.cli.templates import scaffold_project
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            scaffold_project("envproj", "default")
            self.assertTrue(os.path.exists("envproj/.env.example"))
            with open("envproj/.env.example") as f:
                content = f.read()
            self.assertIn("API_KEY", content)
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)

    def test_all_templates_include_env_example(self):
        from nekova.cli.templates import scaffold_project, list_templates
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            for name, _ in list_templates():
                scaffold_project(f"proj_{name}", name)
                self.assertTrue(
                    os.path.exists(f"proj_{name}/.env.example"),
                    f"{name} template is missing .env.example")
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir)


# ── nekova.lock ───────────────────────────────────────────────

class TestLockfile(unittest.TestCase):

    def _project(self, tmpdir, packages):
        with open(os.path.join(tmpdir, "nekova.toml"), "w") as f:
            f.write(
                '[project]\nname = "locktest"\nversion = "0.1.0"\n'
                f'[dependencies]\npackages = {json.dumps(packages)}\n'
            )

    def test_generates_lockfile_with_resolved_versions(self):
        from nekova.cli.lockfile import write_lockfile, LOCKFILE_NAME
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv"])
            data = write_lockfile(tmpdir)
            self.assertIn("csv", data["packages"])
            self.assertTrue(os.path.exists(os.path.join(tmpdir, LOCKFILE_NAME)))
        finally:
            shutil.rmtree(tmpdir)

    def test_unresolved_package_flagged_not_silently_dropped(self):
        from nekova.cli.lockfile import generate_lock_data
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv", "totally-fake-package"])
            data = generate_lock_data(tmpdir)
            self.assertIn("csv", data["packages"])
            self.assertIn("totally-fake-package", data["unresolved"])
            self.assertNotIn("totally-fake-package", data["packages"])
        finally:
            shutil.rmtree(tmpdir)

    def test_check_reports_in_sync_after_generation(self):
        from nekova.cli.lockfile import write_lockfile, check_lockfile
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv"])
            write_lockfile(tmpdir)
            in_sync, drift = check_lockfile(tmpdir)
            self.assertTrue(in_sync)
            self.assertEqual(drift, {})
        finally:
            shutil.rmtree(tmpdir)

    def test_check_detects_drift(self):
        from nekova.cli.lockfile import write_lockfile, check_lockfile, LOCKFILE_NAME
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv"])
            write_lockfile(tmpdir)
            # Simulate drift: hand-edit the committed lockfile as if
            # it's now stale relative to the registry.
            path = os.path.join(tmpdir, LOCKFILE_NAME)
            with open(path) as f:
                data = json.load(f)
            data["packages"]["csv"] = "0.0.1-stale"
            with open(path, "w") as f:
                json.dump(data, f)
            in_sync, drift = check_lockfile(tmpdir)
            self.assertFalse(in_sync)
            self.assertIn("csv", drift)
        finally:
            shutil.rmtree(tmpdir)

    def test_check_without_lockfile_reports_missing(self):
        from nekova.cli.lockfile import check_lockfile
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv"])
            in_sync, drift = check_lockfile(tmpdir)
            self.assertFalse(in_sync)
            self.assertIn("_missing", drift)
        finally:
            shutil.rmtree(tmpdir)

    def test_cli_lock_check_exit_code_reflects_drift(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._project(tmpdir, ["csv"])
            _run_nekova(["lock", ".", "--quiet"], cwd=tmpdir)
            result = _run_nekova(["lock", ".", "--check", "--quiet"], cwd=tmpdir)
            self.assertEqual(result.returncode, 0)
        finally:
            shutil.rmtree(tmpdir)


# ── --why flag ────────────────────────────────────────────────

class TestWhyFlag(unittest.TestCase):

    def test_why_absent_by_default(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("show undefined_var\n")
            result = _run_nekova(["run", "f.nk", "--quiet"], cwd=tmpdir)
            self.assertNotIn("Why:", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_why_shows_internal_origin_on_runtime_error(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("show undefined_var\n")
            result = _run_nekova(["run", "f.nk", "--why", "--quiet"], cwd=tmpdir)
            self.assertIn("Why:", result.stdout)
            self.assertIn("interpreter.py", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_why_shows_internal_origin_on_parse_error(self):
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "f.nk")
            with open(path, "w") as f:
                f.write("let x = )\n")
            result = _run_nekova(["run", "f.nk", "--why", "--quiet"], cwd=tmpdir)
            self.assertIn("Why:", result.stdout)
            self.assertIn("parser.py", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_find_why_origin_direct(self):
        from nekova.cli.error_display import _find_why_origin
        try:
            raise ValueError("boom")
        except ValueError as e:
            origin = _find_why_origin(e)
        # A plain ValueError raised from this test file has no NEKOVA
        # source frames in its traceback at all.
        self.assertIsNone(origin)


# ── expect_snapshot ───────────────────────────────────────────

class TestExpectSnapshot(unittest.TestCase):

    def _run_nk(self, tmpdir, source, env_extra=None):
        path = os.path.join(tmpdir, "s.nk")
        with open(path, "w") as f:
            f.write(source)
        return _run_nekova(["run", "s.nk", "--quiet"], cwd=tmpdir, env_extra=env_extra)

    def test_first_run_creates_snapshot_and_passes(self):
        tmpdir = tempfile.mkdtemp()
        try:
            result = self._run_nk(tmpdir, (
                'test "t":\n'
                '    expect_snapshot(2 + 3, "sum")\n'
            ))
            self.assertIn("Created snapshot", result.stdout)
            self.assertIn("PASS", result.stdout)
            snap_path = os.path.join(tmpdir, "__snapshots__", "s.snap.json")
            self.assertTrue(os.path.exists(snap_path))
            with open(snap_path) as f:
                data = json.load(f)
            self.assertEqual(data["t::sum"], 5)
        finally:
            shutil.rmtree(tmpdir)

    def test_matching_value_passes_silently(self):
        tmpdir = tempfile.mkdtemp()
        try:
            src = 'test "t":\n    expect_snapshot(2 + 3, "sum")\n'
            self._run_nk(tmpdir, src)  # create
            result = self._run_nk(tmpdir, src)  # verify
            self.assertNotIn("Created", result.stdout)
            self.assertIn("PASS", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_mismatch_fails_the_test(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._run_nk(tmpdir, 'test "t":\n    expect_snapshot(2 + 3, "sum")\n')
            result = self._run_nk(tmpdir, 'test "t":\n    expect_snapshot(2 + 4, "sum")\n')
            self.assertIn("FAIL", result.stdout)
            self.assertIn("value changed", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_update_snapshots_flag_accepts_new_value(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._run_nk(tmpdir, 'test "t":\n    expect_snapshot(2 + 3, "sum")\n')
            result = self._run_nk(
                tmpdir, 'test "t":\n    expect_snapshot(2 + 4, "sum")\n',
                env_extra={"NEKOVA_UPDATE_SNAPSHOTS": "1"},
            )
            self.assertIn("Updated snapshot", result.stdout)
            self.assertIn("PASS", result.stdout)
            snap_path = os.path.join(tmpdir, "__snapshots__", "s.snap.json")
            with open(snap_path) as f:
                data = json.load(f)
            self.assertEqual(data["t::sum"], 6)
        finally:
            shutil.rmtree(tmpdir)

    def test_update_snapshots_cli_flag_sets_env_var(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self._run_nk(tmpdir, 'test "t":\n    expect_snapshot(2 + 3, "sum")\n')
            path = os.path.join(tmpdir, "s.nk")
            with open(path, "w") as f:
                f.write('test "t":\n    expect_snapshot(2 + 4, "sum")\n')
            result = _run_nekova(
                ["run", "s.nk", "--update-snapshots", "--quiet"], cwd=tmpdir)
            self.assertIn("Updated snapshot", result.stdout)
        finally:
            shutil.rmtree(tmpdir)

    def test_different_names_do_not_collide(self):
        tmpdir = tempfile.mkdtemp()
        try:
            result = self._run_nk(tmpdir, (
                'test "t":\n'
                '    expect_snapshot(1, "a")\n'
                '    expect_snapshot(2, "b")\n'
            ))
            self.assertIn("2/2", result.stdout)
            snap_path = os.path.join(tmpdir, "__snapshots__", "s.snap.json")
            with open(snap_path) as f:
                data = json.load(f)
            self.assertEqual(data["t::a"], 1)
            self.assertEqual(data["t::b"], 2)
        finally:
            shutil.rmtree(tmpdir)

    def test_standalone_usage_outside_test_block(self):
        tmpdir = tempfile.mkdtemp()
        try:
            result = self._run_nk(tmpdir, 'expect_snapshot("hi", "greeting")\nshow "done"\n')
            self.assertIn("done", result.stdout)
            self.assertEqual(result.returncode, 0)
        finally:
            shutil.rmtree(tmpdir)

    def test_dict_value_snapshot(self):
        tmpdir = tempfile.mkdtemp()
        try:
            result = self._run_nk(tmpdir, (
                'let data = {"name": "Alice", "age": 30}\n'
                'expect_snapshot(data, "person")\n'
            ))
            self.assertEqual(result.returncode, 0)
            snap_path = os.path.join(tmpdir, "__snapshots__", "s.snap.json")
            with open(snap_path) as f:
                data = json.load(f)
            self.assertEqual(data["_global::person"]["name"], "Alice")
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()