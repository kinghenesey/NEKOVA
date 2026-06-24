# nekova/config/toml_loader.py
# ─────────────────────────────────────────────────────────────────────────────
# Loads and validates a nekova.toml project config file.
# Uses Python's built-in `tomllib` (3.11+) or `tomli` fallback (3.10).
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ── tomllib compat (built-in on 3.11+, pip install tomli on 3.10) ────────────
try:
    import tomllib                          # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib             # type: ignore  # pip install tomli
    except ImportError:
        tomllib = None                      # handled gracefully below


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ProjectConfig:
    name:        str  = "unnamed"
    version:     str  = "0.1.0"
    author:      str  = ""
    description: str  = ""
    entry:       str  = "main.nk"


@dataclass
class AIConfig:
    model:         str   = "claude"
    api_key:       str   = ""
    model_version: str   = ""
    think_timeout: float = 30.0  # seconds; set to 0 to disable


@dataclass
class DependenciesConfig:
    packages: list = field(default_factory=list)


@dataclass
class RunConfig:
    strict_types: bool = False
    show_imports: bool = False
    debug:        bool = False


@dataclass
class NekovaConfig:
    """
    Full parsed contents of a nekova.toml file.
    All sections are optional — missing ones get safe defaults.
    """
    project:      ProjectConfig      = field(default_factory=ProjectConfig)
    ai:           AIConfig           = field(default_factory=AIConfig)
    dependencies: DependenciesConfig = field(default_factory=DependenciesConfig)
    run:          RunConfig          = field(default_factory=RunConfig)

    # The directory this config was loaded from
    root_dir: str = ""

    @property
    def entry_path(self) -> str:
        """Absolute path to the entry .nk file."""
        return os.path.join(self.root_dir, self.project.entry)


# ── Loader ───────────────────────────────────────────────────────────────────

class ConfigError(Exception):
    """Raised when nekova.toml is malformed or missing required fields."""


def load_config(start_dir: str = None) -> Optional[NekovaConfig]:
    """
    Search for nekova.toml starting from *start_dir* (default: cwd),
    walking up parent directories until found or filesystem root reached.

    Returns a NekovaConfig on success, or None if no nekova.toml exists.
    Raises ConfigError if the file exists but is malformed.
    """
    search_dir = os.path.abspath(start_dir or os.getcwd())

    toml_path = _find_config(search_dir)
    if toml_path is None:
        return None

    return parse_config(toml_path)


def _find_config(start: str) -> Optional[str]:
    """Walk up the directory tree looking for nekova.toml."""
    current = start
    while True:
        candidate = os.path.join(current, "nekova.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def parse_config(toml_path: str) -> NekovaConfig:
    """
    Parse a nekova.toml file at *toml_path*.
    Raises ConfigError on parse or validation failure.
    """
    if tomllib is None:
        raise ConfigError(
            "Cannot read nekova.toml — no TOML parser available.\n"
            "  On Python 3.10, install one:  pip install tomli\n"
            "  Python 3.11+ includes tomllib automatically."
        )

    # BOM fix for files written on Windows
    with open(toml_path, "rb") as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]

    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except Exception as e:
        raise ConfigError(
            f"nekova.toml has a syntax error:\n  {e}\n"
            f"  File: {toml_path}"
        )

    root_dir = os.path.dirname(os.path.abspath(toml_path))
    return _build_config(data, root_dir, toml_path)


def _build_config(data: dict, root_dir: str, toml_path: str) -> NekovaConfig:
    """Validate and assemble a NekovaConfig from raw parsed TOML data."""

    # ── [project] ────────────────────────────────────────────
    p = data.get("project", {})
    project = ProjectConfig(
        name        = _str(p, "name",        "unnamed"),
        version     = _str(p, "version",     "0.1.0"),
        author      = _str(p, "author",      ""),
        description = _str(p, "description", ""),
        entry       = _str(p, "entry",       "main.nk"),
    )

    # Validate entry file exists (warn, don't error — file may not be created yet)
    entry_path = os.path.join(root_dir, project.entry)
    if not os.path.isfile(entry_path):
        import warnings
        warnings.warn(
            f"nekova.toml: entry file '{project.entry}' not found at '{entry_path}'.\n"
            f"  Create it or update [project] entry in nekova.toml.",
            stacklevel=3,
        )

    # ── [ai] ─────────────────────────────────────────────────
    a = data.get("ai", {})
    ai_key = _str(a, "api_key", "")

    # If api_key is blank, fall back to environment variables
    if not ai_key:
        ai_key = (
            os.environ.get("ANTHROPIC_API_KEY") or
            os.environ.get("GEMINI_API_KEY") or
            os.environ.get("OPENAI_API_KEY") or
            ""
        )

    ai = AIConfig(
        model         = _str(a, "model",         "claude"),
        api_key       = ai_key,
        model_version = _str(a, "model_version", ""),
        think_timeout = float(a.get("think_timeout", 30.0)),
    )

    _validate_model(ai.model, toml_path)

    # ── [dependencies] ────────────────────────────────────────
    d = data.get("dependencies", {})
    packages = d.get("packages", [])
    if not isinstance(packages, list):
        raise ConfigError(
            f"nekova.toml [dependencies] packages must be a list.\n"
            f"  Got: {type(packages).__name__}"
        )
    dependencies = DependenciesConfig(packages=packages)

    # ── [run] ─────────────────────────────────────────────────
    r = data.get("run", {})
    run = RunConfig(
        strict_types = _bool(r, "strict_types", False),
        show_imports = _bool(r, "show_imports", False),
        debug        = _bool(r, "debug",        False),
    )

    return NekovaConfig(
        project      = project,
        ai           = ai,
        dependencies = dependencies,
        run          = run,
        root_dir     = root_dir,
    )


# ── Validation helpers ────────────────────────────────────────────────────────

VALID_MODELS = {"claude", "gemini", "openai", "mock"}

def _validate_model(model: str, toml_path: str):
    if model not in VALID_MODELS:
        raise ConfigError(
            f"nekova.toml [ai] model '{model}' is not recognised.\n"
            f"  Valid options: {', '.join(sorted(VALID_MODELS))}\n"
            f"  File: {toml_path}"
        )

def _str(d: dict, key: str, default: str) -> str:
    val = d.get(key, default)
    if not isinstance(val, str):
        raise ConfigError(
            f"nekova.toml: '{key}' must be a string, got {type(val).__name__}."
        )
    return val

def _bool(d: dict, key: str, default: bool) -> bool:
    val = d.get(key, default)
    if not isinstance(val, bool):
        raise ConfigError(
            f"nekova.toml: '{key}' must be true or false, got {type(val).__name__}."
        )
    return val