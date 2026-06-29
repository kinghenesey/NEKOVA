# =============================================================
# NEKOVA Phase 11 Tests — Package System
# =============================================================
import sys
import os
import re
import json
import tempfile
import shutil
from pathlib import Path
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.packages import (
    BUILTIN_PACKAGES, load_registry, save_registry,
    is_installed, search_packages, PACKAGES_DIR,
)
from nekova.cli.package_manager import (
    install_package, uninstall_package, list_packages,
    search, package_info, _generate_module_code,
)


def silence(fn, *args, **kwargs):
    """Call fn suppressing stdout."""
    buf = StringIO()
    sys.stdout = buf
    try:
        return fn(*args, **kwargs)
    finally:
        sys.stdout = sys.__stdout__


# ── helpers to isolate registry during tests ─────────────────

class IsolatedRegistry:
    """Context manager: redirects registry to a temp dir."""
    def __init__(self):
        self.tmpdir = None
        self._orig_packages_dir = None
        self._orig_registry     = None

    def __enter__(self):
        import nekova.packages as pkg_mod
        self.tmpdir             = tempfile.mkdtemp()
        self._orig_packages_dir = pkg_mod.PACKAGES_DIR
        self._orig_registry     = pkg_mod.REGISTRY_FILE
        pkg_mod.PACKAGES_DIR    = self.tmpdir
        pkg_mod.REGISTRY_FILE   = os.path.join(self.tmpdir, "registry.json")
        # Patch package_manager too
        import nekova.cli.package_manager as pm
        pm.PACKAGES_DIR         = self.tmpdir
        return self.tmpdir

    def __exit__(self, *_):
        import nekova.packages as pkg_mod
        import nekova.cli.package_manager as pm
        pkg_mod.PACKAGES_DIR  = self._orig_packages_dir
        pkg_mod.REGISTRY_FILE = self._orig_registry
        pm.PACKAGES_DIR       = self._orig_packages_dir
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# ==============================================================
# SECTION 1 — Registry / catalogue
# ==============================================================

class TestRegistry:

    def test_builtin_packages_exist(self):
        assert len(BUILTIN_PACKAGES) >= 11

    def test_all_expected_packages_present(self):
        expected = {
            "charts", "auth", "validation", "colors", "random",
            "requests", "openai", "stripe", "sendmail", "csv", "slug",
        }
        assert expected.issubset(set(BUILTIN_PACKAGES.keys()))

    def test_each_package_has_required_fields(self):
        required = {"name", "version", "description", "functions"}
        for name, info in BUILTIN_PACKAGES.items():
            missing = required - set(info.keys())
            assert not missing, f"{name} missing: {missing}"

    def test_each_package_has_functions(self):
        for name, info in BUILTIN_PACKAGES.items():
            assert info["functions"], f"{name} has empty functions list"

    def test_versions_are_strings(self):
        for name, info in BUILTIN_PACKAGES.items():
            assert isinstance(info["version"], str)
            assert "." in info["version"]

    def test_new_packages_have_category(self):
        new_pkgs = {"requests", "openai", "stripe", "sendmail", "csv", "slug"}
        for name in new_pkgs:
            assert "category" in BUILTIN_PACKAGES[name], \
                f"{name} missing category"

    def test_requests_category(self):
        assert BUILTIN_PACKAGES["requests"]["category"] == "networking"

    def test_openai_category(self):
        assert BUILTIN_PACKAGES["openai"]["category"] == "ai"

    def test_stripe_category(self):
        assert BUILTIN_PACKAGES["stripe"]["category"] == "payments"

    def test_csv_category(self):
        assert BUILTIN_PACKAGES["csv"]["category"] == "data"


class TestRegistrySearch:

    def test_search_by_name(self):
        results = search_packages("csv")
        names = [r[0] for r in results]
        assert "csv" in names

    def test_search_by_category(self):
        results = search_packages("networking")
        names = [r[0] for r in results]
        assert "requests" in names

    def test_search_by_description(self):
        results = search_packages("HTTP")
        names = [r[0] for r in results]
        assert "requests" in names

    def test_search_by_function(self):
        results = search_packages("slugify")
        names = [r[0] for r in results]
        assert "slug" in names

    def test_search_no_results(self):
        results = search_packages("xyznonexistent123")
        assert results == []

    def test_search_all_returns_all(self):
        # "all" substring appears in no name/category but let's test
        # by checking that searching for a common word returns something
        results = search_packages("util")
        assert len(results) >= 1

    def test_search_returns_tuples(self):
        results = search_packages("csv")
        assert all(isinstance(r, tuple) and len(r) == 2
                   for r in results)


