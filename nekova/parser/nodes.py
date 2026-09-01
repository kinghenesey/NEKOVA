from dataclasses import dataclass


class Node:
    """Base class for all AST nodes."""
    line: int = 0  # source line — stamped by the parser at construction time


# ── Program ───────────────────────────────────────────────────

class Program(Node):
    """
    The root node — represents the entire NEKOVA program.
    Every other node lives inside this one.
    """
    def __init__(self, statements: list):
        self.statements = statements

    def __repr__(self):
        return f"Program({len(self.statements)} statements)"


# ── Literals ──────────────────────────────────────────────────

class IntegerLiteral(Node):
    """A whole number like 42."""
    def __init__(self, value: int):
        self.value = value

    def __repr__(self):
        return f"Integer({self.value})"


class FloatLiteral(Node):
    """A decimal number like 3.14."""
    def __init__(self, value: float):
        self.value = value

    def __repr__(self):
        return f"Float({self.value})"


class MoneyLiteral(Node):
    """
    A dollar-amount literal like $0.01 (Phase 26c) — used in a
    think budget clause to cap estimated spend rather than raw
    token count: `think "..." with budget: $0.01`.
    """
    def __init__(self, value: float):
        self.value = value

    def __repr__(self):
        return f"Money(${self.value})"


class StringLiteral(Node):
    """A string like "Hello"."""
    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return f"String({repr(self.value)})"


class FStringLiteral(Node):
    """
    An f-string like f"Hello {name}, you are {age}!".
    parts is a list of tuples: ('str', 'Hello ') or ('expr', <AST node>)
    """
    def __init__(self, parts: list):
        self.parts = parts

    def __repr__(self):
        return f"FString({self.parts})"


class BooleanLiteral(Node):
    """true or false."""
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"Boolean({self.value})"


class NullLiteral(Node):
    """null — the absence of a value."""
    def __repr__(self):
        return "Null"

class SetLiteral(Node):
    """
    A set of unique values.
    Example:
        let s = {1, 2, 3}
    Disambiguated from a dict at parse time (a dict entry always has
    a 'key: value' shape; a set element never does). Runtime value is
    a plain Python set built from NEKOVA_SET_UNION/INTERSECTION/
    DIFFERENCE builtins or the |, &, - operators (see interpreter).
    """
    def __init__(self, elements: list):
        self.elements = elements

    def __repr__(self):
        return f"Set({self.elements})"


class ConverseStatement(Node):
    """
    A multi-turn dialogue block:
        converse:
            think "ask a clarifying question about {topic}"
            listen
            think "respond based on what they said"

    Starts with a clean conversation history (previous turns from
    outside the block don't leak in), and every think/listen inside
    it automatically carries that history as context — the same
    memory_store conversation machinery think_engine.ask_structured
    already used, extended to cover plain 'think' and 'listen' too.
    """
    def __init__(self, body: list, line: int = 0):
        self.body = body
        self.line = line

    def __repr__(self):
        return f"Converse(body={len(self.body)} statements)"


class EnumDefinition(Node):
    """
    A first-class enum type.
    Example:
        enum Status: PENDING, ACTIVE, DONE
        show Status.ACTIVE     # "ACTIVE"
    Members are accessed via PropertyAccess (Status.ACTIVE), each
    evaluating to its own member name as a string — simple and
    readable, matching how NEKOVA shows values elsewhere.
    """
    def __init__(self, name: str, members: list, line: int = 0):
        self.name    = name
        self.members = members  # list of member name strings
        self.line    = line

    def __repr__(self):
        return f"Enum({self.name}, members={self.members})"


class SpreadElement(Node):
    """
    A '...expr' item inside a list or dict literal — expanded in place
    when the literal is built.
    Example:
        let combined = [...list_a, ...list_b]
        let merged   = {...defaults, ...overrides}
    """
    def __init__(self, expr: "Node"):
        self.expr = expr

    def __repr__(self):
        return f"Spread(...{self.expr})"


class ListLiteral(Node):
    """
    A list of values.
    Example:
        items = [1, 2, 3]
        names = ["Emmanuel", "Alice", "Bob"]
        mixed = [1, "hello", true]
    """
    def __init__(self, elements: list):
        self.elements = elements

    def __repr__(self):
        return f"List({self.elements})"

class TupleLiteral(Node):
    """
    An immutable, fixed-size grouping of values.
    Example:
        let pair = (1, 2)
        let solo = (1,)          # trailing comma required for 1 element
        let (x, y) = pair        # destructuring already accepted tuples
    Distinct from ListLiteral (mutable) — mirrors the SetLiteral
    precedent of giving a value with different semantics its own
    node rather than overloading ListLiteral. A bare parenthesized
    expression like (1 + 2) still returns the inner expression itself,
    not a TupleLiteral — only a comma inside the parens makes a tuple.
    Runtime value is a plain Python tuple, so item-assignment (t[0] = 1)
    fails naturally with a TypeError the interpreter already surfaces
    as a NEKOVA runtime error, giving immutability for free.
    """
    def __init__(self, elements: list):
        self.elements = elements

    def __repr__(self):
        return f"Tuple({self.elements})"


