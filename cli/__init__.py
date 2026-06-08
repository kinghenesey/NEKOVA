# =============================================================
# AION Language — CLI Module
# =============================================================
# Handles all terminal output formatting.
# Kept separate so the interpreter never depends on colors.

import sys
from config import Color, AION_VERSION, AION_CODENAME


def print_banner():
    """Print the AION startup banner."""
    art = (
        r"    ___    ____  ____  _   __"         "\n"
        r"   /   |  /  _/ / __ \/ | / /"        "\n"
        r"  / /| |  / /  / / / /  |/ / "        "\n"
        r" / ___ |_/ /  / /_/ / /|  /  "        "\n"
        r"/_/  |_/___/  \____/_/ |_/   "
    )
    banner = (
        f"\n{Color.CYAN}{Color.BOLD}\n"
        f"{art}\n"
        f"{Color.RESET}\n"
        f"  {Color.DIM}AI-Native Programming Language{Color.RESET}\n"
        f"  {Color.YELLOW}Version {AION_VERSION} · {AION_CODENAME}{Color.RESET}\n"
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