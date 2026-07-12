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
    print(f"  {Color.DIM}{chr(9472) * 40}{Color.RESET}")
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


# ── nekova new [--template <name>] ────────────────────────────────────────────

def cmd_new(project_name: str = None, template: str = "default"):
    """Create a new NEKOVA project, optionally from a template.

    Templates: default | web | ai | fullstack
    Usage:
        nekova new myapp
        nekova new myapp --template web
        nekova new myapp --template ai
        nekova new myapp --template fullstack
        nekova new                          interactive wizard
    """
    author, description = "", None

    if not project_name:
        # No name given at all — previously this just errored out
        # ("Please provide a project name.") and told you the flag
        # syntax to try again with. Now it launches a short
        # interactive wizard instead, prompting for the name,
        # template, and optional author/description one step at a
        # time, which is friendlier for anyone who doesn't already
        # know the exact --template flag they want.
        project_name, template, author, description = _new_project_wizard()
        if not project_name:
            return False

    if os.path.exists(project_name):
        print_error(f"Folder '{project_name}' already exists.")
        return False

    from nekova.cli.templates import scaffold_project, list_templates, TEMPLATE_DESCRIPTIONS

    valid = [t for t, _ in list_templates()]
    if template not in valid:
        print_error(f"Unknown template '{template}'.")
        print_info(f"Available templates: {', '.join(valid)}")
        return False

    tpl_desc = TEMPLATE_DESCRIPTIONS.get(template, "")
    print_info(f"Creating project '{project_name}' [{template}] — {tpl_desc}...")

    ok = scaffold_project(project_name, template, author=author, description=description)
    if not ok:
        print_error("Failed to create project.")
        return False

    print_success(f"Project '{project_name}' created!")
    print()

    # Show template-aware structure
    _print_project_structure(project_name, template)

    print_info("Get started:")
    print(f"  {Color.CYAN}cd {project_name}{Color.RESET}")
    print(f"  {Color.CYAN}nekova run{Color.RESET}")
    print()
    return True


def _new_project_wizard():
    """
    Interactive `nekova new` wizard: prompts for a project name,
    template, and optional author/description, one step at a time.
    Returns (name, template, author, description), or (None, None,
    None, None) if the person cancels (Ctrl+C/Ctrl+D or an empty
    name).
    """
    from nekova.cli.templates import list_templates

    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA New Project Wizard{Color.RESET}")
    print(f"  {Color.DIM}{chr(9472) * 40}{Color.RESET}")
    print()

    try:
        name = input("  Project name: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None, None, None

    if not name:
        print_error("Project name cannot be empty.")
        return None, None, None, None

    templates = list_templates()
    print()
    print(f"  {Color.BOLD}Templates:{Color.RESET}")
    for i, (tname, tdesc) in enumerate(templates, start=1):
        print(f"    {i}. {tname:<10} {Color.DIM}{tdesc}{Color.RESET}")
    print()

    try:
        choice = input(f"  Choose a template [1-{len(templates)}] "
                        f"(default: 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None, None, None

    if not choice:
        template = templates[0][0]
    else:
        try:
            template = templates[int(choice) - 1][0]
        except (ValueError, IndexError):
            print_error(f"Invalid choice '{choice}'.")
            return None, None, None, None

    try:
        author = input("  Author (optional): ").strip()
        description = input("  Description (optional): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, None, None, None

    print()
    return name, template, author, (description or None)


def _print_project_structure(project_name: str, template: str):
    print(f"  {Color.DIM}Structure:{Color.RESET}")
    print(f"  {project_name}/")
    if template == "fullstack":
        print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} src/")
        print(f"  {chr(9474)}   {chr(9500)}{chr(9472)}{chr(9472)} main.nk       {Color.DIM}(routes + server){Color.RESET}")
        print(f"  {chr(9474)}   {chr(9500)}{chr(9472)}{chr(9472)} db.nk         {Color.DIM}(database helpers){Color.RESET}")
        print(f"  {chr(9474)}   {chr(9492)}{chr(9472)}{chr(9472)} ai.nk         {Color.DIM}(AI helpers){Color.RESET}")
    elif template == "ai":
        print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} src/")
        print(f"  {chr(9474)}   {chr(9500)}{chr(9472)}{chr(9472)} main.nk       {Color.DIM}(think / remember){Color.RESET}")
        print(f"  {chr(9474)}   {chr(9492)}{chr(9472)}{chr(9472)} agent.nk      {Color.DIM}(AI tasks){Color.RESET}")
    elif template == "web":
        print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} src/")
        print(f"  {chr(9474)}   {chr(9500)}{chr(9472)}{chr(9472)} main.nk       {Color.DIM}(routes + serve){Color.RESET}")
        print(f"  {chr(9474)}   {chr(9492)}{chr(9472)}{chr(9472)} routes/api.nk {Color.DIM}(API routes){Color.RESET}")
    else:
        print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} src/")
        print(f"  {chr(9474)}   {chr(9492)}{chr(9472)}{chr(9472)} main.nk")
    print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} tests/")
    print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} nekova.toml")
    print(f"  {chr(9500)}{chr(9472)}{chr(9472) * 2} .env.example")
    print(f"  {chr(9492)}{chr(9472)}{chr(9472) * 2} README.md")
    print()


