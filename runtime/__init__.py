# =============================================================
# NEKOVA Runtime — Return Value Handling
# =============================================================
# When a task executes a "return" statement we need a way
# to stop execution immediately and pass the value back
# to the caller.
#
# Python doesn't let us "break out" of nested function calls
# easily — so we use a special exception for this.
# This is the same technique used by Python itself internally.
#
# Example:
#   task double(x):
#       return x * 2    ← raises ReturnSignal(4)
#
#   result = double(2)  ← catches ReturnSignal, gets 4


class ReturnSignal(Exception):
    """
    Raised when NEKOVA executes a return statement.
    Carries the return value up the call stack.
    """
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    """
    Raised when NEKOVA needs to break out of a loop.
    Reserved for future use in Phase 5+.
    """
    pass