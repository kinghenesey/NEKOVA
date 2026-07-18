# NEKOVA Changelog

All notable changes to NEKOVA are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.13.0] — AI-Native Differentiators III

Six features aimed specifically at "a language where AI is a first-class
citizen" rather than generic language features with an AI label on them.

### Added

- **Typed AI output validation + re-prompt.** `think "..." as User` already
  coerced a response's field types against a shape — it now actually
  *validates* against the shape (missing required fields, wrong types) and,
  if validation fails, automatically re-prompts the AI with the specific
  problems named, up to 2 additional attempts, before raising a clear error.
  Previously a missing required field just silently became `None`.
- **Probabilistic testing.**
  `test "label" repeat 10 times, expect at least 8 passes:` — a test block
  that runs its body N times and only requires a minimum number of runs to
  fully pass, for testing AI-backed behavior where a single run's outcome
  isn't a meaningful signal on its own. `repeat N times` with no explicit
  `expect at least` still requires all N to pass (no silent tolerance).
- **Dollar-denominated think budgets.** `think "..." with budget: $0.01`
  — budgets can now be a cost estimate, not just a token count. `$` money
  literals are a new lexer/parser primitive; the estimate uses a single
  blended cost-per-1000-tokens constant since NEKOVA can't keep a live,
  per-provider pricing table in sync with every provider's rate card.
  Token-count budgets (`with budget: 500`) are unchanged.
- **Model fallback chains.** `think "..." using ["model-a", "model-b",
  "local-model"]` — tries each model in order, falling to the next only
  once an attempt (with its own transient-failure retries) is fully
  exhausted. Fixed a real gap found while building this: real providers
  (Anthropic, OpenAI, Gemini) were hardcoding their default model and
  silently ignoring `using` entirely — they now respect a per-call
  override, falling back to their default when none is given.
- **Deterministic AI-call replay ("cassettes").**
  `nekova run app.nk --record-ai cassette.json` runs for real and saves
  every prompt/response pair; `--replay-ai cassette.json` serves recorded
  responses instead of calling a provider at all — no API key, no spend,
  same output every run. A cassette miss fails immediately with a clear
  message rather than burning through retry backoff on something that can
  never succeed.
- **Capability-scoped agent sandboxing.**
  `sandbox strict allow: [search_web, send_email]:` — an explicit list of
  task names the block may call, enforced by the interpreter at every
  call site, not by convention. Only restricts calls to actual
  user-defined tasks; ordinary builtins (`len`, `filter`, ...) stay
  unrestricted since they're not "capabilities" an agent is being granted.
  Nested sandboxes intersect allow-lists rather than the inner one
  overriding the outer.
- **Streaming as a first-class construct.**
  `for chunk in think_stream("..."):` — genuinely lazy: the loop body
  processes each chunk as it's produced rather than waiting for the whole
  response first (verified with a `break` after 2 of 5 chunks pulling
  exactly 2, not all 5). Providers get a default word-chunking
  `stream_chunks()` built on their existing `ask()`; a provider wanting
  true token-by-token streaming from its underlying API can override it
  directly.

## [1.12.0] — Education Layer

NEKOVA started as a way to help classmates who got tripped up learning
Python — this phase leans back into that directly.

### Added

- **`nekova learn`** — a guided, interactive terminal tutorial. Five
  lessons (variables, printing, conditionals, tasks, `think`), each
  checked by running the learner's actual code against the real
  interpreter rather than string-matching their input.
- **`nekova explain <file.nk>`** — runs a file and, if it errors,
  explains why in plain language: a deterministic, template-based
  walkthrough for every error type in the catalogue, plus an optional
  one-sentence AI-generated addition (via `think` itself). Pass
  `--no-ai` to skip the AI addition.
- **`nekova translate <script.py>`** — best-effort Python-to-NEKOVA
  translation using Python's own `ast` module. Handles assignments,
  functions, conditionals, loops, f-strings, `print()`, and more;
  anything unsupported is flagged with a `# TODO(translate)` comment
  naming exactly what and why, rather than silently dropped or guessed.
