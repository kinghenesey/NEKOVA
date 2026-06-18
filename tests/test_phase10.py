# tests/test_phase10.py
# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 tests: async/await · stream think · HTTP fetch
# Run with:  pytest tests/test_phase10.py -v
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── helpers ──────────────────────────────────────────────────────────────────
from nekova.parser.async_nodes import (
    AsyncFunctionNode,
    AwaitNode,
    FetchNode,
    StreamThinkNode,
)
from nekova.interpreter.async_interpreter import AsyncFunction, FetchResponse


# ─────────────────────────────────────────────────────────────────────────────
# 1. AST NODE CONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncNodes:
    def test_async_function_node_repr(self):
        node = AsyncFunctionNode("greet", [("name", "text")], [], None)
        assert "greet" in repr(node)

    def test_await_node_repr(self):
        inner = MagicMock()
        node = AwaitNode(inner)
        assert "AwaitNode" in repr(node)

    def test_stream_think_node_repr(self):
        node = StreamThinkNode("prompt_expr", "chunk", [])
        assert "StreamThinkNode" in repr(node)
        assert "chunk" in repr(node)

    def test_fetch_node_defaults(self):
        node = FetchNode("url_expr")
        assert node.method == "GET"
        assert node.headers == {}
        assert node.body_expr is None

    def test_fetch_node_custom_method(self):
        node = FetchNode("url_expr", method="POST")
        assert node.method == "POST"

    def test_fetch_node_repr(self):
        node = FetchNode("url_expr", method="DELETE")
        assert "DELETE" in repr(node)


# ─────────────────────────────────────────────────────────────────────────────
# 2. FetchResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchResponse:
    def test_status(self):
        r = FetchResponse(200, '{"ok": true}', {"ok": True})
        assert r.status == 200

    def test_json_preloaded(self):
        r = FetchResponse(200, '{"ok": true}', {"ok": True})
        assert r.json() == {"ok": True}

    def test_json_parsed_from_text(self):
        r = FetchResponse(200, '{"x": 42}')
        assert r.json()["x"] == 42

    def test_text(self):
        r = FetchResponse(200, "hello world")
        assert r.text == "hello world"

    def test_repr(self):
        r = FetchResponse(404, "not found")
        assert "404" in repr(r)


# ─────────────────────────────────────────────────────────────────────────────
# 3. AsyncFunction wrapper
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncFunction:
    def _make_interp(self):
        interp = MagicMock()
        interp.env = {}

        async def mock_block(body, env):
            return "block_result"

        interp.execute_block_async = mock_block
        return interp

    def test_repr(self):
        interp = self._make_interp()
        fn = AsyncFunction("hello", [], [], {}, interp)
        assert "hello" in repr(fn)

    def test_call_async_no_params(self):
        interp = self._make_interp()
        fn = AsyncFunction("hello", [], ["stmt"], {}, interp)
        result = asyncio.run(fn.call_async([]))
        assert result == "block_result"

    def test_call_async_with_params(self):
        interp = self._make_interp()
        fn = AsyncFunction("add", [("x", "number"), ("y", "number")], [], {}, interp)
        asyncio.run(fn.call_async([1, 2]))
        # env should have been set before block was called
        # (checked indirectly — no exception = pass)

    def test_call_async_closure_isolation(self):
        """Calling fn should not pollute outer env."""
        interp = self._make_interp()
        outer_env = {"z": 99}
        interp.env = outer_env
        fn = AsyncFunction("f", [("a", None)], [], dict(outer_env), interp)
        asyncio.run(fn.call_async([42]))
        assert "a" not in outer_env  # outer env unchanged


# ─────────────────────────────────────────────────────────────────────────────
# 4. AsyncInterpreterMixin  –  visit_async_function
# ─────────────────────────────────────────────────────────────────────────────

class FakeInterpreter:
    """Minimal stub that satisfies AsyncInterpreterMixin."""
    from nekova.interpreter.async_interpreter import AsyncInterpreterMixin as _M

    def __init__(self):
        from nekova.interpreter.environment import Environment
        self.env = Environment()

    def visit(self, node):
        if callable(node):
            return node()
        return node

    def execute_block(self, body, env=None):
        return None

    async def execute_block_async(self, body, env):
        return None


