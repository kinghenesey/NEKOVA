# =============================================================
# NEKOVA Lexer — Main Lexer Engine
# =============================================================
# The Lexer reads raw source code character by character
# and produces a list of Tokens.
#
# Process:
#   1. Read one character at a time
#   2. Decide what kind of token it starts
#   3. Consume characters until the token is complete
#   4. Add the token to the list
#   5. Repeat until end of file

from nekova.lexer.token_types import TokenType, KEYWORDS
from nekova.lexer.token import Token


class LexerError(Exception):
    """Raised when the lexer encounters invalid code."""
    def __init__(self, message: str, line: int, column: int):
        self.line    = line
        self.column  = column
        super().__init__(f"\n  Line {line}, Column {column}: {message}")


class Lexer:
    """
    Converts raw NEKOVA source code into a list of Tokens.

    Usage:
        lexer  = Lexer(source_code)
        tokens = lexer.tokenize()
    """

    def __init__(self, source: str):
        self.source  = source
        self.pos     = 0          # current character position
        self.line    = 1          # current line number
        self.column  = 1          # current column number
        self.tokens  = []         # collected tokens
        self.indent_stack = [0]   # tracks indentation levels
        self.bracket_depth = 0    # tracks nesting inside (), [], {}
        # While bracket_depth > 0 we are inside an unfinished
        # (), [], or {} group. Python-style "implicit line joining":
        # newlines in that state are pure whitespace — no NEWLINE,
        # INDENT, or DEDENT tokens are emitted, and indentation is
        # not tracked, no matter how the contents are laid out
        # across lines. This lets dict/list/call literals span
        # multiple indented lines without confusing the block
        # (task/if/while/etc.) indentation tracker.

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """
        Main method — scans the entire source and returns
        a flat list of Token objects.
        """
        while not self._at_end():
            self._scan_token()

        # Close any remaining indentation blocks
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self._add_token(TokenType.DEDENT, "DEDENT")

        self._add_token(TokenType.EOF, "EOF")
        return self.tokens

    # ----------------------------------------------------------
    # Core scanner
    # ----------------------------------------------------------

    def _scan_token(self):
        """Read the next token from the current position."""
        char = self._current()

        # ── Newlines & indentation ────────────────────────────
        if char == "\n":
            self._handle_newline()
            return

        # ── Skip spaces and tabs (mid-line whitespace) ────────
        if char in (" ", "\t"):
            self._advance()
            return

        # ── Skip comments ─────────────────────────────────────
        if char == "#":
            self._skip_comment()
            return

        # ── Skip carriage returns (Windows line endings) ──────
        if char == "\r":
            self._advance()
            return

        # ── String literals ───────────────────────────────────
        if char == '"' or char == "'":
            # Check for triple-quote: """ or '''
            if (self.pos + 2 < len(self.source)
                    and self.source[self.pos + 1] == char
                    and self.source[self.pos + 2] == char):
                self._read_triple_string(char)
            else:
                self._read_string(char)
            return

        # ── Numbers ───────────────────────────────────────────
        if char.isdigit():
            self._read_number()
            return

        # ── Identifiers and keywords ──────────────────────────
        if char.isalpha() or char == "_":
            self._read_identifier()
            return

        # ── Operators and punctuation ─────────────────────────
        self._read_symbol()

    # ----------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------

    def _handle_newline(self):
        """
        Process a newline character.
        After the newline we check indentation to decide
        whether to emit INDENT or DEDENT tokens.

        Blank lines (lines with only whitespace or nothing)
        are completely ignored — they never change the indent
        level. This lets developers write readable code with
        blank lines inside task/if/for/while bodies without
        getting spurious INDENT/DEDENT errors.
        """
        # ── Inside brackets: newline is just whitespace ───────
        # Suspend NEWLINE/INDENT/DEDENT emission entirely while
        # depth > 0, so multi-line dict/list/call literals never
        # touch the block indentation tracker (see bracket_depth
        # note in __init__).
        if self.bracket_depth > 0:
            self._advance()  # consume the \n
            return

        self._add_token(TokenType.NEWLINE, "\\n")
        self._advance()  # consume the \n

        # Count leading whitespace of the NEXT line
        indent = 0
        start  = self.pos
        while not self._at_end() and self._current() in (" ", "\t"):
            if self._current() == "\t":
                indent += 4  # 1 tab = 4 spaces
            else:
                indent += 1
            self._advance()

        # ── Blank line: next non-whitespace is \n, \r, or EOF ─
        # Completely skip it — don't emit INDENT or DEDENT.
        # Reset pos to re-read any consumed whitespace via the
        # normal scanner on the next iteration.
        if self._at_end() or self._current() in ("\n", "\r", "#"):
            self.pos = start   # rewind — let the scanner re-read
            return

        current_indent = self.indent_stack[-1]

        if indent > current_indent:
            self.indent_stack.append(indent)
            self._add_token(TokenType.INDENT, "INDENT")

        elif indent < current_indent:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self._add_token(TokenType.DEDENT, "DEDENT")

        # Equal indent → no token needed, same block continues

    def _skip_comment(self):
        """Skip everything from # to end of line."""
        while not self._at_end() and self._current() != "\n":
            self._advance()

    def _read_fstring(self):
        """
        Read an f-string literal: f"Hello {name}!" or f\"\"\"multi-line {name}\"\"\"
        Stores the raw string value — interpolation is
        handled at parse time by _parse_fstring().
        """
        quote = self._current()

        # Check for triple-quote opening: f\"\"\" or f'''
        if (not self._at_end() and
                self._peek() == quote and
                len(self.source) > self.pos + 1 and
                self.source[self.pos + 1] == quote):
            # Triple-quoted f-string
            self._advance()  # skip first quote
            self._advance()  # skip second quote
            self._advance()  # skip third quote
            triple = quote * 3
            value  = []
            while not self._at_end():
                # Check for closing triple-quote
                if (self._current() == quote and
                        not self._at_end() and
                        self._peek() == quote and
                        len(self.source) > self.pos + 1 and
                        self.source[self.pos + 1] == quote):
                    self._advance()  # skip first closing quote
                    self._advance()  # skip second closing quote
                    self._advance()  # skip third closing quote
                    break
                if self._current() == "\n":
                    value.append("\n")
                    self._advance()
                    self.line  += 1
                    self.column = 1
                elif (self._current() == "\\" and
                      self._peek() in ('"', "'", "n", "t", "\\")):
                    escape = self._peek()
                    self._advance()
                    self._advance()
                    if escape == "n":   value.append("\n")
                    elif escape == "t": value.append("\t")
                    else:               value.append(escape)
                else:
                    value.append(self._current())
                    self._advance()
            else:
                raise LexerError(
                    "Triple-quoted f-string was never closed — "
                    f"did you forget closing {triple}?",
                    self.line, self.column)
            self._add_token(TokenType.F_STRING, "".join(value))
            return

        # Single-quoted f-string
        self._advance()  # skip opening quote

        value = []
        while not self._at_end() and self._current() != quote:
            if self._current() == "\\" and self._peek() in ('"', "'", "n", "t", "\\"):
                escape = self._peek()
                self._advance()
                self._advance()
                if escape == "n":   value.append("\n")
                elif escape == "t": value.append("\t")
                else:               value.append(escape)
            else:
                value.append(self._current())
                self._advance()

        if self._at_end():
            raise LexerError(
                "f-string was never closed — did you forget a closing quote?",
                self.line, self.column)

        self._advance()  # skip closing quote
        self._add_token(TokenType.F_STRING, "".join(value))

    def _read_string(self, quote: str):
        """Read a quoted string literal."""
        self._advance()  # skip opening quote
        start_line   = self.line
        start_column = self.column
        value        = []

        while not self._at_end() and self._current() != quote:
            if self._current() == "\n":
                raise LexerError(
                    "String was never closed — did you forget a closing quote?",
                    start_line, start_column
                )
            # Handle escape sequences
            if self._current() == "\\" and self._peek() in ('"', "'", "n", "t", "\\"):
                self._advance()  # skip backslash
                escape = self._current()
                if   escape == "n":  value.append("\n")
                elif escape == "t":  value.append("\t")
                else:                value.append(escape)
            else:
                value.append(self._current())
            self._advance()

        if self._at_end():
            raise LexerError(
                "String was never closed — did you forget a closing quote?",
                start_line, start_column
            )

        self._advance()  # skip closing quote
        self._add_token(TokenType.STRING, "".join(value))

    def _read_triple_string(self, quote: str):
        """
        Read a triple-quoted string literal: \"\"\"...\"\"\" or '''...'''
        Spans multiple lines. Escape sequences are honoured.
        Leading newline immediately after the opening quotes is stripped.
        """
        start_line   = self.line
        start_column = self.column

        # Consume all three opening quotes
        self._advance()
        self._advance()
        self._advance()

        # Strip a single leading newline (matches Python behaviour)
        if not self._at_end() and self._current() == "\n":
            self._advance()
            self.line  += 1
            self.column = 1

        value = []

        while not self._at_end():
            c = self._current()

            # Check for closing triple-quote
            if (c == quote
                    and self.pos + 1 < len(self.source)
                    and self.source[self.pos + 1] == quote
                    and self.pos + 2 < len(self.source)
                    and self.source[self.pos + 2] == quote):
                self._advance()
                self._advance()
                self._advance()
                self._add_token(TokenType.STRING, "".join(value))
                return

            # Handle escape sequences
            if c == "\\" and not self._at_end():
                nxt = self._peek()
                if nxt in ('"', "'", "\\"):
                    self._advance()
                    value.append(self._peek() if False else self._current())
                elif nxt == "n":
                    self._advance(); self._advance()
                    value.append("\n")
                    continue
                elif nxt == "t":
                    self._advance(); self._advance()
                    value.append("\t")
                    continue
                else:
                    value.append(c)
            elif c == "\n":
                value.append("\n")
                self._advance()
                self.line  += 1
                self.column = 1
                continue
            else:
                value.append(c)

            self._advance()

        raise LexerError(
            "Triple-quoted string was never closed — "
            "did you forget the closing \"\"\"?",
            start_line, start_column
        )

    def _read_number(self):
        """
        Read a numeric literal. Supports:
          - integers:            42
          - floats:              3.14
          - underscore sep:      1_000_000   →  1000000
          - scientific notation: 1.5e-3      →  0.0015
          - hex literals:        0xFF        →  255
        """
        # ── Hex literal: 0x... / 0X... ────────────────────────
        if (self._current() == "0" and not self._at_end()
                and self._peek().lower() == "x"):
            self._advance()  # consume '0'
            self._advance()  # consume 'x'
            hex_digits = []
            while not self._at_end() and (
                    self._current() in "0123456789abcdefABCDEF_"):
                if self._current() != "_":
                    hex_digits.append(self._current())
                self._advance()
            if not hex_digits:
                raise LexerError(
                    "Invalid hex literal — expected digits after '0x'.",
                    self.line, self.column)
            self._add_token(TokenType.INTEGER,
                            int("".join(hex_digits), 16))
            return

        # ── Decimal integer or float ───────────────────────────
        value    = []
        is_float = False

        # Integer part (underscores allowed as separators)
        while not self._at_end() and (self._current().isdigit()
                                       or self._current() == "_"):
            if self._current() != "_":
                value.append(self._current())
            self._advance()

        # Optional decimal point
        if (not self._at_end() and self._current() == "."
                and self._peek().isdigit()):
            is_float = True
            value.append(".")
            self._advance()
            while not self._at_end() and (self._current().isdigit()
                                           or self._current() == "_"):
                if self._current() != "_":
                    value.append(self._current())
                self._advance()

        # Optional scientific notation: e / E followed by optional +/- and digits
        if (not self._at_end()
                and self._current().lower() == "e"
                and (self._peek().isdigit()
                     or self._peek() in ("+", "-"))):
            is_float = True
            value.append("e")
            self._advance()                   # consume 'e'
            if not self._at_end() and self._current() in ("+", "-"):
                value.append(self._current())
                self._advance()               # consume sign
            if self._at_end() or not self._current().isdigit():
                raise LexerError(
                    "Invalid scientific notation — "
                    "expected digits after exponent.",
                    self.line, self.column)
            while not self._at_end() and self._current().isdigit():
                value.append(self._current())
                self._advance()

        raw = "".join(value)
        if is_float:
            self._add_token(TokenType.FLOAT, float(raw))
        else:
            self._add_token(TokenType.INTEGER, int(raw))

    def _read_identifier(self):
        """Read an identifier or keyword."""
        value = []
        while not self._at_end() and (self._current().isalnum()
                                       or self._current() == "_"):
            value.append(self._current())
            self._advance()

        word = "".join(value)

        # ── f-string prefix: f"..." or f'...' ─────────────────
        if word == "f" and not self._at_end() and self._current() in ('"', "'"):
            self._read_fstring()
            return

        tok_type = KEYWORDS.get(word, TokenType.IDENTIFIER)

        # Boolean values get their Python equivalent
        if word == "true":
            self._add_token(tok_type, True)
        elif word == "false":
            self._add_token(tok_type, False)
        elif word == "null":
            self._add_token(tok_type, None)
        else:
            self._add_token(tok_type, word)

    def _read_symbol(self):
        """Read an operator or punctuation character."""
        char = self._current()
        next_char = self._peek()

        # ── Two-character operators ───────────────────────────
        two = char + next_char

        if two == "==":
            self._add_token(TokenType.EQUALS,     "=="); self._advance(); self._advance(); return
        if two == "!=":
            self._add_token(TokenType.NOT_EQUALS,  "!="); self._advance(); self._advance(); return
        if two == "<=":
            self._add_token(TokenType.LESS_EQ,    "<="); self._advance(); self._advance(); return
        if two == ">=":
            self._add_token(TokenType.GREATER_EQ, ">="); self._advance(); self._advance(); return
        if two == "**":
            self._add_token(TokenType.POWER,       "**"); self._advance(); self._advance(); return
        if two == "->":
            self._add_token(TokenType.ARROW,       "->"); self._advance(); self._advance(); return
        if two == "|>":
            self._add_token(TokenType.PIPE,        "|>"); self._advance(); self._advance(); return
        if two == "+=":
            self._add_token(TokenType.PLUS_EQUAL,  "+="); self._advance(); self._advance(); return
        if two == "-=":
            self._add_token(TokenType.MINUS_EQUAL, "-="); self._advance(); self._advance(); return
        if two == "*=":
            self._add_token(TokenType.STAR_EQUAL,  "*="); self._advance(); self._advance(); return
        if two == "//":
            self._add_token(TokenType.FLOOR_DIVIDE, "//"); self._advance(); self._advance(); return
        if two == "/=":
            self._add_token(TokenType.SLASH_EQUAL, "/="); self._advance(); self._advance(); return

        # ── Single-character operators ────────────────────────
        single = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.MULTIPLY,
            "/": TokenType.DIVIDE,
            "@": TokenType.AT,
            "%": TokenType.MODULO,
            "<": TokenType.LESS,
            ">": TokenType.GREATER,
            "=": TokenType.ASSIGN,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ".": TokenType.DOT,
        }

        # ── Range operator: .. (must check before single-char '.') ─
        if char == "." and not self._at_end() and self._peek() == ".":
            self._add_token(TokenType.DOTDOT, "..")
            self._advance()   # consume first  '.'
            self._advance()   # consume second '.'
            return

        if char in single:
            self._add_token(single[char], char)
            self._advance()
            if char in ("(", "[", "{"):
                self.bracket_depth += 1
            elif char in (")", "]", "}"):
                self.bracket_depth = max(0, self.bracket_depth - 1)
            return

        # ── Unknown character ─────────────────────────────────
        raise LexerError(
            f"Unexpected character '{char}' — "
            f"NEKOVA doesn't know what this means.",
            self.line, self.column
        )

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------

    def _current(self) -> str:
        """Return the character at the current position."""
        if self._at_end():
            return "\0"
        return self.source[self.pos]

    def _peek(self) -> str:
        """Look at the NEXT character without consuming it."""
        if self.pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.pos + 1]

    def _advance(self) -> str:
        """Consume the current character and move forward."""
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line  += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _at_end(self) -> bool:
        """Returns True when we've consumed the entire source."""
        return self.pos >= len(self.source)

    def _add_token(self, type: TokenType, value: object):
        """Create a Token and add it to the list."""
        self.tokens.append(Token(type, value, self.line, self.column))