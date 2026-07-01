<<<<<<< HEAD
﻿# NEKOVA Programming Language
=======
# NEKOVA Programming Language
>>>>>>> 3a2735c3b9411ed30379a256c69a30efe81d2b92

### The AI-Native Programming Language by SYNEKCOT Tech

![Version](https://img.shields.io/badge/version-1.9.2-C41E0E?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/nekova-lang?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-BUSL--1.1-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-1130%20passing-success?style=flat-square)

*"The first programming language where AI is syntax, not a library."*

[Install](#installation) · [Features](#features) · [Examples](#examples) · [CLI Reference](#cli-reference) · [Roadmap](#roadmap)

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

NEKOVA was born in Nigeria to prove that world-class programming languages can come from anywhere. **1,130 tests. 20 development phases. One language.**

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

# Check for errors
nekova check app.nk

# Create a new project
nekova new myproject
nekova new myproject --template web
nekova new myproject --template ai
nekova new myproject --template fullstack

# Package management
nekova install requests
nekova uninstall requests
nekova search "http client"
```

---

## Language Reference

### Keywords

| Category     | Keywords                                                                                 |
| ------------ | ----------------------------------------------------------------------------------------- |
| Control flow | `if` `else` `elif` `while` `for` `in` `return` `break` `continue` `match` `when` `yield`   |
| Declarations | `task` `let` `use` `import` `class` `object` `error` `shape`                              |
| Exception    | `try` `catch` `finally` `raise` `assert` `pass`                                           |
| AI           | `think` `remember` `recall` `forget` `imagine` `speak` `listen`                           |
| Scheduling   | `every`                                                                                    |
| Testing      | `test` `expect`                                                                            |
| Watching     | `watch`                                                                                    |
| Sandbox      | `sandbox` `strict` `relaxed`                                                               |
| OOP          | `init` `self` `new` `extends` `func`                                                      |
| Async        | `async` `await` `stream`                                                                  |
| Logic        | `and` `or` `not` `is` `in` `not in` `is not`                                               |

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
| `x if c else y`                | Ternary            |

---

## Project Structure

```
NEKOVA/
├── nekova/              ← Core package: lexer, parser, interpreter, AI runtime, stdlib (.nk + .py)
├── nekova-vscode/        ← VS Code extension source (published on the marketplace)
├── myproject/            ← Example / scaffold project generated by `nekova new`
├── tests/                ← Test suite (1,130 tests across 19 phases)
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
| 20    | 🔄     | **Self-hosting begins** — NEKOVA lexer written in NEKOVA (`nekova/stdlib/nk/lexer.nk`)       |
| 21    | 🔜     | `prompt` blocks, `retry`/`fallback`, enforced types                                          |
| 22    | 🔜     | `observe` telemetry, `mock think` in tests, `\|>` pipe operator                              |
| 23    | 🔜     | Polish — inline errors, destructuring, docstrings                                            |
| 24    | 🔜     | NEKOVA parser in NEKOVA — v2.0 milestone                                                     |
| 27    | 🎯     | Full self-hosting — interpreter in NEKOVA — v3.0                                             |

**Long term:** NEKOVA Game Engine, WASM compilation.

---

## License

NEKOVA is licensed under the **Business Source License 1.1**: free to use, modify, and build on for personal projects, learning, and commercial products under $1M/year in revenue. The license converts automatically to Apache 2.0 four years after each release. See [`LICENSE`](LICENSE) for full terms, or the [Licensing FAQ](LICENSING_FAQ.md) for a plain-English explanation.

---

## Built By

**Emmanuel King Christopher** — Founder, SYNEKCOT Tech. 21 years old, Nigeria. Built from scratch in Python 3.11, starting October 2025.

> *"Because every other language makes you import AI as a library, and I believe if AI is the future of how we build software, it should be a keyword — not an afterthought."*

---

**Star ⭐ this repo if NEKOVA inspired you!**

<<<<<<< HEAD
[github.com/kinghenesey/NEKOVA](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech 🇳🇬
=======
[github.com/kinghenesey/NEKOVA](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech 🇳🇬
>>>>>>> 3a2735c3b9411ed30379a256c69a30efe81d2b92