# Compose the real mixin in
from nekova.interpreter.async_interpreter import AsyncInterpreterMixin

class ConcreteInterp(AsyncInterpreterMixin, FakeInterpreter):
    pass


class TestVisitAsyncFunction:
    def test_stores_async_function_in_env(self):
        interp = ConcreteInterp()
        node = AsyncFunctionNode("greet", [("name", "text")], [], None)
        result = interp.visit_async_function(node)
        assert isinstance(result, AsyncFunction)
        assert interp.env["greet"] is result

    def test_closure_is_snapshot(self):
        interp = ConcreteInterp()
        interp.env["x"] = 10
        node = AsyncFunctionNode("f", [], [], None)
        fn = interp.visit_async_function(node)
        interp.env["x"] = 999   # mutate after definition
        assert fn.closure["x"] == 10  # closure is unchanged


# ─────────────────────────────────────────────────────────────────────────────
# 5. visit_await
# ─────────────────────────────────────────────────────────────────────────────

class TestVisitAwait:
    def test_await_plain_value(self):
        interp = ConcreteInterp()
        # visit returns the node itself (our stub just returns the value)
        node = AwaitNode(42)
        interp.visit = lambda n: n   # identity
        result = asyncio.run(interp.visit_await(node))
        assert result == 42

    def test_await_coroutine(self):
        interp = ConcreteInterp()

        async def coro():
            return "coro_result"

        interp.visit = lambda n: coro()
        node = AwaitNode("ignored")
        result = asyncio.run(interp.visit_await(node))
        assert result == "coro_result"

    def test_await_async_function(self):
        interp = ConcreteInterp()

        async def mock_block(body, env):
            return "from_block"

        interp.execute_block_async = mock_block
        fn = AsyncFunction("f", [], ["stmt"], {}, interp)
        interp.visit = lambda n: fn
        node = AwaitNode("ignored")
        result = asyncio.run(interp.visit_await(node))
        assert result == "from_block"


# ─────────────────────────────────────────────────────────────────────────────
# 6. visit_fetch  (mocked aiohttp)
# ─────────────────────────────────────────────────────────────────────────────

