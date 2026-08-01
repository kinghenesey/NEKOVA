#!/usr/bin/env python3
"""
tools/diff_parsers.py

Diffs the Python reference parser (nekova/parser/parser.py) against
the self-hosted NEKOVA parser (nekova/stdlib/nk/parser.nk) on the
same source file — the Phase 27 counterpart to diff_lexers.py.

Both sides are canonicalized to plain dicts/lists before comparing:
  - Python AST nodes -> {"type": ClassName, <every self.attr>: ...}
    via a generic vars()-based walk (no per-class mapping to maintain
    by hand — new node classes are picked up automatically).
  - NEKOVA's dict-shaped nodes are used as-is.
  - "line" is stripped from both sides recursively before comparing:
    parser.nk doesn't promise line-for-line fidelity with parser.py's
    stamping, and it isn't part of what makes two ASTs the same
    program — only the structural fields are.

Diffing strategy: whenever two nodes agree on "type" but disagree on
which *keys* they carry, that's reported once per distinct
(node type, mismatched keys) pattern — not once per occurrence in the
tree, which for a systemic field-naming difference (e.g. every
BinaryOp in the file) would otherwise bury the one real finding under
hundreds of identical-looking lines. Genuine value differences (same
keys, different content) are still reported per-occurrence, with a
JSON path, since those are usually distinct bugs rather than one
repeated pattern.

Usage:
    python tools/diff_parsers.py <path/to/file.nk>

If no path is given, defaults to a bundled sample exercising a broad
slice of grammar across every layer.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_LINK = REPO_ROOT / "tools" / "parse_target.nk"
NK_AST_OUT = REPO_ROOT / "tools" / "nk_ast.json"

DEFAULT_SAMPLE = '''\
# sample exercising a broad slice of parser behaviour across layers
let name = "Emmanuel"
const PI = 3.14159
let scores = [1, 2, 3, ...more]
let user = {"name": "Sam", "age": 21}

task add(a: int, b: int = 2) -> int:
    return a + b

if scores[0] > 1 and PI != 0:
    show "big"
elif PI == 0:
    show "zero"
else:
    show "small"

while add(1, 2) < 5:
    break

for x in scores:
    show x

try:
    risky()
catch err:
    show err

shape User:
    name str
    age int = 0

let summary = think "summarize this" as json using "claude-sonnet" with budget: 500

sandbox strict:
    do_something()

test "basic math":
    expect 1 + 1 == 2

remember "key" = "value"
let x = recall "key" or "default"

speak "hi"
converse:
    let reply = listen

object Person:
    name: text

    init(name: text):
        self.name = name

    func greet():
        return f"Hi, I'm {self.name}"

let p = new Person("Emmanuel")

match PI:
    when 0: show "zero"
    else: show "nonzero"

async func compute(a, b=5):
    return a + b

@log
task audited():
    return 1
'''


# ── Python side: generic Node -> dict serializer ────────────────────

def serialize(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): serialize(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        d = {"type": obj.__class__.__name__}
        for k, v in vars(obj).items():
            if k == "line":
                continue
            d[k] = serialize(v)
        return d
    # Enum-like or anything else with no __dict__
    return getattr(obj, "name", str(obj))


def strip_line(node):
    """Belt-and-braces: recursively drop any leftover 'line' keys."""
    if isinstance(node, dict):
        return {k: strip_line(v) for k, v in node.items() if k != "line"}
    if isinstance(node, list):
        return [strip_line(x) for x in node]
    return node


def run_python_parser(source: str):
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return strip_line(serialize(program))


def run_nekova_parser(source: str):
    TARGET_LINK.write_text(source, encoding="utf-8")
    if NK_AST_OUT.exists():
        NK_AST_OUT.unlink()

    cmd = [sys.executable, "main.py", "tools/nk_parse.nk"]
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

    if not NK_AST_OUT.exists():
        print("NEKOVA harness ran but produced no tools/nk_ast.json")
        print("stdout:", result.stdout)
        sys.exit(1)

    statements = json.loads(NK_AST_OUT.read_text(encoding="utf-8"))
    return strip_line({"type": "Program", "statements": statements})


# ── Diffing ──────────────────────────────────────────────────────────

class DiffReport:
    def __init__(self):
        self.field_mismatches = {}   # (type, extra_keys, missing_keys) -> example path
        self.value_mismatches = []   # (path, reason, py_val, nk_val)
        self.type_mismatches = []    # (path, py_type, nk_type)

    def any(self):
        return bool(self.field_mismatches or self.value_mismatches or self.type_mismatches)


def compare(py, nk, path, report: DiffReport):
    if isinstance(py, dict) and isinstance(nk, dict):
        py_type = py.get("type")
        nk_type = nk.get("type")

        if py_type != nk_type:
            report.type_mismatches.append((path, py_type, nk_type))
            return

        py_keys = set(py.keys())
        nk_keys = set(nk.keys())
        if py_keys != nk_keys:
            extra = tuple(sorted(nk_keys - py_keys))
            missing = tuple(sorted(py_keys - nk_keys))
            key = (py_type, extra, missing)
            if key not in report.field_mismatches:
                report.field_mismatches[key] = path
            # Still compare the keys both sides agree on, so a field
            # mismatch on one key doesn't hide a real value bug on
            # a sibling key.
            for k in py_keys & nk_keys:
                compare(py[k], nk[k], f"{path}.{k}", report)
            return

        for k in py_keys:
            compare(py[k], nk[k], f"{path}.{k}", report)
        return

    if isinstance(py, list) and isinstance(nk, list):
        if len(py) != len(nk):
            report.value_mismatches.append(
                (path, f"list length {len(py)} vs {len(nk)}", py, nk))
            n = min(len(py), len(nk))
        else:
            n = len(py)
        for i in range(n):
            compare(py[i], nk[i], f"{path}[{i}]", report)
        return

    if py != nk:
        report.value_mismatches.append((path, "value mismatch", py, nk))


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        source = path.read_text(encoding="utf-8")
        label = str(path)
    else:
        source = DEFAULT_SAMPLE
        label = "<bundled default sample>"

    print(f"Diffing parsers on: {label}\n")

    py_ast = run_python_parser(source)
    nk_ast = run_nekova_parser(source)

    py_count = len(py_ast.get("statements", []))
    nk_count = len(nk_ast.get("statements", []))
    print(f"Python parser:  {py_count} top-level statements")
    print(f"NEKOVA parser:  {nk_count} top-level statements\n")

    report = DiffReport()
    compare(py_ast, nk_ast, "Program", report)

    if not report.any():
        print("MATCH — ASTs are structurally identical (ignoring line numbers).")
        return

    if report.type_mismatches:
        print(f"TYPE MISMATCHES — {len(report.type_mismatches)}:")
        for path, py_t, nk_t in report.type_mismatches[:20]:
            print(f"  [{path}] python={py_t!r}  nekova={nk_t!r}")
        print()

    if report.field_mismatches:
        print(f"FIELD-NAME MISMATCHES — {len(report.field_mismatches)} distinct pattern(s):")
        for (node_type, extra, missing), example_path in report.field_mismatches.items():
            print(f"  {node_type}:")
            if missing:
                print(f"      python has, nekova is missing: {list(missing)}")
            if extra:
                print(f"      nekova has extra (unexpected):  {list(extra)}")
            print(f"      example: {example_path}")
        print()

    if report.value_mismatches:
        print(f"VALUE MISMATCHES — {len(report.value_mismatches)} (showing up to 30):")
        for path, reason, py_v, nk_v in report.value_mismatches[:30]:
            print(f"  [{path}] {reason}")
            print(f"      python: {py_v!r}")
            print(f"      nekova: {nk_v!r}")
        if len(report.value_mismatches) > 30:
            print(f"  ... and {len(report.value_mismatches) - 30} more")
        print()

    sys.exit(1)


if __name__ == "__main__":
    main()