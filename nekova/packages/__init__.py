# =============================================================
# NEKOVA Package Manager — Package Registry
# =============================================================
# This module manages all installed NEKOVA packages.
# Packages are stored in the packages/ folder and made
# available via "use <package>" in NEKOVA code.

import os
import json

# Path to the packages directory — always points to root packages/
# regardless of whether running from nekova/ package or root
_this_dir     = os.path.dirname(os.path.abspath(__file__))
_root_dir     = os.path.dirname(_this_dir) if os.path.basename(_this_dir) == 'packages' and 'nekova' in _this_dir else _this_dir
PACKAGES_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "packages") \
                if "nekova" in os.path.abspath(__file__) else _this_dir
REGISTRY_FILE = os.path.join(PACKAGES_DIR, "registry.json")


# ── Built-in package registry ─────────────────────────────────
# These are packages that come with NEKOVA out of the box.
# Future versions will download from a remote registry.

BUILTIN_PACKAGES = {
    "charts": {
        "name":        "charts",
        "version":     "1.0.0",
        "description": "Simple ASCII charts and graphs",
        "author":      "NEKOVA Core Team",
        "functions":   ["bar_chart", "line_chart", "pie_chart"],
    },
    "auth": {
        "name":        "auth",
        "version":     "1.0.0",
        "description": "Basic authentication utilities",
        "author":      "NEKOVA Core Team",
        "functions":   ["hash_password", "check_password",
                        "generate_token"],
    },
    "validation": {
        "name":        "validation",
        "version":     "1.0.0",
        "description": "Input validation helpers",
        "author":      "NEKOVA Core Team",
        "functions":   ["is_email", "is_phone", "is_url",
                        "is_strong_password"],
    },
    "colors": {
        "name":        "colors",
        "version":     "1.0.0",
        "description": "Terminal color and styling utilities",
        "author":      "NEKOVA Core Team",
        "functions":   ["red", "green", "blue", "yellow",
                        "bold", "dim"],
    },
    "random": {
        "name":        "random",
        "version":     "1.0.0",
        "description": "Random number and value generation",
        "author":      "NEKOVA Core Team",
        "functions":   ["random_int", "random_float",
                        "random_choice", "shuffle"],
    },
}


def load_registry() -> dict:
    """Load the local installed packages registry."""
    if not os.path.exists(REGISTRY_FILE):
        return {}
    try:
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_registry(registry: dict):
    """Save the local installed packages registry."""
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def is_installed(name: str) -> bool:
    """Check if a package is installed — checks registry AND file on disk."""
    registry = load_registry()
    if name in registry:
        return True
    # Also check if the .py file physically exists (handles migration edge cases)
    pkg_file = os.path.join(PACKAGES_DIR, f"{name}.py")
    return os.path.exists(pkg_file)


def get_installed() -> dict:
    """Return all installed packages."""
    return load_registry()


def get_available() -> dict:
    """Return all available packages."""
    return BUILTIN_PACKAGES
