# NEKOVA Language — Official Roadmap

**Version:** 1.13.0 · Genesis  
**Tests:** 1,646 passing · 31 test phases  
**Status:** Active development · Phase 26c complete · Phase 27 next  
**Built by:** Emmanuel King Christopher · SYNEKCOT Tech · Nigeria 🇳🇬

---

## What NEKOVA Is

The world's first AI-native programming language. Every other language treats AI as a library you import. NEKOVA makes AI a keyword.

```nekova
result = think "Summarise this document" as json
speak f"Here is your summary: {result.title}"

every 1 day:
    news = think "Top AI news today" as list
    show news
```

No imports. No boilerplate. No setup. Just the idea.

---

## Versioning Policy

Adopted 2026-07 in response to external feedback that version bumps had no
consistent meaning. Going forward:

- **Patch** (`1.9.x`) — bug fixes only, no new syntax or keywords
- **Minor** (`1.x.0`) — new keyword, feature, or stdlib surface
- **Major** (`x.0.0`) — reserved for self-hosting milestones (parser-in-NEKOVA,
  interpreter-in-NEKOVA) — points where the language commits to a new level
  of backward-compatibility guarantee

## Version Map

| Version | Phase | What Ships |
|---------|-------|-----------|
| 1.9.2 | 19b | Self-hosting blockers fixed, 38 security bugs resolved |
| 1.9.4 | 20 | ✅ Lexer in NEKOVA, verified token-for-token against Python reference |
| 1.9.5 | 21 | ✅ `prompt` blocks, `retry`/`fallback` |
| 1.9.6 | 22 | ✅ `observe` blocks, `mock think`, `\|>` pipe operator |
| 1.9.7 | — | ✅ NEKOVA Dark theme revised (grey removed), new NEKOVA Light theme, simplified `.nk` file icon |
| **1.9.8** | 23a | ✅ Correctness & Trust Part 1 — recursion error accuracy, mock AI labeling, string+number type mismatch, near-miss variable suggestions (difflib), documented semver policy |
| **1.9.9** | 23b + 24 | ✅ Correctness & Trust Part 2 + Language Completeness II — see "Phase 23b" and "Phase 24" sections below for the full list; combined into one release per publishing decision. |
| **1.10.0** | 24b + 25 | ✅ Documentation Website + AI-Native Differentiators II — see "Phase 24b" and "Phase 25" sections below; combined into one release per publishing decision. |
| **1.11.0** | 26 | ✅ Developer experience — **current**. Language Server Protocol (real autocomplete, inline errors, hover docs), `nekova fmt --diff`, multi-error parser recovery, interactive `nekova new` wizard, `nekova.lock`, `--why`, `expect_snapshot(...)`, `.env.example` scaffolding |
| **1.12.0** | 26b | ✅ Education layer — `nekova learn`, `nekova explain`, `nekova translate`, `nekova classroom`, `nekova help` glossary, `--simple-errors` |
| **1.13.0** | 26c | ✅ AI-Native Differentiators III — typed AI output validation + re-prompt, probabilistic testing, dollar-denominated think budgets, model fallback chains, deterministic AI-call replay (cassettes), capability-scoped agent sandboxing, `think_stream` |
| **2.0.0** | 27 | Parser in NEKOVA — self-hosting milestone 2. Includes a published formal grammar (EBNF) and a parser/lexer fuzz-testing harness in CI, both prerequisites for this phase, not just nice-to-haves |
| **2.1.0** | 28 | Agent system, unified schema |
| **2.2.0** | 29 | Sandbox commercial API, `nekova teach`, deployment targets, WebSocket + middleware support in the web router |
| **2.3.0** | 30 | Safety & performance hardening — resource-limited sandbox quotas (CPU/memory, not just time), bytecode caching, public test-coverage dashboard |
| **3.0.0** | 31 | Full self-hosting — interpreter in NEKOVA |

