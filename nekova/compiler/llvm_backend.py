# =============================================================
# NEKOVA Compiler — LLVM Backend
# =============================================================
# Compiles NEKOVA AST nodes to native machine code via LLVM.
# Falls back to Python transpiler for unsupported features.
#
# Usage:
#   from compiler.llvm_backend import LLVMCompiler
#   compiler = LLVMCompiler()
#   compiler.compile("examples/hello.NEKOVA", "hello.exe")

import os
import sys


class LLVMCompiler:
    """
    Compiles NEKOVA programs to native executables.
    Uses llvmlite for numeric code, transpiler for everything else.
    """

    def __init__(self):
        self.llvm_available = self._check_llvm()

    def _check_llvm(self) -> bool:
        """Check if llvmlite is available."""
        try:
            import llvmlite.binding as llvm
            llvm.initialize()
            llvm.initialize_native_target()
            llvm.initialize_native_asmprinter()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def compile(self, source_path: str,
                output_path: str = None) -> str:
        """
        Compile an NEKOVA source file to a native executable.
        Returns the path to the compiled output.
        """
        if not os.path.isfile(source_path):
            raise FileNotFoundError(
                f"Source file not found: '{source_path}'"
            )

        # Read and parse the source
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()

        from lexer import Lexer
        from parser.parser import Parser

        tokens  = Lexer(source).tokenize()
        program = Parser(tokens).parse()

        # Determine output path
        if not output_path:
            base = os.path.splitext(source_path)[0]
            output_path = base + (".exe"
                if sys.platform == "win32" else "")

        # Try LLVM first, fall back to transpiler
        if self.llvm_available and self._is_llvm_compatible(program):
            return self._compile_llvm(
                program, source, output_path)
        else:
            return self._compile_transpiler(
                program, source, output_path)

    def _is_llvm_compatible(self, program) -> bool:
        """
        Check if the program only uses LLVM-supported features.
        Currently: integer math, basic print, variables.
        """
        from parser.nodes import (
            Program, IntegerLiteral, FloatLiteral,
            BinaryOp, ShowStatement, AssignStatement,
            Identifier
        )

        supported = (
            Program, IntegerLiteral, FloatLiteral,
            BinaryOp, ShowStatement, AssignStatement,
            Identifier
        )

        for stmt in program.statements:
            if not isinstance(stmt, supported):
                return False
            if isinstance(stmt, ShowStatement):
                if not isinstance(stmt.expression,
                    (IntegerLiteral, FloatLiteral,
                     Identifier, BinaryOp)):
                    return False
        return True

    def _compile_llvm(self, program, source: str,
                      output_path: str) -> str:
        """Compile to native code using llvmlite."""
        try:
            import llvmlite.binding as llvm
            import llvmlite.ir as ir

            # Create LLVM module
            module  = ir.Module(name="NEKOVA_program")
            module.triple = llvm.get_default_triple()

            # Declare printf
            voidptr_ty = ir.IntType(8).as_pointer()
            printf_ty  = ir.FunctionType(
                ir.IntType(32), [voidptr_ty],
                var_arg=True
            )
            printf = ir.Function(
                module, printf_ty, name="printf")

            # Create main function
            main_ty = ir.FunctionType(ir.IntType(32), [])
            main_fn = ir.Function(
                module, main_ty, name="main")
            block   = main_fn.append_basic_block("entry")
            builder = ir.IRBuilder(block)

            # Variable storage
            variables = {}

            # Format strings
            fmt_int   = builder.global_string_ptr("%d\n", "fmt_int")
            fmt_float = builder.global_string_ptr("%.6f\n", "fmt_float")

            def compile_expr(node):
                from parser.nodes import (
                    IntegerLiteral, FloatLiteral,
                    BinaryOp, Identifier
                )
                if isinstance(node, IntegerLiteral):
                    return ir.Constant(ir.IntType(64),
                                       node.value)
                if isinstance(node, FloatLiteral):
                    return ir.Constant(ir.DoubleType(),
                                       node.value)
                if isinstance(node, Identifier):
                    if node.name in variables:
                        return builder.load(
                            variables[node.name])
                    return ir.Constant(ir.IntType(64), 0)
                if isinstance(node, BinaryOp):
                    left  = compile_expr(node.left)
                    right = compile_expr(node.right)
                    op    = node.operator
                    if op == "+": return builder.add(left, right)
                    if op == "-": return builder.sub(left, right)
                    if op == "*": return builder.mul(left, right)
                    if op == "/": return builder.sdiv(left, right)
                return ir.Constant(ir.IntType(64), 0)

            from parser.nodes import (
                ShowStatement, AssignStatement
            )

            for stmt in program.statements:
                if isinstance(stmt, AssignStatement):
                    val = compile_expr(stmt.value)
                    if stmt.name not in variables:
                        ptr = builder.alloca(
                            ir.IntType(64), name=stmt.name)
                        variables[stmt.name] = ptr
                    builder.store(val, variables[stmt.name])

                elif isinstance(stmt, ShowStatement):
                    val = compile_expr(stmt.expression)
                    builder.call(printf, [fmt_int, val])

            # Return 0
            builder.ret(ir.Constant(ir.IntType(32), 0))

            # Compile to machine code
            llvm_ir   = str(module)
            mod       = llvm.parse_assembly(llvm_ir)
            mod.verify()

            target   = llvm.Target.from_default_triple()
            target_m = target.create_target_machine()
            obj_code = target_m.emit_object(mod)

            # Write object file
            obj_path = output_path + ".o"
            with open(obj_path, "wb") as f:
                f.write(obj_code)

            # Link to executable
            os.system(f"gcc {obj_path} -o {output_path}")
            os.remove(obj_path)

            return output_path

        except Exception as e:
            # Fall back to transpiler
            return self._compile_transpiler(
                None, source, output_path)

    def _compile_transpiler(self, program, source: str,
                             output_path: str) -> str:
        """
        Compile NEKOVA to a standalone Python script.
        Works for all NEKOVA features.
        """
        from compiler.transpiler import NEKOVATranspiler
        transpiler = NEKOVATranspiler()
        return transpiler.compile(source, output_path)
