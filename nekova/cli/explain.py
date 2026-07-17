# =============================================================
# NEKOVA CLI — nekova explain  (Phase 26b "Education Layer")
# =============================================================
# `nekova explain err.nk` runs a file the same way `nekova run`
# does, but instead of stopping at the Rust-style error card it
# walks through *why* the error happened in plain language —
# NEKOVA's own origin story is helping classmates who got tripped
# up learning Python, so this is meant to read like a patient
# human explaining the mistake, not a stack trace.
#
# Two layers, deliberately kept separate:
#   1. A deterministic, template-based explanation — always
#      available, fully testable, no AI provider required.
#   2. An optional one-paragraph AI-generated addition (using
#      `think` itself — on-brand for an AI-native language),
#      wrapped in try/except so a missing/unreachable provider
#      never breaks the deterministic explanation above it.
# =============================================================

import os

from nekova.config import Color
from nekova.cli import print_error, print_info
from nekova.cli.error_display import (
    _CATALOGUE, _extract_token, _extract_location, _clean,
)
from nekova.lexer import Lexer, LexerError
from nekova.parser.parser import Parser, ParseError
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import (
    NEKOVARuntimeError, NEKOVAImportError, NEKOVANameError,
    NEKOVARecursionError,
)


# ── Plain-language templates ────────────────────────────────────
# Each template gets **kwargs: var (offending name, may be ""),
# line (int, may be 0), message (cleaned original message).

def _explain_name_error(var, line, message):
    who = f"`{var}`" if var else "a variable"
    where = f" on line {line}" if line else ""
    return (
        f"Your code uses {who}{where}, but nothing with that name has "
        f"been created yet at that point in the program. NEKOVA (like "
        f"most languages) needs a variable to exist before you can "
        f"read it — usually by writing "
        f"`let {var or 'name'} = ...` somewhere earlier in the file. "
        f"A common cause is a typo: check the spelling matches "
        f"exactly, including capitalization."
    )


def _explain_syntax_error(var, line, message):
    where = f" around line {line}" if line else ""
    return (
        f"NEKOVA's parser stopped being able to understand the "
        f"code{where}. This almost always means one of: a missing "
        f"colon after `if`/`while`/`for`/`task`, an unmatched "
        f"quote or bracket, or indentation that doesn't line up "
        f"with the block it's supposed to be part of. Read the "
        f"line just before the one flagged, too — a missing "
        f"closing character there often only causes an error on "
        f"the *next* line."
    )


def _explain_type_error(var, line, message):
    return (
        f"An operation here was given a value of a type it can't "
        f"work with — for example, trying to combine text and a "
        f"number without converting one of them first (`\"5\" + 3` "
        f"raises in NEKOVA rather than silently becoming `\"53\"`). "
        f"Check what type each value actually is — `type(x)` on the "
        f"value in question, or `int(x)` / `str(x)` to convert it "
        f"deliberately, usually fixes this."
    )


def _explain_zero_division(var, line, message):
    where = f" on line {line}" if line else ""
    return (
        f"The code divides a number by zero{where}. Division by "
        f"zero has no defined answer, so NEKOVA stops rather than "
        f"guessing. Guard the division with a check first, e.g. "
        f"`if divisor != 0: result = a / divisor`."
    )


def _explain_index_error(var, line, message):
    return (
        f"Your code tried to reach a position in a list that "
        f"doesn't exist — for example, asking for item 5 of a "
        f"list that only has 3 items. List positions start at 0, "
        f"and the last valid position is `length - 1`. Check the "
        f"list's length before indexing into it: "
        f"`if i < my_list.length: ...`."
    )


def _explain_key_error(var, line, message):
    who = f"`{var}`" if var else "a key"
    return (
        f"Your code asked a dictionary for {who}, but that key was "
        f"never stored in it. Check the spelling matches exactly, "
        f"or check which keys actually exist first with "
        f"`dict.keys()`."
    )


def _explain_import_error(var, line, message):
    who = f"`{var}`" if var else "a module"
    return (
        f"NEKOVA looked for {who} in its standard library and "
        f"didn't find it. Check the spelling, or run `nekova info` "
        f"to see which stdlib modules are actually available."
    )


def _explain_recursion_error(var, line, message):
    who = f"Task `{var}`" if var else "A task"
    return (
        f"{who} called itself over and over without ever reaching "
        f"a stopping point — what's usually called a 'base case'. "
        f"NEKOVA's safety limit kicked in before this could crash "
        f"the whole program. Check that the task has a condition "
        f"that eventually stops the recursion, and that the "
        f"recursive call is actually moving *toward* that "
        f"condition (not, say, calling itself with the same "
        f"argument every time)."
    )


def _explain_runtime_error(var, line, message):
    where = f" on line {line}" if line else ""
    return (
        f"Something went wrong while actually running the "
        f"code{where}. The message above (\"{message}\") has the "
        f"specific reason — read it alongside the line it points "
        f"to, since NEKOVA's runtime errors usually name the exact "
        f"value or operation that failed."
    )