Note on 1.9.9: per the original plan this was 23b alone, with Phase 24
("Language Completeness II") slated for 1.10.0. Both were completed and
shipped together in the same release and published as 1.9.9. This is a
deliberate, one-time exception to the versioning policy above — a minor
bump would have been more correct given the amount of new syntax — made
transparently rather than silently. The same thing happened again with
1.10.0: Phase 25 was slated for 1.11.0, shipped alongside 24b instead.
Future releases follow the policy as written.

Phases 26 onward are directional, not fully scoped — near-term phases (26–26b)
are committed; long-term phases are subject to reordering as the language
matures. See `NEKOVA-feature-analysis-2026-07.md` for the full source list
this roadmap draws from, including items not yet assigned a phase.

Version 2.0 remains a language milestone, not just a version bump. When the parser is written in NEKOVA, the language is stable enough to commit to backward compatibility. Everything before 2.0 is formative. Everything from 2.0 onward is a platform.

---

## Completed Phases

### Phase 1–12 · Core Language ✅
Lexer, Parser (AST), Interpreter, Environment and scope chain, Bytecode compiler and VM, Python transpiler, REPL with history, Formatter, Static checker (W001–W009), Debugger, Notebook, Web IDE, VS Code extension, Package manager, AI primitives (`think`, `remember`, `recall`, `forget`), Web server (`route`, `serve`, `fetch`), Database (`connect`, `db.create`, `db.query`), Class system, Pattern matching (`match`/`when`), Async/await, Agent pipelines, Multi-provider AI (Anthropic, OpenAI, Gemini, Mock), Rust-style error display with carets and `did-you-mean`

**Milestone:** Published to PyPI as `nekova-lang`. VS Code extension shipped.

### Phase 13 · Closures, Scoping, Operators ✅
Lexical closure scoping, `break`/`continue` in all loop types, `global` keyword, `+=` `-=` `*=` `/=` augmented assignment, `and`/`or` with correct precedence, `elif` chains, tab indentation, line numbers on all AST nodes

### Phase 14 · Safety, Stdlib, Timeouts ✅
`"""..."""` triple-quoted strings, `think` timeout (30s default, configurable), `match` exhaustiveness warning W009, `global x, y, z` multiple names, `_with_timeout()` on all AI providers

### Phase 15 · Standard Builtins ✅
`len`, `range`, `int`, `str`, `float`, `abs`, `min`, `max`, `sum`, `round`, `sorted`, `reversed`, `bool`, `list`, `print`, `pow`, `chr`, `ord`, `hex`, `bin`, `oct`, `enumerate`, `zip`, `map`, `filter`, `any`, `all`, `input`, `//` integer division, `in`/`not in`, list slicing `x[1:3]`, real exception objects, default parameter values, `pass`, `raise`, `finally`, `assert`, ternary expressions, f-string expressions, tuple unpacking

### Phase 16 · AI-Native Features ✅
`speak` (TTS), `listen` (speech-to-text), `every N unit [X times]:`, `test "name": expect ...`, `imagine "prompt"`, `shape Name: field type`, `watch "file":`

### Phase 17 · Power User Layer ✅
Generators (`yield`), decorators (`@decorator`), typed task signatures, custom error types (`error NetworkError:`), `async task` keyword

### Phase 18 · Standard Library in NEKOVA ✅
`math.nk`, `string.nk`, `date.nk`, `file.nk` — all written in `.nk`, running on NEKOVA.

**Milestone:** NEKOVA writing NEKOVA.

### Phase 19 · NEKOVA Sandbox ✅
`SandboxEnvironment`, `run_sandboxed(code, mode, limits)` API, resource limits, namespace isolation, `SandboxResult`.

**Milestone:** Commercial story begins.

### Phase 19b · Security + Self-Hosting Blockers ✅
38 security and stability bugs fixed. All 5 self-hosting blockers cleared:
- `dict[key] = value` index assignment
- `0xFF` hex literals
- `1e5` scientific notation  
- `1_000_000` underscore separators
- `match` range arms `when "a".."z":`

