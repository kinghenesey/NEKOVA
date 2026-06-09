# =============================================================
# NEKOVA AI Runtime — Mock Provider
# =============================================================
# The mock provider simulates AI responses without needing
# any API key or internet connection.
#
# It's useful for:
#   - Development and testing
#   - Demos without API costs
#   - Building NEKOVA programs before getting an API key
#
# When you get an API key, just switch the provider to
# "claude" and everything works identically.

from ai.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """
    Simulates AI responses for development and testing.
    Returns realistic-looking fake responses.
    """

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True  # Always available — no key needed

    def ask(self, prompt: str) -> str:
        """Return a mock answer to any question."""
        # Include memory context
        if self.memory:
            facts = [m["content"] for m in self.memory
                     if m["role"] == "user"]
            if facts:
                context = " | ".join(facts[-3:])
                if any(word in prompt.lower()
                       for word in ["what", "who",
                                    "my", "i am", "name"]):
                    return (f"[MOCK with memory] "
                            f"Based on what I know: "
                            f"{context}. "
                            f"Regarding '{prompt}': "
                            f"I remember your context.")

        prompt_lower = prompt.lower()

        # Some realistic mock responses
        if "capital" in prompt_lower and "nigeria" in prompt_lower:
            return "The capital of Nigeria is Abuja."

        if "capital" in prompt_lower:
            return "I can answer questions about world capitals."

        if "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I am NEKOVA's built-in AI assistant."

        if "what is nekova" in prompt_lower:
            return ("NEKOVA is an AI-native programming language "
                    "built with Python. It combines simplicity "
                    "with native AI capabilities.")

        if "who are you" in prompt_lower:
            return ("I am NEKOVA's AI runtime — currently running "
                    "in mock mode. Connect an API key to unlock "
                    "full AI capabilities.")

        if "weather" in prompt_lower:
            return "I cannot check live weather in mock mode."

        if "?" in prompt:
            return (f"[MOCK AI] You asked: '{prompt}' — "
                    f"This is a simulated response. "
                    f"Connect an API key for real answers.")

        return (f"[MOCK AI] Received: '{prompt}' — "
                f"Simulated response active.")
    
    def stream(self, prompt: str) -> str:
        """Simulate streaming with mock responses."""
        import time
        response = self.ask(prompt)
        words    = response.split()

        print(f"\033[96m", end="", flush=True)
        for word in words:
            print(word + " ", end="", flush=True)
            time.sleep(0.05)
        print(f"\033[0m")

        return response
    
    def generate_image(self, prompt: str,
                       filename: str = "generated_image.png") -> str:
        """Mock image generation."""
        import os

        # Create a simple placeholder text file
        mock_path = filename.replace(".png", "_mock.txt")
        with open(mock_path, "w") as f:
            f.write(f"[MOCK IMAGE]\n"
                    f"Prompt: {prompt}\n"
                    f"This would be a real image "
                    f"with an API key.")

        print(f"\033[93m⚡ Mock image created: "
              f"'{mock_path}'\033[0m")
        return mock_path

    def summarize(self, text: str) -> str:
        """Return a mock summary of any text."""
        word_count  = len(text.split())
        char_count  = len(text)
        preview     = text[:60] + "..." if len(text) > 60 else text

        return (f"[MOCK SUMMARY] This text has {word_count} words "
                f"and {char_count} characters. "
                f"It begins with: '{preview}'")

    def generate(self, instruction: str) -> str:
        """Return mock generated content."""
        instruction_lower = instruction.lower()

        if "poem" in instruction_lower:
            return (
                "In lines of code we build our dreams,\n"
                "With NEKOVA's syntax, nothing's hard it seems,\n"
                "Variables flow like rivers wide,\n"
                "With AI as our faithful guide."
            )

        if "function" in instruction_lower or "task" in instruction_lower:
            return (
                "task example(value):\n"
                "    result = value * 2\n"
                "    return result"
            )

        if "list" in instruction_lower:
            return "item1\nitem2\nitem3\nitem4\nitem5"

        return (f"[MOCK GENERATED] Content for: '{instruction}'\n"
                f"Connect an API key to generate real content.")

    def classify(self, text: str, labels: list) -> str:
        """Return a mock classification."""
        # Clean text — remove punctuation and lowercase
        import re
        text_clean = re.sub(r'[^\w\s]', '', text.lower())
        words = set(text_clean.split())

        positive_words = {"good", "great", "love", "excellent",
                          "amazing", "wonderful", "happy", "best"}
        negative_words = {"bad", "terrible", "hate", "awful",
                          "horrible", "sad", "worst", "poor"}

        if "positive" in labels and words & positive_words:
            return "positive"
        if "negative" in labels and words & negative_words:
            return "negative"

        return labels[0] if labels else "unknown"