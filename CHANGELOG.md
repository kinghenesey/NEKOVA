# NEKOVA Changelog

All notable changes to NEKOVA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.4.0] — 2026-06-25 · Phase 15 "Stability"

### Added (RED — Critical Gaps)
- `in` / `not in` operators — membership test for lists, strings, and dicts
- `//` floor division operator — integer division with correct negative rounding
- `range(stop)` / `range(start, stop)` / `range(start, stop, step)` builtin — returns a list
- List and string slicing — `items[1:3]`, `items[:2]`, `items[2:]`, `s[1:4:2]`
- Exception objects — `raise "msg"` and `catch e:` now bind the raised value to `e`
- Core builtins — `len`, `str`, `int`, `float`, `bool`, `abs`, `round`, `min`, `max`, `sum`, `sorted`, `reversed`, `list`, `dict`, `print`

### Added (YELLOW — Language Completeness)
- Default parameters — `task greet(name, greeting="Hello"):`
- `*args` / varargs — `task sum(*nums):` collects extra args into a list
- `raise <expr>` statement — raises a `NEKOVARaiseError` catchable via `try/catch`
- `finally` block — `try: ... catch e: ... finally: ...` always runs cleanup
- `pass` statement — no-op placeholder for empty blocks
- `assert <condition> [, message]` — raises `NEKOVAAssertionError` on failure
- Multi-argument `show` — `show "x =", 42` prints space-separated values
- `is` / `is not` operators — identity comparison (primary use: `x is null`)
- Ternary expression — `value if condition else other` in any expression context
- `run()` alias on `Interpreter` for test and REPL compatibility

### Fixed
- Parser `not in` backtracking — uses `self.pos` (not `self._pos`)
- OSI license classifier removed from `pyproject.toml` (setuptools 72+ compatibility)

### Tests
- 50 new tests in `tests/test_phase15.py` covering all RED and YELLOW items
- Total test suite: **853 passing**, zero regressions

---

## [1.3.1] â€” 2025-06-25 Â· Phase 14 "Foundation"

### Added
- `break` and `continue` keywords for `for`, `while`, and `repeat` loops
- `global` keyword â€” declare outer-scope variables inside tasks (`global x, y`)
- Multi-line string literals (`"""..."""` and `'''...'''`)
- `think` timeout â€” 30s default on all AI provider calls, configurable via `nekova.toml` `[ai] think_timeout`
- W009 checker warning â€” non-exhaustive `match` blocks (missing `else` arm)

### Fixed
- `elif` chain bug â€” 4+ elif levels now wire correctly via explicit `_tail` pointer
- Augmented assignment (`+=`, `-=`, `*=`, `/=`) desugared cleanly in the parser
- `and` / `or` now parsed with correct precedence tower
- Tab indentation now correctly counted (1 tab = 4 spaces)
- F-string unterminated error now raises `LexerError` with line/col instead of bare `SyntaxError`
- Transpiler bare imports fixed â€” works correctly on pip-installed versions
- Import messages routed to stderr, no longer polluting stdout
- `recall` missing key now returns `null` gracefully via sentinel pattern
- `repeat` loop now shares scope with outer environment (consistent with `for`/`while`)

### Improved
- All AST nodes now carry a `line` attribute stamped by the parser
- Interpreter tracks exact line as execution descends into nested statements
- Tasks now use lexical closure scoping â€” close over variables from their definition scope
- `_call_task` parents local environment to `closure_env` instead of always `self.globals`
- `_global_names` properly saved and restored per task call â€” no bleed between nested calls
- Version bumped: `1.3.0` â†’ `1.3.1`

---

## [1.3.0] â€” 2024-06-23 Â· Phase 12 "Forge Tools"

### Added

#### 12A â€” Project Templates (`nekova new --template`)
- `nekova new myapp --template web` â€” web server scaffold with `route`/`serve` structure
- `nekova new myapp --template ai` â€” AI-native scaffold with `think`/`remember`/`recall`
- `nekova new myapp --template fullstack` â€” web + AI + SQLite database scaffold
- Default template (`nekova new myapp`) unchanged â€” blank NEKOVA project
- New module: `nekova/cli/templates.py` with full file scaffolding per template
- Each template generates `src/`, `tests/`, `nekova.toml`, `.gitignore`, `README.md`, `.env.example`

#### 12B â€” REPL Improvements
- **Arrow-key history** â€” Up/Down arrows navigate previous commands (via `readline` on Unix, `pyreadline3` on Windows)
- **Persistent history** â€” session history saved to `~/.nekova_history` (max 500 entries)
- **`?help` shorthand** â€” `?help` now works as an alias for `help`
- **`?<cmd>` aliases** â€” any command can be prefixed with `?` (e.g. `?vars`, `?history`)
- **`templates` command** â€” list available project templates from inside the REPL
- Improved welcome message and help text

#### 12C â€” `nekova run --watch` Auto-rerun
- `nekova run app.nk --watch` â€” re-runs file on every save
- `nekova run --watch` â€” resolves entry from `nekova.toml`, then watches
- `nekova watch app.nk` â€” standalone subcommand alias
- Event-based watching via `watchdog` when installed; falls back to polling (0.5s interval)
- Timestamped run separators in output for clarity
- New module: `watcher.py`

#### 12D â€” Version & Release Prep
- Version bumped: `1.2.0` â†’ `1.3.0`
- Codename: `Genesis` (unchanged)
- `CHANGELOG.md` added
- `pyproject.toml` version updated

---

## [1.2.0] â€” Phase 11 "Package Forge"

### Added
- Full package system: `nekova install`, `nekova uninstall`, `nekova search`, `nekova info`, `nekova deps`, `nekova publish`
- 11 bundled packages: `requests`, `validation`, `crypto`, `charts`, `ui`, `scheduler`, `forms`, `auth`, `email`, `storage`, `ml`
- Test suite: 663 passing tests

---

## [1.1.0] â€” Phase 10 "Developer Experience"

### Added
- `nekova fmt` â€” NEKOVA code formatter
- `nekova check` â€” static analyser (error codes E011, W003, W005, W006)
- Smarter error messages with hints

---

## [1.0.0] â€” Phases 1â€“9 "Foundation"

### Added
- Core language: lexer, parser, interpreter
- AI primitives: `think as json/list/bool/schema/text`, `remember`/`recall`/`forget`
- Web DSL: `route`, `serve`
- Database DSL: `connect`, `query`, `insert`, `create`
- Stdlib: `use json/env/uuid/crypto/math`
- Class system: `object`/`init`/`self`/`new`/`extends`
- Pattern matching: `match`/`when`
- Async/await, streaming `think`, HTTP `fetch`
- REPL, multi-file imports, optional type hints
- `nekova.toml` configuration
- Rust-style error display with `did-you-mean` suggestions
- Published to PyPI (`nekova-lang`) and VS Code Marketplace