**Milestone:** All self-hosting blockers cleared. A working lexer written in NEKOVA is now achievable.

---

## Completed Phases (continued)

### Phase 20 · Self-Hosting Begins ✅ — v1.9.4

**Goal:** Write NEKOVA's lexer in NEKOVA. Ship it as `nekova/stdlib/nk/lexer.nk`.

**Deliverable:** `nekova/stdlib/nk/lexer.nk` — a real, tested NEKOVA lexer that tokenises NEKOVA source code, written entirely in `.nk`. Verified token-for-token identical to the Python reference lexer, including tokenizing its own source.

**Why this matters:** When a language can write its own lexer, it proves the language is expressive enough to handle real complexity. Python did this. Rust did this. Go did this. NEKOVA is next.

### Phase 21 · Prompt Blocks + Retry/Fallback ✅ — v1.9.5

```nekova
prompt summarize(text, style="professional"):
    """Summarize the following in a {style} tone: {text}"""

retry 3 times with exponential backoff:
    let result = think "analyse this" as json
fallback:
    let result = {error: "unavailable"}
```

### Phase 22 · Observability + Testing + Pipe Operator ✅ — v1.9.6

```nekova
observe "pipeline run" with tags {user: user_id}:
    let summary = think summarize(document)

test "classifier":
    mock think as "sports"
    expect classify(text) == "sports"

let result = data |> parse() |> filter() |> sort() |> take(10)
```

---

---

## Completed Phases (continued)

### Phase 23a · Correctness & Trust Part 1 ✅ — v1.9.8

Scoped directly from external feedback on v1.9.5 in live use. Prioritized
first because these fix things that actively mislead learners — which cuts
against NEKOVA's own stated mission — rather than adding new surface area.

1. ✅ **Recursion error accuracy.** `NEKOVARecursionError` now tracks
   NEKOVA's own call depth, separate from Python's built-in
   `RecursionError`, with `sys.setrecursionlimit()` raised at startup so
   the message reflects what actually happened.
2. ✅ **Every mock AI response now self-identifies.** All `MockProvider`
   branches, including `hello`/`hi` and capital-city responses, prefix
   `[MOCK]`.
3. ✅ **Type-mismatch error for `+` between incompatible types.**
   `"5" + 3` now raises instead of silently coercing to `"53"` — bools
   deliberately excluded so `"caught: " + error_obj`-style string-building
   still works.
4. ✅ **Near-miss suggestions for undefined variables.** Real `difflib`
   similarity check against in-scope names, printed as a separate
   "💡 Did you mean" block.
5. ✅ **Documented a real semver policy** — see *Versioning Policy* above.

**Carried forward to Phase 23b:** the bad-indentation-depth hint and the
full audit of remaining raw Python exceptions passed through with generic
messages — both completed below, not dropped.

### Phase 23b · Correctness & Trust Part 2 ✅ — v1.9.9

1. ✅ **Bad-indentation-depth detection.** A dedent that doesn't land
   exactly on a previously-seen indent level now raises immediately with
   the valid depths and the depth actually found, instead of silently
   snapping to the nearest lower level or giving a generic "check your
   indentation" message.
2. ✅ **Builtin exception audit.** Every builtin call (`int()`, `float()`,
   `len()`, `range()`, `sum()`, etc.) is now wrapped so a bad argument
   raises a clean `NEKOVARuntimeError` instead of leaking a raw Python
   exception — several of these (anything raising `ValueError`) weren't
   even caught before and surfaced a full Python traceback with file
   paths. `int()`/`float()` get an extra-specific message since they're
   the most common case a beginner hits.

### Phase 24 · Language Completeness II ✅ — v1.9.9

