# =============================================================
# NEKOVA AI Runtime — Package Init
# =============================================================
# Makes the AI module importable from anywhere like:
#   from ai import load_ai_module

from ai.ai_module import load
from ai.providers import get_provider, get_provider_by_name


def load_ai_module() -> dict:
    """Load all AI functions into the NEKOVA environment."""
    return load()