class IndexExpression(Node):
    """
    Access a list element by index.
    Example:
        items[0]
        names[1]
    """
    def __init__(self, collection: Node, index: Node):
        self.collection = collection
        self.index      = index

    def __repr__(self):
        return f"Index({self.collection}[{self.index}])"


class IndexAssignStatement(Node):
    """
    Assign a value to a list or dict by index/key.
    Example:
        items[0]   = "new"
        d["key"]   = 99
        matrix[i]  = row
    """
    def __init__(self, collection: Node, index: Node, value: Node):
        self.collection = collection
        self.index      = index
        self.value      = value

    def __repr__(self):
        return f"IndexAssign({self.collection}[{self.index}] = {self.value})"

class MethodCall(Node):
    """
    A method call on a value.
    Example:
        name.upper()
        items.length()
        text.replace("a", "b")
    """
    def __init__(self, object: Node,
                 method: str, args: list, optional: bool = False):
        self.object = object
        self.method = method
        self.args   = args
        self.optional = optional  # True if called via ?. — short-circuits to null

    def __repr__(self):
        return f"MethodCall({self.object}.{self.method})"

class PropertyAccess(Node):
    """
    Property access on an object (no parentheses).
    Example:
        args.name
        args.port
        response.status
    """
    def __init__(self, object: Node, property: str, optional: bool = False):
        self.object   = object
        self.property = property
        self.optional = optional  # True if accessed via ?. — short-circuits to null

    def __repr__(self):
        return f"PropertyAccess({self.object}.{self.property})"

class DictLiteral(Node):
    """
    A dictionary of key-value pairs.
    Example:
        person = {name: "Emmanuel", age: 20}
        config = {debug: true, port: 8000}
    """
    def __init__(self, pairs: list):
        # pairs is a list of (key, value) tuples
        self.pairs = pairs

    def __repr__(self):
        return f"Dict({len(self.pairs)} pairs)"


# ── Identifier ────────────────────────────────────────────────

class Identifier(Node):
    """
    A variable name like 'age' or 'name'.
    When the interpreter sees this it looks up the value
    in the current scope.
    """
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


# ── Expressions ───────────────────────────────────────────────

class BinaryOp(Node):
    """
    An operation between two values.
    Examples:
        age + 1
        name == "NEKOVA"
        x >= 18
    """
    def __init__(self, left: Node, operator: str, right: Node):
        self.left     = left
        self.operator = operator
        self.right    = right

    def __repr__(self):
        return f"BinaryOp({self.left} {self.operator} {self.right})"


class UnaryOp(Node):
    """
    An operation on a single value.
    Examples:
        not true
        -42
    """
    def __init__(self, operator: str, operand: Node):
        self.operator = operator
        self.operand  = operand

    def __repr__(self):
        return f"UnaryOp({self.operator} {self.operand})"


# ── Statements ────────────────────────────────────────────────

class AssignStatement(Node):
    """
    Assigns a value to a variable.
    Supports optional type hints:
        name = "Emmanuel"
        name: text = "Emmanuel"
        age: number = 25
        items: list = [1, 2, 3]
    """
    def __init__(self, name: str, value: Node, type_hint: str = None,
                 is_const: bool = False, is_declaration: bool = False):
        self.name      = name
        self.value     = value
        self.type_hint = type_hint  # e.g. "text", "number", "boolean", "list", "dict"
        self.is_const  = is_const
        # True for `let`/`const` (always binds in the *current* scope,
        # e.g. deliberately shadowing an outer variable of the same
        # name). False for a bare `name = value` reassignment, which
        # should walk up to mutate an existing binding in an enclosing
        # scope if the name isn't local — see
        # Interpreter._exec_AssignStatement for why this distinction
        # matters (it's what makes closures able to mutate captured
        # variables instead of always writing a fresh local).
        self.is_declaration = is_declaration or is_const

    def __repr__(self):
        prefix = "const " if self.is_const else ""
        if self.type_hint:
            return f"Assign({prefix}{self.name}: {self.type_hint} = {self.value})"
        return f"Assign({prefix}{self.name} = {self.value})"


class ShowStatement(Node):
    """
    Prints one or more values to the terminal (space-separated).
    Example:
        show "Hello"
        show "x =" x
    """
    def __init__(self, expression: Node, extra_expressions: list = None):
        self.expression        = expression
        self.extra_expressions = extra_expressions or []

    def __repr__(self):
        return f"Show({self.expression})"
    
