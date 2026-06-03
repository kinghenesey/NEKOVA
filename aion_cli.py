# =============================================================
# AION Language — CLI Entry Point
# =============================================================
import sys
import os


def main():
    """Main entry point for the 'aion' command."""

    # Add AION installation dir to path
    aion_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, aion_dir)

    # Load environment variables
    env_path = os.path.join(aion_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    # Handle --version
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        try:
            from config import AION_VERSION, AION_CODENAME
            print(f"AION v{AION_VERSION} · {AION_CODENAME}")
        except Exception:
            print("AION v1.1.0 · Genesis")
        return

    # Handle --help
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("""
AION Programming Language v1.1.0

Usage:
  aion <file.aion>          Run an AION file
  aion repl                 Start interactive shell
  aion <file.aion> --debug  Run with debug output

Examples:
  aion hello.aion
  aion repl
  aion examples/ai_demo.aion
        """)
        return

    # Build argv for the runner
    # Strip the 'aion' command itself — runner expects sys.argv[1:]
    sys.argv = [aion_dir + "/main.py"] + sys.argv[1:]

    try:
        from runner import AIONRunner
        from cli import print_banner

        command = sys.argv[1] if len(sys.argv) > 1 else ""

        if command == "repl":
            print_banner()
            from repl import REPL
            REPL().start()
            return

        # File execution
        filepath = sys.argv[1]
        if not filepath.endswith(".aion"):
            print(f"Error: '{filepath}' is not an .aion file")
            sys.exit(1)

        if not os.path.isfile(filepath):
            print(f"Error: File not found: '{filepath}'")
            sys.exit(1)

        print_banner()
        debug = "--debug" in sys.argv
        runner = AIONRunner(filepath=filepath, debug=debug)
        exit_code = runner.run()
        sys.exit(exit_code)

    except ImportError as e:
        print(f"Error: AION installation incomplete: {e}")
        print("Try: pip install aion-lang --upgrade")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()