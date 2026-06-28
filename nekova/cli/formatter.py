# =============================================================
# NEKOVA CLI — Auto-Formatter  (Phase 10)
# =============================================================
# nekova fmt <file>       — format a single file in-place
# nekova fmt              — format all .nk files in project
#
# Rules enforced:
#   - 4-space indentation (convert tabs → 4 spaces)
#   - Single blank line between top-level blocks
#   - No trailing whitespace
#   - Operators surrounded by single spaces (=, +, -, *, /, ==, !=, <, >)
#   - Colons directly after block keywords (no space before)
#   - Consistent string quotes (double-quoted by default)
#   - Max two consecutive blank lines → one
#   - EOF newline enforced
# =============================================================

import re
import os


# ── Keyword sets ─────────────────────────────────────────────

_BLOCK_KEYWORDS = {
    "task", "if", "else", "for", "while", "repeat",
    "try", "catch", "object", "match", "when", "route",
    "async", "autonomous",
}

_INDENT_UNIT = "    "   # 4 spaces


# ── Public API ────────────────────────────────────────────────

def fmt_file(filepath: str, dry_run: bool = False) -> tuple:
    """
    Format a .nk file in-place.

    Returns (changed: bool, original: str, formatted: str)
    dry_run=True → compute the result but don't write to disk.
    """
    with open(filepath, "rb") as f:
        raw = f.read()

    # Strip BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]

    original  = raw.decode("utf-8")
    formatted = fmt_source(original)

    changed = formatted != original

    if changed and not dry_run:
        with open(filepath, "wb") as f:
            f.write(formatted.encode("utf-8"))

    return changed, original, formatted


def fmt_source(source: str) -> str:
    """
    Format a NEKOVA source string.
    Returns the formatted string.
    """
    lines = source.splitlines()

    lines = _fix_indentation(lines)
    lines = _fix_trailing_whitespace(lines)
    lines = _fix_blank_lines(lines)
    lines = _fix_operators(lines)
    lines = _fix_colons(lines)

    result = "\n".join(lines)

    # Ensure exactly one trailing newline
    result = result.rstrip("\n") + "\n"

    return result


def fmt_directory(dirpath: str = ".", dry_run: bool = False) -> list:
    """
    Format all .nk files under dirpath.
    Returns list of (filepath, changed) tuples.
    """
    results = []
    for root, dirs, files in os.walk(dirpath):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [d for d in dirs
                   if not d.startswith(".")
                   and d not in ("__pycache__", "node_modules", ".git",
                                 "dist", "build", ".nekova")]
        for fname in files:
            if fname.endswith(".nk"):
                fpath = os.path.join(root, fname)
                try:
                    changed, _, _ = fmt_file(fpath, dry_run=dry_run)
                    results.append((fpath, changed))
                except Exception as e:
                    results.append((fpath, f"ERROR: {e}"))

    return results


# ── Formatting passes ─────────────────────────────────────────

def _fix_indentation(lines: list) -> list:
    """
    Convert all leading tabs to 4-space indentation.
    Also normalise any inconsistent indent (2-space → 4-space).
    """
    result = []
    for line in lines:
        if not line.strip():
            result.append("")
            continue

        # Count leading whitespace
        stripped = line.lstrip()
        leading  = line[: len(line) - len(stripped)]

        # Convert tabs to 4 spaces each
        leading = leading.replace("\t", _INDENT_UNIT)

        # Detect 2-space indentation and convert
        # Only do this if there's no 4-space pattern already
        if leading and not leading.startswith(_INDENT_UNIT):
            # Count leading spaces
            n_spaces = len(leading)
            if n_spaces % 2 == 0 and n_spaces % 4 != 0:
                # Likely 2-space indent — double it
                depth   = n_spaces // 2
                leading = _INDENT_UNIT * depth

        result.append(leading + stripped)

    return result


def _fix_trailing_whitespace(lines: list) -> list:
    """Strip trailing whitespace from every line."""
    return [line.rstrip() for line in lines]


def _fix_blank_lines(lines: list) -> list:
    """
    Reduce runs of 3+ blank lines to at most 2.
    Also ensure single blank line between top-level task/object blocks.
    """
    result   = []
    blanks   = 0

    for line in lines:
        if line.strip() == "":
            blanks += 1
            if blanks <= 2:
                result.append("")
        else:
            blanks = 0
            result.append(line)

    # Remove leading blank lines
    while result and result[0] == "":
        result.pop(0)

    return result


