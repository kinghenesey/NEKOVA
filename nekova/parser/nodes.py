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

class MethodCall(Node):
    """
    A method call on a value.
    Example:
        name.upper()
        items.length()
        text.replace("a", "b")
    """
    def __init__(self, object: Node,
                 method: str, args: list):
        self.object = object
        self.method = method
        self.args   = args

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
    def __init__(self, object: Node, property: str):
        self.object   = object
        self.property = property

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
    def __init__(self, name: str, value: Node, type_hint: str = None):
        self.name      = name
        self.value     = value
        self.type_hint = type_hint  # e.g. "text", "number", "boolean", "list", "dict"

    def __repr__(self):
        if self.type_hint:
            return f"Assign({self.name}: {self.type_hint} = {self.value})"
        return f"Assign({self.name} = {self.value})"


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
    
    'variable' is None for standalone usage.
    'prompt' is any expression (string literal, variable, f-string, etc.)
    """
    prompt: any
    variable: str = None
    line: int = 0

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

    'mode' is either "strict" or "relaxed".
    'body' is the list of statements to run sandboxed.
    """
    mode: str
    body: list
    line: int = 0

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
    def __init__(self, name: str, params: list, body: list):
        self.name   = name
        self.params = params  # list of (name, default, is_vararg)
        self.body   = body

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
    """
    def __init__(self, name: str, args: list):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Call({self.name}, args={self.args})"


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
    pattern: the value/type to match against (Node or str)
    is_type_check: True if matching a type name (e.g. when text:)
    is_else: True if this is the else arm
    body: list of statements
    """
    def __init__(self, pattern, body: list,
                 is_type_check: bool = False,
                 is_else: bool = False):
        self.pattern       = pattern
        self.body          = body
        self.is_type_check = is_type_check
        self.is_else       = is_else

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

    prompt:     expression (string/f-string/variable)
    as_format:  "json" | "list" | "bool" | "schema" | "text"
    schema:     dict expression (only when as_format == "schema")
    variable:   optional assignment target
    """
    def __init__(self, prompt, as_format: str,
                 schema=None, variable: str = None, line: int = 0):
        self.prompt     = prompt
        self.as_format  = as_format
        self.schema     = schema
        self.variable   = variable
        self.line       = line

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