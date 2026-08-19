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
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import (
    NEKOVARuntimeError, NEKOVAImportError, NEKOVANameError,
    NEKOVARecursionError
)


class NEKOVARunner:
    """
    Orchestrates execution of a single .NEKOVA source file.
    Knows nothing about the language itself â€” only manages
    file I/O and delegates to the pipeline.
    """

    def __init__(self, filepath: str, debug: bool = False,
                 compile_mode: bool = False, strict_types: bool = False,
                 script_args: dict = None, debug_ai: bool = False,
                 why: bool = False, simple_errors: bool = False,
                 record_ai: str = None, replay_ai: str = None,
                 self_hosted: bool = False):
        self.filepath     = filepath
        self.debug        = debug
        self.debug_ai     = debug_ai
        self.why          = why
        self.simple_errors = simple_errors
        self.record_ai    = record_ai
        self.replay_ai    = replay_ai
        self.compile_mode = compile_mode
        self.strict_types = strict_types
        self.script_args  = script_args or {}
        self.self_hosted  = self_hosted
        self.source       = ""

    def run(self):
        """Full execution pipeline. Returns exit code (0 = ok)."""
        if not self._validate_file():
            return 1
        if not self._load_source():
            return 1

        # Phase 26c — cassette record/replay, scoped to just this run
        # so it can never leak into a later NEKOVARunner instance
        # (e.g. across tests, or nekova watch's repeated re-runs).
        if self.record_ai or self.replay_ai:
            from nekova.ai.providers import (
                enable_cassette_recording, enable_cassette_replay,
                disable_cassette,
            )
            if self.record_ai:
                enable_cassette_recording(self.record_ai)
            else:
                enable_cassette_replay(self.replay_ai)
            try:
                return self._execute()
            finally:
                disable_cassette()

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

        def _display(error_type, message, exception=None, **kwargs):
            """
            Thin wrapper around display_error() that fills in the
            fields every call site here repeats (source, filepath)
            and threads self.why/the actual exception object through
            uniformly — added once here rather than to all twelve
            individual call sites below, so --why couldn't be missed
            on any particular error path.
            """
            display_error(
                error_type=error_type,
                message=message,
                source=self.source,
                filepath=self.filepath,
                why=self.why,
                exception=exception,
                simple=self.simple_errors,
                **kwargs,
            )

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
            # Phase 2 â€” Lexer, Phase 3 â€” Parser
            # Phase 27 â€” self-hosted path: lexer.nk + parser.nk,
            # bootstrapped via the Python toolchain, producing the
            # exact same Node tree the reference parser would (see
            # nekova/parser/rehydrate.py for how). Opt-in only, via
            # --self-hosted or [run] self_hosted_parser in
            # nekova.toml -- the Python path stays the default.
            if self.self_hosted:
                from nekova.parser.rehydrate import parse_self_hosted
                program = parse_self_hosted(self.source)
                tokens = None  # no separate token list to show in --debug
            else:
                lexer  = Lexer(self.source)
                tokens = lexer.tokenize()

                if self.debug:
                    print_info("Tokens:")
                    for token in tokens:
                        print(f"  {Color.CYAN}{token}{Color.RESET}")
                    print()

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
                from nekova.compiler import Compiler, VirtualMachine, CompileError
                try:
                    compiler = Compiler()
                    code     = compiler.compile(program)
                    if self.debug:
                        print_info("Bytecode:")
                        print(code.disassemble())
                        print()
                    vm = VirtualMachine()
                    vm.run(code)
                except CompileError as e:
                    raise NEKOVARuntimeError(f"Compile error: {e}") from e
            else:
                interpreter = Interpreter(strict_types=self.strict_types,
                                          debug_ai=self.debug_ai)
                # Inject CLI script args as built-in 'args' object
                from nekova.cli.args_object import ArgsObject
                interpreter.env["args"] = ArgsObject(self.script_args)
                interpreter.execute(
                    program,
                    filepath=os.path.abspath(self.filepath)
                )

        except LexerError as e:
            _display(
                error_type="SyntaxError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
                col=getattr(e, "column", 0),
            )
            return 1

        except ParseError as e:
            _display(
                error_type="ParseError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
                col=getattr(e, "column", 0),
            )
            return 1

        except NEKOVANameError as e:
            variables = {}
            try:
                variables = {
                    k: v for k, v in
                    interpreter.globals.variables.items()
                    if not callable(v)
                }
            except Exception:
                pass
            _display(
                error_type="NameError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
                col=getattr(e, "column", 0),
                variables=variables,
            )
            return 1

        except NameError as e:
            _display(
                error_type="NameError",
                message=str(e),
                exception=e,
            )
            return 1

        except NEKOVAImportError as e:
            _display(
                error_type="ImportError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
            )
            return 1

        except TypeError as e:
            _display(
                error_type="TypeError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
            )
            return 1

        except ZeroDivisionError as e:
            _display(
                error_type="ZeroDivisionError",
                message=str(e),
                exception=e,
            )
            return 1

        except IndexError as e:
            _display(
                error_type="IndexError",
                message=str(e),
                exception=e,
            )
            return 1

        except KeyError as e:
            _display(
                error_type="KeyError",
                message=str(e),
                exception=e,
            )
            return 1

        except NEKOVARecursionError as e:
            # NEKOVA's own call-depth counter caught this — the depth
            # figure is exact, not a guess derived from Python's stack.
            _display(
                error_type="RecursionError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
            )
            return 1

        except RecursionError:
            # Fallback: Python's own recursion limit fired before our
            # MAX_CALL_DEPTH check did (e.g. recursion that doesn't go
            # through _call_task). We don't know the exact NEKOVA-level
            # depth here, so we say so rather than inventing a number.
            _display(
                error_type="RecursionError",
                message=(
                    "Python's stack limit was reached before NEKOVA's "
                    "own call-depth check could catch it. This usually "
                    "means very deep or unbounded recursion."
                ),
            )
            return 1

        except NEKOVARuntimeError as e:
            _display(
                error_type="RuntimeError",
                message=str(e),
                exception=e,
                line=getattr(e, "line", 0),
            )
            return 1

        # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        elapsed = (time.perf_counter() - start) * 1000
        print()
        print_success(f"Done in {elapsed:.2f}ms")
        return 0