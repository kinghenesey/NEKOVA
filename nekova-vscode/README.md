# NEKOVA VS Code Extension — v1.9.1

Syntax highlighting, snippets, and commands for the **NEKOVA AI-Native Programming Language**.

Built by [SYNEKCOT Tech](https://github.com/kinghenesey/NEKOVA) 🇳🇬

---

## Features

- **Syntax highlighting** for all NEKOVA keywords — `think`, `remember`, `recall`, `route`, `serve`, `connect`, `object`, `class`, `match`, `yield`, `error`, `shape`, `every`, `test`, `expect`, `imagine`, `speak`, `listen`, `watch`, `sandbox`, and more
- **59 snippets** — type `think`, `task`, `route`, `obj`, `class`, `match`, `pipeline`, `parallel`, `sandbox`, `taskgen`, `decorator`, `shape`, `every`, `test`, and more
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
| `assert` | Assert statement |
| `raise` | Raise an error |
| `ternary` | Inline ternary expression |
| `tcf` | Try / catch / finally |
| `speak` | Text-to-speech output |
| `listen` | Speech-to-text input |
| `every` | Scheduled repeated execution |
| `test` | Built-in test block with expect |
| `expect` | Assertion inside a test block |
| `imagine` | AI image generation |
| `shape` | Data schema / validated struct |
| `watch` | File watcher |
| `taskgen` | Generator task with yield |
| `decorator` | Decorator applied to a task |
| `error` | Custom error type definition |
| `taskt` | Typed task with return type |
| `class` | Class definition (alias for object) |
| `usemath` / `usestring` / `usefile` / `usedate` | Import NEKOVA stdlib modules |
| `sandboxs` / `sandboxr` | Strict / relaxed sandbox block |
| `sandboxrun` | Run NEKOVA code in a sandbox programmatically |

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

# Speak and listen — built in
speak "Hello, world!"
let answer = listen "What city are you in?"

# Classes with inheritance
class Animal:
    name: str
    init(name: str):
        self.name = name
    func speak():
        return self.name + " says hello"

let a = new Animal("Lion")
show a.speak()

# Generators
task count(n: int):
    let i = 0
    while i < n:
        yield i
        let i = i + 1

for x in count(5):
    show x

# Built-in test runner
test "math works":
    expect 1 + 1 == 2

# Sandbox — safe execution
sandbox strict:
    show 2 + 2
show sandbox_result["safe"]

# Standard library written in NEKOVA
use math
show clamp(15, 0, 10)
show factorial(10)

# Pattern matching with ranges
match status:
    when "ok":    show "All good"
    when "error": show "Something failed"
    else:         show "Unknown"
```

---

## Release Notes

### 1.9.1
- Grammar updated for Phases 15–19: `yield`, `class`, `error`, `shape`, `every`, `test`/`expect`, `imagine`, `speak`/`listen`, `watch`, `sandbox`/`strict`/`relaxed`
- Decorator syntax (`@`) and return type hints (`->`) highlighted
- Floor division (`//`) and range operator (`..`) added to operator highlighting
- Hex (`0xFF`), scientific (`1e5`), and underscore (`1_000`) number literals highlighted correctly
- 24 new snippets — generators, decorators, error types, typed tasks, classes, sandbox blocks, stdlib imports
- 59 total snippets (up from 35)

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

[GitHub](https://github.com/kinghenesey/NEKOVA) · [PyPI](https://pypi.org/project/nekova-lang/) · [License](https://github.com/kinghenesey/NEKOVA/blob/main/LICENSE) · Built by SYNEKCOT Tech

Licensed under the [Business Source License 1.1](https://github.com/kinghenesey/NEKOVA/blob/main/LICENSE) — free for personal use, learning, internal tools, and any product *written in* NEKOVA, with no revenue cap. See the [Licensing FAQ](https://github.com/kinghenesey/NEKOVA/blob/main/LICENSE-FAQ.md) for details.