```nekova
let (a, b) = pair
let {name, age} = user
let (first, ...rest) = my_list
enum Status: PENDING, ACTIVE, DONE
const MAX_RETRIES = 5
let combined = [...list_a, ...list_b]
let merged = {...defaults, ...overrides}
greet(name="Sam", greeting="Hi")
show user?.email
let s = {1, 2, 3}
show set_union(s, {3, 4})
```

1. ✅ **Tuple-style destructuring** — `let (a, b) = pair`, with the same
   `...rest` support as the existing bracket form. `let (q, r) =
   divmod(10, 3)` covers the "multiple return values" use case for free.
2. ✅ **Named/keyword arguments at call sites** — `greet(name="Sam")`,
   including mixed positional+keyword and gap-filling with declared
   defaults. Clear errors for unknown keywords or a name passed both
   positionally and by keyword.
3. ✅ **`const` bindings** — immutable once declared; reassigning raises,
   redeclaring in the same scope raises. Deliberately simpler than `let`
   (no destructuring or captured-think forms).
4. ✅ **Spread syntax for lists and dicts** — `[...a, ...b]` and
   `{...a, ...b}`, including mixed spread+literal items and last-write-wins
   on overlapping dict keys.
5. ✅ **Optional chaining (`?.`)** — `user?.email` and `user?.method()`
   short-circuit to `null` if `user` is `null`, instead of raising. Chains
   correctly (`a?.b?.c`); a plain `.` after a null result still raises,
   matching how optional chaining works elsewhere.
6. ✅ **Enums as a first-class construct** — `enum Status: PENDING,
   ACTIVE, DONE`; each member evaluates to its own name as a string.
7. ✅ **`Set` type** — `{1, 2, 3}` literal syntax, disambiguated from a
   dict literal at parse time (a dict entry always has a `key: value`
   shape; a set element never does — `{}` stays an empty dict, matching
   the existing convention). `set_union`, `set_intersection`,
   `set_difference` builtins; unhashable elements (lists/dicts) raise a
   clear error instead of a raw Python `TypeError`.
8. ✅ **`null` semantics audited** — comparisons (`null == null`,
   `null == false`), truthiness (falsy), arithmetic (`null + 1` raises
   cleanly), and container membership all checked and confirmed
   consistent; no code changes needed beyond what Phase 23a/23b already
   fixed.

**Not done — deferred, not silently dropped:** opt-in `nekova check
--strict` (treating type hints as enforced constraints in the static
checker). This is CLI/tooling work distinct from the language runtime
changes above and deserves its own scoped pass rather than a rushed
addition here.

### Phase 24b · Documentation Website ✅ — v1.10.0

