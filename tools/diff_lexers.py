#!/usr/bin/env python3
"""
tools/diff_lexers.py

Diffs the Python reference lexer (nekova/lexer/lexer.py) against the
self-hosted NEKOVA lexer (nekova/stdlib/nk/lexer.nk) on the same
source file, so Phase 20 correctness isn't judged on unit tests alone.

Usage:
    python tools/diff_lexers.py <path/to/file.nk>

If no path is given, it defaults to a bundled sample that exercises
strings, f-strings, numbers (hex/float/sci/underscore), keywords,
multi-line brackets, and indentation.
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_LINK = REPO_ROOT / "tools" / "diff_target.nk"
NK_TOKENS_OUT = REPO_ROOT / "tools" / "nk_tokens.json"

DEFAULT_SAMPLE = '''\
# sample exercising a broad slice of lexer behaviour
let name = "Emmanuel"
let pi = 3.141_592
let mask = 0xFF
let avogadro = 6.022e23

task greet(who: str) -> str:
    let msg = f"Hello, {who}!"
    return msg

shape User:
    name str
    age  int = 0

let data = {
    "a": 1,
    "b": [1, 2, 3],
}

match mask:
    when 0x00: show "zero"
    when 0xFF: show "full"

every 5 s:
    think "ping" as text
'''


def run_python_lexer(source: str):
    from nekova.lexer.lexer import Lexer

    tokens = Lexer(source).tokenize()
    out = []
    for t in tokens:
        # Normalize to plain dict — exact attribute names vary by
        # Token implementation, so pull the four fields we care about.
        out.append({
            "type": t.type.name if hasattr(t.type, "name") else str(t.type),
            "value": t.value,
            "line": t.line,
            "column": t.column,
        })
    return out


def run_nekova_lexer(source: str):
    TARGET_LINK.write_text(source, encoding="utf-8")
    if NK_TOKENS_OUT.exists():
        NK_TOKENS_OUT.unlink()

    # Always run against the local repo's main.py, not a globally
    # pip-installed `nekova` command — a global install can be a
    # stale, separate copy that doesn't have the .nk file you're
    # actively editing, even if its reported version matches.
    cmd = [sys.executable, "main.py", "tools/nk_tokenize.nk"]

    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=child_env,
    )
    if result.returncode != 0:
        print("--- NEKOVA harness failed ---")
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        sys.exit(1)

    if not NK_TOKENS_OUT.exists():
        print("NEKOVA harness ran but produced no tools/nk_tokens.json")
        print("stdout:", result.stdout)
        sys.exit(1)

    return json.loads(NK_TOKENS_OUT.read_text(encoding="utf-8"))


def diff_tokens(py_tokens, nk_tokens):
    mismatches = []
    max_len = max(len(py_tokens), len(nk_tokens))

    for i in range(max_len):
        py_t = py_tokens[i] if i < len(py_tokens) else None
        nk_t = nk_tokens[i] if i < len(nk_tokens) else None

        if py_t is None:
            mismatches.append((i, None, nk_t, "NEKOVA lexer emitted an extra token"))
            continue
        if nk_t is None:
            mismatches.append((i, py_t, None, "NEKOVA lexer is missing a token"))
            continue

        if py_t["type"] != nk_t["type"] or py_t["value"] != nk_t["value"]:
            mismatches.append((i, py_t, nk_t, "type/value mismatch"))

    return mismatches


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        source = path.read_text(encoding="utf-8")
        label = str(path)
    else:
        source = DEFAULT_SAMPLE
        label = "<bundled default sample>"

    print(f"Diffing lexers on: {label}\n")

    py_tokens = run_python_lexer(source)
    nk_tokens = run_nekova_lexer(source)

    print(f"Python lexer:  {len(py_tokens)} tokens")
    print(f"NEKOVA lexer:  {len(nk_tokens)} tokens\n")

    mismatches = diff_tokens(py_tokens, nk_tokens)

    if not mismatches:
        print("MATCH — token streams are identical.")
        return

    print(f"MISMATCH — {len(mismatches)} difference(s):\n")
    for i, py_t, nk_t, reason in mismatches[:40]:
        print(f"  [{i}] {reason}")
        print(f"      python: {py_t}")
        print(f"      nekova: {nk_t}")
    if len(mismatches) > 40:
        print(f"  ... and {len(mismatches) - 40} more")

    sys.exit(1)


if __name__ == "__main__":
    main()