# =============================================================
# NEKOVA Lexer — Token Class
# =============================================================
# A Token is a single labelled piece of your source code.
# Every word, number, symbol and operator becomes one Token.
#
# Example:
#   source:  show "Hello"
#   tokens:  Token(SHOW, 'show', line=1)
#            Token(STRING, 'Hello', line=1)

from lexer.token_types import TokenType


class Token:
    """
    Represents a single token in the NEKOVA source code.

    Attributes:
        type    — what kind of token this is (from TokenType)
        value   — the actual text from the source code
        line    — which line it appeared on (for error messages)
        column  — which column it appeared on (for error messages)
    """

    def __init__(self, type: TokenType, value: object,
                 line: int = 0, column: int = 0):
        self.type   = type
        self.value  = value
        self.line   = line
        self.column = column

    def __repr__(self):
        """How the token looks when printed — useful for debugging."""
        return (f"Token({self.type.name}, "
                f"{repr(self.value)}, "
                f"line={self.line})")

    def __eq__(self, other):
        """Two tokens are equal if they have the same type and value."""
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.value == other.value

    def is_type(self, *types: TokenType) -> bool:
        """
        Convenience method — check if this token matches
        one or more types.

        Usage:
            token.is_type(TokenType.SHOW)
            token.is_type(TokenType.IF, TokenType.ELSE)
        """
        return self.type in types