Live at [kinghenesey.github.io/NEKOVA](https://kinghenesey.github.io/NEKOVA/).
28 pages (a scrollytelling landing page plus 27 documentation pages)
generated by a small Python static-site generator
(`docs-site/build.py`) from plain markdown — adding a page means
writing a `.md` file and one line in `content/nav.yaml`, no HTML or
CSS required. Green/white/grey theme pulled directly from the NEKOVA
VS Code color theme, not invented separately; red and amber are
reserved for actual warning/error callouts, matching NEKOVA's own
rule about itself. Every code example on the site was run against
the real interpreter before publishing — several inaccuracies
(a closures example, `?.` behavior, custom error-type syntax) were
caught and fixed this way rather than shipped from memory. Deploys
automatically via GitHub Actions on every push to `main` that
touches `docs-site/`.

---

## Planned Phases

### Phase 25 · AI-Native Differentiators II ✅ — v1.10.0

```nekova
think "..." as text with budget: 500
show ai_usage()

let user = think "extract from: {text}" as User

converse:
    think "ask a clarifying question about {topic}"
    listen
    think "respond based on what they said"

think "..." as text using "claude-sonnet"

imagine "a cat" as file
```

1. ✅ **`think ... as <ShapeName>`** — a previously defined `shape`
   used directly as the output format. Builds an implicit schema
   from the shape's fields; the response comes back type-coerced and
   tagged with the shape's name. Shape names resolve case-insensitively
   against the format identifier, since format identifiers are
   lowercased by the parser (`as JSON` and `as json` mean the same
   thing) but shape names are conventionally capitalized (`User`).
2. ✅ **Cost/token tracking** — `think "..." with budget: 500` raises
   if the estimated tokens exceed the budget; `ai_usage()` returns a
   running `{calls, tokens}` total. Estimated at ~4 characters per
   token — NEKOVA has no real tokenizer for every possible provider.
3. ✅ **Explicit model selection** — `think "..." using "claude-sonnet"`.
4. ✅ **`converse:` blocks** — multi-turn dialogue with a clean
   conversation history per block; `think` and `listen` inside it
   automatically carry prior turns as context.
5. ✅ **`--debug-ai`** — prints the exact prompt sent to the provider
   for every `think` call.
6. ✅ **Sandbox prompt-injection guard** — `think` calls inside a
   `sandbox` block are checked against common injection-style phrases
   and blocked as a sandbox violation if matched. Pattern matching,
   not a real security boundary.
7. ✅ **`imagine ... as file` with local caching** — `file` is now a
   recognized format (alias for `path`); identical `(prompt, format)`
   pairs are cached on disk so a dev loop doesn't regenerate the same
   image repeatedly.
8. ✅ **think's own visible retry/backoff** — two automatic retries
   with a short backoff before falling through to `when error:` or
   the swallow-to-string behavior. Printed to stderr, not stdout, so
   a program's actual output isn't affected.

**Bug fix found along the way:** `self._sandbox_mode` was declared
and checked by the interpreter's operation-blocking guard, but never
actually *set* when entering a sandbox block — meaning `think` was
never really blocked in strict-mode sandboxes despite being on the
blocked-operations list. Fixed as part of building item 6 above.

**Not done — deferred, not silently dropped:** confidence/uncertainty
surfacing for `think ... as bool/json`. Changing what these calls
return would be a breaking change with no real semantic backing in
the mock provider, and deserves proper design rather than a
bolted-on field.

### Phase 26 · Developer Experience ✅ — v1.11.0

```
nekova fmt myfile.nk --diff
nekova new                          # interactive wizard
nekova lock                         # nekova.lock
nekova run myfile.nk --why
nekova run myfile.nk --update-snapshots
```
```nekova
test "arithmetic":
    expect_snapshot(compute_total(cart), "total")
```

1. ✅ **A real Language Server Protocol implementation** —
   `nekova lsp`, a hand-rolled JSON-RPC-over-stdio server (no new
   dependency, consistent with the rest of the toolchain being
   hand-written). Diagnostics, hover, and completion all replace what
   was previously syntax-highlighting-only support in the VS Code
   extension:
   - **Diagnostics** — real inline errors from the actual lexer/parser,
     not a separate approximation.
   - **Hover** — resolves the symbol under the cursor: user-defined
     tasks/prompts/classes take priority (pulled from their real
     signature and docstring), then keywords, then builtins.
   - **Completion** — keywords, builtins, and every declared
     task/class/variable in the document; right after `obj.`, method
     completions with lightweight type inference from the object's
     last literal assignment.
   - **VS Code extension wiring** — the extension now spawns
     `nekova lsp` and talks to it for `.nk` files, toggleable via
     `nekova.enableLanguageServer`.
2. ✅ **Multi-error parser recovery** — `Parser.parse()` now catches
   each syntax error, resynchronizes to the next likely statement
   boundary, and keeps going, so a file with several unrelated
   mistakes reports all of them in one pass. Every existing caller
   still gets the exact same single-exception behavior as before; the
   full list rides along on `.all_errors`. A new `parse_best_effort()`
   sibling always returns whatever was successfully parsed rather than
   raising — needed by hover/completion, since the document is very
   often mid-edit and momentarily invalid elsewhere.
3. ✅ **`nekova fmt --diff`** — shows a unified diff of what would
   change, on a single file or a whole directory, without writing
   anything.
4. ✅ **Interactive `nekova new` wizard** — running `nekova new` with
   no project name now prompts for name, template, and optional
   author/description one step at a time, instead of just erroring
   out with a usage hint. Non-interactive usage (`nekova new name
   --template x`) is unaffected.
5. ✅ **`nekova.lock`** — a committed, reproducible snapshot of the
   exact resolved version of every declared dependency. `nekova lock
   --check` detects drift (for CI) without writing anything.
6. ✅ **`--why`** — walks the actual exception's traceback to name the
   specific internal lexer/parser/interpreter function and line that
   raised it, e.g. `raised in _exec_Identifier() at interpreter.py:2203`.
   Works uniformly for any error type, opt-in, silent by default.
7. ✅ **`expect_snapshot(value, name)`** — snapshot testing for
   AI-output tests where writing out the exact expected value by hand
   isn't practical. First run saves the baseline; later runs compare
   against it and fail on drift. `--update-snapshots` accepts a
   changed value as the new baseline. Plugs into the same test-block
   pass/fail counting as a regular `expect`.
8. ✅ **`.env.example` scaffolding** — every template now includes
   one; the `default` template didn't have one at all before this.

**Bugs found along the way (fixed as part of this phase, not deferred):**
- The parser's "keyword as identifier" fallback (meant for cases like
  a task named `repeat`) was a denylist broad enough to also swallow
  genuine punctuation errors — a bare `)` silently became a bogus
  empty identifier instead of raising. Discovered while building
  multi-error recovery; narrowed to a proper keyword allowlist.
