# NEKOVA Programming Language

### The AI-Native Programming Language by SYNEKCOT Tech

![Version](https://img.shields.io/badge/version-1.13.0-C41E0E?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/nekova-lang?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-BUSL--1.1-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-1513%20passing-success?style=flat-square)
![Docs](https://img.shields.io/badge/docs-live-2ECC71?style=flat-square)

*"The first programming language where AI is syntax, not a library."*

[Install](#installation) · [Features](#features) · [Examples](#examples) · [CLI Reference](#cli-reference) · [Roadmap](#roadmap) · [📖 Full Documentation](https://kinghenesey.github.io/NEKOVA/)

---

## What is NEKOVA?

**NEKOVA** means *"Connected Forge"* — from Latin *nectere* (to connect) and *kova* (to forge). Built by **SYNEKCOT Tech** in Nigeria, for the world.

NEKOVA is an **AI-native programming language** where `think` is syntax. AI isn't a library you import — it's part of the language itself. In one file you can write web routes, query a database, call an AI model, run sandboxed code, and define a class — with no boilerplate.

```
# AI is just syntax
think "What should I build today?" as text

# Speak and listen — built in
speak "Hello, world!"
let command = listen "Say a command"

# Schedule tasks
every 5 s:
    think "Check for new emails" as text

# Run untrusted code safely
sandbox strict:
    let result = 1 + 1
    show result

show sandbox_result["safe"]
```

---

## Why NEKOVA?

> *"Because every other language makes you import AI as a library, and I believe if AI is the future of how we build software, it should be a keyword — not an afterthought."*
> — Emmanuel King Christopher, Founder of SYNEKCOT Tech and Sole Author of NEKOVA

NEKOVA was born in Nigeria to prove that world-class programming languages can come from anywhere. **1,513 tests. 26 phases shipped. One language.**

---

## Installation

### Option 1 — pip (recommended)

```
pip install nekova-lang
```

Add your AI key to a `.env` file in your project:

```
# You only need ONE key — NEKOVA auto-detects it
GEMINI_API_KEY=your_key_here        # Free — aistudio.google.com
ANTHROPIC_API_KEY=your_key_here     # console.anthropic.com
OPENAI_API_KEY=your_key_here        # platform.openai.com
```

Run your first program:

```
nekova hello.nk
```

### Option 2 — Clone from GitHub

```
git clone https://github.com/kinghenesey/NEKOVA.git
cd NEKOVA
pip install -e .
```

### VS Code Extension

Search **"NEKOVA"** in the VS Code Extension Marketplace, or install directly:

```
ext install SYNEKCOTTech.nekova
```

---

## Features

### Core Language

```
# Variables
let name = "Emmanuel"
let age  = 21

# Tasks (functions) with type hints
task add(a: int, b: int) -> int:
    return a + b

# Default parameters
task greet(name, greeting="Hello"):
    show greeting + " " + name

# Varargs
task total(*nums):
    return sum(nums)

# Generators
task count(n: int):
    let i = 0
    while i < n:
        yield i
        let i = i + 1

for x in count(5):
    show x
```

### Classes and Objects

```
class Animal:
    name: str
    init(name: str):
        self.name = name
    func speak():
        return self.name + " says hello"

class Dog extends Animal:
    func fetch():
        return self.name + " fetches!"

let d = new Dog("Rex")
show d.speak()
show d.fetch()
```

### Decorators

```
task log(fn):
    task wrapper(x):
        show "calling with " + str(x)
        return fn(x)
    return wrapper

@log
task double(n):
    return n * 2

show double(21)   # → calling with 21 \n 42
```

### Error Types

```
error NetworkError:
    message str
    code    int = 500

try:
    raise NetworkError("timeout", 408)
catch e:
    show e["message"]   # → timeout
    show e["code"]      # → 408
```

### Language Completeness II (Phase 24)

```
# Tuple-style destructuring — same semantics as the bracket form
let pair = (1, 2)
let (a, b) = pair
show a   # → 1
show b   # → 2

# "Multiple return values" for free
let (quotient, remainder) = divmod(10, 3)
show quotient    # → 3
show remainder   # → 1

# Rest capture works in either form
let (first, ...rest) = [1, 2, 3, 4]
show first   # → 1
show rest    # → [2, 3, 4]

# Named/keyword arguments — mixed positional+keyword, gap-filling
# with declared defaults
task greet(name, greeting = "Hello"):
    show greeting + ", " + name
greet(name="Sam", greeting="Hi")   # → Hi, Sam

# const — immutable once set; reassigning raises
const MAX_RETRIES = 5
show MAX_RETRIES   # → 5

# Spread syntax — lists and dicts, mixed spread+literal items
let combined = [...[1, 2], ...[3, 4]]
show combined       # → [1, 2, 3, 4]

let defaults  = {"color": "blue", "size": "M"}
let overrides = {"size": "L"}
show {...defaults, ...overrides}   # → {color: blue, size: L}

# Optional chaining — short-circuits to null instead of raising
let user = {"email": "a@b.com"}
show user?.email        # → a@b.com

let nothing = null
show nothing?.email     # → null   (no error)

# Enums — each member is its own name as a string
enum Status: PENDING, ACTIVE, DONE
show Status.ACTIVE                  # → ACTIVE
show Status.ACTIVE == "ACTIVE"      # → true

# Set type — disambiguated from a dict literal at parse time
let a = {1, 2, 3}
let b = {2, 3, 4}
show set_union(a, b)          # → {1, 2, 3, 4}
show set_intersection(a, b)   # → {2, 3}
show set_difference(a, b)     # → {1}
```

### AI — Built In

```
# Single line AI calls
think "Summarise this in 3 words" as text
think "Extract the names" as list
think "Is this positive?" as bool
think "Parse this data" as json

# Remember context across calls
remember "user" as "Emmanuel"
let name = recall "user"

# Streaming
stream think "Write a short story about Lagos" as text
```

### AI-Native Differentiators II (Phase 25)

```
# think "..." as <ShapeName> — builds an implicit schema from the
# shape's own fields; the response comes back type-coerced and
# tagged with the shape's name
shape User:
    name str
    age  int

let u = think "extract from: Ada, 30" as User
show u["name"]         # → mock_name (a real API key returns "Ada")
show u["age"]          # → 42 (a real API key returns 30)
show u["__shape__"]    # → User

# Cost/token tracking — raises if the estimated tokens exceed budget
let result = think "summarize this" with budget: 500
show ai_usage()    # → {calls: 2, tokens: 33} (running total so far)

# Explicit model selection
let selected = think "analyse this" using "claude-sonnet"

# converse: blocks — multi-turn dialogue with automatic context.
# Every think/listen inside automatically carries prior turns.
let topic = "pricing"
converse:
    think f"ask a clarifying question about {topic}"
    listen
    think "respond based on what they said"

# imagine "..." as file — cached on disk under
# .nekova_cache/imagine/, so repeated calls during a dev loop don't
# regenerate (or re-bill) the same image
let image = imagine "a futuristic Lagos skyline at sunset" as file
show image
```

### Prompt Blocks (Phase 21)

Named, composable, reusable prompts — call them like any other function:

```
prompt summarize(text, style="professional", max_sentences=3):
    """
    Summarize the following in a {style} tone.
    Use at most {max_sentences} sentences.
    Text: {text}
    """

let summary = think summarize(article, style="casual")
```

`prompt` is intentionally **not** a reserved word — it's only treated as a
definition when it looks like one (`prompt name(...):`), so existing code
using `prompt` as a plain variable keeps working unchanged.

### Retry and Fallback (Phase 21)

First-class resilience for AI and network calls, with configurable backoff:

```
retry 3 times with exponential backoff:
    let result = think "analyse this" as json
fallback:
    let result = {error: "unavailable"}
```

### Observability, Mock Testing, and Pipes (Phase 22)

```
# Tag and trace a block of execution
observe "pipeline run" with tags {user: user_id}:
    let summary = think summarize(document)

# Deterministic AI output in tests — no real API call, no ambiguity
# about whether a response is real or mocked
test "classifier":
    mock think as "sports"
    expect classify(text) == "sports"

# Pipe operator — chain transformations left to right
let result = data |> parse() |> filter() |> sort() |> take(10)
```

### Speak, Listen, Imagine

```
# Text-to-speech
speak "Your report is ready"

# Speech-to-text
let answer = listen "What city are you in?"

# AI image generation
let img = imagine "a futuristic Lagos skyline at sunset" as url
show img
```

### Scheduled Execution

```
# Run every 10 seconds, 5 times
every 10 s 5 times:
    show "checking..."

# Run forever in background
every 1 m:
    think "Any breaking news?" as text
```

### Built-in Test Runner

```
task add(a, b):
    return a + b

test "addition":
    expect add(1, 2) == 3
    expect add(0, 0) == 0
    expect add(-1, 1) == 0

test "strings":
    expect len("hello") == 5
    expect "hello"[0] == "h"

# Snapshot testing (Phase 26) — for AI outputs where writing out
# the exact expected value by hand isn't practical. First run saves
# a baseline; later runs compare against it and fail on drift.
test "AI summary shape":
    let summary = think "Summarize this in one word: excellent!" as text
    expect_snapshot(summary, "one_word_summary")
```

### Data Shapes

```
shape User:
    name  str
    age   int
    email str = "unknown"

let u = User("Emmanuel", 21)
show u["name"]      # → Emmanuel
show u["__shape__"] # → User
```

### Sandbox — Safe Execution

```
# Run untrusted code in isolation
sandbox strict:
    let x = 10 * 10
    show x              # prints 100

show sandbox_result["safe"]      # → true
show sandbox_result["duration"]  # → 0.001

# Programmatic sandbox API
let result = sandbox_run("show 42")
show result["output"]  # → 42
show result["safe"]    # → true
```

### Standard Library in NEKOVA

```
# Math — written in NEKOVA
use math
show pi                     # → 3.141592653589793
show clamp(15, 0, 10)       # → 10
show factorial(10)          # → 3628800
show lerp(0, 100, 0.5)      # → 50.0

# String — written in NEKOVA
use string
show repeat("ha", 3)        # → hahaha
show pad_left("5", 4)       # → "   5"
show is_palindrome("racecar") # → true

# File — written in NEKOVA
use file
write("data.txt", "hello")
let content = read("data.txt")
show line_count("data.txt")

# Date — written in NEKOVA
use date
show today()                # → 2026-06-30
show day_of_week(today())   # → Tuesday
show add_days(today(), 7)   # → 2026-07-07
```

### Pattern Matching

```
let status = 404

match status:
    when 200: show "OK"
    when 404: show "Not Found"
    when 500: show "Server Error"
```

### Web Routes

```
route GET "/":
    think "Write a welcome message" as text

route POST "/api/chat":
    let msg = request["body"]["message"]
    think msg as text

serve port: 8080
```

### Generators and Lazy Sequences

```
task fibonacci():
    let a = 0
    let b = 1
    while true:
        yield a
        let temp = b
        let b = a + b
        let a = temp

let count = 0
for n in fibonacci():
    show n
    let count = count + 1
    if count == 10:
        break
```

---

### Developer Experience (Phase 26)

A real Language Server Protocol implementation — `nekova lsp` — backs
the [VS Code extension](https://github.com/kinghenesey/NEKOVA/tree/main/nekova-vscode)
(and any other LSP-aware editor): live inline errors as you type,
hover docs that resolve to a task/class's actual signature and
docstring, and autocomplete for keywords, builtins, and everything
declared in the open file, including type-aware method suggestions
right after `obj.`.

```
# Preview formatting changes without writing them
nekova fmt app.nk --diff

# Name the exact internal check that raised an error
nekova run app.nk --why

# A committed, reproducible snapshot of resolved dependency versions
nekova lock
nekova lock --check       # detect drift, e.g. in CI
```

---

### Education Layer (Phase 26b)

NEKOVA's own origin story is helping classmates who were tripped up
learning Python — this is that idea built directly into the toolchain.

```
# A guided, interactive tutorial — checks your real code against
# the real interpreter, not a string match against your input
nekova learn

# Explain why a file errored, in plain language
nekova explain app.nk
nekova explain app.nk --no-ai    # skip the AI-generated addition

# Best-effort Python -> NEKOVA translation
nekova translate script.py

# Batch-grade a folder of student submissions against a reference
# solution.nk (or a plain expected.txt)
nekova classroom assignment/

# A keyword/builtin glossary — same lookup on the CLI and in the REPL
nekova help think
nekova> help task

# Strip error output down to plain sentences — no error code, no
# box-drawing header — for a beginner/classroom audience
nekova run app.nk --simple-errors
```

`nekova check` also gained two new proactive warnings: comparing
directly to a boolean literal (`if x == true:` instead of `if x:`),
and equality comparisons between floats, which can silently fail
due to rounding.

---

### AI-Native Differentiators III (Phase 26c)

Six features chosen specifically for being differentiators of "AI as a
first-class language citizen," not generic language features with an
AI label stuck on.

```nekova
# Typed AI output that's actually validated — a missing required
# field or wrong type triggers an automatic re-prompt naming the
# specific problem, not a silent None
shape User:
    name str
    age int

let u = think "Extract: Ada, age 30" as User

# Probabilistic testing — for behavior that isn't meaningfully
# pass/fail on a single run
test "classifies sentiment" repeat 10 times, expect at least 8 passes:
    let result = think "Is this positive?" as bool
    expect result == true

# Budgets in dollars, not just tokens
think "..." as text with budget: $0.01

# A model fallback chain as grammar, not app logic
think "..." using ["claude-sonnet", "gpt-4", "local-model"]

# Streaming, genuinely lazy — the loop body runs per chunk as it
# arrives, not after the whole response finishes
for chunk in think_stream("Tell me a story"):
    show chunk

# Capability-scoped agent sandboxing — this block may only call
# the named tasks, enforced by the interpreter
sandbox strict allow: [search_web, send_email]:
    search_web("nekova language")
```

```
# Deterministic AI-call replay — record real responses once,
# replay them in CI with no API key and no spend
nekova run agent.nk --record-ai calls.json
nekova run agent.nk --replay-ai calls.json
```

Building the fallback chain also surfaced and fixed a real gap: the
real providers (Anthropic, OpenAI, Gemini) were hardcoding their
default model and silently ignoring `using` entirely. They now
respect a per-call override.

---

### Self-Hosting Blockers (Phase 19b)

All five blockers for writing NEKOVA in NEKOVA are now fixed:

```
# 1. Dict subscript assignment
let tokens = {}
let tokens["IF"] = "keyword"
show tokens["IF"]   # → keyword

# 2. Hex literals
let mask = 0xFF
let color = 0xDEADBEEF

# 3. Scientific notation
let avogadro = 6.022e23
let epsilon  = 1e-9

# 4. Underscore separators
let million = 1_000_000
let pi_approx = 3.141_592

# 5. Range arms in match
let c = "k"
match c:
    when "a".."z": show "lowercase"
    when "A".."Z": show "uppercase"
    when "0".."9": show "digit"
```

---

## CLI Reference

```
# Run a file
nekova run app.nk

# Run in sandbox mode
nekova run app.nk --sandbox
nekova run app.nk --sandbox --sandbox-mode relaxed

# Watch for changes
nekova run app.nk --watch

# Start the REPL
nekova repl

# Format code
nekova fmt app.nk
nekova fmt app.nk --diff       # preview changes without writing them

# Check for errors
nekova check app.nk

# Create a new project
nekova new myproject
nekova new myproject --template web
nekova new myproject --template ai
nekova new myproject --template fullstack
nekova new                      # interactive wizard — prompts for
                                 # name, template, author, description

# Dependency lockfile
nekova lock                     # (re)generate nekova.lock
nekova lock --check             # verify it's in sync (for CI)

# Explain which internal check raised an error
nekova run app.nk --why

# Accept new AI-output snapshots as the baseline
nekova run app.nk --update-snapshots

# Language server (used by editor integrations, not typically run by hand)
nekova lsp

# Package management
nekova install requests
nekova uninstall requests
nekova search "http client"
```

---

## Language Reference

📖 **The full language reference — every keyword, every construct, with runnable examples — lives at [kinghenesey.github.io/NEKOVA](https://kinghenesey.github.io/NEKOVA/).** The tables below are a quick-glance summary, not the complete picture.

### Keywords

| Category     | Keywords                                                                                 |
| ------------ | ----------------------------------------------------------------------------------------- |
| Control flow | `if` `else` `elif` `while` `for` `in` `return` `break` `continue` `match` `when` `yield`   |
| Declarations | `task` `let` `const` `enum` `use` `import` `class` `object` `error` `shape`               |
| Exception    | `try` `catch` `finally` `raise` `assert` `pass`                                           |
| AI           | `think` `remember` `recall` `forget` `imagine` `speak` `listen` `converse` (Phase 25)     |
| Resilience   | `retry` `fallback` (Phase 21)                                                              |
| Scheduling   | `every`                                                                                    |
| Testing      | `test` `expect` `mock` (Phase 22)                                                          |
| Observability| `observe` (Phase 22)                                                                       |
| Watching     | `watch`                                                                                    |
| Sandbox      | `sandbox` `strict` `relaxed`                                                               |
| OOP          | `init` `self` `new` `extends` `func`                                                      |
| Async        | `async` `await` `stream`                                                                  |
| Logic        | `and` `or` `not` `is` `in` `not in` `is not`                                               |

`prompt` (Phase 21) is intentionally **not** a reserved word — it's recognized
contextually only when it looks like a definition (`prompt name(...):`), so
existing code using `prompt` as an ordinary variable name keeps working.
`using` and `budget` (Phase 25, inside a `think` clause) work the same way —
soft keywords, matched by value only where they're expected, plain
identifiers everywhere else.

### Operators

| Operator                    | Description      |
| ---------------------------- | ----------------- |
| `+` `-` `*` `/`               | Arithmetic        |
| `//`                          | Floor division     |
| `%` `**`                      | Modulo, power      |
| `==` `!=` `<` `>` `<=` `>=`   | Comparison         |
| `in` `not in`                 | Membership         |
| `is` `is not`                 | Identity           |
| `and` `or` `not`              | Logic              |
| `@`                            | Decorator          |
| `->`                           | Return type hint   |
| `\|>`                          | Pipe (Phase 22) — `data \|> parse() \|> sort()` |
| `?.`                           | Optional chaining (Phase 24) — `user?.email` |
| `...`                          | Spread (Phase 24) — `[...a, ...b]` — and rest capture in destructuring |
| `x if c else y`                | Ternary            |

---

## Project Structure

```
NEKOVA/
├── nekova/              ← Core package: lexer, parser, interpreter, AI runtime, stdlib (.nk + .py)
├── nekova-vscode/        ← VS Code extension source (published on the marketplace)
├── myproject/            ← Example / scaffold project generated by `nekova new`
├── tests/                ← Test suite (1,513 tests across 26 phases)
├── main.py                ← Entry point
├── runner.py              ← Pipeline orchestrator
├── nekova_cli.py          ← pip CLI entry point
├── repl.py                ← Interactive shell
├── debugger.py            ← Debugger
├── formatter.py           ← `nekova fmt`
├── pyproject.toml         ← Package metadata
└── website.html           ← Project landing page
```

---

## Roadmap

| Phase | Status | Description                                                                                |
| ----- | :----: | ------------------------------------------------------------------------------------------ |
| 1–14  | ✅     | Core language, AI, classes, web, packages                                                  |
| 15    | ✅     | Stability — `in`/`not in`, `//`, `range()`, slicing, builtins                              |
| 16    | ✅     | Standout features — `speak`, `listen`, `every`, `test`/`expect`, `imagine`, `shape`, `watch`|
| 17    | ✅     | Power user layer — generators, decorators, error types, typed tasks, `class` keyword        |
| 18    | ✅     | Standard library in NEKOVA — `math.nk`, `string.nk`, `file.nk`, `date.nk`                   |
| 19    | ✅     | NEKOVA Sandbox — isolated execution, resource limits, violation tracking                    |
| 19b   | ✅     | Security fixes — 38 bugs fixed, self-hosting blockers cleared                               |
| 20    | ✅     | **Self-hosting begins** — NEKOVA lexer written in NEKOVA (`nekova/stdlib/nk/lexer.nk`), verified token-for-token identical to the Python reference lexer, including on its own source |
| 21    | ✅     | `prompt` blocks, `retry`/`fallback` with backoff                                             |
| 22    | ✅     | `observe` telemetry, `mock think` in tests, `\|>` pipe operator                              |
| 23a   | ✅     | Correctness & Trust Part 1 — accurate recursion errors, labeled mock AI responses, type-mismatch errors, near-miss variable suggestions, semver policy |
| 23b   | ✅     | Correctness & Trust Part 2 — indentation-depth errors, full builtin-exception audit          |
| 24    | ✅     | Language completeness II — destructuring, keyword arguments, `const`, spread, optional chaining, enums, `Set` type |
| 24b   | ✅     | Documentation website — 28 pages at kinghenesey.github.io/NEKOVA                             |
| 25    | ✅     | AI-native differentiators II — cost/token tracking, `think as <Shape>`, `converse:` blocks, explicit model selection, `imagine as file` caching, sandbox prompt-injection guard |
| 26    | ✅     | **Developer experience** — Language Server Protocol (real inline errors, hover docs, autocomplete), `nekova fmt --diff`, multi-error parser recovery, interactive `nekova new` wizard, `nekova.lock`, `--why`, `expect_snapshot(...)` snapshot testing |
| 26b   | 🔜     | **Next** — Education layer: `nekova learn`, `nekova explain`, classroom mode                |
| 27    | 🔜     | NEKOVA parser in NEKOVA — v2.0 milestone                                                     |
| 31    | 🎯     | Full self-hosting — interpreter in NEKOVA — v3.0                                             |

**Long term:** NEKOVA Game Engine, WASM compilation.

---

## License

NEKOVA is licensed under the **Business Source License 1.1**: free to use, modify, and build on for personal projects, learning, and commercial products under $1M/year in revenue. The license converts automatically to Apache 2.0 four years after each release. See [`LICENSE`](LICENSE) for full terms, or the [Licensing FAQ](LICENSING_FAQ.md) for a plain-English explanation.

---

## Built By

**Emmanuel King Christopher** — Founder, SYNEKCOT Tech, Nigeria. Built from scratch in Python 3.11, starting October 2025.

> *"Because every other language makes you import AI as a library, and I believe if AI is the future of how we build software, it should be a keyword — not an afterthought."*

---

**Star ⭐ this repo if NEKOVA inspired you!**

[github.com/kinghenesey/NEKOVA](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech 🇳🇬