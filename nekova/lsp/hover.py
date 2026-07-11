# =============================================================
# NEKOVA LSP — Hover
# =============================================================
# Resolves the symbol under the cursor and returns documentation:
#   1. A language keyword (let, think, sandbox, every, ...)
#   2. A builtin function (map, filter, len, ...)
#   3. A task/prompt/class defined in the open document itself,
#      pulled straight from its real signature and docstring — not
#      a separate, hand-maintained description that could drift from
#      the actual code.
#
# Resolution order matters: user-defined symbols are checked first,
# so a task that happens to share a name with a builtin (e.g. someone
# defines their own `sort`) shows *their* definition on hover, not
# the builtin's.

from nekova.lexer.lexer import Lexer, LexerError
from nekova.lexer.token_types import TokenType, KEYWORDS
from nekova.parser.parser import Parser
from nekova.parser.nodes import (
    TaskStatement, TypedTaskStatement, ClassDefinition,
    MethodDefinition, PromptStatement,
)

# ── Keyword docs ──────────────────────────────────────────────
# Not every single keyword in KEYWORDS is listed here — soft
# keywords, operators (and/or/not), and a handful of rarely-hovered
# structural ones are left out. Anything missing here still falls
# through cleanly (compute_hover returns None), it just won't show a
# tooltip.
KEYWORD_DOCS = {
    "let":       "Declares a new variable, always in the *current* scope — even if a variable of the same name exists in an enclosing scope (deliberate shadowing).\n\n```\nlet x = 5\n```",
    "const":     "Declares a variable that cannot be reassigned after its first value.\n\n```\nconst PI = 3.14159\n```",
    "task":      "Defines a task (function). Parameters can optionally be typed: `task add(a: int, b: int) -> int:`.\n\n```\ntask greet(name):\n    show \"Hello, \" + name\n```",
    "return":    "Returns a value from the current task and exits it immediately.",
    "show":      "Prints one or more values, separated by commas.\n\n```\nshow \"x is\", x\n```",
    "if":        "Starts a conditional block. Pair with `elif`/`else` for alternatives.",
    "elif":      "An additional condition checked if the preceding `if`/`elif` was false.",
    "else":      "The fallback branch of an `if`/`elif` chain, run when none of the earlier conditions matched.",
    "while":     "Repeats its body as long as the condition stays true.",
    "for":       "Iterates over a collection: `for item in collection:`.",
    "in":        "Used with `for` to iterate a collection, or as a membership check: `x in collection`.",
    "repeat":    "Repeats its body a fixed number of times: `repeat 5:`.",
    "break":     "Exits the innermost enclosing loop immediately.",
    "continue":  "Skips to the next iteration of the innermost enclosing loop.",
    "match":     "Starts a pattern-matching block; pair with `when` for each case.",
    "when":      "A single case inside a `match` block.",
    "try":       "Starts a block whose errors are caught by a following `catch`.",
    "catch":     "Catches an error raised in the preceding `try` block.",
    "global":    "Declares that assignments to this name inside a task should write to the true top-level (global) scope, not a local one.",
    "class":     "Defines a class, with an `init` constructor and methods.",
    "new":       "Creates a new instance of a class: `new Point(1, 2)`.",
    "self":      "Refers to the current instance inside a class method.",
    "init":      "The constructor method of a class, run automatically by `new`.",
    "enum":      "Defines a fixed set of named values.\n\n```\nenum Color:\n    Red\n    Green\n    Blue\n```",
    "error":     "Defines a custom error type that can be `raise`d and `catch`'d by name.",
    "yield":     "Produces one value from a generator task without exiting it — the task resumes after the next call.",
    "async":     "Marks a task as asynchronous; call it with `await`.",
    "await":     "Waits for an async task's result before continuing.",
    "import":    "Loads tasks/variables from another .nk file: `import \"utils.nk\"` or `import square, PI from \"utils.nk\"`.",
    "use":       "Loads a stdlib module: `use database`, `use voice`, `use crypto`, etc.",
    "route":     "Defines a web route (requires `use web`): `route \"/hello\" get:`.",
    "serve":     "Starts the web server for routes defined with `route`.",

    # AI-native constructs — the language's flagship differentiator.
    "think":     "Calls an AI model and returns its response as text. Add `as <format>` (json/list/bool/schema/text) to get a structured, type-coerced result instead.\n\n```\nlet idea = think \"What should I build today?\" as text\n```\nWith no API key configured, returns a `[MOCK AI]` response instead of failing.",
    "speak":     "Converts text to speech and plays it aloud.\n\n```\nspeak \"Hello, world!\"\n```",
    "listen":    "Records audio and transcribes it to text (falls back to typed input if no microphone/API is available).",
    "sandbox":   "Runs its body in an isolated context with restricted operations (no file/network access in `strict` mode). Blocked operations raise a structured violation rather than crashing.\n\n```\nsandbox strict:\n    let result = 1 + 1\nshow sandbox_result[\"safe\"]\n```",
    "every":     "Schedules its body to run repeatedly on an interval, in the background — the rest of the script keeps running immediately after.\n\n```\nevery 5 s:\n    think \"Check for new emails\" as text\n```",
    "converse":  "Starts a multi-turn AI dialogue block with automatic conversation-history tracking across calls.",
    "remember":  "Stores a value in the AI memory store under a key: `remember \"key\" = value`.",
    "recall":    "Retrieves a value from the AI memory store: `recall \"key\"`, or `recall \"key\" or default`.",
    "forget":    "Removes a key from the AI memory store.",
    "imagine":   "Generates an image from a text prompt. Add `as file` to save it to disk (with local caching).",
    "observe":   "Tags and traces a block of execution for observability, e.g. `observe \"pipeline run\" with tags {...}:`.",
    "mock":      "Inside a `test` block, replaces a real AI call with a fixed, deterministic value: `mock think as \"sports\"`.",
    "test":      "Defines a test block, typically paired with `expect` and/or `mock`.",
    "expect":    "Asserts that an expression equals an expected value inside a `test` block.",
    "shape":     "Defines a schema `think ... as <ShapeName>` can coerce its response into.",
    "with":      "Introduces a context block, e.g. `with budget:` for AI cost/token tracking.",
    "watch":     "Watches a file or directory and re-runs on change (used by `nekova watch`-style workflows).",
    "model":     "Explicitly selects which AI model a `think` call should use.",
}