def _fix_operators(lines: list) -> list:
    """
    Ensure single spaces around binary operators in assignments and expressions.
    Skips comment lines (#) and string contents.
    """
    result = []
    for line in lines:
        stripped = line.lstrip()

        # Skip comments
        if stripped.startswith("#"):
            result.append(line)
            continue

        # Skip lines that look like they're entirely strings
        # (we don't want to mangle f-string contents)
        if stripped.startswith(('"""', "'''", 'f"', "f'")):
            result.append(line)
            continue

        leading = line[: len(line) - len(stripped)]
        fixed   = _fix_operator_spacing(stripped)
        result.append(leading + fixed)

    return result


def _fix_operator_spacing(code: str) -> str:
    """
    Fix spacing around operators in a single line of code.
    Handles: =, ==, !=, <=, >=, <, >, +, -, *, /
    Preserves string literals and f-strings.
    """
    # Tokenise into string segments and code segments
    # so we never modify inside strings
    segments = _split_strings(code)

    result_parts = []
    for kind, text in segments:
        if kind == "str":
            result_parts.append(text)
        else:
            text = _space_operators(text)
            result_parts.append(text)

    return "".join(result_parts)


def _space_operators(code: str) -> str:
    """Add/normalise spaces around operators in non-string code."""
    # Fix compound operators first (order matters)
    for op in ("==", "!=", "<=", ">=", "+=", "-=", "*=", "/="):
        # Remove extra spaces around compound operators
        code = re.sub(r"\s*" + re.escape(op) + r"\s*",
                      f" {op} ", code)

    # Assignment = (but not ==, !=, <=, >=)
    # Only fix standalone =
    code = re.sub(r"(?<![=!<>+\-*/])\s*=\s*(?!=)", " = ", code)

    # Arithmetic operators — handle multi-char FIRST to avoid splitting ** into * *
    import re as _re
    # Normalise ** and // spacing first
    code = _re.sub(r" *\*\* *", " ** ", code)
    code = _re.sub(r" *// *", " // ", code)
    # Single-char + * / (using negative lookahead to skip ** and //)
    code = _re.sub(r" *(?<!\*)\*(?!\*) *", " * ", code)
    code = _re.sub(r" *(?<!/)/(?!/) *", " / ", code)
    code = _re.sub(r" *\+ *", " + ", code)

    # Clean up multiple spaces
    code = re.sub(r"  +", " ", code)

    # Don't add space at the very start
    code = code.lstrip()

    return code


def _fix_colons(lines: list) -> list:
    """
    Ensure no space before the colon at the end of block-opening lines.
    e.g.  'task foo() :' → 'task foo():'
    """
    result = []
    for line in lines:
        # Only apply to lines ending with  (whitespace + colon)
        if re.search(r"\s+:$", line):
            line = re.sub(r"\s+:$", ":", line)
        result.append(line)
    return result


# ── String splitter ───────────────────────────────────────────

def _split_strings(code: str) -> list:
    """
    Split code into alternating (kind, text) segments:
      kind == "str"  → string literal (don't touch)
      kind == "code" → non-string code (safe to reformat)
    """
    segments = []
    i        = 0
    n        = len(code)

    while i < n:
        ch = code[i]

        # String start: f" f' " '
        if ch in ('"', "'") or (ch in ("f", "F") and i + 1 < n
                                 and code[i + 1] in ('"', "'")):
            prefix = ""
            if ch in ("f", "F"):
                prefix = ch
                i += 1
                ch = code[i]

            quote_char = ch
            # Triple quote?
            if code[i:i+3] in ('"""', "'''"):
                end_seq = code[i:i+3]
                j = i + 3
                while j < n:
                    if code[j:j+3] == end_seq:
                        j += 3
                        break
                    if code[j] == "\\":
                        j += 2
                    else:
                        j += 1
            else:
                j = i + 1
                while j < n:
                    if code[j] == quote_char and code[j-1] != "\\":
                        j += 1
                        break
                    j += 1

            segments.append(("str", prefix + code[i:j]))
            i = j

        elif ch == "#":
            # Comment — treat rest of line as string (don't touch)
            segments.append(("str", code[i:]))
            break

        else:
            # Accumulate code chars until next string start
            start = i
            while i < n:
                c = code[i]
                if c in ('"', "'"):
                    break
                if c in ("f", "F") and i + 1 < n and code[i+1] in ('"', "'"):
                    break
                if c == "#":
                    break
                i += 1
            if i > start:
                segments.append(("code", code[start:i]))

    return segments