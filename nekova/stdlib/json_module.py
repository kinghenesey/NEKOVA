# =============================================================
# NEKOVA Standard Library — JSON Module (Phase 8)
# =============================================================
# Usage in NEKOVA:
#   use json
#   let text = json_encode({"name": "Emmanuel", "age": 25})
#   show text                        → '{"name": "Emmanuel", "age": 25}'
#   let data = json_decode(text)
#   show data["name"]                → Emmanuel
#   show json_pretty({"a": 1})       → pretty-printed JSON
#   show json_valid('{"ok": true}')  → true

import json as _json


def _encode(value, pretty: bool = False) -> str:
    """Encode a Python value to a JSON string."""
    if pretty:
        return _json.dumps(value, indent=2, ensure_ascii=False)
    return _json.dumps(value, ensure_ascii=False)


def _decode(text: str):
    """Decode a JSON string to a Python value."""
    try:
        return _json.loads(str(text))
    except _json.JSONDecodeError as e:
        raise RuntimeError(f"json_decode failed: {e}")


def _pretty(value) -> str:
    """Pretty-print a value as JSON with 2-space indentation."""
    return _json.dumps(value, indent=2, ensure_ascii=False)


def _valid(text: str) -> bool:
    """Return true if text is valid JSON."""
    try:
        _json.loads(str(text))
        return True
    except _json.JSONDecodeError:
        return False


def _get(data, key: str, default=None):
    """Safely get a key from a decoded JSON object."""
    if isinstance(data, dict):
        return data.get(str(key), default)
    return default


def _keys(data) -> list:
    """Return the keys of a JSON object."""
    if isinstance(data, dict):
        return list(data.keys())
    return []


def _values(data) -> list:
    """Return the values of a JSON object."""
    if isinstance(data, dict):
        return list(data.values())
    return []


def _merge(*dicts) -> dict:
    """Merge multiple JSON objects into one."""
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result


def load() -> dict:
    return {
        "json_encode": _encode,
        "json_decode": _decode,
        "json_pretty": _pretty,
        "json_valid":  _valid,
        "json_get":    _get,
        "json_keys":   _keys,
        "json_values": _values,
        "json_merge":  _merge,
    }