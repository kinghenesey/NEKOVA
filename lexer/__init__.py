# =============================================================
# NEKOVA Lexer — Package Init
# =============================================================
# This makes the lexer importable from anywhere like:
#   from lexer import Lexer
# instead of:
#   from lexer.lexer import Lexer

from lexer.lexer import Lexer, LexerError
from lexer.token import Token
from lexer.token_types import TokenType, KEYWORDS