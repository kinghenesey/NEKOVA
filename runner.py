# =============================================================
# NEKOVA Language — File Runner
# =============================================================
# Loads .nk files and passes them through the pipeline.
# Pipeline is a stub for now — will be filled in Phase 2-4.

import os
import sys
import time

from config import NEKOVA_EXTENSION, Color
from cli import print_error, print_info, print_success, print_separator
from cli.error_display import display_error
from lexer import Lexer, LexerError
from parser.parser import Parser, ParseError
from interpreter.interpreter import (
    Interpreter, RuntimeError,
    NEKOVAImportError, NEKOVANameError
)


class NEKOVARunner:
    """
    Orchestrates execution of a single .aion source file.
    Knows nothing about the language itself — only manages
    file I/O and delegates to the pipeline.
    """

    def __init__(self, filepath: str, debug: bool = False, compile_mode: bool = False):
        self.filepath = filepath
        self.debug    = debug
        self.compile_mode = compile_mode
        self.source   = ""

    def run(self):
        """Full execution pipeline. Returns exit code (0 = ok)."""
        if not self._validate_file():
            return 1
        if not self._load_source():
            return 1
        return self._execute()

    def _validate_file(self) -> bool:
        """Check the file exists and has the .aion extension."""
        if not self.filepath.endswith(NEKOVA_EXTENSION):
            print_error(
                f"'{self.filepath}' is not a NEKOVA file.\n"
                f"  Expected a file ending in '{NEKOVA_EXTENSION}'"
            )
            return False

        if not os.path.isfile(self.filepath):
            print_error(
                f"File not found: '{self.filepath}'\n"
                f"  Check the path and try again."
            )
            return False

        return True

    def _load_source(self) -> bool:
        """Read the source file from disk."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.source = f.read()

            if self.debug:
                print_info(f"Loaded '{self.filepath}' "
                            f"({len(self.source)} bytes, "
                            f"{len(self.source.splitlines())} lines)")
            return True

        except PermissionError:
            print_error(f"Permission denied reading '{self.filepath}'")
            return False

        except Exception as e:
            print_error(f"Could not read file: {e}")
            return False

    def _execute(self) -> int:
        """
        Run source through the NEKOVA pipeline.
        Phases 2-4 will replace the stub below with:
            tokens = Lexer(self.source).tokenize()
            ast    = Parser(tokens).parse()
            result = Interpreter(ast).execute()
        """
        start = time.perf_counter()

        if self.debug:
            print_separator()
            print_info("Source code:")
            for i, line in enumerate(self.source.splitlines(), 1):
                print(f"  {Color.DIM}{i:>3}{Color.RESET}  {line}")
            print_separator()

        # ── PIPELINE STUB ──────────────────────────────────────
        print_info(f"Running '{self.filepath}' ...")
        print()

        try:
            # Phase 2 — Lexer
            lexer  = Lexer(self.source)
            tokens = lexer.tokenize()

            if self.debug:
                print_info("Tokens:")
                for token in tokens:
                    print(f"  {Color.CYAN}{token}{Color.RESET}")
                print()

            # Phase 3 — Parser
            parser  = Parser(tokens)
            program = parser.parse()

            if self.debug:
                print_info("AST:")
                for stmt in program.statements:
                    print(f"  {Color.MAGENTA}{stmt}{Color.RESET}")
                print()

            # Phase 4 — Interpreter (default)
            # Phase 13 — Compiler (when --compile flag used)
            if self.compile_mode:
                from compiler import Compiler, VirtualMachine
                from compiler import CompileError
                compiler = Compiler()
                code     = compiler.compile(program)

                if self.debug:
                    print_info("Bytecode:")
                    print(code.disassemble())
                    print()

                vm = VirtualMachine()
                vm.run(code)
            else:
                interpreter = Interpreter()
                interpreter.execute(
                    program,
                    filepath=os.path.abspath(self.filepath)
                )

        except LexerError as e:
            display_error(
                error_type="SyntaxError",
                message=str(e),
                source=self.source,
                filepath=self.filepath,
                line=getattr(e, "line", 0),
            )
            return 1

        except ParseError as e:
            display_error(
                error_type="ParseError",
                message=str(e),
                source=self.source,
                filepath=self.filepath,
                line=getattr(e, "line", 0),
            )
            return 1

        except NEKOVANameError as e:
            variables = {}
            try:
                # Only show user-defined variables
                # not built-in functions
                variables = {
                    k: v for k, v in
                    interpreter.globals.variables.items()
                    if not callable(v)
                }
            except Exception:
                pass
            display_error(
                error_type="NameError",
                message=str(e),
                source=self.source,
                filepath=self.filepath,
                line=getattr(e, "line", 0),
                variables=variables,
            )
            return 1

        except NEKOVAImportError as e:
            display_error(
                error_type="ImportError",
                message=str(e),
                source=self.source,
                filepath=self.filepath,
                line=getattr(e, "line", 0),
            )
            return 1

        except RuntimeError as e:
            display_error(
                error_type="RuntimeError",
                message=str(e),
                source=self.source,
                filepath=self.filepath,
                line=getattr(e, "line", 0),
            )
            return 1

        # ───────────────────────────────────────────────────────
        elapsed = (time.perf_counter() - start) * 1000
        print()
        print_success(f"Done in {elapsed:.2f}ms")
        return 0