# =============================================================
# NEKOVA CLI — Error Display  (Phase 5A)
# =============================================================
# Rust-style error output: source context, caret underline,
# did-you-mean suggestions, pepper-red SYNEKCOT branding.
#
# Output example:
#
#   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   error[NameError]: Variable Not Found
#    --> src/main.nk:4:6
#   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#    2 │  let age: number = 25
#    3 │  show f"Hello {name}"
#    4 │  show unknown_var
#         ^^^^^^^^^^^^ variable not defined
#   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   💡 Did you mean: name ?
#   🔧 Add before line 4:  unknown_var = "your value here"
#   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import re
import os
import difflib
import traceback

# ── NEKOVA brand colours (ANSI 256 approximations) ───────────
# Pepper red  #C41E0E  → ANSI 196 / escape: \x1b[38;5;196m
# Forged gold #D4940A  → ANSI 172 / escape: \x1b[38;5;172m

_RED    = "\x1b[38;5;196m"   # pepper red
_GOLD   = "\x1b[38;5;172m"   # forged gold
_CYAN   = "\x1b[96m"
_WHITE  = "\x1b[97m"
_DIM    = "\x1b[2m"
_BOLD   = "\x1b[1m"
_RESET  = "\x1b[0m"
_UNDER  = "\x1b[4m"

_WIDTH  = 56


# ── Error catalogue ───────────────────────────────────────────

_CATALOGUE = {
    "NameError": {
        "code":    "E001",
        "title":   "Variable Not Found",
        "hint":    "This variable was used before it was defined.",
        "example": "Define it first:  let {var} = \"value\"",
    },
    "SyntaxError": {
        "code":    "E002",
        "title":   "Syntax Error",
        "hint":    "NEKOVA couldn't read this line.",
        "example": "Check for missing quotes, colons, or brackets.",
    },
    "ParseError": {
        "code":    "E003",
        "title":   "Parse Error",
        "hint":    "NEKOVA couldn't understand the code structure.",
        "example": "Check your indentation and block structure.",
    },
    "TypeError": {
        "code":    "E004",
        "title":   "Type Error",
        "hint":    "A value has the wrong type for this operation.",
        "example": "Use 'let x: any = value' to allow mixed types.",
    },
    "RuntimeError": {
        "code":    "E005",
        "title":   "Runtime Error",
        "hint":    "Something went wrong while running your program.",
        "example": "Check the values your variables hold.",
    },
    "ZeroDivisionError": {
        "code":    "E006",
        "title":   "Division By Zero",
        "hint":    "You cannot divide a number by zero.",
        "example": "Guard with:  if divisor != 0: result = a / divisor",
    },
    "ImportError": {
        "code":    "E007",
        "title":   "Module Not Found",
        "hint":    "This module doesn't exist in NEKOVA's stdlib.",
        "example": "Available: math, text, files, datetime, collections, ai, web",
    },
    "IndexError": {
        "code":    "E008",
        "title":   "Index Out of Range",
        "hint":    "You're accessing a list position that doesn't exist.",
        "example": "Check length first:  if i < list.length: ...",
    },
    "KeyError": {
        "code":    "E009",
        "title":   "Key Not Found",
        "hint":    "This key doesn't exist in the dictionary.",
        "example": "Check available keys with dict.keys()",
    },
    "RecursionError": {
        "code":    "E010",
        "title":   "Maximum Call Depth Exceeded",
        "hint":    "A task called itself too many times. This is usually "
                   "a missing or incorrect base case — but very deep, "
                   "legitimate recursion can also hit this limit.",
        "example": "Check your base case, or rewrite as a loop if the "
                   "recursion is intentionally deep.",
    },
    "KeywordConflict": {
        "code":    "E011",
        "title":   "Reserved Keyword Used as Name",
        "hint":    "This word is reserved by NEKOVA and cannot be a variable or task name.",
        "example": "Rename it (e.g. add _fn or my_ prefix).",
    },
    "UnreachableCode": {
        "code":    "W006",
        "title":   "Unreachable Code",
        "hint":    "Code after a return statement will never execute.",
        "example": "Remove the dead code or move it before the return.",
    },
    "ShadowedBuiltin": {
        "code":    "W005",
        "title":   "Built-in Name Shadowed",
        "hint":    "This name overwrites a built-in NEKOVA function.",
        "example": "Rename to avoid conflicts.",
    },
}


# ── Public API ────────────────────────────────────────────────

