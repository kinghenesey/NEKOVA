---
title: Enums
lede: A first-class enum type, where each member is its own name as a string.
---

## Defining an enum

```nekova
enum Status: PENDING, ACTIVE, DONE

show Status.ACTIVE   # "ACTIVE"
```

## Comparing against enum members

```nekova
enum Status: PENDING, ACTIVE, DONE

let s = Status.ACTIVE
if s == "ACTIVE":
    show "is active"
```

Because each member evaluates to its own name as a string, comparisons against string literals work naturally — you don't need a separate `.value` accessor.

## Using enums in logic

```nekova
enum Status: PENDING, ACTIVE, DONE

task describe(status):
    if status == Status.DONE:
        return "finished"
    return "not finished"

show describe(Status.DONE)      # "finished"
show describe(Status.PENDING)   # "not finished"
```

## Using enums as default parameter values

```nekova
enum Priority: LOW, MEDIUM, HIGH

task create_ticket(title, priority=Priority.MEDIUM):
    return {"title": title, "priority": priority}

let t = create_ticket("Fix login bug", priority=Priority.HIGH)
show t
```