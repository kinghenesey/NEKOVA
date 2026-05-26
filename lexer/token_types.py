# =============================================================
# AION Lexer — Token Types
# =============================================================
# Every possible token in the AION language is defined here.
# Think of these as labels — the lexer will attach one of
# these labels to every piece of code it reads.

from enum import Enum, auto


class TokenType(Enum):

    # ── Literals ──────────────────────────────────────────────
    # Raw values written directly in code
    INTEGER     = auto()   # 42
    FLOAT       = auto()   # 3.14
    STRING      = auto()   # "hello"
    BOOLEAN     = auto()   # true / false
    NULL        = auto()   # null

    # ── Identifiers ───────────────────────────────────────────
    # Variable names, function names, etc.
    IDENTIFIER  = auto()   # name, age, result

    # ── Keywords ──────────────────────────────────────────────
    # Reserved words that mean something in AION
    SHOW        = auto()   # show
    IF          = auto()   # if
    ELSE        = auto()   # else
    REPEAT      = auto()   # repeat
    WHILE       = auto()   # while
    TRY         = auto()   # try
    CATCH       = auto()   # catch
    FOR         = auto()   # for
    IN          = auto()   # in
    TASK        = auto()   # task (functions)
    RETURN      = auto()   # return
    USE         = auto()   # use (imports)
    IMPORT      = auto()   # import (alias for use)
    AND         = auto()   # and
    OR          = auto()   # or
    NOT         = auto()   # not
    THINK       = auto()   # think (agent reasoning)
    MODEL       = auto()   # model (specify LLM for a think step)
    AUTONOMOUS  = auto()   # autonomous
    PARALLEL    = auto()   # parallel
    MEMORY      = auto()   # memory (agent memory access)
    SANDBOX     = auto()   # sandbox (execute code in a safe environment)
    STRICT      = auto()   # strict (enforce stricter rules for a block)
    RELAXED     = auto()   # relaxed (enforce looser rules for a block)

    # ── Operators ─────────────────────────────────────────────
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    MULTIPLY    = auto()   # *
    DIVIDE      = auto()   # /
    MODULO      = auto()   # %
    POWER       = auto()   # **
    ARROW       = auto()   # -> (used in function definitions)

    # ── Comparison ────────────────────────────────────────────
    EQUALS      = auto()   # ==
    NOT_EQUALS  = auto()   # !=
    LESS        = auto()   # <
    LESS_EQ     = auto()   # <=
    GREATER     = auto()   # >
    GREATER_EQ  = auto()   # >=

    # ── Assignment ────────────────────────────────────────────
    ASSIGN      = auto()   # =

    # ── Punctuation ───────────────────────────────────────────
    COLON       = auto()   # :
    DOT         = auto()   # .
    COMMA       = auto()   # ,
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    LBRACE      = auto()   # {
    RBRACE      = auto()   # }

    # ── Structure ─────────────────────────────────────────────
    NEWLINE     = auto()   # end of line
    INDENT      = auto()   # increased indentation
    DEDENT      = auto()   # decreased indentation
    EOF         = auto()   # end of file


# ── Keyword map ───────────────────────────────────────────────
# Maps raw strings to their token type.
# When the lexer sees the word "show" it looks it up here.

KEYWORDS = {
    "show":   TokenType.SHOW,
    "if":     TokenType.IF,
    "else":   TokenType.ELSE,
    "repeat": TokenType.REPEAT,
    "while":  TokenType.WHILE,
    "try":    TokenType.TRY,
    "catch":  TokenType.CATCH,
    "for":    TokenType.FOR,
    "in":     TokenType.IN,
    "task":   TokenType.TASK,
    "return": TokenType.RETURN,
    "use":    TokenType.USE,
    "import": TokenType.IMPORT,
    "and":    TokenType.AND,
    "or":     TokenType.OR,
    "not":    TokenType.NOT,
    "true":   TokenType.BOOLEAN,
    "false":  TokenType.BOOLEAN,
    "null":   TokenType.NULL,
    "think":  TokenType.THINK,
    "model":  TokenType.MODEL,
    "autonomous": TokenType.AUTONOMOUS,
    "parallel": TokenType.PARALLEL,
    "memory": TokenType.MEMORY,
    "sandbox": TokenType.SANDBOX,
    "strict": TokenType.STRICT,
    "relaxed": TokenType.RELAXED
}