<div align="center">

# NEKOVA Programming Language

### The AI-Native Programming Language by SYNEKCOT Tech

![Version](https://img.shields.io/badge/version-1.1.1-00d4ff)
![PyPI](https://img.shields.io/pypi/v/nekova-lang)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-147%20passing-success)

*"The first programming language where AI is syntax, not a library."*

[Install](#installation) · [Features](#features) · [Examples](#examples) · [Community](#community) · [Docs](#cli-commands)

</div>

---

## What is NEKOVA?

**NEKOVA** means *"Connected Forge"* — a language that forges a direct connection between the developer and AI. Built by **SYNEKCOT Tech** in Nigeria, for the world.

NEKOVA is an **AI-native programming language** built with Python. It's the first language where `think` is syntax — AI isn't a library you import, it's part of the language itself.

```nekova
# AI is just syntax
think "What should I build today?"

# Chain AI agents with ->
"Nigerian fintech trends" -> researcher -> analyst -> writer

# Neural pipeline
pipeline market_analysis:
    collect "African tech ecosystem"
    process with ai
    generate report
    save to database

run pipeline market_analysis
```

---

## Why NEKOVA?

> *"I didn't just learn to code. I built the tools other people use to code."*
> — Emmanuel King Christopher, Founder of SYNEKCOT Tech

NEKOVA was born in Nigeria and built to prove that world-class programming languages can come from anywhere. The name comes from two words: **NEKT** (connected, from Latin *nectere*) and **KOVA** (to forge). Together: the forge that connects human intent to AI.

---

## Installation

### Option 1 — pip (recommended)

```bash
pip install nekova-lang
```

Add your API key to a `.env` file in your project folder:

```env
# You only need ONE key — NEKOVA auto-detects which one you have
GEMINI_API_KEY=your_key_here       # Free key at aistudio.google.com
ANTHROPIC_API_KEY=your_key_here    # Key at console.anthropic.com
OPENAI_API_KEY=your_key_here       # Key at platform.openai.com
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
```

Run a program:
```bash
python main.py examples/hello.nk
```

---

## AI Providers

NEKOVA supports three AI providers out of the box. Just add the key for whichever one you have — NEKOVA picks it up automatically.

| Provider | Key | Get it free? |
|----------|-----|-------------|
| Google Gemini | `GEMINI_API_KEY` | ✅ Yes — [aistudio.google.com](https://aistudio.google.com) |
| Anthropic Claude | `ANTHROPIC_API_KEY` | No — [console.anthropic.com](https://console.anthropic.com) |
| OpenAI GPT | `OPENAI_API_KEY` | No — [platform.openai.com](https://platform.openai.com) |
| Mock (no key) | — | ✅ Always available |

Switch providers at runtime inside your `.nk` file:
```nekova
model "gemini"
think "Using Gemini now"

model "openai"
think "Using GPT now"

model "claude"
think "Using Claude now"
```

---

## Features

| Feature | Syntax | Description |
|---------|--------|-------------|
| 🧠 **Think** | `think "prompt"` | Call AI directly — no imports needed |
| 🔗 **Pipelines** | `researcher -> writer` | Chain AI agents with `->` |
| 🔀 **Model Routing** | `model "gemini"` | Switch AI providers at runtime |
| 👁️ **Vision** | `vision_scan("img.png")` | Analyze images with AI |
| 🎙️ **Voice** | `voice_speak("Hello!")` | Text-to-speech built in |
| ⚡ **Parallel** | `autonomous parallel:` | Run AI tasks simultaneously |
| 💾 **Memory** | `memory profile:` | Persistent data between runs |
| 🔒 **Sandbox** | `sandbox strict:` | Secure execution environment |
| 🧬 **Neural Pipeline** | `pipeline name:` | Full AI workflow in one block |
| 🏗️ **Compiler** | `nekova compile app.nk` | Compile to standalone Python |
| ☁️ **Deploy** | `nekova deploy cloud app.nk` | Deploy to cloud with one command |
| 🌐 **Web** | `use web` | Build real HTTP servers |
| 🗄️ **Database** | `use database` | Full SQLite CRUD |
| 🎨 **UI** | `use ui` | Generate HTML apps |

---

## Examples

### Hello World
```nekova
name = "Emmanuel"
show "Hello {name}!"
show "Welcome to NEKOVA — where AI is syntax."
```

### Think (AI as syntax)
```nekova
# Standalone think
think "What is the capital of Nigeria?"

# Captured think
idea = think "Give me one startup idea in one sentence"
show "AI said: {idea}"

# Think with variables
topic = "African fintech"
result = think "Analyze {topic} in 2025"
show result
```

### Agent Pipeline
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
result = run pipeline market_research
show result
```

### Parallel Execution
```nekova
# All three run simultaneously
autonomous parallel:
    think "Capital of Nigeria?"
    think "Capital of Ghana?"
    think "Capital of Kenya?"

# Captured results
results = autonomous parallel:
    think "Name one African unicorn"
    think "Name one Nigerian founder"
```

### Vision + Voice
```nekova
use vision
use voice

# Analyze an image
description = vision_scan("photo.png")
show "AI sees: {description}"

# Speak the result
voice_speak("Analysis complete!")

# Listen for input
transcript = voice_listen()
show "You said: {transcript}"
```

### Persistent Memory
```nekova
memory user_profile:
    name = "Emmanuel"
    language = "NEKOVA"
    run_count = 0

show user_profile["name"]
show user_profile["language"]
```

### Sandbox
```nekova
sandbox strict:
    show "Running in secure mode"
    think "What is 2 + 2?"

sandbox relaxed:
    use files
    data = read_file("input.txt")
    show data
```

### Variables, Loops & Tasks
```nekova
# Variables
name = "Emmanuel"
age  = 20
items = [1, 2, 3]

# Conditions
if age >= 18:
    show "Adult"
else:
    show "Minor"

# Loops
repeat 5:
    show "NEKOVA!"

for item in items:
    show item

# Tasks (functions)
task greet(name):
    show "Hello {name}!"
    return "Done"

result = greet("World")
show result
```

### Standard Library
```nekova
use math
use text
use database
use web

show sqrt(144)
show upper("hello nekova")

db_connect("myapp.db")
db_create("users", "name text, age integer")
db_insert("users", "Emmanuel, 20")
results = db_find("users", "all")
show results
```

---

## CLI Commands

```bash
# Run files
nekova hello.nk
nekova app.nk --debug

# Using python directly
python main.py hello.nk
python main.py repl
python main.py ide

# Developer tools
nekova repl                     # Interactive shell
nekova ide                      # Web IDE at localhost:3000
nekova compile app.nk           # Compile to Python
nekova deploy cloud app.nk      # Deploy to cloud
nekova --version                # Show version
nekova --help                   # Show help

# Package manager
nekova --install charts
nekova --packages
nekova marketplace
```

---

## Standard Library

| Module | Key Functions |
|--------|--------------|
| `use math` | sqrt, floor, ceil, abs, pi |
| `use text` | upper, lower, trim, replace, split |
| `use files` | read_file, write_file, file_exists |
| `use datetime` | today, now, year, month, day |
| `use ai` | ai_ask, ai_summarize, ai_generate |
| `use vision` | vision_scan, vision_compare |
| `use voice` | voice_speak, voice_listen, voice_save |
| `use agents` | agent_create, agent_run |
| `use web` | web_app, web_route, web_start |
| `use database` | db_connect, db_create, db_insert, db_find |
| `use ui` | ui_app, ui_page, ui_title, ui_button |

---

## Project Structure

```
nekova/
├── main.py              ← Entry point
├── runner.py            ← Pipeline orchestrator
├── config.py            ← Version & constants
├── repl.py              ← Interactive shell
├── nekova_cli.py        ← pip CLI entry point
├── lexer/               ← Tokenizer
├── parser/              ← AST builder
├── interpreter/         ← Execution engine
├── compiler/            ← Bytecode compiler + VM
├── stdlib/              ← Standard library
├── ai/                  ← AI runtime + providers
├── web/                 ← Web framework
├── database/            ← Database system
├── ui/                  ← UI framework
├── web_ide/             ← Browser-based IDE
├── deploy/              ← Deployment tools
├── examples/            ← Example programs (.nk)
└── tests/               ← Test suite (147 tests)
```

---

## Community

**NEKOVA Connect** — Share your NEKOVA projects with the community.

- Browse projects built with NEKOVA
- Share your own programs
- Chat with other developers
- Run projects live in the browser

---

## Roadmap

- [x] Core language (lexer, parser, interpreter)
- [x] Standard library (math, text, files, datetime)
- [x] AI runtime (Gemini, Claude, OpenAI, Mock)
- [x] `think` keyword — AI as syntax
- [x] Agent pipelines (`->` operator)
- [x] Model routing (`model "gemini"`)
- [x] Multimodal (vision + voice)
- [x] Parallel execution (`autonomous parallel`)
- [x] Persistent memory blocks
- [x] Sandboxing (`sandbox strict/relaxed`)
- [x] Neural pipelines (`pipeline name:`)
- [x] Bytecode compiler + VM
- [x] Cloud deployment
- [x] Web IDE
- [x] VS Code extension
- [x] PyPI package (`nekova-lang`)
- [x] OpenAI/GPT provider
- [ ] NEKOVA native compilation
- [ ] Language server (LSP)
- [ ] NEKOVA package registry
- [ ] NEKOVA Connect community platform

---

## Built By

**Emmanuel King Christopher** — Founder, SYNEKCOT Tech. Built from scratch with Python 3.11, in Nigeria.

> *"I didn't just learn to code. I built the tools other people use to code."*

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**Star ⭐ this repo if NEKOVA inspired you!**

[github.com/kinghenesey/NEKOVA](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech 🇳🇬

</div>