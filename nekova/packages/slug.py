# NEKOVA Package — slug
import re, html

def load() -> dict:
    return {
        "slugify":          _slugify,
        "truncate":         _truncate,
        "word_count":       _word_count,
        "capitalize_words": _capitalize_words,
        "strip_html":       _strip_html,
    }

def _slugify(text: str, separator: str = "-") -> str:
    """Convert text to a URL-friendly slug."""
    t = str(text).lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", str(separator), t)
    t = re.sub(r"^-+|-+$", "", t)
    return t

def _truncate(text: str, max_len: int = 100,
              suffix: str = "...") -> str:
    t = str(text)
    n = int(max_len)
    if len(t) <= n:
        return t
    return t[:n - len(suffix)].rstrip() + suffix

def _word_count(text: str) -> int:
    return len(str(text).split())

def _capitalize_words(text: str) -> str:
    return " ".join(w.capitalize() for w in str(text).split())

def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", str(text))
    return html.unescape(clean).strip()
