# =============================================================
# NEKOVA CLI — Static Analyser / Checker  (Phase 10)
# =============================================================
# nekova check <file>     — analyse a single file
# nekova check            — analyse all .nk files in project
#
# Checks performed:
#   W001 — undefined variable used
#   W002 — variable defined but never used
#   W003 — task called with wrong argument count
#   W004 — task defined but never called
#   W005 — shadowed built-in name
#   W006 — unreachable code after return
#   W007 — keyword used as task/variable name
#   W008 — think called without use ai (reminder)
#   E011 — reserved keyword used as identifier
# =============================================================

import os
import re

from nekova.lexer.lexer    import Lexer
from nekova.parser.parser  import Parser, ParseError
from nekova.parser.nodes   import (
    Program, AssignStatement, ShowStatement, IfStatement,
    WhileStatement, RepeatStatement, ForStatement,
    TaskStatement, ReturnStatement, UseStatement,
    CallExpression, Identifier, ThinkStatement,
    ThinkAsStatement,
)
from nekova.lexer.token_types import KEYWORDS


# ── Issue dataclass ───────────────────────────────────────────

class Issue:
    __slots__ = ("level", "code", "line", "message", "hint")

    def __init__(self, level: str, code: str, line: int,
                 message: str, hint: str = ""):
        self.level   = level    # "error" | "warning" | "info"
        self.code    = code
        self.line    = line
        self.message = message
        self.hint    = hint

    def __repr__(self):
        return f"[{self.level.upper()} {self.code}] line {self.line}: {self.message}"


# ── Built-in names that shouldn't be shadowed ─────────────────

_BUILTINS = {
    "show", "think", "true", "false", "null",
    "connect", "uuid", "token", "hash",
    "print", "len", "range", "type", "str", "int", "float",
}

# All NEKOVA keywords (from token_types)
_ALL_KEYWORDS = set(KEYWORDS.keys())


# ── Public API ────────────────────────────────────────────────

def check_file(filepath: str) -> list:
    """
    Check a single .nk file.
    Returns list of Issue objects.
    """
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        source = raw.decode("utf-8")
    except Exception as e:
        return [Issue("error", "E000", 0, f"Cannot read file: {e}")]

    return check_source(source, filepath)


def check_source(source: str, filepath: str = "<source>") -> list:
    """
    Lex, parse, and analyse NEKOVA source.
    Returns list of Issue objects.
    """
    issues = []

    # ── Phase 1: lex + parse ──────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
        ast    = Parser(tokens).parse()
    except ParseError as e:
        line = getattr(e, "line", 0)
        issues.append(Issue(
            "error", "E003", line,
            f"Parse error: {str(e).strip()}",
            "Fix the syntax error before running the checker."
        ))
        # Still do token-level checks
        _check_keywords_as_identifiers(source, issues)
        return issues
    except Exception as e:
        issues.append(Issue("error", "E000", 0, f"Unexpected error: {e}"))
        return issues

    # ── Phase 2: AST-level checks ─────────────────────────────
    analyser = _Analyser(source, filepath)
    analyser.analyse(ast)
    issues.extend(analyser.issues)

    # ── Phase 3: token-level checks ───────────────────────────
    _check_keywords_as_identifiers(source, issues)

    return sorted(issues, key=lambda i: i.line)


def check_directory(dirpath: str = ".") -> dict:
    """
    Check all .nk files in dirpath.
    Returns {filepath: [Issue, ...]}
    """
    results = {}
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".")
                   and d not in ("__pycache__", ".git", "dist")]
        for fname in files:
            if fname.endswith(".nk"):
                fpath = os.path.join(root, fname)
                results[fpath] = check_file(fpath)
    return results


# ── AST Analyser ──────────────────────────────────────────────

class _Scope:
    """Tracks variables and tasks in a lexical scope."""

    def __init__(self, parent=None):
        self.parent   = parent
        self.defined  = {}   # name → line defined
        self.used     = set()
        self.tasks    = {}   # name → (arg_count, line)
        self.calls    = []   # [(name, arg_count, line)]

    def define(self, name: str, line: int):
        self.defined[name] = line

    def use(self, name: str):
        self.used.add(name)

    def define_task(self, name: str, arg_count: int, line: int):
        self.tasks[name] = (arg_count, line)

    def record_call(self, name: str, arg_count: int, line: int):
        self.calls.append((name, arg_count, line))

    def lookup(self, name: str):
        """Check if name is defined in this scope or any parent."""
        scope = self
        while scope:
            if name in scope.defined or name in scope.tasks:
                return True
            scope = scope.parent
        return False

    def lookup_task(self, name: str):
        scope = self
        while scope:
            if name in scope.tasks:
                return scope.tasks[name]
            scope = scope.parent
        return None


