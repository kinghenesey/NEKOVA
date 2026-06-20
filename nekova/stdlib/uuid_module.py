# =============================================================
# NEKOVA Standard Library — UUID Module (Phase 8)
# =============================================================
# Usage in NEKOVA:
#   use uuid
#   let id = uuid()            → "f47ac10b-58cc-4372-a567-0e02b2c3d479"
#   let id4 = uuid4()          → UUID v4 (random)
#   let id5 = uuid5("name")    → UUID v5 (name-based, SHA-1)
#   show uuid_valid(id)        → true
#   let short = uuid_short()   → "f47ac10b"  (first 8 chars)
#   let nano  = uuid_nano()    → 12-char compact ID

import uuid as _uuid


def _uuid4() -> str:
    """Generate a random UUID v4."""
    return str(_uuid.uuid4())


def _uuid5(name: str, namespace: str = "dns") -> str:
    """
    Generate a deterministic UUID v5 from a name.
    namespace: 'dns', 'url', 'oid', 'x500'
    """
    ns_map = {
        "dns":  _uuid.NAMESPACE_DNS,
        "url":  _uuid.NAMESPACE_URL,
        "oid":  _uuid.NAMESPACE_OID,
        "x500": _uuid.NAMESPACE_X500,
    }
    ns = ns_map.get(str(namespace).lower(), _uuid.NAMESPACE_DNS)
    return str(_uuid.uuid5(ns, str(name)))


def _uuid_valid(value: str) -> bool:
    """Return true if the string is a valid UUID."""
    try:
        _uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _uuid_short(length: int = 8) -> str:
    """Return a shortened UUID (first N chars, no hyphens)."""
    raw = str(_uuid.uuid4()).replace("-", "")
    return raw[:int(length)]


def _uuid_nano() -> str:
    """Return a compact 12-character alphanumeric ID."""
    import hashlib
    raw = str(_uuid.uuid4()).replace("-", "")
    return raw[:12]


def _uuid_parts(value: str) -> dict:
    """
    Parse a UUID string into its components.
    Returns dict with time_low, time_mid, time_hi, version fields.
    """
    try:
        u = _uuid.UUID(str(value))
        return {
            "version":  u.version,
            "hex":      u.hex,
            "int":      u.int,
            "variant":  str(u.variant),
        }
    except ValueError:
        raise RuntimeError(f"Invalid UUID: '{value}'")


def load() -> dict:
    return {
        # Primary generators
        "uuid":        _uuid4,    # uuid()  → v4 random
        "uuid4":       _uuid4,    # explicit v4
        "uuid5":       _uuid5,    # uuid5("my-resource")

        # Utilities
        "uuid_valid":  _uuid_valid,
        "uuid_short":  _uuid_short,
        "uuid_nano":   _uuid_nano,
        "uuid_parts":  _uuid_parts,
    }