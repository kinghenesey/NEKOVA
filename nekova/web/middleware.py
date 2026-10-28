# =============================================================
# NEKOVA Web Framework - Route middleware
# Phase 29: `route GET "/x" with auth, logging, rate_limit(10, 60):`
# =============================================================
# A middleware is anything with two hooks:
#
#   before(request)           runs ahead of the handler. Return None to
#                             carry on, or a response to end the request
#                             there (the handler never runs).
#   after(request, response)  runs once the response is known, for every
#                             middleware whose before() ran, in reverse
#                             order. Its return value is ignored and an
#                             exception inside it is swallowed - an
#                             observer must never break a response.
#
# User tasks are adapted to this shape (before only). The three
# built-ins below - auth, logging, rate_limit - are written against it.
#
# Built-in names are only visible inside a `with` clause, and a program
# that defines the same name itself keeps its own.
# =============================================================

import hmac
import math
import os
import re
import sys
import threading
import time
from datetime import datetime

from nekova.web.response import (
    NEKOVAResponse,
    error_response,
    json_response,
)

AUTH_TOKEN_ENV = "NEKOVA_AUTH_TOKEN"

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _name_of(mw) -> str:
    return getattr(mw, "name", None) or type(mw).__name__


class Middleware:
    """Base class: both hooks do nothing."""
    name = "middleware"

    def before(self, request):
        return None

    def after(self, request, response):
        return None


class CallableMiddleware(Middleware):
    """Adapts a function `(request) -> None | response` (a user task)."""

    def __init__(self, fn, name: str):
        self._fn = fn
        self.name = name

    def before(self, request):
        return self._fn(request)

    def __repr__(self):
        return f"Middleware({self.name})"


def run_chain(request, chain, handler):
    """
    Run `chain` around `handler` and return the final response.

    Never raises: a failure in a middleware or in the handler becomes a
    500 response, and every middleware whose before() completed still
    gets its after() call, so e.g. logging records the 500.
    """
    ran = []
    response = None
    try:
        for mw in chain:
            result = mw.before(request)
            ran.append(mw)
            if result is None:
                continue
            if not isinstance(result, NEKOVAResponse):
                shown = repr(result)
                if len(shown) > 40:
                    shown = shown[:37] + "..."
                raise TypeError(
                    f"'{_name_of(mw)}' returned {shown}. Return nothing to "
                    f"carry on, or a response such as respond(401, ...) "
                    f"to stop the request."
                )
            response = result
            break
    except Exception as e:
        response = error_response(
            f"Middleware error: {str(e).strip() or type(e).__name__}", 500)

    if response is None:
        try:
            response = handler(request)
        except Exception as e:
            response = error_response(
                f"Handler error: {str(e).strip() or type(e).__name__}", 500)

    for mw in reversed(ran):
        try:
            mw.after(request, response)
        except Exception:
            pass  # an observer must never break the response
    return response


# ── logging ───────────────────────────────────────────────────

class LoggingMiddleware(Middleware):
    """
    One line per request, written once the response is known:

        2026-10-24 14:03:11 GET /admin 200 3.2ms 127.0.0.1

    Logs the path only - never the query string or any header - so
    tokens that travel in either cannot end up in a log file. Control
    characters are replaced, so a request cannot forge extra log lines.
    """
    name = "logging"

    def __init__(self, stream=None, clock=time.perf_counter):
        self._stream = stream
        self._clock = clock
        self._local = threading.local()

    def before(self, request):
        self._local.started = self._clock()
        return None

    def after(self, request, response):
        started = getattr(self._local, "started", None)
        elapsed_ms = 0.0 if started is None else (self._clock() - started) * 1000
        line = "%s %s %s %d %.1fms %s\n" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            _CONTROL_CHARS.sub("?", str(request.method)),
            _CONTROL_CHARS.sub("?", str(request.path)),
            response.status,
            elapsed_ms,
            _CONTROL_CHARS.sub("?", request.remote_addr or "-"),
        )
        stream = self._stream if self._stream is not None else sys.stdout
        stream.write(line)
        flush = getattr(stream, "flush", None)
        if flush:
            flush()


# ── rate limiting ─────────────────────────────────────────────

def _positive_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{what} must be a whole number of 1 or more, "
                         f"got {value!r}")
    return value


