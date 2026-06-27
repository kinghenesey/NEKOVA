# =============================================================
# NEKOVA Standard Library — .nk Module Loader
# Phase 18: Load stdlib modules written in NEKOVA itself
# =============================================================
# This loader finds .nk files in nekova/stdlib/nk/ and runs
# them through the NEKOVA interpreter, capturing all top-level
# task and let definitions as a module namespace dict.
# =============================================================

import os

_NK_STDLIB_DIR = os.path.join(os.path.dirname(__file__), "nk")

# Cache to avoid re-parsing on repeated imports
_cache: dict = {}


def has_nk_module(name: str) -> bool:
    """Return True if a .nk stdlib module exists for this name."""
    path = os.path.join(_NK_STDLIB_DIR, f"{name}.nk")
    return os.path.isfile(path)


def load_nk_module(name: str) -> dict:
    """
    Load a .nk stdlib module, returning a dict of all top-level
    names defined in it (tasks, lets, constants).
    Results are cached after first load.
    """
    if name in _cache:
        return _cache[name]

    path = os.path.join(_NK_STDLIB_DIR, f"{name}.nk")
    if not os.path.isfile(path):
        raise ImportError(f"No .nk stdlib module found for '{name}'.")

    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    # Import here to avoid circular imports at module load time
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter

    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()

    # Run in a fresh interpreter — capture its global environment
    interp = Interpreter()

    import io, sys
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        interp.execute(ast)
    finally:
        sys.stdout = old_stdout

    # Only harvest names that were DEFINED BY the .nk file,
    # not the interpreter's built-in globals.
    # Strategy: snapshot builtins before, compare after.
    from nekova.interpreter.interpreter import Interpreter as _Interp
    blank = _Interp()
    builtin_keys = set(blank.globals.variables.keys())

    namespace = {}
    for key, val in interp.globals.variables.items():
        if key not in builtin_keys and not key.startswith("__"):
            namespace[key] = val

    _cache[name] = namespace
    return namespace


def clear_cache():
    """Clear the module cache — useful for testing."""
    _cache.clear()