@dataclass
class ThinkStatement(Node):
    """
    Represents a think statement — calls the AI provider inline.
    
    Standalone:  think "What should I build?"
    Captured:    thought = think "Analyze this market"
    Inline error handling:
        think "..." when error: "fallback value"
    
    'variable' is None for standalone usage.
    'prompt' is any expression (string literal, variable, f-string, etc.)
    'on_error' is an optional expression evaluated (and returned/assigned
    instead of a "[think error: ...]" string) if the AI call fails.
    """
    prompt: any
    variable: str = None
    line: int = 0
    on_error: any = None
    budget: any = None
    model: any = None

@dataclass
class PipelineStatement(Node):
    """
    Represents an agent communication pipeline.
    
    Simple:    researcher -> marketer -> reporter
    With seed: "Analyze this" -> researcher -> writer
    Captured:  report = "Analyze this" -> researcher -> writer
    
    'steps' is a list of expressions (identifiers or string literals).
    'variable' is None for standalone usage.
    """
    steps: list
    variable: str = None
    line: int = 0

@dataclass
class ModelStatement(Node):
    """
    Represents a model switching statement.
    
    Changes the active AI provider for all subsequent
    think and pipeline calls.
    
    Usage:
        model "gemini"
        model "claude"
        model "mock"
    
    'provider' is a string expression (the provider name).
    """
    provider: any
    line: int = 0

@dataclass
class ParallelStatement(Node):
    """
    Represents an autonomous parallel execution block.
    All statements in the body run simultaneously.

    Simple:
        autonomous parallel:
            think "Research market"
            think "Analyze competitors"

    Captured:
        results = autonomous parallel:
            think "Task one"
            think "Task two"

    'body' is a list of statements to run in parallel.
    'variable' is None for standalone usage.
    """
    body: list
    variable: str = None
    line: int = 0

@dataclass
class MemoryStatement(Node):
    """
    Represents a persistent memory block.
    Data is saved to disk and reloaded between runs.

    Usage:
        memory user_profile:
            name = "Emmanuel"
            language = "NEKOVA"
            run_count = 0

        show user_profile["name"]

    'name' is the memory block identifier.
    'body' is a list of AssignStatements defining the data.
    'persistent' means data survives between program runs.
    """
    name: str
    body: list
    line: int = 0

@dataclass
class SandboxStatement(Node):
    """
    Represents a sandboxed execution block.
    Code inside runs with restricted permissions.

    Strict mode — blocks everything dangerous:
        sandbox strict:
            use web
            think "Safe AI call"

    Relaxed mode — allows read-only operations:
        sandbox relaxed:
            use files
            data = read_file("input.txt")

    Phase 26c — capability-scoped agent tool access: an explicit
    allow-list of task names the block may call, enforced by the
    interpreter rather than by convention. This is the same idea
    as strict/relaxed mode taken further — instead of a fixed set
    of operation *categories* being blocked, a specific agent gets
    a specific, named set of tools and nothing else:
        sandbox strict allow: [search_web, send_email]:
            think "..."   # still blocked by strict mode itself
            search_web("query")   # allowed — it's on the list
            delete_database()     # blocked — not on the list

    'mode' is either "strict" or "relaxed".
    'body' is the list of statements to run sandboxed.
    'allow' is a list of allowed task-name strings, or None for no
    capability restriction beyond whatever the mode itself blocks.
    """
    mode: str
    body: list
    line: int = 0
    allow: list = None

@dataclass
class PipelineDefStatement(Node):
    """
    Represents a named neural pipeline definition.

    pipeline market_analysis:
        collect "Nigerian fintech trends"
        process with ai
        generate report
        save to database

    'name' is the pipeline identifier.
    'steps' is a list of step dicts describing each stage.
    """
    name: str
    steps: list
    line: int = 0


@dataclass
class RunPipelineStatement(Node):
    """
    Represents a pipeline execution statement.

    run pipeline market_analysis
    result = run pipeline market_analysis

    'name' is the pipeline to run.
    'variable' is None for standalone usage.
    """
    name: str
    variable: str = None
    line: int = 0

