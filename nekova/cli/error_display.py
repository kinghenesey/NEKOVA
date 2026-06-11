# =============================================================
# NEKOVA CLI — Enhanced Error Display System
# =============================================================
# Transforms raw errors into beautiful, helpful messages
# with source context, suggestions, and did-you-mean hints.

import re
from nekova.config import Color


ERROR_HINTS = {
    "NameError": {
        "title":   "Variable Not Found",
        "hint":    "This variable was used but never defined.",
        "example": "Define it before using it:  name = value",
    },
    "SyntaxError": {
        "title":   "Syntax Error",
        "hint":    "There's a mistake in how this line is written.",
        "example": "Check for missing quotes, colons, or brackets.",
    },
    "ParseError": {
        "title":   "Parse Error",
        "hint":    "NEKOVA couldn't understand the structure of your code.",
        "example": "Check your indentation and statement structure.",
    },
    "RuntimeError": {
        "title":   "Runtime Error",
        "hint":    "Something went wrong while running your program.",
        "example": "Check the values your variables hold.",
    },
    "TypeError": {
        "title":   "Type Error",
        "hint":    "You're mixing incompatible types of values.",
        "example": "Make sure you're not adding a number to a string.",
    },
    "ZeroDivisionError": {
        "title":   "Division By Zero",
        "hint":    "You cannot divide a number by zero.",
        "example": "Check that your divisor is never 0.",
    },
    "ImportError": {
        "title":   "Module Not Found",
        "hint":    "This module doesn't exist in NEKOVA's standard library.",
        "example": "Available: math, text, files, datetime, collections, ai, agents, ui, web, database",
    },
    "IndexError": {
        "title":   "Index Out of Range",
        "hint":    "You're trying to access an item that doesn't exist.",
        "example": "Check that your index is less than the list length.",
    },
    "KeyError": {
        "title":   "Key Not Found",
        "hint":    "This key doesn't exist in the dictionary.",
        "example": "Check available keys with dict.keys()",
    },
}


def display_error(
    error_type: str,
    message: str,
    source: str = "",
    filepath: str = "",
    line: int = 0,
    variables: dict = None,
):
    """
    Display a beautifully formatted NEKOVA error message
    with source context, suggestions and did-you-mean hints.
    """
    info = ERROR_HINTS.get(error_type, {
        "title":   error_type,
        "hint":    "An unexpected error occurred.",
        "example": "Review the line shown above.",
    })

    width = 52

    # ── Header ────────────────────────────────────────────────
    print()
    print(f"{Color.RED}{'━' * width}{Color.RESET}")
    print(f"{Color.RED}{Color.BOLD}"
          f"  NEKOVA Error — {info['title']}"
          f"{Color.RESET}")

    if filepath and line:
        short_path = _shorten_path(filepath)
        print(f"{Color.DIM}  Line {line} · {short_path}"
              f"{Color.RESET}")
    elif line:
        print(f"{Color.DIM}  Line {line}{Color.RESET}")

    print(f"{Color.RED}{'━' * width}{Color.RESET}")

    # ── Source context ────────────────────────────────────────
    if source and line:
        lines = source.splitlines()
        _show_source_context(lines, line)

    # ── Error message ─────────────────────────────────────────
    print()
    clean_msg = _clean_message(message)
    print(f"  {Color.WHITE}✗ {clean_msg}{Color.RESET}")

    # ── Did you mean? ─────────────────────────────────────────
    if error_type == "NameError" and variables:
        var_name = _extract_var_name(message)
        if var_name:
            suggestions = _did_you_mean(
                var_name, variables)
            if suggestions:
                print()
                print(f"  {Color.YELLOW}"
                      f"💡 Did you mean one of these?"
                      f"{Color.RESET}")
                for s in suggestions:
                    print(f"  {Color.DIM}   → {s}"
                          f"{Color.RESET}")

    # ── Hint ──────────────────────────────────────────────────
    print()
    print(f"  {Color.YELLOW}💡 {info['hint']}"
          f"{Color.RESET}")
    print(f"  {Color.DIM}   {info['example']}"
          f"{Color.RESET}")

    # ── Quick fix suggestion ───────────────────────────────────
    fix = _suggest_fix(error_type, message, line)
    if fix:
        print()
        print(f"  {Color.CYAN}🔧 Quick fix:{Color.RESET}")
        print(f"  {Color.DIM}   {fix}{Color.RESET}")

    print(f"{Color.RED}{'━' * width}{Color.RESET}")
    print()


def _show_source_context(lines: list,
                          error_line: int):
    """Show source lines around the error."""
    start = max(0, error_line - 3)
    end   = min(len(lines), error_line + 2)

    print()
    for i in range(start, end):
        line_num = i + 1
        content  = lines[i]

        if line_num == error_line:
            print(f"  {Color.RED}▶ "
                  f"{line_num:>3} │  "
                  f"{Color.BOLD}{content}"
                  f"{Color.RESET}")
        else:
            print(f"  {Color.DIM}  "
                  f"{line_num:>3} │  {content}"
                  f"{Color.RESET}")


def _clean_message(message: str) -> str:
    """Clean up raw error messages."""
    message = message.strip()
    replacements = [
        ("\n  ", " — "),
        ("\n", " "),
        ("'NoneType'", "'null'"),
        ("'bool'",     "'boolean'"),
        ("'str'",      "'text'"),
        ("'int'",      "'number'"),
        ("'float'",    "'decimal'"),
    ]
    for old, new in replacements:
        message = message.replace(old, new)
    return message


def _extract_var_name(message: str) -> str:
    """Extract variable name from error message."""
    match = re.search(r"'([a-zA-Z_][a-zA-Z0-9_]*)'",
                      message)
    return match.group(1) if match else ""


def _did_you_mean(var_name: str,
                  variables: dict) -> list:
    """Suggest similar variable names."""
    suggestions = []
    var_lower   = var_name.lower()

    for name in variables:
        name_lower = name.lower()
        # Check similarity
        if (var_lower in name_lower or
                name_lower in var_lower or
                _similar(var_lower, name_lower)):
            suggestions.append(name)

    return suggestions[:3]


def _similar(a: str, b: str) -> bool:
    """Check if two strings are similar."""
    if not a or not b:
        return False
    # Check if they share most characters
    common = sum(1 for c in a if c in b)
    return common >= min(len(a), len(b)) * 0.6


def _suggest_fix(error_type: str,
                 message: str,
                 line: int) -> str:
    """Suggest a quick fix for common errors."""
    if error_type == "NameError":
        var = _extract_var_name(message)
        if var:
            return (f"Add before line {line}:  "
                    f"{var} = \"your value here\"")

    if error_type == "ZeroDivisionError":
        return "Check divisor is not zero before dividing."

    if error_type == "ImportError":
        mod = _extract_var_name(message)
        if mod:
            return f"Available modules: math, text, files, ai, web, database"

    if "unclosed" in message.lower():
        return "Check for missing closing quote \" or bracket"

    return ""


def _shorten_path(filepath: str) -> str:
    """Shorten long file paths for display."""
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) > 3:
        return "/".join(parts[-2:])
    return filepath
