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

# Phase 26c — cassette record/replay state. None means disabled
# (normal behavior). Set via enable_cassette_recording/_replay,
# read by get_provider() to transparently wrap whatever provider
# it would have returned anyway.
_cassette_mode = None   # "record" | "replay" | None
_cassette_path = None


def enable_cassette_recording(path: str):
    """Every real .ask() call from here on is made normally and
    saved to `path`. See nekova/ai/cassette.py."""
    global _cassette_mode, _cassette_path
    _cassette_mode = "record"
    _cassette_path = path


def enable_cassette_replay(path: str):
    """Every .ask() call from here on is served from `path`
    instead of reaching a real provider. See nekova/ai/cassette.py."""
    global _cassette_mode, _cassette_path
    _cassette_mode = "replay"
    _cassette_path = path


def disable_cassette():
    """Return to normal (non-cassette) provider behavior."""
    global _cassette_mode, _cassette_path
    _cassette_mode = None
    _cassette_path = None


def get_provider():
    """
    Return the active AI provider.
    If the user has called `model "..."`, use that.
    Otherwise auto-detect from available API keys:
      Gemini → Claude → OpenAI → Mock

    Phase 26c: if cassette record/replay mode is enabled, the
    provider that would normally be returned gets wrapped in a
    CassetteProvider transparently — every other call site in the
    interpreter keeps working exactly as before, unaware it's
    talking to a cassette instead of a live provider.
    """
    if _active_provider is not None:
        provider = get_provider_by_name(_active_provider)
    else:
        provider = None
        for ProviderClass in PROVIDERS:
            candidate = ProviderClass()
            if candidate.is_available:
                provider = candidate
                break
        if provider is None:
            provider = MockProvider()

    if _cassette_mode is not None:
        from nekova.ai.cassette import CassetteProvider
        return CassetteProvider(provider, _cassette_path, mode=_cassette_mode)

    return provider


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