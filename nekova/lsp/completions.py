# =============================================================
# NEKOVA LSP — Completions
# =============================================================
# Two completion contexts:
#
#   1. General expression position: keywords, builtin functions, and
#      every task/prompt/class/method/variable name declared anywhere
#      in the document. Variable completions are document-wide rather
#      than properly scope-narrowed (a variable declared inside one
#      task will also show up while completing in a different,
#      unrelated task) — real scope resolution is a substantially
#      bigger undertaking, and over-suggesting is the safer default
#      for a first version: worst case, picking a suggestion that
#      isn't actually in scope is caught by NEKOVA's existing
#      "variable not found" diagnostics, not silently wrong.
#
#   2. Right after `obj.`: method names. NEKOVA has no static type
#      system, so which methods apply depends on the last thing
#      assigned to `obj`. A best-effort literal-type check (was it
#      last assigned a plain string/list/dict literal?) narrows the
#      suggestions when it can; otherwise every method from all three
#      of string/list/dict's real dispatch tables is offered rather
#      than guessing wrong and hiding a valid one.
#
# Method name lists below are copied from the interpreter's own
# dispatch tables in _exec_MethodCall (interpreter.py) — not a
# separately hand-maintained list that could drift out of sync with
# what's actually callable.

from nekova.lexer.lexer import Lexer, LexerError
from nekova.lexer.token_types import TokenType
from nekova.parser.parser import Parser
from nekova.parser.nodes import (
    AssignStatement, StringLiteral, FStringLiteral, ListLiteral, DictLiteral,
)
from nekova.lsp.hover import KEYWORD_DOCS, BUILTIN_DOCS, _iter_bodies

KIND_KEYWORD = 14
KIND_FUNCTION = 3
KIND_VARIABLE = 6
KIND_CLASS = 7
KIND_METHOD = 2

STRING_METHODS = [
    "upper", "lower", "title", "strip", "trim", "lstrip", "rstrip",
    "reverse", "length", "split", "replace", "contains", "starts_with",
    "ends_with", "find", "index", "count", "repeat", "join", "format",
    "zfill", "center", "ljust", "rjust", "is_digit", "is_alpha",
    "is_lower", "is_upper", "to_list",
]
LIST_METHODS = [
    "length", "append", "remove", "reverse", "sort", "first", "last",
    "contains", "join", "pop", "clear",
]
DICT_METHODS = [
    "keys", "values", "length", "has", "get", "remove",
]


def _item(label, kind, detail=None):
    d = {"label": label, "kind": kind}
    if detail:
        # First line/sentence only -- completion detail is meant to
        # be a short summary shown inline in the suggestion list, not
        # the full hover-length documentation.
        d["detail"] = detail.split("\n")[0].split(". ")[0].strip()
    return d


def _collect_variable_names(statements, seen=None):
    """
    Recursively collect every name bound by a `let`/`const`
    (AssignStatement), anywhere in the document — including inside
    nested task bodies, matching how deeply hover's _iter_bodies
    looks for task/class definitions.
    """
    if seen is None:
        seen = set()
    for stmt in statements:
        if isinstance(stmt, AssignStatement):
            seen.add(stmt.name)
        body = getattr(stmt, "body", None)
        if body:
            _collect_variable_names(body, seen)
        init_body = getattr(stmt, "init_body", None)
        if init_body:
            _collect_variable_names(init_body, seen)
        methods = getattr(stmt, "methods", None)
        if methods:
            for m in methods:
                if getattr(m, "body", None):
                    _collect_variable_names(m.body, seen)
    return seen


def _infer_literal_kind(statements, var_name):
    """
    Best-effort: find the most recent `let`/`const` assignment to
    var_name (searching the whole document, including nested task
    bodies, in source order) and, if its value is a plain literal,
    return "string", "list", or "dict". Returns None if no assignment
    is found or the value isn't a literal NEKOVA can tell the type of
    without actually running the program (e.g. a function call or
    another variable) — callers should fall back to offering every
    method in that case rather than guessing.
    """
    matches = []

    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, AssignStatement) and stmt.name == var_name:
                matches.append(stmt)
            body = getattr(stmt, "body", None)
            if body:
                walk(body)
            init_body = getattr(stmt, "init_body", None)
            if init_body:
                walk(init_body)
            methods = getattr(stmt, "methods", None)
            if methods:
                for m in methods:
                    if getattr(m, "body", None):
                        walk(m.body)

    walk(statements)
    if not matches:
        return None

    value = matches[-1].value  # last one seen, in source order — most recent
    if isinstance(value, (StringLiteral, FStringLiteral)):
        return "string"
    if isinstance(value, ListLiteral):
        return "list"
    if isinstance(value, DictLiteral):
        return "dict"
    return None


