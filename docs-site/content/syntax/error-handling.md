---
title: Error Handling
lede: try/catch/finally, raising your own errors, and defining structured custom error types.
---

## try / catch

```nekova
try:
    let x = 10 / 0
catch e:
    show "caught: " + e
```

The caught value `e` is a real object, not just a string — building a message with `"caught: " + e` works because NEKOVA knows how to render an error object as text.

## finally

```nekova
try:
    let x = 10 / 0
catch e:
    show "caught: " + e
finally:
    show "cleanup"
```

`finally` runs whether or not an error occurred.

## raise

```nekova
try:
    raise "custom error"
catch e:
    show "caught: " + e
```

An unhandled `raise` propagates out of the program.

## Custom error types

For anything more structured than a bare string, define an error type with typed fields — optionally with defaults:

```nekova
error NetworkError:
    message str
    code int

error AppError:
    message str
    code int = 500

try:
    raise NetworkError("timeout", 408)
catch e:
    show e["message"]   # "timeout"
    show e["code"]      # 408
```

## assert

```nekova
assert 1 == 1
```

A failing `assert` raises with a clear message rather than a bare `AssertionError`.

## Errors from built-in functions

Every built-in (`int()`, `len()`, `range()`, `sum()`, and the rest) converts a bad argument into a clean NEKOVA error instead of leaking a raw Python exception:

```nekova
show int("abc")
```
```
error: Cannot convert 'abc' to a number with int().
  It needs to look like a plain number, e.g. int("42").
```

## Recursion limits

```nekova
task loop_forever(n):
    return loop_forever(n + 1)

loop_forever(1)
```

NEKOVA tracks its own call depth (500 by default), so this raises with the exact depth reached — not Python's own stack overflow error, and not a guess about whether it's "infinite" recursion versus a legitimately deep computation.