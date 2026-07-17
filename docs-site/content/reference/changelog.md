---
title: Changelog
lede: The highlights of each recent release. For the complete, unabridged history, see CHANGELOG.md in the repository.
---

<div class="callout">
<div class="callout-title">Full history</div>
This page summarizes recent releases. Every release since the project began is documented in <a href="https://github.com/kinghenesey/NEKOVA/blob/main/CHANGELOG.md" target="_blank" rel="noopener">CHANGELOG.md</a> on GitHub.
</div>

## 1.12.0 — Education Layer

`nekova learn` is a guided terminal tutorial that checks your actual code against the real interpreter, not string-matching. `nekova explain file.nk` walks through why an error happened in plain language. `nekova translate script.py` does best-effort Python-to-NEKOVA translation. `nekova classroom` batch-grades a folder of student submissions against a reference solution. A new `nekova help <topic>` glossary works both from the command line and inside the REPL, and `--simple-errors` strips error output down to plain sentences for a beginner audience.

## 1.11.0 — Developer Experience

A real Language Server Protocol implementation (`nekova lsp`) replaces syntax-highlighting-only support in the VS Code extension with live diagnostics, hover docs, and autocomplete — including method completion on `obj.` with lightweight type inference. The parser now recovers from multiple syntax errors in a single pass instead of stopping at the first. Also new: `nekova fmt --diff`, an interactive `nekova new` wizard, `nekova.lock` for reproducible dependencies, a `--why` flag that names the exact internal function that raised an error, `expect_snapshot(...)` for AI-output snapshot testing, and `.env.example` scaffolding for every project template.

## 1.10.0 — Documentation Website + AI-Native Differentiators II

Two phases in one release. The documentation site you're reading now shipped — 28 pages generated from plain markdown, every code example verified against the real interpreter before publishing. Alongside it: `think "..." as <ShapeName>` for typed AI output from a defined shape, cost/token tracking via `with budget:` and `ai_usage()`, explicit model selection with `using`, multi-turn `converse:` blocks, `--debug-ai` for inspecting exact prompts, a prompt-injection guard for `sandbox` blocks, `imagine ... as file` with local disk caching, and visible retry/backoff for `think` calls.

## 1.9.9 — Correctness & Trust Part 2 + Language Completeness II

Two phases shipped together in one release. On the correctness side: indentation errors now report the exact valid depths instead of guessing, and every built-in function (`int()`, `len()`, `range()`, and the rest) was audited so a bad argument can no longer leak a raw Python traceback. On the language side: tuple-style destructuring, keyword arguments, `const` bindings, spread syntax (`[...a, ...b]`), optional chaining (`?.`), enums, and a new `Set` type all landed.

## 1.9.8 — Correctness & Trust Part 1

The first dedicated bug-fix round, scoped directly from feedback on real usage rather than planned features. Recursion errors now report the actual depth reached instead of guessing "infinite recursion." Every mock AI response is tagged so it's never confused with a real model reply. `"5" + 3` raises instead of silently becoming `"53"`. Near-miss variable name suggestions were added using real string-similarity matching.

## 1.9.7 — NEKOVA Dark and Light Themes

Two VS Code color themes built entirely from NEKOVA's own brand palette — green, white, and grey. Red and amber are reserved exclusively for actual errors and warnings in both themes, never used decoratively.

## 1.9.6 — Observability + Testing + Pipe Operator

`observe` blocks for structured tracing, `mock think as <value>` for deterministic AI testing, and the `|>` pipe operator for chaining transformations without nested calls.

## 1.9.5 — Prompt Blocks + Retry/Fallback

Reusable, parameterized `prompt` templates, and `retry`/`fallback` for structured handling of flaky operations.

## 1.9.4 — Self-Hosting: The Lexer

The first piece of NEKOVA's own toolchain written in NEKOVA itself — a lexer, as the opening move toward full self-hosting.

## Earlier phases

Phases 1 through 19 built the core language up from nothing: the interpreter, classes, pattern matching, the AI-native core (`think`, `remember`, `recall`), the package system, and the sandbox. See the full changelog for details on any of them.