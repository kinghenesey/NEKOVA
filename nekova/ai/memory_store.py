# =============================================================
# NEKOVA AI — Memory Store (Phase 9)
# =============================================================
# Global key-value memory that persists for the lifetime of the
# interpreter session. Values can be any NEKOVA-compatible type.
# Also provides conversation history for contextual think calls.
# =============================================================

_memory: dict = {}
_conversation: list = []   # [{role, content}, ...]


# ── Key-value memory ─────────────────────────────────────────

def remember(key: str, value) -> None:
    """Store a value under key."""
    _memory[str(key)] = value


def recall(key: str, default=None):
    """Retrieve a value by key, with optional default.
    If default is a sentinel object (not None), returns it when key missing.
    """
    return _memory.get(str(key), default)


def has_key(key: str) -> bool:
    """Check if key exists in memory."""
    return str(key) in _memory


def forget(key: str) -> bool:
    """Remove a key. Returns True if it existed."""
    return _memory.pop(str(key), None) is not None


def forget_all() -> None:
    """Clear all stored memory."""
    _memory.clear()


def has(key: str) -> bool:
    return str(key) in _memory


def keys() -> list:
    return list(_memory.keys())


def snapshot() -> dict:
    """Return a copy of the full memory dict."""
    return dict(_memory)


def memory_context() -> str:
    """
    Build a context string summarising stored facts,
    for injection into AI prompts.
    """
    if not _memory:
        return ""
    lines = ["Known facts (from memory):"]
    for k, v in _memory.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines) + "\n\n"


# ── Conversation history ──────────────────────────────────────

def add_to_conversation(role: str, content: str) -> None:
    """Add a message to the running conversation history."""
    _conversation.append({"role": role, "content": str(content)})


def get_conversation() -> list:
    """Return a copy of the conversation history."""
    return list(_conversation)


def clear_conversation() -> None:
    """Clear conversation history."""
    _conversation.clear()


def conversation_context(max_turns: int = 10) -> str:
    """
    Build a conversation context string for prompts.
    Only the last max_turns messages are included.
    """
    if not _conversation:
        return ""
    recent = _conversation[-max_turns * 2:]
    lines = ["Previous conversation:"]
    for msg in recent:
        role = "User" if msg["role"] == "user" else "AI"
        lines.append(f"  {role}: {msg['content']}")
    return "\n".join(lines) + "\n\n"