# ==============================================================
# SECTION 2 — install / uninstall
# ==============================================================

class TestInstall:

    def test_install_charts(self):
        with IsolatedRegistry() as tmpdir:
            ok = silence(install_package, "charts")
            assert ok
            assert os.path.exists(os.path.join(tmpdir, "charts.py"))

    def test_install_auth(self):
        with IsolatedRegistry() as tmpdir:
            ok = silence(install_package, "auth")
            assert ok
            assert os.path.exists(os.path.join(tmpdir, "auth.py"))

    def test_install_validation(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "validation")
            assert ok

    def test_install_colors(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "colors")
            assert ok

    def test_install_random(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "random")
            assert ok

    def test_install_csv(self):
        with IsolatedRegistry() as tmpdir:
            ok = silence(install_package, "csv")
            assert ok
            assert os.path.exists(os.path.join(tmpdir, "csv.py"))

    def test_install_slug(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "slug")
            assert ok

    def test_install_sendmail(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "sendmail")
            assert ok

    def test_install_requests(self):
        with IsolatedRegistry() as _:
            ok = silence(install_package, "requests")
            assert ok

    def test_install_updates_registry(self):
        with IsolatedRegistry() as _:
            import nekova.packages as pkg_mod
            silence(install_package, "charts")
            reg = load_registry()
            assert "charts" in reg
            assert reg["charts"]["version"] == BUILTIN_PACKAGES["charts"]["version"]

    def test_install_already_installed(self):
        with IsolatedRegistry():
            silence(install_package, "auth")
            ok = silence(install_package, "auth")  # second time
            assert ok   # should still return True

    def test_install_unknown_returns_false(self):
        with IsolatedRegistry():
            ok = silence(install_package, "xyznonexistent")
            assert not ok

    def test_install_creates_valid_python(self):
        with IsolatedRegistry() as tmpdir:
            silence(install_package, "slug")
            module_path = os.path.join(tmpdir, "slug.py")
            assert os.path.exists(module_path)
            src = open(module_path).read()
            compile(src, module_path, "exec")  # no SyntaxError


class TestUninstall:

    def test_uninstall_installed(self):
        with IsolatedRegistry() as tmpdir:
            silence(install_package, "charts")
            ok = silence(uninstall_package, "charts")
            assert ok
            assert not os.path.exists(os.path.join(tmpdir, "charts.py"))

    def test_uninstall_removes_from_registry(self):
        with IsolatedRegistry():
            silence(install_package, "auth")
            silence(uninstall_package, "auth")
            reg = load_registry()
            assert "auth" not in reg

    def test_uninstall_not_installed(self):
        with IsolatedRegistry():
            ok = silence(uninstall_package, "notinstalled")
            assert not ok

    def test_install_uninstall_reinstall(self):
        with IsolatedRegistry() as tmpdir:
            silence(install_package, "colors")
            silence(uninstall_package, "colors")
            ok = silence(install_package, "colors")
            assert ok
            assert os.path.exists(os.path.join(tmpdir, "colors.py"))


# ==============================================================
# SECTION 3 — Generated module code correctness
# ==============================================================

