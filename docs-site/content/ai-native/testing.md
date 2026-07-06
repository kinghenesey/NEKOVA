---
title: Testing with mock & observe
lede: Test AI-flavored code deterministically, and trace what's actually happening when it runs.
---

## test / expect

```nekova
test "greet returns correct format":
    expect greet("Ada") == "Hello, Ada"
```

Run every test block in a project with:

```bash
nekova test
```

## mock think

Stub an AI response so a test doesn't depend on what a real (or even mock) provider happens to say:

```nekova
test "summary uses the right tone":
    mock think as "Hello there"
    let result = think "say hi"
    expect result == "Hello there"
```

`mock think as <value>` is scoped to the enclosing `test` block — it doesn't leak into other tests or into the rest of the program.

## observe

Structured tracing for debugging AI-native code — wrap any block to see what ran and how long it took:

```nekova
observe "pipeline run":
    let x = think "hello"
    show x
```

```
👁  pipeline run
🧠 [MOCK] Hello! I am NEKOVA's built-in AI assistant.
   └─ completed in 0.9ms
```

### Tagging an observe block

```nekova
observe "pipeline run" with tags {user: user_id}:
    let summary = think "summarize this"
```

Tags travel with the trace output, useful once you have more than one thing being observed in the same run.

## Why mock responses are tagged

Every mock AI response is prefixed `[MOCK]`, so output from `mock think` or the default mock provider can never be confused with a real model's reply — including in test output, where that distinction matters most.