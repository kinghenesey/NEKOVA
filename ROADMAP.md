# NEKOVA Language — Official Roadmap

**Version:** 1.9.6 · Genesis  
**Tests:** 1,226 passing · 200 test classes · 25 test phases  
**Status:** Active development · Phase 22 complete · Phase 23 next  
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
| **1.9.6** | 22 | ✅ `observe` blocks, `mock think`, `\|>` pipe operator — **current** |
| **1.9.7** | 23 | 🔄 **Next** — Correctness & Trust: recursion error accuracy, mock-AI labeling, type-mismatch errors, near-miss variable suggestions, semver policy (this document) |
| **1.10.0** | 24 | Language completeness II — destructuring, optional/nullable types, enums, `const`, spread syntax, named arguments, `null` semantics, sets, opt-in strict type checking |
| **1.10.1** | 24b | Documentation website + language reference |
| **1.11.0** | 25 | AI-native differentiators II — cost/token tracking, `think ... as <shape>`, multi-turn `converse` blocks, explicit model selection, `--debug-ai`, prompt-injection guard for sandboxed `think` |
| **1.12.0** | 26 | Developer experience — Language Server Protocol (real autocomplete, inline errors, hover docs), `nekova fmt --diff`, multi-error parser recovery |
| **1.13.0** | 26b | Education layer — `nekova learn`, `nekova explain`, classroom/instructor mode, `--simple-errors` |
| **2.0.0** | 27 | Parser in NEKOVA — self-hosting milestone 2. Includes a published formal grammar (EBNF) and a parser/lexer fuzz-testing harness in CI, both prerequisites for this phase, not just nice-to-haves |
| **2.1.0** | 28 | Agent system, unified schema |
| **2.2.0** | 29 | Sandbox commercial API, `nekova teach`, deployment targets, WebSocket + middleware support in the web router |
| **2.3.0** | 30 | Safety & performance hardening — resource-limited sandbox quotas (CPU/memory, not just time), bytecode caching, public test-coverage dashboard |
| **3.0.0** | 31 | Full self-hosting — interpreter in NEKOVA |

Phases 27 onward are directional, not fully scoped — near-term phases (23–26b)
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

## Active Phase

### Phase 23 · Correctness & Trust 🔄 IN PROGRESS — v1.9.7

Scoped directly from external feedback on v1.9.5 in live use. Prioritized
first because these fix things that actively mislead learners — which cuts
against NEKOVA's own stated mission — rather than adding new surface area.

1. **Fix the mislabeled recursion error.** `RecursionError` currently maps
   straight to "Infinite Recursion," but it actually fires around 196–198
   NEKOVA-level calls because of Python's own default frame limit combined
   with the interpreter's per-call overhead — not necessarily a missing
   base case. Raise `sys.setrecursionlimit()` at startup and/or track
   NEKOVA's own call depth so the message is accurate, and split "stack
   limit exceeded" from "no base case detected" as distinct diagnoses.
2. **Label every mock AI response.** `MockProvider`'s `"hello"`/`"hi"` and
   capital-city branches currently return clean text with no `[MOCK]` tag,
   unlike every other branch — a beginner's first `think "hello" as text`
   should never be indistinguishable from a real model response.
3. **Add a type-mismatch error for `+` between incompatible types**,
   instead of silently coercing `"5" + 3` → `"53"`. One of the most
   notorious beginner confusion sources in JS-like languages — exactly the
   kind of gotcha NEKOVA shouldn't be reproducing.
4. **Fix "Define it first" echoing typos.** The undefined-variable hint
   currently proposes `let <same_typo> = "value"` — add a near-miss check
   (Levenshtein distance) against existing names and suggest "did you mean
   `<existing_var>`?" the way Python/Rust do.
5. **Document a real semver policy.** Done as part of this update — see
   *Versioning Policy* above.

