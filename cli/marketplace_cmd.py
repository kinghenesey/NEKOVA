# =============================================================
# NEKOVA CLI — Marketplace Commands
# =============================================================
# Handles all marketplace commands:
#   python main.py marketplace
#   python main.py marketplace search <query>
#   python main.py marketplace install <name>
#   python main.py marketplace uninstall <name>
#   python main.py marketplace info <name>
#   python main.py marketplace featured
#   python main.py marketplace publish

from config import Color
from cli import print_error, print_info


def cmd_marketplace(subcommand: str = "",
                    arg: str = "") -> bool:
    """Handle all marketplace commands."""

    from marketplace import Marketplace
    mp = Marketplace()

    # No subcommand — browse all
    if not subcommand or subcommand == "browse":
        mp.browse()
        return True

    if subcommand == "search":
        if not arg:
            print_error(
                "Please provide a search term.\n"
                "  Usage: python main.py "
                "marketplace search charts"
            )
            return False
        mp.search_packages(arg)
        return True

    if subcommand == "install":
        if not arg:
            print_error(
                "Please provide a package name.\n"
                "  Usage: python main.py "
                "marketplace install aion-charts-pro"
            )
            return False
        return mp.install(arg)

    if subcommand == "uninstall":
        if not arg:
            print_error(
                "Please provide a package name.\n"
                "  Usage: python main.py "
                "marketplace uninstall aion-charts-pro"
            )
            return False
        return mp.uninstall(arg)

    if subcommand == "info":
        if not arg:
            print_error(
                "Please provide a package name.\n"
                "  Usage: python main.py "
                "marketplace info aion-charts-pro"
            )
            return False
        mp.info(arg)
        return True

    if subcommand == "featured":
        mp.featured()
        return True

    if subcommand == "publish":
        mp.publish(arg)
        return True

    print_error(
        f"Unknown marketplace command '{subcommand}'.\n"
        f"  Commands: browse, search, install, "
        f"uninstall, info, featured, publish"
    )
    return False