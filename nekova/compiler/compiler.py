# =============================================================
# NEKOVA Compiler — AST to Bytecode Compiler
# =============================================================
# Walks the AST and emits bytecode instructions.
#
# Process:
#   1. Receive an AST node
#   2. Emit the matching bytecode instructions
#   3. Repeat for all nodes
#   4. Return a CodeObject ready for the VM
#
# This is called a "single-pass compiler" — simple and fast.

from nekova.compiler.bytecode import OpCode, Instruction, CodeObject
from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, Identifier, BinaryOp,
    UnaryOp, AssignStatement, ShowStatement, IfStatement,
    RepeatStatement, TaskStatement, ReturnStatement,
    UseStatement, CallExpression
)


class CompileError(Exception):
    """Raised when the compiler encounters invalid code."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  Line {line}: {message}")


class Compiler:
    """
    Compiles an NEKOVA AST into bytecode.

    Usage:
        compiler = Compiler()
        code     = compiler.compile(program)
        print(code.disassemble())
    """

    def __init__(self):
        self.code  = CodeObject(name="main")
        self.scope = []  # scope stack for functions

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def compile(self, program: Program) -> CodeObject:
        """Compile a full program into a CodeObject."""
        for stmt in program.statements:
            self._compile_node(stmt)

        self.code.emit(OpCode.HALT)
        return self.code

    # ----------------------------------------------------------
    # Node dispatcher
    # ----------------------------------------------------------

    def _compile_node(self, node):
        """Route a node to its matching compile method."""
        method_name = f"_compile_{type(node).__name__}"
        method      = getattr(self, method_name, None)

        if method is None:
            raise CompileError(
                f"Cannot compile '{type(node).__name__}' yet."
            )

        method(node)

    # ----------------------------------------------------------
    # Statement compilers
    # ----------------------------------------------------------

    def _compile_Program(self, node: Program):
        for stmt in node.statements:
            self._compile_node(stmt)

    def _compile_AssignStatement(self,
                                  node: AssignStatement):
        """name = value  →  LOAD_CONST value / STORE_NAME name"""
        self._compile_node(node.value)
        self.code.emit(OpCode.STORE_NAME, node.name)

    def _compile_ShowStatement(self, node: ShowStatement):
        """show expr  →  compile expr / PRINT"""
        self._compile_node(node.expression)
        self.code.emit(OpCode.PRINT)

    def _compile_IfStatement(self, node: IfStatement):
        """
        if condition:       COMPILE condition
            then_body       JUMP_IF_FALSE → else
        else:               COMPILE then_body
            else_body       JUMP → end
                            COMPILE else_body
                            end:
        """
        # Compile condition
        self._compile_node(node.condition)

        # Emit JUMP_IF_FALSE — patch later
        jump_if_false = self.code.emit(
            OpCode.JUMP_IF_FALSE, None)

        # Compile then body
        self.code.emit(OpCode.PUSH_SCOPE)
        for stmt in node.then_body:
            self._compile_node(stmt)
        self.code.emit(OpCode.POP_SCOPE)

        # Emit JUMP to skip else — patch later
        jump_over_else = self.code.emit(OpCode.JUMP, None)

        # Patch JUMP_IF_FALSE to here
        self.code.patch(jump_if_false,
                        self.code.current_index())

        # Compile else body
        if node.else_body:
            self.code.emit(OpCode.PUSH_SCOPE)
            for stmt in node.else_body:
                self._compile_node(stmt)
            self.code.emit(OpCode.POP_SCOPE)

        # Patch JUMP to here
        self.code.patch(jump_over_else,
                        self.code.current_index())

    def _compile_RepeatStatement(self,
                                  node: RepeatStatement):
        """
        repeat N:           LOAD_CONST N
            body            LOAD_CONST 0 (counter)
                            loop_start:
                            CMP_GTE counter N
                            JUMP_IF_TRUE → end
                            COMPILE body
                            counter += 1
                            JUMP → loop_start
                            end:
        """
        # Compile count expression
        self._compile_node(node.count)

        # Store count in temp variable
        self.code.emit(OpCode.STORE_NAME, "__repeat_count__")

        # Initialize counter to 0
        self.code.emit(OpCode.LOAD_CONST, 0)
        self.code.emit(OpCode.STORE_NAME, "__repeat_i__")

        # Loop start
        loop_start = self.code.current_index()

        # Check counter < count
        self.code.emit(OpCode.LOAD_NAME, "__repeat_i__")
        self.code.emit(OpCode.LOAD_NAME, "__repeat_count__")
        self.code.emit(OpCode.CMP_GTE)

        # Jump to end if counter >= count
        jump_to_end = self.code.emit(
            OpCode.JUMP_IF_TRUE, None)

        # Compile body
        self.code.emit(OpCode.PUSH_SCOPE)
        for stmt in node.body:
            self._compile_node(stmt)
        self.code.emit(OpCode.POP_SCOPE)

        # Increment counter
        self.code.emit(OpCode.LOAD_NAME, "__repeat_i__")
        self.code.emit(OpCode.LOAD_CONST, 1)
        self.code.emit(OpCode.ADD)
        self.code.emit(OpCode.STORE_NAME, "__repeat_i__")

        # Jump back to loop start
        self.code.emit(OpCode.JUMP, loop_start)

        # Patch jump to end
        self.code.patch(jump_to_end,
                        self.code.current_index())

    def _compile_TaskStatement(self, node: TaskStatement):
        """
        Compile a task definition.
        Creates a new CodeObject for the task body.
        """
        # Save current code object
        parent_code = self.code

        # Create new code object for the task
        task_code       = CodeObject(name=node.name)
        self.code       = task_code

        # Compile task body
        self.code.emit(OpCode.PUSH_SCOPE)
        for stmt in node.body:
            self._compile_node(stmt)
        self.code.emit(OpCode.POP_SCOPE)

        # Default return None
        self.code.emit(OpCode.LOAD_CONST, None)
        self.code.emit(OpCode.RETURN)

        # Restore parent code object
        self.code = parent_code

        # Store the task's code object
        self.code.emit(
            OpCode.MAKE_FUNCTION,
            (node.name, node.params, task_code)
        )
        self.code.emit(OpCode.STORE_NAME, node.name)

    def _compile_ReturnStatement(self,
                                  node: ReturnStatement):
        """return value  →  compile value / RETURN"""
        if node.value:
            self._compile_node(node.value)
        else:
            self.code.emit(OpCode.LOAD_CONST, None)
        self.code.emit(OpCode.RETURN)

    def _compile_UseStatement(self, node: UseStatement):
        """use module  →  IMPORT module"""
        self.code.emit(OpCode.IMPORT, node.module)

    # ----------------------------------------------------------
    # Expression compilers
    # ----------------------------------------------------------

    def _compile_BinaryOp(self, node: BinaryOp):
        """Compile a binary operation."""
        self._compile_node(node.left)
        self._compile_node(node.right)

        op_map = {
            "+":  OpCode.ADD,
            "-":  OpCode.SUB,
            "*":  OpCode.MUL,
            "/":  OpCode.DIV,
            "%":  OpCode.MOD,
            "**": OpCode.POW,
            "==": OpCode.CMP_EQ,
            "!=": OpCode.CMP_NEQ,
            "<":  OpCode.CMP_LT,
            "<=": OpCode.CMP_LTE,
            ">":  OpCode.CMP_GT,
            ">=": OpCode.CMP_GTE,
        }

        opcode = op_map.get(node.operator)
        if opcode is None:
            raise CompileError(
                f"Unknown operator '{node.operator}'"
            )

        self.code.emit(opcode)

    def _compile_UnaryOp(self, node: UnaryOp):
        """Compile a unary operation."""
        self._compile_node(node.operand)

        if node.operator == "-":
            self.code.emit(OpCode.NEGATE)
        elif node.operator == "not":
            self.code.emit(OpCode.NOT)

    def _compile_CallExpression(self,
                                 node: CallExpression):
        """Compile a function call."""
        # Push all arguments onto stack
        for arg in node.args:
            self._compile_node(arg)

        # Call the function with N args
        self.code.emit(
            OpCode.CALL_FUNCTION,
            (node.name, len(node.args))
        )

    # ── Literals ──────────────────────────────────────────────

    def _compile_IntegerLiteral(self,
                                 node: IntegerLiteral):
        self.code.emit(OpCode.LOAD_CONST, node.value)

    def _compile_FloatLiteral(self, node: FloatLiteral):
        self.code.emit(OpCode.LOAD_CONST, node.value)

    def _compile_StringLiteral(self,
                                node: StringLiteral):
        self.code.emit(OpCode.LOAD_CONST, node.value)

    def _compile_BooleanLiteral(self,
                                 node: BooleanLiteral):
        self.code.emit(OpCode.LOAD_CONST, node.value)

    def _compile_NullLiteral(self, node: NullLiteral):
        self.code.emit(OpCode.LOAD_CONST, None)

    def _compile_Identifier(self, node: Identifier):
        self.code.emit(OpCode.LOAD_NAME, node.name)
