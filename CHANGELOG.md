# NEKOVA Changelog

All notable changes to NEKOVA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.8.0] — 2025-06-27 · Phase 19 "NEKOVA Sandbox"

### Added
- **`nekova/sandbox/`** — full sandbox package: `SandboxEnvironment`, `SandboxResult`, `run_sandboxed()`
- **`SandboxResult`** — structured result with `.output`, `.error`, `.safe`, `.ok`, `.duration`, `.mode`, `.violations`
- **`SandboxEnvironment`** — restricted `Environment` subclass with `STRICT_ALLOWLIST` / `RELAXED_ALLOWLIST` and `ALWAYS_BLOCKED` set; records all violation attempts
- **`run_sandboxed(source, mode, limits, allow)`** — public API: parses + runs NEKOVA code in isolation with timeout, output capture, `builtins.open` / `__import__` patching
- **`sandbox_run(source, mode)`** — NEKOVA-level builtin; callable from `.nk` files
- **`sandbox strict:` / `sandbox relaxed:`** — upgraded from stub to real isolated execution; stores result in `sandbox_result` variable; body output passes through transparently
- **`nekova run --sandbox [--sandbox-mode strict|relaxed]`** — CLI flag to run any `.nk` file in sandbox mode
- stdlib `.nk` modules pre-warmed before strict sandbox activates `__import__` block (allows `use math` / `use string` inside sandboxes)
- Resource limits: `max_time` (default 10s), `max_output` (50k chars), `max_iterations` (100k)

### Tests
- 44 new tests in `tests/test_phase19.py`
- Total: **1033 passing**, zero regressions

---

## [1.7.0] — 2025-06-27 · Phase 18 "Standard Library in NEKOVA"

### Added
- **`nekova/stdlib/nk/math.nk`** — first stdlib module written in NEKOVA: `clamp`, `lerp`, `map_range`, `factorial`, `fibonacci`, `gcd`, `lcm`, `sign`, `average`, `product`, `is_even`, `is_odd`, `pi`, `e`, `inf`
- **`nekova/stdlib/nk/string.nk`** — string utilities in NEKOVA: `repeat`, `pad_left`, `pad_right`, `truncate`, `capitalize`, `reverse`, `is_palindrome`, `starts_with`, `ends_with`, `contains`, `is_empty`, `wrap`
- **`nekova/stdlib/nk/file.nk`** — file utilities in NEKOVA: `read`, `write`, `append`, `exists`, `delete`, `lines`, `line_count`, `head`, `tail`, `copy`
- **`nekova/stdlib/nk/date.nk`** — date utilities in NEKOVA: `now`, `today`, `timestamp`, `year`, `month`, `day`, `format`, `add_days`, `diff_days`, `day_of_week`, `is_weekend`, `is_weekday`, `is_before`, `is_after`, `days_until`, `days_since`, `is_today`
- **`nekova/stdlib/nk_loader.py`** — `.nk` module loader: finds, parses, runs `.nk` files, caches results, exports only user-defined names
- `load_module()` now merges `.nk` exports on top of Python module base — `.nk` wins on conflicts, Python fills in primitives (`sqrt`, `floor`, `ceil`, etc.)
- File builtins registered in interpreter: `file_read`, `file_write`, `file_append`, `file_exists`, `file_delete`
- Date builtins registered in interpreter: `date_now`, `date_today`, `date_timestamp`, `date_format`, `date_add_days`, `date_diff_days`, `date_day_of_week`
- Math primitives registered in interpreter: `sqrt`, `floor`, `ceil`, `log`, `log10`, `sin`, `cos`, `tan`, `pow`

### Fixed
- `_parse_primary`: method calls on string literals (`"sep".join(items)`) now work via `_apply_postfix()`
- `_parse_primary`: keyword tokens used as expressions fall through to identifier fallback (enables `repeat(...)`, `clamp(...)` etc. when they're user tasks)
- `REPEAT` token followed by `(` is now treated as a function call, not a loop
- `_peek_type()` helper added to parser for lookahead disambiguation

### Tests
- 73 new tests in `tests/test_phase18.py`
- Total: **989 passing**, zero regressions

---

## [1.6.0] — 2025-06-26 · Phase 17 "Power User Layer"

### Added
- **Generators / `yield`** — any task containing `yield` becomes a generator factory; fully works inside `while`, `if`, and `for` loops; consumed by `for x in gen():` syntax
- **Decorators / `@`** — `@decorator` and `@decorator(args)` syntax; stackable; accepts keyword names as decorator identifiers
- **Error types** — `error NetworkError: message str, code int` defines typed, raiseable error constructors with `__error__` marker; catchable via `try/catch`
- **Typed tasks** — `task add(a: int, b: int) -> int:` enforces param types at call time with coercion; return type annotation parsed and checked
- **`class` keyword** — alias for `object`; `class Foo extends Bar:` works identically to `object Foo extends Bar:`
- Keywords now accepted as task names, decorator names, and method names (prevents parser collisions)
- `@` lexed as `AT` token; `->` already existed as `ARROW`

### Fixed
- `_exec_CallExpression`: callee resolution now handles both string names and AST node callees (fixes decorator-with-args and higher-order call patterns)
- `for` loop: accepts any `__iter__`-able value including generators
- `test_phase2.py`: unknown character test updated from `@` to `~` (since `@` is now valid syntax)

### Tests
- 29 new tests in `tests/test_phase17.py`
- Total: **916 passing**, zero regressions

---

## [1.5.0] — 2025-06-25 · Phase 16 "Standout Features"

### Added
- `speak <expr>` — text-to-speech; uses `say` (macOS), `espeak` (Linux), PowerShell (Windows), falls back to `[speak] text`
- `listen` / `let x = listen "prompt"` — speech-to-text via SpeechRecognition; falls back to `input()` without the library
- `every <N> <s|m|h> [X times]:` — scheduled repeated execution; finite loops run inline, infinite loops run in a daemon thread
- `test "label": / expect <expr>` — built-in test runner with ✓/✗ output, per-test pass/fail counts, and totals on the interpreter
- `imagine "prompt" [as url|path|base64]` — AI image generation via OpenAI DALL-E 3 or Stability AI; returns mock URL without an API key
- `shape Name: / field type [= default]` — validated data schema constructor with type coercion and `__shape__` marker
- `watch "file.txt":` / `watch variable:` — file mtime watcher and expression change watcher (Ctrl+C to stop)

### Fixed
- Keywords used as method names (e.g. `func speak()`) now parse correctly — dot-access property names accept any token
- Class parser `func` method names accept any token (not just IDENTIFIER)

### Tests
- 34 new tests in `tests/test_phase16.py`
- Total test suite: **887 passing**, zero regressions

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