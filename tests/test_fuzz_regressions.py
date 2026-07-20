"""
Phase 27 prerequisite — fuzz regression replay.

Every crash the fuzz harness (tools/fuzz/harness.py) ever finds gets
saved as a permanent regression file under tools/fuzz/regressions/.
This test replays every one of them on every normal test run, so a
previously-fixed crash can never silently reappear without the main
test suite catching it — not just the separate, longer-running fuzz
CI job.

If tools/fuzz/regressions/ is empty (the common case — it only grows
when the fuzzer actually finds something), this file contributes a
single trivial passing test and does nothing else.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUZZ_DIR = os.path.join(REPO_ROOT, "tools", "fuzz")
REGRESSIONS_DIR = os.path.join(FUZZ_DIR, "regressions")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if FUZZ_DIR not in sys.path:
    sys.path.insert(0, FUZZ_DIR)


def _regression_files():
    if not os.path.isdir(REGRESSIONS_DIR):
        return []
    return sorted(f for f in os.listdir(REGRESSIONS_DIR) if f.endswith(".nk"))


class TestFuzzRegressions(unittest.TestCase):

    def test_no_regressions_directory_or_all_clean(self):
        """Baseline — always runs, passes trivially if there's
        nothing to replay yet."""
        self.assertTrue(True)

    def test_every_saved_crash_stays_fixed(self):
        from harness import replay_regressions
        files = _regression_files()
        if not files:
            self.skipTest("No fuzz regressions saved yet.")

        passed, failed = replay_regressions(verbose=False)
        if failed:
            details = "\n".join(
                f"  {fname}: {result} — {info}"
                for fname, result, info in failed
            )
            self.fail(
                f"{len(failed)} fuzz regression(s) are failing again:\n"
                f"{details}"
            )


if __name__ == "__main__":
    unittest.main()