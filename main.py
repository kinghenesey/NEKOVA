#!/usr/bin/env python3
# =============================================================
# NEKOVA Language â€” Main Entry Point
# =============================================================
# Usage:
#   python main.py <file.nk>              Run a file
#   python main.py run <file.nk>          Run a file
#   python main.py test                     Run all tests
#   python main.py build <file.nk>        Validate a file
#   python main.py new <project>            Create a project
#   python main.py info                     System info
#   python main.py clean                    Remove cache
#   python main.py --install <package>      Install package
#   python main.py --uninstall <package>    Uninstall package
#   python main.py --packages               List packages
#   python main.py --version                Show version
#   python main.py --help                   Show help

import sys
import io
import os
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables from .env file
def _load_env():
    env_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

_load_env()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nekova.config import NEKOVA_VERSION, NEKOVA_CODENAME, Color
from nekova.cli    import print_banner, print_error, print_info, print_success, print_warning
from nekova.toml_loader import load_config, ConfigError
from runner import NEKOVARunner


HELP_TEXT = f"""
{Color.CYAN}{Color.BOLD}NEKOVA Programming Language{Color.RESET} \
v{NEKOVA_VERSION} Â· {NEKOVA_CODENAME}

{Color.BOLD}Running files:{Color.RESET}
  python main.py <file.nk>              Run an NEKOVA file
  python main.py <file.nk> --debug      Run with debug output
  python main.py <file.nk> --compile    Run using the compiler
  python main.py run <file.nk>          Run an NEKOVA file
  python main.py repl                     Start interactive shell

{Color.BOLD}Developer tools:{Color.RESET}
  python main.py test                     Run all test suites
  python main.py build <file.nk>        Validate a file
  python main.py new <project-name>       Create a new project
  python main.py info                     Show system info
  python main.py clean                    Remove cache files
  python main.py debug <file.nk>        Visual debugger
  python main.py repl                     Interactive shell
  python main.py ide                      Launch Web 
  python main.py format <file.nk>        Format code style
  python main.py format --check <file>     Check formatting

{Color.BOLD}Deployment:{Color.RESET}
  python main.py compile <file.nk>      Compile to native/Python
  python main.py export <file.nk>       Export to HTML/script
  python main.py package <dir>            Package a project
  python main.py publish <pkg.nkpkg>    Publish to registry
  python main.py deploy <file.nk>       Full deploy pipeline

{Color.BOLD}Marketplace:{Color.RESET}
  python main.py marketplace              Browse all packages
  python main.py marketplace search <q>  Search packages
  python main.py marketplace install <n> Install a package
  python main.py marketplace info <name> Package details
  python main.py marketplace featured    Top packages

{Color.BOLD}Package manager:{Color.RESET}
  python main.py --packages               List all packages
  python main.py --install <package>      Install a package
  python main.py --uninstall <package>    Uninstall a package

{Color.BOLD}Other:{Color.RESET}
  python main.py --version                Show version
  python main.py --help                   Show this help

{Color.BOLD}Examples:{Color.RESET}
  python main.py examples/hello.nk
  python main.py deploy examples/ui_demo.nk
  python main.py --install charts
  python main.py new myapp
  python main.py test
"""


