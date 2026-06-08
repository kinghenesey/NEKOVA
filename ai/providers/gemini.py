# =============================================================
# NEKOVA AI Runtime — Google Gemini Provider
# =============================================================
# Uses the new google-genai SDK (replaces google-generativeai)
# Get a free API key at: https://aistudio.google.com

import os
from ai.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """
    Connects NEKOVA to Google Gemini AI.
    Requires GEMINI_API_KEY environment variable.
    """

    MODEL = "gemini-2.5-flash"

    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = None

    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(
                    api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "The 'google-genai' package "
                    "is not installed.\n"
                    "  Run: pip install google-genai"
                )
        return self._client

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def ask(self, prompt: str) -> str:
        return self._complete(prompt)

    def summarize(self, text: str) -> str:
        prompt = (
            f"Summarize the following text clearly "
            f"and concisely in 2-3 sentences:\n\n{text}"
        )
        return self._complete(prompt)

    def generate(self, instruction: str) -> str:
        prompt = (
            f"Generate the following. "
            f"Be concise and direct:\n\n{instruction}"
        )
        return self._complete(prompt)

    def classify(self, text: str,
                 labels: list) -> str:
        labels_str = ", ".join(labels)
        prompt = (
            f"Classify the following text into exactly "
            f"one of these categories: {labels_str}\n\n"
            f"Text: {text}\n\n"
            f"Reply with only the category name."
        )
        result = self._complete(prompt)
        result = result.strip().lower()
        for label in labels:
            if label.lower() in result:
                return label
        return labels[0]

    def _complete(self, prompt: str) -> str:
        """Send a prompt to Gemini and return response."""
        if not self.is_available:
            raise RuntimeError(
                "No Gemini API key found.\n"
                "  Add GEMINI_API_KEY to your .env file.\n"
                "  Get a free key at: "
                "https://aistudio.google.com"
            )

        try:
            from google import genai

            # Add memory context if available
            full_prompt = self.get_memory_context() + prompt

            client   = self._get_client()
            response = client.models.generate_content(
                model=self.MODEL,
                contents=full_prompt
            )

            # Save response to memory if enabled
            if self.memory_enabled:
                self.memory.append({
                    "role":    "assistant",
                    "content": response.text
                })

            return response.text

        except Exception as e:
            raise RuntimeError(
                f"Gemini API error: {str(e)}\n"
                f"  Check your API key and try again."
            )
    
    def stream(self, prompt: str):
        """
        Stream a response from Gemini word by word.
        Prints text as it arrives like ChatGPT.
        """
        if not self.is_available:
            raise RuntimeError(
                "No Gemini API key found.\n"
                "  Add GEMINI_API_KEY to your .env file."
            )

        try:
            from google import genai
            client = self._get_client()

            print(f"\033[96m", end="", flush=True)

            response = client.models.generate_content_stream(
                model=self.MODEL,
                contents=prompt
            )

            full_response = []
            for chunk in response:
                if chunk.text:
                    print(chunk.text,
                          end="", flush=True)
                    full_response.append(chunk.text)

            print(f"\033[0m")
            return "".join(full_response)

        except Exception as e:
            raise RuntimeError(
                f"Gemini streaming error: {str(e)}"
            )
    
    def generate_image(self, prompt: str,
                       filename: str = "generated_image.png") -> str:
        """
        Generate an image from a text prompt.
        Uses Pollinations AI — free, no API key needed.
        """
        import urllib.request
        import urllib.parse
        import time

        print(f"\033[96m⚡ Generating image...\033[0m",
              flush=True)

        encoded = urllib.parse.quote(prompt)
        url     = (f"https://image.pollinations.ai/"
                   f"prompt/{encoded}"
                   f"?width=512&height=512&nologo=true"
                   f"&seed={int(time.time())}")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/png,image/*,*/*",
            }
        )

        # Try up to 3 times
        for attempt in range(3):
            try:
                print(f"\033[96m  Attempt {attempt + 1}/3...\033[0m",
                      flush=True)
                with urllib.request.urlopen(
                        req, timeout=120) as response:
                    image_data = response.read()

                with open(filename, "wb") as f:
                    f.write(image_data)

                print(f"\033[92m✓ Image saved: "
                      f"'{filename}'\033[0m")
                return filename

            except Exception as e:
                if attempt < 2:
                    print(f"\033[93m  Retrying...\033[0m",
                          flush=True)
                    time.sleep(3)
                else:
                    raise RuntimeError(
                        f"Image generation failed "
                        f"after 3 attempts: {str(e)}\n"
                        f"  Try again later."
                    )