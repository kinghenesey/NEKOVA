# =============================================================
# NEKOVA AI Runtime — Base Provider
# =============================================================

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Default timeout in seconds for all AI provider calls.
# Can be overridden per-call via the timeout parameter.
DEFAULT_THINK_TIMEOUT = 30


class BaseProvider(ABC):
    """Abstract base class for all NEKOVA AI providers."""

    def __init__(self):
        # Memory system — stores conversation history
        self.memory = []
        self.memory_enabled = False
        # Timeout in seconds for ask() / stream() calls.
        # Set to None to disable the timeout entirely.
        self.timeout = DEFAULT_THINK_TIMEOUT

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

    def _with_timeout(self, fn, *args, timeout=None):
        """
        Run fn(*args) in a thread with a timeout guard.
        Raises RuntimeError with a friendly message if the call
        takes longer than timeout seconds (default: self.timeout).
        Passes through if timeout is None (disabled).
        """
        limit = timeout if timeout is not None else self.timeout
        if limit is None:
            return fn(*args)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn, *args)
            try:
                return future.result(timeout=limit)
            except FuturesTimeout:
                future.cancel()
                raise RuntimeError(
                    f"The AI provider timed out after {limit}s.\n"
                    f"  The provider may be slow or unreachable.\n"
                    f"  Try again, or set a longer timeout in nekova.toml:\n"
                    f"      think_timeout = 60"
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