def parse_args(argv: list) -> dict:
    args = {
        "file":        None,
        "command":     None,
        "arg":         None,
        "debug":       False,
        "sandbox":     False,
        "sandbox_mode": "strict",
        "compile":     False,
        "version":     False,
        "help":        False,
        "packages":    False,
        "install":     None,
        "uninstall":   None,
        "script_args": {},   # --key value pairs passed through to .nk scripts
        "watch":       False,
        "template":    "default",
    }

    if not argv:
        return args

    # ── Known NEKOVA CLI flags ────────────────────────────────
    KNOWN_FLAGS = {"--debug", "--version", "--help", "--packages", "--compile", "--watch"}
    KNOWN_VALUE_FLAGS = {"--install", "--uninstall"}

    argv_list = list(argv)

    args["debug"]    = "--debug"    in argv_list
    args["watch"]    = "--watch"    in argv_list
    args["sandbox"]  = "--sandbox"  in argv_list
    args["sandbox_mode"] = "strict"
    if "--sandbox-mode" in argv_list:
        idx = argv_list.index("--sandbox-mode")
        if idx + 1 < len(argv_list):
            args["sandbox_mode"] = argv_list[idx + 1]
    # --template <name>
    for i, a in enumerate(argv_list):
        if a == "--template" and i + 1 < len(argv_list):
            args["template"] = argv_list[i + 1]
    args["version"]  = "--version"  in argv_list
    args["help"]     = "--help"     in argv_list
    args["packages"] = "--packages" in argv_list
    args["compile"]  = "--compile"  in argv_list

    # Handle --install and --uninstall
    for i, a in enumerate(argv_list):
        if a == "--install" and i + 1 < len(argv_list):
            args["install"] = argv_list[i + 1]
        if a == "--uninstall" and i + 1 < len(argv_list):
            args["uninstall"] = argv_list[i + 1]

    # ── Separate positional values from flags ─────────────────
    values = [a for a in argv_list if not a.startswith("--")]

    # ── Extract script args: unknown --key value pairs ────────
    # These are --key value pairs that aren't NEKOVA CLI flags.
    # They get passed into the .nk script as args.key
    script_args = {}
    i = 0
    while i < len(argv_list):
        a = argv_list[i]
        if a.startswith("--") and a not in KNOWN_FLAGS and a not in KNOWN_VALUE_FLAGS:
            key = a[2:]  # strip leading --
            if i + 1 < len(argv_list) and not argv_list[i + 1].startswith("--"):
                script_args[key] = argv_list[i + 1]
                i += 2
                continue
            else:
                # Boolean flag with no value → "true"
                script_args[key] = "true"
        i += 1
    args["script_args"] = script_args

    # ── Subcommand dispatch ───────────────────────────────────
    commands = {
        "run", "test", "build", "new", "info", "clean",
        "export", "package", "publish", "deploy", "repl",
        "marketplace", "debug", "ide", "format", "notebook",
        "compile", "fmt", "check",
        # Phase 11
        "install", "uninstall", "search", "packages",
        "pkg-info", "deps",
        # Phase 12
        "watch",
    }
    if values and values[0] in commands:
        args["command"] = values[0]
        if len(values) > 1:
            args["arg"] = values[1]
    elif values:
        args["file"] = values[0]

    return args

def _apply_toml_config(config):
    """Apply nekova.toml AI model settings before running."""
    if config.ai.model and config.ai.model != "mock":
        try:
            from nekova.ai.providers import set_provider
            set_provider(config.ai.model)
        except Exception:
            pass
    if config.ai.api_key:
        key_map = {"claude": "ANTHROPIC_API_KEY",
                   "gemini": "GEMINI_API_KEY",
                   "openai": "OPENAI_API_KEY"}
        env_var = key_map.get(config.ai.model)
        if env_var and not os.environ.get(env_var):
            os.environ[env_var] = config.ai.api_key
    # Apply think timeout from [ai] think_timeout in nekova.toml
    try:
        from nekova.ai.providers import set_think_timeout
        set_think_timeout(config.ai.think_timeout)
    except Exception:
        pass

