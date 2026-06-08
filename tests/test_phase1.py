# =============================================================
# NEKOVA — Phase 1 Tests
# =============================================================
# Run with: python tests/test_phase1.py

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NEKOVA_VERSION, NEKOVA_EXTENSION, Color
from runner import NEKOVARunner


class TestConfig(unittest.TestCase):

    def test_version_format(self):
        parts = NEKOVA_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_extension(self):
        self.assertTrue(NEKOVA_EXTENSION.startswith("."))

    def test_colors_are_strings(self):
        for name in ("RESET", "BOLD", "RED", "GREEN", "CYAN"):
            value = getattr(Color, name)
            self.assertIsInstance(value, str)
            self.assertGreater(len(value), 0)


class TestRunner(unittest.TestCase):

    def _make_temp_aion(self, content: str = 'show "test"') -> str:
        fd, path = tempfile.mkstemp(suffix=".aion")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def test_missing_file(self):
        runner = NEKOVARunner("/nonexistent/path/app.aion")
        code = runner.run()
        self.assertEqual(code, 1)

    def test_wrong_extension(self):
        runner = NEKOVARunner("script.py")
        code = runner.run()
        self.assertEqual(code, 1)

    def test_valid_file_loads(self):
        path = self._make_temp_aion('show "Hello NEKOVA"')
        try:
            runner = NEKOVARunner(path, debug=False)
            code = runner.run()
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = self._make_temp_aion("")
        try:
            runner = NEKOVARunner(path, debug=False)
            code = runner.run()
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 1 — Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)
    