class IfStatement(Node):
    """
    A conditional block.
    Example:
        if age >= 18:
            show "Adult"
        else:
            show "Minor"
    """
    def __init__(self, condition: Node,
                 then_body: list,
                 else_body: list = None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body or []

    def __repr__(self):
        return f"If({self.condition})"


class RepeatStatement(Node):
    """
    Repeats a block a fixed number of times.
    Example:
        repeat 5:
            show "Hello"
    """
    def __init__(self, count: Node, body: list):
        self.count = count
        self.body  = body

    def __repr__(self):
        return f"Repeat({self.count})"


class TaskStatement(Node):
    """
    Defines a reusable task (function).
    params: list of (name, default_expr_or_None, is_vararg_bool)
    Example:
        task greet(name, greeting="Hello"):
            show greeting + " " + name
        task sum(*args):
            ...
    """
    def __init__(self, name: str, params: list, body: list, docstring: str = None):
        self.name      = name
        self.params    = params  # list of (name, default, is_vararg)
        self.body      = body
        self.docstring = docstring  # leading triple-quoted string, or None

    def __repr__(self):
        return f"Task({self.name}, params={self.params})"


class ReturnStatement(Node):
    """
    Returns a value from a task.
    Example:
        return result
    """
    def __init__(self, value: Node = None):
        self.value = value

    def __repr__(self):
        return f"Return({self.value})"


class BreakStatement(Node):
    """
    Exits the nearest enclosing loop immediately.
    Example:
        break
    """
    def __repr__(self):
        return "Break"


class ContinueStatement(Node):
    """
    Skips the rest of the current loop iteration
    and jumps to the next one.
    Example:
        continue
    """
    def __repr__(self):
        return "Continue"


class GlobalStatement(Node):
    """
    Declares that a variable name refers to the global scope,
    allowing a task to read AND write an outer variable.
    Example:
        count = 0
        task increment():
            global count
            count = count + 1
    """
    def __init__(self, names: list):
        self.names = names  # list of variable name strings

    def __repr__(self):
        return f"Global({self.names})"


class UnpackStatement(Node):
    """
    Unpacks an iterable into multiple variables.
    Example:
        a, b, c = [1, 2, 3]
        x, y = get_coords()
    """
    def __init__(self, names: list, value: "Node"):
        self.names = names   # list of variable name strings
        self.value = value   # the right-hand side expression

    def __repr__(self):
        return f"Unpack({self.names} = {self.value})"


class ListDestructureStatement(Node):
    """
    Destructures a list into named variables, with an optional rest
    capture for everything after the named targets.
    Example:
        let [first, second] = my_list
        let [first, ...rest] = my_list
    """
    def __init__(self, targets: list, rest, value: "Node"):
        self.targets = targets  # list of leading variable name strings
        self.rest    = rest     # variable name for the remainder, or None
        self.value   = value    # the right-hand side expression

    def __repr__(self):
        tail = f", ...{self.rest}" if self.rest else ""
        return f"ListDestructure([{', '.join(self.targets)}{tail}] = {self.value})"


class DictDestructureStatement(Node):
    """
    Destructures a dict into variables named after its keys.
    Example:
        let {name, age} = user
    """
    def __init__(self, keys: list, value: "Node"):
        self.keys  = keys   # list of key names — also used as variable names
        self.value = value  # the right-hand side expression

    def __repr__(self):
        return f"DictDestructure({{{', '.join(self.keys)}}} = {self.value})"


class UseStatement(Node):
    """
    Imports a standard library module.
    Example:
        use math
    """
    def __init__(self, module: str):
        self.module = module

    def __repr__(self):
        return f"Use({self.module})"

class ImportStatement(Node):
    """
    Imports another .nk file.
    Supports three forms:

        import "utils.nk"
            — executes the file, all names enter current scope

        import greet from "utils.nk"
            — imports only the 'greet' task

        import greet, add, PI from "utils.nk"
            — imports multiple named exports
    """
    def __init__(self, filepath: str, names: list = None):
        self.filepath = filepath
        # names = None means import everything (star import)
        # names = ['greet', 'add'] means named import
        self.names = names

    def __repr__(self):
        if self.names:
            return f"Import({self.names} from {repr(self.filepath)})"
        return f"Import({repr(self.filepath)})"

class WhileStatement(Node):
    """
    Loops while a condition is true.
    Example:
        while count < 5:
            show count
            count = count + 1
    """
    def __init__(self, condition: Node, body: list):
        self.condition = condition
        self.body      = body

    def __repr__(self):
        return f"While({self.condition})"

class TryStatement(Node):
    """
    Error handling block.
    Example:
        try:
            result = 10 / 0
        catch:
            show "Error caught!"

        try:
            result = 10 / 0
        catch error:
            show "Error: " + error
    """
    def __init__(self, try_body: list,
                 catch_body: list,
                 error_var: str = None,
                 finally_body: list = None):
        self.try_body     = try_body
        self.catch_body   = catch_body
        self.error_var    = error_var
        self.finally_body = finally_body or []

    def __repr__(self):
        return f"Try(catch_var={self.error_var})"

class ForStatement(Node):
    """
    Iterates over a list or range.
    Example:
        for item in items:
            show item

        for name in names:
            show "Hello " + name
    """
    def __init__(self, variable: str,
                 iterable: Node, body: list):
        self.variable = variable
        self.iterable = iterable
        self.body     = body

    def __repr__(self):
        return f"For({self.variable} in {self.iterable})"

class CallExpression(Node):
    """
    Calls a task with arguments.
    Example:
        greet("Emmanuel")
        greet(name="Sam", greeting="Hi")   -- keyword arguments
    kwargs: dict of {param_name: expr_node}, empty if none given.
    """
    def __init__(self, name: str, args: list, kwargs: dict = None):
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}

    def __repr__(self):
        return f"Call({self.name}, args={self.args}, kwargs={self.kwargs})"


