---
title: schema
lede: One declaration that works as an object type, an AI response parser, and a database table.
---

## Defining a schema

```nekova
schema Person:
    name: text
    age:  number
```

Each field has a name and a type. The available types are `text`, `number`, `boolean`, `list`, `dict`, and `any`.

## As an object type

Call the schema like a task to build a record — positionally or with keyword arguments:

```nekova
schema Person:
    name: text
    age:  number

let alice = Person("Alice", 30)
let bob = Person(name="Bob", age=25)

show alice["name"]
show bob["age"]
```

A `number` field is stored as a decimal, so `age=25` reads back as `25.0`.

## As an AI parser

Pass the schema's name to `think ... as` and the response is validated and coerced into its fields. If the model's answer doesn't fit, NEKOVA re-prompts instead of handing you malformed data.

```nekova
schema Review:
    verdict: text
    score:   number

let r = think "Review the film Inception" as Review
show r["verdict"]
show r["score"]
```

With no API key configured, the mock provider fills in placeholder values, so this runs offline. The result also carries a `__schema__` entry naming the schema it was parsed against.

## As a database table

`db_create_from_schema` builds a table straight from a schema's fields, so you never spell out column types by hand:

```nekova
use database

schema Person:
    name: text
    age:  number

db_connect(":memory:")
db_create_from_schema(Person, "people")
db_insert("people", "Alice, 30")
show db_find("people", "all")
```

A `boolean` field becomes a boolean column. Passing something that isn't a schema raises a clear error.

## schema or shape?

NEKOVA has both, and they are deliberately separate:

| | `shape` | `schema` |
|---|---|---|
| Type names | `str`, `int`, `float`, `bool` | `text`, `number`, `boolean`, `list`, `dict`, `any` |
| Object type | yes | yes |
| `think ... as Name` | yes | yes |
| Database table | no | yes |

`schema` uses the same type names as the inline form `think "..." as schema {"name": "text"}`, so the two read consistently. `think ... as Name` finds either kind. Use the inline form for a one-off extraction, and a declared `schema` when you want to name the structure and reuse it.

## schema is a soft keyword

`schema` only means "start a definition" when a name and a colon follow it. Anywhere else it's an ordinary identifier, so existing code that uses it as a variable name keeps working:

```nekova
let schema = "just a variable"
show schema
```