def _write(path: str, content: str):
    """Write UTF-8 file without BOM."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ── nekova test ───────────────────────────────────────────────────────────────

def cmd_test():
    """Run the current project's test suite (./tests/) via pytest.

    Previously this resolved `root` from __file__ — the *installed
    package's* location — rather than the directory the user actually
    ran `nekova test` from. That meant it could never find a
    scaffolded project's own tests/ folder (it was always looking
    inside the package install dir instead), and even for the dev
    repo itself the path math was off by one directory level.
    """
    print()
    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA Test Runner{Color.RESET}")
    print(f"  {Color.DIM}{chr(9472) * 40}{Color.RESET}")
    print()

    project_root = os.getcwd()
    tests_dir = os.path.join(project_root, "tests")

    if not os.path.isdir(tests_dir):
        print_error(
            f"No 'tests/' directory found in '{project_root}'.\n"
            f"  Run 'nekova test' from your project's root "
            f"(the folder with nekova.toml), or scaffold a new "
            f"project with 'nekova new'."
        )
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=project_root,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

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

# =============================================================
# Phase 10: fmt and check commands
# =============================================================

def cmd_fmt(target: str = None, dry_run: bool = False, show_diff: bool = False):
    """
    Format NEKOVA source files.
    nekova fmt            format all .nk files in project
    nekova fmt app.nk     format a single file
    nekova fmt --check    dry-run (show what would change)
    nekova fmt --diff     show a unified diff of what would change,
                          without writing anything
    """
    import difflib
    from nekova.cli.formatter import fmt_file, fmt_directory

    _RED   = "\033[38;5;196m"
    _GREEN = "\033[92m"
    _GOLD  = "\033[38;5;172m"
    _DIM   = "\033[2m"
    _BOLD  = "\033[1m"
    _RESET = "\033[0m"

    def _print_diff(filepath, original, formatted):
        diff_lines = difflib.unified_diff(
            original.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=f"{filepath} (before)",
            tofile=f"{filepath} (after)",
        )
        for line in diff_lines:
            line = line.rstrip("\n")
            if line.startswith("+") and not line.startswith("+++"):
                print(f"{_GREEN}{line}{_RESET}")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"{_RED}{line}{_RESET}")
            elif line.startswith("@@"):
                print(f"{_GOLD}{line}{_RESET}")
            else:
                print(f"{_DIM}{line}{_RESET}")

    if target and target.endswith(".nk"):
        try:
            changed, original, formatted = fmt_file(target, dry_run=dry_run)
            if changed:
                if show_diff:
                    _print_diff(target, original, formatted)
                elif dry_run:
                    print(f"{_GOLD}  would reformat  {target}{_RESET}")
                else:
                    print(f"{_GREEN}  reformatted   {target}{_RESET}")
            else:
                print(f"{_DIM}  unchanged       {target}{_RESET}")
        except Exception as e:
            print(f"{_RED}  error         {target}: {e}{_RESET}")
        return True
    else:
        dirpath = target or "."

        if show_diff:
            # Diffing needs the actual before/after text per file, not
            # just the (path, changed) pairs fmt_directory() returns
            # — walk files directly so each diff can be printed as
            # it's computed, same as fmt_directory()'s own walk.
            changed_count = 0
            total = 0
            for root, dirs, files in os.walk(dirpath):
                dirs[:] = [d for d in dirs
                           if not d.startswith(".")
                           and d not in ("__pycache__", "node_modules",
                                         ".git", "dist", "build", ".nekova")]
                for fname in files:
                    if not fname.endswith(".nk"):
                        continue
                    fpath = os.path.join(root, fname)
                    total += 1
                    try:
                        changed, original, formatted = fmt_file(fpath, dry_run=True)
                        if changed:
                            changed_count += 1
                            _print_diff(fpath, original, formatted)
                    except Exception as e:
                        print(f"{_RED}  error  {fpath}: {e}{_RESET}")

            if total == 0:
                print(f"{_DIM}  No .nk files found in '{dirpath}'{_RESET}")
                return True

            print()
            print(f"  {_BOLD}{changed_count} file(s) would be reformatted{_RESET} "
                  f"{_DIM}(of {total} total){_RESET}")
            return True

        results = fmt_directory(dirpath, dry_run=dry_run)

        if not results:
            print(f"{_DIM}  No .nk files found in '{dirpath}'{_RESET}")
            return True

        changed_count = 0
        for fpath, changed in results:
            if isinstance(changed, str) and changed.startswith("ERROR"):
                print(f"{_RED}  {changed}  {fpath}{_RESET}")
            elif changed:
                changed_count += 1
                if dry_run:
                    print(f"{_GOLD}  would reformat  {fpath}{_RESET}")
                else:
                    print(f"{_GREEN}  reformatted   {fpath}{_RESET}")
            else:
                print(f"{_DIM}  unchanged       {fpath}{_RESET}")

        action = "would reformat" if dry_run else "reformatted"
        print()
        print(f"  {_BOLD}{changed_count} file(s) {action}{_RESET} {_DIM}(of {len(results)} total){_RESET}")
        return True


def cmd_check(target: str = None):
    """
    Statically analyse NEKOVA source files.
    nekova check            check all .nk files in project
    nekova check app.nk     check a single file
    """
    from nekova.cli.checker import check_file, check_directory

    _RED   = "\033[38;5;196m"
    _GOLD  = "\033[38;5;172m"
    _CYAN  = "\033[96m"
    _GREEN = "\033[92m"
    _DIM   = "\033[2m"
    _BOLD  = "\033[1m"
    _RESET = "\033[0m"

    def _render_issue(issue, filepath):
        level_colour = {"error": _RED, "warning": _GOLD, "info": _CYAN}.get(issue.level, _DIM)
        level_label  = {"error": "error", "warning": "warn ", "info": "info "}.get(issue.level, issue.level)
        print(f"  {level_colour}{_BOLD}[{issue.code}]{_RESET} {level_colour}{level_label}{_RESET} "
              f"{_DIM}{filepath}:{issue.line}{_RESET}  {issue.message}")
        if issue.hint:
            print(f"         {_DIM}hint: {issue.hint}{_RESET}")

    all_clean  = True
    total_errs = 0
    total_warn = 0

    if target and target.endswith(".nk"):
        files = {target: check_file(target)}
    else:
        files = check_directory(target or ".")

    if not files:
        print(f"{_DIM}  No .nk files found to check.{_RESET}")
        return True

    for fpath, issues in files.items():
        if issues:
            print()
            print(f"  {_BOLD}{fpath}{_RESET}")
            for issue in issues:
                _render_issue(issue, fpath)
                if issue.level == "error":
                    total_errs += 1
                    all_clean = False
                elif issue.level == "warning":
                    total_warn += 1

    print()
    if all_clean and total_warn == 0:
        print(f"  {_GREEN}No issues found — all files look good!{_RESET}")
    else:
        if total_errs:
            print(f"  {_RED}{total_errs} error(s)  {total_warn} warning(s){_RESET}")
        else:
            print(f"  {_GOLD}{total_warn} warning(s) — no errors{_RESET}")

    return all_clean


def cmd_lock(target: str = ".", check_only: bool = False):
    """
    Generate or verify nekova.lock — a reproducible snapshot of the
    exact resolved version of every package in [dependencies]
    packages.

    nekova lock            (re)generate nekova.lock
    nekova lock --check    verify it's still in sync, don't write
                            (exits nonzero on drift — for CI)
    """
    from nekova.cli.lockfile import (
        generate_lock_data, write_lockfile, check_lockfile, LOCKFILE_NAME,
    )

    _RED   = "\033[38;5;196m"
    _GOLD  = "\033[38;5;172m"
    _GREEN = "\033[92m"
    _DIM   = "\033[2m"
    _BOLD  = "\033[1m"
    _RESET = "\033[0m"

    if check_only:
        in_sync, drift = check_lockfile(target)
        if "_missing" in drift:
            print_error(drift["_missing"])
            return False
        if in_sync:
            print_success(f"{LOCKFILE_NAME} is in sync.")
            return True
        print_error(f"{LOCKFILE_NAME} is out of sync:")
        for name, (locked_v, current_v) in drift.items():
            if locked_v is None:
                print(f"  {_GREEN}+ {name}  (new, {current_v}){_RESET}")
            elif current_v is None:
                print(f"  {_RED}- {name}  (removed, was {locked_v}){_RESET}")
            else:
                print(f"  {_GOLD}~ {name}  {locked_v} -> {current_v}{_RESET}")
        print()
        print_info("Run `nekova lock` to update it.")
        return False

    data = write_lockfile(target)
    packages = data["packages"]
    unresolved = data["unresolved"]

    if not packages and not unresolved:
        print(f"{_DIM}  No dependencies declared in nekova.toml — "
              f"wrote an empty {LOCKFILE_NAME}.{_RESET}")
        return True

    print_success(f"Wrote {LOCKFILE_NAME} ({len(packages)} package(s) locked)")
    for name, version in packages.items():
        print(f"  {_GREEN}{name}{_RESET} {_DIM}{version}{_RESET}")
    if unresolved:
        print()
        print_warning(
            f"{len(unresolved)} declared package(s) not found in the "
            f"registry (not locked): {', '.join(unresolved)}"
        )
    return True