- **`nekova classroom <dir>`** — batch-grades a directory of student
  `.nk` submissions against a reference `solution.nk` (or a plain
  `expected.txt`), running each submission in-process with a timeout
  backstop so one runaway submission can't hang the whole grading run.
- **`nekova help <topic>`** and in-REPL **`help <topic>`** — a
  keyword/builtin glossary (~25 entries) with a real code example for
  each, backed by the same lookup on both surfaces. Forgiving of
  near-misses ("function" → task, "print" → show) and typos.
- **`--simple-errors`** flag for `nekova run` — strips error output
  down to plain sentences: no error code, no box-drawing header, just
  the source line and what went wrong. Aimed at a classroom/beginner
  audience, distinct from `--why` (which adds detail rather than
  removing it).
- Two new proactive `nekova check` warnings: **W010** (comparing
  directly to a boolean literal — `if x == true:` instead of
  `if x:`) and **W011** (equality comparison between floats, which
  can silently fail due to rounding).
- The visual debugger's call-stack view now renders as stacked ASCII
  boxes instead of a flat arrow list, making nested calls easier to
  read at a glance.

---

## [1.11.0] — 2026-07-12 · Phase 26 "Developer Experience"

### Added

- **A real Language Server Protocol implementation** — `nekova lsp`,
  served over the standard JSON-RPC-over-stdio transport, hand-rolled
  rather than built on a framework (consistent with the rest of the
  toolchain). Replaces syntax-highlighting-only support in the VS
  Code extension:
  - **Diagnostics** — inline errors from the real lexer/parser, live
    as you type.
  - **Hover** — user-defined tasks/prompts/classes (from their actual
    signature and docstring) take priority over keywords, which take
    priority over builtins.
  - **Completion** — keywords, builtins, and every declared
    task/class/variable in the document; `obj.` triggers method
    completions with lightweight type inference from the object's
    last literal assignment.
  - The VS Code extension now spawns `nekova lsp` and wires it up for
    `.nk` files, toggleable via the new `nekova.enableLanguageServer`
    setting.
- **Multi-error parser recovery** — `Parser.parse()` catches each
  syntax error, resynchronizes to the next likely statement boundary,
  and keeps going, collecting every error in one pass instead of
  stopping at the first (`.all_errors` on the raised exception). A
  new `parse_best_effort()` always returns whatever was successfully
  parsed rather than raising, for LSP features that need to work on a
  document that's currently mid-edit and invalid elsewhere.
- **`nekova fmt --diff`** — shows a unified diff of what would change
  (single file or whole directory) without writing anything.
- **Interactive `nekova new` wizard** — running `nekova new` with no
  project name now prompts for name, template, and optional
  author/description, instead of erroring out immediately.
  Non-interactive usage is unchanged.
- **`nekova.lock`** — a committed, reproducible snapshot of every
  declared dependency's exact resolved version. `nekova lock --check`
  detects drift for CI, without writing anything.
- **`--why`** — walks the raised exception's traceback to name the
  specific internal lexer/parser/interpreter function and line that
  raised it, e.g. `raised in _exec_Identifier() at interpreter.py:2203`.
  Opt-in, silent by default, works uniformly for any error type.
- **`expect_snapshot(value, name)`** — snapshot testing for AI-output
  tests. First run saves a baseline; later runs compare against it
  and fail on drift. `nekova run --update-snapshots` accepts a
  changed value as the new baseline. Counted in the same test-block
  pass/fail tally as a regular `expect`.
- **`.env.example` scaffolding** — every project template now
  includes one; the `default` template didn't have one before this.

### Fixed — found while building the above

- The parser's "keyword as identifier" fallback (for cases like a
  task named `repeat`) was a denylist broad enough to also swallow
  genuine punctuation errors — a bare `)` silently became a bogus
  empty identifier instead of raising. Narrowed to a proper keyword
  allowlist.
- `Token.column` is 1-indexed and points at the position *after* a
  token ends, not its start — confirmed directly against the lexer.
  Fixed the resulting off-by-token-width position math in hover and
  diagnostics.
