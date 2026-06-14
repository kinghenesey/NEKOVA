# =============================================================
# NEKOVA CLI — Commands
# =============================================================

import os
import sys
import time
import subprocess

from nekova.config import Color, NEKOVA_VERSION, NEKOVA_CODENAME
from nekova.cli import (print_success, print_error,
                 print_info, print_warning, print_separator)


def cmd_info():
    """Show NEKOVA system information."""
    print()
    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA System Information{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print(f"  {'Language':<20} NEKOVA")
    print(f"  {'Version':<20} {NEKOVA_VERSION}")
    print(f"  {'Codename':<20} {NEKOVA_CODENAME}")
    print(f"  {'Python':<20} {sys.version.split()[0]}")
    print(f"  {'Platform':<20} {sys.platform}")
    print(f"  {'Location':<20} {os.getcwd()}")
    print()

    from nekova.packages import load_registry, get_available
    installed = load_registry()
    available = get_available()
    print(f"  {'Packages':<20} {len(installed)}/{len(available)} installed")

    from nekova.stdlib import MODULES
    print(f"  {'Stdlib modules':<20} {len(MODULES)}")
    print()


# ── nekova new ────────────────────────────────────────────────────────────────

_MAIN_NK = '''\
# {name} — NEKOVA Project
# Created with nekova v{version}

show "Welcome to {name}!"
show "Built with NEKOVA {version} · {codename}"
'''

_TOML = '''\
# nekova.toml — project configuration
# Run your project with:  nekova run

[project]
name        = "{name}"
version     = "0.1.0"
author      = ""
description = "A NEKOVA project"
entry       = "src/main.nk"

[ai]
# "claude" | "gemini" | "openai" | "mock"
model   = "claude"
api_key = ""

[dependencies]
packages = []

[run]
strict_types = false
show_imports = false
debug        = false
'''

_README = '''\
# {name}

A NEKOVA language project.

## Run

```bash
nekova run
```

Or run a specific file:

```bash
nekova run src/main.nk
```

## Structure

```
{name}/
├── src/
│   └── main.nk      ← entry point
├── tests/
├── nekova.toml       ← project config
└── README.md
```

## Built with

NEKOVA v{version} · {codename}
'''

_GITIGNORE = '''\
__pycache__/
*.pyc
.env
*.nkpkg
dist/
'''


def cmd_new(project_name: str):
    """Create a new NEKOVA project with starter files."""
    if not project_name:
        print_error("Please provide a project name.")
        print_info("Usage:  nekova new myproject")
        return False

    if os.path.exists(project_name):
        print_error(f"Folder '{project_name}' already exists.")
        return False

    print_info(f"Creating project '{project_name}'...")

    dirs = [
        project_name,
        os.path.join(project_name, "src"),
        os.path.join(project_name, "tests"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    ctx = dict(name=project_name, version=NEKOVA_VERSION, codename=NEKOVA_CODENAME)

    _write(os.path.join(project_name, "src", "main.nk"),
           _MAIN_NK.format(**ctx))
    _write(os.path.join(project_name, "nekova.toml"),
           _TOML.format(**ctx))
    _write(os.path.join(project_name, "README.md"),
           _README.format(**ctx))
    _write(os.path.join(project_name, ".gitignore"),
           _GITIGNORE)
    _write(os.path.join(project_name, "tests", ".gitkeep"), "")

    print_success(f"Project '{project_name}' created!")
    print()
    print(f"  {Color.DIM}Structure:{Color.RESET}")
    print(f"  {project_name}/")
    print(f"  ├── src/")
    print(f"  │   └── main.nk")
    print(f"  ├── tests/")
    print(f"  ├── nekova.toml")
    print(f"  └── README.md")
    print()
    print_info("Run your project:")
    print(f"  {Color.CYAN}cd {project_name}{Color.RESET}")
    print(f"  {Color.CYAN}nekova run{Color.RESET}")
    print()
    return True


def _write(path: str, content: str):
    """Write UTF-8 file without BOM."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ── nekova test ───────────────────────────────────────────────────────────────

def cmd_test():
    """Run all NEKOVA test suites via pytest."""
    print()
    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA Test Runner{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Try pytest first (gives us richer output)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=root,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    # Print pytest output
    output = result.stdout + result.stderr
    for line in output.splitlines():
        print(f"  {line}")

    print()
    if result.returncode == 0:
        print_success("All tests passed.")
    else:
        print_error("Some tests failed.")
    print()
    return result.returncode == 0


# ── nekova build ──────────────────────────────────────────────────────────────

def cmd_build(filepath: str):
    """Validate an .nk file without executing it (lex + parse only)."""
    if not filepath:
        print_error("Please provide a file to build.")
        print_info("Usage:  nekova build app.nk")
        return False

    if not os.path.isfile(filepath):
        print_error(f"File not found: '{filepath}'")
        return False

    print_info(f"Building '{filepath}'...")
    start = time.perf_counter()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        from nekova.lexer import Lexer, LexerError
        from nekova.parser.parser import Parser, ParseError

        lexer  = Lexer(source)
        tokens = lexer.tokenize()
        print_success(f"Lexer    — {len(tokens)} tokens")

        parser  = Parser(tokens)
        program = parser.parse()
        print_success(f"Parser   — {len(program.statements)} statements")

        elapsed = (time.perf_counter() - start) * 1000
        print_success(f"Build OK — no errors ({elapsed:.2f}ms)")
        return True

    except Exception as e:
        print_error(f"Build failed: {e}")
        return False


# ── nekova clean ──────────────────────────────────────────────────────────────

def cmd_clean():
    """Remove Python cache files from the project."""
    print_info("Cleaning cache files...")
    removed = 0

    for dirpath, dirs, files in os.walk("."):
        if "venv" in dirpath:
            continue
        for d in dirs:
            if d == "__pycache__":
                import shutil
                shutil.rmtree(os.path.join(dirpath, d))
                removed += 1
        for f in files:
            if f.endswith(".pyc"):
                os.remove(os.path.join(dirpath, f))
                removed += 1

    print_success(f"Cleaned {removed} cache items.")