# =============================================================
# NEKOVA — Fuzz Generator  (Phase 27 prerequisite)
# =============================================================
# Generates syntactically-plausible NEKOVA source, informed by the
# same rule shapes documented in GRAMMAR.md — not a generic EBNF
# interpreter (that's a bigger project on its own), but hand-written
# Python functions that mirror the grammar's actual structure, so
# the generator and the fuzz harness that mutates its output are
# grounded in the real, current grammar rather than guesswork.
#
# generate_program() is the entry point the harness calls; every
# other function here is a building block it composes from.
# =============================================================

import random


IDENTIFIERS = ["x", "y", "count", "total", "name", "result", "data",
                "value", "item", "flag", "user_input", "n", "i"]
STRINGS = ["hello", "world", "test string", "", "with \"escaped\" quotes",
           "unicode: héllo wörld 日本語", "multi\\nline\\nish"]
INT_LITERALS = ["0", "1", "-1", "42", "999999999", "-999999999"]
FLOAT_LITERALS = ["0.0", "1.5", "-3.14", "1e10", "1.0e-10"]
MONEY_LITERALS = ["$0", "$0.01", "$5", "$100.00", "$0.0000001"]

CONSTRUCTS = [
    "let_stmt", "const_stmt", "if_stmt", "while_stmt", "for_stmt",
    "task_def", "show_stmt", "think_stmt", "shape_def", "test_stmt",
    "sandbox_stmt", "try_stmt", "match_stmt", "expression_stmt",
]


def _ident():
    return random.choice(IDENTIFIERS)


def _literal(depth=0):
    if depth >= 3:
        return random.choice(INT_LITERALS + STRINGS_QUOTED())
    kind = random.choice(["int", "float", "money", "string", "bool",
                          "null", "list", "ident"])
    if kind == "int":
        return random.choice(INT_LITERALS)
    if kind == "float":
        return random.choice(FLOAT_LITERALS)
    if kind == "money":
        return random.choice(MONEY_LITERALS)
    if kind == "string":
        return f'"{random.choice(STRINGS).replace(chr(34), chr(92) + chr(34))}"'
    if kind == "bool":
        return random.choice(["true", "false"])
    if kind == "null":
        return "null"
    if kind == "list":
        n = random.randint(0, 3)
        return "[" + ", ".join(_literal(depth + 1) for _ in range(n)) + "]"
    return _ident()


def STRINGS_QUOTED():
    return [f'"{s.replace(chr(34), chr(92) + chr(34))}"' for s in STRINGS]


def _expr(depth=0):
    if depth > 3:
        return _literal()
    kind = random.choice(["literal", "binop", "call", "compare"])
    if kind == "literal":
        return _literal()
    if kind == "binop":
        op = random.choice(["+", "-", "*", "/", "%"])
        return f"({_expr(depth + 1)} {op} {_expr(depth + 1)})"
    if kind == "compare":
        op = random.choice(["==", "!=", "<", "<=", ">", ">=", "and", "or"])
        return f"({_expr(depth + 1)} {op} {_expr(depth + 1)})"
    if kind == "call":
        args = ", ".join(_literal() for _ in range(random.randint(0, 3)))
        return f"{_ident()}({args})"
    return _literal()


def _indent(text, levels=1):
    prefix = "    " * levels
    return "\n".join(prefix + line for line in text.splitlines())


MAX_DEPTH = 4

LEAF_CONSTRUCTS = ["let_stmt", "const_stmt", "show_stmt", "expression_stmt"]


def _body(depth, min_lines=1, max_lines=3):
    n = random.randint(min_lines, max_lines)
    lines = [generate_statement(depth + 1) for _ in range(n)]
    return "\n".join(lines)


def gen_let_stmt(depth):
    return f"let {_ident()} = {_expr()}"


def gen_const_stmt(depth):
    return f"const {_ident().upper()} = {_expr()}"


def gen_if_stmt(depth):
    body = _indent(_body(depth))
    out = f"if {_expr()}:\n{body}"
    if random.random() < 0.4:
        out += f"\nelse:\n{_indent(_body(depth))}"
    return out


def gen_while_stmt(depth):
    return f"while {_expr()}:\n{_indent(_body(depth))}"


def gen_for_stmt(depth):
    return f"for {_ident()} in {_literal()}:\n{_indent(_body(depth))}"


def gen_task_def(depth):
    params = ", ".join(_ident() for _ in range(random.randint(0, 3)))
    return (f"task {_ident()}({params}):\n"
            f"{_indent(_body(depth))}\n"
            f"{_indent('return ' + _expr())}")


def gen_show_stmt(depth):
    return f"show {_expr()}"


def gen_think_stmt(depth):
    fmt = random.choice(["", " as text", " as json", " as bool", " as list"])
    clause = random.choice(["", " with budget: 500",
                            ' with budget: $0.01', ' using "model-a"'])
    text = random.choice(STRINGS).replace(chr(34), chr(92) + chr(34))
    return f'think "{text}"{fmt}{clause}'


def gen_shape_def(depth):
    fields = "\n".join(
        _indent(f"{_ident()} {random.choice(['str', 'int', 'float', 'bool'])}")
        for _ in range(random.randint(1, 3))
    )
    return f"shape {_ident().capitalize()}:\n{fields}"


def gen_test_stmt(depth):
    if random.random() < 0.5:
        return (f'test "generated test":\n'
                f'{_indent("expect " + _expr())}')
    n = random.randint(1, 10)
    k = random.randint(1, n)
    return (f'test "generated probabilistic" repeat {n} times, '
            f'expect at least {k} passes:\n'
            f'{_indent("expect " + _expr())}')


def gen_sandbox_stmt(depth):
    mode = random.choice(["strict", "relaxed"])
    allow = ""
    if random.random() < 0.5:
        names = ", ".join(_ident() for _ in range(random.randint(0, 2)))
        allow = f" allow: [{names}]"
    return f"sandbox {mode}{allow}:\n{_indent(_body(depth))}"


def gen_try_stmt(depth):
    return (f"try:\n{_indent(_body(depth))}\n"
            f"catch:\n{_indent(_body(depth))}")


def gen_match_stmt(depth):
    arms = "\n".join(
        _indent(f'when {_literal()}: {gen_show_stmt(depth)}')
        for _ in range(random.randint(1, 3))
    )
    return f"match {_expr()}:\n{arms}\n{_indent('else: ' + gen_show_stmt(depth))}"


def gen_expression_stmt(depth):
    return _expr()


_GENERATORS = {
    "let_stmt": gen_let_stmt,
    "const_stmt": gen_const_stmt,
    "if_stmt": gen_if_stmt,
    "while_stmt": gen_while_stmt,
    "for_stmt": gen_for_stmt,
    "task_def": gen_task_def,
    "show_stmt": gen_show_stmt,
    "think_stmt": gen_think_stmt,
    "shape_def": gen_shape_def,
    "test_stmt": gen_test_stmt,
    "sandbox_stmt": gen_sandbox_stmt,
    "try_stmt": gen_try_stmt,
    "match_stmt": gen_match_stmt,
    "expression_stmt": gen_expression_stmt,
}


def generate_statement(depth=0):
    if depth >= MAX_DEPTH:
        construct = random.choice(LEAF_CONSTRUCTS)
    else:
        construct = random.choice(CONSTRUCTS)
    return _GENERATORS[construct](depth)


def generate_program(num_statements=None):
    """Generate a complete, syntactically-plausible NEKOVA program."""
    n = num_statements or random.randint(3, 15)
    return "\n".join(generate_statement() for _ in range(n)) + "\n"