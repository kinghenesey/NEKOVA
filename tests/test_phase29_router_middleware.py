"""
Phase 29 (step 2) - Router middleware

    route GET "/admin" with logging, auth, rate_limit(10, 60):
        return text("secret")

Covers:
  - grammar: the `with` clause in parser.py AND parser.nk  (TestRouteWithParsing,
                                                            TestSelfHostedParity)
  - status-aware responses: json(d, 201), respond(401, ...) (TestResponseHelpers)
  - request.remote_addr / request.context                  (TestRequestFields)
  - user-defined task middleware                           (TestUserMiddleware)
  - the chain runner                                       (TestRunChain)
  - built-ins: logging / rate_limit / auth                 (TestLogging, TestRateLimit,
                                                            TestAuth)
  - how names resolve                                      (TestResolution)

Everything that talks HTTP goes through the real Flask app via its test
client, so the full request path (Flask -> NEKOVARequest -> Router ->
middleware -> handler -> Flask response) is exercised.
"""
import contextlib
import io
import os
import re
import subprocess
import sys
import textwrap
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.parser.nodes import RouteStatement, Identifier, CallExpression
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.web import web_module as wm


def _parse(src):
    return Parser(Lexer(textwrap.dedent(src)).tokenize()).parse()


def _first_route(src):
    return [s for s in _parse(src).statements
            if isinstance(s, RouteStatement)][0]


class _App:
    """A NEKOVA program, served by the real Flask app's test client."""

    def __init__(self, source):
        wm._server = None
        self.interp = Interpreter()
        self.interp.run(_parse(source))
        self.server = wm._server
        self.server._setup_flask()
        self.client = self.server._app.test_client()

    def get(self, path="/x", **kw):
        return self.client.get(path, **kw)


class _WebCase(unittest.TestCase):
    def tearDown(self):
        wm._server = None

    def app(self, source):
        return _App(source)


# ── grammar ──────────────────────────────────────────────────

class TestRouteWithParsing(unittest.TestCase):

    def test_no_with_clause_gives_an_empty_list(self):
        r = _first_route('route GET "/x":\n    return text("hi")\n')
        self.assertEqual(r.middleware, [])

    def test_single_identifier(self):
        r = _first_route('route GET "/x" with auth:\n    return text("hi")\n')
        self.assertEqual([type(m) for m in r.middleware], [Identifier])
        self.assertEqual(r.middleware[0].name, "auth")

    def test_several_entries_keep_their_order(self):
        r = _first_route(
            'route GET "/x" with auth, logging:\n    return text("hi")\n')
        self.assertEqual([m.name for m in r.middleware], ["auth", "logging"])

    def test_call_expression_entry(self):
        r = _first_route(
            'route GET "/x" with rate_limit(10, 60):\n    return text("hi")\n')
        self.assertEqual(len(r.middleware), 1)
        self.assertIsInstance(r.middleware[0], CallExpression)
        self.assertEqual(r.middleware[0].name, "rate_limit")
        self.assertEqual(len(r.middleware[0].args), 2)

    def test_mixed_entries(self):
        r = _first_route(
            'route POST "/x" with logging, rate_limit(5, 1), auth:\n'
            '    return text("hi")\n')
        self.assertEqual(
            [type(m).__name__ for m in r.middleware],
            ["Identifier", "CallExpression", "Identifier"])

    def test_method_path_and_body_are_unchanged(self):
        r = _first_route(
            'route PUT "/a/b" with auth:\n    let x = 1\n    return text("hi")\n')
        self.assertEqual((r.method, r.path), ("PUT", "/a/b"))
        self.assertEqual(len(r.body), 2)

    def _parse_error(self, src):
        with self.assertRaises(Exception) as cm:
            _parse(src)
        self.assertEqual(type(cm.exception).__name__, "ParseError")

    def test_dangling_with_is_an_error(self):
        self._parse_error('route GET "/x" with:\n    return text("hi")\n')

    def test_trailing_comma_is_an_error(self):
        self._parse_error('route GET "/x" with auth,:\n    return text("hi")\n')

    def test_missing_comma_is_an_error(self):
        self._parse_error(
            'route GET "/x" with auth logging:\n    return text("hi")\n')


