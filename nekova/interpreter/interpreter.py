from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, FStringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, TupleLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement,
    MemoryStatement, SandboxStatement, PipelineDefStatement, RunPipelineStatement, IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, BreakStatement, ContinueStatement, GlobalStatement, UnpackStatement, UseStatement,
    ListDestructureStatement, DictDestructureStatement, SpreadElement,
    EnumDefinition, SetLiteral, ConverseStatement,
    ImportStatement, CallExpression, IndexExpression, IndexAssignStatement,
    MethodCall,
    PropertyAccess,
    ClassDefinition, NewInstance, SelfAccess, SelfAssign,
    # Phase 7
    MatchStatement, MatchArm, RouteStatement, ServeStatement,
    # Phase 9
    ThinkAsStatement, RememberStatement, RecallStatement, ForgetStatement,
    # Phase 15
    SliceExpression, RaiseStatement, PassStatement, AssertStatement, TernaryExpression,
    # Phase 16
    SpeakStatement, ListenExpression, EveryStatement,
    TestBlock, ExpectStatement, ImagineStatement,
    ShapeDefinition, WatchStatement,
    # Phase 17
    YieldStatement, DecoratorStatement, ErrorDefinition, TypedTaskStatement,
    # Phase 21
    PromptStatement, RetryStatement,
    # Phase 22
    ObserveStatement, MockStatement,
)
from nekova.interpreter.environment import Environment
from nekova.runtime import ReturnSignal, BreakSignal, ContinueSignal
from nekova.parser.async_nodes import (
    AsyncFunctionNode, AwaitNode, StreamThinkNode, FetchNode
)
from nekova.interpreter.exceptions import (
    NEKOVARuntimeError, NEKOVAImportError, NEKOVANameError,
    NEKOVARaiseError, NEKOVAAssertionError, NEKOVARecursionError,
    _ExpectFailed, _YieldSignal
)
from nekova.interpreter.async_interpreter import AsyncInterpreterMixin
from nekova.interpreter.class_interpreter import ClassInterpreterMixin

# Phase 22: sentinel meaning "no mock active" — distinct from None,
# since `mock think as null` should be a legitimate mocked value.
_NO_MOCK = object()


class NEKOVAEnum:
    """
    Runtime value for a Phase 24 'enum' definition.
    Each member is a plain attribute evaluating to its own name as a
    string, so PropertyAccess's existing hasattr/getattr fallback
    handles 'Status.ACTIVE' with no changes needed there.
    """
    def __init__(self, name: str, members: list):
        self.__enum_name__ = name
        self.__members__ = list(members)
        for m in members:
            setattr(self, m, m)

    def __repr__(self):
        return f"<enum {self.__enum_name__}: {', '.join(self.__members__)}>"


