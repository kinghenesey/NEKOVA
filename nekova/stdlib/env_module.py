# =============================================================
# NEKOVA Standard Library — Env Module (Phase 8)
# =============================================================
# Usage in NEKOVA:
#   use env
#   let port = env_get("PORT", "8080")
#   env_set("APP_NAME", "NEKOVA")
#   show env_has("HOME")              → true
#   let all = env_all()               → dict of all env vars
#   env_load(".env")                  → load a .env file

import os as _os


def _get(key: str, default: str = "") -> str:
    """Get an environment variable, with optional default."""
    return _os.environ.get(str(key), str(default))


def _set(key: str, value: str) -> None:
    """Set an environment variable for the current process."""
    _os.environ[str(key)] = str(value)


def _has(key: str) -> bool:
    """Return true if the environment variable exists."""
    return str(key) in _os.environ


def _delete(key: str) -> None:
    """Remove an environment variable."""
    _os.environ.pop(str(key), None)


def _all() -> dict:
    """
    Return a filtered view of environment variables.
    Sensitive keys (API keys, passwords, tokens, secrets) are
    redacted to protect credentials from being exposed to NEKOVA scripts.
    Use env_get() to access a specific variable by name.
    """
    _SENSITIVE_PATTERNS = (
        "key", "secret", "password", "passwd", "token",
        "auth", "credential", "private", "api_key",
        "access_key", "client_secret", "signing",
    )
    safe = {}
    for k, v in _os.environ.items():
        k_lower = k.lower()
        if any(pat in k_lower for pat in _SENSITIVE_PATTERNS):
            safe[k] = "[REDACTED]"
        else:
            safe[k] = v
    return safe


def _load(filepath: str = ".env") -> dict:
    """
    Load a .env file into the environment.
    Supports KEY=VALUE and KEY="VALUE" formats.
    Ignores comment lines (# ...) and blank lines.
    Returns dict of variables that were loaded.
    """
    loaded = {}
    path = str(filepath)

    if not _os.path.exists(path):
        return loaded

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip()

            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            _os.environ[key] = value
            loaded[key] = value

    return loaded


def _require(key: str) -> str:
    """
    Get a required environment variable.
    Raises RuntimeError if it doesn't exist.
    """
    val = _os.environ.get(str(key))
    if val is None:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set.\n"
            f"  Set it with: env_set(\"{key}\", \"your_value\")\n"
            f"  Or add it to your .env file."
        )
    return val


def load() -> dict:
    return {
        "env_get":     _get,
        "env_set":     _set,
        "env_has":     _has,
        "env_delete":  _delete,
        "env_all":     _all,
        "env_load":    _load,
        "env_require": _require,
    }