class TestSelfHostedParity(unittest.TestCase):
    """parser.nk must produce exactly the AST parser.py does."""

    def _same(self, src):
        from tests.test_self_hosted_phase28_parity import _asts_match
        ok, py, nk = _asts_match(textwrap.dedent(src))
        self.assertTrue(ok, "parsers disagree:\n  py: %r\n  nk: %r" % (py, nk))
        return py

    def test_plain_route_still_matches(self):
        py = self._same('route GET "/x":\n    return text("hi")\n')
        # the field is always present, even when empty
        self.assertEqual(py["statements"][0]["middleware"], [])

    def test_identifiers(self):
        self._same('route GET "/x" with auth, logging:\n    return text("hi")\n')

    def test_calls_and_mixed(self):
        self._same(
            'route POST "/x" with logging, rate_limit(5, 1), auth("t"):\n'
            '    return text("hi")\n')

    def test_inside_a_larger_program(self):
        self._same('''
            task gate(request):
                return respond(401, "no")

            route GET "/a" with gate:
                return text("a")

            route GET "/b":
                return text("b")
        ''')

    def test_grammar_md_documents_the_clause(self):
        text = open(os.path.join(REPO_ROOT, "GRAMMAR.md"),
                    encoding="utf-8").read()
        rule = re.search(r"^route_stmt\s*=.*?;", text, re.S | re.M)
        self.assertIsNotNone(rule, "route_stmt rule not found in GRAMMAR.md")
        self.assertIn("'with'", rule.group(0))

    def test_grammar_coverage_tool_is_happy(self):
        p = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "tools",
                                          "check_grammar_coverage.py")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=REPO_ROOT, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_example_program_parses_identically(self):
        path = os.path.join(REPO_ROOT, "examples", "web_middleware.nk")
        self.assertTrue(os.path.exists(path), "examples/web_middleware.nk")
        with open(path, encoding="utf-8") as f:
            self._same(f.read())


# ── response helpers ─────────────────────────────────────────

class TestResponseHelpers(_WebCase):

    def test_json_defaults_to_200(self):
        r = self.app('route GET "/x":\n    return json({"a": 1})\n').get()
        self.assertEqual((r.status_code, r.get_json()), (200, {"a": 1}))

    def test_json_accepts_a_status(self):
        r = self.app('route GET "/x":\n    return json({"a": 1}, 201)\n').get()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json(), {"a": 1})

    def test_text_and_html_accept_a_status(self):
        app = self.app('''
            route GET "/t":
                return text("short", 418)
            route GET "/h":
                return html("<b>x</b>", 404)
        ''')
        t, h = app.get("/t"), app.get("/h")
        self.assertEqual((t.status_code, t.get_data(as_text=True)),
                         (418, "short"))
        self.assertEqual(h.status_code, 404)
        self.assertIn("text/html", h.content_type)

    def test_respond_with_text(self):
        r = self.app('route GET "/x":\n    return respond(404, "nope")\n').get()
        self.assertEqual((r.status_code, r.get_data(as_text=True)),
                         (404, "nope"))
        self.assertIn("text/plain", r.content_type)

    def test_respond_with_data_is_json(self):
        r = self.app(
            'route GET "/x":\n    return respond(202, {"ok": true})\n').get()
        self.assertEqual((r.status_code, r.get_json()), (202, {"ok": True}))
        self.assertIn("application/json", r.content_type)

    def test_respond_with_headers(self):
        r = self.app(
            'route GET "/x":\n'
            '    return respond(401, "no", {"WWW-Authenticate": "Bearer"})\n'
        ).get()
        self.assertEqual(r.headers["WWW-Authenticate"], "Bearer")

    def test_respond_rejects_a_bad_status(self):
        for bad in ('"x"', "99", "1000", "true", "2.5"):
            r = self.app('route GET "/x":\n    return respond(%s, "a")\n'
                         % bad).get()
            self.assertEqual(r.status_code, 500, bad)
            self.assertIn("status", r.get_data(as_text=True).lower(), bad)