# ── Classes / Objects (Phase 6) ──────────────────────────────────────

class MethodDefinition(Node):
    """
    A method defined inside a class/object.
    name: method name
    params: list of (name, hint)
    body: list of statements
    is_async: whether the method is async
    """
    def __init__(self, name: str, params: list, body: list, is_async: bool = False):
        self.name = name
        self.params = params
        self.body = body
        self.is_async = is_async

    def __repr__(self):
        return f"Method({self.name}, params={self.params})"


class ClassDefinition(Node):
    """
    Represents an object/class declaration.
    name: class name
    fields: list of (name, hint)
    init_params: list of (name, hint)
    init_body: list of statements
    methods: list of MethodDefinition
    parent: optional parent class name
    """
    def __init__(self, name: str, fields: list, init_params: list,
                 init_body: list, methods: list, parent: str = None):
        self.name = name
        self.fields = fields
        self.init_params = init_params
        self.init_body = init_body
        self.methods = methods
        self.parent = parent

    def __repr__(self):
        return f"Class({self.name}, fields={len(self.fields)}, methods={len(self.methods)})"


class NewInstance(Node):
    """new ClassName(arg1, arg2)"""
    def __init__(self, class_name: str, args: list):
        self.class_name = class_name
        self.args = args

    def __repr__(self):
        return f"NewInstance({self.class_name}, args={self.args})"


class SelfAccess(Node):
    """Represents `self.attribute` read inside methods/init."""
    def __init__(self, attribute: str):
        self.attribute = attribute

    def __repr__(self):
        return f"SelfAccess({self.attribute})"


class SelfAssign(Node):
    """Represents `self.attribute = value` inside methods/init."""
    def __init__(self, attribute: str, value: Node):
        self.attribute = attribute
        self.value = value

    def __repr__(self):
        return f"SelfAssign({self.attribute} = {self.value})"

# ── Pattern Matching (Phase 7) ────────────────────────────────

class MatchArm(Node):
    """
    A single arm inside a match block.
        when 200: show "OK"
        when 'a'..'z': show "lowercase"
    pattern: the value/type to match against (Node or str)
    is_type_check: True if matching a type name (e.g. when text:)
    is_else: True if this is the else arm
    is_range: True if matching a character/number range (e.g. 'a'..'z')
    range_end: the end of the range (Node), used when is_range=True
    body: list of statements
    """
    def __init__(self, pattern, body: list,
                 is_type_check: bool = False,
                 is_else: bool = False,
                 is_range: bool = False,
                 range_end=None):
        self.pattern       = pattern
        self.body          = body
        self.is_type_check = is_type_check
        self.is_else       = is_else
        self.is_range      = is_range
        self.range_end     = range_end

    def __repr__(self):
        if self.is_else:
            return "MatchArm(else)"
        return f"MatchArm({self.pattern})"


class MatchStatement(Node):
    """
    match <expr>:
        when <pattern>: <body>
        when <pattern>: <body>
        else: <body>
    """
    def __init__(self, subject: Node, arms: list):
        self.subject = subject
        self.arms    = arms

    def __repr__(self):
        return f"Match({self.subject}, {len(self.arms)} arms)"


# ── Web DSL (Phase 7) ─────────────────────────────────────────

class RouteStatement(Node):
    """
    route GET "/path":
        <body>
    method: HTTP method string
    path:   URL path string
    body:   list of statements (handler body)
    """
    def __init__(self, method: str, path: str, body: list):
        self.method = method
        self.path   = path
        self.body   = body

    def __repr__(self):
        return f"Route({self.method} {self.path})"


class ServeStatement(Node):
    """
    serve port: 8080
    serve              ← defaults to 8000
    """
    def __init__(self, port_expr=None):
        self.port_expr = port_expr   # None → default 8000

    def __repr__(self):
        return f"Serve(port={self.port_expr})"


# ── Database DSL (Phase 7) ────────────────────────────────────

class DBConnectStatement(Node):
    """db = connect("nekova.db")"""
    def __init__(self, var_name: str, filepath_expr):
        self.var_name     = var_name
        self.filepath_expr = filepath_expr

    def __repr__(self):
        return f"DBConnect({self.var_name})"

# ── Phase 9: AI-Native Extensions ────────────────────────────