- `Token.column` is 1-indexed and points at the position *after* a
  token ends, not its start — confirmed directly against the lexer
  rather than assumed. Fixed the resulting off-by-token-width position
  math in both hover and diagnostics.
- Every terminal command in the VS Code extension (Run, Format, Check,
  Debug, REPL, New Project — all of them) was non-functional: they
  called `python -m nekova`, but `nekova/` has no `__main__.py`.
  Switched to `-m nekova_cli`, the real module the installed console
  script itself delegates to.
- The extension's `package-lock.json` referenced a dependency version
  that no longer resolves on the npm registry; regenerated from
  scratch.

### Phase 26b · Education Layer — v1.12.0 ✅

```
$ nekova explain err.nk
$ nekova learn
```

This is NEKOVA's actual differentiator versus every other "AI-native
language" claim — the project's own origin story is helping classmates who
were tripped up learning Python. `nekova explain` walks through why an
error happened in plain language: a deterministic template per error type,
plus an optional one-sentence addition from `think` itself (on-brand —
gracefully omitted if that fails, never blocking the deterministic part).
`nekova learn` is a guided, interactive tutorial mode in the terminal —
five lessons, each checked by running the learner's real code against the
real interpreter. Also shipped: the visual debugger's call-stack view now
renders as stacked ASCII boxes instead of a flat arrow list; two new
proactive `nekova check` warnings (W010 — comparing to a boolean literal,
W011 — float equality); `nekova translate script.py`, a best-effort
Python-to-NEKOVA translator built on Python's own `ast` module, with
unsupported constructs flagged inline rather than silently dropped; a
`nekova help <topic>` glossary reachable both from the CLI and inside the
REPL; a `--simple-errors` flag that strips error output to plain sentences
with no error code or box-drawing header; and `nekova classroom <dir>`,
which batch-grades student submissions against a reference solution with
a timeout backstop per submission.

### Phase 26c · AI-Native Differentiators III — v1.13.0 ✅

```
$ nekova run agent.nk --record-ai calls.json
$ nekova run agent.nk --replay-ai calls.json
```