# ── request fields ───────────────────────────────────────────

class TestRequestFields(_WebCase):

    def test_dataclass_defaults(self):
        from nekova.web.request import NEKOVARequest
        req = NEKOVARequest()
        self.assertEqual(req.context, {})
        self.assertEqual(req.remote_addr, "")
        req.context["a"] = 1
        self.assertEqual(NEKOVARequest().context, {})  # not shared

    def test_set_context_stores_a_value(self):
        from nekova.web.request import NEKOVARequest
        req = NEKOVARequest()
        req.set_context("user", "ada")
        self.assertEqual(req.context, {"user": "ada"})
        for bad in ("", None, 5):
            with self.assertRaises(ValueError, msg=repr(bad)):
                req.set_context(bad, 1)

    def test_get_header_ignores_case(self):
        from nekova.web.request import NEKOVARequest
        req = NEKOVARequest(headers={"authorization": "x"})
        self.assertEqual(req.get_header("Authorization"), "x")
        self.assertEqual(req.get_header("X-Missing"), "")
        self.assertEqual(req.get_header("X-Missing", "d"), "d")

    def test_remote_addr_reaches_the_handler(self):
        r = self.app(
            'route GET "/x":\n    return text(request.remote_addr)\n').get()
        self.assertEqual(r.get_data(as_text=True), "127.0.0.1")

    def test_context_starts_empty_for_every_request(self):
        app = self.app('''
            task mark(request):
                request.set_context("seen", true)

            route GET "/x" with mark:
                return text(len(request.context))
        ''')
        self.assertEqual(app.get().get_data(as_text=True), "1")
        self.assertEqual(app.get().get_data(as_text=True), "1")  # not 2


# ── user-defined middleware ──────────────────────────────────

class TestUserMiddleware(_WebCase):

    def test_returning_nothing_continues_to_the_handler(self):
        r = self.app('''
            task noop(request):
                let x = 1

            route GET "/x" with noop:
                return text("handler")
        ''').get()
        self.assertEqual(r.get_data(as_text=True), "handler")

    def test_returning_a_response_stops_the_request(self):
        r = self.app('''
            task gate(request):
                return respond(401, {"error": "stop"})

            route GET "/x" with gate:
                return text("handler")
        ''').get()
        self.assertEqual((r.status_code, r.get_json()),
                         (401, {"error": "stop"}))

    def test_entries_run_left_to_right(self):
        app = self.app('''
            task first(request):
                return respond(401, "first")

            task second(request):
                return respond(402, "second")

            route GET "/a" with first, second:
                return text("handler")

            route GET "/b" with second, first:
                return text("handler")
        ''')
        self.assertEqual(app.get("/a").status_code, 401)
        self.assertEqual(app.get("/b").status_code, 402)

    def test_context_carries_data_to_the_handler(self):
        r = self.app('''
            task who(request):
                request.set_context("user", "ada")

            route GET "/x" with who:
                return text(request.context["user"])
        ''').get()
        self.assertEqual(r.get_data(as_text=True), "ada")

    def test_middleware_can_read_the_request(self):
        app = self.app('''
            task no_bots(request):
                if "X-Bot" in request.headers:
                    return respond(403, "no bots")

            route GET "/x" with no_bots:
                return text("ok")
        ''')
        self.assertEqual(app.get().status_code, 200)
        self.assertEqual(app.get(headers={"X-Bot": "1"}).status_code, 403)

    def test_a_factory_can_supply_the_middleware(self):
        app = self.app('''
            task require_header(name):
                task check(request):
                    if not (name in request.headers):
                        return respond(400, "missing " + name)
                return check

            route GET "/x" with require_header("X-Key"):
                return text("ok")
        ''')
        self.assertEqual(app.get().status_code, 400)
        self.assertEqual(app.get(headers={"X-Key": "1"}).status_code, 200)

    def test_a_non_response_return_is_refused_not_served(self):
        # `return true` must not turn into a 200 "True" body, and must
        # not let the request through either
        r = self.app('''
            task sloppy(request):
                return true

            route GET "/x" with sloppy:
                return text("handler")
        ''').get()
        self.assertEqual(r.status_code, 500)
        body = r.get_data(as_text=True)
        self.assertNotEqual(body, "handler")
        self.assertIn("sloppy", body)

    def test_a_crashing_middleware_is_a_500_and_skips_the_handler(self):
        r = self.app('''
            task broken(request):
                return no_such_name

            route GET "/x" with broken:
                return text("handler")
        ''').get()
        self.assertEqual(r.status_code, 500)
        self.assertNotEqual(r.get_data(as_text=True), "handler")

    def test_routes_without_middleware_are_untouched(self):
        r = self.app('route GET "/x":\n    return text("plain")\n').get()
        self.assertEqual(r.get_data(as_text=True), "plain")


