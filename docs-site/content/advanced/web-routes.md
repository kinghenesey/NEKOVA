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