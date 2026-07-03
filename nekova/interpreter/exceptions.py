# =============================================================
# NEKOVA Interpreter — Exception Types
# =============================================================
# Kept in a separate module so interpreter, async_interpreter,
# and class_interpreter can all import from here without
# creating circular dependencies.


class NEKOVARuntimeError(Exception):
    """Raised when something goes wrong during NEKOVA execution."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class NEKOVAImportError(Exception):
    """Raised when a module cannot be found."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class NEKOVANameError(Exception):
    """Raised when a variable is not found."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")

class NEKOVARaiseError(Exception):
    """Raised by the 'raise' statement in NEKOVA code."""
    def __init__(self, value, line: int = 0):
        self.value = value
        self.line  = line
        super().__init__(str(value))


class NEKOVAAssertionError(Exception):
    """Raised by a failing 'assert' statement."""
    def __init__(self, message: str = "Assertion failed", line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class NEKOVARecursionError(Exception):
    """
    Raised when NEKOVA's own call-depth counter (tracked in
    Interpreter._call_task) exceeds the configured safety limit.

    Deliberately separate from Python's built-in RecursionError:
    it fires at a depth NEKOVA itself chose and counted, so the
    reported number is the true NEKOVA-level call depth reached —
    not a guess derived from Python's interpreter stack. It does
    NOT claim the recursion is infinite; it only reports that the
    safety limit was hit, since NEKOVA cannot know whether a
    missing base case or a legitimately deep computation caused it.
    """
    def __init__(self, task_name: str, depth: int, line: int = 0):
        self.task_name = task_name
        self.depth = depth
        self.line = line
        super().__init__(
            f"\n  Task '{task_name}' exceeded the maximum call depth "
            f"({depth} nested calls)."
        )

class _ExpectFailed(Exception):
    """Internal signal raised by a failing expect statement."""
    pass

class _YieldSignal(Exception):
    """Internal signal raised by yield statement in generator tasks."""
    def __init__(self, value):
        self.value = value
        super().__init__()