# ── Builtin function docs ─────────────────────────────────────
BUILTIN_DOCS = {
    "len":         "`len(x)` — number of items in a string, list, dict, or set.",
    "length":      "`length(x)` — alias for `len(x)`.",
    "range":       "`range(stop)` / `range(start, stop)` / `range(start, stop, step)` — a sequence of numbers.",
    "str":         "`str(x)` — converts `x` to its string representation.",
    "int":         "`int(x)` — converts `x` to an integer. Raises if `x` doesn't look like a whole number.",
    "float":       "`float(x)` — converts `x` to a decimal number.",
    "bool":        "`bool(x)` — converts `x` to `true`/`false`.",
    "abs":         "`abs(x)` — absolute value of a number.",
    "round":       "`round(x)` / `round(x, digits)` — rounds a number.",
    "min":         "`min(a, b, ...)` or `min(collection)` — the smallest value.",
    "max":         "`max(a, b, ...)` or `max(collection)` — the largest value.",
    "sum":         "`sum(collection)` — adds up all values in a collection.",
    "sorted":      "`sorted(collection)` — returns a new sorted list (method-style; see also the `sort` pipeable global).",
    "sort":        "`sort(collection, reverse=false)` — pipeable: `data |> sort()` returns a new sorted list.",
    "take":        "`take(collection, n)` — pipeable: `data |> take(n)` returns the first `n` items.",
    "map":         "`map(collection, task)` — pipeable: `data |> map(double)` applies `task` to every item, returning a new list.",
    "filter":      "`filter(collection, task)` — pipeable: `data |> filter(is_valid)` keeps only items where `task` returns true.",
    "reversed":    "`reversed(collection)` — returns the collection in reverse order.",
    "list":        "`list(x)` — converts `x` (e.g. a set, or an iterable) to a list.",
    "dict":        "`dict()` — creates an empty dictionary, or converts pairs to one.",
    "enumerate":   "`enumerate(collection, start=0)` — pairs each item with its index.",
    "zip":         "`zip(a, b, ...)` — pairs up items from multiple collections positionally.",
    "any":         "`any(collection)` — true if at least one item is truthy.",
    "all":         "`all(collection)` — true if every item is truthy.",
    "isinstance":  "`isinstance(x, type)` — checks whether `x` is of the given type.",
    "callable":    "`callable(x)` — true if `x` can be called like a task.",
    "type_of":     "`type_of(x)` — the name of `x`'s runtime type, as a string.",
    "to_number":   "`to_number(x)` — parses `x` (e.g. a string) into a number.",
    "to_text":     "`to_text(x)` — same as `str(x)`.",
    "chr":         "`chr(code)` — the character for a Unicode code point.",
    "ord":         "`ord(char)` — the Unicode code point of a single character.",
    "hex":         "`hex(n)` — the hexadecimal string for an integer.",
    "oct":         "`oct(n)` — the octal string for an integer.",
    "bin":         "`bin(n)` — the binary string for an integer.",
    "pow":         "`pow(base, exp)` — `base` raised to `exp`.",
    "divmod":      "`divmod(a, b)` — `[a // b, a % b]` as a two-item list.",
    "sqrt":        "`sqrt(x)` — square root.",
    "floor":       "`floor(x)` — rounds down to the nearest integer.",
    "ceil":        "`ceil(x)` — rounds up to the nearest integer.",
    "log":         "`log(x)` / `log(x, base)` — logarithm (natural, or given base).",
    "sin":         "`sin(x)` — sine of `x` (radians).",
    "cos":         "`cos(x)` — cosine of `x` (radians).",
    "tan":         "`tan(x)` — tangent of `x` (radians).",
    "input":       "`input(prompt=\"\")` — reads a line of text typed by the user.",
    "print":       "`print(...)` — like `show`, but without NEKOVA's formatting conventions.",
    "sleep":       "`sleep(seconds)` — pauses execution for the given number of seconds.",
    "clear":       "`clear()` — clears the terminal screen.",
    "random_num":  "`random_num(min, max)` — a random number in the given range.",
    "ask":         "`ask(prompt)` — reads a line of typed input with a prompt.",
    "doc":         "`doc(task)` — returns a task's docstring, if it has one.",
    "ai_usage":    "`ai_usage()` — returns AI cost/token usage tracked so far (see `with budget:`).",
    "sandbox_run": "`sandbox_run(...)` — runs code inside a sandbox programmatically.",
    "file_read":   "`file_read(path)` — reads a file's contents as text.",
    "file_write":  "`file_write(path, content)` — writes text to a file, overwriting it.",
    "file_append": "`file_append(path, content)` — appends text to a file.",
    "file_exists": "`file_exists(path)` — true if the given path exists.",
    "file_delete": "`file_delete(path)` — deletes a file.",
    "date_now":    "`date_now()` — the current date and time.",
    "date_today":  "`date_today()` — today's date.",
    "date_timestamp": "`date_timestamp()` — the current Unix timestamp.",
    "date_format": "`date_format(date, fmt)` — formats a date as a string.",
    "date_add_days": "`date_add_days(date, n)` — a date `n` days from the given one.",
    "date_diff_days": "`date_diff_days(a, b)` — number of days between two dates.",
    "date_day_of_week": "`date_day_of_week(date)` — which day of the week a date falls on.",
    "connect":     "`connect(...)` — opens a connection (context-dependent on the stdlib module in `use`).",
    "args":        "`args()` — the command-line arguments passed to the running script.",
}