class ThinkAsStatement(Node):
    """
    Extended think with output format:

        think "prompt" as json
        think "prompt" as list
        think "prompt" as bool
        think "prompt" as schema {"name": "text", "age": "number"}
        think "prompt" as json when error: {"status": "unavailable"}

    prompt:     expression (string/f-string/variable)
    as_format:  "json" | "list" | "bool" | "schema" | "text"
    schema:     dict expression (only when as_format == "schema")
    variable:   optional assignment target
    on_error:   optional expression evaluated instead of a
                "[think error: ...]" string if the AI call fails
    """
    def __init__(self, prompt, as_format: str,
                 schema=None, variable: str = None, line: int = 0,
                 on_error=None, budget=None, model=None):
        self.prompt     = prompt
        self.as_format  = as_format
        self.schema     = schema
        self.variable   = variable
        self.line       = line
        self.on_error   = on_error
        self.budget     = budget
        self.model      = model

    def __repr__(self):
        return f"ThinkAs({self.as_format})"


class RememberStatement(Node):
    """
    Store a value in AI memory (persists across think calls).

        remember "user_name" = "Emmanuel"
        remember "context"   = some_variable
        remember facts:
            name = "Emmanuel"
            role = "founder"

    key_expr:   expression evaluating to a string key
    value_expr: expression for the value
    """
    def __init__(self, key_expr, value_expr, line: int = 0):
        self.key_expr   = key_expr
        self.value_expr = value_expr
        self.line       = line

    def __repr__(self):
        return f"Remember({self.key_expr})"


class RecallStatement(Node):
    """
    Retrieve a value from AI memory.

        let name = recall "user_name"
        show recall "context"

    key_expr:  expression evaluating to a string key
    variable:  optional assignment target
    default:   optional default expression if key missing
    """
    def __init__(self, key_expr, variable: str = None,
                 default=None, line: int = 0):
        self.key_expr = key_expr
        self.variable = variable
        self.default  = default
        self.line     = line

    def __repr__(self):
        return f"Recall({self.key_expr})"


class ForgetStatement(Node):
    """
    Remove a key from AI memory, or clear all memory.

        forget "user_name"
        forget all

    key_expr:  expression for key, or None if forget_all
    forget_all: True if "forget all"
    """
    def __init__(self, key_expr=None, forget_all: bool = False,
                 line: int = 0):
        self.key_expr  = key_expr
        self.forget_all = forget_all
        self.line      = line

    def __repr__(self):
        return "ForgetAll()" if self.forget_all else f"Forget({self.key_expr})"

# ── Phase 15 Stability Nodes ──────────────────────────────────

class SliceExpression(Node):
    """
    List/string slicing: items[1:3], items[:2], items[1:]
    """
    def __init__(self, obj, start=None, stop=None, step=None, line: int = 0):
        self.obj   = obj
        self.start = start
        self.stop  = stop
        self.step  = step
        self.line  = line

    def __repr__(self):
        return f"Slice({self.obj}[{self.start}:{self.stop}])"


class RaiseStatement(Node):
    """
    Raise an exception: raise "message" or raise ErrorType("msg")
    """
    def __init__(self, expression, line: int = 0):
        self.expression = expression
        self.line       = line

    def __repr__(self):
        return f"Raise({self.expression})"


class PassStatement(Node):
    """
    No-op placeholder: pass
    """
    def __init__(self, line: int = 0):
        self.line = line

    def __repr__(self):
        return "Pass()"


class AssertStatement(Node):
    """
    Assertion: assert condition, "message"
    """
    def __init__(self, condition, message=None, line: int = 0):
        self.condition = condition
        self.message   = message
        self.line      = line

    def __repr__(self):
        return f"Assert({self.condition})"


class TernaryExpression(Node):
    """
    Ternary/conditional expression: value if condition else other
    """
    def __init__(self, condition, true_expr, false_expr, line: int = 0):
        self.condition  = condition
        self.true_expr  = true_expr
        self.false_expr = false_expr
        self.line       = line

    def __repr__(self):
        return f"Ternary({self.condition})"

# ── Phase 16: Standout Feature Nodes ─────────────────────────

class SpeakStatement(Node):
    """
    Text-to-speech output.
        speak "Hello, world!"
        speak greeting
    """
    def __init__(self, expression, line: int = 0):
        self.expression = expression
        self.line = line

    def __repr__(self):
        return f"Speak({self.expression})"


class ListenExpression(Node):
    """
    Speech-to-text input.
        let response = listen
        let cmd = listen "Say a command"
    """
    def __init__(self, prompt=None, line: int = 0):
        self.prompt = prompt
        self.line = line

    def __repr__(self):
        return "Listen()"


class EveryStatement(Node):
    """
    Scheduled/repeated execution.
        every 5s:
            show "tick"
        every 1m:
            check_email()
    interval_value: numeric expression
    interval_unit:  "s", "m", "h"
    body: list of statements
    max_runs: optional limit (None = forever)
    """
    def __init__(self, interval_value, interval_unit: str,
                 body: list, max_runs=None, line: int = 0):
        self.interval_value = interval_value
        self.interval_unit  = interval_unit
        self.body           = body
        self.max_runs       = max_runs
        self.line           = line

    def __repr__(self):
        return f"Every({self.interval_value}{self.interval_unit})"


