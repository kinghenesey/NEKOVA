---
title: Pattern Matching
lede: match/when for branching on a value's shape or range, with exhaustiveness warnings.
---

## Basic matching

```nekova
task classify(x):
    match x:
        when 0:
            return "zero"
        when 1..10:
            return "small"
        else:
            return "large"

show classify(0)     # "zero"
show classify(5)     # "small"
show classify(100)   # "large"
```

## Matching on strings

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

## Ranges as match arms

```nekova
task grade(score):
    match score:
        when 90..100:
            return "A"
        when 80..89:
            return "B"
        when 70..79:
            return "C"
        else:
            return "F"
```

## Exhaustiveness

If NEKOVA can statically tell that a `match` block doesn't cover every case it reasonably could, the checker (`nekova check`) emits warning **W009** rather than staying silent. An `else` arm always satisfies exhaustiveness.