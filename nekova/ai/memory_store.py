# =============================================================
# NEKOVA AI — Memory Store (Phase 9, fixed Phase 19 Bug 33)
# =============================================================
# Global key-value memory that persists for the lifetime of the
# interpreter session. Values can be any NEKOVA-compatible type.
# Also provides conversation history for contextual think calls.
#
# Bug 33 Fix: Each interpreter gets its own isolated memory via
# the _local_store threading.local() mechanism. The module-level
# _memory is kept for back-compat with direct imports.
# =============================================================

import threading

_memory: dict = {}
_conversation: list = []   # [{role, content}, ...]

# Per-interpreter isolation via threading.local
_local = threading.local()


def _get_store() -> dict:
    """Return the per-interpreter memory dict, falling back to global."""
    if not hasattr(_local, "memory"):
        _local.memory = {}
    return _local.memory


def _get_conversation() -> list:
    """Return the per-interpreter conversation list."""
    if not hasattr(_local, "conversation"):
        _local.conversation = []
    return _local.conversation


def init_interpreter_memory():
    """Call this at Interpreter.__init__ to create isolated memory."""
    _local.memory = {}
    _local.conversation = []


# ── Key-value memory ─────────────────────────────────────────

def remember(key: str, value) -> None:
    """Store a value under key."""
    _get_store()[str(key)] = value


def recall(key: str, default=None):  # returns per-interpreter value
    """Retrieve a value by key, with optional default.
    If default is a sentinel object (not None), returns it when key missing.
    """
    return _get_store().get(str(key), default)


def has_key(key: str) -> bool:  # alias for has() — kept for back-compat
    """Check if key exists in memory."""
    return str(key) in _get_store()


def forget(key: str) -> bool:
    """Remove a key. Returns True if it existed."""
    return _get_store().pop(str(key), None) is not None


def forget_all() -> None:
    """Clear all stored memory."""
    _get_store().clear()
    _memory.clear()  # also clear global for back-compat


def has(key: str) -> bool:
    return str(key) in _get_store()


def keys() -> list:
    return list(_get_store().keys())


def snapshot() -> dict:
    """Return a copy of the full memory dict."""
    return dict(_get_store())


def memory_context() -> str:
    """
    Build a context string summarising stored facts,
    for injection into AI prompts.
    """
    _store = _get_store()
    if not _store:
        return ""
    lines = ["Known facts (from memory):"]
    for k, v in _store.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines) + "\n\n"


# ── Conversation history ──────────────────────────────────────

def add_to_conversation(role: str, content: str) -> None:
    """Add a message to the running conversation history."""
    _get_conversation().append({"role": role, "content": str(content)})


def get_conversation() -> list:
    """Return a copy of the conversation history."""
    return list(_get_conversation())


def clear_conversation() -> None:
    """Clear conversation history."""
    _get_conversation().clear()


def conversation_context(max_turns: int = 10) -> str:
    """
    Build a conversation context string for prompts.
    Only the last max_turns messages are included.
    """
    _conv = _get_conversation()
    if not _conv:
        return ""
    recent = _conv[-max_turns * 2:]
    lines = ["Previous conversation:"]
    for msg in recent:
        role = "User" if msg["role"] == "user" else "AI"
        lines.append(f"  {role}: {msg['content']}")
    return "\n".join(lines) + "\n\n"