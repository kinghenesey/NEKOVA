# NEKOVA VS Code Extension — v1.11.0

Syntax highlighting, two branded color themes, snippets, and commands for the **NEKOVA AI-Native Programming Language**.

Built by [SYNEKCOT Tech](https://github.com/kinghenesey/NEKOVA) 🇳🇬

---

## Features

- **Syntax highlighting** for all NEKOVA keywords — `think`, `remember`, `recall`, `route`, `serve`, `connect`, `object`, `class`, `match`, `yield`, `error`, `shape`, `every`, `test`, `expect`, `imagine`, `speak`, `listen`, `watch`, `sandbox`, `prompt`, `retry`, `fallback`, `observe`, `mock`, `const`, `enum`, `converse`, and more — plus operators added in Phase 24: optional chaining (`?.`) and spread (`...`), correctly distinguished from the range operator (`..`), and Phase 25's `using`/`budget` soft keywords inside a `think` clause
- **A real language server (Phase 26)** — `nekova lsp` now backs this extension, replacing what was previously syntax-highlighting-only support: live inline errors as you type (from the real lexer/parser, not a separate approximation), hover docs that resolve to a task/class's actual signature and docstring when it's user-defined, and autocomplete for keywords, builtins, and everything declared in the open file — including type-aware method suggestions right after `obj.`. Toggle via the `nekova.enableLanguageServer` setting
- **`observe` blocks** and **`mock think`** highlighted and auto-indented correctly, plus the **`|>` pipe operator**
- **Two color themes — NEKOVA Dark and NEKOVA Light** — both built from NEKOVA's brand palette of green and white only. AI-native keywords (`think`, `speak`, `listen`, `imagine`, `watch`, `every`) are highlighted in the brightest green in both themes, since that's the language's whole identity. True red/amber are reserved exclusively for actual errors and warnings, so diagnostics stay visually distinct from ordinary syntax in either theme. NEKOVA Light uses a genuine pure-white (`#FFFFFF`) background, not a lightened grey. Select either via `Preferences: Color Theme → NEKOVA Dark` / `NEKOVA Light`
- **Branded `.nk` file icon** — a simplified "nk" mark on a small dark backing, designed to stay legible at actual file-icon size (16px), not just at logo size
- **`prompt` blocks** highlighted as a declaration (like `task`/`class`) only when genuinely defining a prompt — `prompt name(...):` — while still working correctly as an ordinary variable name elsewhere, matching NEKOVA's own soft-keyword design
- **82 snippets** — type `think`, `task`, `route`, `obj`, `class`, `match`, `pipeline`, `parallel`, `sandbox`, `taskgen`, `decorator`, `shape`, `every`, `test`, `prompt`, `retry`, `observe`, `mock`, `pipe`, `const`, `enum`, `lettuple`, `letlist`, `letdict`, `optchain`, `setlit`, `callkw`, `thinkerr`, `taskdoc`, `converse`, `thinkshape`, `thinkbudget`, `thinkmodel`, `imaginefile`, `aiusage`, `expectsnap`, and more
- **Run file** — press `F5` to run the active `.nk` file
- **Watch mode** — press `Ctrl+F5` to run with `--watch` (auto-reruns on save)
- **Format file** — press `Shift+Alt+F` to run `nekova fmt`
- **Lint file** — right-click → NEKOVA: Check File
- **Test file** — right-click → NEKOVA: Test File (runs the active file, including any `test`/`expect` blocks it contains)
- **Debug file** — right-click → NEKOVA: Debug File
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
| NEKOVA: Test File | — | Run active file (executes `test`/`expect` blocks) |
| NEKOVA: Debug File | — | Run `nekova debug` on the active file |
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
| `prompt` / `promptdef` | Named prompt block definition |
| `retry` | Retry block with backoff and `fallback:` clause |
| `retrys` | Retry block with no backoff or fallback |
| `observe` | Tag and trace a block of execution |
| `mock` | Stub `think` inside a test block |
| `pipe` | Chain transformations with `\|>` |
| `expectsnap` | Snapshot assertion inside a test block (Phase 26) |

---

## Settings

| Setting | Default | Description |
|---|---|---|
| `nekova.pythonPath` | `python` | Python interpreter path |
| `nekova.aiProvider` | `auto` | AI provider (auto/claude/gemini/openai/mock) |
| `nekova.formatOnSave` | `false` | Auto-format on save |
| `nekova.showStatusBar` | `true` | Show status bar item |
| `nekova.enableLanguageServer` | `true` | Enable real inline errors, hover docs, and autocomplete (Phase 26) — requires reloading the window to take effect |

---

## NEKOVA Language

```nekova
# AI is just syntax
think "What should I build today?" as text

# Speak and listen — built in
speak "Hello, world!"
let answer = listen "What city are you in?"

# Named, composable prompts
prompt summarize(text, style="professional", max_sentences=3):
    """
    Summarize the following in a {style} tone.
    Use at most {max_sentences} sentences.
    Text: {text}
    """

let summary = think summarize(article, style="casual")

# Resilience for AI and network calls
retry 3 times with exponential backoff:
    let result = think "analyse this" as json
fallback:
    let result = {error: "unavailable"}

# Tag and trace a block of execution
observe "pipeline run" with tags {user: user_id}:
    let summary = think summarize(document)

# Deterministic AI output in tests
test "classifier":
    mock think as "sports"
    expect classify(text) == "sports"

# Pipe operator — chain transformations left to right
let result = data |> parse() |> filter() |> sort() |> take(10)

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

# Snapshot testing for AI outputs (Phase 26)
test "greeting shape":
    expect_snapshot(think "Say hi" as text, "greeting")

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

### 1.11.0
- **Real language server support** — this extension now spawns
  `nekova lsp` (a hand-rolled JSON-RPC-over-stdio server, part of
  NEKOVA core as of Phase 26) as a subprocess and wires it up for
  `.nk` files: live inline errors from the actual lexer/parser
  instead of nothing between manual `Check File` runs, hover docs
  that resolve to a task/class's real signature and docstring when
  it's user-defined, and autocomplete for keywords, builtins, and
  everything declared in the open document — including type-aware
  method suggestions right after `obj.`. New
  `nekova.enableLanguageServer` setting (default on) to turn it off
  if needed
- 1 new snippet: `expectsnap` (`expect_snapshot`, Phase 26's snapshot
  testing for AI outputs) — no new syntax-highlighting patterns were
  needed for it, since it's an ordinary function call and already
  matched by the extension's existing generic
  `identifier(` highlighting rule, same as any other builtin
- Welcome message and status bar now report `v1.11.0`: real inline
  errors/hover/autocomplete, `nekova fmt --diff`, the interactive
  `nekova new` wizard, `nekova.lock`, `--why`, and snapshot testing

### 1.10.0
- Syntax highlighting for Phase 25's `converse` keyword, plus scoped
  highlighting for the `using` and `budget` soft keywords inside a
  `think` clause (`think "..." using "claude-sonnet"`, `think "..."
  with budget: 500`) — matched the same lookahead-based approach
  already used for `prompt`, so ordinary variables named `using` or
  `budget` elsewhere in a program aren't affected
- 6 new snippets: `converse`, `thinkshape` (think as a defined
  shape), `thinkbudget`, `thinkmodel`, `imaginefile`, `aiusage`
- Welcome message and status bar now report `v1.10.0`: the docs site
  going live, plus `think ... as <Shape>`, cost/token tracking,
  `converse:` blocks, and the sandbox prompt-injection guard

### 1.9.9
- Syntax highlighting for all of Phase 23/24's new syntax: `const`,
  `enum`, optional chaining (`?.`), and spread (`...`) — previously
  `...` inside a list/dict would highlight as two range operators
  (`..`) plus a stray dot, since spread didn't exist as its own
  pattern; the range pattern is now correctly checked after spread so
  the three dots aren't split apart
- 10 new snippets: `const`, `enum`, `letlist`/`lettuple`/`letdict`
  (destructuring), `optchain`, `setlit`, `callkw` (keyword arguments),
  `thinkerr` (think with inline error handling), `taskdoc` (task with
  a docstring)
- Welcome message and status bar now report `v1.9.9`, describing what
  actually shipped: destructuring, keyword arguments, `const`, spread
  syntax, optional chaining, enums, and a new `Set` type, plus more
  accurate error messages (indentation depth, builtin exceptions) —
  no extension-side logic changes were needed for the error-message
  improvements, since those are core-interpreter fixes, but the
  version and in-editor messaging now reflect them

### 1.9.8
- Welcome message and status bar now report `v1.9.8`, announcing Phase 23's
  correctness fixes (accurate recursion errors, labeled mock AI responses,
  type-mismatch errors, near-miss variable suggestions) — no extension-side
  code changes required for these, since they're core-interpreter fixes,
  but the version and in-editor messaging now reflect them
- Fixed this file — the 1.9.7 entry below was previously garbled (an
  unclosed bold marker and a stray quote, with no real content) and the
  Features section's theme description was stale, still describing a
  single grey-inclusive theme after 1.9.7 had already split it into two
  grey-free themes

### 1.9.7
- Added the **NEKOVA Light** color theme — a genuine second theme, not a
  toggle: pure white (`#FFFFFF`) background, dark green-black body text
  (the one necessary compromise, since literal white text is invisible on
  white), saturated greens for keywords and accents
- Revised **NEKOVA Dark** — removed every grey token color (comments,
  operators, secondary keyword groups) in favor of white and green only.
  True red/amber remain reserved exclusively for error/warning UI in both
  themes
- Replaced the `.nk` file icon with the current simplified "nk" mark —
  an earlier direct trace of the full NEKOVA logo tested illegible at
  actual 16px file-icon size, even though it read fine at logo size, so
  it was rebuilt from simple strokes instead of fine detail like thin rings

### 1.9.6
- Added **`observe "label" with tags {...}:`** highlighting and correct
  auto-indent (block-opening, like `sandbox`/`retry`)
- Added **`mock think as "..."`** highlighting — a single-line statement,
  not a block, so it's intentionally absent from the indent rules
- Added the **`\|>` pipe operator**
- Added `observe`, `mock`, and `pipe` snippets (65 snippets total, up from 62)
- Fixed `language-configuration.json`'s `onEnterRules` — it's a separate
  list from `indentationRules` for a different VS Code mechanism (Enter-key
  behavior vs. paste/reindent), and had silently fallen out of sync since
  1.9.5: missing `finally`, `memory`, `retry`, `fallback`, `every`, `watch`,
  and `prompt` even though `indentationRules` already had them

### 1.9.5
- Added the **NEKOVA Dark** color theme — pepper-red and gold throughout,
  with AI-native keywords highlighted brightest
- Added **`prompt` block** highlighting as a declaration keyword, but only
  when genuinely defining a prompt (`prompt name(...):`) — everywhere else
  `prompt` still highlights as a plain identifier, matching its status as a
  soft keyword at the language level
- Added **NEKOVA: Test File** and **NEKOVA: Debug File** commands
- Added `prompt`, `retry`, and `retrys` snippets
- Added `retry`, `fallback`, `every`, `watch`, and `prompt` to auto-indent
  rules after a trailing `:`; added `fallback` to the auto-dedent rules
  alongside `catch`/`finally`, since it's a sibling clause of `retry`
- Fixed extension packaging — the file icon and color theme referenced
  paths (`icons/nk-file.svg`, `themes/nekova-color-theme.json`) that didn't
  match where those files actually lived in the packaged extension. Fixed
  and verified by unzipping the built `.vsix` directly

### 1.9.4
- Fixed the file-icon theme (`nekova-icons`) — `.nk` files were falling back
  to the generic text-file icon because the theme pointed at an `icons/`
  folder that didn't exist in the packaged extension. The custom `.nk` file
  icon now actually renders in the file explorer

### 1.9.2
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

Licensed under the [Business Source License 1.1](https://github.com/kinghenesey/NEKOVA/blob/main/LICENSE) — free for personal use, learning, internal tools, and any product *written in* NEKOVA, with no revenue cap. See the [Licensing FAQ](https://github.com/kinghenesey/NEKOVA/blob/main/LICENSING_FAQ.md) for details.