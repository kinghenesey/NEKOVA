# =============================================================
# NEKOVA CLI — nekova classroom  (Phase 26b "Education Layer")
# =============================================================
# Batch-grades a directory of student .nk submissions against an
# expected output, and prints a pass/fail report.
#
# Directory convention (deliberately simple — a folder an
# instructor can set up by hand in under a minute):
#
#   assignment/
#     solution.nk        <- optional instructor reference; if
#                            present, its actual stdout (run
#                            through the real interpreter) becomes
#                            the expected output automatically.
#     expected.txt        <- optional; used instead of solution.nk,
#                            or when solution.nk isn't provided.
#                            Exact expected stdout.
#     students/
#       alice.nk
#       bob.nk
#       ...
#
# Each submission is run in its own subprocess with a timeout, so
# one student's infinite loop can't hang the whole grading run —
# same reasoning as the sandbox for AI-generated code.
# =============================================================

import io
import os
import signal
import contextlib

from nekova.config import Color
from nekova.cli import print_error, print_info


DEFAULT_TIMEOUT_SECONDS = 10


class _GradingTimeout(Exception):
    pass


def _run_submission(filepath: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
    """
    Run one .nk file in-process and capture only the program's own
    stdout — not the runner's decorative "-> Running..." header or
    "Done in Xms" footer, since that timing text would never
    byte-match between two runs even of identical code.

    NEKOVA's own interpreter already guards against runaway loops
    (raises a runtime error after too many iterations — see
    error_display's catalogue), but a SIGALRM timeout is layered
    on top as a backstop against anything that guard doesn't catch
    (e.g. a genuinely slow but finite computation), so one
    submission can never hang the whole grading run.

    Returns (stdout: str, timed_out: bool, crashed: bool).
    """
    from nekova.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter

    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    def _on_alarm(signum, frame):
        raise _GradingTimeout()

    old_handler = None
    have_alarm = hasattr(signal, "SIGALRM")
    if have_alarm:
        old_handler = signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(timeout)

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            tokens = Lexer(source).tokenize()
            program = Parser(tokens).parse()
            interpreter = Interpreter()
            interpreter.execute(program, filepath=os.path.abspath(filepath))
        return buf.getvalue(), False, False
    except _GradingTimeout:
        return buf.getvalue(), True, False
    except Exception as e:
        return buf.getvalue(), False, True
    finally:
        if have_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def _normalize(output: str) -> str:
    """Trailing whitespace and line-ending differences shouldn't
    fail a submission that's otherwise byte-for-byte correct."""
    return "\n".join(line.rstrip() for line in output.strip().splitlines())


def grade_directory(dirpath: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
    """
    Grade every submission under dirpath/students/ (or, if there's
    no students/ subfolder, every *.nk file directly in dirpath
    other than solution.nk).

    Returns a dict:
      {
        "expected": str,
        "expected_source": "solution.nk" | "expected.txt" | None,
        "results": [ {"name": str, "path": str, "passed": bool,
                       "timed_out": bool, "crashed": bool,
                       "output": str}, ... ],
      }
    Raises FileNotFoundError if dirpath doesn't exist, and
    ValueError if neither solution.nk nor expected.txt is present
    (grading needs *something* to compare against).
    """
    if not os.path.isdir(dirpath):
        raise FileNotFoundError(f"Directory not found: '{dirpath}'")

    solution_path = os.path.join(dirpath, "solution.nk")
    expected_txt_path = os.path.join(dirpath, "expected.txt")

    expected = None
    expected_source = None
    if os.path.isfile(solution_path):
        stdout, timed_out, crashed = _run_submission(solution_path, timeout)
        if timed_out or crashed:
            raise ValueError(
                f"solution.nk itself failed to run cleanly — fix the "
                f"reference solution before grading students against it."
            )
        expected = _normalize(stdout)
        expected_source = "solution.nk"
    elif os.path.isfile(expected_txt_path):
        with open(expected_txt_path, "r", encoding="utf-8") as f:
            expected = _normalize(f.read())
        expected_source = "expected.txt"
    else:
        raise ValueError(
            "No 'solution.nk' or 'expected.txt' found — classroom "
            "grading needs one of these to know what a correct "
            "submission looks like."
        )

    students_dir = os.path.join(dirpath, "students")
    if os.path.isdir(students_dir):
        submissions = sorted(
            os.path.join(students_dir, f)
            for f in os.listdir(students_dir) if f.endswith(".nk")
        )
    else:
        submissions = sorted(
            os.path.join(dirpath, f)
            for f in os.listdir(dirpath)
            if f.endswith(".nk") and f != "solution.nk"
        )

    results = []
    for path in submissions:
        name = os.path.splitext(os.path.basename(path))[0]
        stdout, timed_out, crashed = _run_submission(path, timeout)
        passed = (not timed_out and not crashed
                  and _normalize(stdout) == expected)
        results.append({
            "name": name, "path": path, "passed": passed,
            "timed_out": timed_out, "crashed": crashed, "output": stdout,
        })

    return {
        "expected": expected,
        "expected_source": expected_source,
        "results": results,
    }


def cmd_classroom(dirpath: str) -> bool:
    """CLI entry point for `nekova classroom <dir>`."""
    try:
        report = grade_directory(dirpath)
    except FileNotFoundError as e:
        print_error(str(e))
        return False
    except ValueError as e:
        print_error(str(e))
        return False

    results = report["results"]
    if not results:
        print_info(f"No student submissions found under "
                    f"'{dirpath}/students/' (or as loose .nk files).")
        return True

    print(f"\n{Color.CYAN}{Color.BOLD}Classroom Report{Color.RESET}")
    print(f"{Color.DIM}Graded against: {report['expected_source']}"
          f"{Color.RESET}\n")

    passed_count = 0
    for r in results:
        if r["passed"]:
            passed_count += 1
            print(f"  {Color.GREEN}✓ PASS{Color.RESET}  {r['name']}")
        elif r["timed_out"]:
            print(f"  {Color.RED}✗ FAIL{Color.RESET}  {r['name']} "
                  f"{Color.DIM}(timed out — possible infinite "
                  f"loop){Color.RESET}")
        elif r["crashed"]:
            print(f"  {Color.RED}✗ FAIL{Color.RESET}  {r['name']} "
                  f"{Color.DIM}(errored — run 'nekova explain "
                  f"{r['path']}' for details){Color.RESET}")
        else:
            print(f"  {Color.RED}✗ FAIL{Color.RESET}  {r['name']} "
                  f"{Color.DIM}(output didn't match){Color.RESET}")

    print(f"\n{Color.CYAN}{Color.BOLD}{passed_count}/{len(results)} "
          f"passed{Color.RESET}\n")
    return True