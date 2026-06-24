# =============================================================
# NEKOVA Lexer — Token Types
# =============================================================
from enum import Enum, auto


class TokenType(Enum):

    # ── Literals ──────────────────────────────────────────────
    INTEGER     = auto()
    FLOAT       = auto()
    STRING      = auto()
    F_STRING    = auto()
    BOOLEAN     = auto()
    NULL        = auto()

    # ── Identifiers ───────────────────────────────────────────
    IDENTIFIER  = auto()

    # ── Keywords ──────────────────────────────────────────────
    SHOW        = auto()
    IF          = auto()
    ELSE        = auto()
    REPEAT      = auto()
    WHILE       = auto()
    TRY         = auto()
    CATCH       = auto()
    FOR         = auto()
    IN          = auto()
    TASK        = auto()
    RETURN      = auto()
    USE         = auto()
    IMPORT      = auto()
    AND         = auto()
    OR          = auto()
    NOT         = auto()
    THINK       = auto()
    MODEL       = auto()
    AUTONOMOUS  = auto()
    PARALLEL    = auto()
    MEMORY      = auto()
    SANDBOX     = auto()
    STRICT      = auto()
    RELAXED     = auto()
    PIPELINE_DEF = auto()
    COLLECT     = auto()
    GENERATE    = auto()
    SAVE        = auto()
    WITH        = auto()
    RUN         = auto()

    # ── Async / Await / Streaming / Fetch ────────────
    ASYNC       = auto()
    AWAIT       = auto()
    STREAM      = auto()
    EACH        = auto()
    FETCH       = auto()
    FUNC        = auto()
    OBJECT      = auto()
    NEW         = auto()
    INIT        = auto()
    SELF        = auto()
    LET         = auto()

    # ── Pattern Matching (Phase 7) ────────────────────────────
    MATCH       = auto()
    WHEN        = auto()
    ELIF        = auto()
    BREAK       = auto()
    CONTINUE    = auto()

    # ── Web DSL (Phase 7) ─────────────────────────────────────
    ROUTE       = auto()
    SERVE       = auto()

    # ── AI Memory (Phase 9) ──────────────────────────────────
    REMEMBER    = auto()
    RECALL      = auto()
    FORGET      = auto()
    AS          = auto()

    # ── Operators ─────────────────────────────────────────────
    PLUS        = auto()

    # ── Augmented Assignment (Phase 13) ───────────────────────
    PLUS_EQUAL  = auto()   # +=
    MINUS_EQUAL = auto()   # -=
    STAR_EQUAL  = auto()   # *=
    SLASH_EQUAL = auto()   # /=
    MINUS       = auto()
    MULTIPLY    = auto()
    DIVIDE      = auto()
    MODULO      = auto()
    POWER       = auto()
    ARROW       = auto()

    # ── Comparison ────────────────────────────────────────────
    EQUALS      = auto()
    NOT_EQUALS  = auto()
    LESS        = auto()
    LESS_EQ     = auto()
    GREATER     = auto()
    GREATER_EQ  = auto()

    # ── Assignment ────────────────────────────────────────────
    ASSIGN      = auto()

    # ── Punctuation ───────────────────────────────────────────
    COLON       = auto()
    DOT         = auto()
    COMMA       = auto()
    LPAREN      = auto()
    RPAREN      = auto()
    LBRACKET    = auto()
    RBRACKET    = auto()
    LBRACE      = auto()
    RBRACE      = auto()

    # ── Structure ─────────────────────────────────────────────
    NEWLINE     = auto()
    INDENT      = auto()
    DEDENT      = auto()
    EOF         = auto()


# ── Keyword map ───────────────────────────────────────────────
KEYWORDS = {
    "show":       TokenType.SHOW,
    "if":         TokenType.IF,
    "else":       TokenType.ELSE,
    "repeat":     TokenType.REPEAT,
    "while":      TokenType.WHILE,
    "try":        TokenType.TRY,
    "catch":      TokenType.CATCH,
    "for":        TokenType.FOR,
    "in":         TokenType.IN,
    "task":       TokenType.TASK,
    "return":     TokenType.RETURN,
    "use":        TokenType.USE,
    "import":     TokenType.IMPORT,
    "and":        TokenType.AND,
    "or":         TokenType.OR,
    "not":        TokenType.NOT,
    "true":       TokenType.BOOLEAN,
    "false":      TokenType.BOOLEAN,
    "null":       TokenType.NULL,
    "think":      TokenType.THINK,
    "model":      TokenType.MODEL,
    "autonomous": TokenType.AUTONOMOUS,
    "parallel":   TokenType.PARALLEL,
    "memory":     TokenType.MEMORY,
    "sandbox":    TokenType.SANDBOX,
    "strict":     TokenType.STRICT,
    "relaxed":    TokenType.RELAXED,
    "pipeline":   TokenType.PIPELINE_DEF,
    "collect":    TokenType.COLLECT,
    "generate":   TokenType.GENERATE,
    "save":       TokenType.SAVE,
    "with":       TokenType.WITH,
    "run":        TokenType.RUN,
    "async":      TokenType.ASYNC,
    "await":      TokenType.AWAIT,
    "stream":     TokenType.STREAM,
    "each":       TokenType.EACH,
    "fetch":      TokenType.FETCH,
    "func":       TokenType.FUNC,
    "let":        TokenType.LET,
    "object":     TokenType.OBJECT,
    "new":        TokenType.NEW,
    "init":       TokenType.INIT,
    "self":       TokenType.SELF,
    # Phase 7
    "match":      TokenType.MATCH,
    "when":       TokenType.WHEN,
    "elif":       TokenType.ELIF,
    "break":      TokenType.BREAK,
    "continue":   TokenType.CONTINUE,
    "route":      TokenType.ROUTE,
    "serve":      TokenType.SERVE,
    # Phase 9
    "remember":   TokenType.REMEMBER,
    "recall":     TokenType.RECALL,
    "forget":     TokenType.FORGET,
    "as":         TokenType.AS,
}