- Every terminal command in the VS Code extension (Run, Format,
  Check, Debug, REPL, New Project) was non-functional: they called
  `python -m nekova`, but `nekova/` has no `__main__.py`. Switched to
  `-m nekova_cli`, the module the installed console script itself
  delegates to.
- The extension's `package-lock.json` referenced a dependency version
  no longer resolvable on the npm registry; regenerated from scratch.

---

## [1.10.0] — 2026-07-06 · Phase 24b "Documentation Website" + Phase 25 "AI-Native Differentiators II"

Both phases shipped together in this release, same as 1.9.9 before it —
Phase 25 was originally slated for 1.11.0, but landed alongside 24b and
is published as 1.10.0. See the note under the Version Map in
ROADMAP.md.

### Added — Phase 24b

- **Documentation website**, live at
  [kinghenesey.github.io/NEKOVA](https://kinghenesey.github.io/NEKOVA/).
  28 pages (landing page + 27 documentation pages across Getting
  Started, Core Syntax, AI-Native Features, Classes & Objects,
  Advanced, and Reference) generated from plain markdown by a small
  Python static-site generator (`docs-site/build.py`) — adding a page
  means writing a `.md` file and one line in `nav.yaml`, no HTML or
  CSS required. Deploys automatically via GitHub Actions on every
  push to `main` that touches `docs-site/`. Every code example on
  the site was run against the actual interpreter before publishing,
  not written from memory.

### Added — Phase 25

- **`think "..." as <ShapeName>`** — a previously defined `shape`
  used directly as `think`'s output format. Builds an implicit
  schema from the shape's own fields, and the response comes back
  type-coerced and tagged with the shape's name.
  ```nekova
  shape User:
      name str
      age int
  let u = think "extract from: Ada, 30" as User
  ```
- **Cost/token tracking** — `think "..." with budget: 500` raises if
  the estimated prompt+response tokens exceed the budget; the new
  `ai_usage()` builtin returns a running `{calls, tokens}` total.
  Token counts are an estimate (~4 characters per token), since
  NEKOVA doesn't have a real tokenizer for every possible provider.
- **Explicit model selection** — `think "..." using "claude-sonnet"`.
  Sets the provider's `model` attribute for that call; the mock
  provider acknowledges it in plain-text responses (never in
  JSON/schema ones, where that would corrupt parsing).
- **`converse:` blocks** — multi-turn dialogue with automatic context:
  ```nekova
  converse:
      think "ask a clarifying question about {topic}"
      listen
      think "respond based on what they said"
  ```
  Starts with a clean conversation history each time; every `think`
  and `listen` inside the block automatically carries prior turns as
  context. Extended the same conversation-history mechanism (already
  used by `think ... as <format>`) to plain `think` and to `listen`,
  which didn't have it before.
- **`--debug-ai`** — prints the exact prompt sent to the provider
  (after memory/conversation context is prepended) for every `think`
  call, so you can see what a `think` line actually asks the model.
- **Sandbox prompt-injection guard** — `think` calls inside a
  `sandbox` block are checked against a list of common
  injection-style phrases ("ignore previous instructions", "you are
  now", etc.) and blocked as a sandbox violation if matched. Pattern
  matching, not a real security boundary — catches obvious phrasing,
  not a determined attacker rewording around it.
- **`imagine "..." as file`** with local caching — `file` is now a
  recognized format (alias for `path`), and identical
  `(prompt, format)` pairs are cached on disk under
  `.nekova_cache/imagine/`, so repeated calls during a dev loop don't
  regenerate (or re-bill) the same image.
- **think's own visible retry/backoff** — a transient failure gets
  two automatic retries with a short backoff before falling through
  to `when error:` or the swallow-to-string behavior. Retry messages
  print to stderr, not stdout, so they're visible to a human watching
  the terminal without polluting a program's actual output.

### Fixed

- **`self._sandbox_mode` was never actually set when entering a
  sandbox block.** Found while building the prompt-injection guard
  above. `_sandbox_guard()` checked this flag to decide whether to
  block operations like `think` in strict mode, but the flag stayed
  `""` the entire time a sandbox block ran — meaning `think` was
  never actually blocked in strict-mode sandboxes despite being in
  the blocked-operations list. Fixed so strict sandboxes now
  genuinely block `think`, matching what the code already claimed to
  do.

### Not done this release

- **Confidence/uncertainty surfacing** for `think ... as bool/json` —
  deferred rather than rushed. Changing what these calls return would
  be a breaking change with no real semantic backing in the mock
  provider (it has no actual notion of confidence to expose), and
  deserves proper design rather than a bolted-on field.

- **`tests/test_phase25.py`** — 32 tests. **1,358 tests passing, zero
  regressions.**

---

## [1.9.9] — 2026-07-04 · Phase 23b "Correctness & Trust — Part 2" + Phase 24 "Language Completeness II"

Both phases shipped together in this release — Phase 24 was originally
slated for 1.10.0, but landed alongside 23b and is published as 1.9.9.
See the note under the Version Map in ROADMAP.md; this is a deliberate,
transparent exception to the versioning policy, not an oversight.

### Fixed — Phase 23b

- **Bad-indentation-depth detection** — a dedent that doesn't land
  exactly on a previously-seen indent level now raises immediately,
  showing the valid indent levels and the depth actually found, instead
  of silently snapping to the nearest lower level or giving a generic
  "check your indentation" message.
- **Builtin exception audit** — every builtin call (`int()`, `float()`,
  `len()`, `range()`, `sum()`, etc.) is now wrapped so a bad argument
  raises a clean `NEKOVARuntimeError` instead of leaking a raw Python
  exception. Several of these previously weren't caught at all
  (`ValueError` had no handler anywhere) and surfaced a full Python
  traceback with file paths to the user — about as far from
  beginner-friendly as an error message can get. `int()`/`float()` get
  an extra-specific message since they're the most common case a
  beginner will hit.

### Added — Phase 24

- **Tuple-style destructuring** — `let (a, b) = pair`, `let (first,
  ...rest) = my_list`. Same semantics as the existing bracket form.
  `let (q, r) = divmod(10, 3)` covers "multiple return values" for free.
- **Named/keyword arguments** — `greet(name="Sam", greeting="Hi")`,
  including mixed positional+keyword calls and gap-filling with
  declared defaults. Clear errors for an unknown keyword or a value
  passed both positionally and by keyword.
- **`const` bindings** — `const MAX_RETRIES = 5`. Immutable once set;
  reassigning or redeclaring in the same scope raises. Simpler than
  `let` by design — no destructuring or captured-think forms.
- **Spread syntax** — `[...list_a, ...list_b]` and `{...defaults,
  ...overrides}`, including mixed spread+literal items. Overlapping
  dict keys: last write wins, same as writing them out by hand.
- **Optional chaining (`?.`)** — `user?.email`, `user?.method()`.
  Short-circuits to `null` if the object is `null` instead of raising;
  chains correctly (`a?.b?.c`). A plain `.` after a null result from an
  earlier `?.` still raises — only the explicit `?.` short-circuits.
- **Enums** — `enum Status: PENDING, ACTIVE, DONE`. Each member
  evaluates to its own name as a string (`Status.ACTIVE == "ACTIVE"`).
- **`Set` type** — `{1, 2, 3}` literal syntax, automatically
  disambiguated from a dict literal at parse time (a dict entry always
  has a `key: value` shape; a set element never does). `{}` still means
  an empty dict, unchanged. New builtins: `set_union`, `set_intersection`,
  `set_difference`. Putting an unhashable value (a list or dict) in a
  set raises a clear error instead of a raw Python `TypeError`.
- **`null` semantics audited** — comparisons, truthiness, arithmetic,
  and container membership all checked and confirmed consistent; no
  further code changes were needed beyond what 23a/23b already fixed.

### Not done this release

- **`nekova check --strict`** (opt-in static type-hint enforcement) —
  deferred rather than rushed. It's CLI/tooling work distinct from the
  runtime language changes above and deserves its own scoped pass.

- **`tests/test_phase23b.py`** — 10 tests. **`tests/test_phase24.py`** —
  40 tests. **1,326 tests passing, zero regressions.**

---

## [1.9.8] — 2026-07-03 · Phase 23a "Correctness & Trust — Part 1"

### Fixed

- **Recursion error accuracy** — NEKOVA now tracks its own call depth
  independently of Python's frame limit. Unbounded recursion raises
  `NEKOVARuntimeError` with message `"Task 'X' exceeded the maximum call
  depth (500 nested calls)."` rather than the previous misleading
  "Infinite Recursion" label which fired at ~198 calls due to Python's own
  frame overhead. Legitimate deep recursion under the limit succeeds cleanly.
  Call depth resets correctly between independent task calls.

- **Mock AI responses now self-identify everywhere** — every response branch
  in `MockProvider` now prefixes `[MOCK]`. Previously the `hello`/`hi` and
  capital-city branches returned clean, confident text indistinguishable from
  a real model response — a beginner's first `think` call could silently look
  like real AI output. Fixed.

- **`"5" + 3` raises a type error instead of coercing silently** — adding
  `text` to `number` (or vice versa) now raises:
  `Cannot use '+' between 'text' and 'number'. Convert one side explicitly,
  e.g. str(value) or int(value).`
  Numeric addition and string-to-string concatenation are unaffected.

### Added

- **`doc(task_name)`** — built-in function that returns the docstring of any
  task defined with a triple-quoted string as its first statement.
  `doc(greet)` returns the stripped docstring. `doc(task_without_doc)`
  returns `"No docstring for 'X'."` rather than crashing.

- **List destructuring** — `let [first, second, ...rest] = some_list`
  unpacks a list into named bindings. `...rest` captures remaining elements
  as a list. Works with any iterable.

- **Dict destructuring** — `let {name, age} = some_dict` binds dict values
  to local variable names matching the keys.

- **Async task improvements** — loops, conditionals, nested `await` calls,
  and type-hinted signatures all work correctly inside `async task` bodies.
  Default parameters and varargs supported.

- **`think "..." when error: <fallback>`** — inline error handling for `think`
  calls. If the AI call fails, the fallback expression is evaluated instead of
  propagating the error.

- **NEKOVA Light theme** for VS Code — alongside the revised NEKOVA Dark
  theme (greys removed, contrast improved).

### Metrics

- Tests passing: **1,276** (up from 1,226)
- Test classes: **208** (up from 200)
- Test phases: **26** (up from 25)

### Still in progress (Phase 23b)

- Near-miss variable suggestions ("did you mean X?" on undefined names)
- Indentation error specificity (show expected vs. actual indent level)
- Python exception audit (raw `TypeError`/`KeyError` messages still leak in edge cases)


## [1.9.7] — 2026-07-03 · NEKOVA Dark and Light Themes

### Added

- **NEKOVA Light color theme** — a genuine second theme, not a variant
  toggle: pure white (`#FFFFFF`) background, with a dark green-black
  (`#0D2818`) for plain code text (the one necessary compromise, since
  literal white text is invisible on white) and saturated greens for
  keywords and accents
- **NEKOVA Dark theme revised** — removed every grey token color (comments,
  operators, secondary keyword groups) in favor of white and green only,
  addressing feedback that the previous grey tones made the theme feel
  muddy. True red/amber remain reserved exclusively for error/warning UI
  in both themes, so diagnostics stay visually distinct from ordinary
  syntax — verified by scanning rendered output for any surviving grey
  pixels beyond expected antialiasing
- **Simplified `.nk` file icon** — replaced the icon (in both the original
  red/gold "file card" design and a later direct trace of the full NEKOVA
  logo) with an original mark built from simple strokes rather than fine
  detail like thin rings, specifically because the traced logo tested
  illegible at actual 16px file-icon size, even though it read fine at
  logo size

---

## [1.9.6] — 2026-07-03 · Phase 22 "Observability + Testing + Pipe Operator"

### Added

- **`observe "label" with tags {...}:` blocks** — structured telemetry
  around any code block, tagging runs for later inspection
- **`mock think as "response"`** inside `test` blocks — lets tests assert
  against deterministic AI output instead of hitting a real provider,
  directly fixing the "is this a real AI response" ambiguity real users
  ran into with the unlabeled Mock provider (fully resolved in 1.9.8)
- **`|>` pipe operator** — `data |> parse() |> filter() |> sort() |> take(10)`,
  pairs naturally with `think` chains as intended

### Process note

This phase shipped (1,226 tests passing, up from 1,203) without a version
bump at the time — `nekova/config.py`, `pyproject.toml`, and the VS Code
extension's `package.json` all stayed at `1.9.5` despite new keywords
landing. This entry and the version bump to `1.9.6` are a retroactive
correction, and this exact gap — no consistent rule for when a version
number changes — is what Phase 23 formally fixes with a documented semver
policy (see `ROADMAP.md`).

---

## [1.9.5] — 2026-07-02 · Phase 21 "Prompt Blocks + Retry/Fallback"

### Added

- **`prompt` blocks** — first-class named, composable prompt engineering
  at the language level. No other language or framework has this as syntax.
  ```nekova
  prompt summarize(text, style="professional", max_sentences=3):
      """
      Summarize the following in a {style} tone.
      Use at most {max_sentences} sentences.
      Text: {text}
      """
  let summary = think summarize(article, style="casual")
  ```
  Prompts are called via `think`, accept typed parameters with defaults,
  support triple-quoted multi-line templates with `{var}` interpolation,
  and are treated as soft keywords — `prompt` remains usable as a variable
  name for backward compatibility with existing programs.

- **`retry N times [with exponential|linear backoff]:` + `fallback:`** —
  first-class resilience for AI and network calls. Retries the body up to N
  times on any error. Control-flow signals (`return`, `break`, `continue`)
  are never treated as retry-triggering errors — they propagate immediately.
  On exhaustion, runs `fallback:` body if present, otherwise re-raises.
  ```nekova
  retry 3 times with exponential backoff:
      let result = think "analyse this" as json
  fallback:
      let result = {error: "unavailable", raw: text}
  ```

- **`tests/test_phase20.py`** — 4 test classes, 286 lines verifying the
  self-hosted lexer produces byte-for-byte identical token streams to the
  Python reference lexer on all stdlib `.nk` files

- **`tests/test_phase21.py`** — 9 test classes, 355 lines covering prompt
  basics, soft-keyword compatibility, typed params, retry success/exhaustion,
  backoff modes, control-flow propagation through retry, and edge cases

- **`tools/diff_lexers.py`** + **`tools/nk_tokenize.nk`** — token-stream
  diff harness. Verified 3,666 tokens exact match when `lexer.nk` tokenises
  itself using both the Python reference and self-hosted lexers

### Phase Milestones

- **Phase 20 complete** — `nekova/stdlib/nk/lexer.nk` ships: a 572-line
  NEKOVA lexer written in NEKOVA, verified token-for-token against the
  Python reference. NEKOVA has now written its own lexer.

- **Phase 21 complete** — `prompt` blocks and `retry`/`fallback` are both
  live. NEKOVA is now the only programming language with named, versioned,
  composable prompts as a built-in language construct.

---

## [1.9.4] — 2026-07-02 · Phase 20 "Self-Hosting: The Lexer"

### Added
- **`nekova/stdlib/nk/lexer.nk`** — the NEKOVA lexer, written in NEKOVA. A
  line-for-line port of `nekova/lexer/lexer.py`, matching Python `TokenType`
  names 1:1 so its output can be diffed directly against the reference lexer
- **`tools/diff_lexers.py`** + **`tools/nk_tokenize.nk`** — a token-stream
  diff harness that runs the Python reference lexer and the self-hosted
  NEKOVA lexer on the same source file and reports any mismatch, token by
  token. Verified byte-for-byte identical token streams on `math.nk`,
  `string.nk`, `date.nk`, `file.nk`, and `lexer.nk` tokenizing itself
  (3,666 tokens, exact match) — the strongest validation Phase 20 has had
  so far, beyond unit tests alone

### Fixed
- VS Code extension file-icon theme (`nekova-icon-theme.json`) referenced
  `./icons/nk-file.svg`, but the `icons/` folder never existed in the
  extension — `.nk` files silently fell back to the generic text-file icon
  in the file explorer. `nk-file.svg` now lives at the path the theme
  actually expects
- `tests/test_phase12.py::test_version_is_current` hardcoded an exact
  version-string assertion (`== "1.9.2"`) that required manual updates on
  every bump, defeating the point of the dynamic semver-shape check already
  sitting right above it. Removed the redundant literal check — this test
  now never needs manual updates again

---

## [1.9.2] — 2026-06-30 · Patch

### Fixed
- `nekova --version` was displaying `v1.3.1` instead of the current version —
  `nekova/config.py` had never been updated past the initial release while
  `pyproject.toml` was correctly bumped each phase
- Mojibake `Â·` in CLI output (version line and banner) caused by double-encoded
  UTF-8 bytes baked into `main.py` source — fixed at binary level
- Hardcoded `"nekova_version": "1.2.0"` in package manifest —
  now reads from `NEKOVA_VERSION` in `config.py`
- Version tests in `test_phase12.py` were asserting literal `"1.3.1"` and
  `"1.8.0"` — replaced with dynamic checks against `NEKOVA_VERSION` so they
  never need manual updating when the version bumps
- License changed from MIT to Business Source License 1.1 (BUSL-1.1)

### Added
- `LICENSING_FAQ.md` — plain-English explanation of what the BUSL license
  means for users, contributors, and companies building on NEKOVA

## [1.9.2] — 2026-06-27 · Phase 19b "Self-Hosting Blockers + Security"

### Self-Hosting Blockers — All Cleared
- **`dict[key] = value`** — subscript assignment now works for dicts, lists, and chained `d["x"]["y"] = z`
- **`0xFF` / `0XFF`** — hex integer literals with `_` separators (`0xFF_FF`)
- **`1e5` / `2.5e-3` / `1.5E+10`** — scientific notation floats
- **`1_000_000`** — underscore digit separators in all number literals
- **`..` DOTDOT token** — range operator for `match` arms
- **`match` range arms** — `when "a".."z":` matches character ranges, `when 1..10:` matches int ranges

### Security Fixes (38 bugs resolved)
- `not not x` / `--x` — unary operators now recurse correctly (Bug 14)
- `and`/`or` — true short-circuit evaluation, right side skipped when result known (Bug 15)
- SQL injection — full parameterised query rewrite with `_safe_identifier()` validation (Bug 16)
- `hmac_valid()` — now accepts `algorithm` parameter (Bug 17)
- `token_bytes` — exported from crypto module (Bug 18)
- `try` without `catch` — now re-raises instead of swallowing (Bug 19)
- All servers default to `127.0.0.1` not `0.0.0.0` (Bug 20)
- Formatter `**` preserved — no longer split to `* *` (Bug 22)
- `async task` keyword accepted alongside `async func` (Bug 25)
- `init_interpreter_memory()` wired to `Interpreter.__init__` — per-interpreter memory isolation (Bug 33)
- Double memory injection removed from all AI providers (Bug 35)
- `env_all()` redacts secrets (`*KEY*`, `*SECRET*`, `*TOKEN*`, `*PASSWORD*`) (Bug 37)
- Bare imports in `deploy/` and `cli/deploy.py` fixed to use full `nekova.*` paths (Bug 38)
- `is_number("--5")` now returns `false` (Bug 44)
- Voice temp file deleted after playback, sleep duration computed from word count (Bug 36)
- Vision module base64 round-trip removed — raw bytes passed directly (Bug vision)
- `ConfigError` hoisted to single top-level import in `main.py` (duplicate import)

### New String Methods
- `.join()`, `.lstrip()`, `.rstrip()`, `.zfill()`, `.center()`, `.is_digit()`, `.is_alpha()`

### Tests
- 53 new self-hosting tests in `tests/test_self_hosting.py`
- 44 bug fix regression tests in `tests/test_bugfixes2.py`
- Total: **1130 passing**, zero regressions

### Milestone
All self-hosting blockers cleared. Phase 20 begins: write the NEKOVA lexer in NEKOVA.

---

## [1.9.2] — 2026-06-27 · Phase 19 "NEKOVA Sandbox"

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
- Version bumped: `1.3.0` → `1.3.1`

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
- Version bumped: `1.2.0` → `1.3.0`
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