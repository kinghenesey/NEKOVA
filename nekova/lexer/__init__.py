# =============================================================
# NEKOVA Lexer — Package Init
# =============================================================
# This makes the lexer importable from anywhere like:
#   from lexer import Lexer
# instead of:
#   from lexer.lexer import Lexer

from nekova.lexer.lexer import Lexer, LexerError
from nekova.lexer.token import Token
from nekova.lexer.token_types import TokenType, KEYWORDS
