---
title: Quickstart
lede: A five-minute tour through the parts of NEKOVA you'll use every day.
---

## Variables

```nekova
let name = "Ada"
let age = 30
const MAX_RETRIES = 3
```

`let` declares a variable you can reassign later. `const` declares a binding that can never be reassigned — attempting to will raise an error at the point of reassignment, not silently succeed.

## Tasks (functions)

NEKOVA calls functions **tasks**:

```nekova
task greet(name, greeting="Hello"):
    return greeting + ", " + name

show greet("Ada")
show greet("Ada", greeting="Hey")
```

Default parameter values and keyword arguments both work exactly as shown above.

## Control flow

```nekova
task classify(n):
    if n > 0:
        return "positive"
    elif n < 0:
        return "negative"
    else:
        return "zero"

for item in [1, -2, 0]:
    show classify(item)
```

## think — AI as a keyword

```nekova
let summary = think "Summarize the plot of Romeo and Juliet in one sentence"
show summary
```

`think` calls the configured AI provider (the mock provider by default — see [Installation](installation.html)) and returns the response directly, no client object required.

## Classes

```nekova
object Person:
    init(name, age):
        self.name = name
        self.age = age

    func greet():
        return "Hi, I'm " + self.name

let p = new Person("Ada", 30)
show p.greet()
```

## Error handling

```nekova
try:
    let x = 10 / 0
catch e:
    show "Something went wrong: " + e
```

## What's next

- [Core Syntax](../syntax/variables.html) covers the language in depth
- [AI-Native Features](../ai-native/think.html) covers `think`, `remember`, `prompt` blocks, and testing AI code deterministically
- [Reference → CLI Commands](../reference/cli-commands.html) covers everything the `nekova` command can do