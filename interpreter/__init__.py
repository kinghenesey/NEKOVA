# =============================================================
# NEKOVA Interpreter — Package Init
# =============================================================
# Makes the interpreter importable from anywhere like:
#   from interpreter import Interpreter

from interpreter.interpreter import Interpreter, RuntimeError
from interpreter.environment import Environment