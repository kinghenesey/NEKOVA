# =============================================================
# NEKOVA CLI — Lockfile  (Phase 26)
# =============================================================
# nekova.lock captures the exact resolved version of every package
# declared in a project's nekova.toml [dependencies] packages list,
# so `nekova lock --check` can later detect drift — e.g. if the
# NEKOVA toolchain itself bumps a bundled package's version between
# when the lockfile was committed and when CI runs, or when a
# teammate has an older/newer nekova-lang install than whoever
# committed the lockfile.
#
# NEKOVA's package registry is a curated, bundled set (see
# nekova/packages/__init__.py's BUILTIN_PACKAGES), not an externally
# versioned registry like npm/PyPI — there's no dependency
# *resolution* to do in the traditional sense, since each package
# name maps to exactly one version at any given time. The lockfile's
# value here is auditability: a committed, reproducible record of
# what versions a project was actually built and tested against,
# with an explicit way to check whether that's still true.

import os
import json
from datetime import datetime, timezone

from nekova.config import NEKOVA_VERSION
from nekova.packages import BUILTIN_PACKAGES

LOCKFILE_NAME = "nekova.lock"


def _read_declared_packages(project_dir: str) -> list:
    """Read [dependencies] packages from the project's nekova.toml."""
    from nekova.toml_loader import load_config
    cfg = load_config(project_dir)
    if cfg is None:
        return []
    return list(cfg.dependencies.packages)


def generate_lock_data(project_dir: str = ".") -> dict:
    """
    Resolve every declared dependency to its exact current version.
    "unresolved" carries any declared package name that isn't in the
    registry at all, so callers can warn about it rather than
    silently dropping it from the lockfile.
    """
    declared = _read_declared_packages(project_dir)
    resolved = {}
    unresolved = []
    for name in declared:
        key = name.strip().lower()
        if key in BUILTIN_PACKAGES:
            resolved[key] = BUILTIN_PACKAGES[key]["version"]
        else:
            unresolved.append(name)

    return {
        "lockfile_version": 1,
        "generated_by": f"nekova {NEKOVA_VERSION}",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "packages": resolved,
        "unresolved": unresolved,
    }


def write_lockfile(project_dir: str = ".") -> dict:
    """Generate and write nekova.lock. Returns the data written."""
    data = generate_lock_data(project_dir)
    path = os.path.join(project_dir, LOCKFILE_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return data


def read_lockfile(project_dir: str = "."):
    """Read the existing nekova.lock, or None if it doesn't exist."""
    path = os.path.join(project_dir, LOCKFILE_NAME)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_lockfile(project_dir: str = ".") -> tuple:
    """
    Compare the existing nekova.lock against what would be generated
    right now, without writing anything. Returns (in_sync, drift):
      - in_sync: True if nothing has changed since the lockfile was
        last generated.
      - drift: dict of package name -> (locked_version,
        current_version) for anything added, removed, or changed. If
        no lockfile exists at all, drift is {"_missing": <message>}.
    """
    existing = read_lockfile(project_dir)
    if existing is None:
        return False, {"_missing": "No nekova.lock found. Run `nekova lock` first."}

    fresh = generate_lock_data(project_dir)

    drift = {}
    locked_packages = existing.get("packages", {})
    fresh_packages = fresh["packages"]

    for name in sorted(set(locked_packages) | set(fresh_packages)):
        locked_v = locked_packages.get(name)
        fresh_v = fresh_packages.get(name)
        if locked_v != fresh_v:
            drift[name] = (locked_v, fresh_v)

    return (len(drift) == 0), drift