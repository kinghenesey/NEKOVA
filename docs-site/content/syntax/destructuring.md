---
title: Destructuring
lede: Pull values out of lists, tuples, and dicts in one line — three related forms, one underlying idea.
---

## List destructuring

```nekova
let scores = [10, 20, 30]
let [first, second] = scores
show first    # 10
show second   # 20
```

Extra trailing items beyond your named targets are simply ignored. If there aren't *enough* items to fill your named targets, NEKOVA raises rather than leaving some as `null`.

## Rest capture

```nekova
let [first, ...rest] = [1, 2, 3, 4]
show first   # 1
show rest    # [2, 3, 4]
```

`...rest` must be the last element in the pattern, and it always captures a list — even if it ends up empty.

## Tuple-style destructuring

Parentheses work exactly the same way as brackets:

```nekova
let pair = [1, 2]
let (a, b) = pair
show a   # 1
show b   # 2
```

This is also how you capture multiple return values from a task or builtin:

```nekova
let (quotient, remainder) = divmod(10, 3)
show quotient    # 3
show remainder   # 1
```

## Dict destructuring

```nekova
let user = {"name": "Ada", "age": 30}
let {name, age} = user
show name   # "Ada"
show age    # 30
```

Each name inside `{}` is both the key read from the dict and the variable it's bound to. A missing key raises immediately, listing which keys were actually available.

## Where it's useful

Destructuring a task's return value is the most common pattern:

```nekova
task get_bounds(numbers):
    return [min(numbers), max(numbers)]

let [low, high] = get_bounds([4, 8, 1, 9, 3])
show low    # 1
show high   # 9
```