class Interpreter(AsyncInterpreterMixin, ClassInterpreterMixin):
    """
    Executes a NEKOVA AST produced by the Parser.

    Usage:
        interpreter = Interpreter()
        interpreter.execute(program)
    """

    # NEKOVA-level call-depth safety limit (see _call_task). This is
    # independent of Python's own recursion limit — it's the number of
    # nested NEKOVA task calls we allow before raising a NEKOVARecursionError
    # with an honest, accurate depth count instead of letting Python's
    # RecursionError fire first with a misleading message.
    MAX_CALL_DEPTH = 500

    def __init__(self, strict_types: bool = False, debug_ai: bool = False):
        # Isolate this interpreter's memory from all other instances
        from nekova.ai.memory_store import init_interpreter_memory
        init_interpreter_memory()

        # Phase 25: --debug-ai — when set, every think call prints the
        # exact prompt sent to the provider (after memory/conversation
        # context is prepended), so you can see what a `think` line
        # actually asks the model, not just the response.
        self._debug_ai = debug_ai

        # Raise Python's own recursion limit so it never fires before our
        # own MAX_CALL_DEPTH check does. Each NEKOVA-level task call costs
        # several Python stack frames (dispatch, _call_task, statement
        # execution, expression evaluation), so we need real headroom.
        import sys as _sys
        needed = (self.MAX_CALL_DEPTH * 12) + 2000
        if _sys.getrecursionlimit() < needed:
            _sys.setrecursionlimit(needed)

        # NEKOVA-level call depth counter, incremented/decremented in
        # _call_task. This is what MAX_CALL_DEPTH is checked against.
        self._call_depth = 0

        # Phase 25: cumulative AI usage tracking, surfaced via the
        # ai_usage() builtin. Token counts are an estimate (roughly
        # 4 characters per token, the same rule of thumb most
        # providers' own docs use) since NEKOVA doesn't have access
        # to a real tokenizer for every possible provider.
        self._ai_usage = {"calls": 0, "tokens": 0}

        # Global environment — lives for the entire program
        self.globals      = Environment()
        self.env          = self.globals
        self.strict_types = strict_types

        # Type registry: tracks declared type of each variable name
        # { var_name: type_hint_str }  — populated on first typed assignment
        self._type_registry: dict = {}

        # Line tracker — updated as statements execute, used by error display
        self._current_line: int = 0

        # Set of variable names declared 'global' in the current task call.
        # Assignments to these names write directly to self.globals.
        self._global_names: set = set()

        # Sandbox mode — set by run_sandboxed() before execution
        # When True, AI/IO keywords raise a blocked error instead of executing
        self._sandbox_mode:       str  = ""    # "" | "strict" | "relaxed"
        self._sandbox_violations: list = []

        # Built-in functions available everywhere in NEKOVA
        self._register_builtins()

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def run(self, program: Program, filepath: str = None):
        """Alias for execute() for test compatibility."""
        return self.execute(program, filepath)

    def execute(self, program: Program, filepath: str = None):
        """Execute a full NEKOVA program."""
        if filepath:
            self._current_file = filepath
        if not hasattr(self, '_imported_files'):
            self._imported_files = set()
        for statement in program.statements:
            # All stamped nodes now carry .line directly
            if hasattr(statement, "line") and statement.line:
                self._current_line = statement.line
            try:
                self._execute_node(statement)
            except (TypeError, ZeroDivisionError, IndexError,
                    KeyError, RecursionError, NEKOVARecursionError) as e:
                # Attach current line so runner's display_error can use it
                if not hasattr(e, "line") or not e.line:
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
        # Update current line whenever a stamped node is executed
        # so error messages point to the exact source line
        if hasattr(node, "line") and node.line:
            self._current_line = node.line

        if isinstance(node, AsyncFunctionNode):
            return self.visit_async_function(node)
        if isinstance(node, AwaitNode):
            return self.visit_await(node)
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

        # Phase 24: const bindings — a const can be declared once; any
        # further plain assignment to that name in the same scope is a
        # runtime error. Checked against the scope we're about to write
        # to (global if declared 'global' in this task, else current).
        target_env = self.globals if node.name in self._global_names else self.env
        if not node.is_const and node.name in target_env.consts:
            raise NEKOVARuntimeError(
                f"Cannot reassign '{node.name}' — it was declared "
                f"with 'const' and consts can't be changed after "
                f"they're set.\n"
                f"  Use 'let {node.name} = ...' instead if you need "
                f"it to change."
            )
        if node.is_const and node.name in target_env.variables:
            raise NEKOVARuntimeError(
                f"'{node.name}' is already defined and can't be "
                f"redeclared as const in the same scope."
            )

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

        # ── Write to global scope if declared with 'global' ──────────────────
        if node.name in self._global_names:
            self.globals[node.name] = value
        else:
            self.env[node.name] = value
        if node.is_const:
            target_env.consts.add(node.name)
        return value

    def _exec_ShowStatement(self, node: ShowStatement):
        """Execute:  show <expr> [, <expr2> ...]"""
        parts = [self._to_string(self._execute_node(node.expression))]
        for extra in node.extra_expressions:
            parts.append(self._to_string(self._execute_node(extra)))
        print(" ".join(parts))
        return parts[0] if len(parts) == 1 else " ".join(parts)
    
    def _get_think_timeout(self):
        """
        Return the configured think timeout in seconds.
        Reads from nekova.toml [run] think_timeout.
        Returns None if timeout is disabled (set to 0).
        """
        try:
            from nekova.toml_loader import load_config
            cfg = load_config()
            if cfg is not None:
                t = cfg.think_timeout
                return None if t <= 0 else float(t)
        except Exception:
            pass
        return 30.0  # default

    def _sandbox_guard(self, operation: str):
        """
        Raise a NEKOVARuntimeError if this operation is blocked
        by the current sandbox mode. Called from keyword executors.
        """
        if not self._sandbox_mode:
            return  # not sandboxed — allow everything
        blocked_in_strict = {
            "think", "speak", "listen", "imagine", "every",
            "connect", "watch",
        }
        if self._sandbox_mode == "strict" and operation in blocked_in_strict:
            self._sandbox_violations.append({
                "operation": operation,
                "mode": self._sandbox_mode
            })
            raise NEKOVARuntimeError(
                f"[sandbox:{self._sandbox_mode}] "
                f"'{operation}' is blocked in strict mode.\n"
                f"  Use relaxed mode to enable AI and I/O operations."
            )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Rough token estimate — about 4 characters per token, the
        same rule of thumb most providers' own docs quote. Not exact
        (no real tokenizer is used), but good enough for a budget
        check and for ai_usage() to be a useful running total.
        """
        return max(1, len(str(text)) // 4)

    def _track_ai_usage(self, prompt: str, response) -> int:
        """Record one AI call's estimated token cost and return it."""
        tokens = self._estimate_tokens(prompt) + self._estimate_tokens(response)
        self._ai_usage["calls"]  += 1
        self._ai_usage["tokens"] += tokens
        return tokens

    def _check_think_budget(self, node, prompt: str, response) -> int:
        """
        Phase 25: think "..." with budget: <n> — a hard cap on the
        estimated tokens (prompt + response) for a single think call.
        Checked after the call completes (NEKOVA has no way to tell
        an arbitrary provider to stop generating early), so a budget
        catches an overly long response rather than preventing one —
        it's a cost/usage guardrail, not a generation-length limiter.
        Returns the estimated token count either way, for ai_usage().
        """
        tokens = self._estimate_tokens(prompt) + self._estimate_tokens(response)
        if node.budget is not None:
            budget_value = self._execute_node(node.budget)
            if tokens > budget_value:
                raise NEKOVARuntimeError(
                    f"think exceeded its token budget: used ~{tokens} "
                    f"tokens, budget was {budget_value}.\n"
                    f"  Shorten the prompt, expect a shorter response, "
                    f"or raise the budget."
                )
        return tokens

    _PROMPT_INJECTION_PATTERNS = (
        "ignore previous instructions", "ignore all previous",
        "ignore the above", "disregard the above", "disregard previous",
        "new instructions:", "system prompt:", "you are now",
        "pretend you are", "act as if you", "forget everything above",
        "override your instructions", "reveal your system prompt",
    )

    def _check_prompt_injection(self, prompt: str):
        """
        Phase 25: a heuristic guard against prompt injection when
        'think' is called inside a sandbox — relevant when untrusted
        input (a file, a network response, user text) flows into a
        think call inside sandboxed code. This is pattern matching,
        not a real security boundary — it catches common, obvious
        injection phrasing, not a determined attacker rewording
        around it. Recorded as a sandbox violation, same mechanism
        as blocking eval/exec, rather than a separate error path.
        """
        if not self._sandbox_mode:
            return
        prompt_lower = str(prompt).lower()
        for pattern in self._PROMPT_INJECTION_PATTERNS:
            if pattern in prompt_lower:
                self._sandbox_violations.append({
                    "operation": "think",
                    "mode": self._sandbox_mode,
                    "reason": f"possible prompt injection: matched '{pattern}'",
                })
                raise NEKOVARuntimeError(
                    f"[sandbox:{self._sandbox_mode}] This prompt looks like "
                    f"it may contain a prompt-injection attempt (matched: "
                    f"'{pattern}').\n"
                    f"  Blocked inside a sandbox as a precaution. If this "
                    f"is a false positive, rephrase the prompt or handle "
                    f"this think call outside the sandbox."
                )

    def _call_ai_with_visible_retry(self, fn, max_retries: int = 2):
        """
        Phase 25: think's own default retry/backoff — separate from
        the language-level `retry:`/`fallback:` block. A transient
        failure (timeout, rate limit, dropped connection) gets a
        couple of automatic retries with a short backoff, and each
        retry attempt is printed so it's visible rather than a
        silent pause before the eventual result or error. Still
        raises on the final attempt's failure — this doesn't change
        think's existing on_error/swallow behavior, it just gives a
        transient failure a couple of chances before reaching it.
        """
        import time as _time
        import sys as _sys
        backoffs = [0.3, 0.6][:max_retries]
        last_exc = None
        for attempt, _ in enumerate([None] + backoffs, start=1):
            try:
                return fn()
            except Exception as e:
                last_exc = e
                if attempt > len(backoffs):
                    raise
                delay = backoffs[attempt - 1]
                # stderr, not stdout: stdout is the program's actual
                # output (what show/print produce, what tests and
                # other tools capture and assert on) — retry noise
                # doesn't belong mixed into that, but should still be
                # visible to a human watching the terminal, which is
                # exactly what "visible, not silent" means here.
                print(
                    f"[think] attempt {attempt} failed ({e}) — "
                    f"retrying in {delay}s...",
                    file=_sys.stderr
                )
                _time.sleep(delay)
        raise last_exc

    def _exec_ThinkStatement(self, node):
        """Execute a think statement — calls the active AI provider."""
        self._sandbox_guard("think")
        from colorama import Fore, Style, init
        init(autoreset=True)

        # Step 1: Evaluate the prompt
        prompt = self._execute_node(node.prompt)
        prompt = str(prompt)
        self._check_prompt_injection(prompt)

        # Phase 22: `mock think as <value>` short-circuits the real
        # AI call for the rest of the enclosing test block.
        mock = getattr(self, "_think_mock", _NO_MOCK)
        if mock is not _NO_MOCK:
            response = mock
            print(f"{Fore.CYAN}🧠 {response}{Style.RESET_ALL}")
            if node.variable:
                self.env.set(node.variable, response)
            return response

        # Step 2: Call the AI provider (with timeout)
        try:
            from nekova.ai.providers import get_provider
            from nekova.ai.memory_store import (
                conversation_context, add_to_conversation
            )
            provider = get_provider()
            provider.timeout = self._get_think_timeout()
            if node.model is not None:
                provider.model = self._execute_node(node.model)
            # Same conversation-history behavior 'think ... as <format>'
            # already had via ask_structured — extended here so plain
            # 'think' inside a converse: block (or anywhere else) also
            # remembers prior turns.
            full_prompt = conversation_context() + prompt
            if self._debug_ai:
                print(f"{Fore.YELLOW}[debug-ai] prompt sent: {full_prompt!r}{Style.RESET_ALL}")
            response = self._call_ai_with_visible_retry(
                lambda: provider.ask(full_prompt)
            )
            add_to_conversation("user", prompt)
            add_to_conversation("assistant", response)
        except Exception as e:
            if node.on_error is not None:
                # Inline error handling: evaluate the fallback
                # expression instead of embedding an error string.
                response = self._execute_node(node.on_error)
            else:
                # No fallback clause — preserve old behaviour so
                # existing programs don't start crashing.
                response = f"[think error: {e}]"
        else:
            # Only track usage / enforce budget for a genuine
            # successful call — not for mock, error-fallback, or
            # swallowed-error responses, none of which reflect real
            # AI usage.
            self._check_think_budget(node, prompt, response)
            self._track_ai_usage(prompt, response)

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
        Phase 19: Uses the full SandboxEnvironment infrastructure.

        strict  — blocks file system, network, system imports
        relaxed — allows read-only files, blocks writes/system
        Returns a SandboxResult dict accessible as sandbox_result.
        """
        from nekova.sandbox.runner import run_sandboxed
        from nekova.lexer.lexer import Lexer as _Lexer

        mode = node.mode

        # Re-serialise the body back to source for run_sandboxed
        # Since we have the AST, we execute it directly instead
        from nekova.sandbox.environment import SandboxEnvironment
        import builtins, io, sys, time

        start = time.monotonic()
        output_buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buf

        original_open = builtins.open
        violations = []

        if mode == "strict":
            def _blocked_open(*args, **kwargs):
                violations.append("file.open")
                raise NEKOVARuntimeError(
                    f"[sandbox:{mode}] File system access is blocked."
                )
            builtins.open = _blocked_open

        # Swap env to sandboxed version
        sandbox_env = SandboxEnvironment(
            parent=self.env, mode=mode
        )
        prev_env = self.env
        self.env = sandbox_env

        # Bug fix (found while building Phase 25's prompt-injection
        # guard): self._sandbox_mode was declared and checked by
        # _sandbox_guard() but never actually SET when entering a
        # sandbox block, so operation-level blocking (e.g. 'think' in
        # strict mode) was silent dead code — it never fired. Track
        # the previous value too, since sandbox blocks can nest.
        prev_sandbox_mode = self._sandbox_mode
        self._sandbox_mode = mode

        result = {
            "output": "", "error": None, "safe": True,
            "duration": 0.0, "mode": mode, "violations": violations
        }

        try:
            self._execute_block(node.body)
        except NEKOVARuntimeError as e:
            msg = str(e)
            result["error"] = msg
            if "sandbox" in msg.lower():
                result["safe"] = False
                print(f"[sandbox:{mode}] Blocked: {msg}")
            else:
                raise
        finally:
            self.env = prev_env
            self._sandbox_mode = prev_sandbox_mode
            builtins.open = original_open
            sys.stdout = old_stdout

        result["output"]     = output_buf.getvalue()
        result["duration"]   = time.monotonic() - start
        result["violations"].extend(sandbox_env.violations)
        result["safe"]       = result["safe"] and not result["violations"]

        # Store result so user can inspect: let r = sandbox strict: ...
        self.env.set("sandbox_result", result)

        # Print body output to outer stdout so show() works transparently
        if result["output"]:
            print(result["output"], end="")

        status = "✓ safe" if result["safe"] else "✗ violations detected"
        print(f"[sandbox:{mode}] {status} ({result['duration']:.3f}s)")

        return result
    
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

        Runs in current scope (new_scope=False) so that variable
        assignments inside if/else blocks are visible to the outer
        scope — consistent with Python and NEKOVA's design intent.
        """
        condition = self._execute_node(node.condition)

        if self._is_truthy(condition):
            self._execute_block(node.then_body, new_scope=False)
        else:
            self._execute_block(node.else_body, new_scope=False)

    def _exec_BreakStatement(self, node: BreakStatement):
        """Execute: break — exits the nearest enclosing loop."""
        raise BreakSignal()

    def _exec_ContinueStatement(self, node: ContinueStatement):
        """Execute: continue — skips to the next loop iteration."""
        raise ContinueSignal()

    def _exec_GlobalStatement(self, node: GlobalStatement):
        """
        Execute:  global count
                  global x, y, z
        Marks the listed names as belonging to global scope.
        """
        for name in node.names:
            self._global_names.add(name)

    def _exec_UnpackStatement(self, node: UnpackStatement):
        """
        Execute:  a, b, c = [1, 2, 3]
        Evaluates the right side, then assigns each element
        to the corresponding variable name on the left.
        """
        value = self._execute_node(node.value)

        # Flatten range objects and other iterables
        if isinstance(value, range):
            value = list(value)

        if not isinstance(value, (list, tuple)):
            raise NEKOVARuntimeError(
                f"Cannot unpack '{self._to_string(value)}' — "
                f"expected a list with {len(node.names)} items.\n"
                f"  Example:  a, b, c = [1, 2, 3]"
            )

        if len(value) < len(node.names):
            raise NEKOVARuntimeError(
                f"Not enough values to unpack — "
                f"expected {len(node.names)} but got {len(value)}.\n"
                f"  Right side: {self._to_string(list(value))}\n"
                f"  Variables:  {', '.join(node.names)}"
            )

        for name, val in zip(node.names, value):
            if name in self._global_names:
                self.globals.set(name, val)
            else:
                self.env.set(name, val)

    def _assign_destructured(self, name: str, value):
        """Shared assignment helper for destructuring executors —
        respects 'global' declarations the same way plain assignment
        and tuple unpacking do."""
        if name in self._global_names:
            self.globals.set(name, value)
        else:
            self.env.set(name, value)

    def _exec_ListDestructureStatement(self, node: ListDestructureStatement):
        """
        Execute:  let [first, second] = my_list
                  let [first, ...rest] = my_list
        """
        value = self._execute_node(node.value)

        if isinstance(value, range):
            value = list(value)

        if not isinstance(value, (list, tuple)):
            raise NEKOVARuntimeError(
                f"Cannot destructure '{self._to_string(value)}' as a "
                f"list — it's a {type(value).__name__}.\n"
                f"  Example:  let [first, ...rest] = [1, 2, 3]"
            )

        value = list(value)
        needed = len(node.targets)

        if len(value) < needed:
            raise NEKOVARuntimeError(
                f"Not enough values to destructure — "
                f"expected at least {needed} but got {len(value)}.\n"
                f"  Right side: {self._to_string(value)}\n"
                f"  Variables:  {', '.join(node.targets)}"
            )

        for name, val in zip(node.targets, value[:needed]):
            self._assign_destructured(name, val)

        if node.rest is not None:
            self._assign_destructured(node.rest, value[needed:])

    def _exec_DictDestructureStatement(self, node: DictDestructureStatement):
        """
        Execute:  let {name, age} = user
        Each key is read from the dict and bound to a variable of
        the same name.
        """
        value = self._execute_node(node.value)

        if not isinstance(value, dict):
            raise NEKOVARuntimeError(
                f"Cannot destructure '{self._to_string(value)}' as a "
                f"dict — it's a {type(value).__name__}.\n"
                f"  Example:  let {{name, age}} = "
                f"{{\"name\": \"Sam\", \"age\": 30}}"
            )

        for key in node.keys:
            if key not in value:
                available = ", ".join(value.keys()) or "(none)"
                raise NEKOVARuntimeError(
                    f"Key '{key}' not found while destructuring dict.\n"
                    f"  Available keys: {available}"
                )
            self._assign_destructured(key, value[key])

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
            try:
                self._execute_block(node.body, new_scope=False)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
    
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
            try:
                self._execute_block(node.body, new_scope=False)
            except BreakSignal:
                break
            except ContinueSignal:
                pass  # condition is re-evaluated naturally
            count += 1
            if count >= max_iterations:
                raise NEKOVARuntimeError(
                    "While loop ran too many times.\n"
                    "  Check your loop condition."
                )
    
    def _exec_TryStatement(self, node: TryStatement):
        """
        Execute:
            try: ...
            catch error: ...
            finally: ...

        The catch variable is bound to a NEKOVA exception object
        with .message and .type properties, not just a plain string.
        """
        try:
            self._execute_block(node.try_body)

        except NEKOVARaiseError as e:
            # 'raise "something"' or 'raise CustomError(...)' 
            if node.error_var:
                raised = e.value

                if isinstance(raised, str):
                    # raise "plain string"
                    obj = {
                        "message": raised,
                        "type":    "RaiseError",
                        "value":   raised,
                    }
                elif isinstance(raised, dict):
                    # raise CustomError(...) — has __error__ and field values
                    # Normalize into standard {message, type, value} shape
                    error_type = raised.get("__error__", "RaiseError")
                    # message field: prefer explicit 'message' key,
                    # else first non-dunder value, else str repr
                    msg = raised.get(
                        "message",
                        next(
                            (v for k, v in raised.items()
                             if not k.startswith("__")),
                            str(raised)
                        )
                    )
                    obj = {
                        "message": str(msg),
                        "type":    error_type,
                        "value":   raised,
                        # preserve all original fields so e.code etc work
                        **{k: v for k, v in raised.items()
                           if not k.startswith("__")},
                    }
                else:
                    obj = {
                        "message": str(raised),
                        "type":    "RaiseError",
                        "value":   raised,
                    }

                self.env.set(node.error_var, obj)
            if node.catch_body:
                self._execute_block(node.catch_body)
            else:
                raise

        except Exception as e:
            if node.error_var:
                # Build a clean message — strip leading whitespace/newlines
                raw = str(e).strip()
                msg = raw.split("\n")[-1].strip() if "\n" in raw else raw

                # Determine a friendly type name
                type_name = type(e).__name__
                friendly  = {
                    "ZeroDivisionError":  "ZeroDivisionError",
                    "IndexError":         "IndexError",
                    "KeyError":           "KeyError",
                    "TypeError":          "TypeError",
                    "ValueError":         "ValueError",
                    "NEKOVARuntimeError": "RuntimeError",
                    "NEKOVANameError":    "NameError",
                    "NEKOVAAssertionError": "AssertionError",
                }.get(type_name, type_name)

                # Bind as a dict-object so e.message and e.type work
                error_obj = {
                    "message": msg,
                    "type":    friendly,
                    "value":   msg,
                }
                self.env.set(node.error_var, error_obj)

            if node.catch_body:
                self._execute_block(node.catch_body)
            else:
                raise  # Bug 19: re-raise when no catch block

        finally:
            if node.finally_body:
                self._execute_block(node.finally_body)

    def _exec_ForStatement(self, node: ForStatement):
        """
        Execute:
            for item in items:              ← single variable
                <body>
            for i, v in enumerate(items):   ← multi-variable unpack
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
        elif hasattr(iterable, "__iter__"):
            # Covers _NEKOVAGenerator and any other iterable
            items = list(iterable)
        else:
            raise NEKOVARuntimeError(
                f"Cannot iterate over "
                f"'{type(iterable).__name__}'.\n"
                f"  Use a list, string, range, or generator."
            )

        multi = isinstance(node.variable, list)

        for item in items:
            if multi:
                # Unpack each item into the named variables
                variables = node.variable
                if not isinstance(item, (list, tuple)):
                    item = [item]
                if len(item) < len(variables):
                    raise NEKOVARuntimeError(
                        f"Not enough values to unpack in for loop — "
                        f"expected {len(variables)} but got {len(item)}."
                    )
                for name, val in zip(variables, item):
                    self.env.set(name, val)
            else:
                self.env.set(node.variable, item)

            try:
                self._execute_block(node.body, new_scope=False)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_TaskStatement(self, node: TaskStatement):
        """
        Execute:  task greet(name): ...
        If body contains yield, registers a generator factory instead.
        """
        node.closure_env = self.env
        if self._body_has_yield(node.body):
            # Register as a generator factory
            interp = self
            def _make_gen_factory(n):
                def _factory(*args):
                    return _NEKOVAGenerator(n, args, interp)
                _factory.__name__ = n.name
                _factory._is_generator = True
                return _factory
            self.env.set(node.name, _make_gen_factory(node))
        else:
            self.env.set(node.name, node)

    def _exec_PromptStatement(self, node: PromptStatement):
        """
        Execute:  prompt summarize(text, style="professional"): ...
        Registers the prompt like a task — calling it later returns
        the interpolated template string (see _call_prompt).
        """
        node.closure_env = self.env
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
                if self.debug:
                    import sys
                    print(f"{Color.DIM}→ imported {names_str} from '{node.filepath}'{Color.RESET}", file=sys.stderr)
            else:
                if self.debug:
                    import sys
                    print(f"{Color.DIM}→ imported '{node.filepath}'{Color.RESET}", file=sys.stderr)

        except NEKOVARuntimeError:
            raise
        except Exception as e:
            raise NEKOVARuntimeError(
                f"Error importing '{node.filepath}':\n"
                f"  {e}"
            )

    @staticmethod
    def _param_name_default_pairs(params):
        """
        Normalize either param-tuple shape into (name, default, is_vararg):
          - TaskStatement:                (name, default, is_vararg)
          - TypedTaskStatement/AsyncFunction: (name, type_hint, default, is_vararg)
        """
        if not params:
            return []
        if len(params[0]) == 3:
            return [(n, d, v) for (n, d, v) in params]
        return [(n, d, v) for (n, _t, d, v) in params]

    def _resolve_kwargs(self, node, callee, args):
        """
        Merge node.kwargs into a fully-positional args list matching
        callee's declared parameters, evaluating defaults for any
        parameters that get neither a positional nor a keyword value.
        This runs entirely before dispatching to _call_task /
        _call_typed_task / AsyncFunction.call, so none of those need
        their own keyword-argument logic — they just see a complete
        positional list, exactly like any other call.

        Note: default expressions filled in here evaluate in the
        *caller's* environment (this hasn't switched into the callee's
        local scope yet), whereas purely-positional calls evaluate
        missing defaults inside the callee's own local environment.
        This only matters if a default expression references another
        parameter or a task-local name, which is rare — defaults are
        almost always literals.
        """
        raw_params = getattr(callee, "params", None) or []
        if raw_params and isinstance(raw_params[0], str):
            raw_params = [(p, None, False) for p in raw_params]

        norm = self._param_name_default_pairs(raw_params)
        if not norm:
            raise NEKOVARuntimeError(
                f"'{node.name}' doesn't accept keyword arguments — "
                f"it has no parameters."
            )
        names = [n for (n, _d, _v) in norm]
        callee_label = getattr(callee, "name", node.name)

        resolved = list(args)

        # The gap-filling loop below assumes it's walking keyword
        # arguments in *declared* parameter order — it fills any gap
        # before the current one with that parameter's default. If the
        # caller passed keywords out of declaration order (e.g.
        # greet(greeting="Hi", name="World") for task greet(name,
        # greeting)), iterating node.kwargs in call-site order fills
        # those gaps with defaults instead of the not-yet-visited
        # keyword value, silently misassigning arguments. Sorting by
        # each keyword's declared position first makes the loop see
        # them in the order it expects, regardless of call-site order.
        sorted_kwargs = sorted(
            node.kwargs.items(),
            key=lambda kv: names.index(kv[0]) if kv[0] in names else -1
        )

        for kw_name, kw_expr in sorted_kwargs:
            if kw_name not in names:
                raise NEKOVARuntimeError(
                    f"'{callee_label}' has no parameter named "
                    f"'{kw_name}'.\n"
                    f"  Available parameters: {', '.join(names)}"
                )
            idx = names.index(kw_name)
            if idx < len(args):
                raise NEKOVARuntimeError(
                    f"'{callee_label}' got multiple values for "
                    f"parameter '{kw_name}' — it was passed both "
                    f"positionally and by keyword."
                )
            value = self._execute_node(kw_expr)
            while len(resolved) <= idx:
                gap_i = len(resolved)
                gap_name, gap_default, _gap_vararg = norm[gap_i]
                if gap_i == idx:
                    resolved.append(value)
                elif gap_default is not None:
                    resolved.append(self._execute_node(gap_default))
                else:
                    raise NEKOVARuntimeError(
                        f"'{callee_label}': parameter '{gap_name}' has "
                        f"no default and no value was given (needed to "
                        f"fill the gap before keyword argument "
                        f"'{kw_name}')."
                    )
        return resolved

    def _exec_CallExpression(self, node: CallExpression):
        """
        Execute:  greet("Emmanuel")
        Looks up the task and runs it with the given arguments.
        """
        # Resolve callee — node.name may be a string or an AST node (Identifier, etc.)
        if isinstance(node.name, str):
            callee = self.env.get(node.name)
        else:
            callee = self._execute_node(node.name)

        # Evaluate all arguments
        args = [self._execute_node(arg) for arg in node.args]

        # Built-in Python function
        if callable(callee) and not isinstance(callee, (TaskStatement, TypedTaskStatement)):
            builtin_name = node.name if isinstance(node.name, str) else "<builtin>"
            try:
                return callee(*args)
            except NEKOVARuntimeError:
                raise
            except (ValueError, TypeError, OverflowError, AttributeError,
                    IndexError, KeyError, ZeroDivisionError) as e:
                shown_args = ", ".join(self._to_string(a) for a in args)

                if builtin_name in ("int", "float") and len(args) == 1:
                    raise NEKOVARuntimeError(
                        f"Cannot convert {self._to_string(args[0])!r} "
                        f"to {'a number' if builtin_name == 'int' else 'a decimal number'} "
                        f"with {builtin_name}().\n"
                        f"  It needs to look like a plain number, "
                        f"e.g. {builtin_name}(\"42\")."
                    )

                # Phase 23b exception audit (generic fallback): builtins
                # like len(), range(), sum(), chr(), etc. are thin
                # wrappers around Python's own functions, so a bad
                # argument used to raise Python's raw exception straight
                # at the user — plus a full Python traceback with file
                # paths, since these exception types weren't even caught
                # anywhere. Every builtin call now gets a clean,
                # NEKOVA-flavoured message instead, regardless of which
                # Python exception type it happens to raise internally.
                raise NEKOVARuntimeError(
                    f"'{builtin_name}({shown_args})' failed: {e}\n"
                    f"  Check that the argument(s) are the type "
                    f"'{builtin_name}' expects."
                )

        # Phase 24: keyword arguments — greet(name="Sam", greeting="Hi").
        # Resolved into a fully-positional args list up front (filling
        # any gaps with evaluated defaults) so every call path below
        # (typed task, prompt, task, async task) is unaffected and
        # doesn't need its own kwargs-handling logic.
        if node.kwargs:
            args = self._resolve_kwargs(node, callee, args)

        # NEKOVA typed task (Phase 17)
        if isinstance(callee, TypedTaskStatement):
            return self._call_typed_task(callee, args)

        # NEKOVA prompt block (Phase 21)
        if isinstance(callee, PromptStatement):
            return self._call_prompt(callee, args)

        # NEKOVA task
        if isinstance(callee, TaskStatement):
            return self._call_task(callee, args)

        # NEKOVA async task — calling it is synchronous under the hood
        # (see AsyncFunction.call in async_interpreter.py). No event-loop
        # detection needed here anymore: the previous version tried to
        # detect whether it was inside a running loop by catching
        # NEKOVARuntimeError around asyncio.get_running_loop(), but that
        # function actually raises the built-in RuntimeError — so the
        # except clause never matched, and calling an async task without
        # 'await' crashed with an unhandled RuntimeError.
        from nekova.interpreter.async_interpreter import AsyncFunction as _AsyncFn
        if isinstance(callee, _AsyncFn):
            return callee.call(args)

        raise NEKOVARuntimeError(
            f"'{node.name}' is not a task you can call.\n"
            f"  Define it first with:  task {node.name}(...):"
        )

    # ----------------------------------------------------------
    # Expression evaluators
    # ----------------------------------------------------------

    def _exec_BinaryOp(self, node: BinaryOp):
        """Evaluate a binary operation like age + 1 or x == y."""
        op = node.operator

        # Bug 15 fix: short-circuit and/or before evaluating right side
        if op == "and":
            left = self._execute_node(node.left)
            if not self._is_truthy(left):
                return left  # short-circuit: return falsy left
            return self._execute_node(node.right)
        if op == "or":
            left = self._execute_node(node.left)
            if self._is_truthy(left):
                return left  # short-circuit: return truthy left
            return self._execute_node(node.right)

        left  = self._execute_node(node.left)
        right = self._execute_node(node.right)

        try:
            if op == "+":
                # String + string is concatenation.
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                # Mixing a string with a number is a common beginner
                # mistake ("5" + 3) that silently produces "53" in
                # JS-like languages. NEKOVA raises instead of coercing,
                # so the mistake is caught immediately.
                # (Bools are intentionally excluded from this check since
                # isinstance(True, int) is True in Python — a bool here
                # falls through to string-building below, same as dicts
                # and lists, which is the deliberate, useful pattern for
                # things like "caught: " + error_object.)
                str_num_mismatch = (
                    (isinstance(left, str) and isinstance(right, (int, float))
                     and not isinstance(right, bool))
                    or
                    (isinstance(right, str) and isinstance(left, (int, float))
                     and not isinstance(left, bool))
                )
                if str_num_mismatch:
                    raise NEKOVARuntimeError(
                        f"Cannot use '+' between "
                        f"'{type(left).__name__}' and "
                        f"'{type(right).__name__}'.\n"
                        f"  Convert one side explicitly, e.g. "
                        f"str(value) or int(value)."
                    )
                # String + other (dict, list, bool, None, error object,
                # etc.) still builds a string — this is the deliberate
                # pattern used for messages like "caught: " + error_obj.
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
            # and/or handled above with short-circuit
            if op == "//":  return int(left // right)
            if op == "in":     return left in right
            if op == "not in": return left not in right
            if op == "is":     return left is right
            if op == "is not": return left is not right

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
    
    def _exec_SetLiteral(self, node: SetLiteral):
        """
        Execute a set literal like {1, 2, 3} — duplicates are silently
        collapsed, matching normal set semantics.
        """
        result = set()
        for e in node.elements:
            value = self._execute_node(e)
            try:
                result.add(value)
            except TypeError:
                raise NEKOVARuntimeError(
                    f"Cannot put '{self._to_string(value)}' in a set — "
                    f"{type(value).__name__} values can't be checked "
                    f"for uniqueness (lists and dicts aren't allowed "
                    f"inside a set)."
                )
        return result

    def _exec_ConverseStatement(self, node):
        """
        Execute a converse: block — a fresh, isolated multi-turn
        conversation. Clears any prior conversation history so an
        earlier think/listen elsewhere in the program doesn't leak
        into this block, runs the body (think/listen inside it
        automatically carry conversation context — see
        _exec_ThinkStatement and _exec_ListenExpression), then
        leaves the accumulated history in place afterward in case
        the caller wants to inspect it via recall/memory tools.
        """
        from nekova.ai.memory_store import clear_conversation
        clear_conversation()
        result = None
        for stmt in node.body:
            result = self._execute_node(stmt)
        return result

    def _exec_EnumDefinition(self, node: EnumDefinition):
        """Execute:  enum Status: PENDING, ACTIVE, DONE"""
        enum_obj = NEKOVAEnum(node.name, node.members)
        self.env.set(node.name, enum_obj)
        return enum_obj

    def _exec_ListLiteral(self, node: ListLiteral):
        """
        Execute a list literal like [1, 2, 3], expanding any spread
        items in place: [...list_a, extra, ...list_b].
        """
        result = []
        for e in node.elements:
            if isinstance(e, SpreadElement):
                spread_val = self._execute_node(e.expr)
                if not isinstance(spread_val, (list, tuple)):
                    raise NEKOVARuntimeError(
                        f"Cannot spread '{self._to_string(spread_val)}' "
                        f"into a list — it's a "
                        f"{type(spread_val).__name__}, not a list.\n"
                        f"  Example:  [...list_a, ...list_b]"
                    )
                result.extend(spread_val)
            else:
                result.append(self._execute_node(e))
        return result

    def _exec_TupleLiteral(self, node: TupleLiteral):
        """
        Execute a tuple literal like (1, 2), expanding any spread
        items in place: (...pair_a, extra, ...pair_b). Built as a
        Python tuple, so it's immutable at runtime for free — index
        assignment into it already fails via the existing
        IndexAssignStatement handling, which only special-cases
        list/dict.
        """
        result = []
        for e in node.elements:
            if isinstance(e, SpreadElement):
                spread_val = self._execute_node(e.expr)
                if not isinstance(spread_val, (list, tuple)):
                    raise NEKOVARuntimeError(
                        f"Cannot spread '{self._to_string(spread_val)}' "
                        f"into a tuple — it's a "
                        f"{type(spread_val).__name__}, not a list or "
                        f"tuple.\n"
                        f"  Example:  (...pair_a, ...pair_b)"
                    )
                result.extend(spread_val)
            else:
                result.append(self._execute_node(e))
        return tuple(result)

    def _exec_DictLiteral(self, node: DictLiteral):
        """
        Execute a dictionary literal, expanding any spread items in
        place: {...defaults, ...overrides} — later keys (including
        those from a later spread) win, matching how a plain repeated
        key would behave.
        """
        result = {}
        for key_node, value_node in node.pairs:
            if isinstance(key_node, SpreadElement):
                spread_val = self._execute_node(key_node.expr)
                if not isinstance(spread_val, dict):
                    raise NEKOVARuntimeError(
                        f"Cannot spread '{self._to_string(spread_val)}' "
                        f"into a dict — it's a "
                        f"{type(spread_val).__name__}, not a dict.\n"
                        f"  Example:  {{...defaults, ...overrides}}"
                    )
                result.update(spread_val)
                continue
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
    
    def _exec_IndexAssignStatement(self, node: IndexAssignStatement):
        """
        Assign a value into a list or dict by index/key.
            items[0]   = "new"
            d["key"]   = 99
        """
        collection = self._execute_node(node.collection)
        index      = self._execute_node(node.index)
        value      = self._execute_node(node.value)

        if isinstance(collection, dict):
            collection[str(index)] = value
        elif isinstance(collection, list):
            try:
                collection[int(index)] = value
            except IndexError:
                raise NEKOVARuntimeError(
                    f"Index {index} is out of range.\n"
                    f"  List has {len(collection)} items."
                )
        else:
            raise NEKOVARuntimeError(
                f"Cannot assign by index into "
                f"'{type(collection).__name__}'. "
                f"Only lists and dicts support this."
            )
        return value

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

        # Optional chaining: obj?.prop — if obj is null, the whole
        # chain short-circuits to null instead of raising.
        if obj is None and getattr(node, "optional", False):
            return None

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

        # Optional chaining: obj?.method() — if obj is null, the whole
        # chain short-circuits to null instead of raising.
        if obj is None and getattr(node, "optional", False):
            return None

        # ── String methods ────────────────────────────────
        if isinstance(obj, str):
            methods = {
                "upper":       lambda: obj.upper(),
                "lower":       lambda: obj.lower(),
                "title":       lambda: obj.title(),
                "strip":       lambda: obj.strip(),
                "trim":        lambda: obj.strip(),
                "lstrip":      lambda: obj.lstrip(args[0] if args else None),
                "rstrip":      lambda: obj.rstrip(args[0] if args else None),
                "reverse":     lambda: obj[::-1],
                "length":      lambda: len(obj),
                "split":       lambda: obj.split(
                                   args[0] if args else " "),
                "replace":     lambda: obj.replace(
                                   args[0], args[1]),
                "contains":    lambda: args[0] in obj,
                "starts_with": lambda: obj.startswith(args[0]),
                "ends_with":   lambda: obj.endswith(args[0]),
                "find":        lambda: obj.find(args[0]),
                "index":       lambda: obj.index(args[0]),
                "count":       lambda: obj.count(args[0]),
                "repeat":      lambda: obj * int(args[0]),
                # join: "sep".join(list) — joins list items with separator
                "join":        lambda: obj.join(
                                   str(x) for x in args[0]
                               ) if args and isinstance(args[0], list)
                               else obj.join(args[0] if args else []),
                "format":      lambda: obj.format(*args),
                "zfill":       lambda: obj.zfill(int(args[0])),
                "center":      lambda: obj.center(
                                   int(args[0]),
                                   args[1] if len(args) > 1 else " "),
                "ljust":       lambda: obj.ljust(
                                   int(args[0]),
                                   args[1] if len(args) > 1 else " "),
                "rjust":       lambda: obj.rjust(
                                   int(args[0]),
                                   args[1] if len(args) > 1 else " "),
                "is_digit":    lambda: obj.isdigit(),
                "is_alpha":    lambda: obj.isalpha(),
                "is_lower":    lambda: obj.islower(),
                "is_upper":    lambda: obj.isupper(),
                "to_list":     lambda: list(obj),
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
        Supports default params and *args (varargs).
        params is list of (name, default_or_None, is_vararg).
        Old-style params (plain strings) are supported for back-compat.
        """
        self._call_depth += 1
        if self._call_depth > self.MAX_CALL_DEPTH:
            self._call_depth -= 1
            raise NEKOVARecursionError(
                task.name, self.MAX_CALL_DEPTH, line=self._current_line
            )

        closure      = getattr(task, "closure_env", self.globals)
        local_env    = Environment(parent=closure)
        previous_env = self.env
        previous_globals = self._global_names
        self._global_names = set()

        # Normalise params: support old-style plain strings
        params = task.params
        if params and isinstance(params[0], str):
            params = [(p, None, False) for p in params]

        # Check for vararg param
        vararg_idx = next((i for i, (n, d, v) in enumerate(params) if v), None)

        if vararg_idx is not None:
            # All params before vararg are positional
            positional = params[:vararg_idx]
            vararg_name = params[vararg_idx][0]
            if len(args) < len(positional):
                raise NEKOVARuntimeError(
                    f"Task '{task.name}' expects at least "
                    f"{len(positional)} argument(s) but got {len(args)}."
                )
            for (pname, default, _), val in zip(positional, args[:len(positional)]):
                local_env.set(pname, val)
            local_env.set(vararg_name, list(args[len(positional):]))
        else:
            # Count required (no default) params
            required = sum(1 for (_, d, _) in params if d is None)
            if len(args) < required or len(args) > len(params):
                raise NEKOVARuntimeError(
                    f"Task '{task.name}' expects "
                    f"{required}–{len(params)} argument(s) "
                    f"but got {len(args)}."
                )
            for i, (pname, default, _) in enumerate(params):
                if i < len(args):
                    local_env.set(pname, args[i])
                else:
                    # Evaluate default expression
                    local_env.set(pname, self._execute_node(default))

        self.env = local_env
        try:
            for stmt in task.body:
                self._execute_node(stmt)
            return None
        except ReturnSignal as r:
            return r.value
        finally:
            self.env = previous_env
            self._global_names = previous_globals
            self._call_depth -= 1

    def _call_prompt(self, prompt: PromptStatement, args: list):
        """
        Call a prompt block. Binds parameters exactly like a typed
        task (name, type_hint, default, is_vararg) — including type
        enforcement — but the return value is implicit: it's the
        value of the last statement in the body (typically the
        interpolated template string), not something you need an
        explicit `return` for. An explicit `return` still works if
        the prompt body has one.
        """
        TYPE_VALIDATORS = {
            "int":   (int,   "an integer"),
            "float": (float, "a float"),
            "str":   (str,   "a string"),
            "bool":  (bool,  "a boolean"),
            "list":  (list,  "a list"),
            "dict":  (dict,  "a dict"),
        }

        closure   = getattr(prompt, "closure_env", self.globals)
        local_env = Environment(parent=closure)
        prev_env  = self.env
        prev_globals = self._global_names
        self._global_names = set()

        params = prompt.params  # (name, type_hint, default, is_vararg)

        vararg_idx = next((i for i, p in enumerate(params) if p[3]), None)

        if vararg_idx is not None:
            positional = params[:vararg_idx]
            vararg_name = params[vararg_idx][0]
            if len(args) < len(positional):
                raise NEKOVARuntimeError(
                    f"Prompt '{prompt.name}' expects at least "
                    f"{len(positional)} argument(s) but got {len(args)}."
                )
            for (pname, phint, _, _), val in zip(positional, args):
                self._check_type(pname, val, phint, TYPE_VALIDATORS, prompt.name, kind="Prompt")
                local_env.set(pname, val)
            local_env.set(vararg_name, list(args[len(positional):]))
        else:
            required = sum(1 for (_, _, d, _) in params if d is None)
            if len(args) < required or len(args) > len(params):
                raise NEKOVARuntimeError(
                    f"Prompt '{prompt.name}' expects "
                    f"{required}\u2013{len(params)} argument(s) but got {len(args)}."
                )
            for i, (pname, phint, default, _) in enumerate(params):
                val = args[i] if i < len(args) else self._execute_node(default)
                self._check_type(pname, val, phint, TYPE_VALIDATORS, prompt.name, kind="Prompt")
                local_env.set(pname, val)

        self.env = local_env
        last_value = None
        try:
            for stmt in prompt.body:
                last_value = self._execute_node(stmt)
            return last_value
        except ReturnSignal as r:
            return r.value
        finally:
            self.env = prev_env
            self._global_names = prev_globals

    def _exec_RetryStatement(self, node: RetryStatement):
        """
        Execute:
            retry 3 times with exponential backoff:
                <body>
            fallback:
                <body>

        Retries `body` up to `times` times whenever it raises an
        error. Control-flow signals (return/break/continue) are
        never treated as retry-triggering errors — they propagate
        immediately, exactly like they would outside a retry block.
        On exhausting all attempts: runs `fallback_body` if given,
        otherwise re-raises the last error.
        """
        import time

        times = self._execute_node(node.times)
        try:
            times = int(times)
        except (TypeError, ValueError):
            raise NEKOVARuntimeError(
                f"'retry' expects a number of attempts, got "
                f"{type(times).__name__}."
            )
        if times < 1:
            raise NEKOVARuntimeError(
                "'retry' needs at least 1 attempt — got "
                f"{times}."
            )

        last_error = None
        for attempt in range(1, times + 1):
            try:
                self._execute_block(node.body, new_scope=False)
                return
            except (ReturnSignal, BreakSignal, ContinueSignal):
                raise
            except (NEKOVARaiseError, Exception) as e:
                last_error = e
                if attempt < times:
                    if node.backoff == "exponential":
                        time.sleep(min(2 ** (attempt - 1), 30))
                    elif node.backoff == "linear":
                        time.sleep(attempt)
                    # no backoff clause -> immediate retry, no delay

        if node.fallback_body is not None:
            self._execute_block(node.fallback_body, new_scope=False)
            return

        raise last_error

    def _exec_ObserveStatement(self, node: ObserveStatement):
        """
        Execute:
            observe "pipeline run" with tags {user: user_id}:
                let summary = think summarize(document)

        Traces the block: prints a start line (label + tags), runs
        the body, then prints a completed/failed line with elapsed
        time. Errors are logged and re-raised — observe never
        swallows exceptions, it just makes them visible.
        """
        import time
        from colorama import Fore, Style, init
        init(autoreset=True)

        label = self._to_string(self._execute_node(node.label))

        tags = None
        if node.tags is not None:
            tags = self._execute_node(node.tags)

        tag_suffix = ""
        if isinstance(tags, dict) and tags:
            pairs = ", ".join(f"{k}: {self._to_string(v)}" for k, v in tags.items())
            tag_suffix = f"  {{{pairs}}}"

        print(f"{Fore.BLUE}👁  {label}{tag_suffix}{Style.RESET_ALL}")

        start = time.time()
        try:
            result = self._execute_block(node.body, new_scope=False)
        except (ReturnSignal, BreakSignal, ContinueSignal):
            elapsed_ms = (time.time() - start) * 1000
            print(f"{Fore.BLUE}   └─ exited early ({elapsed_ms:.1f}ms){Style.RESET_ALL}")
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            print(f"{Fore.RED}   └─ failed after {elapsed_ms:.1f}ms: {e}{Style.RESET_ALL}")
            raise

        elapsed_ms = (time.time() - start) * 1000
        print(f"{Fore.BLUE}   └─ completed in {elapsed_ms:.1f}ms{Style.RESET_ALL}")
        return result

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
            # Error objects (from catch) display as their message, not raw dict
            if "message" in value and "type" in value and "value" in value:
                return str(value["message"])
            pairs = []
            for k, v in value.items():
                pairs.append(f"{k}: {self._to_string(v)}")
            return "{" + ", ".join(pairs) + "}"
        if isinstance(value, list):
            items = [self._to_string(i) for i in value]
            return "[" + ", ".join(items) + "]"
        if isinstance(value, tuple):
            items = [self._to_string(i) for i in value]
            if len(items) == 1:
                return "(" + items[0] + ",)"
            return "(" + ", ".join(items) + ")"
        if isinstance(value, set):
            if not value:
                return "{}"
            items = [self._to_string(i) for i in sorted(value, key=str)]
            return "{" + ", ".join(items) + "}"
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
        # Phase 7: database connect() built-in
        self.globals.set("connect",   lambda fp="nekova.db": _DBObject(str(fp)))
        self.globals.set("type_of",   lambda x: type(x).__name__)
        self.globals.set("to_number", lambda x: float(x)
                         if "." in str(x) else int(x))
        self.globals.set("to_text",   lambda x: str(x))
        self.globals.set("length",    lambda x: len(x))
        self.globals.set("ask",       lambda prompt="": input(str(prompt)))
        self.globals.set("clear",     lambda: print("\033[H\033[J", end=""))
        self.globals.set("sleep",     lambda s=1: __import__("time").sleep(float(s)))
        self.globals.set("random_num",lambda a, b: __import__("random").randint(int(a), int(b)))
        # Phase 15: Python-compatible builtins
        self.globals.set("range",    lambda *a: list(range(*[int(x) for x in a])))
        self.globals.set("len",      lambda x: len(x))
        self.globals.set("str",      lambda x: str(x))
        self.globals.set("int",      lambda x: int(x))
        self.globals.set("float",    lambda x: float(x))
        self.globals.set("bool",     lambda x: bool(x))
        self.globals.set("abs",      lambda x: abs(x))
        self.globals.set("round",    lambda x, n=0: round(x, n))
        self.globals.set("min",      lambda *a: min(*a) if len(a) > 1 else min(a[0]))
        self.globals.set("max",      lambda *a: max(*a) if len(a) > 1 else max(a[0]))
        self.globals.set("sum",      lambda x: sum(x))
        self.globals.set("sorted",   lambda x, **kw: sorted(x, **kw))
        self.globals.set("reversed", lambda x: list(reversed(x)))
        self.globals.set("list",     lambda x: list(x))
        self.globals.set("dict",     lambda: {})
        self.globals.set("print",    print)

        # ── Phase 23: task docstrings ───────────────────────────
        def _doc(task_obj):
            """
            doc(some_task) — returns the docstring captured from a
            task's leading triple-quoted string, or a helpful message
            if the task has none. Pass the task itself (not a call):
                doc(greet)     — correct
                doc(greet())   — wrong, that calls greet first
            """
            text = getattr(task_obj, "docstring", None)
            if text:
                return text
            name = getattr(task_obj, "name", None)
            if name:
                return f"No docstring for '{name}'."
            return "No docstring available."
        self.globals.set("doc", _doc)

        # ── Phase 25: AI usage tracking ──────────────────────────
        def _ai_usage():
            """Cumulative {calls, tokens} across every real think()
            call so far (mock/error-fallback calls aren't counted).
            Token counts are an estimate — see _estimate_tokens."""
            return dict(self._ai_usage)
        self.globals.set("ai_usage", _ai_usage)

        # ── Phase 24: set operations ─────────────────────────────
        def _as_set(x, fn_name):
            if isinstance(x, set):
                return x
            if isinstance(x, (list, tuple)):
                return set(x)
            raise NEKOVARuntimeError(
                f"{fn_name}() needs sets (or lists), got a "
                f"{type(x).__name__}."
            )
        self.globals.set(
            "set_union",
            lambda a, b: _as_set(a, "set_union") | _as_set(b, "set_union")
        )
        self.globals.set(
            "set_intersection",
            lambda a, b: _as_set(a, "set_intersection") & _as_set(b, "set_intersection")
        )
        self.globals.set(
            "set_difference",
            lambda a, b: _as_set(a, "set_difference") - _as_set(b, "set_difference")
        )


        # ── Phase 19: Sandbox API ─────────────────────────────
        from nekova.sandbox.runner import run_sandboxed as _run_sandboxed

        def _sandbox_run(source, mode="strict", **limits):
            """Run NEKOVA source string in a sandbox, return result dict."""
            result = _run_sandboxed(str(source), mode=str(mode))
            return {
                "output":     result.output,
                "error":      result.error,
                "safe":       result.safe,
                "duration":   result.duration,
                "mode":       result.mode,
                "violations": result.violations,
            }

        self.globals.set("sandbox_run", _sandbox_run)
        # ── Math primitives (delegated to Python's math module) ──
        import math as _math
        self.globals.set("sqrt",   _math.sqrt)
        self.globals.set("floor",  _math.floor)
        self.globals.set("ceil",   _math.ceil)
        self.globals.set("log",    _math.log)
        self.globals.set("log10",  _math.log10)
        self.globals.set("sin",    _math.sin)
        self.globals.set("cos",    _math.cos)
        self.globals.set("tan",    _math.tan)
        self.globals.set("pow",    _math.pow)

        # ── Phase 18: file builtins (used by file.nk) ────────
        import os as _os

        def _file_read(path):
            with open(_os.path.expanduser(str(path)), "r", encoding="utf-8") as f:
                return f.read()

        def _file_write(path, content):
            with open(_os.path.expanduser(str(path)), "w", encoding="utf-8") as f:
                f.write(str(content))

        def _file_append(path, content):
            with open(_os.path.expanduser(str(path)), "a", encoding="utf-8") as f:
                f.write(str(content))

        def _file_exists(path):
            return _os.path.exists(_os.path.expanduser(str(path)))

        def _file_delete(path):
            p = _os.path.expanduser(str(path))
            if _os.path.exists(p):
                _os.remove(p)

        self.globals.set("file_read",   _file_read)
        self.globals.set("file_write",  _file_write)
        self.globals.set("file_append", _file_append)
        self.globals.set("file_exists", _file_exists)
        self.globals.set("file_delete", _file_delete)

        # ── Phase 18: date builtins (used by date.nk) ────────
        import datetime as _dt

        def _date_now():
            return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _date_today():
            return _dt.date.today().isoformat()

        def _date_timestamp():
            import time as _time
            return int(_time.time())

        def _date_format(date_str, fmt):
            d = _dt.datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return d.strftime(str(fmt))

        def _date_add_days(date_str, n):
            d = _dt.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            return (d + _dt.timedelta(days=int(n))).isoformat()

        def _date_diff_days(date_a, date_b):
            a = _dt.datetime.strptime(str(date_a)[:10], "%Y-%m-%d").date()
            b = _dt.datetime.strptime(str(date_b)[:10], "%Y-%m-%d").date()
            return (b - a).days

        def _date_day_of_week(date_str):
            d = _dt.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            return d.strftime("%A")

        self.globals.set("date_now",        _date_now)
        self.globals.set("date_today",      _date_today)
        self.globals.set("date_timestamp",  _date_timestamp)
        self.globals.set("date_format",     _date_format)
        self.globals.set("date_add_days",   _date_add_days)
        self.globals.set("date_diff_days",  _date_diff_days)
        self.globals.set("date_day_of_week", _date_day_of_week)
        # Math
        self.globals.set("pow",      lambda x, y: x ** y)
        self.globals.set("divmod",   lambda x, y: list(divmod(x, y)))
        # Character conversion
        self.globals.set("chr",      lambda x: chr(int(x)))
        self.globals.set("ord",      lambda x: ord(str(x)[0]))
        self.globals.set("hex",      lambda x: hex(int(x)))
        self.globals.set("bin",      lambda x: bin(int(x)))
        self.globals.set("oct",      lambda x: oct(int(x)))
        # Input
        self.globals.set("input",    lambda prompt="": input(str(prompt)))
        # Functional
        self.globals.set("enumerate", lambda x, start=0: list(enumerate(x, start)))
        self.globals.set("zip",       lambda *a: [list(t) for t in zip(*a)])
        self.globals.set("map",       lambda f, x: list(map(f, x)))
        self.globals.set("filter",    lambda f, x: list(filter(f, x)))
        self.globals.set("any",       lambda x: any(x))
        self.globals.set("all",       lambda x: all(x))
        # Type checks
        self.globals.set("isinstance", lambda x, t: isinstance(x, t))
        self.globals.set("callable",   lambda x: callable(x))

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
    # ----------------------------------------------------------
    # Phase 7: Pattern Matching
    # ----------------------------------------------------------

    def _exec_MatchStatement(self, node: MatchStatement):
        """
        Evaluate the subject then iterate arms in order.
        First matching arm wins; else arm is a catch-all.
        """
        from nekova.interpreter.nekova_class import NEKOVAInstance
        subject = self._execute_node(node.subject)

        for arm in node.arms:
            # ── else arm ──────────────────────────────────────
            if arm.is_else:
                result = None
                for stmt in arm.body:
                    result = self._execute_node(stmt)
                    if isinstance(result, ReturnSignal):
                        return result
                return result

            # ── range arm: when 'a'..'z' or when 0..9 ────────
            if arm.is_range:
                lo = self._execute_node(arm.pattern)
                hi = self._execute_node(arm.range_end)
                try:
                    matched = lo <= subject <= hi
                except TypeError:
                    matched = False
                if matched:
                    result = None
                    for stmt in arm.body:
                        result = self._execute_node(stmt)
                        if isinstance(result, ReturnSignal):
                            return result
                    return result
                continue

            # ── type-check arm ────────────────────────────────
            if arm.is_type_check:
                type_name = arm.pattern   # string like "text"
                matched   = False

                if type_name == "text":
                    matched = isinstance(subject, str)
                elif type_name == "number":
                    matched = isinstance(subject, (int, float)) and not isinstance(subject, bool)
                elif type_name == "boolean":
                    matched = isinstance(subject, bool)
                elif type_name == "list":
                    matched = isinstance(subject, list)
                elif type_name == "dict":
                    matched = isinstance(subject, dict)
                elif type_name == "null":
                    matched = subject is None
                elif type_name == "any":
                    matched = True
                else:
                    # Class name check
                    if isinstance(subject, NEKOVAInstance):
                        matched = self._instance_is_a(subject, type_name)

                if matched:
                    result = None
                    for stmt in arm.body:
                        result = self._execute_node(stmt)
                        if isinstance(result, ReturnSignal):
                            return result
                    return result
                continue

            # ── value-match arm ───────────────────────────────
            pattern_val = self._execute_node(arm.pattern)
            if subject == pattern_val:
                result = None
                for stmt in arm.body:
                    result = self._execute_node(stmt)
                    if isinstance(result, ReturnSignal):
                        return result
                return result

        # No arm matched and no else — return None silently
        return None

    def _instance_is_a(self, instance, class_name: str) -> bool:
        """Walk the inheritance chain to check type membership."""
        cls = instance.nekova_class
        while cls is not None:
            if cls.name == class_name:
                return True
            parent_name = getattr(cls, "parent", None)
            if parent_name and parent_name in self.env.vars:
                cls = self.env.vars[parent_name]
            else:
                break
        return False

    # ----------------------------------------------------------
    # Phase 7: Web DSL
    # ----------------------------------------------------------

    def _exec_RouteStatement(self, node: RouteStatement):
        """
        route GET "/path":
            <body>

        Registers a Flask route using the web module's server.
        The body is captured as a closure over the current env.
        """
        from nekova.web import web_module as wm
        from nekova.web.request import NEKOVARequest
        from nekova.web.response import (
            NEKOVAResponse, text_response, json_response, html_response
        )

        # Ensure a server exists
        if wm._server is None:
            wm._web_app("NEKOVA Web App")

        body_stmts = node.body
        interpreter = self

        def handler(request: NEKOVARequest):
            # Create a child env so route body has a fresh scope
            child_env = Environment(parent=interpreter.env)
            old_env   = interpreter.env
            interpreter.env = child_env

            # Expose `request` in the handler scope
            child_env.set("request", _RequestObject(request))
            # Expose response helpers
            child_env.set("html",    lambda c: html_response(str(c)))
            child_env.set("json",    lambda d: json_response(d))
            child_env.set("text",    lambda c: text_response(str(c)))

            result = None
            try:
                for stmt in body_stmts:
                    result = interpreter._execute_node(stmt)
            except ReturnSignal as rs:
                result = rs.value
            finally:
                interpreter.env = old_env

            if isinstance(result, NEKOVAResponse):
                return result
            if result is None:
                return text_response("")
            return text_response(str(result))

        wm._server.router.add(node.path, handler, methods=[node.method])

    def _exec_ServeStatement(self, node: ServeStatement):
        """
        serve port: 8080
        Starts the web server (blocks until Ctrl+C).
        """
        from nekova.web import web_module as wm

        port = 8000
        if node.port_expr is not None:
            port = int(self._execute_node(node.port_expr))

        wm._web_start(port)


    # ----------------------------------------------------------

    def _exec_ThinkAsStatement(self, node):
        """
        Execute:
            think "prompt" as json
            think "prompt" as list
            think "prompt" as bool
            think "prompt" as schema {"name": "text"}
        """
        self._sandbox_guard("think")
        from nekova.ai.providers import get_provider
        from nekova.ai.think_engine import ask_structured

        prompt = str(self._execute_node(node.prompt))
        fmt    = node.as_format
        self._check_prompt_injection(prompt)

        # Phase 22: `mock think as <value>` short-circuits the real
        # AI call — the mock value is returned as-is, no coercion
        # to the requested `as` format, since the person mocking it
        # controls exactly what comes back.
        mock = getattr(self, "_think_mock", _NO_MOCK)
        if mock is not _NO_MOCK:
            if node.variable:
                self.env.set(node.variable, mock)
            return mock

        # Evaluate schema if present (explicit `as schema {...}`)
        schema = None
        if node.schema is not None:
            schema = self._execute_node(node.schema)
            if not isinstance(schema, dict):
                schema = None

        # Phase 25: think "..." as <ShapeName> — a previously defined
        # `shape` used directly as the output format. Builds an
        # implicit schema from the shape's own field list, then
        # coerces the AI's response through the shape's real
        # constructor afterward, so `as User` gets the exact same
        # type validation a manual `User(...)` call would.
        shape_name_matched = None
        if schema is None and fmt not in ("json", "list", "bool", "text", "number", "schema"):
            shapes = getattr(self, "_shapes", {})
            # Format identifiers are lowercased by the parser (so
            # `as JSON` and `as json` behave the same) — but shape
            # names are typically capitalized ('User'), so match
            # case-insensitively against the real shape registry.
            real_name = next((n for n in shapes if n.lower() == fmt), None)
            shape_fields = shapes.get(real_name) if real_name else None
            if shape_fields is not None:
                schema = {fname: ftype for fname, ftype, _default in shape_fields}
                shape_name_matched = real_name
                fmt = "schema"

        try:
            provider = get_provider()
            if node.model is not None:
                provider.model = self._execute_node(node.model)
            result   = self._call_ai_with_visible_retry(lambda: ask_structured(
                provider, prompt, fmt,
                schema=schema,
                timeout=self._get_think_timeout(),
                debug=self._debug_ai,
            ))
            # ask_structured's _coerce_schema already type-coerced every
            # field against the schema built from the shape above — no
            # need to re-run it through the shape's own constructor
            # (which only accepts positional args, not the kwargs a
            # dict naturally provides). Just tag it as that shape.
            if shape_name_matched is not None and isinstance(result, dict):
                result["__shape__"] = shape_name_matched
        except Exception as e:
            if node.on_error is not None:
                result = self._execute_node(node.on_error)
            else:
                result = f"[think error: {e}]"
        else:
            self._check_think_budget(node, prompt, result)
            self._track_ai_usage(prompt, result)

        if node.variable:
            self.env.set(node.variable, result)

        return result

    # ----------------------------------------------------------
    # Phase 9: Remember / Recall / Forget
    # ----------------------------------------------------------

    def _exec_RememberStatement(self, node):
        """remember "key" = value"""
        from nekova.ai.memory_store import remember as _remember
        key   = str(self._execute_node(node.key_expr))
        value = self._execute_node(node.value_expr)
        _remember(key, value)
        return value

    def _exec_RecallStatement(self, node):
        """recall "key"  or  recall "key" or <default>"""
        from nekova.ai.memory_store import recall as _recall
        key      = str(self._execute_node(node.key_expr))
        _sentinel = object()
        result   = _recall(key, _sentinel)
        if result is _sentinel:
            # Key not found — use default if provided, else None
            if node.default is not None:
                result = self._execute_node(node.default)
            else:
                result = None  # silently return None for missing keys

        if node.variable:
            self.env.set(node.variable, result)

        return result

    def _exec_ForgetStatement(self, node):
        """forget "key"  or  forget all"""
        from nekova.ai.memory_store import forget as _forget, forget_all as _forget_all
        if node.forget_all:
            _forget_all()
        else:
            key = str(self._execute_node(node.key_expr))
            _forget(key)
        return None


    # ── Phase 15: New execution methods ──────────────────────

    def _exec_PassStatement(self, node):
        """pass — no-op."""
        return None

    def _exec_RaiseStatement(self, node):
        """raise <expr>"""
        value = self._execute_node(node.expression)
        raise NEKOVARaiseError(value, line=getattr(node, "line", 0))

    def _exec_AssertStatement(self, node):
        """assert <condition> [, message]"""
        result = self._execute_node(node.condition)
        if not self._is_truthy(result):
            msg = "Assertion failed"
            if node.message is not None:
                msg = str(self._execute_node(node.message))
            raise NEKOVAAssertionError(msg, line=getattr(node, "line", 0))
        return None

    def _exec_TernaryExpression(self, node):
        """<true_val> if <condition> else <false_val>"""
        condition = self._execute_node(node.condition)
        if self._is_truthy(condition):
            return self._execute_node(node.true_expr)
        return self._execute_node(node.false_expr)

    def _exec_SliceExpression(self, node):
        """items[start:stop:step]"""
        obj = self._execute_node(node.obj)
        start = self._execute_node(node.start) if node.start is not None else None
        stop  = self._execute_node(node.stop)  if node.stop  is not None else None
        step  = self._execute_node(node.step)  if node.step  is not None else None
        try:
            return obj[start:stop:step]
        except TypeError:
            raise NEKOVARuntimeError(
                f"Cannot slice '{type(obj).__name__}'.\n"
                "  Slicing works on lists and strings."
            )


    # ══════════════════════════════════════════════════════════
    # Phase 17 — Power User Layer Executors
    # ══════════════════════════════════════════════════════════

    # ── generators / yield ────────────────────────────────────

    def _exec_YieldStatement(self, node: YieldStatement):
        """yield value — raises YieldSignal caught by generator machinery."""
        value = self._execute_node(node.expression) if node.expression else None
        raise _YieldSignal(value)

    def _exec_TypedTaskStatement(self, node: TypedTaskStatement):
        """
        Typed task with param type hints and optional return type.
        Checks if any param uses `yield` — if so, registers a generator factory.
        """
        # Check if body contains yield (makes it a generator)
        is_gen = self._body_has_yield(node.body)

        if is_gen:
            self._register_generator_task(node)
        else:
            # Treat like a regular task but enforce types at call time
            node.closure_env = self.env
            self.env.set(node.name, node)
        return None

    def _body_has_yield(self, body: list) -> bool:
        """Recursively check if a body contains a YieldStatement."""
        from nekova.parser.nodes import YieldStatement as YS
        for stmt in body:
            if isinstance(stmt, YS):
                return True
            for attr in ("body", "then_body", "else_body", "try_body",
                         "catch_body", "finally_body"):
                sub = getattr(stmt, attr, None)
                if isinstance(sub, list) and self._body_has_yield(sub):
                    return True
        return False

    def _register_generator_task(self, node: TypedTaskStatement):
        """Register a generator factory function."""
        interp = self

        def _generator_factory(*args):
            return _NEKOVAGenerator(node, args, interp)

        _generator_factory.__name__ = node.name
        _generator_factory._is_generator = True
        self.env.set(node.name, _generator_factory)

    # ── decorators ────────────────────────────────────────────

    def _exec_DecoratorStatement(self, node: DecoratorStatement):
        """
        Apply decorator to the target task.
        @memoize
        task fib(n): ...
        Equivalent to:  fib = memoize(fib)
        """
        # Execute the inner task first (registers it)
        self._execute_node(node.target)

        # Get the task name from the target
        target = node.target
        # Unwrap nested decorators to find the innermost task name
        while isinstance(target, DecoratorStatement):
            target = target.target
        task_name = target.name

        # Get the registered task/function
        task_fn = self.env.get(task_name)

        # Evaluate the decorator expression
        decorator = self._execute_node(node.decorator_expr)

        # Apply: task = decorator(task)
        # decorator may be a TaskStatement, TypedTaskStatement, or Python callable
        if isinstance(decorator, TypedTaskStatement):
            result = self._call_typed_task(decorator, [task_fn])
        elif isinstance(decorator, TaskStatement):
            result = self._call_task(decorator, [task_fn])
        elif callable(decorator):
            result = decorator(task_fn)
        else:
            raise NEKOVARuntimeError(
                f"Decorator '@{node.decorator_expr}' is not callable."
            )
        self.env.set(task_name, result)
        return None

    # ── error types ───────────────────────────────────────────

    def _exec_ErrorDefinition(self, node: ErrorDefinition):
        """
        error NetworkError:
            message str
            code    int = 0
        Registers a raiseable error constructor.
        """
        error_name = node.name
        fields = node.fields
        interp = self

        TYPE_COERCE = {
            "str":   str,
            "int":   int,
            "float": float,
            "bool":  bool,
            "any":   lambda v: v,
        }

        def _error_constructor(*args, **kwargs):
            instance = {"__error__": error_name}
            for i, (fname, ftype, fdefault) in enumerate(fields):
                if i < len(args):
                    raw = args[i]
                elif fname in kwargs:
                    raw = kwargs[fname]
                elif fdefault is not None:
                    raw = interp._execute_node(fdefault)
                else:
                    raise NEKOVARuntimeError(
                        f"Error '{error_name}' requires field '{fname}'."
                    )
                coerce = TYPE_COERCE.get(ftype, lambda v: v)
                try:
                    instance[fname] = coerce(raw)
                except (ValueError, TypeError):
                    instance[fname] = raw
            return instance

        # Register the constructor
        self.env.set(error_name, _error_constructor)

        # Store schema
        if not hasattr(self, "_error_types"):
            self._error_types = {}
        self._error_types[error_name] = fields

        return None

    # ── type-enforced task calls ──────────────────────────────

    def _call_typed_task(self, task: TypedTaskStatement, args: list):
        """
        Call a typed task — enforces type hints on arguments.
        params: (name, type_hint, default, is_vararg)
        """
        from nekova.interpreter.environment import Environment
        from nekova.runtime import ReturnSignal

        TYPE_VALIDATORS = {
            "int":   (int,   "an integer"),
            "float": (float, "a float"),
            "str":   (str,   "a string"),
            "bool":  (bool,  "a boolean"),
            "list":  (list,  "a list"),
            "dict":  (dict,  "a dict"),
        }

        closure   = getattr(task, "closure_env", self.globals)
        local_env = Environment(parent=closure)
        prev_env  = self.env
        prev_globals = self._global_names
        self._global_names = set()

        params = task.params  # (name, type_hint, default, is_vararg)

        # Check for vararg
        vararg_idx = next((i for i, p in enumerate(params) if p[3]), None)

        if vararg_idx is not None:
            positional = params[:vararg_idx]
            vararg_name = params[vararg_idx][0]
            for (pname, phint, _, _), val in zip(positional, args):
                self._check_type(pname, val, phint, TYPE_VALIDATORS, task.name)
                local_env.set(pname, val)
            local_env.set(vararg_name, list(args[len(positional):]))
        else:
            required = sum(1 for (_, _, d, _) in params if d is None)
            if len(args) < required or len(args) > len(params):
                raise NEKOVARuntimeError(
                    f"Task '{task.name}' expects "
                    f"{required}–{len(params)} args, got {len(args)}."
                )
            for i, (pname, phint, default, _) in enumerate(params):
                val = args[i] if i < len(args) else self._execute_node(default)
                self._check_type(pname, val, phint, TYPE_VALIDATORS, task.name)
                local_env.set(pname, val)

        self.env = local_env
        result = None
        try:
            for stmt in task.body:
                self._execute_node(stmt)
        except ReturnSignal as r:
            result = r.value
        finally:
            self.env = prev_env
            self._global_names = prev_globals

        # Check return type
        if task.return_type and task.return_type in TYPE_VALIDATORS:
            py_type, label = TYPE_VALIDATORS[task.return_type]
            if result is not None and not isinstance(result, py_type):
                try:
                    result = py_type(result)
                except (ValueError, TypeError):
                    raise NEKOVARuntimeError(
                        f"Task '{task.name}' declared return type "
                        f"'{task.return_type}' but returned "
                        f"{type(result).__name__}."
                    )
        return result

    def _check_type(self, pname, val, phint, validators, task_name, kind="Task"):
        """Enforce a type hint on a parameter value."""
        if not phint or phint == "any":
            return
        if phint in validators:
            py_type, label = validators[phint]
            if val is not None and not isinstance(val, py_type):
                # Try coercion first
                try:
                    return py_type(val)
                except (ValueError, TypeError):
                    raise NEKOVARuntimeError(
                        f"{kind} '{task_name}': parameter '{pname}' "
                        f"expects {label}, got {type(val).__name__}."
                    )


    # ══════════════════════════════════════════════════════════
    # Phase 16 — Standout Feature Executors
    # ══════════════════════════════════════════════════════════

    def _exec_SpeakStatement(self, node: SpeakStatement):
        """speak <expr>  — text-to-speech output.

        Always prints the spoken text to stdout (with a [speak] prefix
        when TTS is unavailable) so programs and tests can capture it.
        TTS runs asynchronously in the background when available.
        """
        self._sandbox_guard("speak")
        text = self._to_string(self._execute_node(node.expression))

        # Always echo to stdout so tests and piped programs can read it
        print(text)

        # Fire TTS in background (non-blocking) when available
        try:
            import subprocess, shutil
            if shutil.which("say"):            # macOS
                subprocess.Popen(["say", text])
            elif shutil.which("espeak"):       # Linux
                subprocess.Popen(["espeak", text])
            elif shutil.which("espeak-ng"):    # Linux alt
                subprocess.Popen(["espeak-ng", text])
            elif shutil.which("powershell"):   # Windows
                subprocess.Popen([
                    "powershell", "-Command",
                    f"Add-Type -AssemblyName System.Speech; "
                    f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak({text!r})"
                ])
        except Exception:
            pass  # TTS failure is silent — stdout output already happened

        return text

    def _exec_ListenExpression(self, node: ListenExpression):
        """listen  — speech-to-text, returns transcribed string."""
        self._sandbox_guard("listen")
        prompt = None
        if node.prompt is not None:
            prompt = self._to_string(self._execute_node(node.prompt))

        from nekova.ai.memory_store import add_to_conversation

        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                if prompt:
                    print(f"[listen] {prompt}")
                else:
                    print("[listen] Listening...")
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=10)
            result = r.recognize_google(audio)
            add_to_conversation("user", result)
            return result
        except ImportError:
            # SpeechRecognition not installed — fall back to input()
            msg = prompt if prompt else "Listening (type instead): "
            result = input(msg)
            add_to_conversation("user", result)
            return result
        except Exception as e:
            raise NEKOVARuntimeError(
                f"listen failed: {e}\n"
                "  Install SpeechRecognition: pip install SpeechRecognition"
            )

    def _exec_EveryStatement(self, node: EveryStatement):
        """every <N><unit>:  — scheduled repeated execution.

        Finite loops (max_runs set, or body uses break) run
        synchronously in the current thread.
        Infinite loops run in a background daemon thread.
        """
        import time, threading

        interval_val = self._execute_node(node.interval_value)
        unit         = node.interval_unit
        multipliers  = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}
        seconds      = float(interval_val) * multipliers.get(unit, 1)
        max_runs     = int(node.max_runs) if node.max_runs is not None else None

        # ── finite loop error handler ──────────────────────────
        def _run_body_finite():
            """
            Run body once for a finite loop.
            Propagates all exceptions so the caller sees them.
            Returns 'break', 'continue', or 'ok'.
            """
            try:
                self._execute_block(node.body, new_scope=False)
                return "ok"
            except BreakSignal:
                return "break"
            except ContinueSignal:
                return "continue"
            # All other exceptions propagate to the caller — finite loops
            # must not silently swallow errors. The programmer should know.

        # ── infinite loop error handler ────────────────────────
        def _run_body_infinite():
            """
            Run body once for an infinite loop.
            Prints a full error message (with type and value) and
            continues — stopping an infinite loop on every error
            would be too disruptive for long-running background tasks.
            Returns 'break', 'continue', or 'ok'.
            """
            try:
                self._execute_block(node.body, new_scope=False)
                return "ok"
            except BreakSignal:
                return "break"
            except ContinueSignal:
                return "continue"
            except Exception as e:
                # Print full error so the programmer can see what failed
                err_type = type(e).__name__
                err_msg  = str(e).strip() or "(no message)"
                print(f"[every] {err_type}: {err_msg}")
                return "ok"

        if max_runs is not None:
            # Finite — run synchronously and let errors propagate
            for _ in range(max_runs):
                result = _run_body_finite()
                if result == "break":
                    break
                if _ < max_runs - 1:
                    time.sleep(seconds)
        else:
            # Infinite — run in a background daemon thread
            stop_event = threading.Event()

            def _loop():
                while not stop_event.is_set():
                    result = _run_body_infinite()
                    if result == "break":
                        stop_event.set()
                        break
                    if not stop_event.is_set():
                        stop_event.wait(seconds)

            t = threading.Thread(target=_loop, daemon=True)
            t.start()
            print(f"[every] Running every {interval_val}{unit} (Ctrl+C to stop)")
            try:
                t.join()
            except KeyboardInterrupt:
                stop_event.set()

        return None

    # ── test / expect ─────────────────────────────────────────

    def _exec_TestBlock(self, node: TestBlock):
        """
        test "label":
            expect expr == val
        Runs all expect statements, collects results, prints summary.
        """
        passed = 0
        failed = 0
        errors = []

        # Push test context so expect knows its label
        prev_test = getattr(self, "_current_test", None)
        self._current_test = node.label
        prev_mock = getattr(self, "_think_mock", _NO_MOCK)

        for stmt in node.body:
            try:
                self._execute_node(stmt)
                # If we get here without ExpectFailed, it passed
                if isinstance(stmt, ExpectStatement):
                    passed += 1
            except _ExpectFailed as e:
                failed += 1
                errors.append(str(e))
            except Exception as e:
                failed += 1
                errors.append(f"Error: {e}")

        self._current_test = prev_test
        self._think_mock = prev_mock

        # Print result
        status = "✓ PASS" if failed == 0 else "✗ FAIL"
        print(f"  {status}  {node.label}  ({passed}/{passed+failed})")
        for err in errors:
            print(f"       └─ {err}")

        # Track totals on the interpreter for final summary
        if not hasattr(self, "_test_totals"):
            self._test_totals = {"passed": 0, "failed": 0}
        self._test_totals["passed"] += passed
        self._test_totals["failed"] += failed

        return {"passed": passed, "failed": failed}

    def _exec_ExpectStatement(self, node: ExpectStatement):
        """expect <expr>  — must evaluate to truthy, else raises _ExpectFailed."""
        result = self._execute_node(node.expression)
        if not self._is_truthy(result):
            expr_repr = repr(node.expression)
            raise _ExpectFailed(
                f"expect failed: {expr_repr} → got {self._to_string(result)!r}"
            )
        return result

    def _exec_MockStatement(self, node: MockStatement):
        """
        Execute:  mock think as "sports"
        Stubs `think`/`think ... as ...` for the rest of the
        enclosing test block — see _exec_ThinkStatement /
        _exec_ThinkAsStatement, and the save/restore in
        _exec_TestBlock that scopes this to just that test.
        """
        if node.target != "think":
            raise NEKOVARuntimeError(
                f"'mock' doesn't know how to mock '{node.target}' — "
                "only 'think' is supported right now."
            )
        self._think_mock = self._execute_node(node.value)
        return None

    # ── imagine ───────────────────────────────────────────────

    def _exec_ImagineStatement(self, node: ImagineStatement):
        """imagine <prompt> [as url|path|file|base64]"""
        self._sandbox_guard("imagine")
        prompt = self._to_string(self._execute_node(node.prompt))
        fmt = node.result_format
        # 'file' is an alias for 'path' — same meaning ("give me a
        # local file"), just the more intuitive word for it.
        if fmt == "file":
            fmt = "path"

        try:
            result = self._imagine_cached(prompt, fmt)
        except Exception as e:
            raise NEKOVARuntimeError(
                f"imagine failed: {e}\n"
                "  Check your AI provider config in nekova.toml."
            )

        if node.result_var:
            self.env.set(node.result_var, result)
        return result

    def _imagine_cached(self, prompt: str, fmt: str):
        """
        Phase 25: local caching for imagine — an identical
        (prompt, format) pair during a dev loop returns the cached
        result instead of re-generating (and re-billing) it. Cached
        on disk under .nekova_cache/imagine/ so it persists across
        separate script runs, not just within one.
        """
        import hashlib, json, os

        cache_dir = os.path.join(".nekova_cache", "imagine")
        key = hashlib.sha256(f"{fmt}:{prompt}".encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, f"{key}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                return cached["result"]
            except (OSError, ValueError, KeyError):
                pass  # corrupt cache entry — fall through and regenerate

        result = self._imagine(prompt, fmt)

        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"prompt": prompt, "format": fmt, "result": result}, f)
        except OSError:
            pass  # caching is a nice-to-have — don't fail the call over it

        return result

    def _imagine(self, prompt: str, fmt: str = "url"):
        """Call the configured image generation provider."""
        try:
            from nekova.toml_loader import load_config
            cfg = load_config()
            provider = getattr(cfg, "imagine_provider", "openai") if cfg else "openai"
        except Exception:
            provider = "openai"

        if provider == "openai":
            return self._imagine_openai(prompt, fmt)
        elif provider == "stability":
            return self._imagine_stability(prompt, fmt)
        else:
            # Mock for testing
            return f"https://imagine.nekova.dev/mock?prompt={prompt.replace(' ', '+')}"

    def _imagine_openai(self, prompt: str, fmt: str):
        import os, urllib.request, json
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            # Return mock URL in dev mode
            return f"https://imagine.nekova.dev/mock?prompt={prompt.replace(' ', '+')}"

        payload = json.dumps({
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url" if fmt in ("url", "path") else "b64_json"
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if fmt == "url":
            return data["data"][0]["url"]
        elif fmt == "base64":
            return data["data"][0]["b64_json"]
        elif fmt == "path":
            import tempfile, urllib.request as urlr
            url = data["data"][0]["url"]
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            urlr.urlretrieve(url, tmp.name)
            return tmp.name

    def _imagine_stability(self, prompt: str, fmt: str):
        import os, urllib.request, json, base64, tempfile
        api_key = os.environ.get("STABILITY_API_KEY", "")
        if not api_key:
            return f"https://imagine.nekova.dev/mock?prompt={prompt.replace(' ', '+')}"

        payload = json.dumps({
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7, "height": 1024, "width": 1024, "samples": 1
        }).encode()
        req = urllib.request.Request(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}",
                     "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        b64 = data["artifacts"][0]["base64"]
        if fmt == "base64":
            return b64
        img_bytes = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(img_bytes)
        tmp.close()
        if fmt == "path":
            return tmp.name
        return f"file://{tmp.name}"

    # ── shape ─────────────────────────────────────────────────

    def _exec_ShapeDefinition(self, node: ShapeDefinition):
        """
        shape User:
            name str
            age  int
        Registers a validated constructor in the environment.
        """
        shape_name = node.name
        fields = node.fields  # [(name, type_str, default)]

        TYPE_VALIDATORS = {
            "str":   (str,   lambda v: str(v)),
            "int":   (int,   lambda v: int(v)),
            "float": (float, lambda v: float(v)),
            "bool":  (bool,  lambda v: bool(v)),
            "list":  (list,  lambda v: list(v) if not isinstance(v, list) else v),
            "dict":  (dict,  lambda v: v if isinstance(v, dict) else {}),
            "any":   (object, lambda v: v),
        }

        interp = self   # capture for closure

        def _constructor(**kwargs):
            instance = {}
            for fname, ftype, fdefault in fields:
                if fname in kwargs:
                    raw = kwargs[fname]
                elif fdefault is not None:
                    raw = interp._execute_node(fdefault)
                else:
                    raise NEKOVARuntimeError(
                        f"Shape '{shape_name}' requires field '{fname}'."
                    )
                # Type coercion/validation
                if ftype in TYPE_VALIDATORS:
                    py_type, coerce = TYPE_VALIDATORS[ftype]
                    try:
                        instance[fname] = coerce(raw)
                    except (ValueError, TypeError):
                        raise NEKOVARuntimeError(
                            f"Shape '{shape_name}': field '{fname}' "
                            f"must be {ftype}, got {type(raw).__name__}."
                        )
                else:
                    instance[fname] = raw
            instance["__shape__"] = shape_name
            return instance

        # Also support positional call: User("Alice", 30)
        def _positional_constructor(*args):
            if len(args) > len(fields):
                raise NEKOVARuntimeError(
                    f"Shape '{shape_name}' takes {len(fields)} fields, "
                    f"got {len(args)}."
                )
            kw = {}
            for i, val in enumerate(args):
                kw[fields[i][0]] = val
            return _constructor(**kw)

        self.env.set(shape_name, _positional_constructor)
        # Store schema for introspection
        if not hasattr(self, "_shapes"):
            self._shapes = {}
        self._shapes[shape_name] = fields
        return None

    # ── watch ─────────────────────────────────────────────────

    def _exec_WatchStatement(self, node: WatchStatement):
        """watch <file|expr>:  — re-runs body when target changes."""
        import time, threading, os

        if node.is_file:
            # File watcher
            filepath = self._to_string(self._execute_node(node.target))
            filepath = os.path.expanduser(filepath)

            def _get_mtime():
                try:
                    return os.path.getmtime(filepath)
                except FileNotFoundError:
                    return None

            last_mtime = _get_mtime()
            print(f"[watch] Watching {filepath!r} (Ctrl+C to stop)")

            try:
                while True:
                    time.sleep(0.5)
                    cur_mtime = _get_mtime()
                    if cur_mtime != last_mtime:
                        last_mtime = cur_mtime
                        try:
                            self._execute_block(node.body)
                        except Exception as e:
                            print(f"[watch] Error: {e}")
            except KeyboardInterrupt:
                print(f"[watch] Stopped watching {filepath!r}")
        else:
            # Expression watcher — run body when value changes
            last_val = self._execute_node(node.target)
            print("[watch] Watching expression (Ctrl+C to stop)")
            try:
                while True:
                    time.sleep(0.1)
                    cur_val = self._execute_node(node.target)
                    if cur_val != last_val:
                        last_val = cur_val
                        try:
                            self._execute_block(node.body)
                        except Exception as e:
                            print(f"[watch] Error: {e}")
            except KeyboardInterrupt:
                print("[watch] Stopped")

        return None


class _RequestObject:
    """Wraps NEKOVARequest for use inside route handlers.

    Exposes:
        request.method   → "GET"
        request.path     → "/api/chat"
        request.body     → raw body string  OR dict if JSON
        request.params   → query params dict
        request.headers  → headers dict
        request.json     → parsed JSON dict
    """

    def __init__(self, req):
        self._req = req

    def __getattr__(self, key):
        req = object.__getattribute__(self, "_req")
        if key == "body":
            # If JSON was parsed, expose the dict; else raw string
            return req.json if req.json else req.body
        if hasattr(req, key):
            return getattr(req, key)
        raise AttributeError(f"request has no attribute '{key}'")

    def __repr__(self):
        req = object.__getattribute__(self, "_req")
        return f"Request({req.method} {req.path})"


class _DBObject:
    """
    Wraps a DatabaseConnection + QueryBuilder so NEKOVA code
    can call db.create(), db.insert(), db.query(), etc.

    Usage in NEKOVA:
        db = connect("app.db")
        db.create("users", {"name": "text", "email": "text"})
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com"})
        let rows = db.query("users").where("name", "Emmanuel").all()
    """

    def __init__(self, filepath: str):
        from nekova.database.connection import DatabaseConnection
        from nekova.database.query import QueryBuilder
        self._conn = DatabaseConnection(filepath)
        self._conn.connect()
        self._qb   = QueryBuilder(self._conn)

    # ── DDL ────────────────────────────────────────────────────

    def create(self, table: str, schema):
        """
        db.create("users", {"name": "text", "email": "text"})
        schema can be dict  → {col: type, ...}
                  or string → "name text, email text"
        """
        if isinstance(schema, dict):
            columns = {k: v.upper() for k, v in schema.items()}
        else:
            columns = {}
            for part in str(schema).split(","):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                if len(pieces) >= 2:
                    columns[pieces[0]] = pieces[1].upper()
                elif len(pieces) == 1:
                    columns[pieces[0]] = "TEXT"
        self._qb.create_table(table, columns)
        return self

    def drop(self, table: str):
        self._qb.drop_table(table)
        return self

    def exists(self, table: str) -> bool:
        return self._qb.table_exists(table)

    def tables(self) -> list:
        return self._conn.tables()

    # ── DML ────────────────────────────────────────────────────

    def insert(self, table: str, data: dict) -> int:
        """db.insert("users", {"name": "Emmanuel", "email": "e@x.com"})"""
        if not isinstance(data, dict):
            raise RuntimeError(
                "db.insert() requires a dict, e.g. {'name': 'Emmanuel'}"
            )
        return self._qb.insert(table, data)

    def update(self, table: str, data: dict, where: str = None) -> bool:
        """db.update("users", {"email": "new@x.com"}, "name = 'Emmanuel'")"""
        return self._qb.update(table, data, where=where)

    def delete(self, table: str, where: str = None) -> bool:
        """db.delete("users", "id = 1")"""
        return self._qb.delete(table, where=where)

    # ── Query builder ──────────────────────────────────────────

    def query(self, table: str) -> "_DBQuery":
        return _DBQuery(self._qb, table)

    def find(self, table: str, where: str = None) -> list:
        rows = self._qb.select(table, where=where)
        return [dict(r) for r in rows]

    def find_one(self, table: str, where: str = None):
        row = self._qb.find_one(table, where) if where else None
        return dict(row) if row else None

    def count(self, table: str, where: str = None) -> int:
        return self._qb.count(table, where=where)

    def sql(self, raw_sql: str) -> list:
        """Execute raw SQL and return list of row dicts."""
        rows = self._conn.execute(raw_sql)
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()

    def __repr__(self):
        return f"DB({self._conn.filepath})"


class _DBQuery:
    """Chainable query builder returned by db.query('table')."""

    def __init__(self, qb, table: str):
        self._qb      = qb
        self._table   = table
        self._where   = None
        self._order   = None
        self._limit   = None

    def where(self, col: str, val) -> "_DBQuery":
        """db.query("users").where("name", "Emmanuel")"""
        if isinstance(val, str):
            clause = f"{col} = '{val}'"
        else:
            clause = f"{col} = {val}"
        if self._where:
            self._where += f" AND {clause}"
        else:
            self._where = clause
        return self

    def order(self, col: str, direction: str = "ASC") -> "_DBQuery":
        self._order = f"{col} {direction.upper()}"
        return self

    def limit(self, n: int) -> "_DBQuery":
        self._limit = int(n)
        return self

    def all(self) -> list:
        rows = self._qb.select(
            self._table,
            where=self._where,
            order_by=self._order,
            limit=self._limit,
        )
        return [_DBRow(dict(r)) for r in rows]

    def first(self):
        rows = self._qb.select(
            self._table,
            where=self._where,
            order_by=self._order,
            limit=1,
        )
        return _DBRow(dict(rows[0])) if rows else None

    def count(self) -> int:
        return self._qb.count(self._table, where=self._where)

    def __repr__(self):
        return f"DBQuery({self._table}, where={self._where!r})"


class _DBRow:
    """
    A single database row — fields accessible as attributes.
        user.id, user.name, user.email
    Also subscriptable: user["name"]
    """

    def __init__(self, data: dict):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, key):
        data = object.__getattribute__(self, "_data")
        if key in data:
            return data[key]
        raise AttributeError(
            f"Row has no column '{key}'. Available: {list(data.keys())}"
        )

    def __getitem__(self, key):
        data = object.__getattribute__(self, "_data")
        return data[key]

    def __repr__(self):
        data = object.__getattribute__(self, "_data")
        pairs = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"Row({pairs})"

    def to_dict(self) -> dict:
        return dict(object.__getattribute__(self, "_data"))

    def keys(self):
        return object.__getattribute__(self, "_data").keys()

    # ----------------------------------------------------------
    # Phase 9: Structured Think (think ... as json/list/bool/schema)

# ── NEKOVA Generator Runtime ──────────────────────────────────

class _NEKOVAGenerator:
    """
    Truly lazy sequence produced by a generator task (one with yield).

    Uses a background thread and a queue so values are produced one at a
    time on demand — infinite generators work, and side-effects happen at
    iteration time rather than at construction time.

    Protocol:
      - Producer thread runs the task body, putting each yielded value
        onto a queue.  A sentinel (_DONE) marks exhaustion.
      - The consumer (__next__) blocks on queue.get() until a value or
        the sentinel arrives.
    """

    _DONE = object()  # sentinel

    def __init__(self, task_node, args, interp):
        self._task   = task_node
        self._args   = args
        self._interp = interp
        self._queue  = None   # created lazily on first iteration
        self._thread = None

    def _start(self):
        """Spin up the producer thread."""
        import queue
        import threading
        from nekova.interpreter.environment import Environment
        from nekova.runtime import ReturnSignal
        from nekova.interpreter.exceptions import _YieldSignal

        q      = queue.Queue(maxsize=1)   # back-pressure: one item ahead
        task   = self._task
        args   = self._args
        interp = self._interp

        def _producer():
            closure   = getattr(task, "closure_env", interp.globals)
            local_env = Environment(parent=closure)
            prev_env  = interp.env
            interp.env = local_env

            # Bind params
            params = task.params
            for i, param in enumerate(params):
                if len(param) == 4:
                    pname, _, default, is_vararg = param
                else:
                    pname, default, is_vararg = param
                if is_vararg:
                    local_env.set(pname, list(args[i:]))
                elif i < len(args):
                    local_env.set(pname, args[i])
                elif default is not None:
                    local_env.set(pname, interp._execute_node(default))

            original_yield = interp._exec_YieldStatement

            def _lazy_yield(node):
                value = interp._execute_node(node.expression) if node.expression else None
                q.put(value)           # blocks until consumer calls next()

            interp._exec_YieldStatement = _lazy_yield

            try:
                for stmt in task.body:
                    try:
                        interp._execute_node(stmt)
                    except ReturnSignal:
                        break
                    except _YieldSignal as y:
                        q.put(y.value)
            except Exception:
                pass   # generator body errors stop iteration silently
            finally:
                interp._exec_YieldStatement = original_yield
                interp.env = prev_env
                q.put(_NEKOVAGenerator._DONE)   # signal exhaustion

        self._queue  = q
        self._thread = threading.Thread(target=_producer, daemon=True)
        self._thread.start()

    def __iter__(self):
        if self._queue is None:
            self._start()
        return self

    def __next__(self):
        if self._queue is None:
            self._start()
        value = self._queue.get()
        if value is _NEKOVAGenerator._DONE:
            raise StopIteration
        return value

    def __repr__(self):
        return f"<generator {self._task.name}>"