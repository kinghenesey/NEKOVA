# =============================================================
# NEKOVA Interpreter — Package Init
# =============================================================
# Makes the interpreter importable from anywhere like:
#   from interpreter import Interpreter

from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import (
    NEKOVARuntimeError, NEKOVAImportError, NEKOVANameError
)
from nekova.interpreter.environment import Environment