# ── the chain runner ─────────────────────────────────────────

class TestRunChain(unittest.TestCase):

    def setUp(self):
        from nekova.web.middleware import Middleware, run_chain
        from nekova.web.request import NEKOVARequest
        from nekova.web.response import NEKOVAResponse, text_response
        self.run_chain = run_chain
        self.req = NEKOVARequest()
        self.log = []
        log = self.log

        class Rec(Middleware):
            def __init__(self, name, stop=None, boom=False, boom_after=False):
                self.name, self.stop = name, stop
                self.boom, self.boom_after = boom, boom_after

            def before(self, request):
                log.append("before:" + self.name)
                if self.boom:
                    raise RuntimeError("kaput")
                return self.stop

            def after(self, request, response):
                log.append("after:%s:%d" % (self.name, response.status))
                if self.boom_after:
                    raise RuntimeError("after kaput")

        self.Rec = Rec
        self.ok = lambda: (log.append("handler"), text_response("h"))[1]
        self.stop401 = NEKOVAResponse(body="no", status=401)

    def test_before_in_order_after_in_reverse(self):
        resp = self.run_chain(self.req, [self.Rec("a"), self.Rec("b")],
                              lambda r: self.ok())
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.log, ["before:a", "before:b", "handler",
                                    "after:b:200", "after:a:200"])

    def test_short_circuit_skips_the_handler_and_later_entries(self):
        resp = self.run_chain(
            self.req,
            [self.Rec("a"), self.Rec("b", stop=self.stop401), self.Rec("c")],
            lambda r: self.ok())
        self.assertEqual(resp.status, 401)
        self.assertEqual(self.log, ["before:a", "before:b",
                                    "after:b:401", "after:a:401"])

    def test_an_exception_becomes_a_500_and_earlier_after_hooks_see_it(self):
        resp = self.run_chain(
            self.req, [self.Rec("a"), self.Rec("b", boom=True)],
            lambda r: self.ok())
        self.assertEqual(resp.status, 500)
        self.assertEqual(self.log, ["before:a", "before:b", "after:a:500"])

    def test_a_failing_after_hook_cannot_break_the_response(self):
        resp = self.run_chain(
            self.req, [self.Rec("a"), self.Rec("b", boom_after=True)],
            lambda r: self.ok())
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.log[-2:], ["after:b:200", "after:a:200"])

    def test_a_handler_exception_is_a_500_seen_by_after_hooks(self):
        def bad(r):
            raise ValueError("handler blew up")
        resp = self.run_chain(self.req, [self.Rec("a")], bad)
        self.assertEqual(resp.status, 500)
        self.assertIn("handler blew up", resp.body)
        self.assertEqual(self.log, ["before:a", "after:a:500"])

    def test_a_non_response_from_before_is_a_500(self):
        class Sloppy(self.Rec):
            def before(self, request):
                return "not a response"
        resp = self.run_chain(self.req, [Sloppy("s")], lambda r: self.ok())
        self.assertEqual(resp.status, 500)
        self.assertNotIn("handler", self.log)


