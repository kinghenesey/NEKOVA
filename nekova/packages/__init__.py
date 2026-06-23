# =============================================================
# NEKOVA Package Manager — Package Registry  (Phase 11)
# =============================================================

import os
import json

# ── Directory layout ─────────────────────────────────────────
# All installed package modules live in  <repo_root>/packages/
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR     = os.path.dirname(_THIS_DIR)          # repo root
PACKAGES_DIR  = os.path.join(_ROOT_DIR, "packages")
REGISTRY_FILE = os.path.join(PACKAGES_DIR, "registry.json")

os.makedirs(PACKAGES_DIR, exist_ok=True)

# ── Built-in / bundled packages ───────────────────────────────
# Every entry here is available via  nekova install <name>
# without a network connection.

BUILTIN_PACKAGES = {
    # ── Existing ──────────────────────────────────────────────
    "charts": {
        "name":        "charts",
        "version":     "1.0.0",
        "description": "Simple ASCII charts and graphs",
        "author":      "Emmanuel King Christopher",
        "functions":   ["bar_chart", "line_chart", "pie_chart"],
        "category":    "visualisation",
    },
    "auth": {
        "name":        "auth",
        "version":     "1.1.0",
        "description": "Password hashing and token generation",
        "author":      "Emmanuel King Christopher",
        "functions":   ["hash_password", "check_password", "generate_token"],
        "category":    "security",
    },
    "validation": {
        "name":        "validation",
        "version":     "1.0.0",
        "description": "Input validation helpers",
        "author":      "Emmanuel King Christopher",
        "functions":   ["is_email", "is_phone", "is_url", "is_strong_password"],
        "category":    "utilities",
    },
    "colors": {
        "name":        "colors",
        "version":     "1.0.0",
        "description": "Terminal colour and styling utilities",
        "author":      "Emmanuel King Christopher",
        "functions":   ["red", "green", "blue", "yellow", "bold", "dim"],
        "category":    "utilities",
    },
    "random": {
        "name":        "random",
        "version":     "1.0.0",
        "description": "Random number and value generation",
        "author":      "Emmanuel King Christopher",
        "functions":   ["random_int", "random_float", "random_choice", "shuffle"],
        "category":    "utilities",
    },

    # ── Phase 11: New packages ────────────────────────────────
    "requests": {
        "name":        "requests",
        "version":     "1.0.0",
        "description": "Simple HTTP client (GET, POST, PUT, DELETE)",
        "author":      "Emmanuel King Christopher",
        "functions":   ["http_get", "http_post", "http_put",
                        "http_delete", "http_headers"],
        "category":    "networking",
        "requires":    ["requests"],
    },
    "openai": {
        "name":        "openai",
        "version":     "1.0.0",
        "description": "OpenAI GPT integration (chat, embeddings, images)",
        "author":      "Emmanuel King Christopher",
        "functions":   ["gpt_chat", "gpt_complete", "gpt_embed",
                        "gpt_image", "gpt_models"],
        "category":    "ai",
        "requires":    ["openai"],
    },
    "stripe": {
        "name":        "stripe",
        "version":     "1.0.0",
        "description": "Stripe payments (charges, customers, subscriptions)",
        "author":      "Emmanuel King Christopher",
        "functions":   ["stripe_charge", "stripe_customer",
                        "stripe_subscription", "stripe_refund"],
        "category":    "payments",
        "requires":    ["stripe"],
    },
    "sendmail": {
        "name":        "sendmail",
        "version":     "1.0.0",
        "description": "Send emails via SMTP or SendGrid",
        "author":      "Emmanuel King Christopher",
        "functions":   ["send_email", "send_html_email",
                        "email_template"],
        "category":    "communication",
        "requires":    [],
    },
    "csv": {
        "name":        "csv",
        "version":     "1.0.0",
        "description": "Read, write, and process CSV files",
        "author":      "Emmanuel King Christopher",
        "functions":   ["csv_read", "csv_write", "csv_append",
                        "csv_to_dict", "csv_from_dict",
                        "csv_filter", "csv_columns"],
        "category":    "data",
        "requires":    [],
    },
    "slug": {
        "name":        "slug",
        "version":     "1.0.0",
        "description": "URL slug generation and text utilities",
        "author":      "Emmanuel King Christopher",
        "functions":   ["slugify", "truncate", "word_count",
                        "capitalize_words", "strip_html"],
        "category":    "text",
        "requires":    [],
    },
}


# ── Registry helpers ──────────────────────────────────────────

def load_registry() -> dict:
    """Load the local installed-packages registry."""
    if not os.path.exists(REGISTRY_FILE):
        return {}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_registry(registry: dict):
    """Persist the local installed-packages registry."""
    os.makedirs(PACKAGES_DIR, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def is_installed(name: str) -> bool:
    """True if a package is registered AND its file exists."""
    registry = load_registry()
    if name in registry:
        return True
    pkg_file = os.path.join(PACKAGES_DIR, f"{name}.py")
    return os.path.exists(pkg_file)


def get_installed() -> dict:
    return load_registry()


def get_available() -> dict:
    return BUILTIN_PACKAGES


def search_packages(query: str) -> list:
    """
    Search available packages by name, description, or category.
    Returns a list of (name, info) tuples sorted by relevance.
    """
    q = query.lower().strip()
    results = []
    for name, info in BUILTIN_PACKAGES.items():
        score = 0
        if q in name:
            score += 10
        if q in info["description"].lower():
            score += 5
        if q in info.get("category", "").lower():
            score += 3
        if any(q in fn for fn in info.get("functions", [])):
            score += 2
        if score > 0:
            results.append((score, name, info))
    results.sort(reverse=True)
    return [(name, info) for _, name, info in results]