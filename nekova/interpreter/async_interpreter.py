import asyncio
import aiohttp
import sys

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


# ── Coroutine wrapper stored in the environment for async functions ───────────
class AsyncFunction:
    def __init__(self, name: str, params: list, body: list, closure, interpreter):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure          # environment snapshot at definition time
        self.interpreter = interpreter

    async def call_async(self, args: list):
        env = self.closure.copy() if hasattr(self.closure, "copy") else dict(self.closure)
        for (param_name, _type_hint), value in zip(self.params, args):
            env[param_name] = value
        return await self.interpreter.execute_block_async(self.body, env)

    def __repr__(self):
        return f"<async func {self.name}>"


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
        """Define an async function and store it in env."""
        fn = AsyncFunction(
            name=node.name,
            params=node.params,
            body=node.body,
            closure=self.env.snapshot(),
            interpreter=self,
        )
        self.env[node.name] = fn
        return fn

    # ── await ─────────────────────────────────────────────────────────────────
    async def visit_await(self, node: AwaitNode):
        """Evaluate the inner expression; if it's a coroutine, await it."""
        value = self.visit(node.expr)
        if asyncio.iscoroutine(value):
            return await value
        if isinstance(value, AsyncFunction):
            # bare  await greet()  — call with no args (shouldn't normally happen)
            return await value.call_async([])
        # Already a plain value (e.g. await "hello") — just return it
        return value

    # ── execute_block_async ───────────────────────────────────────────────────
    async def execute_block_async(self, body: list, env: dict):
        """
        Async version of execute_block.  Needed so that await inside an async
        function body propagates the coroutine chain properly.
        """
        from nekova.runtime import ReturnSignal
        from nekova.parser.async_nodes import AwaitNode as _AW
        from nekova.parser.nodes import AssignStatement as _AS
        from nekova.parser.nodes import ReturnStatement as _RS
        old_env = self.env
        self.env = env
        result = None
        try:
            for stmt in body:
                # top-level:  await task()
                if isinstance(stmt, _AW):
                    result = await self.visit_await(stmt)
                # assignment:  x = await task()
                elif isinstance(stmt, _AS) and isinstance(stmt.value, _AW):
                    value = await self.visit_await(stmt.value)
                    self.env[stmt.name] = value
                    result = value
                # return:  return await task()
                elif isinstance(stmt, _RS) and isinstance(stmt.value, _AW):
                    value = await self.visit_await(stmt.value)
                    raise ReturnSignal(value)
                else:
                    result = self.visit(stmt)
                    if asyncio.iscoroutine(result):
                        result = await result
        except ReturnSignal as ret:
            result = ret.value
        finally:
            self.env = old_env
        return result

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
            raise RuntimeError(
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