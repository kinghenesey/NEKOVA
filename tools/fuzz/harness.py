#!/usr/bin/env python3
# =============================================================
# NEKOVA — Fuzz Harness  (Phase 27 prerequisite)
# =============================================================
# Feeds generator+mutator output through the real Lexer and Parser,
# classifies every result, and saves anything that crashes
# ungracefully as a permanent regression test input.
#
# A NEKOVA LexerError or ParseError is a SUCCESS for this harness —
# it means malformed input was rejected the way it's supposed to be.
# Anything else escaping (IndexError, AttributeError, a raw Python
# traceback, RecursionError past a sane guard, or a hang) is a
# FAILURE — the parser crashed ungracefully instead of raising a
# clean, expected error.
#
# Usage:
#   python3 tools/fuzz/harness.py                    # default budget
#   python3 tools/fuzz/harness.py --iterations 5000
#   python3 tools/fuzz/harness.py --seconds 60
#   python3 tools/fuzz/harness.py --replay-regressions   # replay only
# =============================================================

import argparse
import hashlib
import os
import random
import signal
import sys
import time
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
FUZZ_DIR = os.path.dirname(os.path.abspath(__file__))
REGRESSIONS_DIR = os.path.join(FUZZ_DIR, "regressions")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if FUZZ_DIR not in sys.path:
    sys.path.insert(0, FUZZ_DIR)

from generator import generate_program
from mutator import mutate

from nekova.lexer import Lexer
from nekova.lexer.lexer import LexerError
from nekova.parser.parser import Parser, ParseError


class _FuzzTimeout(Exception):
    pass


def _run_one(source: str, timeout_seconds: int = 3):
    """
    Feed one source string through Lexer -> Parser.
    Returns one of: "valid", "rejected", "crash", "timeout".
    On crash, also returns (exc_type_name, exc_message, traceback_text).
    """
    have_alarm = hasattr(signal, "SIGALRM")
    old_handler = None
    if have_alarm:
        def _on_alarm(signum, frame):
            raise _FuzzTimeout()
        old_handler = signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(timeout_seconds)

    try:
        tokens = Lexer(source).tokenize()
        Parser(tokens).parse()
        return ("valid", None)
    except (LexerError, ParseError):
        return ("rejected", None)
    except _FuzzTimeout:
        return ("timeout", None)
    except Exception as e:
        tb = traceback.format_exc()
        return ("crash", (type(e).__name__, str(e), tb))
    finally:
        if have_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def _save_regression(source: str, mutations: list, crash_info):
    os.makedirs(REGRESSIONS_DIR, exist_ok=True)
    digest = hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()[:16]
    path = os.path.join(REGRESSIONS_DIR, f"crash_{digest}.nk")
    exc_type, exc_message, tb = crash_info
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# FUZZ REGRESSION — {exc_type}: {exc_message}\n")
        f.write(f"# mutations applied: {mutations}\n")
        f.write("# --- source below ---\n")
        f.write(source)
    return path


def run_campaign(iterations=None, seconds=None, seed=None, verbose=True):
    """
    Run a fuzzing campaign. Stops after `iterations` iterations or
    `seconds` wall-clock time, whichever comes first (at least one
    of the two must be given). Returns a summary dict.
    """
    if iterations is None and seconds is None:
        iterations = 1000

    if seed is not None:
        random.seed(seed)

    counts = {"valid": 0, "rejected": 0, "crash": 0, "timeout": 0}
    crashes = []
    start = time.time()
    i = 0

    while True:
        if iterations is not None and i >= iterations:
            break
        if seconds is not None and (time.time() - start) >= seconds:
            break
        i += 1

        base = generate_program()
        num_mutations = random.choice([0, 1, 1, 2, 3])  # weight toward 1
        if num_mutations == 0:
            source, mutations = base, []
        else:
            source, mutations = mutate(base, num_mutations)

        result, info = _run_one(source)
        counts[result] += 1

        if result == "crash":
            path = _save_regression(source, mutations, info)
            crashes.append({
                "path": path, "mutations": mutations,
                "exc_type": info[0], "exc_message": info[1],
            })
            if verbose:
                print(f"[CRASH] {info[0]}: {info[1]}  -> saved to {path}")
        elif result == "timeout" and verbose:
            print(f"[TIMEOUT] mutations={mutations}")

    elapsed = time.time() - start
    if verbose:
        print()
        print(f"Ran {i} iterations in {elapsed:.1f}s")
        print(f"  valid={counts['valid']} rejected={counts['rejected']} "
              f"crash={counts['crash']} timeout={counts['timeout']}")
        if crashes:
            print(f"\n{len(crashes)} crash(es) found — regression files "
                  f"saved under {REGRESSIONS_DIR}")

    return {"iterations": i, "elapsed": elapsed, "counts": counts,
            "crashes": crashes}


def replay_regressions(verbose=True):
    """
    Replay every saved regression file — used both standalone and
    by tests/test_fuzz_regressions.py to make sure a previously
    found crash stays fixed. Returns (passed_count, failed_list).
    """
    if not os.path.isdir(REGRESSIONS_DIR):
        if verbose:
            print("No regressions directory — nothing to replay.")
        return 0, []

    files = sorted(f for f in os.listdir(REGRESSIONS_DIR) if f.endswith(".nk"))
    passed = 0
    failed = []

    for fname in files:
        path = os.path.join(REGRESSIONS_DIR, fname)
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Strip the leading '# FUZZ REGRESSION ...' header comments
        lines = content.splitlines()
        source_lines = []
        in_header = True
        for line in lines:
            if in_header and line.startswith("#"):
                continue
            in_header = False
            source_lines.append(line)
        source = "\n".join(source_lines)

        result, info = _run_one(source)
        if result in ("valid", "rejected"):
            passed += 1
        else:
            failed.append((fname, result, info))
            if verbose:
                print(f"[STILL FAILING] {fname}: {result} {info}")

    if verbose:
        print(f"Replayed {len(files)} regression(s): "
              f"{passed} clean, {len(failed)} still failing.")

    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="NEKOVA fuzz harness")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--replay-regressions", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.replay_regressions:
        _, failed = replay_regressions(verbose=not args.quiet)
        sys.exit(1 if failed else 0)

    result = run_campaign(
        iterations=args.iterations, seconds=args.seconds,
        seed=args.seed, verbose=not args.quiet,
    )
    sys.exit(1 if result["counts"]["crash"] else 0)


if __name__ == "__main__":
    main()