class TestVisitFetch:
    def _make_mock_response(self, status=200, text="ok", json_data=None, ct="text/plain"):
        resp = AsyncMock()
        resp.status = status
        resp.text = AsyncMock(return_value=text)
        resp.headers = {"Content-Type": ct}
        if json_data is not None:
            resp.json = AsyncMock(return_value=json_data)
            resp.headers = {"Content-Type": "application/json"}
        return resp

    def test_fetch_get_plain(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: n  # URL node returns itself as string

        mock_resp = self._make_mock_response(200, "hello")

        cm_session = MagicMock()
        cm_request = MagicMock()
        cm_request.__aenter__ = AsyncMock(return_value=mock_resp)
        cm_request.__aexit__ = AsyncMock(return_value=False)
        cm_session.__aenter__ = AsyncMock(return_value=cm_session)
        cm_session.__aexit__ = AsyncMock(return_value=False)
        cm_session.request = MagicMock(return_value=cm_request)

        node = FetchNode("https://example.com")

        with patch("aiohttp.ClientSession", return_value=cm_session):
            result = interp.visit_fetch(node)

        assert isinstance(result, FetchResponse)
        assert result.status == 200
        assert result.text == "hello"

    def test_fetch_returns_json(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: n

        mock_resp = self._make_mock_response(
            200, '{"name": "nekova"}', {"name": "nekova"}, "application/json"
        )

        cm_session = MagicMock()
        cm_request = MagicMock()
        cm_request.__aenter__ = AsyncMock(return_value=mock_resp)
        cm_request.__aexit__ = AsyncMock(return_value=False)
        cm_session.__aenter__ = AsyncMock(return_value=cm_session)
        cm_session.__aexit__ = AsyncMock(return_value=False)
        cm_session.request = MagicMock(return_value=cm_request)

        node = FetchNode("https://api.example.com/data")

        with patch("aiohttp.ClientSession", return_value=cm_session):
            result = interp.visit_fetch(node)

        assert result.json() == {"name": "nekova"}

    def test_fetch_post_with_body(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: n if not isinstance(n, dict) else n

        mock_resp = self._make_mock_response(201, "created")

        cm_session = MagicMock()
        cm_request = MagicMock()
        cm_request.__aenter__ = AsyncMock(return_value=mock_resp)
        cm_request.__aexit__ = AsyncMock(return_value=False)
        cm_session.__aenter__ = AsyncMock(return_value=cm_session)
        cm_session.__aexit__ = AsyncMock(return_value=False)
        cm_session.request = MagicMock(return_value=cm_request)

        node = FetchNode(
            url="https://api.example.com/users",
            method="POST",
            body_expr={"name": "Emmanuel"},
        )

        with patch("aiohttp.ClientSession", return_value=cm_session):
            result = interp.visit_fetch(node)

        assert result.status == 201

    def test_fetch_404(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: n

        mock_resp = self._make_mock_response(404, "not found")

        cm_session = MagicMock()
        cm_request = MagicMock()
        cm_request.__aenter__ = AsyncMock(return_value=mock_resp)
        cm_request.__aexit__ = AsyncMock(return_value=False)
        cm_session.__aenter__ = AsyncMock(return_value=cm_session)
        cm_session.__aexit__ = AsyncMock(return_value=False)
        cm_session.request = MagicMock(return_value=cm_request)

        node = FetchNode("https://example.com/missing")

        with patch("aiohttp.ClientSession", return_value=cm_session):
            result = interp.visit_fetch(node)

        assert result.status == 404


# ─────────────────────────────────────────────────────────────────────────────
# 7. stream think  (mocked anthropic)
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamThink:
    def test_stream_think_calls_body_per_chunk(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: "Tell me about NEKOVA"

        chunks_received = []

        async def mock_block(body, env):
            chunks_received.append(env.get("chunk"))

        interp.execute_block_async = mock_block

        # Build a fake async context manager for the stream
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        async def fake_text_stream():
            for c in ["Hello", " World", "!"]:
                yield c

        mock_stream.text_stream = fake_text_stream()

        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=mock_stream)

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.AsyncAnthropic = MagicMock(return_value=mock_client)

        node = StreamThinkNode("prompt_node", "chunk", ["show_stmt"])

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            interp.visit_stream_think(node)

        assert chunks_received == ["Hello", " World", "!"]

    def test_stream_think_missing_anthropic_raises(self):
        interp = ConcreteInterp()
        interp.visit = lambda n: "prompt"
        interp.execute_block_async = AsyncMock()

        node = StreamThinkNode("prompt_node", "chunk", [])

        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises((RuntimeError, ImportError, Exception)):
                interp.visit_stream_think(node)


# ─────────────────────────────────────────────────────────────────────────────
# 8. _run_sync utility
# ─────────────────────────────────────────────────────────────────────────────

class TestRunSync:
    def test_run_sync_returns_value(self):
        async def coro():
            return 42

        result = AsyncInterpreterMixin._run_sync(coro())
        assert result == 42

    def test_run_sync_propagates_exception(self):
        async def bad():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            AsyncInterpreterMixin._run_sync(bad())


# ─────────────────────────────────────────────────────────────────────────────
# 9. execute_block_async
# ─────────────────────────────────────────────────────────────────────────────

class TestExecuteBlockAsync:
    def test_executes_each_node(self):
        interp = ConcreteInterp()
        visited = []
        interp.visit = lambda n: visited.append(n) or n

        asyncio.run(interp.execute_block_async(["a", "b", "c"], {}))
        assert visited == ["a", "b", "c"]

    def test_restores_env_after_block(self):
        interp = ConcreteInterp()
        interp.env = {"outer": True}
        interp.visit = lambda n: n

        asyncio.run(interp.execute_block_async([], {"inner": True}))
        assert "outer" in interp.env
        assert "inner" not in interp.env

    def test_awaits_coroutine_nodes(self):
        interp = ConcreteInterp()
        results = []

        async def coro_node():
            results.append("awaited")
            return "done"

        interp.visit = lambda n: coro_node() if callable(n) else n

        asyncio.run(interp.execute_block_async([coro_node], {}))
        assert "awaited" in results