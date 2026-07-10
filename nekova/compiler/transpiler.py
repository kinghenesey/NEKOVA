# =============================================================
# NEKOVA Compiler — Python Transpiler
# =============================================================
import os
import sys


class NEKOVATranspiler:

    def __init__(self):
        self.indent_level = 0
        self.output_lines = []

    def compile(self, source: str, output_path: str) -> str:
        base    = os.path.splitext(output_path)[0]
        py_path = base + ".py"

        from nekova.lexer import Lexer
        from nekova.parser.parser import Parser
        tokens  = Lexer(source).tokenize()
        program = Parser(tokens).parse()

        self.indent_level = 0
        self.output_lines = []

        NEKOVA_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self._write_header(NEKOVA_root)

        for stmt in program.statements:
            self._transpile_stmt(stmt)

        python_code = "\n".join(self.output_lines)
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        return py_path

    def _write_header(self, NEKOVA_root: str = ""):
        safe_root = NEKOVA_root.replace("\\", "/")
        lines = [
            "#!/usr/bin/env python3",
            "# Compiled NEKOVA Program — NEKOVA Compiler v1.0.0",
            "import os, sys, re, time, random",
            "",
            "_NEKOVA_root = " + repr(safe_root),
            "if _NEKOVA_root not in sys.path:",
            "    sys.path.insert(0, _NEKOVA_root)",
            "",
            "def _NEKOVA_show(value):",
            "    if value is None:    print('null')",
            "    elif value is True:  print('true')",
            "    elif value is False: print('false')",
            "    else:                print(str(value))",
            "",
            "def _NEKOVA_think(prompt):",
            "    try:",
            "        from ai.providers import get_provider",
            "        provider = get_provider()",
            "        response = provider.ask(str(prompt))",
            "        print('\\033[96m🧠 ' + response + '\\033[0m')",
            "        return response",
            "    except Exception as e:",
            "        print('[think error: ' + str(e) + ']')",
            "        return ''",
            "",
            "def _NEKOVA_interpolate(text, local_vars):",
            "    import re",
            "    def replace(m):",
            "        name = m.group(1)",
            "        return str(local_vars.get(name, m.group(0)))",
            "    return re.sub(r'{(\\w+)}', replace, text)",
            "",
            "def _NEKOVA_to_string(v):",
            "    if v is None:  return 'null'",
            "    if v is True:  return 'true'",
            "    if v is False: return 'false'",
            "    return str(v)",
            "",
            "def type_of(x):       return type(x).__name__",
            "def to_number(x):     return float(x) if '.' in str(x) else int(x)",
            "def to_text(x):       return str(x)",
            "def length(x):        return len(x)",
            "def ask(p=''):        return input(str(p))",
            "def clear():          print('\\033[H\\033[J', end='')",
            "def sleep(s=1):       time.sleep(float(s))",
            "def random_num(a, b): return random.randint(int(a), int(b))",
            "",
        ]
        self.output_lines.extend(lines)

    def _indent(self) -> str:
        return "    " * self.indent_level

    def _write(self, line: str):
        self.output_lines.append(self._indent() + line)

    def _transpile_stmt(self, node):
        from nekova.parser.nodes import (
            ShowStatement, ThinkStatement, AssignStatement,
            IfStatement, RepeatStatement, WhileStatement,
            ForStatement, TaskStatement, ReturnStatement,
            UseStatement, CallExpression, TryStatement,
            ImportStatement, PipelineStatement,
            ModelStatement, ParallelStatement,
            MemoryStatement, SandboxStatement
        )
        if isinstance(node, ShowStatement):
            self._transpile_show(node)
        elif isinstance(node, ThinkStatement):
            self._transpile_think(node)
        elif isinstance(node, AssignStatement):
            self._transpile_assign(node)
        elif isinstance(node, IfStatement):
            self._transpile_if(node)
        elif isinstance(node, RepeatStatement):
            self._transpile_repeat(node)
        elif isinstance(node, WhileStatement):
            self._transpile_while(node)
        elif isinstance(node, ForStatement):
            self._transpile_for(node)
        elif isinstance(node, TaskStatement):
            self._transpile_task(node)
        elif isinstance(node, ReturnStatement):
            self._transpile_return(node)
        elif isinstance(node, UseStatement):
            self._transpile_use(node)
        elif isinstance(node, CallExpression):
            self._write(self._transpile_expr(node))
        elif isinstance(node, TryStatement):
            self._transpile_try(node)
        elif isinstance(node, ModelStatement):
            self._transpile_model(node)
        elif isinstance(node, MemoryStatement):
            self._transpile_memory(node)
        elif isinstance(node, SandboxStatement):
            self._transpile_sandbox(node)

    def _transpile_show(self, node):
        self._write("_NEKOVA_show(" + self._transpile_expr(node.expression) + ")")

    def _transpile_think(self, node):
        prompt = self._transpile_expr(node.prompt)
        if node.variable:
            self._write(node.variable + " = _NEKOVA_think(" + prompt + ")")
        else:
            self._write("_NEKOVA_think(" + prompt + ")")

    def _transpile_assign(self, node):
        self._write(node.name + " = " + self._transpile_expr(node.value))

    def _transpile_if(self, node):
        self._write("if " + self._transpile_expr(node.condition) + ":")
        self.indent_level += 1
        if node.then_body:
            for stmt in node.then_body:
                self._transpile_stmt(stmt)
        else:
            self._write("pass")
        self.indent_level -= 1
        if node.else_body:
            self._write("else:")
            self.indent_level += 1
            for stmt in node.else_body:
                self._transpile_stmt(stmt)
            self.indent_level -= 1

    def _transpile_repeat(self, node):
        self._write("for _i in range(int(" + self._transpile_expr(node.count) + ")):")
        self.indent_level += 1
        for stmt in node.body:
            self._transpile_stmt(stmt)
        self.indent_level -= 1

    def _transpile_while(self, node):
        self._write("while " + self._transpile_expr(node.condition) + ":")
        self.indent_level += 1
        for stmt in node.body:
            self._transpile_stmt(stmt)
        self.indent_level -= 1

    def _transpile_for(self, node):
        self._write("for " + node.variable + " in " + self._transpile_expr(node.iterable) + ":")
        self.indent_level += 1
        for stmt in node.body:
            self._transpile_stmt(stmt)
        self.indent_level -= 1

    def _transpile_task(self, node):
        params = self._format_params(node.params)
        self._write("def " + node.name + "(" + params + "):")
        self.indent_level += 1
        if node.body:
            for stmt in node.body:
                self._transpile_stmt(stmt)
        else:
            self._write("pass")
        self.indent_level -= 1

    def _format_params(self, params) -> str:
        """
        Render a task's params (list of (name, default, is_vararg)
        tuples) as a valid Python parameter list. A previous version
        did `", ".join(node.params)` directly on the tuples, which
        always raised "expected str instance, tuple found" the moment
        any task had parameters — every real-world NEKOVA program has
        at least one.
        """
        parts = []
        for (pname, default, is_vararg) in params:
            if is_vararg:
                parts.append("*" + pname)
            elif default is not None:
                parts.append(pname + "=" + self._transpile_expr(default))
            else:
                parts.append(pname)
        return ", ".join(parts)

    def _transpile_return(self, node):
        if node.value:
            self._write("return " + self._transpile_expr(node.value))
        else:
            self._write("return None")

    def _transpile_use(self, node):
        self._write("# use " + node.module + " (stdlib loaded at runtime)")

    def _transpile_try(self, node):
        self._write("try:")
        self.indent_level += 1
        for stmt in node.try_body:
            self._transpile_stmt(stmt)
        self.indent_level -= 1
        err_var = node.error_var or "_NEKOVA_err"
        self._write("except Exception as " + err_var + ":")
        self.indent_level += 1
        for stmt in node.catch_body:
            self._transpile_stmt(stmt)
        self.indent_level -= 1

    def _transpile_model(self, node):
        name = self._transpile_expr(node.provider)
        self._write("__import__('ai.providers', fromlist=['set_provider']).set_provider(" + name + ")")

    def _transpile_memory(self, node):
        self._write("# memory block: " + node.name)
        self._write(node.name + " = {")
        self.indent_level += 1
        for stmt in node.body:
            from nekova.parser.nodes import AssignStatement
            if isinstance(stmt, AssignStatement):
                val = self._transpile_expr(stmt.value)
                self._write('"' + stmt.name + '": ' + val + ",")
        self.indent_level -= 1
        self._write("}")

    def _transpile_sandbox(self, node):
        self._write("# sandbox [" + node.mode + "]")
        for stmt in node.body:
            self._transpile_stmt(stmt)

    def _transpile_expr(self, node) -> str:
        from nekova.parser.nodes import (
            IntegerLiteral, FloatLiteral, StringLiteral,
            BooleanLiteral, NullLiteral, Identifier,
            BinaryOp, UnaryOp, CallExpression,
            IndexExpression, MethodCall,
            ListLiteral, DictLiteral
        )
        if isinstance(node, IntegerLiteral):
            return str(node.value)
        if isinstance(node, FloatLiteral):
            return str(node.value)
        if isinstance(node, StringLiteral):
            escaped = node.value.replace("'", "\\'")
            return "_NEKOVA_interpolate('" + escaped + "', locals())"
        if isinstance(node, BooleanLiteral):
            return "True" if node.value else "False"
        if isinstance(node, NullLiteral):
            return "None"
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, BinaryOp):
            left  = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            py_op = {
                "==": "==", "!=": "!=", "<": "<", "<=": "<=",
                ">": ">", ">=": ">=", "+": "+", "-": "-",
                "*": "*", "/": "/", "%": "%", "**": "**",
            }.get(node.operator, node.operator)
            return "(" + left + " " + py_op + " " + right + ")"
        if isinstance(node, UnaryOp):
            operand = self._transpile_expr(node.operand)
            if node.operator == "not":
                return "(not " + operand + ")"
            return "(" + node.operator + operand + ")"
        if isinstance(node, CallExpression):
            parts = [self._transpile_expr(a) for a in node.args]
            # Keyword arguments were previously dropped entirely here —
            # only node.args (positional) was ever transpiled, so any
            # call using name=value syntax silently lost those
            # arguments, producing a call with too few args at runtime.
            for kw_name, kw_expr in node.kwargs.items():
                parts.append(kw_name + "=" + self._transpile_expr(kw_expr))
            args = ", ".join(parts)
            return node.name + "(" + args + ")"
        if isinstance(node, IndexExpression):
            col = self._transpile_expr(node.collection)
            idx = self._transpile_expr(node.index)
            return col + "[" + idx + "]"
        if isinstance(node, MethodCall):
            obj  = self._transpile_expr(node.object)
            args = ", ".join(self._transpile_expr(a) for a in node.args)
            return obj + "." + node.method + "(" + args + ")"
        if isinstance(node, ListLiteral):
            items = ", ".join(self._transpile_expr(e) for e in node.elements)
            return "[" + items + "]"
        if isinstance(node, DictLiteral):
            pairs = ", ".join(
                self._transpile_expr(k) + ": " + self._transpile_expr(v)
                for k, v in node.pairs
            )
            return "{" + pairs + "}"
        return "None"