class TestModuleCodeGeneration:

    def _load_module(self, name):
        """Generate and exec a module, return load() dict."""
        code = _generate_module_code(name, BUILTIN_PACKAGES[name])
        ns   = {}
        exec(compile(code, f"{name}.py", "exec"), ns)
        return ns["load"]()

    def test_charts_bar_chart(self):
        fns = self._load_module("charts")
        assert "bar_chart" in fns
        result = fns["bar_chart"]([10, 20, 30])
        assert isinstance(result, str)
        assert "30" in result

    def test_charts_pie_chart(self):
        fns = self._load_module("charts")
        result = fns["pie_chart"]({"a": 50, "b": 50})
        assert "50.0%" in result

    def test_auth_hash_and_check(self):
        fns = self._load_module("auth")
        h = fns["hash_password"]("secret")
        assert ":" in h
        assert fns["check_password"]("secret", h) is True
        assert fns["check_password"]("wrong", h) is False

    def test_auth_token_length(self):
        fns = self._load_module("auth")
        tok = fns["generate_token"](16)
        assert len(tok) == 32   # 16 bytes = 32 hex chars

    def test_validation_email(self):
        fns = self._load_module("validation")
        assert fns["is_email"]("user@example.com") is True
        assert fns["is_email"]("notanemail") is False

    def test_validation_url(self):
        fns = self._load_module("validation")
        assert fns["is_url"]("https://example.com") is True
        assert fns["is_url"]("not a url") is False

    def test_validation_strong_password(self):
        fns = self._load_module("validation")
        assert fns["is_strong_password"]("Secure123") is True
        assert fns["is_strong_password"]("weak") is False

    def test_colors_red(self):
        fns = self._load_module("colors")
        result = fns["red"]("hello")
        assert "hello" in result
        assert "\033[" in result

    def test_random_int_in_range(self):
        fns = self._load_module("random")
        for _ in range(10):
            n = fns["random_int"](1, 10)
            assert 1 <= n <= 10

    def test_random_choice(self):
        fns = self._load_module("random")
        items = ["a", "b", "c"]
        result = fns["random_choice"](items)
        assert result in items

    def test_csv_write_read(self, tmp_path):
        fns  = self._load_module("csv")
        path = str(tmp_path / "test.csv")
        fns["csv_write"](path, [["a", "b"], ["1", "2"]], headers=["x", "y"])
        rows = fns["csv_read"](path)
        assert len(rows) == 2
        assert rows[0] == ["a", "b"]

    def test_csv_to_dict(self, tmp_path):
        fns  = self._load_module("csv")
        path = str(tmp_path / "dict.csv")
        fns["csv_write"](path, [["Alice", "30"]], headers=["name", "age"])
        data = fns["csv_to_dict"](path)
        assert data[0]["name"] == "Alice"
        assert data[0]["age"]  == "30"

    def test_csv_columns(self, tmp_path):
        fns  = self._load_module("csv")
        path = str(tmp_path / "cols.csv")
        fns["csv_write"](path, [], headers=["id", "name", "email"])
        cols = fns["csv_columns"](path)
        assert cols == ["id", "name", "email"]

    def test_slug_slugify(self):
        fns = self._load_module("slug")
        assert fns["slugify"]("Hello World!") == "hello-world"
        assert fns["slugify"]("  Spaces  and--dashes  ") == "spaces-and-dashes"

    def test_slug_truncate(self):
        fns = self._load_module("slug")
        assert fns["truncate"]("Hello World", 8) == "Hello..."
        assert fns["truncate"]("Short", 100) == "Short"

    def test_slug_word_count(self):
        fns = self._load_module("slug")
        assert fns["word_count"]("hello world foo") == 3

    def test_slug_capitalize_words(self):
        fns = self._load_module("slug")
        assert fns["capitalize_words"]("hello world") == "Hello World"

    def test_slug_strip_html(self):
        fns = self._load_module("slug")
        assert fns["strip_html"]("<b>hello</b> <i>world</i>") == "hello world"
        assert fns["strip_html"]("&amp; &lt;") == "& <"

    def test_sendmail_template_welcome(self):
        fns = self._load_module("sendmail")
        result = fns["email_template"](
            "welcome", {"app": "NEKOVA", "name": "Emmanuel"}
        )
        assert "NEKOVA" in result
        assert "Emmanuel" in result

    def test_sendmail_template_reset(self):
        fns = self._load_module("sendmail")
        result = fns["email_template"](
            "reset", {"name": "Emmanuel", "link": "https://x.com/reset"}
        )
        assert "https://x.com/reset" in result


# ==============================================================
# SECTION 4 — use <package> integration
# ==============================================================

