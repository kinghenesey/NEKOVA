# =============================================================
# NEKOVA AI Runtime â€” AI Module
# =============================================================
# This is what gets loaded when you write "use ai" in NEKOVA.
# It exposes all AI functions to your NEKOVA programs.
#
# Usage in NEKOVA:
#   use ai
#   answer  = ai_ask("What is the capital of Nigeria?")
#   summary = ai_summarize("Long text here...")
#   content = ai_generate("Write a poem about coding")
#   label   = ai_classify("I love NEKOVA!", "positive,negative")
#   show answer

from nekova.ai.providers import get_provider


def load() -> dict:
    """
    Returns all AI functions to be loaded
    into the NEKOVA environment when "use ai" is called.
    """
    # Get the best available provider
    provider = get_provider()

    # Show which provider is active
    _print_provider_info(provider)

    return {
        # Core AI functions
        "ai_ask":      lambda prompt: provider.ask(
                           str(prompt)),
        "ai_summarize": lambda text: provider.summarize(
                           str(text)),
        "ai_generate": lambda instruction: provider.generate(
                           str(instruction)),
        "ai_classify": lambda text, labels: provider.classify(
                           str(text),
                           [l.strip() for l in
                            str(labels).split(",")]
                       ),
        "ai_stream":   lambda prompt: provider.stream(
                           str(prompt)),
        
        # Image generation
        "ai_image":    lambda prompt, filename="generated_image.png": (
                           provider.generate_image(
                               str(prompt), str(filename))
                       ),

        # Memory system
        "ai_remember":  lambda text: provider.remember(
                            str(text)),
        "ai_forget":    lambda: provider.forget(),
        "ai_memory_on": lambda: setattr(
                            provider,
                            'memory_enabled', True),
        "ai_recall":    lambda: provider.get_memory_context(),

        # Provider info
        "ai_provider":  lambda: provider.name,
        "ai_available": lambda: provider.is_available,

        # Utility
        "ai_mock":     lambda prompt: f"[MOCK] {prompt}",
    }


def _print_provider_info(provider):
    """Print which AI provider is active when use ai loads."""
    from nekova.config import Color

    if provider.name == "mock":
        print(
            f"{Color.YELLOW}âš¡ AI Runtime active "
            f"[mock mode]{Color.RESET}"
        )
        print(
            f"{Color.DIM}  Add ANTHROPIC_API_KEY to .env "
            f"for real AI responses.{Color.RESET}"
        )
    else:
        print(
            f"{Color.GREEN}âš¡ AI Runtime active "
            f"[{provider.name}]{Color.RESET}"
        )