Six features chosen specifically for being differentiators of "AI as a
first-class language citizen" rather than generic features with an AI
label stuck on. `think "..." as User` now actually validates the AI's
response against the shape (missing required fields, wrong types) and
re-prompts with the specific problems named before giving up — previously
a missing field just silently became `None`. `test "label" repeat 10
times, expect at least 8 passes:` is a new test-block form for behavior
that isn't meaningfully pass/fail on a single run, which no mainstream
language has as a built-in construct. Budgets can be dollar amounts
(`with budget: $0.01`) as well as token counts, and
`using ["model-a", "model-b", "local-model"]` gives a fallback chain as
grammar rather than something every AI app hand-rolls — building this
also surfaced and fixed a real gap where the real providers were
hardcoding their model and silently ignoring `using` entirely.
`--record-ai` / `--replay-ai` formalizes the existing mock-provider idea
into genuine deterministic replay: record real responses once, replay
them in CI with no API key and no spend, failing fast (not retrying) on
a cassette miss since that's deterministic, not transient.
`sandbox strict allow: [search_web, send_email]:` extends the sandbox
infrastructure from Phase 19/25 to per-call capability scoping — an
agent's blast radius provably limited by the grammar, not by convention.
And `for chunk in think_stream("..."):` is genuinely lazy — the loop body
processes each chunk as it arrives rather than waiting for the full
response, verified by breaking after 2 of 5 chunks and confirming only
2 were ever pulled from the underlying generator.

### Phase 27 · NEKOVA Parser in NEKOVA — v2.0.0 📋

Self-hosting milestone 2. The parser is recursive descent — more complex
than the lexer. Two prerequisites, not afterthoughts: a **published formal
grammar (EBNF)** as the stable reference this phase implements against, and
a **fuzz-testing harness** feeding malformed input through the lexer/parser
in CI, so this phase surfaces crashes on bad input before it ships rather
than after. When Phase 27 ships, v2.0 commits to backward compatibility.

### Phase 28 · Agent System + Unified Schema — v2.1.0 📋

```nekova
let researcher = agent "Research Assistant":
    tools: [web_search, summarize]
    model: "gpt-4o"

schema Person:
    name: text
    age:  number
# Works as AI parser, DB table, and object type simultaneously
```

### Phase 29 · Sandbox API + Ecosystem — v2.2.0 📋

Sandbox as a deployable commercial API. `nekova teach` — AI-powered
interactive tutorials built into the CLI. Also: middleware support in the
web router (`route GET "/x" with auth, logging:`), WebSocket support
alongside HTTP `route`/`serve`, built-in static file serving, database
migrations as a language feature rather than raw `db_connect`/`query`,
concrete one-command deploy targets (`nekova deploy --target render`), and
marketplace package signing/verification as the package ecosystem grows.

### Phase 30 · Safety & Performance Hardening — v2.3.0 📋

Resource-limited sandbox quotas beyond time (CPU/memory ceilings for
`sandbox strict`, not just execution duration — untrusted-code execution is
an explicit stated feature and deserves real limits). Bytecode caching
(`.nkc`) persisting compiled bytecode between runs, the way Python's
`__pycache__` speeds up repeated execution. A public test-suite dashboard —
"1,226 tests passing" becomes an actual trust signal, not just a number,
once anyone can see which phases and features it actually covers.

### Phase 31 · Full Self-Hosting — v3.0.0 🎯

`lexer.nk` → `parser.nk` → `interpreter.nk`. NEKOVA interprets itself. This is the proof.

---

## The Numbers

| Metric | Value |
|--------|-------|
| Test phases | 29 |
| Tests passing | 1,358 / 1,358 |
| Version | 1.10.0 |
| PyPI package | `nekova-lang` |
| VS Code extension | ✅ Published |
| Documentation site | ✅ Live — kinghenesey.github.io/NEKOVA |
| Self-hosting blockers | 0 remaining |
| Self-hosting status | Phase 20 complete (lexer) — Phase 27 next (parser) |
| Commercial story | Phase 19 Sandbox — live |
| Critical bugs fixed | 39 of 39 |

---

*Last updated: July 2026 · SYNEKCOT Tech · Nigeria 🇳🇬*  
*Built with NEKOVA · Documented with intent*