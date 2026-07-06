---
title: think
lede: The keyword that calls an AI model — no client, no SDK, no response object to unwrap.
---

## Basic usage

```nekova
let summary = think "Summarize the plot of Romeo and Juliet in one sentence"
show summary
```

`think` sends the prompt to the configured AI provider and returns the response directly.

## The mock provider

By default, NEKOVA uses a **mock provider** so you can write and test AI-flavored code without an API key. Every mock response is tagged `[MOCK]`, so it's never mistaken for a real model reply — this was a deliberate fix (see the [Changelog](../reference/changelog.html)) after early versions had some untagged mock branches.

## Output formats

`think` can ask for a specific shape back:

```nekova
let data = think "Extract fields from this text" as json
let items = think "List three colors" as list
let is_valid = think "Is this a valid email?" as bool
let count = think "How many legs does a spider have?" as number
```

## Structured schemas

```nekova
let user = think "Extract name and age from: Ada, 30" as schema {"name": "text", "age": "number"}
```

## Inline error handling

If the AI call fails, `when error:` lets you supply a fallback instead of embedding an error string in the result:

```nekova
let summary = think "summarize this document" when error: "unavailable"
```

Without the `when error:` clause, a failed call embeds `[think error: ...]` in the result rather than crashing the program — `when error:` exists for when you'd rather control that fallback yourself.

```nekova
let x = think "hi" as json when error: {"status": "down"}
```

## f-strings in prompts

```nekova
task summarize(document):
    return think f"Summarize this in one sentence: {document}"
```

## Timeouts

`think` calls run with a timeout under the hood, so a hung provider doesn't hang your whole program — see [async & await](async-await.html) for how NEKOVA handles this without you needing to manage an event loop yourself.