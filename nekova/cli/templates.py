# =============================================================
# NEKOVA CLI — Project Templates (Phase 12)
# =============================================================
# Provides template scaffolding for:
#   nekova new myapp --template web
#   nekova new myapp --template ai
#   nekova new myapp --template fullstack
# =============================================================

import os
from nekova.config import NEKOVA_VERSION, NEKOVA_CODENAME

# ── Shared helpers ─────────────────────────────────────────────────────────

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ── Template: default (blank) ──────────────────────────────────────────────

TEMPLATE_DEFAULT_FILES = {
    "src/main.nk": '''\
# {name} — NEKOVA Project
# Created with NEKOVA v{version}

show "Welcome to {name}!"
show "Built with NEKOVA {version} · {codename}"
''',
    "nekova.toml": '''\
[project]
name        = "{name}"
version     = "0.1.0"
author      = "{author}"
description = "{description}"
entry       = "src/main.nk"

[ai]
model   = "claude"
api_key = ""

[dependencies]
packages = []

[run]
strict_types = false
debug        = false
''',
    "README.md": '''\
# {name}

A NEKOVA project.

## Run

```bash
nekova run
```

## Structure

```
{name}/
├── src/
│   └── main.nk
├── tests/
├── nekova.toml
└── README.md
```
''',
    ".gitignore": '''\
__pycache__/
*.pyc
.env
*.nkpkg
dist/
''',
    ".env.example": '''\
# AI provider keys for {name} (used by the [ai] section in nekova.toml)
# Set one of these if you use think/remember/recall:
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
''',
    "tests/.gitkeep": "",
}

# ── Template: web ──────────────────────────────────────────────────────────

TEMPLATE_WEB_FILES = {
    "src/main.nk": '''\
# {name} — NEKOVA Web App
# Template: web · NEKOVA v{version}

route GET "/":
    return "Hello from {name}!"

route GET "/health":
    return "OK"

route POST "/echo":
    return request.body

serve port: 8080
''',
    "src/routes/api.nk": '''\
# API routes for {name}

route GET "/api/status":
    return "{{status: running, app: {name}}}"

route GET "/api/version":
    return "{{version: 0.1.0}}"
''',
    "nekova.toml": '''\
[project]
name        = "{name}"
version     = "0.1.0"
author      = "{author}"
description = "{description}"
entry       = "src/main.nk"

[ai]
model   = "claude"
api_key = ""

[dependencies]
packages = ["requests"]

[run]
strict_types = false
debug        = false

[web]
port = 8080
host = "127.0.0.1"
''',
    "README.md": '''\
# {name}

A NEKOVA web application.

## Run

```bash
nekova run
```

Server starts at http://localhost:8080

## Routes

| Method | Path          | Description |
|--------|---------------|-------------|
| GET    | /             | Home        |
| GET    | /health       | Health check|
| POST   | /echo         | Echo body   |
| GET    | /api/status   | API status  |
| GET    | /api/version  | API version |

## Structure

```
{name}/
├── src/
│   ├── main.nk          ← entry + routes
│   └── routes/
│       └── api.nk       ← API routes
├── tests/
├── nekova.toml
└── README.md
```
''',
    ".gitignore": '''\
__pycache__/
*.pyc
.env
*.nkpkg
dist/
''',
    ".env.example": '''\
# Environment variables for {name}
PORT=8080
''',
    "tests/.gitkeep": "",
}

# ── Template: ai ───────────────────────────────────────────────────────────

TEMPLATE_AI_FILES = {
    "src/main.nk": '''\
# {name} — NEKOVA AI App
# Template: ai · NEKOVA v{version}

# Session memory is built-in
remember "project" as "{name}"
remember "started" as "now"

# Ask the AI a question
think "What can I help you build today?" as text

# Recall something from memory
recall "project"

# Structured AI response
think "List 3 ideas for a new AI feature" as list

# Type-safe schema response
think "Give me a greeting for the user" as json
''',
    "src/agent.nk": '''\
# AI agent example for {name}

task ask_ai(prompt: text):
    think prompt as text

task summarise(content: text):
    think f"Summarise this in one sentence: {{content}}" as text

task classify(text_input: text):
    think f"Classify the sentiment of: {{text_input}}" as json

# Example usage
ask_ai("What is NEKOVA?")
''',
    "nekova.toml": '''\
[project]
name        = "{name}"
version     = "0.1.0"
author      = "{author}"
description = "{description}"
entry       = "src/main.nk"

[ai]
model   = "claude"
api_key = ""

[dependencies]
packages = []

[run]
strict_types = false
debug        = false
''',
    "README.md": '''\
# {name}

A NEKOVA AI-native application.

## Run

```bash
nekova run
```

## AI Features Used

- `think ... as text` — natural language responses
- `think ... as json` — structured JSON output
- `think ... as list` — list responses
- `remember/recall/forget` — session memory

## Setup

Add your AI API key to `.env`:

```
ANTHROPIC_API_KEY=your-key-here
```

## Structure

```
{name}/
├── src/
│   ├── main.nk      ← entry + AI queries
│   └── agent.nk     ← reusable AI tasks
├── tests/
├── nekova.toml
└── README.md
```
''',
    ".gitignore": '''\
__pycache__/
*.pyc
.env
*.nkpkg
dist/
''',
    ".env.example": '''\
# AI provider keys for {name}
# Set one of these:
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
''',
    "tests/.gitkeep": "",
}

# ── Template: fullstack ────────────────────────────────────────────────────