_EXPLAINERS = {
    "NameError":        _explain_name_error,
    "SyntaxError":       _explain_syntax_error,
    "ParseError":        _explain_syntax_error,
    "TypeError":         _explain_type_error,
    "ZeroDivisionError": _explain_zero_division,
    "IndexError":        _explain_index_error,
    "KeyError":          _explain_key_error,
    "ImportError":       _explain_import_error,
    "RecursionError":    _explain_recursion_error,
    "RuntimeError":      _explain_runtime_error,
}


def _ai_explanation(error_type: str, message: str, line: int) -> str:
    """
    Ask the configured AI provider (mock, by default) for one extra
    plain-language sentence or two. Best-effort: any failure here
    (no provider configured, network error, timeout) is swallowed
    and simply omitted from the output — the deterministic
    explanation above never depends on this succeeding.
    """
    try:
        from nekova.ai.providers import get_provider
        provider = get_provider()
        prompt = (
            f"A beginner programmer got this error in a program: "
            f"{error_type}: {message}"
            + (f" (line {line})" if line else "")
            + ". In one short, encouraging sentence, explain what "
              "likely caused it, in plain language with no jargon."
        )
        return provider.ask(prompt).strip()
    except Exception:
        return ""


def explain_error(error_type: str, message: str, line: int = 0,
                   use_ai: bool = True) -> str:
    """
    Build the full plain-language explanation for one error.
    Pure function (no I/O) so it's directly unit-testable.
    """
    var = _extract_token(message)
    if not line:
        line, _ = _extract_location(message)

    template = _EXPLAINERS.get(error_type, _explain_runtime_error)
    body = template(var, line, _clean(message))

    parts = [body]

    if use_ai:
        ai_note = _ai_explanation(error_type, _clean(message), line)
        if ai_note:
            parts.append(f"\n{Color.DIM}Additionally: {ai_note}{Color.RESET}")

    return "\n".join(parts)


# ── CLI entry point ──────────────────────────────────────────────

def cmd_explain(filepath: str, use_ai: bool = True) -> bool:
    """
    Run a .nk file and explain the first error encountered in
    plain language. Returns True if the file ran without error
    (nothing to explain) or an explanation was successfully shown;
    False only for I/O-level failures (file missing, unreadable).
    """
    if not filepath:
        print_error("Usage: nekova explain <file.nk>")
        return False

    if not os.path.isfile(filepath):
        print_error(f"File not found: '{filepath}'")
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print_error(f"Could not read file: {e}")
        return False

    error_type, message, line, exc = None, None, 0, None

    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        interpreter = Interpreter()
        interpreter.execute(program, filepath=os.path.abspath(filepath))
    except LexerError as e:
        error_type, message, line = "SyntaxError", str(e), getattr(e, "line", 0)
    except ParseError as e:
        error_type, message, line = "ParseError", str(e), getattr(e, "line", 0)
    except NEKOVANameError as e:
        error_type, message, line = "NameError", str(e), getattr(e, "line", 0)
    except NameError as e:
        error_type, message, line = "NameError", str(e), 0
    except NEKOVAImportError as e:
        error_type, message, line = "ImportError", str(e), getattr(e, "line", 0)
    except TypeError as e:
        error_type, message, line = "TypeError", str(e), getattr(e, "line", 0)
    except ZeroDivisionError as e:
        error_type, message, line = "ZeroDivisionError", str(e), 0
    except IndexError as e:
        error_type, message, line = "IndexError", str(e), 0
    except KeyError as e:
        error_type, message, line = "KeyError", str(e), 0
    except NEKOVARecursionError as e:
        error_type, message, line = "RecursionError", str(e), getattr(e, "line", 0)
    except RecursionError:
        error_type, message, line = "RecursionError", (
            "Python's stack limit was reached before NEKOVA's own "
            "call-depth check could catch it."
        ), 0
    except NEKOVARuntimeError as e:
        error_type, message, line = "RuntimeError", str(e), getattr(e, "line", 0)

    print()
    if error_type is None:
        print_info(f"'{filepath}' ran without error — nothing to explain.")
        return True

    info = _CATALOGUE.get(error_type, {"title": error_type})
    print(f"{Color.CYAN}{Color.BOLD}Explaining: {info['title']}"
          f"{Color.RESET}")
    if line:
        print(f"{Color.DIM}  {filepath}:{line}{Color.RESET}")
    print()

    lines = source.splitlines()
    if line and 0 < line <= len(lines):
        print(f"  {Color.DIM}{line} │{Color.RESET}  {lines[line - 1].strip()}")
        print()

    explanation = explain_error(error_type, message, line, use_ai=use_ai)
    for para in explanation.split("\n"):
        print(f"  {para}")
    print()
    return True