class TestBlock(Node):
    """
    Built-in test block.
        test "adds numbers":
            expect add(1, 2) == 3
            expect add(0, 0) == 0

    Phase 26c — probabilistic form, for testing non-deterministic
    (AI-backed) behavior where a single pass/fail isn't meaningful:
        test "ai classifies sentiment" repeat 10 times, expect at least 8 passes:
            let result = think "Is this positive?" as bool
            expect result == true

    repeat_count / min_passes are Node expressions (or None for the
    plain, single-run form above). When repeat_count is set and
    min_passes isn't, min_passes defaults to repeat_count — i.e.
    "repeat 5 times" alone still means all 5 must pass, same as
    running the body 5 times with no tolerance for flakiness.
    """
    def __init__(self, label: str, body: list, line: int = 0,
                 repeat_count=None, min_passes=None):
        self.label = label
        self.body  = body
        self.line  = line
        self.repeat_count = repeat_count
        self.min_passes   = min_passes

    def __repr__(self):
        if self.repeat_count is not None:
            return f"Test({self.label!r}, repeat={self.repeat_count})"
        return f"Test({self.label!r})"


class ExpectStatement(Node):
    """
    Assertion inside a test block.
        expect result == 42
        expect name == "Emmanuel"
    """
    def __init__(self, expression, line: int = 0):
        self.expression = expression
        self.line       = line

    def __repr__(self):
        return f"Expect({self.expression})"


class ImagineStatement(Node):
    """
    AI image generation.
        imagine "a futuristic city at sunset"
        let img = imagine "red fox" as url
    """
    def __init__(self, prompt, result_var: str = None,
                 result_format: str = "url", line: int = 0):
        self.prompt        = prompt
        self.result_var    = result_var
        self.result_format = result_format   # "url" | "path" | "base64"
        self.line          = line

    def __repr__(self):
        return f"Imagine({self.prompt})"


class ShapeDefinition(Node):
    """
    Data schema / validated struct.
        shape User:
            name str
            age  int
            email str = "unknown"

    fields: list of (name, type_str, default_expr_or_None)
    """
    def __init__(self, name: str, fields: list, line: int = 0):
        self.name   = name
        self.fields = fields   # [(field_name, type_str, default)]
        self.line   = line

    def __repr__(self):
        return f"Shape({self.name})"


class SchemaDefinition(Node):
    """
    Phase 28: unified schema — same idea as ShapeDefinition (a named,
    reusable, validated struct) but a separate keyword and registry
    from `shape`, using the text/number/boolean/list/dict vocabulary
    that `think ... as schema {...}` (Phase 9) already validates
    against, rather than shape's str/int/float/bool names. Kept as its
    own node/keyword rather than folded into `shape` itself, so
    existing `shape` code and its "str"/"int" vocabulary are completely
    unaffected.

        schema Person:
            name: text
            age:  number
            note: text = "none"

    Three uses of the same declaration:
      1. Object type   — Person(name="Alice", age=30)
      2. AI parser     — think "..." as Person
      3. DB table      — db_create_from_schema(Person, "people")

    fields: list of (name, type_str, default_expr_or_None) — same
    shape as ShapeDefinition.fields, deliberately, so the AI-parser
    pillar can reuse _validate_shape_fields/_SHAPE_TYPE_CHECKERS as-is.
    """
    def __init__(self, name: str, fields: list, line: int = 0):
        self.name   = name
        self.fields = fields   # [(field_name, type_str, default)]
        self.line   = line

    def __repr__(self):
        return f"Schema({self.name})"


class WatchStatement(Node):
    """
    File or expression watcher — runs body when target changes.
        watch "config.toml":
            show "config reloaded"
        watch counter:
            show "counter changed to " + counter
    """
    def __init__(self, target, body: list,
                 is_file: bool = True, line: int = 0):
        self.target  = target
        self.body    = body
        self.is_file = is_file
        self.line    = line

    def __repr__(self):
        return f"Watch({self.target})"

# ── Phase 17: Power User Layer Nodes ─────────────────────────

class YieldStatement(Node):
    """
    Yield a value from a generator task.
        yield value
        yield          (yield None)
    """
    def __init__(self, expression=None, line: int = 0):
        self.expression = expression
        self.line = line
    def __repr__(self): return f"Yield({self.expression})"


