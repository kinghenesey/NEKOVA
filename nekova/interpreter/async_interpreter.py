import asyncio
import aiohttp
import sys

from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.parser.async_nodes import (
    AsyncFunctionNode,
    AwaitNode,
    StreamThinkNode,
    FetchNode,
)


# ── Tiny response wrapper returned by fetch ───────────────────────────────────
class FetchResponse:
    def __init__(self, status: int, text: str, json_data=None, headers=None):
        self.status = status
        self.text = text
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        if self._json is not None:
            return self._json
        import json as _json
        return _json.loads(self.text)

    def __repr__(self):
        return f"<FetchResponse status={self.status} len={len(self.text)}>"


# ── Async function value stored in the environment ─────────────────────────────
class AsyncFunction:
    """
    A defined 'async task'. Calling it is synchronous under the hood —
    NEKOVA's interpreter is single-threaded, so there's no actual
    concurrency to schedule. This is the core of the Phase 23 async
    rewrite: execution is delegated to Interpreter._call_typed_task,
    the same proven code path regular typed tasks use, rather than a
    hand-rolled coroutine walker that manipulated raw Python dicts
    instead of real Environment objects and only knew how to handle
    three narrow statement shapes (bare await / assign-await /
    return-await) — breaking on anything else, including a plain
    `for` loop inside an async task body.

    Reusing _call_typed_task also means async tasks get full parity
    with regular tasks for free: default parameter values, *varargs,
    type-hint enforcement, and arbitrary control flow (if/for/while/
    try/match/etc.) all just work.
    """
    def __init__(self, name: str, params: list, body: list,
                 closure_env, interpreter,
                 return_type=None, docstring=None):
        self.name        = name
        self.params      = params        # (name, type_hint, default, is_vararg)
        self.body         = body
        self.closure_env = closure_env   # real Environment, not a dict
        self.interpreter = interpreter
        self.return_type = return_type
        self.docstring   = docstring

    def call(self, args: list):
        """Run the task body synchronously and return its result."""
        return self.interpreter._call_typed_task(self, args)

    def __repr__(self):
        return f"<async task {self.name}>"


# ── Mixin ─────────────────────────────────────────────────────────────────────
class AsyncInterpreterMixin:
    """
    Mixin for the main Interpreter class.
    Assumes self has:
      - self.env               : current variable environment (dict-like)
      - self.visit(node)       : synchronous node visitor
      - self.execute_block(body, env=None) : run a list of nodes
    """

    # ── Helper: run a coroutine from a synchronous context ───────────────────
    @staticmethod
    def _run_sync(coro):
        """
        Run *coro* to completion whether or not there is already a running loop.
        Works inside pytest-asyncio, Jupyter, and plain scripts.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # asyncio raises built-in RuntimeError when there is no running loop
            loop = None

        if loop and loop.is_running():
            # We're inside an already-running event loop (e.g. REPL or Jupyter).
            # Schedule as a task and block via a threading trick.
            import concurrent.futures
            future = concurrent.futures.Future()

            async def _wrapper():
                try:
                    future.set_result(await coro)
                except Exception as exc:
                    future.set_exception(exc)

            loop.create_task(_wrapper())
            return future.result(timeout=60)
        else:
            return asyncio.run(coro)

    # ── async func definition ─────────────────────────────────────────────────
    def visit_async_function(self, node: AsyncFunctionNode):
        """Define an async task and store it in env — mirrors how a
        plain TaskStatement or TypedTaskStatement is registered."""
        fn = AsyncFunction(
            name=node.name,
            params=node.params,
            body=node.body,
            closure_env=self.env,
            interpreter=self,
            return_type=getattr(node, "return_type", None),
            docstring=getattr(node, "docstring", None),
        )
        self.env.set(node.name, fn)
        return fn

    # ── await ─────────────────────────────────────────────────────────────────
    def visit_await(self, node: AwaitNode):
        """
        Evaluate the awaited expression. AsyncFunction.call() and
        fetch() (visit_fetch) already run synchronously under the
        hood, so this is almost always just evaluating a plain
        expression — 'await' exists mainly for readability, matching
        the async/await syntax people already know. If a genuine
        Python coroutine somehow reaches here, it's driven to
        completion as a defensive fallback.
        """
        value = self._execute_node(node.expr)
        if asyncio.iscoroutine(value):
            return self._run_sync(value)
        return value

    # ── stream think ──────────────────────────────────────────────────────────
    async def _stream_think_async(self, node: StreamThinkNode):
        """
        Core coroutine for streaming AI think.
        Requires the anthropic Python SDK with streaming support.
        Falls back to a single-shot call if streaming is unavailable.
        """
        prompt_value = self.visit(node.prompt)

        try:
            import anthropic  # type: ignore
        except ImportError:
            raise NEKOVARuntimeError(
                "The 'anthropic' package is required for `stream think`. "
                "Install it: pip install anthropic"
            )

        client = anthropic.AsyncAnthropic()

        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": str(prompt_value)}],
        ) as stream:
            async for chunk_text in stream.text_stream:
                # Bind the chunk variable and run the body
                self.env[node.chunk_var] = chunk_text
                await self.execute_block_async(node.body, dict(self.env))

    def visit_stream_think(self, node: StreamThinkNode):
        return self._run_sync(self._stream_think_async(node))

    # ── fetch ─────────────────────────────────────────────────────────────────
    async def _fetch_async(self, node: FetchNode) -> FetchResponse:
        url = str(self.visit(node.url))
        method = node.method

        # Resolve headers / body if they are AST nodes
        headers = node.headers
        if hasattr(headers, "__class__") and hasattr(headers, "visit"):
            headers = self.visit(headers)
        if not isinstance(headers, dict):
            headers = {}

        body_data = None
        if node.body_expr is not None:
            body_data = self.visit(node.body_expr)

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            req_kwargs = {"headers": headers}
            if body_data is not None:
                if isinstance(body_data, dict):
                    req_kwargs["json"] = body_data
                else:
                    req_kwargs["data"] = str(body_data)

            async with session.request(method, url, **req_kwargs) as resp:
                text = await resp.text()
                json_data = None
                ct = resp.headers.get("Content-Type", "")
                if "application/json" in ct:
                    try:
                        json_data = await resp.json(content_type=None)
                    except Exception:
                        pass

                return FetchResponse(
                    status=resp.status,
                    text=text,
                    json_data=json_data,
                    headers=dict(resp.headers),
                )

    def visit_fetch(self, node: FetchNode) -> FetchResponse:
        return self._run_sync(self._fetch_async(node))