def display_error(
    error_type: str,
    message:    str,
    source:     str  = "",
    filepath:   str  = "",
    line:       int  = 0,
    col:        int  = 0,
    variables:  dict = None,
    why:        bool = False,
    exception:  Exception = None,
    simple:     bool = False,
):
    """
    Render a Rust-style NEKOVA error to stdout.

    Parameters
    ----------
    error_type  Python exception class name  ("NameError", "TypeError" …)
    message     Raw exception message string
    source      Full source text of the file being run
    filepath    Path to the source file
    line        1-based line number of the error (0 = unknown)
    col         1-based column number (0 = unknown)
    variables   Dict of currently-defined variables (for did-you-mean)
    why         If True (--why flag), append a section naming the
                actual internal function/line that raised this —
                which grammar rule or interpreter check fired.
    exception   The original exception object, needed to walk its
                traceback for the `why` section above. Ignored if
                why=False.
    simple      If True (--simple-errors flag, Phase 26b), strips
                jargon entirely: no error code, no "E005"-style
                catalogue label, no "--> file:line" arrow, no --why
                section even if why=True. Just the source line, a
                caret, and the hint in plain sentences — aimed at
                a classroom/beginner audience who don't need (and
                are often confused by) the full Rust-style card.
    """
    if simple:
        _display_error_simple(error_type, message, source, filepath,
                               line, col, variables)
        return

    info = _CATALOGUE.get(error_type, {
        "code":    "E000",
        "title":   error_type,
        "hint":    "An unexpected error occurred.",
        "example": "Review the line shown above.",
    })

    # Auto-detect line/col from message if not supplied
    if not line:
        line, col = _extract_location(message)

    # ── Header ────────────────────────────────────────────────
    print()
    _hr()
    print(f"{_RED}{_BOLD}  error[{info['code']}]: {info['title']}{_RESET}")
    if filepath and line:
        short = _shorten(filepath)
        loc   = f"{short}:{line}" + (f":{col}" if col else "")
        print(f"{_DIM}   --> {loc}{_RESET}")
    elif line:
        print(f"{_DIM}   --> line {line}{_RESET}")
    _hr()

    # ── Source context with caret ─────────────────────────────
    if source and line:
        _render_source(source, line, col, message)

    # ── Error message ─────────────────────────────────────────
    clean = _clean(message)
    print()
    print(f"  {_RED}✗  {_WHITE}{_BOLD}{clean}{_RESET}")

    # ── Did you mean? ─────────────────────────────────────────
    if variables:
        var = _extract_token(message)
        if var:
            suggestions = _did_you_mean(var, list(variables.keys()))
            if suggestions:
                print()
                print(f"  {_GOLD}💡 Did you mean:{_RESET}")
                for s in suggestions:
                    print(f"     {_CYAN}{s}{_RESET}")

    # ── Hint ──────────────────────────────────────────────────
    hint = info["hint"]
    example = info["example"]
    # Substitute {var} in example if we have a token
    var = _extract_token(message)
    if var and "{var}" in example:
        example = example.replace("{var}", var)

    print()
    print(f"  {_GOLD}💡 {hint}{_RESET}")
    print(f"  {_DIM}   {example}{_RESET}")

    # ── Quick fix ─────────────────────────────────────────────
    fix = _quick_fix(error_type, message, line, col)
    if fix:
        print()
        print(f"  {_CYAN}🔧 {fix}{_RESET}")

    # ── Why (--why flag) ───────────────────────────────────────
    if why:
        origin = _find_why_origin(exception) if exception is not None else None
        print()
        if origin:
            print(f"  {_CYAN}💭 Why:{_RESET} {origin}")
        else:
            print(f"  {_CYAN}💭 Why:{_RESET} {_DIM}"
                  f"No internal NEKOVA source frame found in the "
                  f"traceback for this error.{_RESET}")

    _hr()
    print()


def _display_error_simple(error_type, message, source, filepath,
                          line, col, variables):
    """
    The --simple-errors rendering: plain sentences, no jargon.
    Deliberately does not reuse the Rust-style card layout at all
    (no box-drawing header, no error code) rather than just
    trimming pieces of it, since a beginner's first reaction to a
    wall of red box-drawing characters is often "I broke something
    badly" even when the underlying issue is a one-word typo.
    """
    info = _CATALOGUE.get(error_type, {
        "title": error_type,
        "hint":  "Something went wrong.",
    })

    if not line:
        line, col = _extract_location(message)

    print()
    print(f"{_RED}{_BOLD}Problem: {info['title']}{_RESET}")

    if source and line:
        lines = source.splitlines()
        if 0 < line <= len(lines):
            print(f"{_DIM}Line {line}:{_RESET}  {lines[line - 1].strip()}")

    clean = _clean(message)
    print()
    print(f"  {clean}")

    if variables:
        var = _extract_token(message)
        if var:
            suggestions = _did_you_mean(var, list(variables.keys()))
            if suggestions:
                print(f"  Did you mean: {', '.join(suggestions)}?")

    print()
    print(f"  {info['hint']}")
    print()


def _find_why_origin(exception: Exception):
    """
    Walk the exception's traceback and find the deepest frame that's
    inside NEKOVA's own lexer/parser/interpreter source — i.e. the
    actual internal check or grammar rule that raised this error —
    skipping generic Python-internal frames (argument unpacking,
    site-packages, etc.). Returns a short "function() at file:line"
    string, or None if no such frame is in the traceback at all.
    """
    tb = getattr(exception, "__traceback__", None)
    if tb is None:
        return None

    frames = traceback.extract_tb(tb)
    relevant = [
        f for f in frames
        if any(seg in f.filename.replace("\\", "/") for seg in
               ("nekova/lexer/", "nekova/parser/", "nekova/interpreter/"))
    ]
    if not relevant:
        return None

    deepest = relevant[-1]
    fname = os.path.basename(deepest.filename)
    return f"raised in {deepest.name}() at {fname}:{deepest.lineno}"


