# =============================================================
# NEKOVA Compiler — Package Init
# =============================================================
# Makes the compiler importable from anywhere like:
#   from compiler import Compiler, VirtualMachine

from nekova.compiler.compiler import Compiler, CompileError
from nekova.compiler.vm import VirtualMachine, VMError
from nekova.compiler.bytecode import OpCode, Instruction, CodeObject