class _Analyser:

    def __init__(self, source: str, filepath: str):
        self.source   = source
        self.filepath = filepath
        self.issues   = []
        self.scope    = _Scope()
        self._uses_ai = False
        self._after_return = False

        # Pre-seed global scope with stdlib names
        for name in _BUILTINS:
            self.scope.define(name, 0)
        # Built-in functions from stdlib modules
        for name in ["connect", "uuid", "token", "hash",
                     "json_encode", "json_decode",
                     "env_get", "env_set", "recall"]:
            self.scope.define(name, 0)

    def warn(self, code, line, msg, hint=""):
        self.issues.append(Issue("warning", code, line, msg, hint))

    def error(self, code, line, msg, hint=""):
        self.issues.append(Issue("error", code, line, msg, hint))

    def info(self, code, line, msg, hint=""):
        self.issues.append(Issue("info", code, line, msg, hint))

    def analyse(self, program: Program):
        for stmt in program.statements:
            self._visit(stmt)

        # After full pass: check for unused vars
        self._check_unused()
        # Check for wrong-arity calls
        self._check_calls()

    def _visit(self, node, after_return=False):
        if node is None:
            return

        node_type = type(node).__name__

        # Unreachable code after return
        if self._after_return and node_type not in (
            "ReturnStatement", "Program"
        ):
            line = getattr(node, "line", 0)
            self.warn("W006", line,
                      "Unreachable code after 'return'.",
                      "Remove the statement or restructure the block.")
            return

        method = getattr(self, f"_visit_{node_type}", self._visit_generic)
        method(node)

    def _visit_AssignStatement(self, node):
        line = getattr(node, "line", 0)
        name = node.name

        # Check for keyword conflict
        if name in _ALL_KEYWORDS:
            self.error("E011", line,
                       f"'{name}' is a reserved keyword — cannot use as variable name.",
                       f"Rename to something like '{name}_val' or 'my_{name}'.")

        # Check for shadowed built-in
        elif name in _BUILTINS:
            self.warn("W005", line,
                      f"'{name}' shadows a built-in NEKOVA name.",
                      f"Consider renaming to avoid confusion.")

        self.scope.define(name, line)
        self._visit(node.value)

    def _visit_Identifier(self, node):
        name = node.name
        line = getattr(node, "line", 0)

        # Skip keywords used as identifiers (handled elsewhere)
        if name in _ALL_KEYWORDS:
            return

        if not self.scope.lookup(name):
            self.warn("W001", line,
                      f"'{name}' is used but may not be defined.",
                      f"Define it first:  let {name} = \"value\"")
        else:
            self.scope.use(name)

    def _visit_TaskStatement(self, node):
        line = getattr(node, "line", 0)
        name = node.name

        if name in _ALL_KEYWORDS:
            self.error("E011", line,
                       f"'{name}' is a reserved keyword — cannot use as task name.",
                       f"Rename to 'task {name}_fn(...):'")

        arg_count = len(node.params) if node.params else 0
        self.scope.define_task(name, arg_count, line)
        self.scope.define(name, line)

        # Analyse body in child scope
        child = _Scope(parent=self.scope)
        old_scope = self.scope
        self.scope = child

        # Add params to child scope
        if node.params:
            for param in node.params:
                param_name = param if isinstance(param, str) else param[0]
                self.scope.define(param_name, line)

        old_after_return = self._after_return
        self._after_return = False

        for stmt in (node.body or []):
            self._visit(stmt)

        self._after_return = old_after_return
        self.scope = old_scope

    def _visit_ReturnStatement(self, node):
        if node.value:
            self._visit(node.value)
        self._after_return = True

    def _visit_CallExpression(self, node):
        line = getattr(node, "line", 0)
        name = None

        if hasattr(node, "name"):
            name = node.name
        elif hasattr(node, "callee") and hasattr(node.callee, "name"):
            name = node.callee.name

        if name:
            arg_count = len(node.args) if node.args else 0
            self.scope.record_call(name, arg_count, line)
            self.scope.use(name)

        # Visit arguments
        for arg in (node.args or []):
            self._visit(arg)

    def _visit_UseStatement(self, node):
        module = node.module if hasattr(node, "module") else str(node)
        if module in ("ai", "anthropic", "openai"):
            self._uses_ai = True

    def _visit_ThinkStatement(self, node):
        self._visit(node.prompt)

    def _visit_ThinkAsStatement(self, node):
        self._visit(node.prompt)

    def _visit_ShowStatement(self, node):
        self._visit(node.expression)

    def _visit_IfStatement(self, node):
        self._visit(node.condition)
        old_after = self._after_return
        self._after_return = False
        for stmt in (node.then_body or []):
            self._visit(stmt)
        self._after_return = False
        for stmt in (node.else_body or []):
            self._visit(stmt)
        self._after_return = old_after

    def _visit_WhileStatement(self, node):
        self._visit(node.condition)
        old = self._after_return
        self._after_return = False
        for stmt in (node.body or []):
            self._visit(stmt)
        self._after_return = old

    def _visit_ForStatement(self, node):
        line = getattr(node, "line", 0)
        self.scope.define(node.variable, line)
        self._visit(node.iterable)
        old = self._after_return
        self._after_return = False
        for stmt in (node.body or []):
            self._visit(stmt)
        self._after_return = old

    def _visit_RepeatStatement(self, node):
        self._visit(node.count)
        old = self._after_return
        self._after_return = False
        for stmt in (node.body or []):
            self._visit(stmt)
        self._after_return = old

    def _visit_generic(self, node):
        """Visit children of any node we don't have a specific handler for."""
        for attr in ("body", "then_body", "else_body", "statements",
                     "value", "left", "right", "condition",
                     "expression", "args", "iterable", "prompt",
                     "subject", "arms"):
            child = getattr(node, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                for item in child:
                    if hasattr(item, "__class__") and hasattr(item, "__dict__"):
                        self._visit(item)
            elif hasattr(child, "__class__") and hasattr(child, "__dict__"):
                self._visit(child)

    def _check_unused(self):
        """Warn about variables defined but never used."""
        # Stdlib functions pre-seeded into scope must never be
        # reported as unused -- they are builtins, not user variables.
        _STDLIB_PRESEEDED = {
            "connect", "uuid", "token", "hash",
            "json_encode", "json_decode",
            "env_get", "env_set", "recall",
        }
        for name, line in self.scope.defined.items():
            if name in _BUILTINS:
                continue
            if name in _STDLIB_PRESEEDED:
                continue
            if name in self.scope.tasks:
                continue
            if name not in self.scope.used:
                # Only warn for let-style names (not builtins or tasks)
                if name and not name.startswith("_"):
                    self.warn("W002", line,
                              f"'{name}' is defined but never used.",
                              f"Remove it or use it somewhere in your code.")

    def _check_calls(self):
        """Warn about calls with wrong argument count."""
        for (name, arg_count, line) in self.scope.calls:
            task_info = self.scope.lookup_task(name)
            if task_info is None:
                continue
            expected, _ = task_info
            if arg_count != expected:
                self.warn("W003", line,
                          f"'{name}' called with {arg_count} argument(s) "
                          f"but expects {expected}.",
                          f"Check the task definition for '{name}'.")


# ── Token-level checks ────────────────────────────────────────

def _check_keywords_as_identifiers(source: str, issues: list):
    """
    Scan for patterns like 'task fetch(' where a keyword is used as a name.
    """
    kw_pattern = "|".join(re.escape(k) for k in sorted(_ALL_KEYWORDS))
    # task <keyword>(  or  let <keyword> =
    pattern = re.compile(
        r"^(\s*)(?:task|let|object)\s+(" + kw_pattern + r")\s*[=(:]",
        re.MULTILINE
    )
    for m in pattern.finditer(source):
        line_no = source[:m.start()].count("\n") + 1
        name    = m.group(2)
        # Skip common false positives
        if name in ("else", "or", "and", "not", "in", "as"):
            continue
        issues.append(Issue(
            "error", "E011", line_no,
            f"'{name}' is a reserved keyword — cannot be used as a name here.",
            f"Rename it (e.g. '{name}_fn', 'my_{name}', 'do_{name}')."
        ))