# ── logging ──────────────────────────────────────────────────

class TestLogging(_WebCase):

    def _request(self, source, path="/x", **kw):
        app, buf = self.app(source), io.StringIO()
        with contextlib.redirect_stdout(buf):
            resp = app.get(path, **kw)
        return resp, buf.getvalue()

    def test_logs_method_path_status_and_time(self):
        _, out = self._request(
            'route GET "/x" with logging:\n    return text("hi")\n')
        self.assertRegex(out, r"GET /x 200 \d+(\.\d+)?ms")
        self.assertEqual(out.count("\n"), 1)

    def test_logs_the_client_address(self):
        _, out = self._request(
            'route GET "/x" with logging:\n    return text("hi")\n')
        self.assertIn("127.0.0.1", out)

    def test_never_logs_the_query_string_or_credentials(self):
        _, out = self._request(
            'route GET "/x" with logging:\n    return text("hi")\n',
            path="/x?token=QUERYSECRET",
            headers={"Authorization": "Bearer HEADERSECRET"})
        self.assertNotIn("QUERYSECRET", out)
        self.assertNotIn("HEADERSECRET", out)

    def test_logs_requests_rejected_by_later_middleware(self):
        resp, out = self._request('''
            task deny(request):
                return respond(401, "no")

            route GET "/x" with logging, deny:
                return text("hi")
        ''')
        self.assertEqual(resp.status_code, 401)
        self.assertRegex(out, r"GET /x 401 ")

    def test_does_not_log_requests_rejected_by_earlier_middleware(self):
        resp, out = self._request('''
            task deny(request):
                return respond(401, "no")

            route GET "/x" with deny, logging:
                return text("hi")
        ''')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(out, "")

    def test_logs_a_500(self):
        _, out = self._request('''
            route GET "/x" with logging:
                return no_such_name
        ''')
        self.assertRegex(out, r"GET /x 500 ")

    def test_writes_to_a_given_stream(self):
        from nekova.web.middleware import LoggingMiddleware
        from nekova.web.request import NEKOVARequest
        from nekova.web.response import text_response
        stream = io.StringIO()
        mw = LoggingMiddleware(stream=stream)
        req = NEKOVARequest(method="POST", path="/p")
        mw.before(req)
        mw.after(req, text_response("x"))
        self.assertRegex(stream.getvalue(), r"POST /p 200 \d+(\.\d+)?ms -\n$")


# ── rate limiting ────────────────────────────────────────────