class DecoratorStatement(Node):
    """
    Decorator applied to the next task definition.
        @memoize
        task fib(n):
            ...
        @retry(3)
        task fetch_data():
            ...
    decorator_expr: the expression after @
    target: the TaskStatement being decorated
    """
    def __init__(self, decorator_expr, target, line: int = 0):
        self.decorator_expr = decorator_expr
        self.target = target
        self.line = line
    def __repr__(self): return f"Decorator({self.decorator_expr})"


class ErrorDefinition(Node):
    """
    Define a custom error type.
        error NetworkError:
            message str
            code    int = 0
    fields: list of (name, type_str, default_or_None)
    """
    def __init__(self, name: str, fields: list, line: int = 0):
        self.name   = name
        self.fields = fields
        self.line   = line
    def __repr__(self): return f"ErrorDef({self.name})"


class TypedTaskStatement(Node):
    """
    Task with typed parameters and optional return type.
        task add(a: int, b: int) -> int:
            return a + b
    Extends TaskStatement with type annotations.
    params: list of (name, type_str_or_None, default_or_None, is_vararg)
    return_type: str or None
    """
    def __init__(self, name: str, params: list, body: list,
                 return_type: str = None, line: int = 0, docstring: str = None):
        self.name        = name
        self.params      = params
        self.body         = body
        self.return_type = return_type
        self.line        = line
        self.docstring   = docstring  # leading triple-quoted string, or None
    def __repr__(self): return f"TypedTask({self.name})"


# ── Phase 21: Prompt Blocks + Retry/Fallback ───────────────────

class PromptStatement(Node):
    """
    Defines a reusable, interpolated prompt template — a task whose
    body is (typically) a single triple-quoted string with {var}
    placeholders, filled in from the task's own parameters. Calling
    a prompt like a task returns the interpolated string; the
    result is usually fed straight into `think`:

        prompt summarize(text, style="professional"):
            \"\"\"Summarize the following in a {style} tone: {text}\"\"\"

        let result = think summarize(document) as json

    params: list of (name, type_hint_or_None, default_or_None, is_vararg)
      — same shape as TypedTaskStatement.params, so prompts can be
      typed exactly like tasks.
    body: list of statements. Any bare StringLiteral statement in
      the body is parsed as if it were an f-string (interpolated
      against the prompt's own parameter scope) even without an
      `f` prefix — that's what makes a prompt block a *template*
      rather than an ordinary task. The value of the last statement
      in the body is the prompt's implicit return value; an
      explicit `return` also works if present.
    """
    def __init__(self, name: str, params: list, body: list, line: int = 0):
        self.name   = name
        self.params = params
        self.body   = body
        self.line   = line

    def __repr__(self):
        return f"Prompt({self.name}, params={self.params})"


class RetryStatement(Node):
    """
    Retries a block up to `times` times on error, with an optional
    backoff delay between attempts, falling back to `fallback_body`
    (if given) once attempts are exhausted — otherwise the last
    error is re-raised.

        retry 3 times with exponential backoff:
            let result = think "analyse this" as json
        fallback:
            let result = {error: "unavailable"}

        retry 5 times:               # no backoff clause -> immediate retry
            connect_to_service()

    times: expression evaluating to a positive integer
    backoff: None | "exponential" | "linear" — delay strategy
      between attempts (no delay when None)
    body: the block to retry
    fallback_body: list of statements to run if every attempt
      fails, or None to re-raise the final error instead
    """
    def __init__(self, times, backoff, body: list,
                 fallback_body: list = None, line: int = 0):
        self.times         = times
        self.backoff       = backoff
        self.body           = body
        self.fallback_body = fallback_body
        self.line          = line

    def __repr__(self):
        return f"Retry({self.times}, backoff={self.backoff})"


# ── Phase 22: Observability + Testing + Pipe Operator ──────────

class ObserveStatement(Node):
    """
    Traces a block's execution — prints a structured start/end log
    with an optional tag dict and a measured duration:

        observe "pipeline run" with tags {user: user_id}:
            let summary = think summarize(document)

        observe "quick check":
            validate(input)

    label: expression evaluating to the trace label (usually a string)
    tags: expression evaluating to a dict, or None if no `with tags` clause
    body: the traced block
    """
    def __init__(self, label, tags, body: list, line: int = 0):
        self.label = label
        self.tags  = tags
        self.body  = body
        self.line  = line

    def __repr__(self):
        return f"Observe({self.label!r})"


class MockStatement(Node):
    """
    Stubs out `think`/`think ... as ...` for the rest of the
    enclosing test block, so tests don't make real AI calls:

        test "classifier":
            mock think as "sports"
            expect classify(text) == "sports"

    target: the thing being mocked (currently only "think" is
      supported, but the grammar is generic for future targets)
    value: expression evaluating to the value `think` should
      return while the mock is active
    """
    def __init__(self, target: str, value, line: int = 0):
        self.target = target
        self.value  = value
        self.line   = line

    def __repr__(self):
        return f"Mock({self.target} as {self.value})"