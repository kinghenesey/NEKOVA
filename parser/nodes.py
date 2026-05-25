# =============================================================
# AION Parser — AST Nodes
# =============================================================
# Every possible structure in AION code is represented as a
# Node. The Parser builds a tree of these nodes. The
# Interpreter then walks the tree and executes each node.
#
# Think of nodes like LEGO pieces — each one represents one
# concept in your program.

from dataclasses import dataclass


class Node:
    """Base class for all AST nodes."""
    pass


# ── Program ───────────────────────────────────────────────────

class Program(Node):
    """
    The root node — represents the entire AION program.
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
        name == "AION"
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
    Example:
        name = "Emmanuel"
    """
    def __init__(self, name: str, value: Node):
        self.name  = name
        self.value = value

    def __repr__(self):
        return f"Assign({self.name} = {self.value})"


class ShowStatement(Node):
    """
    Prints a value to the terminal.
    Example:
        show "Hello"
    """
    def __init__(self, expression: Node):
        self.expression = expression

    def __repr__(self):
        return f"Show({self.expression})"
    
@dataclass
class ThinkStatement:
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
class PipelineStatement:
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
class ModelStatement:
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
class ParallelStatement:
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
    Example:
        task greet(name):
            show "Hello " + name
    """
    def __init__(self, name: str, params: list, body: list):
        self.name   = name
        self.params = params
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
    Imports another .aion file.
    Example:
        import "utils.aion"
        import "greetings.aion"
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def __repr__(self):
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
                 error_var: str = None):
        self.try_body  = try_body
        self.catch_body = catch_body
        self.error_var  = error_var

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