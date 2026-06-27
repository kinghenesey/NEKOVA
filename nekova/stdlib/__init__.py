# =============================================================
# NEKOVA Standard Library — Package Init
# =============================================================
# This is the central registry for all NEKOVA stdlib modules.
# When NEKOVA sees "use math" it calls load_module("math")
# which returns all functions for that module.
#
# Adding a new module in the future is as simple as:
#   1. Create stdlib/yourmodule_module.py with a load() fn
#   2. Add it to the MODULES registry below

from nekova.stdlib.nk_loader import has_nk_module, load_nk_module
from nekova.stdlib import (
    math_module,
    text_module,
    files_module,
    datetime_module,
    collections_module,
    vision_module,
    voice_module,
    # Phase 8
    json_module,
    env_module,
    uuid_module,
    crypto_module,
)

from nekova.ai import ai_module
from nekova.ai import agents_module
from nekova.ui import ui_module
from nekova.web import web_module
from nekova.database import db_module


# ── Module registry ───────────────────────────────────────────

MODULES = {
    "math":        math_module,
    "text":        text_module,
    "files":       files_module,
    "datetime":    datetime_module,
    "collections": collections_module,
    "ai":          ai_module,
    "agents":      agents_module,
    "ui":          ui_module,
    "web":         web_module,
    "database":    db_module,
    "vision":      vision_module,
    "voice":       voice_module,
    # Phase 8
    "json":        json_module,
    "env":         env_module,
    "uuid":        uuid_module,
    "crypto":      crypto_module,
}


def load_module(name: str) -> dict:
    """
    Load a stdlib module by name.
    Priority: .nk module → Python module → installed package
    """
    # Phase 18: Merge .nk module ON TOP of Python module
    # .nk definitions take priority; Python fills in primitives
    if has_nk_module(name):
        nk_exports = load_nk_module(name)
        if name in MODULES:
            base = MODULES[name].load()
            base.update(nk_exports)   # .nk wins on conflicts
            return base
        return nk_exports

    # Check built-in Python modules
    if name in MODULES:
        return MODULES[name].load()

    # Check installed packages
    package_functions = _load_package(name)
    if package_functions is not None:
        return package_functions

    # Nothing found — give helpful error
    available = ", ".join(MODULES.keys())
    raise ImportError(
        f"Module '{name}' was not found.\n"
        f"  Built-in modules: {available}\n"
        f"  .nk modules: math, string, file, date\n"
        f"  Install packages with: nekova install <name>"
    )


def _load_package(name: str) -> dict:
    """
    Try to load an installed package by name.
    Returns None if package is not installed.
    """
    import sys
    import importlib
    import importlib.util
    from nekova.packages import is_installed, PACKAGES_DIR

    if not is_installed(name):
        return None

    try:
        # Build the full path to the package file
        import os
        package_file = os.path.join(PACKAGES_DIR, f"{name}.py")

        # Load the module directly from its file path
        # This avoids any naming conflicts with Python builtins
        spec   = importlib.util.spec_from_file_location(
                     f"NEKOVA_pkg_{name}", package_file)
        module = importlib.util.module_from_spec(spec)

        # Temporarily remove packages dir from sys.path
        # so the module can import Python builtins cleanly
        clean_path = [p for p in sys.path
                      if p != PACKAGES_DIR]
        original_path = sys.path[:]
        sys.path = clean_path

        try:
            spec.loader.exec_module(module)
        finally:
            sys.path = original_path

        return module.load()

    except Exception as e:
        raise ImportError(
            f"Package '{name}' is installed but failed to load.\n"
            f"  Error: {e}"
        )


def available_modules() -> list:
    """Return a list of all available module names."""
    return list(MODULES.keys())