class RateLimitMiddleware(Middleware):
    """
    At most `limit` requests per `window` seconds from one client
    address, then 429 with a Retry-After header.

    A fixed window kept in memory, per middleware instance - so each
    `rate_limit(...)` in a route list counts on its own, and counts are
    lost when the process restarts. The client is the connection's
    address: behind a reverse proxy that is the proxy, so every user
    shares one allowance. Memory is bounded: expired entries are
    dropped each window, and past `max_clients` the oldest go first
    (a flood of distinct addresses can therefore reset other clients'
    counts, which is the price of a hard memory cap).
    """
    name = "rate_limit"

    def __init__(self, limit=60, window=60, clock=time.monotonic,
                 max_clients=10_000):
        self.limit = _positive_int(limit, "limit")
        if (isinstance(window, bool) or not isinstance(window, (int, float))
                or not math.isfinite(window) or window <= 0):
            raise ValueError(
                f"window (seconds) must be a number greater than 0, "
                f"got {window!r}")
        self.window = window
        self._max_clients = _positive_int(max_clients, "max_clients")
        self._clock = clock
        self._lock = threading.Lock()
        # insertion order == order of window start, so the oldest entry
        # is always first
        self._buckets = {}
        self._last_purge = clock()

    @property
    def tracked_clients(self) -> int:
        return len(self._buckets)

    def _purge(self, now):
        for key in list(self._buckets):
            if now - self._buckets[key][0] < self.window:
                break  # everything after this one is newer
            del self._buckets[key]
        self._last_purge = now

    def before(self, request):
        now = self._clock()
        key = request.remote_addr or ""
        with self._lock:
            if now - self._last_purge >= self.window:
                self._purge(now)
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket[0] >= self.window:
                if bucket is not None:
                    del self._buckets[key]  # re-insert at the newest end
                elif len(self._buckets) >= self._max_clients:
                    del self._buckets[next(iter(self._buckets))]
                bucket = self._buckets[key] = [now, 0]
            bucket[1] += 1
            if bucket[1] <= self.limit:
                return None
            retry_after = max(1, math.ceil(self.window - (now - bucket[0])))
        response = json_response({"error": "rate limit exceeded"}, 429)
        response.headers["Retry-After"] = str(retry_after)
        return response


# ── auth ──────────────────────────────────────────────────────

class AuthMiddleware(Middleware):
    """
    Requires `Authorization: Bearer <token>` to match a configured
    token. Anything else is a 401 with `WWW-Authenticate: Bearer`; the
    response never says whether the header was missing, malformed or
    simply wrong, and never contains a token.

    Tokens are compared in constant time. On success the handler can
    read request.context["authenticated"].
    """
    name = "auth"

    def __init__(self, tokens):
        if isinstance(tokens, str):
            tokens = [tokens]
        if not isinstance(tokens, (list, tuple)) or not tokens:
            raise ValueError("expected a token string or a non-empty list "
                             "of token strings")
        encoded = []
        for t in tokens:
            if not isinstance(t, str):
                raise ValueError(f"tokens must be strings, got {t!r}")
            if not t.strip():
                raise ValueError("a token must not be empty")
            encoded.append(t.encode("utf-8"))
        self._tokens = encoded

    def __repr__(self):
        return f"AuthMiddleware(<{len(self._tokens)} token(s) configured>)"

    def before(self, request):
        scheme, _, supplied = request.get_header("Authorization").partition(" ")
        ok = False
        if scheme.lower() == "bearer" and supplied:
            candidate = supplied.encode("utf-8")
            for token in self._tokens:  # no early exit
                if hmac.compare_digest(candidate, token):
                    ok = True
        if not ok:
            response = json_response({"error": "unauthorized"}, 401)
            response.headers["WWW-Authenticate"] = "Bearer"
            return response
        request.context["authenticated"] = True
        return None


# ── the built-in names ────────────────────────────────────────

class MiddlewareFactory:
    """
    A built-in middleware name. Used bare (`with logging`) it builds the
    default; called (`with rate_limit(10, 60)`) it builds a configured
    one. Problems are reported with the built-in's own name.
    """

    def __init__(self, name, build):
        self.name = name
        self._build = build

    def default(self):
        return self(*())

    def __call__(self, *args):
        try:
            return self._build(*args)
        except (ValueError, TypeError) as e:
            raise ValueError(f"{self.name}: {e}") from None

    def __repr__(self):
        return f"<built-in middleware {self.name}>"


def _build_auth(tokens=None):
    if tokens is None:
        tokens = os.environ.get(AUTH_TOKEN_ENV, "")
        if not tokens.strip():
            raise ValueError(
                f"no token configured. Set the {AUTH_TOKEN_ENV} environment "
                f'variable, or pass one: auth("token")')
    return AuthMiddleware(tokens)


def _build_logging():
    return LoggingMiddleware()


def _build_rate_limit(limit=60, window=60):
    return RateLimitMiddleware(limit, window)


BUILTIN_MIDDLEWARE = {
    "auth":       MiddlewareFactory("auth", _build_auth),
    "logging":    MiddlewareFactory("logging", _build_logging),
    "rate_limit": MiddlewareFactory("rate_limit", _build_rate_limit),
}