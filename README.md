<div align="center">

# NEKOVA Programming Language

### The AI-Native Programming Language by SYNEKCOT Tech

![Version](https://img.shields.io/badge/version-1.3.0-C41E0E?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/nekova-lang?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Tests](https://img.shields.io/badge/tests-744%20passing-success?style=flat-square)

*"The first programming language where AI is syntax, not a library."*

[Install](#installation) · [Features](#features) · [Examples](#examples) · [CLI Reference](#cli-reference) · [Roadmap](#roadmap)

</div>

---

## What is NEKOVA?

**NEKOVA** means *"Connected Forge"* — from Latin *nectere* (to connect) and *kova* (to forge). Built by **SYNEKCOT Tech** in Nigeria, for the world.

NEKOVA is an **AI-native programming language** where `think` is syntax. AI isn't a library you import — it's part of the language itself. In one file you can write web routes, query a database, call an AI model, and define a class — with no boilerplate.

```nekova
# AI is just syntax
think "What should I build today?" as text

# Remember context across calls
remember "user" as "Emmanuel"
recall "user"

# Chain AI agents with ->
"Nigerian fintech trends" -> researcher -> analyst -> writer

# Full web server
route GET "/":
    think "Write a welcome message" as text

serve port: 8080
```

---

## Why NEKOVA?

> *"I didn't just learn to code. I built the tools other people use to code."*
> — Emmanuel King Christopher, Founder of SYNEKCOT Tech

NEKOVA was born in Nigeria to prove that world-class programming languages can come from anywhere. 744 tests. 12 development phases. One language.

---

## Installation

### Option 1 — pip (recommended)

```bash
pip install nekova-lang
```

Add your AI key to a `.env` file in your project:

```env
# You only need ONE key — NEKOVA auto-detects it
GEMINI_API_KEY=your_key_here        # Free — aistudio.google.com
ANTHROPIC_API_KEY=your_key_here     # console.anthropic.com
OPENAI_API_KEY=your_key_here        # platform.openai.com
```

Run your first program:

```bash
nekova hello.nk
```

### Option 2 — Clone from GitHub

```bash
git clone https://github.com/kinghenesey/NEKOVA.git
cd NEKOVA
pip install -r requirements.txt
python main.py examples/hello.nk
```

---

## AI Providers

| Provider | Environment Variable | Free? |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | ✅ [aistudio.google.com](https://aistudio.google.com) |
| Anthropic Claude | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| OpenAI GPT | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| Mock (no key) | — | ✅ Always available |

Switch providers at runtime:

```nekova
model "gemini"
think "Using Gemini" as text

model "claude"
think "Using Claude" as text

model "openai"
think "Using GPT" as text
```

---

## Features

| Feature | Syntax | Description |
|---|---|---|
| 🧠 **Think** | `think "prompt" as json` | AI call — returns text, json, list, bool, or schema |
| 💾 **Memory** | `remember / recall / forget` | Session memory built into the language |
| 🔗 **Agent Pipelines** | `researcher -> analyst -> writer` | Chain AI agents with `->` |
| 🔀 **Model Routing** | `model "gemini"` | Switch providers at runtime |
| 🌐 **Web DSL** | `route GET "/" ... serve port: 8080` | HTTP server with zero boilerplate |
| 🗄️ **Database DSL** | `connect / query / insert / create` | SQLite built in |
| 🏗️ **Class System** | `object / init / self / extends` | Full OOP with inheritance |
| 🔀 **Pattern Matching** | `match / when` | Rust-style exhaustive matching |
| 📦 **Package System** | `nekova install <pkg>` | 11 built-in packages |
| 📚 **Stdlib** | `use json / env / uuid / crypto` | Standard modules via `use` |
| ⚡ **Async / Await** | `async task / await` | First-class async support |
| ⚡ **Parallel** | `autonomous parallel:` | Run tasks simultaneously |
| 🔒 **Sandbox** | `sandbox strict:` | Secure execution environment |
| 🧬 **Neural Pipeline** | `pipeline name:` | Full AI workflow in one block |
| 🏗️ **Compiler** | `nekova compile app.nk` | Compile to standalone Python |
| ☁️ **Deploy** | `nekova deploy cloud app.nk` | One-command cloud deploy |
| 🎨 **Templates** | `nekova new app --template web` | Scaffold web / ai / fullstack projects |
| 👁️ **Auto-rerun** | `nekova run --watch` | Re-run on every file save |
| 🖥️ **REPL** | `nekova repl` | Interactive shell with history |

---

## Examples

### Hello World

```nekova
name = "Emmanuel"
show "Hello {name}!"
show "Welcome to NEKOVA — where AI is syntax."
```

### AI as Syntax

```nekova
# Text response
think "What is the capital of Nigeria?" as text

# Captured result
idea = think "Give me one startup idea in one sentence" as text
show idea

# Structured JSON
data = think "Return a JSON object with name and country" as json
show data["name"]

# List response
ideas = think "List 3 African tech trends" as list
for item in ideas:
    show item

# Memory
remember "language" as "NEKOVA"
recall "language"
forget "language"
```

### Web Server

```nekova
route GET "/":
    return "Welcome to NEKOVA!"

route GET "/health":
    return "OK"

route POST "/ai":
    think request.body as text

serve port: 8080
```

### Database

```nekova
let db = connect("myapp.db")
db.create("users", "name text, age integer")
db.insert("users", "Emmanuel, 20")
let rows = db.query("users")
show rows
```

### Class System

```nekova
object Animal:
    init(name, sound):
        self.name = name
        self.sound = sound

    task speak():
        show "{self.name} says {self.sound}!"

object Dog extends Animal:
    init(name):
        super("Dog", "Woof")
        self.name = name

let d = new Dog("Rex")
d.speak()
```

### Pattern Matching

```nekova
let status = "active"

match status:
    when "active":  show "User is active"
    when "banned":  show "User is banned"
    else:           show "Unknown status"
```

### Package System

```nekova
# Install a package
nekova install validation

# Use it
use validation
let ok = validate_email("user@example.com")
show ok
```

### Standard Library

```nekova
use json
use env
use uuid
use crypto

let id   = uuid()
let key  = env("API_KEY")
let hash = sha256("hello")
let obj  = json.parse('{"x": 1}')
show id
```

### Agent Pipelines

```nekova
# Chain agents — output flows left to right
"Analyze Nigerian tech ecosystem" -> researcher -> marketer -> reporter

# Captured result
report = "Future of AI in Africa" -> analyst -> writer
show report
```

### Neural Pipeline

```nekova
pipeline market_research:
    collect "Nigerian startup ecosystem 2025"
    process with ai
    generate report
    save to database

run pipeline market_research
```

### Parallel Execution

```nekova
autonomous parallel:
    think "Capital of Nigeria?" as text
    think "Capital of Ghana?" as text
    think "Capital of Kenya?" as text
```

### Async / Await

```nekova
async task fetch_data(url):
    let result = await http_get(url)
    return result

await fetch_data("https://api.example.com/data")
```

---

## CLI Reference

```bash
# Run files
nekova run app.nk
nekova run app.nk --debug
nekova run app.nk --watch       # Auto-rerun on save
nekova run                      # Uses entry from nekova.toml

# Project scaffolding
nekova new myapp                            # Blank project
nekova new myapp --template web             # Web server project
nekova new myapp --template ai              # AI-native project
nekova new myapp --template fullstack       # Web + AI + database

# Developer tools
nekova repl                     # Interactive shell (arrow-key history)
nekova build app.nk             # Validate without running
nekova fmt app.nk               # Format source
nekova fmt --check              # Dry-run formatting check
nekova check app.nk             # Static analysis
nekova test                     # Run test suite
nekova info                     # System info
nekova clean                    # Remove cache files

# Package manager
nekova install <package>        # Install a package
nekova uninstall <package>      # Uninstall a package
nekova search <query>           # Search packages
nekova info <package>           # Package details
nekova deps                     # Install from nekova.toml

# Deploy & compile
nekova compile app.nk           # Compile to Python
nekova deploy app.nk            # Full deploy pipeline
nekova deploy cloud app.nk      # Deploy to cloud
nekova export app.nk            # Export to HTML/script

# Other
nekova --version
nekova --help
```

### REPL Commands

```
help / ?help      Show help
vars / ?vars      Show all variables
history           Show last 10 commands
reset             Clear session
templates         List project templates
version           Show version
exit / quit / q   Exit
```

Arrow keys navigate history. `?<cmd>` is a shorthand for any command.

---

## Project Templates

| Template | Command | Includes |
|---|---|---|
| `default` | `nekova new myapp` | Blank starter project |
| `web` | `nekova new myapp --template web` | Routes, serve, API scaffold |
| `ai` | `nekova new myapp --template ai` | think, remember, recall, agent tasks |
| `fullstack` | `nekova new myapp --template fullstack` | Web + AI + SQLite database |

---

## Built-in Packages

Install any of these with `nekova install <name>`:

| Package | Description |
|---|---|
| `requests` | HTTP client |
| `validation` | Input validation (email, URL, schema) |
| `crypto` | Hashing, encryption, JWT |
| `charts` | ASCII + data charts |
| `ui` | HTML UI generation |
| `scheduler` | Cron-style task scheduler |
| `forms` | Form parsing and validation |
| `auth` | JWT authentication |
| `email` | Email sending |
| `storage` | File and object storage |
| `ml` | Simple ML utilities |

---

## Standard Library

| Module | Key Exports |
|---|---|
| `use json` | `json.parse`, `json.stringify` |
| `use env` | `env("KEY")` |
| `use uuid` | `uuid()` |
| `use crypto` | `sha256`, `md5`, `encrypt`, `decrypt` |
| `use math` | `sqrt`, `floor`, `ceil`, `abs`, `pi` |
| `use text` | `upper`, `lower`, `trim`, `replace`, `split` |

---

## nekova.toml

Every NEKOVA project is configured with `nekova.toml`:

```toml
[project]
name        = "myapp"
version     = "0.1.0"
description = "My NEKOVA project"
entry       = "src/main.nk"

[ai]
model   = "claude"      # claude | gemini | openai | mock
api_key = ""            # or set via .env

[dependencies]
packages = ["validation", "requests"]

[run]
strict_types = false
debug        = false
```

Run `nekova install` (no args) to install all packages listed in `[dependencies]`.

---

## Error Messages

NEKOVA produces Rust-style error output with source context, carets, error codes, and *did-you-mean* suggestions:

```
error[E005] undefined variable 'nme'
  --> app.nk:3:6
   |
 3 |   show nme
   |        ^^^ not found in this scope
   |
   = did you mean: name
```

Error codes: `E001`–`E011`, `W003`, `W005`, `W006`.

---

## Project Structure

```
NEKOVA/
├── main.py                   ← CLI entry point
├── runner.py                 ← File runner
├── repl.py                   ← Interactive shell
├── watcher.py                ← --watch auto-rerun
├── nekova.toml               ← Project config
├── CHANGELOG.md
├── nekova/
│   ├── config.py             ← Version & constants
│   ├── lexer/                ← Tokenizer
│   ├── parser/               ← AST builder
│   ├── interpreter/          ← Execution engine
│   │   ├── interpreter.py
│   │   ├── class_interpreter.py
│   │   └── environment.py
│   ├── ai/                   ← AI runtime
│   │   ├── think_engine.py
│   │   ├── memory_store.py
│   │   └── providers/        ← claude / gemini / openai / mock
│   ├── cli/
│   │   ├── commands.py
│   │   ├── templates.py      ← Project scaffolding
│   │   ├── package_manager.py
│   │   ├── formatter.py
│   │   └── checker.py
│   ├── stdlib/               ← use json/env/uuid/crypto
│   ├── packages/             ← 11 built-in packages
│   ├── database/             ← SQLite DSL
│   ├── compiler/             ← Bytecode compiler + VM
│   └── deploy/               ← Deploy pipeline
└── tests/                    ← 744 passing tests
```

---

## Roadmap

- [x] Core language — lexer, parser, interpreter
- [x] Standard library — json, env, uuid, crypto
- [x] AI runtime — Claude, Gemini, OpenAI, Mock
- [x] `think` keyword — AI as syntax (text, json, list, bool, schema)
- [x] `remember` / `recall` / `forget` — session memory
- [x] Agent pipelines — `->` operator
- [x] Model routing — `model "gemini"`
- [x] Web DSL — `route` / `serve`
- [x] Database DSL — `connect` / `query` / `insert`
- [x] Class system — `object` / `init` / `self` / `extends`
- [x] Pattern matching — `match` / `when`
- [x] Async / await
- [x] Parallel execution — `autonomous parallel`
- [x] Neural pipelines — `pipeline name:`
- [x] Sandbox — `sandbox strict / relaxed`
- [x] Rust-style errors with did-you-mean
- [x] Strict types + type registry
- [x] CLI args via `ArgsObject`
- [x] `nekova fmt` — formatter
- [x] `nekova check` — static analyser
- [x] Package system — 11 built-in packages
- [x] Bytecode compiler + VM
- [x] Cloud deployment
- [x] VS Code extension
- [x] PyPI package (`nekova-lang`)
- [x] Project templates — `--template web / ai / fullstack`
- [x] REPL improvements — history, `?help`, persistent `~/.nekova_history`
- [x] `nekova run --watch` — auto-rerun on save
- [ ] Native compilation
- [ ] Language Server Protocol (LSP)
- [ ] NEKOVA community platform

---

## Built By

**Emmanuel King Christopher** — Founder, SYNEKCOT Tech. Built from scratch in Nigeria.

> *"I didn't just learn to code. I built the tools other people use to code."*

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">

**Star ⭐ this repo if NEKOVA inspired you.**

[github.com/kinghenesey/NEKOVA](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech 🇳🇬

</div>