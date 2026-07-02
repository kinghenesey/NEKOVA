# NEKOVA Language — Official Roadmap

**Version:** 1.9.3 · Genesis  
**Tests:** 1,177 passing · 188 test classes · 22 test phases  
**Status:** Active development · Phase 20 complete, Phase 21 in progress  
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

## Version Map

| Version | Phase | What Ships |
|---------|-------|-----------|
| 1.9.2 | 19b | Self-hosting blockers fixed, 38 security bugs resolved |
| **1.9.3** | 20 | Current — lexer in NEKOVA, verified token-for-token against the Python reference lexer |
| **1.9.4** | 21 | Prompt blocks, retry/fallback, enforced types |
| **1.9.5** | 22 | Observe, mock think, pipe operator |
| **1.9.6** | 23 | Polish — inline errors, destructuring, docstrings |
| **1.9.7** | 23b | Documentation website + language reference |
| **2.0** | 24 | Parser in NEKOVA — self-hosting milestone 2 |
| **2.5** | 25 | Agent system, unified schema |
| **3.0** | 27 | Full self-hosting — interpreter in NEKOVA |

Version 2.0 is a language milestone, not just a version bump. When the parser is written in NEKOVA, the language is stable enough to commit to backward compatibility. Everything before 2.0 is formative. Everything from 2.0 onward is a platform.

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

## Active Phase

### Phase 20 · Self-Hosting Begins 🔄 IN PROGRESS — v1.4

**Goal:** Write NEKOVA's lexer in NEKOVA. Ship it as `nekova/stdlib/nk/lexer.nk`.

**All prerequisites now available:**
- ✅ String character access `s[i]`
- ✅ String iteration `for c in s:`
- ✅ `.is_alpha()`, `.is_digit()` on strings
- ✅ `ord()` / `chr()`
- ✅ `dict[key] = value` mutable lookup tables
- ✅ `key in dict` membership
- ✅ While loops with index counters
- ✅ Recursive tasks
- ✅ Error raising and catching
- ✅ Multi-line strings
- ✅ `match` with character ranges `when "a".."z":`
- ✅ `raise` inside tasks

**Deliverable:** `nekova/stdlib/nk/lexer.nk` — a real, tested NEKOVA lexer that tokenises NEKOVA source code, written entirely in `.nk`.

**Why this matters:** When a language can write its own lexer, it proves the language is expressive enough to handle real complexity. Python did this. Rust did this. Go did this. NEKOVA is next.

---

## Planned Phases

### Phase 21 · Prompt Blocks + Retry + Enforced Types — v1.5 📋

```nekova
prompt summarize(text, style="professional"):
    """Summarize the following in a {style} tone: {text}"""

retry 3 times with exponential backoff:
    let result = think "analyse this" as json
fallback:
    let result = {error: "unavailable"}
```

### Phase 22 · Observability + Testing + Pipe Operator — v1.6 📋

```nekova
observe "pipeline run" with tags {user: user_id}:
    let summary = think summarize(document)

test "classifier":
    mock think as "sports"
    expect classify(text) == "sports"

let result = data |> parse() |> filter() |> sort() |> take(10)
```

### Phase 23 · Polish + Inline Error Handling — v1.7 📋

```nekova
let summary = think "summarize: {doc}" when error: "unavailable"
let [first, ...rest] = my_list
let {name, age} = my_dict
```

### Phase 24 · NEKOVA Parser in NEKOVA — v2.0 📋

Self-hosting milestone 2. The parser is recursive descent — more complex than the lexer. When it ships, v2.0 commits to backward compatibility.

### Phase 25 · Agent System + Unified Schema — v2.5 📋

```nekova
let researcher = agent "Research Assistant":
    tools: [web_search, summarize]
    model: "gpt-4o"

schema Person:
    name: text
    age:  number
# Works as AI parser, DB table, and object type simultaneously
```

### Phase 26 · Sandbox API + `nekova teach` — v2.5 📋

Sandbox as a deployable commercial API. `nekova teach` — AI-powered interactive tutorials built into the CLI.

### Phase 27 · Full Self-Hosting — v3.0 🎯

`lexer.nk` → `parser.nk` → `interpreter.nk`. NEKOVA interprets itself. This is the proof.

---

## The Numbers

| Metric | Value |
|--------|-------|
| Test phases | 22 |
| Test classes | 188 |
| Tests passing | 1,177 / 1,177 |
| Version | 1.9.3 |
| PyPI package | `nekova-lang` |
| VS Code extension | ✅ Published |
| Self-hosting blockers | 0 remaining |
| Self-hosting status | Phase 20 complete (lexer) — Phase 21 next |
| Commercial story | Phase 19 Sandbox — live |
| Critical bugs fixed | 38 of 38 |

---

*Last updated: June 2026 · SYNEKCOT Tech · Nigeria 🇳🇬*  
*Built with NEKOVA · Documented with intent*