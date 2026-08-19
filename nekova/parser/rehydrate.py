# nekova/parser/rehydrate.py
# =============================================================
# Phase 27 — self-hosted parser runtime wiring.
#
# parser.nk (nekova/stdlib/nk/parser.nk) produces plain dicts/lists
# as its AST representation (see that file's own header comment for
# why — no classes to lean on while bootstrapping the parser itself).
# The Python interpreter, however, is built entirely around real
# Node object instances with attribute access (node.condition,
# node.body, ...). This module is the bridge: it walks the dict/list
# structure parser.nk returns and reconstructs the exact same Node
# tree the Python reference parser (nekova/parser/parser.py) would
# have produced for the same source — the same relationship
# tools/diff_parsers.py verifies structurally, just run in reverse
# and actually used at runtime instead of only for comparison.
#
# This means the existing interpreter needs zero changes to run
# self-hosted-parsed programs: it never has to know the AST didn't
# come from parser.py.
# =============================================================

import inspect
import re

import nekova.parser.nodes as _nodes_module
import nekova.parser.async_nodes as _async_nodes_module

Node = _nodes_module.Node
Program = _nodes_module.Program


def _build_node_registry():
    """Map every Node subclass name -> class object, across both
    nodes.py and async_nodes.py. Built once via introspection rather
    than hand-maintained, so a new node type just needs to exist in
    one of those modules to be picked up automatically."""
    registry = {}
    for module in (_nodes_module, _async_nodes_module):
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if cls is Node:
                continue
            if issubclass(cls, Node):
                registry[name] = cls
    return registry


_NODE_REGISTRY = _build_node_registry()


def rehydrate(value):
    """
    Recursively convert a dict/list/primitive structure (as produced
    by parser.nk) back into real Node instances where applicable.
    This is the exact inverse of tools/diff_parsers.py's serialize().

    Node instances are constructed via object.__new__ + setattr for
    each field, bypassing __init__ entirely. This is deliberate, not
    a shortcut: every Node class's __init__ params are supposed to
    match its self.attr names, but that's a convention, not something
    enforced anywhere, and getting it wrong (e.g. `self.value = val`
    for an __init__(self, val) that doesn't match a dict key exactly)
    would fail silently or noisily depending on the class. Setting
    attributes directly guarantees exact parity with whatever
    tools/diff_parsers.py already verified structurally — the dict
    keys ARE the attribute names, by construction of that
    verification — with no dependency on constructor call
    conventions at all.

    A dict is only treated as a Node if its "type" key matches a
    known Node class name; otherwise it's rehydrated as a plain dict
    (e.g. CallExpression.kwargs, a DictLiteral's data payload, or any
    other genuinely-plain-data dict nested in the AST).
    """
    if isinstance(value, dict):
        node_type = value.get("type")
        if node_type is not None and node_type in _NODE_REGISTRY:
            cls = _NODE_REGISTRY[node_type]
            instance = object.__new__(cls)
            for key, sub_value in value.items():
                if key == "type":
                    continue
                setattr(instance, key, rehydrate(sub_value))
            if not hasattr(instance, "line"):
                instance.line = 0
            return instance
        return {key: rehydrate(sub_value) for key, sub_value in value.items()}

    if isinstance(value, list):
        return [rehydrate(item) for item in value]

    return value


def rehydrate_program(statements: list) -> Program:
    """
    statements: the list of dicts returned by parser.nk's parse().
    Returns a real Program node, ready to hand to
    nekova.interpreter.interpreter.Interpreter().execute(...) exactly
    like parser.py's Parser(...).parse() output.
    """
    program = object.__new__(Program)
    program.statements = [rehydrate(stmt) for stmt in statements]
    return program


# Cache the bootstrap module load (lexer.nk + parser.nk, executed via
# the Python toolchain) across calls in the same process — mirrors
# nk_loader.load_nk_module's own caching, but we need the actual
# 'parse' task value itself, not just its harvested namespace dict.
_bootstrap_parse_task = None


def _get_bootstrap_parse_task():
    global _bootstrap_parse_task
    if _bootstrap_parse_task is None:
        from nekova.stdlib.nk_loader import load_nk_module
        namespace = load_nk_module("parser")
        if "parse" not in namespace:
            raise RuntimeError(
                "Self-hosted parser is unavailable: nekova/stdlib/nk/"
                "parser.nk loaded but defines no top-level 'parse' task."
            )
        _bootstrap_parse_task = namespace["parse"]
    return _bootstrap_parse_task


def parse_self_hosted(source: str) -> Program:
    """
    Parse NEKOVA source using the self-hosted lexer.nk + parser.nk
    instead of the Python reference lexer/parser, returning a real
    Program node — a drop-in replacement for
    `Parser(Lexer(source).tokenize()).parse()`.

    lexer.nk/parser.nk are themselves still loaded and bootstrapped
    via the Python toolchain (nk_loader, same as any other .nk stdlib
    module reached via 'use parser') — this doesn't eliminate the
    Python parser from the pipeline entirely, it uses it to load the
    self-hosted one, then hands off to that for parsing the target
    program. That's what "self-hosted" means at this stage: the
    NEKOVA-level parsing logic is written in NEKOVA, not that the
    bootstrap chain has no Python left in it at all.

    Any error raised while parsing (a genuine NEKOVA `raise`
    statement inside parser.nk, e.g. "Unexpected token ...") is
    converted to a ParseError, the exact type the Python reference
    parser raises for the same situation — so callers (runner.py in
    particular) don't need a separate error-handling path for the
    self-hosted case; it plugs into the existing except ParseError
    handling unchanged.
    """
    from nekova.parser.parser import ParseError
    from nekova.interpreter.exceptions import NEKOVARaiseError
    from nekova.interpreter.interpreter import Interpreter

    parse_task = _get_bootstrap_parse_task()
    bootstrap_interp = Interpreter()

    try:
        dict_ast = bootstrap_interp._call_task(parse_task, [source])
    except NEKOVARaiseError as e:
        # e.line is the line *inside parser.nk itself* where the
        # raise statement lives (unhelpful — it's always somewhere
        # around parser.nk's own source, never the target program).
        # The line that actually matters is embedded in the message
        # text instead: every raised message in parser.nk ends with
        # "... Line N." referring to the target source being parsed
        # (that's a convention followed throughout parser.nk, not
        # something enforced here — fall back to 0 if a message
        # doesn't happen to follow it).
        message = str(e.value)
        target_line = 0
        match = re.search(r"\s*Line (\d+)\.?\s*$", message)
        if match:
            target_line = int(match.group(1))
            message = message[:match.start()].rstrip()
        raise ParseError(message, line=target_line) from e
    except RecursionError as e:
        raise ParseError(
            "Source is too deeply nested for the self-hosted parser "
            "to handle.", line=0
        ) from e

    return rehydrate_program(dict_ast)