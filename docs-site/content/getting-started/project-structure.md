---
title: Project Structure
lede: How a NEKOVA project is laid out, and the files the CLI generates for you.
---

## Scaffolding a new project

```bash
nekova new my-project
cd my-project
```

This creates:

```
my-project/
├── main.nk              ← entry point
├── nekova.toml           ← project config (name, entry point, dependencies)
├── .env.example          ← expected AI provider environment variables
└── tests/
    └── test_main.nk      ← starter test file
```

## nekova.toml

The project's manifest — analogous to `pyproject.toml` or `package.json`:

```toml
[project]
name = "my-project"
version = "0.1.0"
entry = "main.nk"

[dependencies]
# packages installed via `nekova install <name>`
```

## Running your project

```bash
nekova run main.nk
```

Or, from inside a scaffolded project directory, just:

```bash
nekova run
```

which reads `entry` from `nekova.toml` automatically.

## Running tests

```nekova
test "greet returns the right shape":
    expect greet("Ada") == "Hello, Ada"
```

```bash
nekova test
```

runs every `test` block found in the project.

## The REPL

```bash
nekova repl
```

Starts an interactive session with command history persisted between sessions.