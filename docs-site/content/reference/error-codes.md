---
title: Error Codes
lede: Every error and warning code NEKOVA can report, and what each one means.
---

## Runtime errors (raised while a program runs)

| Code | Name | Meaning |
|---|---|---|
| E001 | Variable Not Found | A name was used before it was defined. Comes with a "did you mean?" suggestion (real `difflib` similarity check) when a similarly-named variable is in scope. |
| E002 | Syntax Error | The lexer or tokenizer hit something it couldn't read — includes inconsistent indentation that doesn't match any enclosing block. |
| E003 | Parse Error | The parser understood the tokens but not their arrangement. |
| E004 | Type Error | An operation got a value of the wrong type — including the `"5" + 3` string/number mismatch. |
| E005 | Runtime Error | The general-purpose runtime error — most custom interpreter errors (destructuring failures, const reassignment, keyword-argument mistakes) surface under this code. |
| E006 | Division By Zero | Self-explanatory. |
| E007 | Module Not Found | An `import`/`use` couldn't find its target. |
| E008 | Index Out of Range | A list index (or negative index) fell outside the list's bounds. |
| E009 | Key Not Found | A dict key or destructured key wasn't present — lists the keys that *were* available. |
| E010 | Maximum Call Depth Exceeded | NEKOVA's own call-depth tracking (500 by default) caught unbounded recursion, and reports the exact depth reached. |
| E011 | Reserved Keyword Used as Name | A variable or parameter tried to reuse a language keyword (e.g. naming something `fetch`). |

## Checker warnings (`nekova check`)

These don't stop your program from running — they're surfaced by the static checker.

| Code | Meaning |
|---|---|
| W001 | A name is used but may not be defined anywhere in scope. |
| W002 | A variable is defined but never used. |
| W003 | A task was called with the wrong number of arguments. |
| W005 | A built-in name (like `len` or `str`) was shadowed by a local variable. |
| W006 | Unreachable code — statements after a `return`/`raise`/`break` that can never run. |
| W009 | A `match` block has no `else` arm and may not cover every case. |

## Reading an error message

Every NEKOVA error follows the same shape: **what happened**, **why**, and **what to check next** — never a bare stack trace. For example:

```
error[E010]: Maximum Call Depth Exceeded
  Task 'loop_forever' exceeded the maximum call depth (500 nested calls).
```

If you hit a raw Python traceback instead of this format, that's considered a bug in NEKOVA itself worth reporting — see the [Changelog](changelog.html) for the ongoing audit of exactly this class of issue.