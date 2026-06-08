# =============================================================
# NEKOVA Standard Library — Math Module
# =============================================================
# Usage in NEKOVA:
#   use math
#   show sqrt(16)      → 4.0
#   show pi            → 3.14159...
#   show floor(3.9)    → 3
#   show ceil(3.1)     → 4
#   show abs(-5)       → 5
#   show round(3.567)  → 4

import math


def load() -> dict:
    """
    Returns all math functions and constants
    to be loaded into the NEKOVA environment.
    """
    return {
        # Constants
        "pi":    math.pi,
        "e":     math.e,
        "inf":   math.inf,

        # Basic operations
        "sqrt":  math.sqrt,
        "abs":   abs,
        "round": round,
        "floor": math.floor,
        "ceil":  math.ceil,

        # Power and logarithms
        "pow":   math.pow,
        "log":   math.log,
        "log10": math.log10,

        # Trigonometry
        "sin":   math.sin,
        "cos":   math.cos,
        "tan":   math.tan,

        # Utility
        "min":   min,
        "max":   max,
        "sum":   sum,
    }