Also in scope: a specific bad-indentation hint (expected vs. actual depth,
already computable from the token stream), and an audit of the remaining
raw Python exceptions (`TypeError`, `KeyError`, etc.) passed through for
similarly generic or misleading messages.

---

## Planned Phases

### Phase 24 · Language Completeness II — v1.10.0 📋

```nekova
let (a, b) = pair
let {name, age} = user
enum Status: PENDING, ACTIVE, DONE
const MAX_RETRIES = 5
let combined = [...list_a, ...list_b]
greet(name="Sam", greeting="Hi")
```

Destructuring assignment, optional/nullable types with safe-navigation
(`user?.email`), multiple return values, enums as a first-class construct
distinct from `shape`/`error`, `const` bindings alongside `let`, spread/rest
syntax for lists and dicts, named/keyword arguments at call sites, a real
`null` literal with documented comparison/arithmetic/truthiness semantics,
a `set` type with union/intersection/difference, and an opt-in
`nekova check --strict` that treats type hints as real constraints.

### Phase 24b · Documentation Website — v1.10.1 📋

Full language reference site, generated from the same source examples used
in tests where possible, so docs and behavior can't silently drift apart.

### Phase 25 · AI-Native Differentiators II — v1.11.0 📋

```nekova
think "..." as text with budget: 500
show ai_usage()

let user = think "extract from: {text}" as User

converse:
    think "ask a clarifying question about {topic}"
    listen
    think "respond based on what they said"

think "..." as text using "claude-sonnet"
```

Cost/token tracking built into `think`, `think ... as <custom-shape>` with
schema-guided prompting, a structured `converse` block for multi-turn
dialogue, explicit model selection per call, confidence/uncertainty
surfacing for structured extraction, `--debug-ai` extending `observe` to
show the exact prompt sent under the hood (doubles as a teaching tool),
a first-class prompt-injection guard for `sandbox` + `think` combinations,
local caching for `imagine ... as file`, and a visible (not silent)
default backoff for `think` retries.

### Phase 26 · Developer Experience — v1.12.0 📋

A real Language Server Protocol implementation — real autocomplete, inline
errors, and hover docs, replacing syntax-highlighting-only support in the
VS Code extension. Also: `nekova fmt --diff`, multi-error parser recovery
(report several syntax errors per pass instead of halting at the first),
an interactive `nekova new` wizard, a `nekova.lock` dependency lockfile,
a `--why` flag explaining which grammar rule or interpreter check fired,
snapshot testing (`expect_snapshot(...)`) for AI-output tests, and
`.env.example` scaffolding in `nekova new`.

### Phase 26b · Education Layer — v1.13.0 📋

```
$ nekova explain err.nk
$ nekova learn
```

This is NEKOVA's actual differentiator versus every other "AI-native
language" claim — the project's own origin story is helping classmates who
were tripped up learning Python. `nekova explain` walks through why an
error happened in plain language (itself using `think` — on-brand).
`nekova learn` is a guided, interactive tutorial mode in the terminal. Also:
a companion visualization for step-through execution (even simple ASCII
call-stack rendering), proactive common-mistake detection in `nekova check`,
a `nekova translate script.py` mode producing idiomatic `.nk`, an in-REPL
`nekova help think`-style glossary, a `--simple-errors` verbosity flag that
strips jargon entirely, and classroom/instructor batch-grading mode.

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
| Test phases | 25 |
| Test classes | 200 |
| Tests passing | 1,226 / 1,226 |
| Version | 1.9.6 |
| PyPI package | `nekova-lang` |
| VS Code extension | ✅ Published |
| Self-hosting blockers | 0 remaining |
| Self-hosting status | Phase 20 complete (lexer) — Phase 27 next (parser) |
| Commercial story | Phase 19 Sandbox — live |
| Critical bugs fixed | 38 of 38 |

---

*Last updated: July 2026 · SYNEKCOT Tech · Nigeria 🇳🇬*  
*Built with NEKOVA · Documented with intent*