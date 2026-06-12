# =============================================================
# NEKOVA Language — Interactive REPL
# =============================================================
# Read-Eval-Print Loop for NEKOVA.
# Run with: nekova repl
# =============================================================

import sys
import os

from nekova.config import Color, NEKOVA_VERSION, NEKOVA_CODENAME


class REPL:
    """
    Interactive NEKOVA shell.
    Maintains state between inputs so variables persist across lines.
    """

    PROMPT      = f"{Color.CYAN}nekova>{Color.RESET} "
    PROMPT_CONT = f"{Color.DIM}   ...>{Color.RESET} "

    # Statements that produce side effects (show, use, etc.)
    # — don't auto-print their return value
    SILENT_NODES = (
        "AssignStatement", "ShowStatement", "UseStatement",
        "ImportStatement", "TaskStatement", "ThinkStatement",
        "PipelineStatement", "MemoryStatement", "SandboxStatement",
        "ParallelStatement", "PipelineDefStatement",
        "RunPipelineStatement", "ModelStatement",
    )

    def __init__(self):
        from nekova.interpreter.interpreter import Interpreter
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
                if self._handle_command(source):
                    continue
                self._execute(source)

            except KeyboardInterrupt:
                print()
                print(f"{Color.YELLOW}  Ctrl+C — use 'exit' to quit{Color.RESET}")
            except EOFError:
                self._quit()

    # ── Input ──────────────────────────────────────────────────────────────

    def _read_input(self) -> str:
        """
        Read one line or a complete block.
        Detects block starters (lines ending with :) and
        reads continuation lines until the block is complete.
        """
        try:
            line = input(self.PROMPT)
        except EOFError:
            raise

        if not line.strip():
            return ""

        # Multi-line block (ends with colon)
        if line.rstrip().endswith(":"):
            lines = [line]
            while True:
                try:
                    cont = input(self.PROMPT_CONT)
                    if not cont.strip():
                        # Empty line — check if more blocks expected
                        last = self._last_keyword(lines)
                        if last == "try":
                            continue  # need catch block
                        break
                    lines.append(cont)
                    stripped = cont.strip()
                    if stripped.startswith("catch") or stripped == "else:":
                        continue  # these need their own body
                except EOFError:
                    break

            # Indent non-block continuation lines
            result = [lines[0]]
            for l in lines[1:]:
                if l.strip() and not l.startswith(" ") and not l.startswith("\t"):
                    if not any(l.strip().startswith(k) for k in ("catch", "else")):
                        l = "    " + l
                result.append(l)
            return "\n".join(result)

        return line

    def _last_keyword(self, lines: list) -> str:
        for line in reversed(lines):
            s = line.strip()
            for kw in ("try", "if", "while", "repeat", "for"):
                if s.startswith(kw):
                    return kw
        return ""

    # ── Execute ────────────────────────────────────────────────────────────

    def _execute(self, source: str):
        """Execute NEKOVA source code and display results."""
        try:
            from nekova.lexer.lexer import Lexer
            from nekova.parser.parser import Parser

            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()

            if not program.statements:
                return

            for stmt in program.statements:
                result = self.interpreter._execute_node(stmt)

                # Auto-print expression results (not side-effect statements)
                node_type = type(stmt).__name__
                if result is not None and node_type not in self.SILENT_NODES:
                    display = self.interpreter._to_string(result)
                    print(f"{Color.DIM}= {Color.RESET}{display}")

            self.history.append(source)

        except Exception as e:
            # Try wrapping as expression if it looks like one
            stripped = source.strip()
            if not any(stripped.startswith(kw) for kw in (
                "show", "think", "use", "import", "if", "while",
                "repeat", "for", "try", "task", "pipeline", "memory",
                "sandbox", "model", "autonomous", "run", "#"
            )) and "=" not in stripped.split("(")[0]:
                try:
                    from nekova.lexer.lexer import Lexer
                    from nekova.parser.parser import Parser
                    tokens  = Lexer(f"show {stripped}").tokenize()
                    program = Parser(tokens).parse()
                    for stmt in program.statements:
                        result = self.interpreter._execute_node(stmt)
                        if result is not None:
                            display = self.interpreter._to_string(result)
                            print(f"{Color.DIM}= {Color.RESET}{display}")
                    self.history.append(source)
                    return
                except Exception:
                    pass

            msg = str(e).strip()
            first_line = msg.split("\n")[0]
            print(f"{Color.RED}Error: {first_line}{Color.RESET}")
            if len(msg.split("\n")) > 1:
                for line in msg.split("\n")[1:]:
                    if line.strip():
                        print(f"{Color.DIM}  {line.strip()}{Color.RESET}")

    # ── Commands ───────────────────────────────────────────────────────────

    def _handle_command(self, source: str) -> bool:
        """Handle special REPL commands. Returns True if handled."""
        cmd = source.strip().lower()

        if cmd in ("exit", "quit", "q", ":q"):
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
            from nekova.interpreter.interpreter import Interpreter
            self.interpreter = Interpreter()
            self.history = []
            print(f"{Color.GREEN}✓ Session reset{Color.RESET}")
            return True

        if cmd == "version":
            print(f"NEKOVA v{NEKOVA_VERSION} · {NEKOVA_CODENAME}")
            return True

        return False

    # ── Display ────────────────────────────────────────────────────────────

    def _print_welcome(self):
        border = "─" * 42
        print(f"""
{Color.CYAN}{Color.BOLD}  NEKOVA Interactive Shell{Color.RESET}
{Color.DIM}  {border}{Color.RESET}
{Color.DIM}  Version {NEKOVA_VERSION} · {NEKOVA_CODENAME}{Color.RESET}
{Color.DIM}  Connected Forge · SYNEKCOT Tech{Color.RESET}
{Color.DIM}  {border}{Color.RESET}
{Color.DIM}  Type 'help' for commands · 'exit' to quit{Color.RESET}
""")

    def _print_help(self):
        print(f"""
{Color.CYAN}Commands:{Color.RESET}
  {Color.BOLD}exit{Color.RESET}      Quit the REPL
  {Color.BOLD}clear{Color.RESET}     Clear the screen
  {Color.BOLD}vars{Color.RESET}      Show all variables in scope
  {Color.BOLD}history{Color.RESET}   Show last 10 commands
  {Color.BOLD}reset{Color.RESET}     Reset session (clear all vars)
  {Color.BOLD}version{Color.RESET}   Show NEKOVA version

{Color.CYAN}Examples:{Color.RESET}
  {Color.DIM}name = "Emmanuel"{Color.RESET}
  {Color.DIM}show f"Hello {{name}}!"{Color.RESET}
  {Color.DIM}use math{Color.RESET}
  {Color.DIM}show sqrt(144){Color.RESET}
  {Color.DIM}think "What is the capital of Nigeria?"{Color.RESET}
  {Color.DIM}task greet(n): show f"Hello {{n}}!"{Color.RESET}
""")

    def _print_history(self):
        if not self.history:
            print(f"{Color.DIM}  No history yet.{Color.RESET}")
            return
        print(f"{Color.CYAN}History:{Color.RESET}")
        for i, cmd in enumerate(self.history[-10:], 1):
            preview = cmd.replace("\n", " ↵ ")[:60]
            print(f"  {Color.DIM}{i:>2}.{Color.RESET} {preview}")

    def _print_vars(self):
        try:
            variables = self.interpreter.env.variables
            # Filter out built-in callables
            user_vars = {
                k: v for k, v in variables.items()
                if not callable(v) and not isinstance(v, type)
            }
            if not user_vars:
                print(f"{Color.DIM}  No variables defined yet.{Color.RESET}")
                return
            print(f"{Color.CYAN}Variables:{Color.RESET}")
            for name, value in user_vars.items():
                val_str = repr(value) if not isinstance(value, str) else f'"{value}"'
                print(f"  {Color.BOLD}{name}{Color.RESET} = {Color.DIM}{val_str}{Color.RESET}")
        except Exception:
            print(f"{Color.DIM}  Could not read variables.{Color.RESET}")

    def _quit(self):
        print(f"\n{Color.CYAN}Goodbye! Keep forging with NEKOVA. 🔥{Color.RESET}\n")
        self.running = False
        sys.exit(0)