def main():
    argv = sys.argv[1:]

    if not argv:
        print_banner()
        print(HELP_TEXT)
        sys.exit(0)

    args = parse_args(argv)

    # â”€â”€ Flag commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    if "--repl" in argv:
        print_banner()
        from repl import REPL
        repl = REPL()
        repl.start()
        sys.exit(0)

    if args["version"]:
        print(f"NEKOVA v{NEKOVA_VERSION} Â· {NEKOVA_CODENAME}")
        sys.exit(0)

    if args["help"]:
        print_banner()
        print(HELP_TEXT)
        sys.exit(0)

    if args["packages"]:
        print_banner()
        from nekova.cli.package_manager import list_packages
        list_packages()
        sys.exit(0)

    if args["install"]:
        print_banner()
        from nekova.cli.package_manager import install_package
        success = install_package(args["install"])
        sys.exit(0 if success else 1)

    if args["uninstall"]:
        print_banner()
        from nekova.cli.package_manager import uninstall_package
        success = uninstall_package(args["uninstall"])
        sys.exit(0 if success else 1)

    # â”€â”€ Subcommands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    if args["command"]:
        print_banner()
        cmd = args["command"]
        arg = args["arg"]

        from nekova.cli.commands import (
            cmd_info, cmd_new, cmd_test,
            cmd_build, cmd_clean,
            cmd_fmt, cmd_check,
        )

        if cmd == "info":
            if arg:
                from nekova.cli.package_manager import package_info
                success = package_info(arg)
                sys.exit(0 if success else 1)
            else:
                cmd_info()
                sys.exit(0)

        if cmd == "test":
            success = cmd_test()
            sys.exit(0 if success else 1)

        if cmd == "clean":
            cmd_clean()
            sys.exit(0)

        if cmd == "new":
            success = cmd_new(arg, template=args["template"])
            sys.exit(0 if success else 1)

        if cmd == "build":
            success = cmd_build(arg)
            sys.exit(0 if success else 1)

        if cmd == "fmt":
            dry_run = "--check" in argv or "--dry-run" in argv
            success = cmd_fmt(arg, dry_run=dry_run)
            sys.exit(0 if success else 1)

        if cmd == "check":
            success = cmd_check(arg)
            sys.exit(0 if success else 1)

        if cmd == "run":
            if args["watch"]:
                from watcher import watch
                # resolve filepath first (may come from toml)
                run_file = arg
                if not run_file:
                    try:
                        _cfg = load_config()
                        if _cfg:
                            run_file = _cfg.entry_path
                    except Exception:
                        pass
                if not run_file:
                    print_error("No file specified and no nekova.toml found.")
                    sys.exit(1)
                watch(run_file)
                sys.exit(0)
            if not arg:
                try:
                    config = load_config()
                except ConfigError as e:
                    print_error(f"Config error: {e}")
                    sys.exit(1)
                if config is None:
                    print_error(
                        "No file specified and no nekova.toml found.\n"
                        "  Usage: nekova run app.nk\n"
                        "  Or create a nekova.toml with [project] entry = \"main.nk\""
                    )
                    sys.exit(1)
                _apply_toml_config(config)
                print_info(f"{config.project.name} v{config.project.version}")
                if not args["debug"] and config.run.debug:
                    args["debug"] = True
                strict = config.run.strict_types
                arg = config.entry_path
                runner = NEKOVARunner(filepath=arg, debug=args["debug"],
                                      strict_types=strict,
                                      script_args=args["script_args"])
            else:
                runner = NEKOVARunner(filepath=arg, debug=args["debug"],
                                      script_args=args["script_args"])
            if args["sandbox"]:
                # Run file in sandbox mode
                mode = args.get("sandbox_mode", "strict")
                filepath = arg
                if not filepath:
                    print_error("No file specified for sandbox run.")
                    sys.exit(1)
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
                from nekova.sandbox.runner import run_sandboxed
                result = run_sandboxed(source, mode=mode)
                if result.output:
                    print(result.output, end="")
                if result.error:
                    print_error(f"Sandbox error: {result.error}")
                if result.violations:
                    print_warning(f"Violations: {result.violations}")
                status = "safe" if result.ok else "unsafe"
                print_info(f"[sandbox:{mode}] {status} ({result.duration:.3f}s)")
                sys.exit(0 if result.ok else 1)
            exit_code = runner.run()
            sys.exit(exit_code)
        
        if cmd == "watch":
            from watcher import watch
            if not arg:
                try:
                    _cfg = load_config()
                    arg = _cfg.entry_path if _cfg else None
                except Exception:
                    arg = None
            if not arg:
                print_error("No file specified. Usage: nekova watch app.nk")
                sys.exit(1)
            watch(arg)
            sys.exit(0)

        if cmd == "repl":
            from repl import REPL
            repl = REPL()
            repl.start()
            sys.exit(0)
        
        if cmd == "debug":
            if not arg:
                print_error(
                    "Please provide a file to debug.\n"
                    "  Usage: python main.py debug app.nk"
                )
                sys.exit(1)
            from debugger import Debugger
            debugger = Debugger(filepath=arg)
            debugger.start()
            sys.exit(0)
        
        if cmd == "ide":
            from nekova.web_ide.ide_server import start_ide
            port = int(arg) if arg and arg.isdigit() else 3000
            start_ide(port=port)
            sys.exit(0)
        
        if cmd == "format":
            from formatter import format_file, format_directory
            check_only = "--check" in argv
            if arg and not arg.startswith("--"):
                success = format_file(
                    arg, check_only=check_only)
            else:
                print_info("Formatting all .nk files...")
                count = format_directory("examples")
                print_success(
                    f"Formatted {count} files")
            sys.exit(0)
        
        if cmd == "notebook":
            from notebook import start_notebook
            port = 4000
            start_notebook(filepath=arg, port=port)
            sys.exit(0)

        if cmd == "marketplace":
            from nekova.cli.marketplace_cmd import cmd_marketplace
            # arg could be subcommand, values[1] could be the query
            values = [a for a in argv
                      if not a.startswith("--")]
            subcommand = values[1] if len(values) > 1 else ""
            mp_arg     = values[2] if len(values) > 2 else ""
            success = cmd_marketplace(subcommand, mp_arg)
            sys.exit(0 if success else 1)

        if cmd == "export":
            from nekova.cli.deploy import cmd_export
            success = cmd_export(arg)
            sys.exit(0 if success else 1)

        if cmd == "package":
            from nekova.cli.deploy import cmd_package
            success = cmd_package(arg or ".")
            sys.exit(0 if success else 1)

        if cmd == "publish":
            from nekova.cli.deploy import cmd_publish
            success = cmd_publish(arg)

        # Phase 11: Package system subcommands
        if cmd == "install":
            from nekova.cli.package_manager import install_package, install_from_toml
            if arg:
                success = install_package(arg)
            else:
                success = install_from_toml()
            sys.exit(0 if success else 1)

        if cmd == "uninstall":
            from nekova.cli.package_manager import uninstall_package
            if not arg:
                print_error("Usage: nekova uninstall <package>")
                sys.exit(1)
            success = uninstall_package(arg)
            sys.exit(0 if success else 1)

        if cmd == "search":
            from nekova.cli.package_manager import search, list_packages
            if arg:
                success = search(arg)
            else:
                success = list_packages()
            sys.exit(0 if success else 1)

        if cmd == "info":
            from nekova.cli.package_manager import package_info
            if not arg:
                print_error("Usage: nekova info <package>")
                sys.exit(1)
            success = package_info(arg)
            sys.exit(0 if success else 1)

        if cmd == "deps":
            from nekova.cli.package_manager import install_from_toml
            success = install_from_toml()
            sys.exit(0 if success else 1)
            sys.exit(0 if success else 1)

        if cmd == "deploy":
            # Check for: deploy cloud app.nk
            values = [a for a in argv
                      if not a.startswith("--")]
            if len(values) >= 3 and values[1] == "cloud":
                from nekova.cli.deploy import cmd_deploy_cloud
                success = cmd_deploy_cloud(values[2])
            else:
                from nekova.cli.deploy import cmd_deploy
                success = cmd_deploy(arg)
            sys.exit(0 if success else 1)
        
        if cmd == "compile":
            if not arg:
                print_error(
                    "Please provide a file to compile.\n"
                    "  Usage: python main.py compile app.nk"
                )
                sys.exit(1)
            from nekova.compiler.llvm_backend import LLVMCompiler
            compiler = LLVMCompiler()
            print_info(f"Compiling '{arg}'...")
            try:
                output = compiler.compile(arg)
                print_success(f"Compiled â†’ {output}")
            except Exception as e:
                print_error(f"Compile error: {e}")
                sys.exit(1)
            sys.exit(0)

    # â”€â”€ Direct file execution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    if args["file"]:
        print_banner()
        runner    = NEKOVARunner(filepath=args["file"],
                               debug=args["debug"],
                               compile_mode=args["compile"],
                               script_args=args["script_args"])
        exit_code = runner.run()
        sys.exit(exit_code)

    # â”€â”€ Nothing matched â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print_error(
        "Unknown command. "
        "Run 'python main.py --help' for usage."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()