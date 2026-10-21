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

## Resource limits

`sandbox strict:` controls *which operations* a snippet may use. It does not cap how much CPU or memory the snippet consumes, because the block runs inside your own program. When you need hard limits, run the code through `sandbox_run()`, the CLI, or `run_sandboxed()` from Python. Each of those runs it in a separate worker process that is killed the moment it goes over a limit.

```
nekova run app.nk --sandbox --max-memory 128 --max-cpu 5 --max-time 10
```

| Flag | What it limits | Default |
|------|----------------|---------|
| `--max-memory <MB>` | Memory the program may use on top of the interpreter's own footprint (minimum 16) | 256 |
| `--max-cpu <seconds>` | CPU time the program may use | 10 |
| `--max-time <seconds>` | Wall-clock time | 10 |

The same limits are available as keyword arguments to `sandbox_run()`:

```nekova
let r = sandbox_run("show 6 * 7", "strict", max_memory_mb=64, max_time=5)
show r["output"]
```

And from Python:

```python
from nekova.sandbox import run_sandboxed

result = run_sandboxed(source, limits={"max_memory_mb": 128, "max_cpu_seconds": 5})
print(result.error, result.enforced_by)
```

A program that goes over a limit is stopped and the result reports a `memory_limit`, `cpu_limit` or `timeout` violation. Unknown limit names are an error, so a typo can't silently leave a run unlimited.

`result.enforced_by` says how the limits were enforced:

| Value | Meaning |
|-------|---------|
| `job-object` | Windows Job Object. Enforced by the operating system. |
| `rlimit` | Linux `setrlimit`. Enforced by the operating system. |
| `watchdog` | A polling thread kills the worker. Best-effort: memory can spike between checks. |
| `wall-clock` | Only the time limit applied. |

A few details worth knowing. The CPU limit is rounded up to a whole second on Linux, and Windows checks it periodically, so a program can overshoot slightly. Every run starts a fresh worker process, which adds a fraction of a second of startup (about 0.3 s on Linux), and a program that asks for input gets an immediate end-of-input error rather than waiting on your terminal.

## Where this is useful

The sandbox is the mechanism behind running AI-generated code, user-submitted snippets, or anything else you don't fully trust yet, without giving it access to the filesystem or network by default. For code you genuinely don't trust, combine it with the resource limits above, since a block alone can't stop a runaway loop from using all your memory.