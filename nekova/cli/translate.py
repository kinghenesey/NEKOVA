# =============================================================
# NEKOVA CLI — nekova translate  (Phase 26b "Education Layer")
# =============================================================
# `nekova translate script.py` produces idiomatic-ish .nk from a
# real Python source file, using Python's own `ast` module rather
# than regex/string munging — the same discipline as everything
# else in the toolchain (parse the real grammar, don't pattern-
# match text).
#
# Deliberately a *best-effort* translator, not a full compiler:
# Python has constructs NEKOVA has no equivalent for (decorators
# other than the ones NEKOVA itself supports, comprehensions,
# context managers, multiple inheritance, etc.). Anything
# unsupported is emitted as a NEKOVA comment naming exactly what
# couldn't be translated and why, on the line it would have gone,
# rather than silently dropped or guessed at.
# =============================================================

import ast
import os

from nekova.cli import print_error, print_success, print_info


class _Unsupported(Exception):
    def __init__(self, node, reason):
        self.node = node
        self.reason = reason
        super().__init__(reason)


class Translator:
    """
    Walks a Python AST and emits NEKOVA source. One instance per
    translation — `self.declared` tracks which names have already
    been `let`-declared in the current scope stack, so a second
    assignment to the same name doesn't repeat 'let' (matching how
    a human would actually write it).
    """

    def __init__(self):
        self.lines = []
        self.declared_stack = [set()]
        self.warnings = []

    # ── Public entry point ──────────────────────────────────────

    def translate_module(self, tree: ast.Module) -> str:
        for stmt in tree.body:
            self._emit_stmt(stmt, indent=0)
        return "\n".join(self.lines)

    # ── Scope helpers ────────────────────────────────────────────

    def _declared(self):
        return self.declared_stack[-1]

    def _push_scope(self):
        self.declared_stack.append(set())

    def _pop_scope(self):
        self.declared_stack.pop()

    def _add(self, indent: int, text: str):
        self.lines.append(("    " * indent) + text)

    def _warn(self, node, reason: str, indent: int):
        lineno = getattr(node, "lineno", "?")
        msg = f"# TODO(translate): {reason} (Python line {lineno})"
        self._add(indent, msg)
        self.warnings.append(f"line {lineno}: {reason}")

    # ── Statements ────────────────────────────────────────────────

    def _emit_stmt(self, node, indent: int):
        handler = getattr(self, f"_stmt_{type(node).__name__}", None)
        if handler is None:
            self._warn(node, f"unsupported statement "
                              f"'{type(node).__name__}'", indent)
            return
        handler(node, indent)

    def _stmt_Assign(self, node: ast.Assign, indent: int):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            self._warn(node, "multi-target or non-simple assignment "
                              "isn't translated", indent)
            return
        name = node.targets[0].id
        expr = self._expr(node.value)
        if name in self._declared():
            self._add(indent, f"{name} = {expr}")
        else:
            self._declared().add(name)
            self._add(indent, f"let {name} = {expr}")

    def _stmt_AugAssign(self, node: ast.AugAssign, indent: int):
        if not isinstance(node.target, ast.Name):
            self._warn(node, "augmented assignment to a non-simple "
                              "target isn't translated", indent)
            return
        op = self._binop_symbol(node.op)
        self._add(indent, f"{node.target.id} {op}= {self._expr(node.value)}")

    def _stmt_Expr(self, node: ast.Expr, indent: int):
        v = node.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) \
                and v.func.id == "print":
            self._add(indent, f"show {self._print_args(v)}")
            return
        self._add(indent, self._expr(v))

    def _stmt_If(self, node: ast.If, indent: int):
        cond = self._expr(node.test)
        self._add(indent, f"if {cond}:")
        self._push_scope()
        for s in node.body:
            self._emit_stmt(s, indent + 1)
        self._pop_scope()
        orelse = node.orelse
        # A single `elif` shows up in Python's AST as orelse == [If(...)]
        while len(orelse) == 1 and isinstance(orelse[0], ast.If):
            elif_node = orelse[0]
            self._add(indent, f"elif {self._expr(elif_node.test)}:")
            self._push_scope()
            for s in elif_node.body:
                self._emit_stmt(s, indent + 1)
            self._pop_scope()
            orelse = elif_node.orelse
        if orelse:
            self._add(indent, "else:")
            self._push_scope()
            for s in orelse:
                self._emit_stmt(s, indent + 1)
            self._pop_scope()

    def _stmt_While(self, node: ast.While, indent: int):
        self._add(indent, f"while {self._expr(node.test)}:")
        self._push_scope()
        for s in node.body:
            self._emit_stmt(s, indent + 1)
        self._pop_scope()
        if node.orelse:
            self._warn(node, "while/else has no NEKOVA equivalent — "
                              "the else body was dropped", indent)

    def _stmt_For(self, node: ast.For, indent: int):
        if not isinstance(node.target, ast.Name):
            self._warn(node, "for-loop with a non-simple target "
                              "(tuple unpacking) isn't translated", indent)
            return
        self._add(indent, f"for {node.target.id} in "
                          f"{self._expr(node.iter)}:")
        self._push_scope()
        for s in node.body:
            self._emit_stmt(s, indent + 1)
        self._pop_scope()

    def _stmt_FunctionDef(self, node: ast.FunctionDef, indent: int):
        params = self._params(node.args)
        self._add(indent, f"task {node.name}({params}):")
        self._push_scope()
        for a in node.args.args:
            self._declared().add(a.arg)
        for s in node.body:
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) \
                    and isinstance(s.value.value, str) and s is node.body[0]:
                # Docstring — NEKOVA tasks support docstrings directly.
                self._add(indent + 1, f'"""{s.value.value}"""')
                continue
            self._emit_stmt(s, indent + 1)
        self._pop_scope()

    def _stmt_Return(self, node: ast.Return, indent: int):
        if node.value is None:
            self._add(indent, "return")
        else:
            self._add(indent, f"return {self._expr(node.value)}")

    def _stmt_Pass(self, node: ast.Pass, indent: int):
        self._add(indent, "pass")

    def _stmt_Break(self, node: ast.Break, indent: int):
        self._add(indent, "break")

    def _stmt_Continue(self, node: ast.Continue, indent: int):
        self._add(indent, "continue")

    def _stmt_ClassDef(self, node: ast.ClassDef, indent: int):
        bases = ", ".join(self._expr(b) for b in node.bases)
        header = f"class {node.name}({bases}):" if bases else f"class {node.name}:"
        self._add(indent, header)
        self._push_scope()
        for s in node.body:
            self._emit_stmt(s, indent + 1)
        self._pop_scope()

    def _stmt_Import(self, node: ast.Import, indent: int):
        for alias in node.names:
            self._add(indent, f"# TODO(translate): 'import {alias.name}' — "
                              f"check NEKOVA's stdlib (nekova info) for an "
                              f"equivalent 'use' module")

    def _stmt_ImportFrom(self, node: ast.ImportFrom, indent: int):
        self._add(indent, f"# TODO(translate): 'from {node.module} import "
                          f"...' — check NEKOVA's stdlib (nekova info) for "
                          f"an equivalent 'use' module")

    # ── Expressions ───────────────────────────────────────────────

    def _expr(self, node) -> str:
        handler = getattr(self, f"_expr_{type(node).__name__}", None)
        if handler is None:
            raise _Unsupported(node, f"unsupported expression "
                                      f"'{type(node).__name__}'")
        return handler(node)

    def _expr_Constant(self, node: ast.Constant):
        v = node.value
        if v is None:
            return "null"
        if v is True:
            return "true"
        if v is False:
            return "false"
        if isinstance(v, str):
            return '"' + v.replace('"', '\\"') + '"'
        return repr(v)

    def _expr_Name(self, node: ast.Name):
        return node.id

    def _expr_BinOp(self, node: ast.BinOp):
        return (f"({self._expr(node.left)} "
                f"{self._binop_symbol(node.op)} "
                f"{self._expr(node.right)})")

    def _expr_BoolOp(self, node: ast.BoolOp):
        symbol = "and" if isinstance(node.op, ast.And) else "or"
        return f" {symbol} ".join(self._expr(v) for v in node.values)

    def _expr_UnaryOp(self, node: ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return f"not {self._expr(node.operand)}"
        if isinstance(node.op, ast.USub):
            return f"-{self._expr(node.operand)}"
        if isinstance(node.op, ast.UAdd):
            return f"+{self._expr(node.operand)}"
        raise _Unsupported(node, "unsupported unary operator")

    def _expr_Compare(self, node: ast.Compare):
        parts = [self._expr(node.left)]
        symbol_map = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=", ast.In: "in", ast.NotIn: "not in",
        }
        out = self._expr(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            symbol = symbol_map.get(type(op))
            if symbol is None:
                raise _Unsupported(node, f"unsupported comparison "
                                          f"'{type(op).__name__}'")
            out += f" {symbol} {self._expr(comparator)}"
        return out

    def _expr_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            return self._print_args(node)
        func = self._expr(node.func)
        args = [self._expr(a) for a in node.args]
        for kw in node.keywords:
            args.append(f"{kw.arg}={self._expr(kw.value)}")
        return f"{func}({', '.join(args)})"

    def _expr_Attribute(self, node: ast.Attribute):
        return f"{self._expr(node.value)}.{node.attr}"

    def _expr_List(self, node: ast.List):
        return "[" + ", ".join(self._expr(e) for e in node.elts) + "]"

    def _expr_Tuple(self, node: ast.Tuple):
        return "(" + ", ".join(self._expr(e) for e in node.elts) + ")"

    def _expr_Dict(self, node: ast.Dict):
        pairs = [f"{self._expr(k)}: {self._expr(v)}"
                 for k, v in zip(node.keys, node.values)]
        return "{" + ", ".join(pairs) + "}"

    def _expr_Subscript(self, node: ast.Subscript):
        idx = node.slice
        if isinstance(idx, ast.Slice):
            lo = self._expr(idx.lower) if idx.lower else ""
            hi = self._expr(idx.upper) if idx.upper else ""
            return f"{self._expr(node.value)}[{lo}:{hi}]"
        return f"{self._expr(node.value)}[{self._expr(idx)}]"

    def _expr_JoinedStr(self, node: ast.JoinedStr):
        # Python f-string -> NEKOVA f-string; same {expr} syntax.
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                parts.append("{" + self._expr(v.value) + "}")
            else:
                raise _Unsupported(node, "unsupported f-string piece")
        return 'f"' + "".join(parts).replace('"', '\\"') + '"'

    def _expr_IfExp(self, node: ast.IfExp):
        # Python's `a if cond else b` -> NEKOVA ternary, same shape.
        return (f"({self._expr(node.body)} if {self._expr(node.test)} "
                f"else {self._expr(node.orelse)})")

    # ── Shared helpers ────────────────────────────────────────────

    def _binop_symbol(self, op) -> str:
        table = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
        }
        symbol = table.get(type(op))
        if symbol is None:
            raise _Unsupported(op, f"unsupported operator "
                                    f"'{type(op).__name__}'")
        return symbol

    def _params(self, args: ast.arguments) -> str:
        parts = []
        defaults = [None] * (len(args.args) - len(args.defaults)) + \
                   list(args.defaults)
        for arg, default in zip(args.args, defaults):
            if default is None:
                parts.append(arg.arg)
            else:
                parts.append(f"{arg.arg}={self._expr(default)}")
        if args.vararg:
            parts.append(f"*{args.vararg.arg}")
        return ", ".join(parts)

    def _print_args(self, call: ast.Call) -> str:
        """
        Python's print() takes any number of positional args and
        joins them with a space. A single arg maps straight to
        `show <expr>`; multiple args become an f-string joining
        them the same way, since NEKOVA's `show` only takes one
        value.

        String-constant args are inlined as literal text rather
        than an f-string {expr} placeholder — `print("i is", i)`
        should become `f"i is {i}"`, not `f"{"i is"} {i}"` (which
        is a nested, unescaped-quote syntax error).
        """
        if len(call.args) == 1 and not call.keywords:
            return self._expr(call.args[0])

        pieces = []
        for a in call.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                pieces.append(a.value.replace('"', '\\"'))
            else:
                pieces.append("{" + self._expr(a) + "}")
        return 'f"' + " ".join(pieces) + '"'


