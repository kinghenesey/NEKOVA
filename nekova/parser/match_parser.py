# =============================================================
# NEKOVA Parser — Pattern Matching Mixin (Phase 7)
# =============================================================
from nekova.lexer.token_types import TokenType
from nekova.parser.nodes import MatchStatement, MatchArm

# Type-name keywords/identifiers that trigger a type check
_TYPE_NAMES = {"text", "number", "boolean", "list", "dict", "any", "null"}


class MatchParserMixin:
    """
    Mixin that adds match/when parsing to the main Parser.

    Syntax:
        match <expr>:
            when <value>: <body>
            when <type>:  <body>
            else:         <body>

    The when/else arms live inside the INDENT/DEDENT block that
    follows the match colon, just like if/while/for bodies do.
    """

    def _parse_match(self) -> MatchStatement:
        """Parse a full match statement."""
        self._advance()           # consume 'match'

        subject = self._parse_expression()

        self._consume(TokenType.COLON)
        self._skip_newlines()

        # Consume the INDENT that wraps all the when/else arms
        if self._current().type == TokenType.INDENT:
            self._advance()

        arms = []

        while not self._at_end():
            self._skip_newlines()
            tok = self._current()

            # End of the match block
            if tok.type in (TokenType.DEDENT, TokenType.EOF):
                break

            # ── else arm ──────────────────────────────────────
            if tok.type == TokenType.ELSE:
                self._advance()                      # consume 'else'
                self._consume(TokenType.COLON)
                body = self._parse_inline_or_block()
                arms.append(MatchArm(None, body, is_else=True))
                self._skip_newlines()
                break                                # else is always last

            # ── when arm ──────────────────────────────────────
            if tok.type == TokenType.WHEN:
                self._advance()                      # consume 'when'

                cur = self._current()
                is_type_check = False
                is_range      = False
                range_end     = None
                pattern       = None

                if cur.type == TokenType.IDENTIFIER:
                    name = cur.value
                    next_idx = self.pos + 1
                    next_tok = (self.tokens[next_idx]
                                if next_idx < len(self.tokens)
                                else self._current())
                    # It's a type check if:
                    #   name is a built-in type word ("text", "number", …), OR
                    #   name starts with uppercase and is followed by a colon
                    if (name in _TYPE_NAMES or
                            (name[0].isupper() and
                             next_tok.type == TokenType.COLON)):
                        is_type_check = True
                        pattern       = name
                        self._advance()              # consume type name
                    else:
                        pattern = self._parse_expression()
                else:
                    pattern = self._parse_expression()

                # ── Range pattern: when 'a'..'z' or when 0..9 ─
                if self._current().type == TokenType.DOTDOT:
                    self._advance()                  # consume '..'
                    range_end = self._parse_expression()
                    is_range  = True

                self._consume(TokenType.COLON)
                body = self._parse_inline_or_block()
                arms.append(MatchArm(pattern, body,
                                     is_type_check=is_type_check,
                                     is_range=is_range,
                                     range_end=range_end))
                continue

            # Anything unrecognised ends the match block
            break

        # Consume the closing DEDENT
        if self._current().type == TokenType.DEDENT:
            self._advance()

        return MatchStatement(subject, arms)

    # ----------------------------------------------------------
    # Helper: parse either an inline statement or an indented block
    # ----------------------------------------------------------
    def _parse_inline_or_block(self) -> list:
        """
        After the colon of a when/else arm, parse:
          - an inline statement on the same line (no NEWLINE yet), OR
          - a full INDENT-block on subsequent lines
        """
        cur = self._current()

        if cur.type == TokenType.NEWLINE:
            # _parse_block handles: skip newlines, consume INDENT,
            # parse stmts until DEDENT, consume DEDENT
            return self._parse_block()

        # Inline: single statement right after the colon
        stmt = self._parse_statement()
        self._skip_newlines()
        return [stmt] if stmt else []