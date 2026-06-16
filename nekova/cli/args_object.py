# =============================================================
# NEKOVA — ArgsObject
# =============================================================
class ArgsObject:
    """CLI script args passed via --key value, accessible as args.key"""

    def __init__(self, data: dict):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, key: str):
        data = object.__getattribute__(self, "_data")
        if key in data:
            return data[key]
        raise AttributeError(
            f"No argument '--{key}' was passed to this script.\n"
            f"  Usage:  nekova run script.nk --{key} value"
        )

    def __setattr__(self, key, value):
        raise AttributeError("args is read-only.")

    def has(self, key: str) -> bool:
        return key in object.__getattribute__(self, "_data")

    def get(self, key: str, default=None):
        return object.__getattribute__(self, "_data").get(key, default)

    def keys(self) -> list:
        return list(object.__getattribute__(self, "_data").keys())

    def all(self) -> dict:
        return dict(object.__getattribute__(self, "_data"))

    def __repr__(self):
        data = object.__getattribute__(self, "_data")
        pairs = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"Args({pairs})" if pairs else "Args()"

    def __contains__(self, key):
        return key in object.__getattribute__(self, "_data")