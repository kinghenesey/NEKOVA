#!/usr/bin/env python3
# =============================================================
# NEKOVA Language â€” Main Entry Point
# =============================================================
# Usage:
#   nekova <file.nk>              Run a file
#   nekova run <file.nk>          Run a file
#   nekova test                     Run all tests
#   nekova build <file.nk>        Validate a file
#   nekova new <project>            Create a project
#   nekova info                     System info
#   nekova clean                    Remove cache
#   nekova --install <package>      Install package
#   nekova --uninstall <package>    Uninstall package
#   nekova --packages               List packages
#   nekova --version                Show version
#   nekova --help                   Show help

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
v{NEKOVA_VERSION} · {NEKOVA_CODENAME}

{Color.BOLD}Running files:{Color.RESET}
  nekova <file.nk>              Run an NEKOVA file
  nekova <file.nk> --debug      Run with debug output
  nekova <file.nk> --debug-ai   Print the exact prompt every think call sends
  nekova <file.nk> --compile    Run using the compiler
  nekova run <file.nk>          Run an NEKOVA file
  nekova repl                     Start interactive shell

{Color.BOLD}Developer tools:{Color.RESET}
  nekova test                     Run all test suites
  nekova build <file.nk>        Validate a file
  nekova new <project-name>       Create a new project
  nekova info                     Show system info
  nekova clean                    Remove cache files
  nekova debug <file.nk>        Visual debugger
  nekova repl                     Interactive shell
  nekova ide                      Launch Web 
  nekova format <file.nk>        Format code style
  nekova format --check <file>     Check formatting

{Color.BOLD}Learning tools:{Color.RESET}
  nekova learn                     Interactive guided tutorial
  nekova explain <file.nk>       Explain an error in plain language
  nekova explain <file> --no-ai  Explain without the AI addition
  nekova translate <file.py>     Translate Python to NEKOVA
  nekova classroom <dir>           Batch-grade student submissions
  nekova help <topic>              Look up a keyword (e.g. think)
  nekova run <file> --simple-errors  Plain-language error output

{Color.BOLD}AI-native tooling:{Color.RESET}
  nekova run <file> --record-ai <cassette.json>  Record real AI calls
  nekova run <file> --replay-ai <cassette.json>  Replay without an API key
  think "..." as User                              Typed + validated + re-prompted
  think "..." with budget: $0.01                   Dollar-denominated budget
  think "..." using ["a", "b", "local"]           Model fallback chain
  for chunk in think_stream("..."):                 Lazy streaming
  sandbox strict allow: [task_a, task_b]:          Capability-scoped agent
  test "x" repeat 10 times, expect at least 8 passes:  Probabilistic testing

{Color.BOLD}Deployment:{Color.RESET}
  nekova compile <file.nk>      Compile to native/Python
  nekova export <file.nk>       Export to HTML/script
  nekova package <dir>            Package a project
  nekova publish <pkg.nkpkg>    Publish to registry
  nekova deploy <file.nk>       Full deploy pipeline

{Color.BOLD}Marketplace:{Color.RESET}
  nekova marketplace              Browse all packages
  nekova marketplace search <q>  Search packages
  nekova marketplace install <n> Install a package
  nekova marketplace info <name> Package details
  nekova marketplace featured    Top packages

{Color.BOLD}Package manager:{Color.RESET}
  nekova --packages               List all packages
  nekova --install <package>      Install a package
  nekova --uninstall <package>    Uninstall a package

{Color.BOLD}Other:{Color.RESET}
  nekova --version                Show version
  nekova --help                   Show this help

