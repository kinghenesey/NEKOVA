from nekova.parser.nodes import Node  # adjust import if your base is elsewhere


# ── Async function definition ─────────────────────────────────────────────────
class AsyncFunctionNode(Node):
    """async func greet(name): ..."""
    def __init__(self, name: str, params: list, body: list, return_type=None):
        self.name = name
        self.params = params          # list of (param_name, type_hint|None)
        self.body = body
        self.return_type = return_type

    def __repr__(self):
        return f"AsyncFunctionNode({self.name}, params={self.params})"


# ── Await expression ──────────────────────────────────────────────────────────
class AwaitNode(Node):
    """result = await some_async_func()"""
    def __init__(self, expr):
        self.expr = expr              # the coroutine expression to await

    def __repr__(self):
        return f"AwaitNode({self.expr})"


# ── Streaming think statement ─────────────────────────────────────────────────
class StreamThinkNode(Node):
    """stream think "prompt": each chunk: show chunk"""
    def __init__(self, prompt, chunk_var: str, body: list):
        self.prompt = prompt          # any expression (string or variable)
        self.chunk_var = chunk_var    # loop variable name  e.g. "chunk"
        self.body = body              # statements inside the each-block

    def __repr__(self):
        return f"StreamThinkNode(prompt={self.prompt}, var={self.chunk_var})"


# ── HTTP fetch expression ─────────────────────────────────────────────────────
class FetchNode(Node):
    """response = fetch "https://api.example.com" """
    def __init__(self, url, method: str = "GET", headers=None, body_expr=None):
        self.url = url                # expression that yields the URL string
        self.method = method          # "GET" | "POST" | "PUT" | "DELETE"
        self.headers = headers or {}  # dict expression or literal {}
        self.body_expr = body_expr    # optional request body expression

    def __repr__(self):
        return f"FetchNode({self.method} {self.url})"