# =============================================================
# NEKOVA Compiler — Bytecode Instruction Set
# =============================================================
# Defines every operation the NEKOVA Virtual Machine can execute.
#
# Each instruction is called an "opcode" (operation code).
# The compiler converts AST nodes into sequences of opcodes.
# The VM then executes those opcodes one by one.
#
# This is exactly how Python, Java, and Lua work internally.

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, List


class OpCode(Enum):
    """Every possible instruction in the NEKOVA VM."""

    # ── Stack operations ──────────────────────────────────────
    LOAD_CONST   = auto()   # Push a constant onto the stack
    LOAD_NAME    = auto()   # Push a variable's value onto stack
    STORE_NAME   = auto()   # Pop stack → store in variable
    POP          = auto()   # Discard top of stack

    # ── Arithmetic ────────────────────────────────────────────
    ADD          = auto()   # Pop two → push sum
    SUB          = auto()   # Pop two → push difference
    MUL          = auto()   # Pop two → push product
    DIV          = auto()   # Pop two → push quotient
    MOD          = auto()   # Pop two → push remainder
    POW          = auto()   # Pop two → push power
    NEGATE       = auto()   # Pop one → push negated value

    # ── Comparison ────────────────────────────────────────────
    CMP_EQ       = auto()   # Pop two → push (a == b)
    CMP_NEQ      = auto()   # Pop two → push (a != b)
    CMP_LT       = auto()   # Pop two → push (a < b)
    CMP_LTE      = auto()   # Pop two → push (a <= b)
    CMP_GT       = auto()   # Pop two → push (a > b)
    CMP_GTE      = auto()   # Pop two → push (a >= b)

    # ── Logic ─────────────────────────────────────────────────
    AND          = auto()   # Pop two → push (a and b)
    OR           = auto()   # Pop two → push (a or b)
    NOT          = auto()   # Pop one → push (not a)

    # ── Control flow ──────────────────────────────────────────
    JUMP         = auto()   # Jump to instruction index
    JUMP_IF_FALSE = auto()  # Jump if top of stack is falsy
    JUMP_IF_TRUE  = auto()  # Jump if top of stack is truthy

    # ── Output ────────────────────────────────────────────────
    PRINT        = auto()   # Pop and print top of stack

    # ── Functions ─────────────────────────────────────────────
    MAKE_FUNCTION = auto()  # Create a function object
    CALL_FUNCTION = auto()  # Call a function with N args
    RETURN        = auto()  # Return from function

    # ── Scope ─────────────────────────────────────────────────
    PUSH_SCOPE   = auto()   # Enter a new scope
    POP_SCOPE    = auto()   # Exit current scope

    # ── Modules ───────────────────────────────────────────────
    IMPORT       = auto()   # Import a module

    # ── Program ───────────────────────────────────────────────
    HALT         = auto()   # Stop execution


@dataclass
class Instruction:
    """
    A single bytecode instruction.

    Attributes:
        opcode  — what operation to perform
        arg     — optional argument (constant value, name, etc.)
        line    — source line number (for error messages)
    """
    opcode: OpCode
    arg:    Any    = None
    line:   int    = 0

    def __repr__(self):
        if self.arg is not None:
            return f"{self.opcode.name:<16} {repr(self.arg)}"
        return self.opcode.name


@dataclass
class CodeObject:
    """
    A compiled unit of NEKOVA code.
    Contains the bytecode instructions for one
    program or function.

    Attributes:
        name         — name of this code object
        instructions — list of bytecode instructions
        constants    — constant values used in the code
        names        — variable names used in the code
    """
    name:         str               = "main"
    instructions: List[Instruction] = field(
                      default_factory=list)
    constants:    List[Any]         = field(
                      default_factory=list)
    names:        List[str]         = field(
                      default_factory=list)

    def emit(self, opcode: OpCode,
             arg: Any = None, line: int = 0):
        """Add an instruction to this code object."""
        instr = Instruction(opcode, arg, line)
        self.instructions.append(instr)
        return len(self.instructions) - 1

    def patch(self, index: int, arg: Any):
        """Update an instruction's argument (for jumps)."""
        self.instructions[index].arg = arg

    def current_index(self) -> int:
        """Return the index of the next instruction."""
        return len(self.instructions)

    def disassemble(self) -> str:
        """Return a human-readable bytecode listing."""
        lines = [f"=== {self.name} ==="]
        for i, instr in enumerate(self.instructions):
            lines.append(f"  {i:>4}  {instr}")
        return "\n".join(lines)

    def __repr__(self):
        return (f"CodeObject('{self.name}', "
                f"{len(self.instructions)} instructions)")
