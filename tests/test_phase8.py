# =============================================================
# NEKOVA — Phase 8 Tests (Package Manager)
# =============================================================
# Run with: python tests/test_phase8.py

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.packages import (
    BUILTIN_PACKAGES, load_registry, save_registry,
    is_installed, get_available
)
from nekova.cli.package_manager import (
    install_package, uninstall_package
)
from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """Helper — run NEKOVA source and capture printed output."""
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


class TestPackageRegistry(unittest.TestCase):

    def test_builtin_packages_exist(self):
        self.assertIn("charts",     BUILTIN_PACKAGES)
        self.assertIn("auth",       BUILTIN_PACKAGES)
        self.assertIn("validation", BUILTIN_PACKAGES)
        self.assertIn("colors",     BUILTIN_PACKAGES)
        self.assertIn("random",     BUILTIN_PACKAGES)

    def test_package_has_required_fields(self):
        for name, pkg in BUILTIN_PACKAGES.items():
            self.assertIn("name",        pkg)
            self.assertIn("version",     pkg)
            self.assertIn("description", pkg)
            self.assertIn("functions",   pkg)

    def test_get_available_returns_dict(self):
        available = get_available()
        self.assertIsInstance(available, dict)
        self.assertGreater(len(available), 0)


class TestInstallUninstall(unittest.TestCase):

    def setUp(self):
        """Make sure test package is uninstalled before each test."""
        registry = load_registry()
        if "random" in registry:
            del registry["random"]
            save_registry(registry)

    def tearDown(self):
        """Clean up after each test."""
        registry = load_registry()
        if "random" in registry:
            del registry["random"]
            save_registry(registry)
        # Remove module file if exists
        pkg_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "packages", "random.py"
        )
        if os.path.exists(pkg_file):
            os.remove(pkg_file)

    def test_install_package(self):
        success = install_package("random")
        self.assertTrue(success)
        self.assertTrue(is_installed("random"))

    def test_install_unknown_package(self):
        success = install_package("nonexistent_package")
        self.assertFalse(success)

    def test_install_already_installed(self):
        install_package("random")
        # Installing again should succeed with warning
        success = install_package("random")
        self.assertTrue(success)

    def test_uninstall_package(self):
        install_package("random")
        success = uninstall_package("random")
        self.assertTrue(success)
        self.assertFalse(is_installed("random"))

    def test_uninstall_not_installed(self):
        success = uninstall_package("nonexistent_package")
        self.assertFalse(success)


class TestPackagesInNEKOVA(unittest.TestCase):

    def setUp(self):
        """Install packages needed for tests."""
        install_package("random")
        install_package("validation")
        install_package("auth")

    def tearDown(self):
        """Clean up installed packages."""
        for name in ["random", "validation", "auth"]:
            registry = load_registry()
            if name in registry:
                del registry[name]
                save_registry(registry)
            pkg_file = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))),
                "packages", f"{name}.py"
            )
            if os.path.exists(pkg_file):
                os.remove(pkg_file)

    def test_use_random_int(self):
        source = (
            "use random\n"
            "x = random_int(1, 10)\n"
            "show x"
        )
        output = run(source)
        self.assertTrue(output.isdigit())
        self.assertTrue(1 <= int(output) <= 10)

    def test_use_random_token(self):
        source = (
            "use random\n"
            "token = random_token(8)\n"
            "show token"
        )
        output = run(source)
        self.assertEqual(len(output.strip().split("\n")[-1]), 8)

    def test_use_validation_email(self):
        source = (
            "use validation\n"
            'show is_email("user@example.com")'
        )
        output = run(source)
        self.assertEqual(output.strip().split("\n")[-1], "true")

    def test_use_validation_invalid_email(self):
        source = (
            "use validation\n"
            'show is_email("notanemail")'
        )
        output = run(source)
        self.assertEqual(output.strip().split("\n")[-1], "false")

    def test_use_auth_token(self):
        source = (
            "use auth\n"
            "token = generate_token(16)\n"
            "show token"
        )
        output = run(source)
        token = output.strip().split("\n")[-1]
        self.assertEqual(len(token), 32)

    def test_use_auth_hash_and_check(self):
        source = (
            "use auth\n"
            'hashed = hash_password("mypassword")\n'
            'result = check_password("mypassword", hashed)\n'
            "show result"
        )
        output = run(source)
        self.assertEqual(output.strip().split("\n")[-1], "true")


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 8 — Package Manager Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)
    