# =============================================================
# NEKOVA Compiler — Virtual Machine
# =============================================================
# Executes bytecode instructions produced by the Compiler.
#
# The VM uses a "stack" — a list where values are pushed
# and popped. Operations take values from the stack,
# process them, and push the result back.
#
# Example — executing "show 2 + 3":
#   LOAD_CONST 2  → stack: [2]
#   LOAD_CONST 3  → stack: [2, 3]
#   ADD           → stack: [5]
#   PRINT         → prints "5", stack: []

from compiler.bytecode import OpCode, CodeObject, Instruction
from interpreter.environment import Environment
from runtime import ReturnSignal


class VMError(Exception):
    """Raised when the VM encounters a runtime error."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class VirtualMachine:
    """
    Executes NEKOVA bytecode.

    Usage:
        vm = VirtualMachine()
        vm.run(code_object)
    """

    def __init__(self):
        self.stack   = []           # value stack
        self.globals = Environment() # global scope
        self.env     = self.globals  # current scope
        self.ip      = 0            # instruction pointer

        # Register built-in functions
        self._register_builtins()

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def run(self, code: CodeObject):
        """Execute a CodeObject."""
        self.ip = 0
        instructions = code.instructions

        while self.ip < len(instructions):
            instr = instructions[self.ip]
            self.ip += 1

            self._execute(instr)

            # Stop on HALT
            if instr.opcode == OpCode.HALT:
                break

    # ----------------------------------------------------------
    # Instruction executor
    # ----------------------------------------------------------

    def _execute(self, instr: Instruction):
        """Execute a single instruction."""
        op  = instr.opcode
        arg = instr.arg

        # ── Stack operations ──────────────────────────────────
        if op == OpCode.LOAD_CONST:
            self._push(arg)

        elif op == OpCode.LOAD_NAME:
            try:
                value = self.env.get(arg)
                self._push(value)
            except NameError:
                raise VMError(
                    f"Variable '{arg}' is not defined.\n"
                    f"  Define it before using it."
                )

        elif op == OpCode.STORE_NAME:
            value = self._pop()
            self.env.set(arg, value)

        elif op == OpCode.POP:
            self._pop()

        # ── Arithmetic ────────────────────────────────────────
        elif op == OpCode.ADD:
            b, a = self._pop(), self._pop()
            if isinstance(a, str) or isinstance(b, str):
                self._push(self._to_str(a) + self._to_str(b))
            else:
                self._push(a + b)

        elif op == OpCode.SUB:
            b, a = self._pop(), self._pop()
            self._push(a - b)

        elif op == OpCode.MUL:
            b, a = self._pop(), self._pop()
            self._push(a * b)

        elif op == OpCode.DIV:
            b, a = self._pop(), self._pop()
            if b == 0:
                raise VMError("Cannot divide by zero.")
            self._push(a / b)

        elif op == OpCode.MOD:
            b, a = self._pop(), self._pop()
            self._push(a % b)

        elif op == OpCode.POW:
            b, a = self._pop(), self._pop()
            self._push(a ** b)

        elif op == OpCode.NEGATE:
            self._push(-self._pop())

        # ── Comparison ────────────────────────────────────────
        elif op == OpCode.CMP_EQ:
            b, a = self._pop(), self._pop()
            self._push(a == b)

        elif op == OpCode.CMP_NEQ:
            b, a = self._pop(), self._pop()
            self._push(a != b)

        elif op == OpCode.CMP_LT:
            b, a = self._pop(), self._pop()
            self._push(a < b)

        elif op == OpCode.CMP_LTE:
            b, a = self._pop(), self._pop()
            self._push(a <= b)

        elif op == OpCode.CMP_GT:
            b, a = self._pop(), self._pop()
            self._push(a > b)

        elif op == OpCode.CMP_GTE:
            b, a = self._pop(), self._pop()
            self._push(a >= b)

        # ── Logic ─────────────────────────────────────────────
        elif op == OpCode.AND:
            b, a = self._pop(), self._pop()
            self._push(a and b)

        elif op == OpCode.OR:
            b, a = self._pop(), self._pop()
            self._push(a or b)

        elif op == OpCode.NOT:
            self._push(not self._pop())

        # ── Control flow ──────────────────────────────────────
        elif op == OpCode.JUMP:
            self.ip = arg

        elif op == OpCode.JUMP_IF_FALSE:
            if not self._is_truthy(self._pop()):
                self.ip = arg

        elif op == OpCode.JUMP_IF_TRUE:
            if self._is_truthy(self._pop()):
                self.ip = arg

        # ── Output ────────────────────────────────────────────
        elif op == OpCode.PRINT:
            value = self._pop()
            print(self._to_str(value))

        # ── Functions ─────────────────────────────────────────
        elif op == OpCode.MAKE_FUNCTION:
            name, params, code_obj = arg
            self._push((name, params, code_obj))

        elif op == OpCode.CALL_FUNCTION:
            name, argc = arg
            args = []
            for _ in range(argc):
                args.insert(0, self._pop())

            result = self._call(name, args)
            self._push(result)

        elif op == OpCode.RETURN:
            value = self._pop()
            raise ReturnSignal(value)

        # ── Scope ─────────────────────────────────────────────
        elif op == OpCode.PUSH_SCOPE:
            self.env = Environment(parent=self.env)

        elif op == OpCode.POP_SCOPE:
            if self.env.parent:
                self.env = self.env.parent

        # ── Modules ───────────────────────────────────────────
        elif op == OpCode.IMPORT:
            self._import_module(arg)

        # ── Halt ──────────────────────────────────────────────
        elif op == OpCode.HALT:
            pass

        else:
            raise VMError(f"Unknown opcode: {op}")

    # ----------------------------------------------------------
    # Function calling
    # ----------------------------------------------------------

    def _call(self, name: str, args: list):
        """Call a function by name with given arguments."""
        try:
            callee = self.env.get(name)
        except NameError:
            raise VMError(
                f"'{name}' is not defined.\n"
                f"  Define it with:  task {name}(...):"
            )

        # Built-in Python callable
        if callable(callee) and not isinstance(callee, tuple):
            try:
                return callee(*args)
            except Exception as e:
                raise VMError(f"Error in '{name}': {e}")

        # NEKOVA task (name, params, code_object)
        if isinstance(callee, tuple):
            task_name, params, code_obj = callee

            if len(args) != len(params):
                raise VMError(
                    f"'{task_name}' expects "
                    f"{len(params)} argument(s) "
                    f"but got {len(args)}."
                )

            # Create local scope
            local_env    = Environment(parent=self.globals)
            previous_env = self.env
            previous_ip  = self.ip

            for param, value in zip(params, args):
                local_env.set(param, value)

            self.env = local_env

            try:
                self.run(code_obj)
                return None
            except ReturnSignal as r:
                return r.value
            finally:
                self.env = previous_env
                self.ip  = previous_ip

        raise VMError(f"'{name}' is not callable.")

    # ----------------------------------------------------------
    # Module importing
    # ----------------------------------------------------------

    def _import_module(self, name: str):
        """Import a stdlib module into the environment."""
        from stdlib import load_module
        try:
            functions = load_module(name)
            for fname, func in functions.items():
                self.env.set(fname, func)
        except ImportError as e:
            raise VMError(str(e))

    # ----------------------------------------------------------
    # Stack helpers
    # ----------------------------------------------------------

    def _push(self, value):
        """Push a value onto the stack."""
        self.stack.append(value)

    def _pop(self):
        """Pop a value from the stack."""
        if not self.stack:
            raise VMError(
                "Stack underflow — this is an internal error."
            )
        return self.stack.pop()

    def _peek(self):
        """Look at the top of the stack without popping."""
        if not self.stack:
            return None
        return self.stack[-1]

    # ----------------------------------------------------------
    # Utility
    # ----------------------------------------------------------

    def _is_truthy(self, value) -> bool:
        """Determine if a value is truthy in NEKOVA."""
        if value is None:   return False
        if value is False:  return False
        if value == 0:      return False
        if value == "":     return False
        return True

    def _to_str(self, value) -> str:
        """Convert any value to a printable string."""
        if value is None:   return "null"
        if value is True:   return "true"
        if value is False:  return "false"
        return str(value)

    def _register_builtins(self):
        """Register built-in functions."""
        self.globals.set("type_of",   lambda x: type(x).__name__)
        self.globals.set("to_number", lambda x: float(x)
                        if "." in str(x) else int(x))
        self.globals.set("to_text",   lambda x: str(x))
        self.globals.set("length",    lambda x: len(x))