# =============================================================
# AION Interpreter — Main Execution Engine
# =============================================================
# The Interpreter walks the AST tree and executes each node.
#
# Process:
#   1. Receive the root Program node
#   2. Execute each statement one by one
#   3. For each node type call the matching execute_ method
#   4. Return the result
#
# This is called a "tree-walk interpreter" — the simplest
# and most readable interpreter architecture possible.

from parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement,
    IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, UseStatement,
    ImportStatement, CallExpression, IndexExpression,
    MethodCall
)
from interpreter.environment import Environment
from runtime import ReturnSignal


class RuntimeError(Exception):
    """Raised when something goes wrong during execution."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")

class AIONImportError(Exception):
    """Raised when a module cannot be found."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class AIONNameError(Exception):
    """Raised when a variable is not found."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  {message}")


class Interpreter:
    """
    Executes an AION AST produced by the Parser.

    Usage:
        interpreter = Interpreter()
        interpreter.execute(program)
    """

    def __init__(self):
        # Global environment — lives for the entire program
        self.globals = Environment()
        self.env     = self.globals

        # Built-in functions available everywhere in AION
        self._register_builtins()

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def execute(self, program: Program,
                filepath: str = None):
        """Execute a full AION program."""
        if filepath:
            self._current_file  = filepath
        if not hasattr(self, '_imported_files'):
            self._imported_files = set()
        for statement in program.statements:
            self._execute_node(statement)

    # ----------------------------------------------------------
    # Node dispatcher
    # ----------------------------------------------------------

    def _execute_node(self, node):
        """
        Route a node to its matching execute method.
        This is the heart of the interpreter.
        """
        method_name = f"_exec_{type(node).__name__}"
        method      = getattr(self, method_name, None)

        if method is None:
            raise RuntimeError(
                f"AION doesn't know how to execute "
                f"'{type(node).__name__}' yet."
            )

        return method(node)

    # ----------------------------------------------------------
    # Statement executors
    # ----------------------------------------------------------

    def _exec_Program(self, node: Program):
        for stmt in node.statements:
            self._execute_node(stmt)

    def _exec_AssignStatement(self, node: AssignStatement):
        """Execute:  name = value"""
        value = self._execute_node(node.value)
        # Deep copy dicts and lists to prevent mutation
        if isinstance(value, dict):
            import copy
            value = copy.deepcopy(value)
        elif isinstance(value, list):
            import copy
            value = copy.deepcopy(value)
        self.env.set(node.name, value)
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
            from ai.providers import get_provider
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
        from parser.nodes import Identifier
        init(autoreset=True)

        try:
            from ai.providers import get_provider
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
                except (AIONNameError, NameError, KeyError):
                    value = step.name
            else:
                value = self._execute_node(step)

            # First step: only treat as seed if it came from a string literal
            from parser.nodes import StringLiteral
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
            from ai.providers import set_provider
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
            raise RuntimeError(
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
                raise RuntimeError(
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
            raise RuntimeError(
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
        from stdlib import load_module
        try:
            stdlib = load_module(module_name)
            for name, func in stdlib.items():
                self.env.set(name, func)
        except ImportError as e:
            raise AIONImportError(str(e))
    
    def _exec_ImportStatement(self,
                               node: ImportStatement):
        """
        Execute:  import "filepath.aion"
        Loads and executes another .aion file,
        making all its tasks and variables available
        in the current scope.
        """
        import os

        filepath = node.filepath

        # Resolve relative to the current file if possible
        if (not os.path.isabs(filepath) and
                hasattr(self, '_current_file') and
                self._current_file):
            base_dir = os.path.dirname(
                self._current_file)
            filepath = os.path.join(base_dir, filepath)

        # Check file exists
        if not os.path.isfile(filepath):
            raise RuntimeError(
                f"Cannot import '{node.filepath}'.\n"
                f"  File not found: '{filepath}'"
            )

        # Prevent circular imports
        if not hasattr(self, '_imported_files'):
            self._imported_files = set()

        abs_path = os.path.abspath(filepath)
        if abs_path in self._imported_files:
            return  # Already imported — skip

        self._imported_files.add(abs_path)

        # Load and execute the file
        try:
            with open(filepath, "r",
                      encoding="utf-8") as f:
                source = f.read()

            from lexer import Lexer
            from parser.parser import Parser

            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()

            # Execute in current scope so tasks/vars
            # are available to the importing file
            prev_file = getattr(
                self, '_current_file', None)
            self._current_file = abs_path

            for stmt in program.statements:
                self._execute_node(stmt)

            self._current_file = prev_file

            from config import Color
            print(f"{Color.DIM}→ imported "
                  f"'{node.filepath}'{Color.RESET}")

        except Exception as e:
            raise RuntimeError(
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

        # AION task
        if isinstance(callee, TaskStatement):
            return self._call_task(callee, args)

        raise RuntimeError(
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
                    raise RuntimeError(
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
            raise RuntimeError(
                f"Cannot use '{op}' between "
                f"'{type(left).__name__}' and '{type(right).__name__}'.\n"
                f"  Check that both values are the right type."
            )

        raise RuntimeError(f"Unknown operator '{op}'.")

    def _exec_UnaryOp(self, node: UnaryOp):
        """Evaluate a unary operation like -x or not true."""
        operand = self._execute_node(node.operand)

        if node.operator == "-":
            return -operand
        if node.operator == "not":
            return not self._is_truthy(operand)

        raise RuntimeError(f"Unknown operator '{node.operator}'.")

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
                    raise RuntimeError(
                        f"Key '{key}' not found "
                        f"in dictionary.\n"
                        f"  Available keys: "
                        f"{list(collection.keys())}"
                    )
                return collection[key]
            return collection[int(index)]
        except IndexError:
            raise RuntimeError(
                f"Index {index} is out of range.\n"
                f"  List has {len(collection)} items."
            )
        except TypeError:
            raise RuntimeError(
                f"Cannot index into "
                f"'{type(collection).__name__}'."
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

            raise RuntimeError(
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

            raise RuntimeError(
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

            raise RuntimeError(
                f"Dictionary has no method '{method}'.\n"
                f"  Available: "
                f"{', '.join(methods.keys())}"
            )

        raise RuntimeError(
            f"'{type(obj).__name__}' has no methods."
        )

    def _exec_Identifier(self, node: Identifier):
        """Look up a variable's value in the current scope."""
        try:
            return self.env.get(node.name)
        except NameError as e:
            raise AIONNameError(str(e))

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

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
            raise RuntimeError(
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
        Determine if a value is considered true in AION.
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
        """Convert any AION value to a printable string."""
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
        """Register built-in functions available in all AION programs."""
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
        from stdlib import load_module
        try:
            return load_module(name)
        except ImportError:
            return None