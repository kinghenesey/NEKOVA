---
title: Agents
lede: Declare an AI agent with a goal, tools, and a model — no function-call assembly required.
---

## Declaring an agent

Agents live in the `agents` module, so start with `use agents`.

```nekova
use agents

let researcher = agent "Research Assistant":
    goal:  "Summarize topics"
    tools: [summarize, calculate]
    model: "mock"
```

| Field | Meaning | If omitted |
|---|---|---|
| `goal:` | What the agent is for | `"Complete tasks"` |
| `tools:` | A list of tools it may use | no tools |
| `model:` | Which AI model it runs on | the default model |

You can capture the agent in a variable with `let`, as above, or declare it on its own — the agent is registered under its name either way:

```nekova
use agents

agent "Simple Bot":
    goal: "Just talk"

show "declared"
```

## Running an agent

Hand `agent_run` the agent (or its name) and a task:

```nekova
use agents

let helper = agent "Helper":
    goal:  "Answer questions"
    tools: [summarize]
    model: "mock"

let answer = agent_run(helper, "What is 2 + 2?")
show "finished"
```

## Built-in tools

These names work in a `tools:` list without any setup: `search`, `summarize`, `generate`, `classify`, `save`, and `calculate`. `calculate` evaluates arithmetic safely — it is a whitelist-based evaluator, never Python's `eval()`.

## Your own tasks as tools

Name any `task` in scope and the agent can call it. If a task shares a name with a built-in, your task wins.

```nekova
use agents

task shout(text):
    return upper(text) + "!"

let helper = agent "Helper":
    tools: [summarize, shout]
    model: "mock"

show "ready"
```

## Typed tool input

By default a tool receives the agent's entire raw plan text. Give a tool a [schema](schema.html) and it receives only the fields that schema declares, extracted the same way `think ... as` extracts them:

```nekova
use agents

schema CalcInput:
    expression: text

let helper = agent "Helper":
    tools: [calculate(CalcInput)]
    model: "mock"

show "ready"
```

This is the safer way to wire up a tool that expects structured input — it never has to parse free-form plan text itself.

## The function API still works

An `agent` declaration compiles down to the same `agent_create` and `agent_tool` calls the function API uses, so the two styles interoperate freely:

```nekova
use agents

agent_create("Classic", "an older-style agent")
agent_tool("Classic", "summarize", "")

show "ready"
```

## agent is a soft keyword

`agent` only starts a declaration when a quoted name and a colon follow it. Anywhere else it's an ordinary identifier, so a variable named `agent` keeps working:

```nekova
let agent = "just a variable"
show agent
```