def _dot_context(source: str, line_1idx: int, character: int):
    """
    If the cursor is positioned right after `<identifier>.` (i.e.
    this is a method-completion request), return that identifier's
    name. Returns None for any other context. Works directly off the
    raw source line rather than the token stream, since the user is
    very likely still mid-edit (nothing typed after the dot yet, or a
    partial method name) and the document may not tokenize/parse
    cleanly at this exact moment.
    """
    lines = source.split("\n")
    if line_1idx - 1 >= len(lines):
        return None
    text = lines[line_1idx - 1][:character]
    if not text.endswith(".") and "." not in text[-20:]:
        return None
    # Walk back from the cursor over an optional partial method name,
    # then require a literal '.', then capture the identifier before it.
    i = character
    text_full = lines[line_1idx - 1]
    j = i
    while j > 0 and (text_full[j - 1].isalnum() or text_full[j - 1] == "_"):
        j -= 1
    if j == 0 or text_full[j - 1] != ".":
        return None
    dot_pos = j - 1
    k = dot_pos
    while k > 0 and (text_full[k - 1].isalnum() or text_full[k - 1] == "_"):
        k -= 1
    if k == dot_pos:
        return None
    return text_full[k:dot_pos]


def _current_word_prefix(source: str, line_1idx: int, character: int) -> str:
    """The partial identifier being typed, for filtering suggestions
    (e.g. typing 'sh' should still suggest 'show')."""
    lines = source.split("\n")
    if line_1idx - 1 >= len(lines):
        return ""
    text = lines[line_1idx - 1][:character]
    j = len(text)
    while j > 0 and (text[j - 1].isalnum() or text[j - 1] == "_"):
        j -= 1
    return text[j:]


def compute_completions(source: str, line: int, character: int) -> list:
    """
    Compute LSP CompletionItem[] for a 0-indexed (line, character)
    position. Always returns a list (possibly empty), never None —
    an empty completion list is a normal, valid response.
    """
    nekova_line = line + 1

    # ── Method-completion context: right after `obj.` ──────────
    dot_name = _dot_context(source, nekova_line, character)
    if dot_name is not None:
        kind_hint = None
        try:
            tokens = Lexer(source).tokenize()
            program = Parser(tokens).parse_best_effort()
            kind_hint = _infer_literal_kind(program.statements, dot_name)
        except LexerError:
            pass  # fall through to the untyped, over-suggest case below

        if kind_hint == "string":
            names = STRING_METHODS
        elif kind_hint == "list":
            names = LIST_METHODS
        elif kind_hint == "dict":
            names = DICT_METHODS
        else:
            # Unknown type: union of all three rather than guessing
            # wrong and hiding a method that's actually valid.
            names = sorted(set(STRING_METHODS) | set(LIST_METHODS) | set(DICT_METHODS))
        return [_item(n, KIND_METHOD) for n in names]

    # ── General expression context ──────────────────────────────
    prefix = _current_word_prefix(source, nekova_line, character)
    items = []

    for kw, doc in KEYWORD_DOCS.items():
        if kw.startswith(prefix):
            items.append(_item(kw, KIND_KEYWORD, doc))

    for name, doc in BUILTIN_DOCS.items():
        if name.startswith(prefix):
            items.append(_item(name, KIND_FUNCTION, doc))

    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse_best_effort()
        for defn in _iter_bodies(program.statements):
            if defn.name.startswith(prefix):
                from nekova.parser.nodes import ClassDefinition
                kind = KIND_CLASS if isinstance(defn, ClassDefinition) else KIND_FUNCTION
                items.append(_item(defn.name, kind))
        for name in _collect_variable_names(program.statements):
            if name.startswith(prefix):
                items.append(_item(name, KIND_VARIABLE))
    except LexerError:
        pass  # keyword/builtin completions still work without a valid AST

    return items