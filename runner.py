# =============================================================
# NEKOVA Language â€” File Runner
# =============================================================
# Loads .nk files and passes them through the pipeline.
# Pipeline is a stub for now â€” will be filled in Phase 2-4.

import sys
import io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import sys
import time

from nekova.config import NEKOVA_EXTENSION, Color
from nekova.cli import print_error, print_info, print_success, print_separator
from nekova.cli.error_display import display_error
from nekova.lexer import Lexer, LexerError
from nekova.parser.parser import Parser, ParseError
from nekova.interpreter.interpreter import (
    Interpreter, RuntimeError,
    NEKOVAImportError, NEKOVANameError
)


class NEKOVARunner:
    """
    Orchestrates execution of a single .NEKOVA source file.
    Knows nothing about the language itself â€” only manages
    file I/O and delegates to the pipeline.
    """

    def __init__(self, filepath: str, debug: bool = False,
                 compile_mode: bool = False, strict_types: bool = False):
        self.filepath     = filepath
        self.debug        = debug
        self.compile_mode = compile_mode
        self.strict_types = strict_types
        self.source       = ""

    def run(self):
        """Full execution pipeline. Returns exit code (0 = ok)."""
        if not self._validate_file():
            return 1
        if not self._load_source():
            return 1
        return self._execute()

    def _validate_file(self) -> bool:
        """Check the file exists and has the .NEKOVA extension."""
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

        # â”€â”€ PIPELINE STUB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        print_info(f"Running '{self.filepath}' ...")
        print()

        try:
            # Phase 2 â€” Lexer
            lexer  = Lexer(self.source)
            tokens = lexer.tokenize()

            if self.debug:
                print_info("Tokens:")
                for token in tokens:
                    print(f"  {Color.CYAN}{token}{Color.RESET}")
                print()

            # Phase 3 â€” Parser
            parser  = Parser(tokens)
            program = parser.parse()

            if self.debug:
                print_info("AST:")
                for stmt in program.statements:
                    print(f"  {Color.MAGENTA}{stmt}{Color.RESET}")
                print()

            # Phase 4 â€” Interpreter (default)
            # Phase 13 â€” Compiler (when --compile flag used)
            if self.compile_mode:
                from nekova.compiler import Compiler, VirtualMachine
                from nekova.compiler import CompileError
                compiler = Compiler()
                code     = compiler.compile(program)

                if self.debug:
                    print_info("Bytecode:")
                    print(code.disassemble())
                    print()

                vm = VirtualMachine()
                vm.run(code)
            else:
                interpreter = Interpreter(strict_types=self.strict_types)
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

        # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        elapsed = (time.perf_counter() - start) * 1000
        print()
        print_success(f"Done in {elapsed:.2f}ms")
        return 0