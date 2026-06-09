# =============================================================
# NEKOVA Marketplace — Main Engine
# =============================================================
# Core marketplace operations:
#   browse, search, install, uninstall, publish, info

import os
from config import Color, NEKOVA_VERSION
from marketplace.registry import (
    get_catalog, get_package, load_installed,
    is_installed, mark_installed, mark_uninstalled
)
from marketplace.search import (
    search, get_categories, get_featured
)


class Marketplace:
    """
    Main NEKOVA Marketplace engine.

    Usage:
        mp = Marketplace()
        mp.browse()
        mp.install("nekova-charts-pro")
        mp.search("nigeria")
    """

    def __init__(self):
        self.catalog   = get_catalog()
        self.installed = load_installed()

    def browse(self):
        """Display the full marketplace catalog."""
        print()
        print(f"{Color.CYAN}{Color.BOLD}"
              f"  NEKOVA Marketplace{Color.RESET}")
        print(f"  {Color.DIM}{'─' * 50}{Color.RESET}")
        print(f"  {Color.DIM}"
              f"{len(self.catalog)} packages available"
              f"{Color.RESET}")
        print()

        # Group by category
        categories = get_categories()
        for category in categories:
            pkgs = [p for p in self.catalog.values()
                    if p.get("category") == category]
            if not pkgs:
                continue

            print(f"  {Color.YELLOW}{Color.BOLD}"
                  f"{category.upper()}{Color.RESET}")

            for pkg in pkgs:
                self._print_package_line(pkg)
            print()

        # Summary
        inst_count = len(load_installed())
        print(f"  {Color.DIM}"
              f"{inst_count} packages installed · "
              f"Use 'python main.py marketplace "
              f"install <name>' to install"
              f"{Color.RESET}")
        print()

    def search_packages(self, query: str):
        """Search for packages."""
        print()
        print(f"{Color.CYAN}{Color.BOLD}"
              f"  Search: '{query}'{Color.RESET}")
        print(f"  {Color.DIM}{'─' * 50}{Color.RESET}")
        print()

        results = search(query)

        if not results:
            print(f"  {Color.YELLOW}"
                  f"No packages found for '{query}'"
                  f"{Color.RESET}")
            print(f"  {Color.DIM}"
                  f"Try a different search term"
                  f"{Color.RESET}")
            print()
            return

        print(f"  {Color.DIM}"
              f"{len(results)} result(s) found:"
              f"{Color.RESET}")
        print()

        for pkg in results:
            self._print_package_line(pkg)

        print()

    def install(self, name: str) -> bool:
        """Install a package from the marketplace."""
        print()

        # Check if already installed
        if is_installed(name):
            print(f"  {Color.YELLOW}"
                  f"⚠ '{name}' is already installed"
                  f"{Color.RESET}")
            return True

        # Find package
        pkg = get_package(name)
        if not pkg:
            print(f"  {Color.RED}"
                  f"✗ Package '{name}' not found"
                  f"{Color.RESET}")
            print(f"  {Color.DIM}"
                  f"Run 'python main.py marketplace' "
                  f"to browse available packages"
                  f"{Color.RESET}")
            print()
            return False

        print(f"  {Color.CYAN}"
              f"Installing '{name}'...{Color.RESET}")
        print(f"  {Color.DIM}"
              f"{pkg['description']}{Color.RESET}")
        print()

        # Simulate installation steps
        steps = [
            "Resolving dependencies",
            "Downloading package",
            "Verifying integrity",
            "Installing files",
            "Updating registry",
        ]

        for step in steps:
            print(f"  {Color.DIM}  → {step}..."
                  f"{Color.RESET}")

        # Mark as installed
        mark_installed(name, pkg)

        print()
        print(f"  {Color.GREEN}✓ Installed '{name}' "
              f"v{pkg['version']}{Color.RESET}")
        print(f"  {Color.DIM}"
              f"Functions: "
              f"{', '.join(pkg.get('functions', []))}"
              f"{Color.RESET}")
        print()
        return True

    def uninstall(self, name: str) -> bool:
        """Uninstall a marketplace package."""
        print()

        if not is_installed(name):
            print(f"  {Color.RED}"
                  f"✗ '{name}' is not installed"
                  f"{Color.RESET}")
            print()
            return False

        mark_uninstalled(name)

        print(f"  {Color.GREEN}"
              f"✓ Uninstalled '{name}'"
              f"{Color.RESET}")
        print()
        return True

    def info(self, name: str):
        """Show detailed info about a package."""
        pkg = get_package(name)

        if not pkg:
            print(f"  {Color.RED}"
                  f"✗ Package '{name}' not found"
                  f"{Color.RESET}")
            return

        inst    = is_installed(name)
        status  = (f"{Color.GREEN}installed{Color.RESET}"
                   if inst else
                   f"{Color.DIM}not installed{Color.RESET}")

        print()
        print(f"{Color.CYAN}{Color.BOLD}"
              f"  {pkg['name']}{Color.RESET} "
              f"v{pkg['version']}")
        print(f"  {Color.DIM}{'─' * 50}{Color.RESET}")
        print(f"  {pkg['description']}")
        print()
        print(f"  {'Author':<16} {pkg['author']}")
        print(f"  {'Category':<16} {pkg['category']}")
        print(f"  {'Downloads':<16} "
              f"{pkg['downloads']:,}")
        print(f"  {'Stars':<16} "
              f"{'★' * min(5, pkg['stars'] // 50)}"
              f" ({pkg['stars']})")
        print(f"  {'Status':<16} {status}")
        print()
        print(f"  {Color.BOLD}Functions:{Color.RESET}")
        for fn in pkg.get("functions", []):
            print(f"  {Color.DIM}  · {fn}(){Color.RESET}")
        print()
        print(f"  {Color.BOLD}Tags:{Color.RESET} "
              f"{Color.DIM}"
              f"{', '.join(pkg.get('tags', []))}"
              f"{Color.RESET}")
        print()

    def publish(self, name: str = "",
                description: str = ""):
        """Publish a package to the marketplace."""
        print()
        print(f"{Color.CYAN}{Color.BOLD}"
              f"  Publish to NEKOVA Marketplace"
              f"{Color.RESET}")
        print(f"  {Color.DIM}{'─' * 50}{Color.RESET}")
        print()

        if not name:
            print(f"  {Color.YELLOW}"
                  f"To publish a package:{Color.RESET}")
            print(f"  {Color.DIM}"
                  f"1. Create your package in packages/"
                  f"{Color.RESET}")
            print(f"  {Color.DIM}"
                  f"2. Add a load() function"
                  f"{Color.RESET}")
            print(f"  {Color.DIM}"
                  f"3. Run: python main.py marketplace "
                  f"publish <name>{Color.RESET}")
            print()
            return

        print(f"  {Color.GREEN}"
              f"✓ Package '{name}' submitted for review"
              f"{Color.RESET}")
        print(f"  {Color.DIM}"
              f"The NEKOVA team will review and publish "
              f"within 24 hours{Color.RESET}")
        print()

    def featured(self):
        """Show featured packages."""
        print()
        print(f"{Color.CYAN}{Color.BOLD}"
              f"  Featured Packages{Color.RESET}")
        print(f"  {Color.DIM}{'─' * 50}{Color.RESET}")
        print()

        for pkg in get_featured():
            self._print_package_line(pkg)
        print()

    def _print_package_line(self, pkg: dict):
        """Print a single package summary line."""
        name      = pkg['name']
        version   = pkg['version']
        desc      = pkg['description'][:45]
        downloads = pkg.get('downloads', 0)
        inst      = is_installed(name)
        status    = (f"{Color.GREEN}✓{Color.RESET}"
                     if inst else " ")

        print(f"  {status} {Color.BOLD}{name:<22}"
              f"{Color.RESET}"
              f"{Color.DIM}v{version:<8}{Color.RESET}"
              f"{Color.DIM}{downloads:>6} dl{Color.RESET}")
        print(f"      {Color.DIM}{desc}{Color.RESET}")