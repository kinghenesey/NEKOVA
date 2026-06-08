# =============================================================
# NEKOVA AI Runtime — Base Provider
# =============================================================

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for all NEKOVA AI providers."""

    def __init__(self):
        # Memory system — stores conversation history
        self.memory = []
        self.memory_enabled = False

    def remember(self, text: str):
        """Add a fact to AI memory."""
        self.memory.append({
            "role":    "user",
            "content": text
        })

    def forget(self):
        """Clear all memory."""
        self.memory = []

    def get_memory_context(self) -> str:
        """Build memory context string for prompts."""
        if not self.memory:
            return ""
        facts = [m["content"] for m in self.memory]
        return (
            "Remember these facts about the user:\n" +
            "\n".join(f"- {f}" for f in facts) +
            "\n\nNow answer this: "
        )

    @abstractmethod
    def ask(self, prompt: str) -> str:
        pass

    @abstractmethod
    def summarize(self, text: str) -> str:
        pass

    @abstractmethod
    def generate(self, instruction: str) -> str:
        pass

    @abstractmethod
    def classify(self, text: str,
                 labels: list) -> str:
        pass

    def stream(self, prompt: str) -> str:
        return self.ask(prompt)
    
    def generate_image(self, prompt: str,
                       filename: str = "generated_image.png") -> str:
        """Generate an image from a text prompt."""
        raise NotImplementedError(
            f"Image generation not supported by "
            f"'{self.name}' provider."
        )

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        pass