# ── Source renderer ───────────────────────────────────────────

def _render_source(source: str, error_line: int,
                   col: int, message: str):
    """
    Print source context with:
      - 2 lines before and after
      - error line highlighted in pepper red
      - caret (^^^) pointing at the column
    """
    lines   = source.splitlines()
    start   = max(0, error_line - 3)
    end     = min(len(lines), error_line + 2)
    gutter  = len(str(end + 1)) + 1   # width for line numbers

    print()
    # Vertical bar connector
    print(f"  {_DIM}{' ' * gutter} │{_RESET}")

    for i in range(start, end):
        n       = i + 1
        content = lines[i]
        num_str = str(n).rjust(gutter)

        if n == error_line:
            # Error line — pepper red, bold
            print(f"  {_RED}{num_str} │  {_BOLD}{content}{_RESET}")

            # Caret line
            if col > 0:
                # Point at specific column
                token = _extract_token(message) or ""
                caret_len = max(len(token), 1)
                pad   = " " * (col - 1)
                caret = "^" * caret_len
            else:
                # Point at first non-whitespace
                stripped = content.lstrip()
                pad   = " " * (len(content) - len(stripped))
                caret = "^" * max(len(stripped.split()[0]) if stripped.split() else 1, 1)

            print(f"  {_DIM}{' ' * gutter} │{_RESET}  "
                  f"{_RED}{_BOLD}{pad}{caret}{_RESET}"
                  f"  {_DIM}{_extract_short_label(message)}{_RESET}")
        else:
            print(f"  {_DIM}{num_str} │  {content}{_RESET}")

    print(f"  {_DIM}{' ' * gutter} │{_RESET}")


# ── Helpers ───────────────────────────────────────────────────

def _hr():
    print(f"{_RED}{'━' * _WIDTH}{_RESET}")


def _shorten(filepath: str) -> str:
    parts = filepath.replace("\\", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) > 2 else filepath


def _clean(message: str) -> str:
    """Map Python internals to NEKOVA-friendly names."""
    msg = message.strip()
    for old, new in [
        ("\n  ", " — "),
        ("\n",   " "),
        ("'NoneType'", "'null'"),
        ("'bool'",     "'boolean'"),
        ("'str'",      "'text'"),
        ("'int'",      "'number'"),
        ("'float'",    "'decimal'"),
        ("'list'",     "'list'"),
    ]:
        msg = msg.replace(old, new)
    # Truncate very long messages
    if len(msg) > 200:
        msg = msg[:197] + "…"
    return msg


def _extract_token(message: str) -> str:
    """Pull the first quoted token out of an error message."""
    m = re.search(r"'([a-zA-Z_][a-zA-Z0-9_]*)'", message)
    return m.group(1) if m else ""


def _extract_short_label(message: str) -> str:
    """One-word label for the caret annotation."""
    token = _extract_token(message)
    if token:
        return f"'{token}' not defined here"
    return "error here"


def _extract_location(message: str):
    """Try to parse 'Line N, Column M' or 'Line N:' from message."""
    m = re.search(r"[Ll]ine\s+(\d+)[,\s]+[Cc]ol(?:umn)?\s+(\d+)", message)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"[Ll]ine\s+(\d+)", message)
    if m:
        return int(m.group(1)), 0
    return 0, 0


def _did_you_mean(name: str, candidates: list) -> list:
    """
    Use difflib for real similarity — much better than the old char-overlap.
    Returns up to 3 close matches.
    """
    if not candidates:
        return []
    matches = difflib.get_close_matches(
        name, candidates,
        n=3, cutoff=0.5
    )
    return matches


def _quick_fix(error_type: str, message: str,
               line: int, col: int) -> str:
    """Return a one-line actionable fix string, or empty string."""
    if error_type == "NameError":
        var = _extract_token(message)
        if var:
            loc = f"line {line}" if line else "use"
            return f"Add before {loc}:  let {var} = \"your value\""

    if error_type == "TypeError" and "strict" in message.lower():
        return "Set  strict_types = false  in nekova.toml to allow dynamic types."

    if error_type == "TypeError":
        return "Use  let x: any = value  to allow any type for this variable."

    if error_type == "ZeroDivisionError":
        return "Guard with:  if divisor != 0: result = a / divisor"

    if error_type == "ImportError":
        mod = _extract_token(message)
        return f"Check spelling of '{mod}'. Run  nekova info  to see stdlib." if mod else ""

    if "unclosed" in message.lower():
        return "Add a closing  \"  or  ]  to complete the expression."

    if "reserved keyword" in message.lower() or "keyword" in message.lower():
        token = _extract_token(message)
        if token:
            return f"Rename '{token}' to '{token}_fn' (tasks) or 'my_{token}' (variables)."

    if "unreachable" in message.lower():
        return "Move this code before the 'return' statement."

    if "shadows" in message.lower():
        token = _extract_token(message)
        return f"Rename '{token}' to avoid shadowing the built-in." if token else ""

    return ""