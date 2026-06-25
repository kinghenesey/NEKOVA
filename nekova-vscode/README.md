# NEKOVA VS Code Extension — v1.3.1

Syntax highlighting, snippets, and commands for the **NEKOVA AI-Native Programming Language**.

Built by [SYNEKCOT Tech](https://github.com/kinghenesey/NEKOVA) 🇳🇬

---

## Features

- **Syntax highlighting** for all NEKOVA keywords — `think`, `remember`, `recall`, `route`, `serve`, `connect`, `object`, `match`, and more
- **35 snippets** — type `think`, `task`, `route`, `obj`, `match`, `pipeline`, `parallel`, and more
- **Run file** — press `F5` to run the active `.nk` file
- **Watch mode** — press `Ctrl+F5` to run with `--watch` (auto-reruns on save)
- **Format file** — press `Shift+Alt+F` to run `nekova fmt`
- **Lint file** — right-click → NEKOVA: Check File
- **New project** — Command Palette → NEKOVA: New Project (choose template)
- **Open REPL** — Command Palette → NEKOVA: Open REPL
- **Status bar** — shows active AI provider, click to run

---

## Requirements

NEKOVA must be installed:

```bash
pip install nekova-lang
```

---

## Commands

| Command | Shortcut | Description |
|---|---|---|
| NEKOVA: Run File | `F5` | Run active `.nk` file |
| NEKOVA: Run with Watch | `Ctrl+F5` | Auto-rerun on save |
| NEKOVA: Open REPL | — | Interactive shell |
| NEKOVA: Format File | `Shift+Alt+F` | Run `nekova fmt` |
| NEKOVA: Check File | — | Run `nekova check` |
| NEKOVA: New Project | — | Scaffold project from template |

---

## Snippets

| Prefix | Inserts |
|---|---|
| `think` / `tk` | `think "..." as text` |
| `thinkj` | `think "..." as json` |
| `thinkl` | `think "..." as list` |
| `thinkcap` | Captured think result |
| `rem` | `remember "key" as "value"` |
| `rec` | `recall "key"` |
| `task` | Task definition |
| `atask` | Async task |
| `obj` | Object class |
| `objext` | Object with inheritance |
| `new` | New instance |
| `routeg` | GET route handler |
| `routep` | POST route handler |
| `serve` | Start web server |
| `dbcon` | DB connect |
| `dbcreate` | Create table |
| `dbins` | DB insert |
| `dbq` | DB query |
| `match` | Pattern matching |
| `pipeline` | Neural pipeline |
| `parallel` | Parallel AI execution |
| `sandbox` | Sandbox block |
| `agent` | Agent pipeline (`->`) |
| `if` / `ife` | If / if-else |
| `for` / `repeat` / `while` | Loops |
| `try` | Try/catch |
| `use` | Import stdlib module |
| `model` | Switch AI provider |
| `let` | Variable declaration |
| `fs` | F-string |
| `show` | Print output |
| `header` | File header |

---

## Settings

| Setting | Default | Description |
|---|---|---|
| `nekova.pythonPath` | `python` | Python interpreter path |
| `nekova.aiProvider` | `auto` | AI provider (auto/claude/gemini/openai/mock) |
| `nekova.formatOnSave` | `false` | Auto-format on save |
| `nekova.showStatusBar` | `true` | Show status bar item |

---

## NEKOVA Language

```nekova
# AI is just syntax
think "What should I build today?" as text

# Capture and use AI output
idea = think "Give me a startup idea" as json
show idea["name"]

# Remember context
remember "user" as "Emmanuel"
recall "user"

# Web server
route GET "/":
    return "Hello from NEKOVA!"

serve port: 8080

# Object system
object Animal:
    init(name):
        self.name = name
    task speak():
        show f"{self.name} says hello!"

let a = new Animal("Lion")
a.speak()

# Pattern matching
match status:
    when "ok":    show "All good"
    when "error": show "Something failed"
    else:         show "Unknown"
```

---

## Release Notes

### 1.3.0
- Added `nekova.runWatch` command (`Ctrl+F5`) — `--watch` mode
- Added `nekova.fmtFile` command (`Shift+Alt+F`) — format file
- Added `nekova.checkFile` command — static analysis
- Added `nekova.newProject` command — template picker (default/web/ai/fullstack)
- 35 snippets covering all NEKOVA features
- Grammar updated: `object`/`init`/`self`/`extends`/`super`, `match`/`when`, `route`/`serve`, `connect`/`query`, `remember`/`recall`/`forget`, `as text|json|list|bool|schema`, f-strings, async/await
- Status bar now shows active AI provider
- Welcome message on first install
- `nekova.toml` activates the extension

### 1.1.0
- Initial release with syntax highlighting and Run/REPL commands

---

[GitHub](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · Built by SYNEKCOT Tech