def _find_position_in_tokens(tokens, target_line, target_char):
    """
    Find the token whose span covers (target_line, target_char) —
    target_line already converted to NEKOVA's 1-indexed line numbers
    by the caller; target_char is still LSP's 0-indexed character
    offset.

    NEKOVA's own Token.column is 1-indexed AND points to the
    position *right after* the token ends, not where it starts (e.g.
    for "task" starting at the very beginning of a line, column is
    5, not 1 — confirmed directly against the lexer, not assumed).
    So a token's LSP-style [start, end) range is:
        start = token.column - width - 1
        end   = token.column - 1
    """
    for tok in tokens:
        if tok.line != target_line:
            continue
        width = max(1, len(str(tok.value)))
        lsp_start = tok.column - width - 1
        lsp_end = tok.column - 1
        if lsp_start <= target_char < lsp_end:
            return tok, lsp_start, lsp_end
    return None, None, None


def _iter_bodies(statements):
    """
    Yield every TaskStatement/TypedTaskStatement/ClassDefinition/
    MethodDefinition/PromptStatement reachable from `statements`,
    recursing into nested task bodies, class methods, and init
    blocks — so hovering over a nested task (a closure, e.g. the
    counter-factory pattern) still finds its definition, not just
    top-level ones.
    """
    for stmt in statements:
        if isinstance(stmt, (TaskStatement, TypedTaskStatement, PromptStatement)):
            yield stmt
            if getattr(stmt, "body", None):
                yield from _iter_bodies(stmt.body)
        elif isinstance(stmt, ClassDefinition):
            yield stmt
            if stmt.init_body:
                yield from _iter_bodies(stmt.init_body)
            for method in stmt.methods:
                yield method
                if method.body:
                    yield from _iter_bodies(method.body)
        elif isinstance(stmt, MethodDefinition):
            yield stmt
            if stmt.body:
                yield from _iter_bodies(stmt.body)


