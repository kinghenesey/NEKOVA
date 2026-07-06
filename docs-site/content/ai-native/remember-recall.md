---
title: remember & recall
lede: Simple persistent key-value memory, built into the language rather than a database you have to wire up.
---

## remember

```nekova
remember "favorite_color" = "blue"
```

## recall

```nekova
remember "favorite_color" = "blue"
let c = recall "favorite_color"
show c   # "blue"
```

## Default values

```nekova
let c = recall "nonexistent_key" or "default_val"
show c   # "default_val"
```

`or <default>` only kicks in when the key was never remembered — it isn't a general boolean-or, it's specific to `recall`.

## Why this exists

Memory is scoped per-interpreter-run and designed for the common case in AI-native programs: carrying small facts between `think` calls — a user's name, a running total, the last few turns of a conversation — without reaching for a database or a file for something that small.

## Isolation between test runs

If you're using [`test` blocks](testing.html), memory is cleared between tests automatically, so one test's `remember` calls can't leak into another's.