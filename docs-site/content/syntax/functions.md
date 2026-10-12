---
title: Functions & Tasks
lede: NEKOVA calls functions "tasks" — with default values, varargs, keyword arguments, and type hints all supported.
---

## Basic tasks

```nekova
task add(a, b):
    return a + b

show add(2, 3)
```

## Default parameter values

```nekova
task greet(name, greeting="Hello"):
    return greeting + ", " + name

show greet("Ada")               # "Hello, Ada"
show greet("Ada", "Hey")        # "Hey, Ada"
```

## Keyword arguments

```nekova
task greet(name, greeting="Hello"):
    return greeting + ", " + name

show greet(name="Ada", greeting="Hey")
show greet("Ada", greeting="Yo")   # positional + keyword mixed
```

Keyword arguments can fill in a later parameter while leaving an earlier one at its default:

```nekova
task greet(name="World", greeting="Hello"):
    return greeting + ", " + name

show greet(greeting="Hey")   # "Hey, World"
```

Passing an unknown keyword, or the same parameter both positionally and by keyword, raises a clear error rather than guessing what you meant.

## Variadic arguments

```nekova
task total(*nums):
    let sum = 0
    for n in nums:
        sum = sum + n
    return sum

show total(1, 2, 3, 4)
```

## Spreading arguments into a call

`*rest` collects extra arguments in a declaration. The mirror image, `...`, spreads a list or tuple back out into separate arguments at a call:

```nekova
task total(*nums):
    let sum = 0
    for n in nums:
        sum = sum + n
    return sum

let values = [1, 2, 3, 4]
show total(...values)
show total(10, ...values)
```

The thing being spread must be a list or tuple. It combines freely with ordinary positional arguments, as in `total(10, ...values)`.

This is what lets a wrapper forward whatever it was given, so one decorator can wrap a function of any arity:

```nekova
task total(*nums):
    let sum = 0
    for n in nums:
        sum = sum + n
    return sum

task logged(f):
    task wrapper(*args):
        show "calling with " + str(len(args)) + " args"
        return f(...args)
    return wrapper

let safe_total = logged(total)
show safe_total(5, 6)
show safe_total(1, 2, 3, 4)
```

`...` also spreads inside list and dictionary literals — `[...a, ...b]` — so it works the same way in all three places.

## Type hints and typed tasks

```nekova
task add(a: int, b: int) -> int:
    return a + b
```

Type hints on parameters and return values are checked at call time for `int`, `float`, `str`, `bool`, `list`, and `dict`.

## Docstrings

A leading string in a task body is captured as documentation rather than treated as a statement:

```nekova
task greet(name):
    """Says hello to someone."""
    show "Hello " + name

show doc(greet)   # "Says hello to someone."
```

## Recursion

```nekova
task factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

NEKOVA tracks its own call depth (500 by default) independently of Python's stack, so an unbounded recursive call reports the exact depth reached rather than a vague "infinite recursion" guess.

## Closures

Tasks capture variables from their enclosing scope by reading them, the same as any nested scope:

```nekova
task make_adder(x):
    task add(y):
        return x + y
    return add

let add5 = make_adder(5)
show add5(3)    # 8
show add5(10)   # 15
```

Each call to `make_adder` creates a fresh `x`, so `add5` and a second `make_adder(100)` don't interfere with each other.