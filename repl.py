# =============================================================
# NEKOVA Language — Interactive REPL
# =============================================================
# Read-Eval-Print Loop for NEKOVA.
# Type NEKOVA code interactively and see results immediately.
#
# Usage:
#   python main.py --repl
#   python main.py repl

import sys
import os

from nekova.config import Color, NEKOVA_VERSION, NEKOVA_CODENAME
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.environment import Environment


class REPL:
    """
    Interactive NEKOVA shell.
    Maintains state between inputs so variables persist.
    """

    PROMPT      = f"{Color.CYAN}NEKOVA>{Color.RESET} "
    PROMPT_CONT = f"{Color.DIM}  ...>{Color.RESET} "

    def __init__(self):
        # Single interpreter instance — keeps all variables
        self.interpreter = Interpreter()
        self.history     = []
        self.running     = True

    def start(self):
        """Start the REPL session."""
        self._print_welcome()

        while self.running:
            try:
                source = self._read_input()

                if not source:
                    continue

                # Handle special REPL commands
                if self._handle_command(source):
                    continue

                # Execute the NEKOVA code
                self._execute(source)

            except KeyboardInterrupt:
                print()
                print(f"{Color.YELLOW}  Use 'exit' "
                      f"to quit{Color.RESET}")

            except EOFError:
                self._quit()

    def _read_input(self) -> str:
        """
        Read one line or a complete block from the user.
        Handles multi-line input for all block types.
        """
        try:
            line = input(self.PROMPT)
        except EOFError:
            raise

        if not line.strip():
            return ""

        # Check if line starts a block (ends with :)
        if line.rstrip().endswith(":"):
            lines  = [line]
            indent = 0

            while True:
                try:
                    cont = input(self.PROMPT_CONT)

                    # Empty line — check if we need
                    # to keep reading for catch/else
                    if not cont.strip():
                        # Check if last keyword needs
                        # a continuation block
                        last_keyword = self._last_keyword(
                            lines)
                        if last_keyword in ("try",):
                            # Need catch block — keep reading
                            continue
                        break

                    lines.append(cont)

                    # Track if we need more blocks
                    stripped = cont.strip()
                    if stripped in ("catch:",
                                   "catch error:") or \
                       stripped.startswith("catch ") or \
                       stripped == "else:":
                        # These need their own body
                        continue

                except EOFError:
                    break

            # Add indentation to block lines
            result = []
            result.append(lines[0])
            for l in lines[1:]:
                if not l.startswith(" ") and \
                   not l.startswith("\t") and \
                   not l.strip().startswith("catch") and \
                   not l.strip().startswith("else"):
                    result.append("    " + l)
                else:
                    result.append(l)
            return "\n".join(result)

        return line

    def _last_keyword(self, lines: list) -> str:
        """Get the last block keyword from lines."""
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("try"):
                return "try"
            if stripped.startswith("if"):
                return "if"
            if stripped.startswith("while"):
                return "while"
            if stripped.startswith("repeat"):
                return "repeat"
        return ""

    def _execute(self, source: str):
        """Execute NEKOVA source code in the REPL."""
        try:
            from nekova.lexer import Lexer, LexerError
            from nekova.parser.parser import Parser, ParseError
            from nekova.interpreter.interpreter import RuntimeError

            # Tokenize
            tokens = Lexer(source).tokenize()

            # Parse
            parser  = Parser(tokens)
            program = parser.parse()

            if not program.statements:
                return

            # Execute each statement
            for stmt in program.statements:
                result = self.interpreter._execute_node(stmt)

                # Auto-print expression results
                if result is not None:
                    from nekova.parser.nodes import (
                        AssignStatement, ShowStatement,
                        UseStatement
                    )
                    if not isinstance(stmt, (
                        AssignStatement, ShowStatement,
                        UseStatement
                    )):
                        print(f"{Color.DIM}= "
                              f"{self.interpreter._to_string(result)}"
                              f"{Color.RESET}")

            # Save to history
            self.history.append(source)

        except Exception as e:
            # Show clean error without traceback
            msg = str(e).strip()
            print(f"{Color.RED}Error: {msg}{Color.RESET}")

    def _handle_command(self, source: str) -> bool:
        """
        Handle special REPL commands.
        Returns True if command was handled.
        """
        cmd = source.strip().lower()

        if cmd in ("exit", "quit", "q"):
            self._quit()
            return True

        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return True

        if cmd == "help":
            self._print_help()
            return True

        if cmd == "history":
            self._print_history()
            return True

        if cmd == "vars":
            self._print_vars()
            return True

        if cmd == "reset":
            self.interpreter = Interpreter()
            print(f"{Color.GREEN}? Session reset"
                  f"{Color.RESET}")
            return True

        return False

    def _print_welcome(self):
        """Print the REPL welcome message."""
        print(f"""
{Color.CYAN}{Color.BOLD}NEKOVA Interactive Shell{Color.RESET}
{Color.DIM}Version {NEKOVA_VERSION} · {NEKOVA_CODENAME}{Color.RESET}
{Color.DIM}Type 'help' for commands, 'exit' to quit{Color.RESET}
{Color.DIM}{'-' * 40}{Color.RESET}
""")

    def _print_help(self):
        """Print REPL help."""
        print(f"""
{Color.CYAN}REPL Commands:{Color.RESET}
  {Color.BOLD}exit{Color.RESET}      Quit the REPL
  {Color.BOLD}clear{Color.RESET}     Clear the screen
  {Color.BOLD}vars{Color.RESET}      Show all variables
  {Color.BOLD}history{Color.RESET}   Show command history
  {Color.BOLD}reset{Color.RESET}     Reset the session

{Color.CYAN}NEKOVA Examples:{Color.RESET}
  {Color.DIM}name = "Emmanuel"{Color.RESET}
  {Color.DIM}show "Hello " + name{Color.RESET}
  {Color.DIM}show 2 + 3{Color.RESET}
  {Color.DIM}use math{Color.RESET}
  {Color.DIM}show sqrt(16){Color.RESET}
""")

    def _print_history(self):
        """Print command history."""
        if not self.history:
            print(f"{Color.DIM}No history yet.{Color.RESET}")
            return
        print(f"{Color.CYAN}History:{Color.RESET}")
        for i, cmd in enumerate(self.history[-10:], 1):
            print(f"  {Color.DIM}{i:>3}.{Color.RESET} {cmd}")

    def _print_vars(self):
        """Print all current variables."""
        variables = self.interpreter.globals.variables
        if not variables:
            print(f"{Color.DIM}No variables defined yet."
                  f"{Color.RESET}")
            return
        print(f"{Color.CYAN}Variables:{Color.RESET}")
        for name, value in variables.items():
            if not callable(value) and not isinstance(
                    value, type):
                print(f"  {Color.BOLD}{name}{Color.RESET}"
                      f" = {repr(value)}")

    def _quit(self):
        """Exit the REPL."""
        print(f"\n{Color.CYAN}Goodbye! Keep building "
              f"with NEKOVA. ??{Color.RESET}\n")
        self.running = False
        sys.exit(0)
