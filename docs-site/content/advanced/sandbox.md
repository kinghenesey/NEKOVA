---
title: Sandbox
lede: Run untrusted or exploratory code with a restricted set of available operations.
---

## Basic usage

```nekova
sandbox strict:
    show 2 + 2
```

## strict vs relaxed

`strict` allows only a small, safe set of built-in names — ordinary computation, string/list/dict operations, and nothing that touches the filesystem, network, or Python's own `eval`/`exec`. `relaxed` is a superset of `strict` that additionally allows file reads.

```nekova
sandbox relaxed:
    let contents = file_read("data.txt")
    show contents
```

## What gets blocked

Names like `eval` and `exec` are blocked unconditionally in a sandbox, regardless of mode. A blocked attempt doesn't halt the whole program — it's recorded as a violation and reported when the sandbox block finishes:

```nekova
sandbox strict:
    eval("some code")
```
```
[sandbox:strict] Blocked:
  [sandbox:strict] Access to 'eval' is blocked.
  This operation is not permitted in any sandbox mode.
[sandbox:strict] ✗ violations detected (0.000s)
```

Every blocked attempt is recorded, which is what powers NEKOVA's sandbox violation reporting when you're auditing what an untrusted snippet tried to do.

## What still works

Ordinary variables, arithmetic, and the safe subset of built-ins all work exactly as outside a sandbox:

```nekova
sandbox strict:
    let x = 10
    let y = 20
    show x + y
```
```
30
[sandbox:strict] ✓ safe (0.000s)
```

## Where this is useful

The sandbox is the mechanism behind running AI-generated code, user-submitted snippets, or anything else you don't fully trust yet, without giving it access to the filesystem or network by default.