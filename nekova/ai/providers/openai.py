# =============================================================
# NEKOVA AI Runtime — OpenAI / GPT Provider
# =============================================================
# Connects NEKOVA to OpenAI's GPT models.
# Get an API key at: https://platform.openai.com
#
# To activate:
#   1. Get an API key from https://platform.openai.com
#   2. Open (or create) the .env file in your NEKOVA folder
#   3. Add this line:  OPENAI_API_KEY=sk-your-key-here
#
# NEKOVA will automatically detect your key and use GPT.
# Priority order: Gemini → Claude → OpenAI → Mock

import os
from nekova.ai.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    Connects NEKOVA to OpenAI's GPT models.
    Requires OPENAI_API_KEY environment variable.
    """

    MODEL      = "gpt-4o-mini"   # Fast and affordable
    MAX_TOKENS = 1024

    def __init__(self):
        super().__init__()
        self.api_key  = os.environ.get("OPENAI_API_KEY", "")
        self._client  = None

    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "The 'openai' package is not installed.\n"
                    "  Run:  pip install openai"
                )
        return self._client

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def ask(self, prompt: str) -> str:
        """Send a question to GPT and return the answer."""
        return self._complete(prompt)

    def summarize(self, text: str) -> str:
        """Ask GPT to summarize a piece of text."""
        prompt = (
            f"Summarize the following text clearly "
            f"and concisely in 2-3 sentences:\n\n{text}"
        )
        return self._complete(prompt)

    def generate(self, instruction: str) -> str:
        """Ask GPT to generate content from an instruction."""
        prompt = (
            f"Generate the following. "
            f"Be concise and direct:\n\n{instruction}"
        )
        return self._complete(prompt)

    def classify(self, text: str, labels: list) -> str:
        """Ask GPT to classify text into one of the labels."""
        labels_str = ", ".join(labels)
        prompt = (
            f"Classify the following text into exactly one "
            f"of these categories: {labels_str}\n\n"
            f"Text: {text}\n\n"
            f"Reply with only the category name, nothing else."
        )
        result = self._complete(prompt)
        result = result.strip().lower()
        for label in labels:
            if label.lower() in result:
                return label
        return labels[0]

    def _complete(self, prompt: str) -> str:
        """
        Core method — sends a prompt to GPT and
        returns the text response. Protected by a timeout.
        """
        if not self.is_available:
            raise RuntimeError(
                "No OpenAI API key found.\n"
                "  Add OPENAI_API_KEY to your .env file.\n"
                "  Get a key at: https://platform.openai.com"
            )

        try:
            full_prompt = prompt  # memory already injected by think_engine
            return self._with_timeout(self._raw_complete, full_prompt)

        except RuntimeError:
            raise

        except Exception as e:
            raise RuntimeError(
                f"OpenAI API error: {str(e)}\n"
                f"  Check your API key and internet connection."
            )

    def _raw_complete(self, full_prompt: str) -> str:
        """Perform the actual blocking HTTP call to the OpenAI API."""
        client   = self._get_client()
        response = client.chat.completions.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        response_text = response.choices[0].message.content

        if self.memory_enabled:
            self.memory.append({
                "role":    "assistant",
                "content": response_text
            })

        return response_text

    def stream(self, prompt: str) -> str:
        """
        Stream a response from GPT word by word.
        Prints text as it arrives.
        """
        if not self.is_available:
            raise RuntimeError(
                "No OpenAI API key found.\n"
                "  Add OPENAI_API_KEY to your .env file."
            )

        try:
            full_prompt = prompt  # memory already injected by think_engine
            client      = self._get_client()

            print("\033[96m", end="", flush=True)

            full_response = []
            stream = client.chat.completions.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                stream=True
            )

            for chunk in stream:
                text = chunk.choices[0].delta.content or ""
                if text:
                    print(text, end="", flush=True)
                    full_response.append(text)

            print("\033[0m")

            response_text = "".join(full_response)

            if self.memory_enabled:
                self.memory.append({
                    "role":    "assistant",
                    "content": response_text
                })

            return response_text

        except Exception as e:
            raise RuntimeError(
                f"OpenAI streaming error: {str(e)}\n"
                f"  Check your API key and internet connection."
            )

    def generate_image(self, prompt: str,
                       filename: str = "generated_image.png") -> str:
        """
        Generate an image using OpenAI's DALL-E 3.
        Falls back to Pollinations if the key lacks image access.
        """
        if not self.is_available:
            raise RuntimeError(
                "No OpenAI API key found.\n"
                "  Add OPENAI_API_KEY to your .env file."
            )

        try:
            import urllib.request
            client = self._get_client()

            print("\033[96m⚡ Generating image with DALL-E...\033[0m",
                  flush=True)

            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                n=1
            )

            image_url = response.data[0].url

            # Download the image
            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                image_data = r.read()

            with open(filename, "wb") as f:
                f.write(image_data)

            print(f"\033[92m✓ Image saved: '{filename}'\033[0m")
            return filename

        except Exception as e:
            raise RuntimeError(
                f"OpenAI image generation failed: {str(e)}\n"
                f"  Check your API key and try again."
            )