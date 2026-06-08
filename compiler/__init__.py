# =============================================================
# NEKOVA Compiler — Package Init
# =============================================================
# Makes the compiler importable from anywhere like:
#   from compiler import Compiler, VirtualMachine

from compiler.compiler import Compiler, CompileError
from compiler.vm import VirtualMachine, VMError
from compiler.bytecode import OpCode, Instruction, CodeObject