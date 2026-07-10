# =============================================================
# NEKOVA Language — CLI Module
# =============================================================
# Handles all terminal output formatting.
# Kept separate so the interpreter never depends on colors.

import sys
from nekova.config import Color, NEKOVA_VERSION, NEKOVA_CODENAME


def print_banner():
    """
    Print the NEKOVA startup banner — unless --quiet/-q was passed.

    Previously this always printed unconditionally, with no way to
    suppress it, which meant every single CLI invocation was preceded
    by ~12 lines of ASCII logo even in scripts, CI, or piped output
    where only the command's actual output matters. Checking sys.argv
    directly here (rather than threading a `quiet` flag through every
    one of this function's several call sites in main.py) keeps the
    fix to one place.
    """
    if "--quiet" in sys.argv or "-q" in sys.argv:
        return
    art = (
        "  _   _ _____  _  ______  _    __ \n"
        " | \\ | | ____|| |/ / __ \\| |   \\ \\\n"
        " |  \\| |  _|  | ' / |  | | |    \\ \\\n"
        " | |\\  | |___ | . \\ |__| | |___ / /\n"
        " |_| \\_|_____||_|\\_\\____/|_____/_/ "
    )
    banner = (
        f"\n{Color.CYAN}{Color.BOLD}\n"
        f"{art}\n"
        f"{Color.RESET}\n"
        f"  {Color.DIM}AI-Native Programming Language{Color.RESET}\n"
        f"  {Color.DIM}Connected Forge · by SYNEKCOT Tech{Color.RESET}\n"
        f"  {Color.YELLOW}Version {NEKOVA_VERSION} · {NEKOVA_CODENAME}{Color.RESET}\n"
        f"  {Color.DIM}{'─' * 40}{Color.RESET}\n"
    )
    print(banner)


def print_success(message: str):
    print(f"{Color.GREEN}✓ {message}{Color.RESET}")


def print_error(message: str):
    print(f"{Color.RED}✗ {message}{Color.RESET}", file=sys.stderr)


def print_info(message: str):
    print(f"{Color.CYAN}→ {message}{Color.RESET}")


def print_warning(message: str):
    print(f"{Color.YELLOW}⚠ {message}{Color.RESET}")


def print_separator():
    print(f"{Color.DIM}{'─' * 50}{Color.RESET}")