# =============================================================
# NEKOVA Sandbox — SandboxResult
# Phase 19: Structured result from sandboxed execution
# =============================================================

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxResult:
    """
    The result of running code inside a NEKOVA sandbox.

    Attributes:
        output    — everything printed to stdout during execution
        error     — error message if execution failed, else None
        safe      — True if execution completed without violation
        duration  — wall-clock seconds the sandbox ran
        mode      — "strict" | "relaxed" | "custom"
        violations — list of blocked operations that were attempted
        return_value — the value of the last expression, if any
    """
    output:       str        = ""
    error:        str | None = None
    safe:         bool       = True
    duration:     float      = 0.0
    mode:         str        = "strict"
    violations:   list       = field(default_factory=list)
    return_value: Any        = None

    @property
    def ok(self) -> bool:
        """True if sandbox ran cleanly with no errors or violations."""
        return self.safe and self.error is None

    def __repr__(self):
        status = "✓ ok" if self.ok else "✗ failed"
        return (
            f"SandboxResult({status}, mode={self.mode!r}, "
            f"duration={self.duration:.3f}s, "
            f"output={self.output[:40]!r}{'...' if len(self.output) > 40 else ''})"
        )