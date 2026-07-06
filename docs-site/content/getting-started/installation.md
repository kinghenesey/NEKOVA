---
title: Installation
lede: NEKOVA installs like any other Python package — one command, no separate runtime to manage.
---

## Requirements

NEKOVA runs on top of Python 3.10 or later. You don't need to know Python to write NEKOVA programs, but the interpreter itself is a Python package, so `pip` is how it gets onto your machine.

## Install from PyPI

```bash
pip install nekova-lang
```

This installs the `nekova` command-line tool, which gives you everything: running files, the REPL, the project scaffolder, and the built-in checker.

Verify it worked:

```bash
nekova --version
```

## Your first file

Create a file called `hello.nk`:

```nekova
show "Hello from NEKOVA"
```

Run it:

```bash
nekova run hello.nk
```

## The AI provider

NEKOVA ships with a **mock AI provider** enabled by default, so `think` and friends work immediately with no API key — every mock response is tagged `[MOCK]` so it's never mistaken for a real model reply. This is deliberate: you shouldn't need to sign up for anything to try the language.

When you're ready to use a real model, set the relevant API key as an environment variable (the exact variable name depends on which provider you configure) and NEKOVA will use it automatically. See [`think`](../ai-native/think.html) for details.

## VS Code extension

If you use VS Code, search the marketplace for **"NEKOVA - AI Native Programming Language"** (publisher: SYNEKCOTTech), or install directly:

```bash
code --install-extension SYNEKCOTTech.nekova-lang
```

It adds syntax highlighting, snippets, two color themes built from NEKOVA's own brand palette, and a `.nk` file icon.

<div class="callout">
<div class="callout-title">Next</div>
Head to the <a href="quickstart.html">Quickstart</a> for a guided tour of the language, or jump straight to <a href="../syntax/variables.html">Core Syntax</a> if you'd rather explore on your own.
</div>