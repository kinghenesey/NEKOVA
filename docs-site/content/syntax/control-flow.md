---
title: Control Flow
lede: if/elif/else, loops, and pattern matching — the branching and repetition NEKOVA gives you.
---

## if / elif / else

```nekova
task classify(n):
    if n > 0:
        return "positive"
    elif n < 0:
        return "negative"
    else:
        return "zero"
```

## Inline ternary

```nekova
let label = "adult" if age >= 18 else "minor"
```

## while

```nekova
let n = 5
while n > 0:
    show n
    n = n - 1
```

## for … in

```nekova
for item in [1, 2, 3]:
    show item

for i in range(5):
    show i

for key in {"a": 1, "b": 2}:
    show key
```

## repeat

```nekova
repeat 3:
    show "hi"
```

## break and continue

```nekova
for n in range(10):
    if n == 3:
        continue
    if n == 7:
        break
    show n
```

## in / not in

```nekova
show 3 in [1, 2, 3]        # true
show "xyz" not in "hello"  # true
```

## match

Pattern matching against a value, with exhaustiveness checking:

```nekova
task describe(status):
    match status:
        when "pending":
            return "waiting to start"
        when "active":
            return "in progress"
        when "done":
            return "finished"
        else:
            return "unknown status"
```

Ranges work as match arms too:

```nekova
match score:
    when 90..100:
        show "A"
    when 80..89:
        show "B"
    else:
        show "C or below"
```

If a `match` block doesn't cover every case NEKOVA can statically reason about, the checker emits warning **W009** rather than staying silent about it.