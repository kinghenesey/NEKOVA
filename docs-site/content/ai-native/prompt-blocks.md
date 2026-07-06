---
title: Prompt Blocks
lede: Reusable, parameterized prompt templates — defined once, called like any other task.
---

## Defining a prompt

```nekova
prompt summarize(text, style="professional"):
    """Summarize this in a {style} tone: {text}"""

let result = summarize("the quick brown fox")
show result
```

A `prompt` block's triple-quoted body is a template — `{style}` and `{text}` are filled in from the arguments, the same way an f-string works.

## What it returns

Calling a `prompt` returns the **interpolated template string itself** — it doesn't call an AI provider on its own. That makes it composable with `think`:

```nekova
prompt summarize(text):
    """Summarize this in one sentence: {text}"""

task get_summary(document):
    return think summarize(document)
```

This separation is deliberate: the prompt's wording lives in one place, versioned and reusable, while `think` stays the single place that actually talks to a model.

## Default parameter values

```nekova
prompt summarize(text, style="professional"):
    """Summarize this in a {style} tone: {text}"""

show summarize("hello world")                    # uses "professional"
show summarize("hello world", style="casual")    # overrides it
```