{Color.BOLD}Examples:{Color.RESET}
  nekova examples/hello.nk
  nekova deploy examples/ui_demo.nk
  nekova --install charts
  nekova new myapp
  nekova test
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
        "quiet":       False,
    }

    if not argv:
        return args

    # ── Known NEKOVA CLI flags ────────────────────────────────
    KNOWN_FLAGS = {"--debug", "--debug-ai", "--version", "--help", "--packages", "--compile", "--watch", "--quiet", "-q"}
    KNOWN_VALUE_FLAGS = {"--install", "--uninstall"}

    argv_list = list(argv)

    args["debug"]    = "--debug"    in argv_list
    args["debug_ai"] = "--debug-ai" in argv_list
    # --why: explain which internal grammar rule or interpreter
    # check actually raised an error, for anyone debugging NEKOVA
    # itself or trying to understand its error taxonomy in depth.
    args["why"] = "--why" in argv_list
    # --simple-errors: strips jargon from error output entirely —
    # no error codes, no "--> file:line" arrows, plain sentences.
    # Aimed at Phase 26b's beginner/classroom audience, distinct
    # from --why which adds detail rather than removing it.
    args["simple_errors"] = "--simple-errors" in argv_list
    # Phase 26c — cassette record/replay for deterministic AI testing
    args["record_ai"] = None
    args["replay_ai"] = None
    if "--record-ai" in argv_list:
        idx = argv_list.index("--record-ai")
        if idx + 1 < len(argv_list):
            args["record_ai"] = argv_list[idx + 1]
    if "--replay-ai" in argv_list:
        idx = argv_list.index("--replay-ai")
        if idx + 1 < len(argv_list):
            args["replay_ai"] = argv_list[idx + 1]
    args["watch"]    = "--watch"    in argv_list
    args["sandbox"]  = "--sandbox"  in argv_list
    # --quiet/-q: skip the banner — makes the CLI usable in scripts,
    # CI, and piped output, where ~12 lines of ASCII logo ahead of
    # every command's actual output was previously unavoidable (no
    # such flag existed at all).
    args["quiet"]    = ("--quiet" in argv_list) or ("-q" in argv_list)
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
        "compile", "fmt", "check", "lsp", "lock",
        # Phase 11
        "install", "uninstall", "search", "packages",
        "pkg-info", "deps",
        # Phase 12
        "watch",
        # Phase 26b — Education Layer
        "explain", "learn", "translate", "classroom", "help",
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
        print(f"NEKOVA v{NEKOVA_VERSION} · {NEKOVA_CODENAME}")
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

    # --- LSP server ---
    # Dispatched before print_banner() below on purpose: editors spawn
    # `nekova lsp` as a subprocess and read its stdout as the raw
    # JSON-RPC wire protocol. Anything else written there -- the
    # banner, a stray print, whatever -- corrupts every message after
    # it. This is the one command that can never go through the
    # normal print_banner() + dispatch path every other subcommand
    # uses.
    if args.get("command") == "lsp":
        from nekova.lsp.server import main as lsp_main
        lsp_main()
        sys.exit(0)

    if args["command"]:
        print_banner()
        cmd = args["command"]
        arg = args["arg"]

        from nekova.cli.commands import (
            cmd_info, cmd_new, cmd_test,
            cmd_build, cmd_clean,
            cmd_fmt, cmd_check, cmd_lock,
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
            show_diff = "--diff" in argv
            # --diff shows what would change instead of writing it —
            # matches the familiar convention from tools like Black's
            # own --diff flag, rather than silently writing AND
            # printing a diff, which nobody asked for.
            if show_diff:
                dry_run = True
            success = cmd_fmt(arg, dry_run=dry_run, show_diff=show_diff)
            sys.exit(0 if success else 1)

        if cmd == "check":
            success = cmd_check(arg)
            sys.exit(0 if success else 1)

        if cmd == "lock":
            check_only = "--check" in argv
            success = cmd_lock(arg or ".", check_only=check_only)
            sys.exit(0 if success else 1)

        if cmd == "run":
            if "--update-snapshots" in argv:
                # Read by expect_snapshot() in the interpreter — lets
                # a mismatch intentionally become the new accepted
                # baseline instead of failing, the standard workflow
                # for snapshot testing once a change is verified as
                # correct rather than a regression.
                os.environ["NEKOVA_UPDATE_SNAPSHOTS"] = "1"
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
                                      strict_types=strict, debug_ai=args["debug_ai"],
                                      script_args=args["script_args"], why=args["why"],
                                      simple_errors=args["simple_errors"],
                                      record_ai=args["record_ai"], replay_ai=args["replay_ai"])
            else:
                runner = NEKOVARunner(filepath=arg, debug=args["debug"],
                                      debug_ai=args["debug_ai"],
                                      script_args=args["script_args"], why=args["why"],
                                      simple_errors=args["simple_errors"],
                                      record_ai=args["record_ai"], replay_ai=args["replay_ai"])
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
                    "  Usage: nekova debug app.nk"
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
        
        if cmd == "explain":
            if not arg:
                print_error(
                    "Please provide a file to explain.\n"
                    "  Usage: nekova explain app.nk"
                )
                sys.exit(1)
            from nekova.cli.explain import cmd_explain
            use_ai = "--no-ai" not in argv
            success = cmd_explain(arg, use_ai=use_ai)
            sys.exit(0 if success else 1)

        if cmd == "learn":
            from nekova.cli.learn import cmd_learn
            cmd_learn()
            sys.exit(0)

        if cmd == "translate":
            if not arg:
                print_error(
                    "Please provide a Python file to translate.\n"
                    "  Usage: nekova translate script.py"
                )
                sys.exit(1)
            from nekova.cli.translate import cmd_translate
            success = cmd_translate(arg)
            sys.exit(0 if success else 1)

        if cmd == "classroom":
            from nekova.cli.classroom import cmd_classroom
            success = cmd_classroom(arg or ".")
            sys.exit(0 if success else 1)

        if cmd == "help":
            # Multi-word topics ("async task", "think as", "with
            # budget") need every positional arg after "help", not
            # just the first — args["arg"] only ever holds values[1].
            values = [a for a in argv if not a.startswith("--")]
            topic = " ".join(values[1:]) if len(values) > 1 else ""
            from nekova.cli.glossary import format_topic, format_topic_list
            if topic:
                print(format_topic(topic))
            else:
                print(format_topic_list())
            sys.exit(0)

        if cmd == "compile":
            if not arg:
                print_error(
                    "Please provide a file to compile.\n"
                    "  Usage: nekova compile app.nk"
                )
                sys.exit(1)
            from nekova.compiler.llvm_backend import LLVMCompiler
            compiler = LLVMCompiler()
            print_info(f"Compiling '{arg}'...")
            try:
                output = compiler.compile(arg)
                print_success(f"Compiled → {output}")
            except Exception as e:
                print_error(f"Compile error: {e}")
                sys.exit(1)
            sys.exit(0)

    # â”€â”€ Direct file execution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    if args["file"]:
        print_banner()
        runner    = NEKOVARunner(filepath=args["file"],
                               debug=args["debug"],
                               debug_ai=args["debug_ai"],
                               compile_mode=args["compile"],
                               script_args=args["script_args"], why=args["why"],
                               simple_errors=args["simple_errors"],
                               record_ai=args["record_ai"], replay_ai=args["replay_ai"])
        exit_code = runner.run()
        sys.exit(exit_code)

    # â”€â”€ Nothing matched â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print_error(
        "Unknown command. "
        "Run 'nekova --help' for usage."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()