class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class TestRateLimit(_WebCase):

    def _mw(self, **kw):
        from nekova.web.middleware import RateLimitMiddleware
        self.clock = _Clock()
        return RateLimitMiddleware(clock=self.clock, **kw)

    def _req(self, addr="1.1.1.1"):
        from nekova.web.request import NEKOVARequest
        return NEKOVARequest(remote_addr=addr)

    def test_allows_up_to_the_limit_then_429(self):
        mw = self._mw(limit=2, window=10)
        self.assertIsNone(mw.before(self._req()))
        self.assertIsNone(mw.before(self._req()))
        resp = mw.before(self._req())
        self.assertEqual(resp.status, 429)
        self.assertEqual(resp.headers["Retry-After"], "10")

    def test_retry_after_counts_down(self):
        mw = self._mw(limit=1, window=10)
        mw.before(self._req())
        self.clock.t = 3
        self.assertEqual(mw.before(self._req()).headers["Retry-After"], "7")

    def test_the_window_resets(self):
        mw = self._mw(limit=1, window=10)
        mw.before(self._req())
        self.assertEqual(mw.before(self._req()).status, 429)
        self.clock.t = 10
        self.assertIsNone(mw.before(self._req()))

    def test_clients_are_counted_separately(self):
        mw = self._mw(limit=1, window=10)
        self.assertIsNone(mw.before(self._req("1.1.1.1")))
        self.assertIsNone(mw.before(self._req("2.2.2.2")))
        self.assertEqual(mw.before(self._req("1.1.1.1")).status, 429)

    def test_unknown_clients_share_one_bucket(self):
        mw = self._mw(limit=1, window=10)
        self.assertIsNone(mw.before(self._req("")))
        self.assertEqual(mw.before(self._req("")).status, 429)

    def test_expired_clients_are_forgotten(self):
        mw = self._mw(limit=5, window=10)
        for i in range(1000):
            mw.before(self._req("10.0.%d.%d" % (i // 250, i % 250)))
        self.assertEqual(mw.tracked_clients, 1000)
        self.clock.t = 100
        mw.before(self._req("9.9.9.9"))
        self.assertEqual(mw.tracked_clients, 1)

    def test_tracked_clients_are_capped(self):
        mw = self._mw(limit=5, window=1000, max_clients=5)
        for i in range(20):
            mw.before(self._req("10.0.0.%d" % i))
        self.assertLessEqual(mw.tracked_clients, 5)

    def test_bad_arguments_are_refused(self):
        from nekova.web.middleware import RateLimitMiddleware
        for kw in ({"limit": 0}, {"limit": -1}, {"limit": "x"},
                   {"limit": True}, {"limit": 2.5},
                   {"window": 0}, {"window": -5}, {"window": "x"}):
            with self.assertRaises(ValueError, msg=repr(kw)):
                RateLimitMiddleware(**kw)

    def test_over_http(self):
        app = self.app('''
            route GET "/x" with rate_limit(2, 60):
                return text("ok")

            route GET "/y" with rate_limit(1, 60):
                return text("ok")
        ''')
        self.assertEqual([app.get().status_code for _ in range(3)],
                         [200, 200, 429])
        r = app.get()
        self.assertEqual(r.status_code, 429)
        self.assertTrue(r.headers["Retry-After"].isdigit())
        self.assertIn("rate limit", r.get_json()["error"].lower())
        # a different route has its own counter
        self.assertEqual(app.get("/y").status_code, 200)

    def test_bare_rate_limit_uses_a_default(self):
        app = self.app('route GET "/x" with rate_limit:\n    return text("ok")\n')
        self.assertEqual(app.get().status_code, 200)

    def test_bad_arguments_fail_at_declaration(self):
        with self.assertRaises(NEKOVARuntimeError) as cm:
            self.app('route GET "/x" with rate_limit(0, 60):\n'
                     '    return text("ok")\n')
        self.assertIn("rate_limit", str(cm.exception))


# ── auth ─────────────────────────────────────────────────────

class TestAuth(_WebCase):

    ROUTE = 'route GET "/x" with auth:\n    return text("secret page")\n'

    def _env(self, token="s3cret"):
        env = {k: v for k, v in os.environ.items()
               if k != "NEKOVA_AUTH_TOKEN"}
        if token is not None:
            env["NEKOVA_AUTH_TOKEN"] = token
        return mock.patch.dict(os.environ, env, clear=True)

    def _bearer(self, token, scheme="Bearer"):
        return {"headers": {"Authorization": "%s %s" % (scheme, token)}}

    def test_the_right_token_gets_in(self):
        with self._env():
            r = self.app(self.ROUTE).get(**self._bearer("s3cret"))
        self.assertEqual((r.status_code, r.get_data(as_text=True)),
                         (200, "secret page"))

    def test_the_scheme_is_case_insensitive(self):
        with self._env():
            app = self.app(self.ROUTE)
            self.assertEqual(
                app.get(**self._bearer("s3cret", "bearer")).status_code, 200)
            self.assertEqual(
                app.get(**self._bearer("s3cret", "BEARER")).status_code, 200)

    def test_everything_else_is_a_401(self):
        with self._env():
            app = self.app(self.ROUTE)
            attempts = {
                "no header": {},
                "wrong token": self._bearer("nope"),
                "prefix of the token": self._bearer("s3cre"),
                "token plus extra": self._bearer("s3cretX"),
                "empty token": {"headers": {"Authorization": "Bearer "}},
                "wrong scheme": self._bearer("s3cret", "Basic"),
                "no scheme": {"headers": {"Authorization": "s3cret"}},
            }
            for name, kw in attempts.items():
                r = app.get(**kw)
                self.assertEqual(r.status_code, 401, name)
                self.assertEqual(r.get_json(), {"error": "unauthorized"}, name)
                self.assertEqual(r.headers["WWW-Authenticate"], "Bearer", name)

    def test_a_rejection_never_reveals_the_token(self):
        with self._env("TOPSECRETVALUE"):
            r = self.app(self.ROUTE).get(**self._bearer("wrong"))
        blob = r.get_data(as_text=True) + str(dict(r.headers))
        self.assertNotIn("TOPSECRETVALUE", blob)

    def test_the_handler_is_told_the_request_was_authenticated(self):
        with self._env():
            r = self.app('''
                route GET "/x" with auth:
                    if request.context["authenticated"]:
                        return text("yes")
                    return text("no")
            ''').get(**self._bearer("s3cret"))
        self.assertEqual(r.get_data(as_text=True), "yes")

    def test_an_explicit_token(self):
        with self._env(None):
            app = self.app('route GET "/x" with auth("abc"):\n'
                           '    return text("ok")\n')
            self.assertEqual(app.get(**self._bearer("abc")).status_code, 200)
            self.assertEqual(app.get(**self._bearer("abd")).status_code, 401)

    def test_several_tokens(self):
        with self._env(None):
            app = self.app('route GET "/x" with auth(["a", "b"]):\n'
                           '    return text("ok")\n')
            self.assertEqual(app.get(**self._bearer("a")).status_code, 200)
            self.assertEqual(app.get(**self._bearer("b")).status_code, 200)
            self.assertEqual(app.get(**self._bearer("c")).status_code, 401)

    def test_an_explicit_token_wins_over_the_environment(self):
        with self._env("from-env"):
            app = self.app('route GET "/x" with auth("explicit"):\n'
                           '    return text("ok")\n')
            self.assertEqual(
                app.get(**self._bearer("from-env")).status_code, 401)
            self.assertEqual(
                app.get(**self._bearer("explicit")).status_code, 200)

    def test_no_configured_token_fails_at_declaration(self):
        # never "allow everyone" and never "silently deny everyone"
        with self._env(None):
            with self.assertRaises(NEKOVARuntimeError) as cm:
                self.app(self.ROUTE)
        self.assertIn("NEKOVA_AUTH_TOKEN", str(cm.exception))

    def test_an_empty_token_is_refused(self):
        for value in ("", "   "):
            with self._env(value):
                with self.assertRaises(NEKOVARuntimeError, msg=repr(value)):
                    self.app(self.ROUTE)
        with self._env(None):
            for arg in ('""', "[]", '["a", ""]', "5", '["a", 5]'):
                with self.assertRaises(NEKOVARuntimeError, msg=arg):
                    self.app('route GET "/x" with auth(%s):\n'
                             '    return text("ok")\n' % arg)

    def test_a_failed_declaration_leaves_the_route_unregistered(self):
        with self._env(None):
            with self.assertRaises(NEKOVARuntimeError):
                self.app(self.ROUTE)
        self.assertEqual(wm._server.router.get_routes(), [])

    def test_tokens_are_compared_in_constant_time(self):
        import hmac
        with self._env():
            app = self.app(self.ROUTE)
            with mock.patch("nekova.web.middleware.hmac.compare_digest",
                            wraps=hmac.compare_digest) as spy:
                app.get(**self._bearer("wrong"))
        self.assertTrue(spy.called)

    def test_the_token_is_not_stored_in_clear_on_the_instance_repr(self):
        from nekova.web.middleware import AuthMiddleware
        self.assertNotIn("hunter2", repr(AuthMiddleware(["hunter2"])))


# ── nekova fmt must not mangle the new syntax ────────────────

class TestFormatter(unittest.TestCase):
    """
    The formatter used to glue any word that follows a string literal
    onto it (`"ada"and ready`). Every middleware route has one -
    `route GET "/x" with auth` - so it had to be fixed.
    """

    def _fmt(self, src):
        from nekova.cli.formatter import fmt_source
        return fmt_source(src)

    def test_middleware_routes_are_left_alone(self):
        for src in (
            'route GET "/x" with auth, logging:\n    return text("hi")\n',
            'route GET "/x" with rate_limit(10, 60):\n    return text("hi")\n',
            'route POST "/x" with logging, rate_limit(5, 1), auth("t"):\n'
            '    return text("hi")\n',
        ):
            self.assertEqual(self._fmt(src), src)

    def test_words_after_a_string_keep_their_space(self):
        for src in ('if name == "ada" and ready:\n    show 1\n',
                    'let ok = "a" in names\n',
                    'if x == "a" or y == "b":\n    show 1\n'):
            self.assertEqual(self._fmt(src), src)

    def test_punctuation_after_a_string_behaves_as_before(self):
        self.assertEqual(self._fmt('show "total" , 5\n'), 'show "total", 5\n')

    def test_it_is_idempotent_and_the_result_still_parses(self):
        messy = ('route   GET  "/x"   with  auth ,logging,rate_limit( 10,60 ):\n'
                 '    return text( "hi" )\n')
        once = self._fmt(messy)
        self.assertEqual(self._fmt(once), once)
        _first_route(once)  # still parses


# ── how names resolve ────────────────────────────────────────

class TestResolution(_WebCase):

    def test_a_user_task_overrides_a_builtin_of_the_same_name(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEKOVA_AUTH_TOKEN", None)
            r = self.app('''
                task auth(request):
                    return respond(403, "custom")

                route GET "/x" with auth:
                    return text("ok")
            ''').get()
        self.assertEqual((r.status_code, r.get_data(as_text=True)),
                         (403, "custom"))

    def test_builtins_do_not_leak_into_global_scope(self):
        app = self.app('route GET "/x" with logging, rate_limit(5, 5):\n'
                       '    return text("ok")\n')
        for name in ("logging", "auth", "rate_limit"):
            self.assertNotIn(name, app.interp.globals)

    def test_an_undefined_name_fails_at_declaration(self):
        with self.assertRaises(NEKOVARuntimeError) as cm:
            self.app('route GET "/x" with nosuch:\n    return text("ok")\n')
        self.assertIn("nosuch", str(cm.exception))
        self.assertEqual(wm._server.router.get_routes(), [])

    def test_a_non_callable_fails_at_declaration(self):
        with self.assertRaises(NEKOVARuntimeError) as cm:
            self.app('let logging = 5\n'
                     'route GET "/x" with logging:\n    return text("ok")\n')
        self.assertIn("middleware", str(cm.exception).lower())

    def test_builtin_names_are_documented_in_the_error(self):
        with self.assertRaises(NEKOVARuntimeError) as cm:
            self.app('route GET "/x" with nosuch:\n    return text("ok")\n')
        msg = str(cm.exception)
        for name in ("auth", "logging", "rate_limit"):
            self.assertIn(name, msg)

    def test_registry_exposes_the_three_builtins(self):
        from nekova.web.middleware import BUILTIN_MIDDLEWARE
        self.assertEqual(set(BUILTIN_MIDDLEWARE),
                         {"auth", "logging", "rate_limit"})


if __name__ == "__main__":
    unittest.main()