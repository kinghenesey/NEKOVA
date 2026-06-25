# =============================================================
# NEKOVA AI — Think Engine (Phase 9)
# =============================================================
# Wraps the raw AI provider response with:
#   - Output format enforcement (json / list / bool / schema)
#   - Memory context injection
#   - Conversation history tracking
#   - Schema validation and coercion
# =============================================================

import json as _json
import re   as _re


def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` fences from LLM responses."""
    text = text.strip()
    # Remove ```json or ``` fences
    text = _re.sub(r'^```[a-zA-Z]*\s*', '', text)
    text = _re.sub(r'\s*```$', '', text)
    return text.strip()


def _extract_json(text: str):
    """
    Try to extract the first valid JSON object or array from text.
    Handles cases where the LLM adds extra explanation around the JSON.
    """
    text = _strip_markdown(text)

    # Try direct parse first
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass

    # Try to find JSON object
    for pattern in (r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
                    r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'):
        matches = _re.findall(pattern, text, _re.DOTALL)
        for m in matches:
            try:
                return _json.loads(m)
            except _json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract JSON from response:\n{text[:200]}")


def _extract_list(text: str) -> list:
    """
    Convert an AI response to a Python list.
    Handles JSON arrays and numbered/bulleted text lists.
    """
    text = _strip_markdown(text)

    # Try JSON array
    try:
        val = _json.loads(text)
        if isinstance(val, list):
            return val
    except _json.JSONDecodeError:
        pass

    # Parse line-by-line (numbered list, bullet list, plain list)
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading bullets / numbers
        line = _re.sub(r'^[\d]+[.)\-]\s*', '', line)
        line = _re.sub(r'^[-*•]\s*', '', line)
        if line:
            items.append(line)

    return items


def _extract_bool(text: str) -> bool:
    """Convert an AI response to a boolean."""
    text = text.strip().lower()
    if text in ("true", "yes", "1", "correct", "affirmative"):
        return True
    if text in ("false", "no", "0", "incorrect", "negative"):
        return False
    # Heuristic: does the response lean positive?
    positives = ("yes", "true", "correct", "right", "affirmative",
                 "absolutely", "certainly", "indeed")
    negatives = ("no", "false", "incorrect", "wrong", "negative",
                 "not", "neither")
    pos = sum(1 for w in positives if w in text)
    neg = sum(1 for w in negatives if w in text)
    return pos >= neg


def _coerce_schema(data: dict, schema: dict) -> dict:
    """
    Coerce values in `data` to the types declared in `schema`.
    schema: {"name": "text", "age": "number", "active": "boolean"}
    """
    type_map = {
        "text":    str,
        "str":     str,
        "string":  str,
        "number":  float,
        "int":     int,
        "integer": int,
        "float":   float,
        "boolean": bool,
        "bool":    bool,
        "list":    list,
        "dict":    dict,
    }

    result = {}
    for key, type_name in schema.items():
        if key not in data:
            result[key] = None
            continue
        val = data[key]
        target = type_map.get(str(type_name).lower(), str)
        try:
            if target == bool:
                result[key] = bool(val)
            elif target in (int, float):
                result[key] = target(val)
            else:
                result[key] = target(val)
        except (ValueError, TypeError):
            result[key] = val   # Keep original if coercion fails

    return result


def _build_schema_prompt(prompt: str, schema: dict) -> str:
    """
    Wrap a user prompt with instructions to return JSON matching schema.
    """
    schema_str = _json.dumps(schema, indent=2)
    return (
        f"{prompt}\n\n"
        f"Respond ONLY with a valid JSON object matching this schema "
        f"(no explanation, no markdown):\n{schema_str}"
    )


def _build_format_prompt(prompt: str, fmt: str) -> str:
    """Add format instructions to the prompt."""
    instructions = {
        "json":   "Respond ONLY with valid JSON (no explanation, no markdown fences).",
        "list":   "Respond ONLY with a JSON array of strings (no explanation, no markdown).",
        "bool":   "Respond with only 'true' or 'false' (no explanation).",
        "number": "Respond with only a number (no explanation).",
        "text":   "",  # plain text — no instruction needed
    }
    instr = instructions.get(fmt, "")
    if instr:
        return f"{prompt}\n\n{instr}"
    return prompt


def ask_structured(provider, prompt: str, fmt: str,
                   schema: dict = None, use_memory: bool = True,
                   use_history: bool = True,
                   timeout: float = None):
    """
    Call the AI provider and return a structured result.

    provider:    BaseProvider instance
    prompt:      raw user prompt string
    fmt:         "json" | "list" | "bool" | "schema" | "text" | "number"
    schema:      dict when fmt == "schema"
    use_memory:  inject remembered facts into prompt
    use_history: inject conversation history into prompt
    timeout:     seconds before raising RuntimeError (None = use provider default)
    """
    # Apply per-call timeout override
    if timeout is not None:
        provider.timeout = timeout

    from nekova.ai.memory_store import (
        memory_context, conversation_context, add_to_conversation
    )

    # Build the full prompt with context
    context = ""
    if use_memory:
        context += memory_context()
    if use_history:
        context += conversation_context()

    if fmt == "schema" and schema:
        full_prompt = context + _build_schema_prompt(prompt, schema)
    else:
        full_prompt = context + _build_format_prompt(prompt, fmt)

    # Call the provider
    raw = provider.ask(full_prompt)

    # Record in conversation history
    add_to_conversation("user", prompt)
    add_to_conversation("assistant", raw)

    # Parse the response into the requested format
    try:
        if fmt == "json":
            return _extract_json(raw)
        elif fmt == "schema":
            data = _extract_json(raw)
            if schema and isinstance(data, dict):
                return _coerce_schema(data, schema)
            return data
        elif fmt == "list":
            return _extract_list(raw)
        elif fmt == "bool":
            return _extract_bool(raw)
        elif fmt == "number":
            nums = _re.findall(r"-?\d+(?:\.\d+)?", raw)
            if nums:
                val = float(nums[0])
                return int(val) if val.is_integer() else val
            return 0
        else:
            # "text" or unknown — return raw string
            return raw.strip()
    except Exception as e:
        # Graceful degradation — return raw on parse failure
        return raw.strip()