def translate_source(python_source: str):
    """
    Translate a Python source string to NEKOVA source.
    Returns (nk_source: str, warnings: list[str]).
    Raises SyntaxError if the input isn't valid Python.
    """
    tree = ast.parse(python_source)
    translator = Translator()
    try:
        nk_source = translator.translate_module(tree)
    except _Unsupported as e:
        # A hard-unsupported top-level construct — still return what
        # was translated so far plus a note, rather than nothing.
        translator._warn(e.node, e.reason, 0)
        nk_source = "\n".join(translator.lines)
    return nk_source, translator.warnings


def cmd_translate(filepath: str) -> bool:
    """CLI entry point for `nekova translate script.py`."""
    if not os.path.isfile(filepath):
        print_error(f"File not found: '{filepath}'")
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print_error(f"Could not read file: {e}")
        return False

    try:
        nk_source, warnings = translate_source(source)
    except SyntaxError as e:
        print_error(f"'{filepath}' isn't valid Python: {e}")
        return False

    output_path = os.path.splitext(filepath)[0] + ".nk"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(nk_source + "\n")
    except Exception as e:
        print_error(f"Could not write output: {e}")
        return False

    print_success(f"Translated → {output_path}")
    if warnings:
        print_info(f"{len(warnings)} construct(s) need manual attention "
                    f"(see '# TODO(translate)' comments in the output).")
    return True