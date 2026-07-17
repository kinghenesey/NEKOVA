# =============================================================
# NEKOVA Language — Interactive REPL  (Phase 12B)
# =============================================================
# Improvements over v1.2.0:
#   - Arrow-key history  (readline on Unix; pyreadline3 on Windows)
#   - ?help  shorthand for help
#   - ?<command>  alias for any REPL command
#   - Persistent history file (~/.nekova_history)
#   - Multiline blocks (unchanged — already working)
# =============================================================

import sys
import io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os

from nekova.config import Color, NEKOVA_VERSION, NEKOVA_CODENAME

# ── Readline / history setup ──────────────────────────────────────────────────

HISTORY_FILE = os.path.expanduser("~/.nekova_history")
MAX_HISTORY  = 500

def _setup_readline():
    """Enable arrow-key history on all platforms."""
    try:
        import readline
        try:
            readline.read_history_file(HISTORY_FILE)
        except FileNotFoundError:
            pass
        readline.set_history_length(MAX_HISTORY)
        return readline
    except ImportError:
        # Windows fallback: try pyreadline3
        try:
            import pyreadline3  # noqa: F401 — importing activates arrow-key support
        except ImportError:
            pass
        return None

def _save_history(readline_mod):
    if readline_mod is not None:
        try:
            readline_mod.write_history_file(HISTORY_FILE)
        except Exception:
            pass

# ── REPL ──────────────────────────────────────────────────────────────────────

class REPL:
    """
    Interactive NEKOVA shell.
    Maintains state between inputs so variables persist across lines.
    Phase 12B: arrow-key history, ?help / ?<cmd> aliases, persistent history.
    """

    PROMPT      = f"{Color.CYAN}nekova>{Color.RESET} "
    PROMPT_CONT = f"{Color.DIM}   ...>{Color.RESET} "

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
        self.history     = []          # session history (REPL-level)
        self.running     = True
        self._readline   = _setup_readline()

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

        _save_history(self._readline)

    # ── Input ─────────────────────────────────────────────────────────────────

    def _read_input(self) -> str:
        """Read one line or a complete block."""
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
                        last = self._last_keyword(lines)
                        if last == "try":
                            continue
                        break
                    lines.append(cont)
                    stripped = cont.strip()
                    if stripped.startswith("catch") or stripped == "else:":
                        continue
                except EOFError:
                    break

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

    # ── Execute ───────────────────────────────────────────────────────────────

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
                node_type = type(stmt).__name__
                if result is not None and node_type not in self.SILENT_NODES:
                    display = self.interpreter._to_string(result)
                    print(f"{Color.DIM}= {Color.RESET}{display}")

            self.history.append(source)

        except Exception as e:
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

    # ── Commands ──────────────────────────────────────────────────────────────

    def _handle_command(self, source: str) -> bool:
        """Handle special REPL commands. Returns True if handled."""
        raw = source.strip()

        # ?help  and ?<cmd>  shortcuts
        if raw.startswith("?"):
            raw = raw[1:].strip() or "help"

        cmd = raw.lower()

        if cmd in ("exit", "quit", "q", ":q"):
            self._quit()
            return True

        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return True

        # help <topic>  — glossary lookup (Phase 26b), checked before
        # the bare "help" command below since both start with "help".
        # Reachable either directly ("help think") or via the "?"
        # shortcut above, which turns "?help think" into "help think"
        # before cmd is computed here.
        if cmd.startswith("help "):
            topic = raw.split(None, 1)[1]
            from nekova.cli.glossary import format_topic
            print(format_topic(topic))
            return True

        if cmd in ("help", "?"):
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
            print(f"{Color.GREEN}Session reset{Color.RESET}")
            return True

        if cmd == "version":
            print(f"NEKOVA v{NEKOVA_VERSION} · {NEKOVA_CODENAME}")
            return True

        if cmd == "templates":
            self._print_templates()
            return True

        return False

    # ── Display ───────────────────────────────────────────────────────────────

    def _print_welcome(self):
        border = chr(9472) * 42
        print(f"""
{Color.CYAN}{Color.BOLD}  NEKOVA Interactive Shell{Color.RESET}
{Color.DIM}  {border}{Color.RESET}
{Color.DIM}  Version {NEKOVA_VERSION} · {NEKOVA_CODENAME}{Color.RESET}
{Color.DIM}  Connected Forge · SYNEKCOT Tech{Color.RESET}
{Color.DIM}  {border}{Color.RESET}
{Color.DIM}  Type 'help' or '?help' for commands · 'exit' to quit{Color.RESET}
""")

    def _print_help(self):
        print(f"""
{Color.CYAN}REPL Commands:{Color.RESET}
  {Color.BOLD}exit{Color.RESET}        Quit the REPL  (also: quit, q, :q)
  {Color.BOLD}clear{Color.RESET}       Clear the screen
  {Color.BOLD}vars{Color.RESET}        Show all variables in scope
  {Color.BOLD}history{Color.RESET}     Show last 10 commands
  {Color.BOLD}reset{Color.RESET}       Reset session (clear all vars)
  {Color.BOLD}version{Color.RESET}     Show NEKOVA version
  {Color.BOLD}templates{Color.RESET}   List available project templates

{Color.CYAN}Shorthand:{Color.RESET}
  {Color.DIM}?help{Color.RESET}  →  help
  {Color.DIM}?vars{Color.RESET}  →  vars
  {Color.DIM}?<cmd>{Color.RESET} →  <cmd>

{Color.CYAN}Navigation:{Color.RESET}
  {Color.DIM}Up/Down arrow keys{Color.RESET}   Browse command history
  {Color.DIM}Ctrl+C{Color.RESET}               Cancel current input
  {Color.DIM}Ctrl+D{Color.RESET}               Exit REPL

{Color.CYAN}NEKOVA Examples:{Color.RESET}
  {Color.DIM}name = "Emmanuel"{Color.RESET}
  {Color.DIM}show f"Hello {{name}}!"{Color.RESET}
  {Color.DIM}use math{Color.RESET}
  {Color.DIM}show sqrt(144){Color.RESET}
  {Color.DIM}think "What is the capital of Nigeria?" as text{Color.RESET}
  {Color.DIM}task greet(n): show f"Hello {{n}}!"{Color.RESET}
  {Color.DIM}remember "key" as "value"{Color.RESET}
  {Color.DIM}recall "key"{Color.RESET}
""")

    def _print_history(self):
        if not self.history:
            print(f"{Color.DIM}  No history yet.{Color.RESET}")
            return
        print(f"{Color.CYAN}History:{Color.RESET}")
        for i, cmd in enumerate(self.history[-10:], 1):
            preview = cmd.replace("\n", " ") [:60]
            print(f"  {Color.DIM}{i:>2}.{Color.RESET} {preview}")

    def _print_vars(self):
        try:
            variables = self.interpreter.env.variables
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

    def _print_templates(self):
        from nekova.cli.templates import list_templates
        print(f"{Color.CYAN}Project Templates:{Color.RESET}")
        for name, desc in list_templates():
            print(f"  {Color.BOLD}{name:<12}{Color.RESET} {Color.DIM}{desc}{Color.RESET}")
        print()
        print(f"  {Color.DIM}Usage: nekova new myapp --template <name>{Color.RESET}")
        print()

    def _quit(self):
        print(f"\n{Color.CYAN}Goodbye! Keep forging with NEKOVA.{Color.RESET}\n")
        self.running = False
        _save_history(self._readline)
        sys.exit(0)