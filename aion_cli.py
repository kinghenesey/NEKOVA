
# =============================================================
# AION Language — CLI Entry Point
# =============================================================
# This is the entry point registered in setup.cfg:
#   aion = aion_cli:main
#
# It sets up the path and environment, then delegates
# everything to main.py so all commands work identically
# whether you run "python main.py ..." or "aion ...".

import sys
import os


def main():
    """Main entry point for the 'aion' shell command."""

    # Add AION installation directory to the Python path
    aion_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, aion_dir)

    # Load .env file so API keys are available before anything imports
    env_path = os.path.join(aion_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    # Delegate everything to main.py's main() function.
    # This means every command (run, repl, test, ide, marketplace,
    # deploy, format, debug, etc.) works exactly the same whether
    # the user calls "aion ..." or "python main.py ...".
    try:
        from main import main as _main
        _main()
    except ImportError as e:
        print(f"Error: AION installation incomplete: {e}")
        print("Try: pip install aion-lang --upgrade")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()