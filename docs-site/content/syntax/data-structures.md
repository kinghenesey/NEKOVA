---
title: Data Structures
lede: Lists, dicts, and sets, plus the spread syntax that combines them without a loop.
---

## Lists

```nekova
let items = [1, 2, "three", true]
show items[0]
show len(items)
```

## Dicts

```nekova
let user = {"name": "Ada", "age": 30}
show user["name"]

let no_user = null
show no_user?.email     # null — see Optional Chaining
```

## Sets

```nekova
let a = {1, 2, 3}
show a          # {1, 2, 3}

let dupes = {1, 2, 2, 3, 1}
show dupes      # {1, 2, 3} — duplicates collapse automatically
```

`{}` on its own is still an empty **dict**, not a set — that convention doesn't change. NEKOVA tells dicts and sets apart by shape: a dict entry always looks like `key: value`, a set element never does.

```nekova
let empty_dict = {}
let a_set = {1, 2, 3}
```

### Set operations

```nekova
let a = {1, 2, 3}
let b = {2, 3, 4}

show set_union(a, b)          # {1, 2, 3, 4}
show set_intersection(a, b)   # {2, 3}
show set_difference(a, b)     # {1}
```

Putting a list or dict inside a set raises a clear error — sets need every element to be checkable for uniqueness, and lists/dicts can't be.

## Spread syntax

Expand one list or dict into another, without writing a loop:

```nekova
let a = [1, 2]
let b = [3, 4]
show [...a, ...b]          # [1, 2, 3, 4]
show [0, ...a, 99]         # [0, 1, 2, 99]
```

```nekova
let defaults = {"theme": "dark", "retries": 3}
let overrides = {"retries": 5}
show {...defaults, ...overrides}   # {theme: dark, retries: 5}
```

When keys collide, whichever spread comes later wins — the same rule as if you'd written the keys out by hand in that order.

## Enums

```nekova
enum Status: PENDING, ACTIVE, DONE

let s = Status.ACTIVE
show s   # "ACTIVE"

task describe(status):
    if status == Status.DONE:
        return "finished"
    return "not finished"
```

Each enum member evaluates to its own name as a string, so comparisons against string literals work naturally.