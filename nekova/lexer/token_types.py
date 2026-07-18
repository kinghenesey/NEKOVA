# =============================================================
# NEKOVA Lexer — Token Types
# =============================================================
from enum import Enum, auto


class TokenType(Enum):

    # ── Literals ──────────────────────────────────────────────
    INTEGER     = auto()
    FLOAT       = auto()
    MONEY       = auto()   # $0.01 — Phase 26c think budgets in dollars
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
    CONST       = auto()
    ENUM        = auto()
    CONVERSE    = auto()

    # ── Pattern Matching (Phase 7) ────────────────────────────
    MATCH       = auto()
    WHEN        = auto()
    ELIF        = auto()
    BREAK       = auto()
    CONTINUE    = auto()
    GLOBAL      = auto()

    # ── Web DSL (Phase 7) ─────────────────────────────────────
    ROUTE       = auto()
    SERVE       = auto()

    # ── AI Memory (Phase 9) ──────────────────────────────────
    REMEMBER    = auto()
    RECALL      = auto()
    FORGET      = auto()
    AS          = auto()

    # ── Phase 17: Power User Layer ───────────────────────────
    YIELD       = auto()   # yield expr
    AT          = auto()   # @decorator
    ERROR_TYPE  = auto()   # error NetworkError: ...
    CLASS       = auto()   # class (alias for object)

    # ── Phase 16: Standout Features ──────────────────────────
    SPEAK       = auto()   # speak "Hello"
    LISTEN      = auto()   # let x = listen
    EVERY       = auto()   # every 5s: ...
    TEST        = auto()   # test "label": ...
    EXPECT      = auto()   # expect expr == val
    IMAGINE     = auto()   # imagine "prompt"
    SHAPE       = auto()   # shape User: name str
    WATCH       = auto()   # watch "file.txt": ...

    # ── Phase 21: Prompt Blocks + Retry/Fallback ─────────────
    PROMPT      = auto()   # prompt name(args): """template {var}"""
    RETRY       = auto()   # retry 3 times [with exponential backoff]: ...
    FALLBACK    = auto()   # fallback: ...  (sibling clause of retry)

    # ── Phase 22: Observability + Testing + Pipe Operator ────
    OBSERVE     = auto()   # observe "label" with tags {...}: ...
    MOCK        = auto()   # mock think as "response"
    PIPE        = auto()   # |>  (pipe operator)

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
    FLOOR_DIVIDE = auto()  # //
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
    DOTDOT      = auto()   # range operator: 'a'..'z'  or  0..9
    ELLIPSIS    = auto()   # rest/spread marker: let [first, ...rest] = list
    QUESTION_DOT = auto()  # optional chaining: user?.email
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
    "const":      TokenType.CONST,
    "enum":       TokenType.ENUM,
    "converse":   TokenType.CONVERSE,
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
    "global":     TokenType.GLOBAL,
    "route":      TokenType.ROUTE,
    "serve":      TokenType.SERVE,
    # Phase 9
    "remember":   TokenType.REMEMBER,
    "recall":     TokenType.RECALL,
    "forget":     TokenType.FORGET,
    "as":         TokenType.AS,
    # Phase 16
    "yield":      TokenType.YIELD,
    "error":      TokenType.ERROR_TYPE,
    "class":      TokenType.CLASS,
    "speak":      TokenType.SPEAK,
    "listen":     TokenType.LISTEN,
    "every":      TokenType.EVERY,
    "test":       TokenType.TEST,
    "expect":     TokenType.EXPECT,
    "imagine":    TokenType.IMAGINE,
    "shape":      TokenType.SHAPE,
    "watch":      TokenType.WATCH,
    # Phase 21
    # NOTE: "prompt" is intentionally NOT a hard keyword — existing
    # NEKOVA code (e.g. examples/mood_tracker.nk) already uses
    # `prompt` as an ordinary variable name. It's handled as a soft
    # keyword in the parser instead (see _looks_like_prompt_def),
    # same treatment as "pass"/"assert"/"raise".
    "retry":      TokenType.RETRY,
    "fallback":   TokenType.FALLBACK,
    # Phase 22
    "observe":    TokenType.OBSERVE,
    "mock":       TokenType.MOCK,
}