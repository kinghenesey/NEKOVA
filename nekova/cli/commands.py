# =============================================================
# NEKOVA CLI — Commands
# =============================================================
# Implements all NEKOVA developer commands:
#   run     — execute an .NEKOVA file
#   test    — run all test suites
#   new     — create a new NEKOVA project
#   info    — show NEKOVA system information
#   build   — check and validate an .NEKOVA file
#   clean   — remove cache files

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

    # Show installed packages
    from nekova.packages import load_registry, get_available
    installed = load_registry()
    available = get_available()
    print(f"  {'Packages':<20} "
          f"{len(installed)}/{len(available)} installed")

    # Show stdlib modules
    from nekova.stdlib import MODULES
    print(f"  {'Stdlib modules':<20} {len(MODULES)}")
    print()


def cmd_new(project_name: str):
    """Create a new NEKOVA project with starter files."""
    if not project_name:
        print_error("Please provide a project name.")
        print_info("Usage:  python main.py new myproject")
        return False

    # Create project folder
    if os.path.exists(project_name):
        print_error(f"Folder '{project_name}' already exists.")
        return False

    print_info(f"Creating project '{project_name}'...")

    # Create directory structure
    dirs = [
        project_name,
        os.path.join(project_name, "src"),
        os.path.join(project_name, "tests"),
    ]

    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Create main.NEKOVA
    main_NEKOVA = os.path.join(project_name, "src", "main.NEKOVA")
    with open(main_NEKOVA, "w", encoding="utf-8") as f:
        f.write(f'''# {project_name} — NEKOVA Project
# Created with NEKOVA v{NEKOVA_VERSION}

name = "{project_name}"
show "Welcome to " + name
show "Built with NEKOVA {NEKOVA_VERSION}"
''')

    # Create README
    readme = os.path.join(project_name, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(f'''# {project_name}

An NEKOVA language project.

## Run

```bash
python main.py src/main.NEKOVA
```

## Built with

NEKOVA v{NEKOVA_VERSION} · {NEKOVA_CODENAME}
''')

    # Create project config
    config = os.path.join(project_name, "NEKOVA.json")
    import json
    with open(config, "w", encoding="utf-8") as f:
        json.dump({
            "name":    project_name,
            "version": "1.0.0",
            "main":    "src/main.NEKOVA",
            "NEKOVA":    NEKOVA_VERSION,
        }, f, indent=2)

    print_success(f"Project '{project_name}' created!")
    print()
    print(f"  {Color.DIM}Structure:{Color.RESET}")
    print(f"  {project_name}/")
    print(f"  ├── src/")
    print(f"  │   └── main.NEKOVA")
    print(f"  ├── tests/")
    print(f"  └── README.md")
    print()
    print_info(f"Run your project:")
    print(f"  {Color.CYAN}cd {project_name}{Color.RESET}")
    print(f"  {Color.CYAN}python ../main.py src/main.NEKOVA{Color.RESET}")
    print()
    return True


def cmd_test():
    """Run all NEKOVA test suites."""
    print()
    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA Test Runner{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()

    # Get project root directory
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    test_files = [
        ("Phase 1 — Foundation",   "tests/test_phase1.py"),
        ("Phase 2 — Lexer",        "tests/test_phase2.py"),
        ("Phase 3 — Parser",       "tests/test_phase3.py"),
        ("Phase 4 — Interpreter",  "tests/test_phase4.py"),
        ("Phase 5 — Stdlib",       "tests/test_phase5.py"),
        ("Phase 7 — AI Runtime",   "tests/test_phase7.py"),
        ("Phase 8 — Packages",     "tests/test_phase8.py"),
    ]

    total_passed = 0
    total_failed = 0
    start_time   = time.perf_counter()

    for name, filepath in test_files:
        full_path = os.path.join(root, filepath)

        if not os.path.exists(full_path):
            print(f"  {Color.DIM}⊘ {name} — not found{Color.RESET}")
            continue

        result = subprocess.run(
            [sys.executable, full_path],
            capture_output=True,
            text=True,
            cwd=root,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )

        # unittest writes results to stderr, install msgs to stdout
        output = result.stderr
        passed, failed = _parse_test_results(output)
        total_passed += passed
        total_failed += failed

        if failed == 0 and passed > 0:
            print(f"  {Color.GREEN}✓{Color.RESET} "
                  f"{name:<30} "
                  f"{Color.DIM}{passed} passed{Color.RESET}")
        elif failed == 0 and passed == 0:
            print(f"  {Color.YELLOW}?{Color.RESET} "
                  f"{name:<30} "
                  f"{Color.DIM}no results{Color.RESET}")
        else:
            print(f"  {Color.RED}✗{Color.RESET} "
                  f"{name:<30} "
                  f"{Color.RED}{failed} failed{Color.RESET}, "
                  f"{Color.DIM}{passed} passed{Color.RESET}")

    elapsed = (time.perf_counter() - start_time) * 1000
    print()
    print_separator()

    if total_failed == 0:
        print_success(
            f"All {total_passed} tests passed "
            f"in {elapsed:.0f}ms"
        )
    else:
        print_error(
            f"{total_failed} tests failed, "
            f"{total_passed} passed"
        )
    print()
    return total_failed == 0

def cmd_build(filepath: str):
    """
    Validate and check an .NEKOVA file without executing it.
    Runs the file through Lexer and Parser only.
    """
    if not filepath:
        print_error("Please provide a file to build.")
        print_info("Usage:  python main.py build app.NEKOVA")
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

        # Lex
        lexer  = Lexer(source)
        tokens = lexer.tokenize()
        print_success(f"Lexer    — {len(tokens)} tokens")

        # Parse
        parser  = Parser(tokens)
        program = parser.parse()
        print_success(f"Parser   — "
                      f"{len(program.statements)} statements")

        elapsed = (time.perf_counter() - start) * 1000
        print_success(f"Build OK — no errors found "
                      f"({elapsed:.2f}ms)")
        return True

    except Exception as e:
        print_error(f"Build failed: {e}")
        return False


def cmd_clean():
    """Remove Python cache files from the project."""
    print_info("Cleaning cache files...")
    removed = 0

    for root, dirs, files in os.walk("."):
        # Skip venv
        if "venv" in root:
            continue

        for d in dirs:
            if d == "__pycache__":
                import shutil
                path = os.path.join(root, d)
                shutil.rmtree(path)
                removed += 1

        for f in files:
            if f.endswith(".pyc"):
                os.remove(os.path.join(root, f))
                removed += 1

    print_success(f"Cleaned {removed} cache items.")


def _parse_test_results(output: str):
    """Parse unittest output to get pass/fail counts."""
    passed = 0
    total  = 0

    lines = output.splitlines()

    # Find "Ran X tests" line
    for line in lines:
        line = line.strip()
        if line.startswith("Ran ") and "test" in line:
            try:
                total = int(line.split()[1])
            except Exception:
                pass

    if total == 0:
        return 0, 0

    # Find the LAST occurrence of OK or FAILED
    # scan from bottom up, skip blank lines
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        if line == "OK":
            return total, 0
        if line.startswith("FAILED"):
            fail_count = 0
            if "failures=" in line:
                try:
                    fail_count += int(
                        line.split("failures=")[1]
                        .split(")")[0].split(",")[0])
                except Exception:
                    pass
            if "errors=" in line:
                try:
                    fail_count += int(
                        line.split("errors=")[1]
                        .split(")")[0].split(",")[0])
                except Exception:
                    pass
            return total - fail_count, fail_count

    return total, 0
