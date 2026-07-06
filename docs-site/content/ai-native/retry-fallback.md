---
title: retry & fallback
lede: Structured retry logic for flaky operations — an AI call, a network request, anything that can transiently fail.
---

## Basic usage

```nekova
retry 3:
    let x = think "hello"
    show x
fallback:
    show "could not get a response"
```

`retry <n>` attempts the block up to `n` times. If every attempt raises, the `fallback` block runs instead of letting the error propagate.

## Why this exists

AI calls (and network calls generally) fail transiently more often than most code — a timeout, a rate limit, a dropped connection. `retry`/`fallback` makes handling that a language-level pattern instead of hand-rolled loop-and-try/catch boilerplate every time.

## Combined with raise

```nekova
task fetch_data():
    raise "simulated failure"

retry 3:
    fetch_data()
fallback:
    show "all 3 attempts failed"
```