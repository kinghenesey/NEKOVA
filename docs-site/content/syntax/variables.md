---
title: Variables & Constants
lede: let for values that change, const for values that shouldn't — and NEKOVA enforces the difference at runtime.
---

## let

```nekova
let name = "Ada"
let age = 30
name = "Grace"
```

`let` declares a variable. Reassigning it later — with or without writing `let` again — works fine.

## const

```nekova
const MAX_RETRIES = 3
show MAX_RETRIES
```

A `const` binding can be set once. Both reassigning it and redeclaring it raise a runtime error:

```nekova
const MAX_RETRIES = 3
MAX_RETRIES = 5
```
```
error: Cannot reassign 'MAX_RETRIES' — it was declared with 'const' and
consts can't be changed after they're set.
  Use 'let MAX_RETRIES = ...' instead if you need it to change.
```

`const` is deliberately simpler than `let` — no destructuring form, no captured-`think` form. It exists for one job: a value that should never silently change.

## Type hints

```nekova
let age: int = 30
let name: str = "Ada"
```

Type hints are enforced when present. NEKOVA currently checks `int`, `float`, `str`, `bool`, `list`, and `dict` — a hint using any other word (like a descriptive `number` or `text`) is accepted syntactically but isn't type-checked, so stick to the six recognized names if you want real enforcement.

## null

```nekova
let user = null

if user:
    show "has a user"
else:
    show "no user"
```

`null` is falsy, compares equal to itself, and is distinct from `false`. Arithmetic on `null` raises a clear error rather than silently producing a wrong number:

```nekova
show null + 1
```
```
error: Cannot use '+' between 'NoneType' and 'int'.
```

## Booleans

```nekova
let is_ready = true
let is_done = false
```

## The type-mismatch guardrail

One specific case is worth calling out: mixing a string and a number with `+` raises instead of silently concatenating.

```nekova
show "5" + 3
```
```
error: Cannot use '+' between 'str' and 'int'.
  Convert one side explicitly, e.g. str(value) or int(value).
```

This is deliberate — `"5" + 3` silently becoming `"53"` is one of the most common sources of confusing bugs in JS-like languages, and NEKOVA's whole design philosophy is catching exactly this kind of mistake at the point it happens.