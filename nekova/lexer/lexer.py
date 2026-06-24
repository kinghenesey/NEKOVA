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
        """
        self._add_token(TokenType.NEWLINE, "\\n")
        self._advance()  # consume the \n

        # Count leading whitespace (spaces and tabs)
        indent = 0
        while not self._at_end() and self._current() in (" ", "\t"):
            if self._current() == "\t":
                indent += 4  # 1 tab = 4 spaces
            else:
                indent += 1
            self._advance()


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
        Read an f-string literal: f"Hello {name}!"
        Stores the raw string value — interpolation is
        handled at parse time by _parse_fstring().
        """
        quote = self._current()
        self._advance()  # skip opening quote

        value = []
        while not self._at_end() and self._current() != quote:
            if self._current() == "\\" and self._peek() in ('"', "'", "n", "t", "\\"):
                escape = self._peek()
                self._advance()
                self._advance()
                if escape == "n":
                    value.append("\n")
                elif escape == "t":
                    value.append("\t")
                else:
                    value.append(escape)
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

    def _read_number(self):
        """Read an integer or float literal."""
        value  = []
        is_float = False

        while not self._at_end() and self._current().isdigit():
            value.append(self._current())
            self._advance()

        # Check for decimal point
        if (not self._at_end() and self._current() == "."
                and self._peek().isdigit()):
            is_float = True
            value.append(".")
            self._advance()
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
        if two == "+=":
            self._add_token(TokenType.PLUS_EQUAL,  "+="); self._advance(); self._advance(); return
        if two == "-=":
            self._add_token(TokenType.MINUS_EQUAL, "-="); self._advance(); self._advance(); return
        if two == "*=":
            self._add_token(TokenType.STAR_EQUAL,  "*="); self._advance(); self._advance(); return
        if two == "/=":
            self._add_token(TokenType.SLASH_EQUAL, "/="); self._advance(); self._advance(); return

        # ── Single-character operators ────────────────────────
        single = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.MULTIPLY,
            "/": TokenType.DIVIDE,
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

        if char in single:
            self._add_token(single[char], char)
            self._advance()
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