class TestUsePackageIntegration:
    """Test that installed packages work via 'use <name>' in NEKOVA."""

    def _run(self, code: str) -> str:
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.interpreter.interpreter import Interpreter
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        interp = Interpreter()
        buf    = StringIO()
        sys.stdout = buf
        try:
            interp.execute(ast)
        finally:
            sys.stdout = sys.__stdout__
        return re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue()).strip()

    def test_use_auth(self):
        with IsolatedRegistry():
            silence(install_package, "auth")
            out = self._run(
                "use auth\n"
                "let h = hash_password(\"secret\")\n"
                "show check_password(\"secret\", h)"
            )
            assert out == "true"

    def test_use_validation(self):
        with IsolatedRegistry():
            silence(install_package, "validation")
            out = self._run(
                'use validation\n'
                'show is_email("user@example.com")'
            )
            assert out == "true"

    def test_use_slug(self):
        with IsolatedRegistry():
            silence(install_package, "slug")
            out = self._run(
                "use slug\n"
                'show slugify("Hello World!")'
            )
            assert out == "hello-world"

    def test_use_colors_bold(self):
        with IsolatedRegistry():
            silence(install_package, "colors")
            out = self._run(
                "use colors\n"
                'let b = bold("NEKOVA")\n'
                'show b'
            )
            assert "NEKOVA" in out

    def test_use_csv_write_read(self, tmp_path):
        with IsolatedRegistry():
            silence(install_package, "csv")
            # Use Python directly to write the file, then read from NEKOVA
            import csv as _csv
            path = str(tmp_path / "data.csv")
            with open(path, "w", newline="") as f:
                _csv.writer(f).writerows([["a", "b"], ["1", "2"]])
            path_fwd = path.replace("\\", "/")
            out = self._run(
                "use csv\n"
                f'let rows = csv_read("{path_fwd}", false)\n'
                "show rows[0][0]"
            )
            assert out == "a"

    def test_use_random_int(self):
        with IsolatedRegistry():
            silence(install_package, "random")
            out = self._run(
                "use random\n"
                "let n = random_int(1, 100)\n"
                "show n"
            )
            assert out.isdigit()
            assert 1 <= int(out) <= 100

    def test_use_slug_with_match(self):
        with IsolatedRegistry():
            silence(install_package, "slug")
            out = self._run(
                "use slug\n"
                'let s = slugify("Hello World")\n'
                'match s:\n'
                '    when "hello-world": show "correct"\n'
                '    else: show "wrong"'
            )
            assert out == "correct"


# ==============================================================
# SECTION 5 — publish / package bundling
# ==============================================================

class TestPublish:

    def test_publish_creates_nkpkg(self, tmp_path):
        from nekova.cli.package_manager import publish_package
        # Set up a minimal project
        (tmp_path / "nekova.toml").write_text(
            '[project]\nname = "test-app"\nversion = "1.0.0"\nauthor = "Test"\n'
            '[dependencies]\npackages = []\n',
            encoding="utf-8"
        )
        (tmp_path / "main.nk").write_text('show "hello"\n', encoding="utf-8")
        ok = silence(publish_package, str(tmp_path))
        assert ok
        pkg_files = list(tmp_path.glob("*.nkpkg"))
        assert len(pkg_files) == 1

    def test_publish_package_name(self, tmp_path):
        from nekova.cli.package_manager import publish_package
        (tmp_path / "nekova.toml").write_text(
            '[project]\nname = "my-lib"\nversion = "2.3.0"\nauthor = "Dev"\n'
            '[dependencies]\npackages = []\n',
            encoding="utf-8"
        )
        (tmp_path / "lib.nk").write_text('show "lib"\n', encoding="utf-8")
        silence(publish_package, str(tmp_path))
        pkg = list(tmp_path.glob("*.nkpkg"))[0]
        assert "my-lib" in pkg.name
        assert "2.3.0" in pkg.name

    def test_publish_contains_manifest(self, tmp_path):
        import zipfile
        from nekova.cli.package_manager import publish_package
        (tmp_path / "nekova.toml").write_text(
            '[project]\nname = "pkg"\nversion = "1.0.0"\nauthor = "A"\n'
            '[dependencies]\npackages = []\n',
            encoding="utf-8"
        )
        (tmp_path / "main.nk").write_text('show "hi"\n', encoding="utf-8")
        silence(publish_package, str(tmp_path))
        pkg = list(tmp_path.glob("*.nkpkg"))[0]
        with zipfile.ZipFile(str(pkg)) as zf:
            assert "manifest.json" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["name"] == "pkg"
            assert manifest["version"] == "1.0.0"

    def test_publish_contains_nk_files(self, tmp_path):
        import zipfile
        from nekova.cli.package_manager import publish_package
        (tmp_path / "nekova.toml").write_text(
            '[project]\nname = "app"\nversion = "1.0.0"\nauthor = "Dev"\n'
            '[dependencies]\npackages = []\n',
            encoding="utf-8"
        )
        (tmp_path / "main.nk").write_text('show "main"\n', encoding="utf-8")
        (tmp_path / "utils.nk").write_text('show "utils"\n', encoding="utf-8")
        silence(publish_package, str(tmp_path))
        pkg = list(tmp_path.glob("*.nkpkg"))[0]
        with zipfile.ZipFile(str(pkg)) as zf:
            nk_files = [n for n in zf.namelist() if n.endswith(".nk")]
            assert len(nk_files) == 2

    def test_publish_no_toml_fails(self, tmp_path):
        from nekova.cli.package_manager import publish_package
        ok = silence(publish_package, str(tmp_path))
        assert not ok