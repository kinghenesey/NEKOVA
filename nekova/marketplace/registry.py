# =============================================================
# NEKOVA Marketplace — Package Registry
# =============================================================
# Manages the marketplace package catalog.
# Contains all available community packages with metadata.
#
# In a real production system this would fetch from a remote
# server. For now it's a rich local registry that simulates
# a real marketplace.

import os
import json
from datetime import datetime
from nekova.config import NEKOVA_VERSION


# Registry file path
REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "marketplace_registry.json"
)


# ── Built-in marketplace catalog ──────────────────────────────
# These simulate packages from the community

CATALOG = {
    # ── UI & Design ───────────────────────────────────────────
    "NEKOVA-ui-pro": {
        "name":        "NEKOVA-ui-pro",
        "version":     "2.1.0",
        "description": "Advanced UI components for NEKOVA apps",
        "author":      "NEKOVA Core Team",
        "category":    "ui",
        "downloads":   15420,
        "stars":       234,
        "tags":        ["ui", "components", "design"],
        "functions":   ["modal", "toast", "sidebar",
                        "navbar", "footer"],
    },
    "NEKOVA-charts-pro": {
        "name":        "NEKOVA-charts-pro",
        "version":     "1.3.0",
        "description": "Beautiful charts and data visualizations",
        "author":      "DataViz Team",
        "category":    "data",
        "downloads":   8930,
        "stars":       187,
        "tags":        ["charts", "data", "visualization"],
        "functions":   ["line_chart", "bar_chart",
                        "pie_chart", "scatter_plot"],
    },

    # ── AI & ML ───────────────────────────────────────────────
    "NEKOVA-nlp": {
        "name":        "NEKOVA-nlp",
        "version":     "1.0.0",
        "description": "Natural language processing tools",
        "author":      "AI Labs",
        "category":    "ai",
        "downloads":   6721,
        "stars":       143,
        "tags":        ["nlp", "ai", "text", "language"],
        "functions":   ["tokenize", "sentiment",
                        "extract_keywords", "translate"],
    },
    "NEKOVA-vision": {
        "name":        "NEKOVA-vision",
        "version":     "0.9.0",
        "description": "Computer vision and image processing",
        "author":      "Vision AI",
        "category":    "ai",
        "downloads":   3240,
        "stars":       98,
        "tags":        ["vision", "image", "ai", "cv"],
        "functions":   ["detect_objects", "read_text",
                        "resize_image", "filter_image"],
    },

    # ── Web & API ─────────────────────────────────────────────
    "NEKOVA-rest": {
        "name":        "NEKOVA-rest",
        "version":     "1.5.0",
        "description": "REST API builder with authentication",
        "author":      "Web Dev Team",
        "category":    "web",
        "downloads":   11200,
        "stars":       201,
        "tags":        ["api", "rest", "web", "http"],
        "functions":   ["api_get", "api_post",
                        "api_auth", "api_middleware"],
    },
    "NEKOVA-websocket": {
        "name":        "NEKOVA-websocket",
        "version":     "1.1.0",
        "description": "Real-time WebSocket communication",
        "author":      "RealTime Team",
        "category":    "web",
        "downloads":   4560,
        "stars":       112,
        "tags":        ["websocket", "realtime", "web"],
        "functions":   ["ws_connect", "ws_send",
                        "ws_listen", "ws_broadcast"],
    },

    # ── Database ──────────────────────────────────────────────
    "NEKOVA-orm": {
        "name":        "NEKOVA-orm",
        "version":     "2.0.0",
        "description": "Object-relational mapper for NEKOVA",
        "author":      "DB Team",
        "category":    "database",
        "downloads":   9870,
        "stars":       176,
        "tags":        ["orm", "database", "sql", "models"],
        "functions":   ["model_create", "model_find",
                        "model_save", "model_delete"],
    },

    # ── Utilities ─────────────────────────────────────────────
    "NEKOVA-crypto": {
        "name":        "NEKOVA-crypto",
        "version":     "1.2.0",
        "description": "Cryptography and security utilities",
        "author":      "Security Team",
        "category":    "security",
        "downloads":   7340,
        "stars":       159,
        "tags":        ["crypto", "security", "encryption"],
        "functions":   ["encrypt", "decrypt",
                        "hash_sha256", "generate_key"],
    },
    "NEKOVA-email": {
        "name":        "NEKOVA-email",
        "version":     "1.0.0",
        "description": "Send emails from NEKOVA applications",
        "author":      "Comm Team",
        "category":    "communication",
        "downloads":   5120,
        "stars":       134,
        "tags":        ["email", "smtp", "communication"],
        "functions":   ["send_email", "send_html_email",
                        "email_template"],
    },
    "NEKOVA-pdf": {
        "name":        "NEKOVA-pdf",
        "version":     "1.1.0",
        "description": "Generate and manipulate PDF files",
        "author":      "Document Team",
        "category":    "documents",
        "downloads":   6890,
        "stars":       145,
        "tags":        ["pdf", "documents", "files"],
        "functions":   ["create_pdf", "read_pdf",
                        "merge_pdfs", "add_watermark"],
    },

    # ── Nigeria / Africa specific ─────────────────────────────
    "NEKOVA-naira": {
        "name":        "NEKOVA-naira",
        "version":     "1.0.0",
        "description": "Nigerian Naira currency and payments",
        "author":      "FinTech Nigeria",
        "category":    "finance",
        "downloads":   3210,
        "stars":       87,
        "tags":        ["nigeria", "naira", "payments",
                        "finance"],
        "functions":   ["format_naira", "convert_currency",
                        "paystack_pay", "flutterwave_pay"],
    },
    "NEKOVA-sms-ng": {
        "name":        "NEKOVA-sms-ng",
        "version":     "1.0.0",
        "description": "Send SMS via Nigerian providers",
        "author":      "Telecom Team",
        "category":    "communication",
        "downloads":   2890,
        "stars":       76,
        "tags":        ["sms", "nigeria", "communication"],
        "functions":   ["send_sms", "send_bulk_sms",
                        "check_balance"],
    },
}


def get_catalog() -> dict:
    """Return the full package catalog."""
    return CATALOG


def get_package(name: str) -> dict:
    """Get a specific package by name."""
    return CATALOG.get(name)


def load_installed() -> dict:
    """Load locally installed marketplace packages."""
    if not os.path.exists(REGISTRY_PATH):
        return {}
    try:
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_installed(installed: dict):
    """Save installed packages registry."""
    with open(REGISTRY_PATH, "w") as f:
        json.dump(installed, f, indent=2)


def is_installed(name: str) -> bool:
    """Check if a marketplace package is installed."""
    return name in load_installed()


def mark_installed(name: str, package: dict):
    """Mark a package as installed."""
    installed = load_installed()
    installed[name] = {
        **package,
        "installed_at": datetime.now().isoformat()
    }
    save_installed(installed)


def mark_uninstalled(name: str):
    """Mark a package as uninstalled."""
    installed = load_installed()
    if name in installed:
        del installed[name]
        save_installed(installed)
