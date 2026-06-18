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