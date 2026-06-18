from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, FStringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement,
    MemoryStatement, SandboxStatement, PipelineDefStatement, RunPipelineStatement, IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, UseStatement,
    ImportStatement, CallExpression, IndexExpression,
    MethodCall,
    PropertyAccess,
    ClassDefinition, NewInstance, SelfAccess, SelfAssign
)
from nekova.interpreter.environment import Environment
from nekova.runtime import ReturnSignal
from nekova.parser.async_nodes import (
    AsyncFunctionNode, AwaitNode, StreamThinkNode, FetchNode
)
from nekova.interpreter.exceptions import (
    NEKOVARuntimeError, NEKOVAImportError, NEKOVANameError
)
from nekova.interpreter.async_interpreter import AsyncInterpreterMixin
from nekova.interpreter.class_interpreter import ClassInterpreterMixin


class Interpreter(AsyncInterpreterMixin, ClassInterpreterMixin):
    """
    Executes a NEKOVA AST produced by the Parser.

    Usage:
        interpreter = Interpreter()
        interpreter.execute(program)
    """

    def __init__(self, strict_types: bool = False):
        # Global environment — lives for the entire program
        self.globals      = Environment()
        self.env          = self.globals
        self.strict_types = strict_types

        # Type registry: tracks declared type of each variable name
        # { var_name: type_hint_str }  — populated on first typed assignment
        self._type_registry: dict = {}

        # Line tracker — updated as statements execute, used by error display
        self._current_line: int = 0

        # Built-in functions available everywhere in NEKOVA
        self._register_builtins()

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def execute(self, program: Program, filepath: str = None):
        """Execute a full NEKOVA program."""
        if filepath:
            self._current_file = filepath
        if not hasattr(self, '_imported_files'):
            self._imported_files = set()
        for statement in program.statements:
            # Track line for error display (tokens carry line, nodes don't yet)
            if hasattr(statement, "line"):
                self._current_line = statement.line
            try:
                self._execute_node(statement)
            except (TypeError, ZeroDivisionError, IndexError,
                    KeyError, RecursionError) as e:
                # Attach current line so runner's display_error can use it
                if not hasattr(e, "line"):
                    e.line = self._current_line
                raise

    # ----------------------------------------------------------
    # Node dispatcher
    # ----------------------------------------------------------

    def _execute_node(self, node):
        """
        Route a node to its matching execute method.
        This is the heart of the interpreter.
        """
        if isinstance(node, AsyncFunctionNode):
            return self.visit_async_function(node)
        if isinstance(node, AwaitNode):
            return self._run_sync(self.visit_await(node))
        if isinstance(node, StreamThinkNode):
            return self.visit_stream_think(node)
        if isinstance(node, FetchNode):
            return self.visit_fetch(node)

        method_name = f"_exec_{type(node).__name__}"
        method      = getattr(self, method_name, None)

        if method is None:
            raise NEKOVARuntimeError(
                f"NEKOVA doesn't know how to execute "
                f"'{type(node).__name__}' yet."
            )

        return method(node)

    # ----------------------------------------------------------
    # Statement executors
    # ----------------------------------------------------------

    def _exec_Program(self, node: Program):
        for stmt in node.statements:
            self._execute_node(stmt)

    # Type hint mapping — NEKOVA type names to Python types
    _TYPE_MAP = {
        "text":    str,
        "number":  (int, float),
        "boolean": bool,
        "list":    list,
        "dict":    dict,
        "any":     None,   # any = no check
    }

    def _exec_AssignStatement(self, node: AssignStatement):
        """
        Execute:  let name: type = value
                  name = value

        Type checking behaviour:
          - Always enforced when a type hint is declared on the assignment.
          - strict_types=True additionally:
              • Tracks declared types across re-assignments.
              • Raises on re-assignment if the new value's type doesn't match
                the originally declared type, even without a hint on the
                re-assignment.
              • Raises on untyped assignments that change the type of an
                already-declared variable.
        """
        value = self._execute_node(node.value)

        # Deep copy mutable values to prevent aliasing bugs
        if isinstance(value, (dict, list)):
            import copy
            value = copy.deepcopy(value)

        hint = node.type_hint  # may be None

        # ── 1. Explicit type hint on this assignment ──────────────────────────
        if hint:
            if hint != "any":
                expected = self._TYPE_MAP.get(hint)
                if expected is not None and not isinstance(value, expected):
                    actual = type(value).__name__
                    raise TypeError(
                        f"Type error on '{node.name}': "
                        f"expected '{hint}', got '{actual}'.\n"
                        f"  Hint: use 'any' to allow any type."
                    )
            # Register declared type (including "any") for future strict checks
            self._type_registry[node.name] = hint

        # ── 2. strict_types re-assignment check ───────────────────────────────
        elif self.strict_types and node.name in self._type_registry:
            declared = self._type_registry[node.name]
            if declared != "any":
                expected = self._TYPE_MAP.get(declared)
                if expected is not None and not isinstance(value, expected):
                    actual = type(value).__name__
                    raise TypeError(
                        f"Type error on '{node.name}': "
                        f"variable was declared as '{declared}', "
                        f"cannot assign '{actual}'.\n"
                        f"  Tip: disable strict_types in nekova.toml to allow dynamic typing."
                    )
            # declared == "any" → skip all checks, any value is fine

        # ── 3. strict_types untyped assignment that changes type ──────────────
        # Only applies when the variable has NO type declaration at all
        elif self.strict_types and node.name not in self._type_registry and node.name in self.env:
            try:
                current = self.env[node.name]
                if type(current) != type(value) and value is not None:
                    current_t = type(current).__name__
                    new_t     = type(value).__name__
                    raise TypeError(
                        f"Type error on '{node.name}': "
                        f"cannot change type from '{current_t}' to '{new_t}' "
                        f"in strict mode.\n"
                        f"  Declare a type hint or set strict_types = false in nekova.toml."
                    )
            except (NameError, KeyError):
                pass  # variable doesn't exist yet — first assignment is fine

        self.env[node.name] = value
        return value

    def _exec_ShowStatement(self, node: ShowStatement):
        """Execute:  show <expression>"""
        value = self._execute_node(node.expression)
        print(self._to_string(value))
        return value
    
    def _exec_ThinkStatement(self, node):
        """Execute a think statement — calls the active AI provider."""
        from colorama import Fore, Style, init
        init(autoreset=True)

        # Step 1: Evaluate the prompt
        prompt = self._execute_node(node.prompt)
        prompt = str(prompt)

        # Step 2: Call the AI provider
        try:
            from nekova.ai.providers import get_provider
            provider = get_provider()
            response = provider.ask(prompt)
        except Exception as e:
            response = f"[think error: {e}]"

        # Step 3: Print with cyan formatting
        print(f"{Fore.CYAN}🧠 {response}{Style.RESET_ALL}")

        # Step 4: Store in variable if captured
        if node.variable:
            self.env.set(node.variable, response)

        return response
    
    def _exec_PipelineStatement(self, node: PipelineStatement):
        """
        Execute an agent communication pipeline.
        Output flows left to right through each step.

        researcher -> marketer -> reporter
        "Analyze this" -> researcher -> writer
        """
        from colorama import Fore, Style, init
        from nekova.parser.nodes import Identifier
        init(autoreset=True)

        try:
            from nekova.ai.providers import get_provider
            provider = get_provider()
        except Exception as e:
            print(f"{Fore.RED}Pipeline error: could not load AI provider: {e}{Style.RESET_ALL}")
            return None

        current_output = None

        for i, step in enumerate(node.steps):
            # Safely evaluate the step —
            # undefined identifiers become agent role names
            if isinstance(step, Identifier):
                try:
                    value = self._execute_node(step)
                except (NEKOVANameError, NameError, KeyError):
                    value = step.name
            else:
                value = self._execute_node(step)

            # First step: only treat as seed if it came from a string literal
            from nekova.parser.nodes import StringLiteral
            if i == 0 and isinstance(step, StringLiteral) and len(node.steps) > 1:
                current_output = value
                print(f"{Fore.YELLOW}⟶ Seed: {current_output}{Style.RESET_ALL}")
                continue

            # Determine the agent role name
            if hasattr(value, 'run'):
                role = getattr(value, 'name', str(value))
            elif isinstance(value, str):
                role = value
            elif isinstance(step, Identifier):
                role = step.name
            else:
                role = str(value)

            # Build the prompt for this agent
            if current_output:
                agent_prompt = (
                    f"You are a {role}. "
                    f"Here is the input from the previous step:\n\n"
                    f"{current_output}\n\n"
                    f"Respond as a {role} would."
                )
            else:
                agent_prompt = f"You are a {role}. Begin your work."

            # Call the AI provider
            try:
                response = provider.ask(agent_prompt)
            except Exception as e:
                response = f"[{role} error: {e}]"

            current_output = response

            # Print with pipeline formatting
            print(f"{Fore.MAGENTA}🤖 [{role}]{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{current_output}{Style.RESET_ALL}")
            print(f"{Style.DIM}{'─' * 50}{Style.RESET_ALL}")

        # Store final output if captured
        if node.variable:
            self.env.set(node.variable, current_output)

        return current_output
    
    def _exec_ModelStatement(self, node: ModelStatement):
        """
        Execute:  model "gemini" / model "claude" / model "mock"
        Switches the active AI provider for all subsequent
        think and pipeline calls.
        """
        from colorama import Fore, Style, init
        init(autoreset=True)

        # Evaluate the provider name expression
        provider_name = self._execute_node(node.provider)
        provider_name = str(provider_name).strip().lower()

        # Attempt to switch the provider
        try:
            from nekova.ai.providers import set_provider
            set_provider(provider_name)
            print(f"{Fore.GREEN}✓ Model switched to '{provider_name}'{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Could not switch to '{provider_name}': {e}{Style.RESET_ALL}")
    
    def _exec_ParallelStatement(self, node: ParallelStatement):
        """
        Execute all statements in the body simultaneously
        using threads. Collects and returns all results.

        autonomous parallel:
            think "Research market"
            think "Analyze competitors"
            think "Generate report"
        """
        from colorama import Fore, Style, init
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        init(autoreset=True)

        print(f"{Fore.YELLOW}⚡ Running {len(node.body)} tasks in parallel...{Style.RESET_ALL}")

        results = [None] * len(node.body)
        lock = threading.Lock()

        def run_task(index, stmt):
            """Run a single statement and capture its result."""
            try:
                # Each thread gets its own environment snapshot
                result = self._execute_node(stmt)
                with lock:
                    results[index] = result
                return index, result
            except Exception as e:
                with lock:
                    results[index] = f"[parallel error: {e}]"
                return index, None

        # Run all tasks simultaneously
        with ThreadPoolExecutor(max_workers=len(node.body)) as executor:
            futures = {
                executor.submit(run_task, i, stmt): i
                for i, stmt in enumerate(node.body)
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                index, result = future.result()
                print(
                    f"{Fore.YELLOW}⚡ Task {index + 1} of "
                    f"{len(node.body)} complete{Style.RESET_ALL}"
                )

        print(f"{Fore.GREEN}✓ All {len(node.body)} parallel tasks done{Style.RESET_ALL}")

        # Store results list if captured
        if node.variable:
            self.env.set(node.variable, results)

        return results
    
    def _exec_MemoryStatement(self, node: MemoryStatement):
        """
        Execute a persistent memory block.
        Data is saved to disk and reloaded between runs.

        memory user_profile:
            name = "Emmanuel"
            run_count = 0
        """
        import json
        import os
        from colorama import Fore, Style, init
        init(autoreset=True)

        # Memory files stored in .NEKOVAmem/ folder
        mem_dir = ".NEKOVAmem"
        os.makedirs(mem_dir, exist_ok=True)
        mem_file = os.path.join(mem_dir, f"{node.name}.json")

        # Step 1: Load existing data from disk if it exists
        saved_data = {}
        if os.path.isfile(mem_file):
            try:
                with open(mem_file, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                print(
                    f"{Style.DIM}💾 memory '{node.name}' "
                    f"loaded from disk{Style.RESET_ALL}"
                )
            except Exception:
                saved_data = {}

        # Step 2: Execute body statements to get default values
        # Use a temporary environment to capture assignments
        from nekova.interpreter.environment import Environment
        temp_env = Environment(parent=self.env)
        prev_env = self.env
        self.env = temp_env

        try:
            for stmt in node.body:
                self._execute_node(stmt)
        finally:
            self.env = prev_env

        # Step 3: Build final data —
        # saved values take priority over defaults
        default_data = {}
        for key in temp_env.variables:
            default_data[key] = temp_env.variables[key]

        # Merge: saved data wins over defaults
        final_data = {**default_data, **saved_data}

        # Step 4: Save back to disk
        try:
            with open(mem_file, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2,
                          default=str)
        except Exception as e:
            print(
                f"{Fore.RED}💾 memory save error: "
                f"{e}{Style.RESET_ALL}"
            )

        # Step 5: Store in environment as a dict
        self.env.set(node.name, final_data)

        return final_data
    
    def _exec_SandboxStatement(self, node: SandboxStatement):
        """
        Execute a sandboxed block with restricted permissions.

        strict  — blocks file system, system commands, network
        relaxed — allows read-only files, blocks writes/system
        """
        from colorama import Fore, Style, init
        init(autoreset=True)

        mode = node.mode
        print(f"{Fore.YELLOW}🔒 Sandbox [{mode}] activated{Style.RESET_ALL}")

        # ── Define what's blocked in each mode ────────────────
        strict_blocked = {
            "write_file":   "file writes",
            "read_file":    "file reads",
            "file_exists":  "file system access",
        }

        relaxed_blocked = {
            "write_file":   "file writes",
        }

        blocked = strict_blocked if mode == "strict" else relaxed_blocked

        # ── Save original functions ────────────────────────────
        saved = {}
        for func_name in blocked:
            try:
                saved[func_name] = self.env.get(func_name)
            except Exception:
                saved[func_name] = None

        # ── Install sandbox blockers ───────────────────────────
        def make_blocker(name, reason):
            def blocked_fn(*args, **kwargs):
                raise NEKOVARuntimeError(
                    f"🔒 Sandbox [{mode}] blocked: "
                    f"'{name}' — {reason} not allowed.\n"
                    f"  Use 'sandbox relaxed' for read-only access."
                )
            return blocked_fn

        for func_name, reason in blocked.items():
            self.env.set(func_name, make_blocker(func_name, reason))

        # ── Also block dangerous Python builtins ──────────────
        import builtins
        original_open = builtins.open
        original_import = builtins.__import__

        if mode == "strict":
            def safe_open(*args, **kwargs):
                raise NEKOVARuntimeError(
                    "🔒 Sandbox [strict] blocked: "
                    "file access not allowed."
                )
            builtins.open = safe_open

        # ── Execute the sandboxed body ─────────────────────────
        try:
            self._execute_block(node.body)
            print(
                f"{Fore.GREEN}🔒 Sandbox [{mode}] "
                f"completed safely{Style.RESET_ALL}"
            )

        except NEKOVARuntimeError as e:
            error_msg = str(e)
            if "Sandbox" in error_msg:
                print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            else:
                raise

        finally:
            # ── Always restore everything ──────────────────────
            builtins.open = original_open

            for func_name, original in saved.items():
                if original is not None:
                    self.env.set(func_name, original)
                    
        return None
    
    def _exec_PipelineDefStatement(self, node: PipelineDefStatement):
        """
        Execute a pipeline definition — stores it for later use.

        pipeline market_analysis:
            collect "Nigerian fintech"
            process with ai
            generate report
            save to database
        """
        # Store the pipeline definition in the environment
        self.env.set(f"__pipeline_{node.name}__", node)
        from colorama import Fore, Style, init
        init(autoreset=True)
        print(f"{Fore.CYAN}⚡ Pipeline '{node.name}' defined "
              f"({len(node.steps)} steps){Style.RESET_ALL}")
        return node

    def _exec_RunPipelineStatement(self, node: RunPipelineStatement):
        """
        Execute a named pipeline.

        run pipeline market_analysis
        result = run pipeline market_analysis
        """
        from colorama import Fore, Style, init
        init(autoreset=True)

        # Look up the pipeline definition
        try:
            pipeline = self.env.get(
                f"__pipeline_{node.name}__")
        except Exception:
            raise NEKOVARuntimeError(
                f"Pipeline '{node.name}' is not defined.\n"
                f"  Define it first with:  pipeline {node.name}:"
            )

        print(f"{Fore.CYAN}🧠 Running pipeline "
              f"'{node.name}'...{Style.RESET_ALL}")

        current_data = None
        final_result = None

        for i, step in enumerate(pipeline.steps):
            step_type = step["type"]
            step_num  = i + 1
            total     = len(pipeline.steps)

            print(f"{Style.DIM}  Step {step_num}/{total}: "
                  f"{step_type}...{Style.RESET_ALL}")

            # ── collect ───────────────────────────────────────
            if step_type == "collect":
                current_data = self._execute_node(
                    step["expr"])
                current_data = str(current_data)
                print(f"{Style.DIM}  📥 Collected: "
                      f"{current_data[:80]}..."
                      if len(str(current_data)) > 80
                      else f"{Style.DIM}  📥 Collected: "
                           f"{current_data}{Style.RESET_ALL}")

            # ── process with ai ───────────────────────────────
            elif step_type == "process":
                try:
                    from nekova.ai.providers import get_provider
                    provider = get_provider()
                    prompt = (
                        f"Analyze and process the following:\n\n"
                        f"{current_data}\n\n"
                        f"Provide a detailed analysis."
                    )
                    current_data = provider.ask(prompt)
                    print(f"{Fore.GREEN}  🤖 AI processed "
                          f"({len(current_data)} chars)"
                          f"{Style.RESET_ALL}")
                except Exception as e:
                    current_data = f"[process error: {e}]"
                    print(f"{Fore.RED}  ✗ Process failed: "
                          f"{e}{Style.RESET_ALL}")

            # ── generate report ───────────────────────────────
            elif step_type == "generate":
                fmt = step.get("format", "report")
                try:
                    from nekova.ai.providers import get_provider
                    provider = get_provider()
                    prompt = (
                        f"Format the following as a professional "
                        f"{fmt}:\n\n{current_data}"
                    )
                    current_data = provider.ask(prompt)
                    print(f"{Fore.GREEN}  📄 Generated "
                          f"{fmt} ({len(current_data)} chars)"
                          f"{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}  ✗ Generate failed: "
                          f"{e}{Style.RESET_ALL}")

            # ── save to database ──────────────────────────────
            elif step_type == "save":
                target = step.get("target", "database")
                try:
                    import json
                    import os
                    os.makedirs(".NEKOVAmem", exist_ok=True)
                    save_path = os.path.join(
                        ".NEKOVAmem",
                        f"pipeline_{node.name}.json"
                    )
                    save_data = {
                        "pipeline": node.name,
                        "result":   current_data,
                        "target":   target,
                    }
                    with open(save_path, "w",
                              encoding="utf-8") as f:
                        json.dump(save_data, f, indent=2)
                    print(f"{Fore.GREEN}  💾 Saved to "
                          f"'{save_path}'"
                          f"{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}  ✗ Save failed: "
                          f"{e}{Style.RESET_ALL}")

            final_result = current_data

        print(f"{Fore.CYAN}✓ Pipeline '{node.name}' "
              f"complete{Style.RESET_ALL}")

        # Store result if captured
        if node.variable:
            self.env.set(node.variable, final_result)

        return final_result

    def _exec_IfStatement(self, node: IfStatement):
        """
        Execute:
            if <condition>:
                <then_body>
            else:
                <else_body>
        """
        condition = self._execute_node(node.condition)

        if self._is_truthy(condition):
            self._execute_block(node.then_body)
        else:
            self._execute_block(node.else_body)

    def _exec_RepeatStatement(self, node: RepeatStatement):
        """
        Execute:
            repeat <count>:
                <body>
        """
        count = self._execute_node(node.count)

        if not isinstance(count, (int, float)):
            raise NEKOVARuntimeError(
                f"'repeat' needs a number, not '{count}'.\n"
                f"  Example:  repeat 5:"
            )

        for _ in range(int(count)):
            self._execute_block(node.body)
    
    def _exec_WhileStatement(self, node: WhileStatement):
        """
        Execute:
            while <condition>:
                <body>
        """
        max_iterations = 10000
        count = 0

        while self._is_truthy(
                self._execute_node(node.condition)):
            # No new scope — variables update in current scope
            self._execute_block(node.body, new_scope=False)
            count += 1
            if count >= max_iterations:
                raise NEKOVARuntimeError(
                    "While loop ran too many times.\n"
                    "  Check your loop condition."
                )
    
    def _exec_TryStatement(self, node: TryStatement):
        """
        Execute:
            try:
                <body>
            catch error:
                <handler>
        """
        try:
            self._execute_block(node.try_body)

        except Exception as e:
            # Store error message in variable if specified
            if node.error_var:
                error_msg = str(e).strip()
                # Clean up internal Python paths
                if "\n" in error_msg:
                    error_msg = error_msg.split("\n")[-1].strip()
                self.env.set(node.error_var, error_msg)

            # Execute catch body
            self._execute_block(node.catch_body)
    
    def _exec_ForStatement(self, node: ForStatement):
        """
        Execute:
            for item in items:
                <body>
        """
        iterable = self._execute_node(node.iterable)

        # Support lists, strings, dicts and ranges
        if isinstance(iterable, str):
            items = list(iterable)
        elif isinstance(iterable, dict):
            items = list(iterable.keys())
        elif isinstance(iterable, list):
            items = iterable
        elif isinstance(iterable, range):
            items = list(iterable)
        else:
            raise NEKOVARuntimeError(
                f"Cannot iterate over "
                f"'{type(iterable).__name__}'.\n"
                f"  Use a list, string, or range."
            )

        for item in items:
            # Set loop variable in current scope
            self.env.set(node.variable, item)
            # Execute body without new scope so
            # loop variable is accessible
            self._execute_block(
                node.body, new_scope=False)

    def _exec_TaskStatement(self, node: TaskStatement):
        """
        Execute:  task greet(name): ...
        Stores the task definition in the environment.
        The task body is NOT executed yet — only when called.
        """
        self.env.set(node.name, node)

    def _exec_ReturnStatement(self, node: ReturnStatement):
        """
        Execute:  return <value>
        Raises ReturnSignal to unwind the call stack.
        """
        value = None
        if node.value is not None:
            value = self._execute_node(node.value)
        raise ReturnSignal(value)

    def _exec_UseStatement(self, node: UseStatement):
        module_name = node.module
        from nekova.stdlib import load_module
        try:
            stdlib = load_module(module_name)
            for name, func in stdlib.items():
                self.env.set(name, func)
        except ImportError as e:
            raise NEKOVAImportError(str(e))
    
    def _exec_ImportStatement(self, node: ImportStatement):
        """
        Execute import statements in three forms:

            import "utils.nk"
                — executes file, all names enter current scope

            import greet from "utils.nk"
                — imports only 'greet' from the file

            import greet, add from "utils.nk"
                — imports multiple named exports
        """
        import os

        filepath = node.filepath

        # Auto-add .nk extension if missing
        if not filepath.endswith(".nk") and "." not in os.path.basename(filepath):
            filepath = filepath + ".nk"

        # Resolve relative to the current file if possible
        if (not os.path.isabs(filepath) and
                hasattr(self, '_current_file') and
                self._current_file):
            base_dir = os.path.dirname(self._current_file)
            filepath = os.path.join(base_dir, filepath)

        # Also search in current working directory
        if not os.path.isfile(filepath):
            cwd_path = os.path.join(os.getcwd(), filepath)
            if os.path.isfile(cwd_path):
                filepath = cwd_path

        # Check file exists
        if not os.path.isfile(filepath):
            raise NEKOVARuntimeError(
                f"Cannot import '{node.filepath}'.\n"
                f"  File not found: '{filepath}'\n"
                f"  Make sure the file exists and the path is correct."
            )

        # Prevent circular imports
        if not hasattr(self, '_imported_files'):
            self._imported_files = set()

        abs_path = os.path.abspath(filepath)
        if abs_path in self._imported_files:
            return  # Already imported — skip silently

        self._imported_files.add(abs_path)

        # Load and execute the file in an isolated child environment
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            from nekova.lexer import Lexer
            from nekova.parser.parser import Parser
            from nekova.interpreter.environment import Environment

            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()

            # Execute in a child environment to isolate the module
            child_env  = Environment(parent=self.globals)
            prev_env   = self.env
            prev_file  = getattr(self, '_current_file', None)

            self.env           = child_env
            self._current_file = abs_path

            for stmt in program.statements:
                self._execute_node(stmt)

            self.env           = prev_env
            self._current_file = prev_file

            # Bring names into current scope
            if node.names is None:
                # Star import — bring everything into scope
                for name, value in child_env.variables.items():
                    self.env.set(name, value)
            else:
                # Named import — only bring requested names
                for name in node.names:
                    try:
                        value = child_env.get(name)
                        self.env.set(name, value)
                    except Exception:
                        available = list(child_env.variables.keys())
                        raise NEKOVARuntimeError(
                            f"Cannot import '{name}' from '{node.filepath}'.\n"
                            f"  '{name}' is not defined in that file.\n"
                            f"  Available names: {available}"
                        )

            from nekova.config import Color
            if node.names:
                names_str = ", ".join(node.names)
                print(f"{Color.DIM}→ imported {names_str} from '{node.filepath}'{Color.RESET}")
            else:
                print(f"{Color.DIM}→ imported '{node.filepath}'{Color.RESET}")

        except NEKOVARuntimeError:
            raise
        except Exception as e:
            raise NEKOVARuntimeError(
                f"Error importing '{node.filepath}':\n"
                f"  {e}"
            )

    def _exec_CallExpression(self, node: CallExpression):
        """
        Execute:  greet("Emmanuel")
        Looks up the task and runs it with the given arguments.
        """
        # Check built-ins first
        callee = self.env.get(node.name)

        # Evaluate all arguments
        args = [self._execute_node(arg) for arg in node.args]

        # Built-in Python function
        if callable(callee) and not isinstance(callee, TaskStatement):
            return callee(*args)

        # NEKOVA task
        if isinstance(callee, TaskStatement):
            return self._call_task(callee, args)

        # NEKOVA async task
        from nekova.interpreter.async_interpreter import AsyncFunction as _AsyncFn
        if isinstance(callee, _AsyncFn):
            import asyncio
            try:
                asyncio.get_running_loop()
                return callee.call_async(args)  # return coroutine to outer await
            except NEKOVARuntimeError:
                return self._run_sync(callee.call_async(args))

        raise NEKOVARuntimeError(
            f"'{node.name}' is not a task you can call.\n"
            f"  Define it first with:  task {node.name}(...):"
        )

    # ----------------------------------------------------------
    # Expression evaluators
    # ----------------------------------------------------------

    def _exec_BinaryOp(self, node: BinaryOp):
        """Evaluate a binary operation like age + 1 or x == y."""
        left  = self._execute_node(node.left)
        right = self._execute_node(node.right)
        op    = node.operator

        try:
            if op == "+":
                # Support string concatenation
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_string(left) + self._to_string(right)
                return left + right
            if op == "-":  return left - right
            if op == "*":  return left * right
            if op == "/":
                if right == 0:
                    raise NEKOVARuntimeError(
                        "Cannot divide by zero.\n"
                        "  Check your divisor value."
                    )
                return left / right
            if op == "%":  return left % right
            if op == "**": return left ** right
            if op == "==": return left == right
            if op == "!=": return left != right
            if op == "<":  return left <  right
            if op == "<=": return left <= right
            if op == ">":  return left >  right
            if op == ">=": return left >= right

        except TypeError:
            raise NEKOVARuntimeError(
                f"Cannot use '{op}' between "
                f"'{type(left).__name__}' and '{type(right).__name__}'.\n"
                f"  Check that both values are the right type."
            )

        raise NEKOVARuntimeError(f"Unknown operator '{op}'.")

    def _exec_UnaryOp(self, node: UnaryOp):
        """Evaluate a unary operation like -x or not true."""
        operand = self._execute_node(node.operand)

        if node.operator == "-":
            return -operand
        if node.operator == "not":
            return not self._is_truthy(operand)

        raise NEKOVARuntimeError(f"Unknown operator '{node.operator}'.")

    # ── Literals ──────────────────────────────────────────────

    def _exec_IntegerLiteral(self, node: IntegerLiteral):
        return node.value

    def _exec_FloatLiteral(self, node: FloatLiteral):
        return node.value

    def _exec_StringLiteral(self, node: StringLiteral):
        """
        Execute a string literal.
        Supports interpolation: "Hello {name}!"
        """
        import re
        value = node.value

        # Find all {variable} patterns
        def replace_var(match):
            var_name = match.group(1).strip()
            try:
                val = self.env.get(var_name)
                return self._to_string(val)
            except Exception:
                return match.group(0)

        return re.sub(r'\{(\w+)\}', replace_var, value)

    def _exec_BooleanLiteral(self, node: BooleanLiteral):
        return node.value

    def _exec_FStringLiteral(self, node: FStringLiteral):
        """
        Execute an f-string literal.
        Each part is either ('str', text) or ('expr', AST node).
        Expressions are evaluated and converted to strings.

        Example:
            f"Hello {name}, you scored {score * 2}!"
        """
        result = []
        for kind, val in node.parts:
            if kind == 'str':
                result.append(val)
            else:
                # Evaluate the expression and convert to string
                try:
                    evaluated = self._execute_node(val)
                    result.append(self._to_string(evaluated))
                except Exception as e:
                    result.append(f"{{error: {e}}}")
        return "".join(result)

    def _exec_NullLiteral(self, node: NullLiteral):
        return None
    
    def _exec_ListLiteral(self, node: ListLiteral):
        """Execute a list literal like [1, 2, 3]."""
        return [self._execute_node(e) for e in node.elements]
    
    def _exec_DictLiteral(self, node: DictLiteral):
        """Execute a dictionary literal."""
        result = {}
        for key_node, value_node in node.pairs:
            key   = self._execute_node(key_node)
            value = self._execute_node(value_node)
            result[str(key)] = value
        # Return a copy to prevent mutation
        return dict(result)
    
    def _exec_IndexExpression(self,
                               node: IndexExpression):
        """Execute list/dict indexing."""
        collection = self._execute_node(node.collection)
        index      = self._execute_node(node.index)

        try:
            if isinstance(collection, dict):
                key = str(index)
                if key not in collection:
                    raise NEKOVARuntimeError(
                        f"Key '{key}' not found "
                        f"in dictionary.\n"
                        f"  Available keys: "
                        f"{list(collection.keys())}"
                    )
                return collection[key]
            return collection[int(index)]
        except IndexError:
            raise NEKOVARuntimeError(
                f"Index {index} is out of range.\n"
                f"  List has {len(collection)} items."
            )
        except TypeError:
            raise NEKOVARuntimeError(
                f"Cannot index into "
                f"'{type(collection).__name__}'."
            )
    
    def _exec_PropertyAccess(self, node: PropertyAccess):
        """
        Execute property access: obj.prop (no parentheses).

        Supports:
          - ArgsObject:    args.name, args.port
          - FetchResponse: res.status, res.ok, res.text
          - Any Python object with __getattr__
          - Dict key access as fallback: obj["prop"]
        """
        obj  = self._execute_node(node.object)
        prop = node.property

        # NEKOVA class instances — check first
        from nekova.interpreter.nekova_class import NEKOVAInstance
        if isinstance(obj, NEKOVAInstance):
            return obj.get_attr(prop)

        # ArgsObject and FetchResponse use __getattr__
        if hasattr(obj, prop):
            value = getattr(obj, prop)
            return value

        # Dict fallback: treat prop as key
        if isinstance(obj, dict):
            if prop in obj:
                return obj[prop]
            raise KeyError(
                f"Key '{prop}' not found in dict. "
                f"Available keys: {list(obj.keys())}"
            )

        raise AttributeError(
            f"'{type(obj).__name__}' has no property '{prop}'."
        )

    def _exec_MethodCall(self, node: MethodCall):
        """Execute a method call like name.upper()."""
        obj    = self._execute_node(node.object)
        method = node.method
        args   = [self._execute_node(a) for a in node.args]

        # ── String methods ────────────────────────────────
        if isinstance(obj, str):
            methods = {
                "upper":      lambda: obj.upper(),
                "lower":      lambda: obj.lower(),
                "title":      lambda: obj.title(),
                "strip":      lambda: obj.strip(),
                "trim":       lambda: obj.strip(),
                "reverse":    lambda: obj[::-1],
                "length":     lambda: len(obj),
                "split":      lambda: obj.split(
                                  args[0] if args else " "),
                "replace":    lambda: obj.replace(
                                  args[0], args[1]),
                "contains":   lambda: args[0] in obj,
                "starts_with": lambda: obj.startswith(
                                  args[0]),
                "ends_with":  lambda: obj.endswith(
                                  args[0]),
                "find":       lambda: obj.find(args[0]),
                "count":      lambda: obj.count(args[0]),
                "repeat":     lambda: obj * int(args[0]),
            }

            if method in methods:
                return methods[method]()

            raise NEKOVARuntimeError(
                f"String has no method '{method}'.\n"
                f"  Available: "
                f"{', '.join(methods.keys())}"
            )

        # ── List methods ──────────────────────────────────
        if isinstance(obj, list):
            methods = {
                "length":   lambda: len(obj),
                "append":   lambda: obj.append(args[0]),
                "remove":   lambda: obj.remove(args[0]),
                "reverse":  lambda: list(reversed(obj)),
                "sort":     lambda: sorted(obj),
                "first":    lambda: obj[0] if obj else None,
                "last":     lambda: obj[-1] if obj else None,
                "contains": lambda: args[0] in obj,
                "join":     lambda: (args[0] if args
                                else ", ").join(
                                [str(i) for i in obj]),
                "pop":      lambda: obj.pop(),
                "clear":    lambda: obj.clear(),
            }

            if method in methods:
                return methods[method]()

            raise NEKOVARuntimeError(
                f"List has no method '{method}'.\n"
                f"  Available: "
                f"{', '.join(methods.keys())}"
            )

        # ── Dict methods ──────────────────────────────────
        if isinstance(obj, dict):
            methods = {
                "keys":     lambda: list(obj.keys()),
                "values":   lambda: list(obj.values()),
                "length":   lambda: len(obj),
                "has":      lambda: args[0] in obj,
                "get":      lambda: obj.get(
                                args[0],
                                args[1] if len(args) > 1
                                else None),
                "remove":   lambda: obj.pop(args[0], None),
            }

            if method in methods:
                return methods[method]()

            raise NEKOVARuntimeError(
                f"Dictionary has no method '{method}'.\n"
                f"  Available: "
                f"{', '.join(methods.keys())}"
            )

        # ── NEKOVAInstance method call ──────────────────────────────────────
        from nekova.interpreter.nekova_class import NEKOVAInstance
        if isinstance(obj, NEKOVAInstance):
            return self._call_instance_method(obj, node.method, args)

        # ── Generic Python object fallback (ArgsObject, FetchResponse, etc.) ──
        method_fn = getattr(obj, node.method, None)
        if method_fn is not None and callable(method_fn):
            return method_fn(*args)

        raise NEKOVARuntimeError(
            f"'{type(obj).__name__}' has no method '{node.method}'."
        )

    def _exec_Identifier(self, node: Identifier):
        """Look up a variable's value in the current scope."""
        try:
            return self.env.get(node.name)
        except NameError as e:
            raise NEKOVANameError(str(e))

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------


    # -- Bridge methods for AsyncInterpreterMixin -----------------
    def visit(self, node):
        return self._execute_node(node)

    def execute_block(self, body, env=None):
        if env is not None:
            previous = self.env
            from nekova.interpreter.environment import Environment
            new_env = Environment(parent=self.env)
            for k, v in env.items():
                new_env.set(k, v)
            self.env = new_env
            try:
                return self._execute_block(body, new_scope=False)
            finally:
                self.env = previous
        return self._execute_block(body)

    # -- End bridge methods ----------------------------------------

    def _execute_block(self, statements: list,
                       new_scope: bool = True):
        """
        Execute a list of statements.
        new_scope=False keeps variables in the current scope.
        Used by while loops so counter updates propagate.
        """
        if new_scope:
            previous = self.env
            self.env = Environment(parent=previous)
        try:
            for stmt in statements:
                self._execute_node(stmt)
        finally:
            if new_scope:
                self.env = previous

    def _call_task(self, task: TaskStatement, args: list):
        """
        Execute a task with the given arguments.
        Creates a fresh local scope for the task.
        """
        if len(args) != len(task.params):
            raise NEKOVARuntimeError(
                f"Task '{task.name}' expects "
                f"{len(task.params)} argument(s) "
                f"but got {len(args)}."
            )

        # Create a new local scope with params as variables
        local_env    = Environment(parent=self.globals)
        previous_env = self.env

        for param, value in zip(task.params, args):
            local_env.set(param, value)

        self.env = local_env

        try:
            for stmt in task.body:
                self._execute_node(stmt)
            return None

        except ReturnSignal as r:
            return r.value

        finally:
            self.env = previous_env

    def _is_truthy(self, value) -> bool:
        """
        Determine if a value is considered true in NEKOVA.
        Rules:
            null  → false
            false → false
            0     → false
            ""    → false
            everything else → true
        """
        if value is None:        return False
        if value is False:       return False
        if value == 0:           return False
        if value == "":          return False
        return True

    def _to_string(self, value) -> str:
        """Convert any NEKOVA value to a printable string."""
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, dict):
            pairs = []
            for k, v in value.items():
                pairs.append(f"{k}: {self._to_string(v)}")
            return "{" + ", ".join(pairs) + "}"
        if isinstance(value, list):
            items = [self._to_string(i) for i in value]
            return "[" + ", ".join(items) + "]"
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    def _register_builtins(self):
        """Register built-in functions available in all NEKOVA programs."""
        from nekova.cli.args_object import ArgsObject
        # Default empty args — overwritten by runner when CLI args are passed
        self.globals.set("args",      ArgsObject({}))
        self.globals.set("type_of",   lambda x: type(x).__name__)
        self.globals.set("to_number", lambda x: float(x)
                         if "." in str(x) else int(x))
        self.globals.set("to_text",   lambda x: str(x))
        self.globals.set("length",    lambda x: len(x))
        self.globals.set("ask",       lambda prompt="": input(str(prompt)))
        self.globals.set("clear",     lambda: print("\033[H\033[J", end=""))
        self.globals.set("sleep",     lambda s=1: __import__("time").sleep(float(s)))
        self.globals.set("random_num",lambda a, b: __import__("random").randint(int(a), int(b)))

    def _load_stdlib(self, name: str) -> dict:
        """
        Load a standard library module.
        Delegates to the stdlib package registry.
        """
        from nekova.stdlib import load_module
        try:
            return load_module(name)
        except ImportError:
            return None