# =============================================================
# NEKOVA Language — CLI Entry Point
# =============================================================
# This is the entry point registered in setup.cfg:
#   nekova = nekova_cli:main
#
# It sets up the path and environment, then delegates
# everything to main.py so all commands work identically
# whether you run "python main.py ..." or "nekova ...".

import sys
import io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import sys
import os


def main():
    """Main entry point for the 'nekova' shell command."""

    # Add NEKOVA installation directory to the Python path
    nekova_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, nekova_dir)

    # Load .env file so API keys are available before anything imports
    env_path = os.path.join(nekova_dir, ".env")
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
    # the user calls "nekova ..." or "python main.py ...".
    try:
        from main import main as _main
        _main()
    except ImportError as e:
        print(f"Error: NEKOVA installation incomplete: {e}")
        print("Try: pip install nekova-lang --upgrade")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
