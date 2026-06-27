# =============================================================
# NEKOVA Sandbox — SandboxEnvironment
# Phase 19: Restricted execution namespace
# =============================================================

from nekova.interpreter.environment import Environment
from nekova.interpreter.exceptions import NEKOVARuntimeError


class SandboxViolation(Exception):
    """Raised when sandboxed code attempts a blocked operation."""
    def __init__(self, operation: str, mode: str, message: str = ""):
        self.operation = operation
        self.mode = mode
        super().__init__(
            f"[sandbox:{mode}] '{operation}' is not permitted.\n"
            + (f"  {message}" if message else "")
        )


# Operations allowed per mode
STRICT_ALLOWLIST = {
    # Pure computation — always safe
    "show", "let", "if", "while", "for", "task", "return",
    "match", "pass", "assert", "yield",
    # Safe builtins
    "len", "str", "int", "float", "bool", "abs", "round",
    "min", "max", "sum", "range", "sorted", "reversed",
    "list", "dict", "type_of", "print",
    # Math
    "sqrt", "floor", "ceil", "pow", "log",
    # String methods (via method calls on values)
    "split", "join", "strip", "upper", "lower", "replace",
}

RELAXED_ALLOWLIST = STRICT_ALLOWLIST | {
    # Read-only file access
    "file_read", "file_exists",
    "read", "exists", "lines", "line_count", "head", "tail",
    # Date/time (read-only)
    "date_now", "date_today", "date_timestamp",
    "date_format", "date_day_of_week",
    "now", "today", "timestamp", "day_of_week",
    # JSON parsing (read)
    "parse",
}

# Operations always blocked regardless of mode
ALWAYS_BLOCKED = {
    # System access
    "__import__", "eval", "exec", "compile", "open",
    # Process control
    "os", "sys", "subprocess", "socket",
    # Dangerous builtins
    "globals", "locals", "vars", "dir", "getattr", "setattr",
    "delattr", "object", "__class__", "__bases__",
}

# Operations blocked in strict mode only
STRICT_BLOCKED = {
    # Database — file system side effect
    "connect",
    # AI calls — external network
    "think",
    # I/O — voice, image generation
    "speak", "listen", "imagine",
    # File write operations
    "write", "append", "delete", "write_json",
}


class SandboxEnvironment(Environment):
    """
    A restricted Environment that blocks access to dangerous operations.
    Tracks all violation attempts for the SandboxResult.
    """

    def __init__(self, parent: Environment, mode: str = "strict",
                 custom_allowlist: set | None = None):
        super().__init__(parent=parent)
        self.mode = mode
        self.violations: list = []

        if custom_allowlist is not None:
            self._allowlist = custom_allowlist
        elif mode == "strict":
            self._allowlist = STRICT_ALLOWLIST
        elif mode == "relaxed":
            self._allowlist = RELAXED_ALLOWLIST
        else:
            self._allowlist = STRICT_ALLOWLIST  # default safe

    def get(self, name: str):
        """Get a variable, blocking dangerous names."""
        if name in ALWAYS_BLOCKED:
            self._record_violation(name)
            raise NEKOVARuntimeError(
                f"[sandbox:{self.mode}] Access to '{name}' is blocked.\n"
                f"  This operation is not permitted in any sandbox mode."
            )
        if self.mode == "strict" and name in STRICT_BLOCKED:
            self._record_violation(name)
            raise NEKOVARuntimeError(
                f"[sandbox:{self.mode}] Access to '{name}' is blocked.\n"
                f"  Use relaxed mode to enable this operation."
            )
        return super().get(name)

    def set(self, name: str, value):
        """Set a variable — always allowed (it's the get that's restricted)."""
        super().set(name, value)

    def _record_violation(self, operation: str):
        """Record an attempted policy violation."""
        entry = {"operation": operation, "mode": self.mode}
        if entry not in self.violations:
            self.violations.append(entry)