def _format_params(params) -> str:
    """
    Render a params list as a signature fragment. Handles both
    TaskStatement's 3-tuples (name, default, is_vararg) and
    TypedTaskStatement's 4-tuples (name, type_hint, default,
    is_vararg) — whichever this particular node's params are.
    """
    parts = []
    for p in params:
        if len(p) == 4:
            name, type_hint, default, is_vararg = p
        else:
            name, default, is_vararg = p
            type_hint = None
        piece = ("*" if is_vararg else "") + name
        if type_hint:
            piece += f": {type_hint}"
        parts.append(piece)
    return ", ".join(parts)


def _hover_for_definition(node) -> str:
    """Build a markdown hover string for a user-defined task, prompt,
    class, or method — using its real signature and docstring
    straight from the parsed source, not a separately maintained
    description that could go stale."""
    if isinstance(node, ClassDefinition):
        header = f"class {node.name}"
        if node.parent:
            header += f"({node.parent})"
        lines = [f"```\n{header}\n```"]
        if node.methods:
            method_names = ", ".join(m.name for m in node.methods)
            lines.append(f"Methods: {method_names}")
        return "\n\n".join(lines)

    params = _format_params(node.params)
    return_type = getattr(node, "return_type", None)
    kind = "prompt" if isinstance(node, PromptStatement) else \
           "task" if isinstance(node, (TaskStatement, TypedTaskStatement)) else \
           "method"
    sig = f"{kind} {node.name}({params})"
    if return_type:
        sig += f" -> {return_type}"
    lines = [f"```\n{sig}\n```"]
    docstring = getattr(node, "docstring", None)
    if docstring:
        lines.append(docstring.strip())
    return "\n\n".join(lines)


def compute_hover(source: str, line: int, character: int):
    """
    Compute LSP hover contents for a 0-indexed (line, character)
    position. Returns a dict shaped like an LSP Hover result, or None
    if there's nothing to show (no symbol under the cursor, or an
    unrecognized one).

    Deliberately tolerant of syntax errors elsewhere in the document:
    keyword/builtin lookups only need the token stream (from the
    lexer), and even the AST-based lookup for user definitions is
    attempted on a best-effort basis — a hover request can arrive
    while the user is mid-edit with an invalid file elsewhere, and
    that shouldn't take down hover for the rest of it.
    """
    nekova_line = line + 1  # LSP is 0-indexed; NEKOVA tokens are 1-indexed

    try:
        tokens = Lexer(source).tokenize()
    except LexerError:
        return None

    token, lsp_start, lsp_end = _find_position_in_tokens(tokens, nekova_line, character)
    if token is None:
        return None

    name = str(token.value)
    contents = None

    # 1. User-defined tasks/prompts/classes/methods take priority —
    #    if someone names their own task `sort`, hovering it should
    #    show *their* definition, not the builtin's. Identifier
    #    tokens only, so e.g. a string literal that happens to
    #    contain a task's name doesn't false-positive.
    #
    #    parse_best_effort() (not parse()) so a task defined earlier
    #    in the file is still found even if some *other*, unrelated
    #    part of the document currently has a syntax error — very
    #    much the normal state of a file while someone is mid-edit.
    if token.type == TokenType.IDENTIFIER:
        program = Parser(list(tokens)).parse_best_effort()
        for defn in _iter_bodies(program.statements):
            if defn.name == name:
                contents = _hover_for_definition(defn)
                break

    # 2. Keywords — only for tokens that are actually that keyword
    #    (checked against the real KEYWORDS mapping), not just any
    #    token whose text happens to match one. Without this, hovering
    #    over the word "let" inside a plain string literal like
    #    show "let me explain" would incorrectly show the `let`
    #    keyword's doc.
    if contents is None:
        lowered = name.lower()
        if lowered in KEYWORD_DOCS and KEYWORDS.get(lowered) == token.type:
            contents = KEYWORD_DOCS[lowered]

    # 3. Builtins (identifier tokens only — same reasoning as above)
    if contents is None and token.type == TokenType.IDENTIFIER and name in BUILTIN_DOCS:
        contents = BUILTIN_DOCS[name]

    if contents is None:
        return None

    return {
        "contents": {"kind": "markdown", "value": contents},
        "range": {
            "start": {"line": line, "character": lsp_start},
            "end": {"line": line, "character": lsp_end},
        },
    }