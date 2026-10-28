---
title: Web Routes
lede: A minimal built-in web layer — define routes, serve them, no framework import required.
---

## Defining routes

```nekova
use web

route GET "/":
    return "hello"

route POST "/api/chat":
    let message = think "respond to this greeting"
    return message

route PUT "/users":
    return "updated"

route DELETE "/users":
    return "deleted"
```

`route <METHOD> "<path>":` supports the standard HTTP methods — `GET`, `POST`, `PUT`, `DELETE` — followed by the path and a block that returns the response body.

## Middleware

Add `with` after the path to run middleware before the handler:

```nekova
route GET "/admin" with logging, auth("change-me"), rate_limit(10, 60):
    return json({"admin": true})
```

The entries run left to right. A middleware either lets the request carry on or answers it itself, in which case the handler never runs and the entries after it are skipped. Entries are looked up once, when the `route` statement runs, so a misspelled or missing name fails at startup instead of on the first request.

### Built-in middleware

| Name | What it does |
|---|---|
| `logging` | Prints one line per request once the response is known, such as `2026-10-24 14:03:11 GET /admin 200 3.2ms 127.0.0.1`. It logs the path only, never the query string or a header. |
| `rate_limit(limit, seconds)` | Allows `limit` requests per `seconds` from one client address (60 per 60 if you write plain `rate_limit`), then answers `429` with a `Retry-After` header. |
| `auth` | Requires `Authorization: Bearer <token>`, checked against the token in the `NEKOVA_AUTH_TOKEN` environment variable. Anything else gets a `401`. |
| `auth("token")`, `auth(["a", "b"])` | The same, with the token or tokens written in the program. |

A few things worth knowing:

- `auth` will not start without a token. If neither `NEKOVA_AUTH_TOKEN` nor an argument supplies one, the `route` statement fails with an error, so a missing setting can never leave a route open.
- A `401` never says whether the header was missing, malformed or just wrong. When the token matches, the handler can read `request.context["authenticated"]`.
- Order matters. With `with logging, auth`, requests that `auth` rejects are logged. With `with auth, logging` they are not, because `auth` answered before `logging` ran.
- `rate_limit` counts per route and per client address, in memory, so counts reset when the program restarts. Behind a reverse proxy the address it sees is the proxy's, and every user shares one allowance.

### Writing your own

A middleware is a task that takes the request. Return nothing to carry on, or a response to stop:

```nekova
task add_user(request):
    request.set_context("user", "guest")

task no_bots(request):
    if "X-Bot" in request.headers:
        return respond(403, "no bots allowed")

route GET "/hello" with no_bots, add_user:
    return text("hello, " + request.context["user"])
```

- `respond(status, body, headers)` builds a response anywhere, including inside a middleware. A dict or list body becomes JSON and anything else is plain text. The headers argument is optional.
- Returning anything else, such as `true`, is an error and the request gets a `500`. A middleware that returns a value by accident can never let a request through.
- `request.set_context(key, value)` stores a value for the rest of the request, and `request.context[key]` reads it. The context starts empty for every request.
- `request.remote_addr` is the client's address. `request.headers` has names in the form `X-Api-Key`, and `request.get_header("x-api-key")` finds a header whatever its case.
- If your program defines a task with the same name as a built-in, such as `auth`, your task is the one `with` uses.

A middleware that takes settings is a task that returns a task:

```nekova
task require_header(name):
    task check(request):
        if not (name in request.headers):
            return respond(400, "missing " + name)
    return check

route GET "/data" with require_header("X-Key"):
    return text("ok")
```

### Choosing the status

`text`, `json` and `html` take an optional status as a second argument:

```nekova
route POST "/items":
    return json({"id": 7}, 201)
```

## Starting the server

```nekova
use web

route GET "/":
    return "hello"

serve port: 8080
```

`serve` on its own (no `port:`) starts on a default port.

## Why this exists

For small AI-native services — a webhook, a single API endpoint wrapping a `think` call — pulling in a full web framework is often more setup than the actual logic warrants. `route`/`serve` cover that common case directly in the language.