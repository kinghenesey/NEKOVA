# =============================================================
# NEKOVA LSP — Diagnostics
# =============================================================
# Turns NEKOVA source text into a list of LSP Diagnostic objects
# (https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#diagnostic)
# by running it through the real lexer and parser — the same ones
# `nekova run` uses — not a separate approximation. This is what
# makes "inline errors" trustworthy: what the editor flags is exactly
# what would fail at parse time.
#
# Two error sources are handled differently:
#   - LexerError: the lexer stops at the first invalid token, so at
#     most one diagnostic comes from it.
#   - ParseError: since Parser.parse() now does multi-error recovery
#     (Phase 26), e.all_errors carries every syntax error collected
#     in a single pass, not just the first — so a file with three
#     unrelated mistakes gets three diagnostics, not one-fix-rerun
#     x3.
#
# Column precision: LexerError carries a real column. ParseError
# historically only ever carries a line (see parser.py's many
# `raise ParseError(msg, token.line)` call sites — none pass a
# column). Rather than touching dozens of raise sites to thread
# column info through just for this, parse-error diagnostics span
# column 0 to end-of-line, which editors render as an underline
# across the whole line — clear enough for a first version of
# diagnostics, and non-breaking to improve later without changing
# this module's public shape.

from nekova.lexer.lexer import Lexer, LexerError
from nekova.parser.parser import Parser, ParseError

SEVERITY_ERROR = 1
SEVERITY_WARNING = 2
SEVERITY_INFO = 3
SEVERITY_HINT = 4


def _diagnostic(line_1_indexed: int, message: str,
                 column_start: int = 0, column_end: int = None,
                 severity: int = SEVERITY_ERROR) -> dict:
    """
    Build one LSP Diagnostic. NEKOVA's own line numbers are
    1-indexed (matching how they're shown in nekova run's own error
    output); LSP positions are 0-indexed, so every line gets -1'd
    here — this is the one place that conversion happens.
    """
    line = max(0, line_1_indexed - 1)
    if column_end is None:
        # No known column — underline the whole line. A very large
        # end character is clamped by every real editor to the
        # actual line length, so this is safe without knowing it.
        column_end = 100000
    return {
        "range": {
            "start": {"line": line, "character": column_start},
            "end": {"line": line, "character": column_end},
        },
        "severity": severity,
        "source": "nekova",
        "message": message,
    }


def compute_diagnostics(source: str) -> list:
    """
    Run `source` through the lexer and parser and return every
    syntax error found as a list of LSP Diagnostic dicts. Returns an
    empty list for source with no errors — callers publish that
    empty list too (see server.py), which is what clears previously
    reported errors in the editor once they're fixed.
    """
    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        return [_diagnostic(
            e.line, str(e).strip().split(": ", 1)[-1],
            column_start=max(0, e.column),
            column_end=max(0, e.column) + 1,
        )]
    except Exception as e:
        # Anything else unexpected from the lexer shouldn't crash the
        # whole diagnostics pass — surface it as a single diagnostic
        # on line 1 rather than taking the server down.
        return [_diagnostic(1, f"Lexer error: {e}")]

    try:
        Parser(tokens).parse()
        return []
    except ParseError as e:
        errors = getattr(e, "all_errors", [e])
        return [
            _diagnostic(err.line, str(err).strip().split(": ", 1)[-1])
            for err in errors
        ]
    except Exception as e:
        return [_diagnostic(1, f"Parser error: {e}")]