TEMPLATE_FULLSTACK_FILES = {
    "src/main.nk": '''\
# {name} — NEKOVA Fullstack App
# Template: fullstack · NEKOVA v{version}

use json

# AI-powered home route
route GET "/":
    think "Write a one-line welcome message for {name}" as text
    return "Welcome to {name}"

# AI endpoint
route POST "/ai/ask":
    think request.body as text

# DB-backed endpoint
route GET "/items":
    let db = connect("{name}.db")
    let rows = db.query("items")
    return rows

route POST "/items":
    let db = connect("{name}.db")
    db.create("items", "name text, created_at text")
    db.insert("items", request.body)
    return "created"

# Health check
route GET "/health":
    return "{{status: ok, app: {name}}}"

serve port: 8080
''',
    "src/db.nk": '''\
# Database helpers for {name}

task init_db():
    let db = connect("{name}.db")
    db.create("items",   "name text, value text, created_at text")
    db.create("logs",    "level text, message text, ts text")
    db.create("users",   "username text, email text, created_at text")
    show "Database initialised"

task seed_db():
    let db = connect("{name}.db")
    db.insert("items", "demo, hello-world, 2024-01-01")
    show "Seed data inserted"
''',
    "src/ai.nk": '''\
# AI helpers for {name}

remember "app_name" as "{name}"

task generate_response(prompt: text):
    think prompt as text

task analyse_data(data: text):
    think f"Analyse this data and summarise key insights: {{data}}" as json

task classify(input_text: text):
    think f"Classify sentiment: {{input_text}}" as json
''',
    "nekova.toml": '''\
[project]
name        = "{name}"
version     = "0.1.0"
author      = "{author}"
description = "{description}"
entry       = "src/main.nk"

[ai]
model   = "claude"
api_key = ""

[dependencies]
packages = ["requests", "validation"]

[run]
strict_types = false
debug        = false

[web]
port = 8080
host = "127.0.0.1"

[database]
path = "{name}.db"
''',
    "README.md": '''\
# {name}

A NEKOVA fullstack application with AI, web routes, and database.

## Run

```bash
nekova run
```

Server starts at http://localhost:8080

## Stack

- **Web** — `route GET/POST`, `serve port:`
- **AI** — `think ... as json/text/list`, `remember/recall`
- **Database** — `connect()`, `db.create/insert/query`

## Setup

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY
nekova run src/db.nk   # initialise DB
nekova run             # start server
```

## API Routes

| Method | Path        | Description         |
|--------|-------------|---------------------|
| GET    | /           | AI welcome          |
| POST   | /ai/ask     | Ask AI anything     |
| GET    | /items      | List DB items       |
| POST   | /items      | Create DB item      |
| GET    | /health     | Health check        |

## Structure

```
{name}/
├── src/
│   ├── main.nk      ← routes + server
│   ├── db.nk        ← database helpers
│   └── ai.nk        ← AI helpers
├── tests/
├── nekova.toml
└── README.md
```
''',
    ".gitignore": '''\
__pycache__/
*.pyc
.env
*.db
*.nkpkg
dist/
''',
    ".env.example": '''\
# API keys for {name}
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=

# Server
PORT=8080
''',
    "tests/.gitkeep": "",
}

# ── Registry ───────────────────────────────────────────────────────────────

TEMPLATES = {
    "default":   TEMPLATE_DEFAULT_FILES,
    "web":       TEMPLATE_WEB_FILES,
    "ai":        TEMPLATE_AI_FILES,
    "fullstack": TEMPLATE_FULLSTACK_FILES,
}

TEMPLATE_DESCRIPTIONS = {
    "default":   "Blank NEKOVA project",
    "web":       "Web server with GET/POST routes",
    "ai":        "AI-native app with think/remember/recall",
    "fullstack": "Web + AI + SQLite database",
}

# The nekova.toml `description` field's default text if the wizard
# (or a --description flag) doesn't override it — kept separate from
# TEMPLATE_DESCRIPTIONS above (which is the CLI's own "here's what
# this template is" listing text) so switching nekova.toml over to a
# format-string placeholder didn't change what non-interactive
# `nekova new` calls have always written into that field.
_DEFAULT_TOML_DESCRIPTIONS = {
    "default":   "A NEKOVA project",
    "web":       "A NEKOVA web application",
    "ai":        "A NEKOVA AI application",
    "fullstack": "A NEKOVA fullstack application",
}

TEMPLATE_EXTRAS = {
    "default":   [".env.example"],
    "web":       ["src/routes/", ".env.example"],
    "ai":        ["src/agent.nk", ".env.example"],
    "fullstack": ["src/db.nk", "src/ai.nk", ".env.example"],
}


def scaffold_project(project_name: str, template: str = "default",
                      author: str = "", description: str = None) -> bool:
    """
    Create project directory tree from a template.
    Returns True on success.

    author/description let `nekova new`'s interactive wizard (or a
    future --author/--description flag) personalize the generated
    nekova.toml. Non-interactive callers that don't pass them get
    exactly the same defaults as before (empty author, the
    template's own description).
    """
    template = template.lower()
    if template not in TEMPLATES:
        return False

    if description is None:
        description = _DEFAULT_TOML_DESCRIPTIONS.get(template, "A NEKOVA project")

    files = TEMPLATES[template]
    ctx   = dict(name=project_name, version=NEKOVA_VERSION, codename=NEKOVA_CODENAME,
                 author=author, description=description)

    for rel_path, content in files.items():
        abs_path = os.path.join(project_name, rel_path)
        _write(abs_path, content.format(**ctx))

    return True


def list_templates() -> list:
    """Return list of (name, description) tuples."""
    return [(k, TEMPLATE_DESCRIPTIONS[k]) for k in TEMPLATES]