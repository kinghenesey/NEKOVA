# =============================================================
# NEKOVA AI Runtime — Cassette Record/Replay  (Phase 26c)
# =============================================================
# Formalizes the existing mock-provider idea into a real fix for
# "AI features are hard to test cheaply": record real provider
# responses once, replay them afterward with no API key and no
# spend. Deliberately scoped to .ask() alone — that's the single
# method every think call actually routes through (plain `think`
# calls it directly; `think ... as <format>` goes through it via
# ask_structured), so wrapping just that one method gives full
# coverage of NEKOVA's actual AI surface without needing to touch
# every provider method individually.
#
# Cassette file format — plain JSON, one entry per unique prompt:
#   {
#     "<sha256 of prompt>": {
#       "prompt": "...",     (kept for human-readability/debugging)
#       "response": "..."
#     },
#     ...
#   }
# =============================================================

import hashlib
import json
import os


class CassetteMissError(RuntimeError):
    """
    Raised when replay mode can't find a recorded response for a
    prompt. Deliberately a distinct exception type (not a plain
    RuntimeError) so _call_ai_with_visible_retry can recognize it
    and fail immediately instead of burning through retry attempts
    and backoff delays on something that will never succeed no
    matter how many times it's retried — a cassette miss is
    deterministic, not a transient network blip.
    """
    pass


def _prompt_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class CassetteProvider:
    """
    Wraps a real (or mock) provider. In "record" mode, every real
    .ask() call is made normally and its prompt/response pair is
    saved to the cassette file. In "replay" mode, .ask() never
    touches the wrapped provider at all — it looks the prompt up in
    the cassette and returns the recorded response, raising a clear
    error if that exact prompt was never recorded.

    Every other attribute/method (name, model, timeout, is_available,
    summarize, classify, ...) passes straight through to the wrapped
    provider via __getattr__, so a CassetteProvider is a drop-in
    replacement anywhere a normal provider is used.
    """

    def __init__(self, inner_provider, cassette_path: str,
                 mode: str = "replay"):
        if mode not in ("record", "replay"):
            raise ValueError(f"Cassette mode must be 'record' or "
                              f"'replay', got '{mode}'.")
        self._inner = inner_provider
        self._path = cassette_path
        self._mode = mode
        self._cassette = self._load()
        self._dirty = False

    def _load(self) -> dict:
        if not os.path.isfile(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._cassette, f, indent=2, ensure_ascii=False)

    def ask(self, prompt: str) -> str:
        key = _prompt_key(prompt)

        if self._mode == "record":
            response = self._inner.ask(prompt)
            self._cassette[key] = {"prompt": prompt, "response": response}
            self._dirty = True
            self._save()
            return response

        # replay mode
        entry = self._cassette.get(key)
        if entry is None:
            raise CassetteMissError(
                f"No recorded AI response for this prompt in cassette "
                f"'{self._path}'.\n"
                f"  Prompt (first 80 chars): {prompt[:80]!r}\n"
                f"  Re-run with --record-ai {self._path} to capture a "
                f"real response for it, or check whether the prompt "
                f"changed since the cassette was recorded."
            )
        return entry["response"]

    def __getattr__(self, name):
        # Anything not explicitly defined on CassetteProvider itself
        # (model, timeout, name, is_available, summarize, classify,
        # stream, ...) passes straight through to the wrapped
        # provider — only .ask() is intercepted for record/replay.
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        # provider.model = "..." (from a `using` clause) needs to
        # reach the *wrapped* provider, not shadow it on this
        # wrapper object, or a real record pass would silently keep
        # using the wrapped provider's original default model.
        if name in ("_inner", "_path", "_mode", "_cassette", "_dirty"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._inner, name, value)