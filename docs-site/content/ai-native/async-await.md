---
title: async & await
lede: async task and await, with the same defaults/varargs/type-hints support as a regular task.
---

## Basic usage

```nekova
async task greet(name):
    return name

show await greet("Sam")
```

## Why "async" if NEKOVA is single-threaded?

There's no actual concurrency being scheduled — calling an `async task` runs synchronously under the hood, the same as a regular task. `async`/`await` exist as a familiar, readable marker for operations that conceptually involve waiting (an AI call, a network request), matching syntax people already know from other languages, without requiring you to manage an event loop yourself.

## Full parity with regular tasks

`async task` supports everything a regular task does — default values, varargs, type hints, arbitrary control flow, and docstrings:

```nekova
async task add(a, b=5):
    return a + b

show await add(10)       # 15
show await add(10, 20)   # 30
```

```nekova
async task total(*nums):
    let s = 0
    for n in nums:
        s = s + n
    return s

show await total(1, 2, 3)   # 6
```

## Calling without await

Calling an `async task` without `await` still works — you just get the return value directly rather than through the `await` keyword:

```nekova
async task greet(name):
    return name

let r = greet("Sam")
show r   # "Sam"
```

## Nesting

```nekova
async task inner(x):
    return x * 2

async task outer(x):
    let y = await inner(x)
    return y + 1

show await outer(5)   # 11
```

## await as a general expression

`await` works anywhere an expression can appear, not just as a standalone statement:

```nekova
async task get_num():
    return 10

show await get_num() + 5      # 15

async task inner():
    return 1

async task outer():
    return await inner() + 1

show await outer()            # 2
```