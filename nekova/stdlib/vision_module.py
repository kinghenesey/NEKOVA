# =============================================================
# NEKOVA Standard Library — Vision Module
# =============================================================
import os


def _read_image(filepath: str) -> tuple:
    """Read an image file and return (raw_bytes, mime_type)."""
    ext = os.path.splitext(filepath)[1].lower()
    mime_types = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_types.get(ext, "image/jpeg")
    with open(filepath, "rb") as f:
        data = f.read()
    return data, mime


def vision_scan(filepath: str, prompt: str = None) -> str:
    """
    Analyze an image file using Gemini's vision API.

    Usage in NEKOVA:
        description = vision_scan("photo.png")
        detail = vision_scan("chart.png", "What data does this show?")
    """
    if not prompt:
        prompt = "Describe this image in detail."

    if not os.path.isfile(filepath):
        return f"[vision error: file not found: '{filepath}']"

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return f"[vision error: '{filepath}' is not a supported image]"

    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "[vision error: GEMINI_API_KEY not set in .env]"

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        image_bytes, mime_type = _read_image(filepath)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime_type,
                                data=image_bytes
                            )
                        ),
                        types.Part(text=prompt)
                    ]
                )
            ]
        )
        return response.text

    except Exception as e:
        return f"[vision error: {e}]"


def vision_compare(filepath1: str, filepath2: str) -> str:
    """
    Compare two images.

    Usage in NEKOVA:
        result = vision_compare("before.png", "after.png")
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "[vision error: GEMINI_API_KEY not set in .env]"

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        bytes1, mime1 = _read_image(filepath1)
        bytes2, mime2 = _read_image(filepath2)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime1,
                                data=bytes1
                            )
                        ),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime2,
                                data=bytes2
                            )
                        ),
                        types.Part(
                            text="Compare these two images. What are the key differences?"
                        )
                    ]
                )
            ]
        )
        return response.text

    except Exception as e:
        return f"[vision error: {e}]"


def load() -> dict:
    """Return all vision functions for NEKOVA's use statement."""
    return {
        "vision_scan":    vision_scan,
        "vision_compare": vision_compare,
    }