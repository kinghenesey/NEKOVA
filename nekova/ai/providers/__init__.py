# =============================================================
# NEKOVA AI Runtime — Provider Registry
# =============================================================
# Priority order:
#   1. Gemini  (if GEMINI_API_KEY is set)
#   2. Claude  (if ANTHROPIC_API_KEY is set)
#   3. OpenAI  (if OPENAI_API_KEY is set)
#   4. Mock    (always available as fallback)

from nekova.ai.providers.mock      import MockProvider
from nekova.ai.providers.anthropic import AnthropicProvider
from nekova.ai.providers.gemini    import GeminiProvider
from nekova.ai.providers.openai    import OpenAIProvider


PROVIDERS = [
    GeminiProvider,
    AnthropicProvider,
    OpenAIProvider,
    MockProvider,
]

# Holds the user-selected provider name (set via `model "..."`)
# None means auto-detect from available API keys
_active_provider = None


def get_provider():
    """
    Return the active AI provider.
    If the user has called `model "..."`, use that.
    Otherwise auto-detect from available API keys:
      Gemini → Claude → OpenAI → Mock
    """
    if _active_provider is not None:
        return get_provider_by_name(_active_provider)

    for ProviderClass in PROVIDERS:
        provider = ProviderClass()
        if provider.is_available:
            return provider

    return MockProvider()


def set_provider(name: str):
    """
    Set the active provider by name.
    Called by the `model` keyword in NEKOVA programs.
    Raises ValueError if the name is not recognized.
    """
    global _active_provider

    providers = {
        "mock":      MockProvider,
        "claude":    AnthropicProvider,
        "anthropic": AnthropicProvider,
        "gemini":    GeminiProvider,
        "openai":    OpenAIProvider,
        "gpt":       OpenAIProvider,
    }

    if name not in providers:
        available = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown provider '{name}'.\n"
            f"  Available providers: {available}"
        )

    # Validate the provider is actually available
    provider = providers[name]()
    if not provider.is_available and name != "mock":
        raise ValueError(
            f"Provider '{name}' is not available.\n"
            f"  Make sure the API key is set in your .env file."
        )

    _active_provider = name


def get_provider_by_name(name: str):
    """Get a specific provider by name."""
    providers = {
        "mock":      MockProvider,
        "claude":    AnthropicProvider,
        "anthropic": AnthropicProvider,
        "gemini":    GeminiProvider,
        "openai":    OpenAIProvider,
        "gpt":       OpenAIProvider,
    }

    if name not in providers:
        available = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown provider '{name}'.\n"
            f"  Available providers: {available}"
        )

    return providers[name]()


def reset_provider():
    """
    Reset to auto-detection mode.
    Useful for testing or after a program finishes.
    """
    global _active_provider
    _active_provider = None


def set_think_timeout(timeout: float):
    """
    Set the think timeout on the current active provider.
    Called from _apply_toml_config when nekova.toml is loaded.
    timeout=0 disables the timeout entirely.
    """
    try:
        provider = get_provider()
        provider.timeout = None if timeout <= 0 else float(timeout)
    except Exception:
        pass