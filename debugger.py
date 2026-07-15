# =============================================================
# NEKOVA Language — Visual Debugger
# =============================================================
# Step through NEKOVA code line by line.
# See variables, current line, and execution flow.
#
# Usage:
#   python main.py debug examples/hello.NEKOVA

import os
import sys
from nekova.config import Color, NEKOVA_VERSION


class Debugger:
    """
    Visual step-through debugger for NEKOVA programs.

    Features:
        - Step through code line by line
        - View all variables at each step
        - Run to completion
        - Set breakpoints
        - View call stack
    """

    def __init__(self, filepath: str):
        self.filepath    = filepath
        self.source      = ""
        self.lines       = []
        self.current_line = 0
        self.variables   = {}
        self.call_stack  = []
        self.breakpoints = set()
        self.running     = False
        self.history     = []

        self._load_source()

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def start(self):
        """Start the debugging session."""
        self._print_header()
        self._run_debug_session()

    # ----------------------------------------------------------
    # Core debug session
    # ----------------------------------------------------------

    def _run_debug_session(self):
        """
        Main debug loop.
        Executes the program with instrumentation,
        pausing at each statement.
        """
        try:
            from nekova.lexer import Lexer, LexerError
            from nekova.parser.parser import Parser, ParseError
            from nekova.interpreter.interpreter import Interpreter

            # Lex and parse
            tokens  = Lexer(self.source).tokenize()
            program = Parser(tokens).parse()

            # Create instrumented interpreter
            self.interpreter = Interpreter()
            self.variables   = {}

            # Execute statements one by one
            for i, stmt in enumerate(
                    program.statements):
                # Get line number for this statement
                line_num = self._get_stmt_line(stmt)
                self.current_line = line_num

                # Check breakpoint
                if (line_num in self.breakpoints and
                        self.running):
                    self.running = False
                    print(f"\n{Color.YELLOW}"
                          f"  ⏸ Breakpoint hit at "
                          f"line {line_num}"
                          f"{Color.RESET}")

                # Show current state
                self._display_state(line_num)

                # Wait for user input
                action = self._get_action()

                if action == "quit":
                    print(f"\n{Color.CYAN}"
                          f"  Debug session ended."
                          f"{Color.RESET}\n")
                    return

                if action == "run":
                    self.running = True

                # Execute the statement
                try:
                    self.interpreter._execute_node(stmt)
                    # Update variable snapshot
                    self._update_variables()
                    self.history.append(
                        f"Line {line_num}: executed")

                except Exception as e:
                    print(f"\n{Color.RED}"
                          f"  ✗ Error at line "
                          f"{line_num}: {e}"
                          f"{Color.RESET}\n")
                    action = self._get_action()
                    if action == "quit":
                        return

                # If running, don't pause
                if self.running:
                    continue

            print(f"\n{Color.GREEN}"
                  f"  ✓ Program completed successfully!"
                  f"{Color.RESET}\n")

        except Exception as e:
            print(f"\n{Color.RED}"
                  f"  ✗ Debug error: {e}"
                  f"{Color.RESET}\n")

    def _display_state(self, current_line: int):
        """Display the current debug state."""
        if self.running:
            return

        width = 50
        print(f"\n{Color.DIM}{chr(9472) * width}{Color.RESET}")

        # Show source with current line highlighted
        self._display_source(current_line)

        # Show variables
        self._display_variables()

        # Show call stack if any
        if self.call_stack:
            self._display_call_stack()

        print(f"{Color.DIM}{chr(9472) * width}{Color.RESET}")

    def _display_source(self, current_line: int):
        """Show source code with current line marked."""
        print(f"\n  {Color.CYAN}Source:{Color.RESET}")

        # Show 3 lines before and after current
        start = max(0, current_line - 3)
        end   = min(len(self.lines),
                    current_line + 3)

        for i in range(start, end):
            line_num = i + 1
            content  = self.lines[i]

            if line_num == current_line:
                # Current line — highlight
                print(f"  {Color.GREEN}▶{Color.RESET} "
                      f"{Color.BOLD}"
                      f"{line_num:>3}{Color.RESET}  "
                      f"{Color.GREEN}{content}"
                      f"{Color.RESET}")
            elif line_num in self.breakpoints:
                # Breakpoint line
                print(f"  {Color.RED}●{Color.RESET} "
                      f"{line_num:>3}  "
                      f"{Color.DIM}{content}"
                      f"{Color.RESET}")
            else:
                # Normal line
                print(f"    {Color.DIM}"
                      f"{line_num:>3}  {content}"
                      f"{Color.RESET}")

    def _display_variables(self):
        """Display current variable values."""
        print(f"\n  {Color.CYAN}Variables:{Color.RESET}")

        if not self.variables:
            print(f"  {Color.DIM}  (none yet)"
                  f"{Color.RESET}")
            return

        for name, value in self.variables.items():
            if callable(value):
                continue
            val_str = repr(value)
            if len(val_str) > 40:
                val_str = val_str[:37] + "..."
            print(f"  {Color.DIM}  "
                  f"{name:<16} = {val_str}"
                  f"{Color.RESET}")

    def _display_call_stack(self):
        """Display the call stack."""
        print(f"\n  {Color.CYAN}Call Stack:{Color.RESET}")
        for frame in reversed(self.call_stack):
            print(f"  {Color.DIM}  → {frame}"
                  f"{Color.RESET}")

    def _get_action(self) -> str:
        """
        Get action from user.
        Returns: 'step', 'run', 'quit',
                 'breakpoint', 'vars'
        """
        if self.running:
            return "step"

        print(f"\n  {Color.DIM}"
              f"[s] Step  "
              f"[r] Run  "
              f"[b] Breakpoint  "
              f"[v] Variables  "
              f"[q] Quit"
              f"{Color.RESET}")

        try:
            choice = input(
                f"  {Color.CYAN}debug>{Color.RESET} "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        if choice in ("s", "step", ""):
            return "step"
        if choice in ("r", "run"):
            return "run"
        if choice in ("q", "quit", "exit"):
            return "quit"
        if choice.startswith("b "):
            # Set breakpoint: "b 5"
            try:
                line = int(choice.split()[1])
                self.breakpoints.add(line)
                print(f"  {Color.YELLOW}"
                      f"✓ Breakpoint set at "
                      f"line {line}{Color.RESET}")
            except Exception:
                pass
            return "step"
        if choice in ("v", "vars"):
            self._display_variables()
            return "step"
        if choice in ("h", "help"):
            self._print_commands()
            return "step"

        return "step"

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _load_source(self):
        """Load the source file."""
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(
                f"File not found: '{self.filepath}'"
            )
        with open(self.filepath, "r",
                  encoding="utf-8") as f:
            self.source = f.read()
        self.lines = self.source.splitlines()

    def _get_stmt_line(self, stmt) -> int:
        """Get the line number of a statement."""
        # Try to get line from token info
        for attr in ("line", "_line"):
            if hasattr(stmt, attr):
                return getattr(stmt, attr)

        # Try child nodes
        for attr in ("expression", "value",
                     "condition", "name"):
            child = getattr(stmt, attr, None)
            if child and hasattr(child, "line"):
                return child.line

        return self.current_line + 1

    def _update_variables(self):
        """Snapshot current variables."""
        if hasattr(self, 'interpreter'):
            self.variables = {
                k: v for k, v in
                self.interpreter.globals
                    .variables.items()
                if not callable(v)
            }

    def _print_header(self):
        """Print the debugger header."""
        print(f"""
{Color.CYAN}{Color.BOLD}  NEKOVA Visual Debugger{Color.RESET}
  {Color.DIM}Version {NEKOVA_VERSION}{Color.RESET}
  {Color.DIM}File: {self.filepath}{Color.RESET}
  {Color.DIM}Lines: {len(self.lines)}{Color.RESET}
  {Color.DIM}{'-' * 40}{Color.RESET}
  {Color.DIM}Commands: [s]tep [r]un [b]reakpoint [q]uit{Color.RESET}
""")

    def _print_commands(self):
        """Print available commands."""
        print(f"""
  {Color.CYAN}Commands:{Color.RESET}
  {Color.BOLD}s{Color.RESET} or Enter  Step to next line
  {Color.BOLD}r{Color.RESET}           Run to end or breakpoint
  {Color.BOLD}b <line>{Color.RESET}    Set breakpoint at line
  {Color.BOLD}v{Color.RESET}           Show all variables
  {Color.BOLD}h{Color.RESET}           Show this help
  {Color.BOLD}q{Color.RESET}           Quit debugger
""")