# =============================================================
# NEKOVA Standard Library — Text Module
# =============================================================
# Usage in NEKOVA:
#   use text
#   show upper("hello")        → HELLO
#   show lower("NEKOVA")         → nekova
#   show length("hello")       → 5
#   show replace("hi", "hi", "hello")  → hello
#   show contains("NEKOVA", "AI")        → true
#   show trim("  hello  ")     → hello


def load() -> dict:
    """
    Returns all text functions to be loaded
    into the NEKOVA environment.
    """
    return {
        # Case
        "upper":    lambda s: str(s).upper(),
        "lower":    lambda s: str(s).lower(),
        "title":    lambda s: str(s).title(),

        # Whitespace
        "trim":     lambda s: str(s).strip(),
        "trim_left":  lambda s: str(s).lstrip(),
        "trim_right": lambda s: str(s).rstrip(),

        # Search
        "contains": lambda s, sub: sub in str(s),
        "starts_with": lambda s, sub: str(s).startswith(sub),
        "ends_with":   lambda s, sub: str(s).endswith(sub),
        "find":     lambda s, sub: str(s).find(sub),

        # Modification
        "replace":  lambda s, old, new: str(s).replace(old, new),
        "repeat_text": lambda s, n: str(s) * int(n),
        "reverse":  lambda s: str(s)[::-1],

        # Splitting and joining
        "split":    lambda s, sep=" ": str(s).split(sep),
        "join":     lambda sep, items: str(sep).join(
                        [str(i) for i in items]),

        # Info
        "length":   lambda s: len(str(s)),
        "is_number": lambda s: str(s).replace(
                        ".", "", 1).lstrip("-").isdigit(),
        "is_empty": lambda s: str(s).strip() == "",
    }