# =============================================================
# NEKOVA CLI — Glossary  (Phase 26b "Education Layer")
# =============================================================
# A single source of truth for "what does this keyword/builtin
# actually do" — backs three surfaces at once:
#   nekova help <topic>        (CLI subcommand)
#   help <topic>                (inside the REPL)
#   nekova learn                (pulls lesson bodies from here)
#
# Every entry's `example` is real NEKOVA syntax — kept in sync
# with the interpreter by hand, same discipline as the docs site
# (verify against the actual running interpreter, don't write
# from memory).
# =============================================================

from nekova.config import Color

GLOSSARY = {
    "let": {
        "summary": "Declares a variable that can be reassigned later.",
        "example": 'let name = "Ada"\nname = "Grace"',
        "see_also": ["const"],
    },
    "const": {
        "summary": "Declares a variable that cannot be reassigned after "
                    "its first value.",
        "example": 'const PI = 3.14159',
        "see_also": ["let"],
    },
    "show": {
        "summary": "Prints a value to the terminal. NEKOVA's version of "
                    "print — works with strings, numbers, lists, and "
                    "f-strings.",
        "example": 'show "Hello, world!"\nshow f"Age: {age}"',
        "see_also": [],
    },
    "task": {
        "summary": "Declares a reusable function. Supports default "
                    "arguments, varargs, keyword arguments, and typed "
                    "signatures.",
        "example": "task greet(name, greeting=\"Hello\"):\n"
                    "    return f\"{greeting}, {name}!\"",
        "see_also": ["return", "async task"],
    },
    "if": {
        "summary": "Conditional branch. Pairs with elif and else, same "
                    "as most languages.",
        "example": "if age >= 18:\n    show \"adult\"\nelse:\n    show \"minor\"",
        "see_also": ["match", "while"],
    },
    "while": {
        "summary": "Loops while a condition stays true.",
        "example": "let i = 0\nwhile i < 3:\n    show i\n    i += 1",
        "see_also": ["for", "if"],
    },
    "for": {
        "summary": "Loops over a list, range, or other iterable.",
        "example": 'for name in ["Ada", "Grace"]:\n    show name',
        "see_also": ["while"],
    },
    "match": {
        "summary": "Pattern-matching branch — clearer than a long "
                    "if/elif chain when checking one value against "
                    "several possibilities. Warns if there's no else arm.",
        "example": "match status:\n"
                    "    when \"ok\": show \"all good\"\n"
                    "    when \"error\": show \"something broke\"\n"
                    "    else: show \"unknown\"",
        "see_also": ["if"],
    },
    "class": {
        "summary": "Declares a class, with support for inheritance, "
                    "docstrings, and custom methods.",
        "example": "class Animal:\n"
                    "    task speak(self):\n"
                    "        return \"...\"\n\n"
                    "class Dog(Animal):\n"
                    "    task speak(self):\n"
                    "        return \"Woof!\"",
        "see_also": ["task"],
    },
    "think": {
        "summary": "NEKOVA's AI-native keyword — sends a prompt to the "
                    "configured AI provider (or the built-in mock "
                    "provider, if none is configured) and returns the "
                    "response. This is the core of what makes NEKOVA "
                    "\"AI-native\": think is a language keyword, not a "
                    "library import.",
        "example": 'result = think "Summarise this document" as json\n'
                    'show result',
        "see_also": ["think as", "remember", "converse", "sandbox"],
    },
    "think as": {
        "summary": "think supports output-format coercion: 'as json', "
                    "'as list', 'as bool', 'as text', or 'as <ShapeName>' "
                    "for a previously defined shape.",
        "example": "shape User:\n"
                    "    name str\n"
                    "    age int\n"
                    "let u = think \"extract from: Ada, 30\" as User",
        "see_also": ["think", "shape"],
    },
    "remember": {
        "summary": "Stores a fact that later think calls can use as "
                    "context, without you having to re-explain it every "
                    "time.",
        "example": 'remember "favourite color" as "green"\n'
                    'think "what is my favourite color?"',
        "see_also": ["recall", "think"],
    },
    "recall": {
        "summary": "Retrieves a previously remembered fact by key.",
        "example": 'recall "favourite color"',
        "see_also": ["remember"],
    },
    "prompt": {
        "summary": "Declares a reusable, parameterized template for "
                    "think calls, so you don't repeat the same wording "
                    "everywhere.",
        "example": "prompt summarise(text):\n"
                    "    \"Summarise this in one sentence: {text}\"\n\n"
                    "think summarise(document) as text",
        "see_also": ["think"],
    },
    "converse": {
        "summary": "A multi-turn dialogue block — every think and "
                    "listen inside it automatically carries the prior "
                    "turns as context, without you managing history "
                    "by hand.",
        "example": "converse:\n"
                    "    think \"ask a clarifying question\"\n"
                    "    listen\n"
                    "    think \"respond based on what they said\"",
        "see_also": ["think", "listen"],
    },
    "sandbox": {
        "summary": "Runs a block under restrictions (strict or relaxed "
                    "mode) — useful for running untrusted or "
                    "AI-generated code safely. Strict mode blocks "
                    "operations like file access and think calls that "
                    "look like prompt injection.",
        "example": "sandbox strict:\n"
                    "    show \"this runs restricted\"",
        "see_also": ["think"],
    },
    "async task": {
        "summary": "Declares an asynchronous task, used with await for "
                    "concurrent work.",
        "example": "async task fetch_data():\n"
                    "    return await get_data(\"https://example.com\")",
        "see_also": ["task", "await"],
    },
    "await": {
        "summary": "Waits for an async task to finish and returns its "
                    "result.",
        "example": "let data = await fetch_data()",
        "see_also": ["async task"],
    },
    "shape": {
        "summary": "Declares a typed data structure — mainly used as a "
                    "target format for think ... as <ShapeName>.",
        "example": "shape User:\n"
                    "    name str\n"
                    "    age int",
        "see_also": ["think as"],
    },
    "error": {
        "summary": "Declares a custom error type, which can then be "
                    "raised and caught like a built-in one.",
        "example": "error NetworkError:\n"
                    "    pass\n\n"
                    "raise NetworkError(\"timed out\")",
        "see_also": [],
    },
    "enum": {
        "summary": "Declares a fixed set of named values.",
        "example": "enum Status:\n"
                    "    ACTIVE\n"
                    "    INACTIVE",
        "see_also": [],
    },
    "|>": {
        "summary": "The pipe operator — chains transformations without "
                    "nesting calls. `a |> f(x)` is the same as `f(a, x)`.",
        "example": "data |> filter(is_even) |> map(double) |> sort()",
        "see_also": ["filter", "map"],
    },
    "?.": {
        "summary": "Optional chaining — safely accesses a property "
                    "that might be null, returning null instead of "
                    "raising if the left side is null.",
        "example": "let city = user?.address?.city",
        "see_also": [],
    },
    "observe": {
        "summary": "A structured-tracing block for debugging — logs "
                    "what happens inside it without changing behaviour.",
        "example": "observe:\n    result = risky_task()",
        "see_also": [],
    },
    "with budget": {
        "summary": "Caps the estimated token cost of a think call, "
                    "raising if it would exceed the budget.",
        "example": 'think "..." with budget: 500',
        "see_also": ["think", "ai_usage"],
    },
    "using": {
        "summary": "Explicitly selects which AI model a think call "
                    "uses.",
        "example": 'think "..." using "claude-sonnet"',
        "see_also": ["think"],
    },
}


def list_topics() -> list:
    """Return every glossary topic name, sorted."""
    return sorted(GLOSSARY.keys())


def get_topic(name: str):
    """
    Look up a glossary entry, case-insensitively, with a couple of
    forgiving aliases for the most obvious near-misses (function ->
    task, def -> task, print -> show) so a beginner coming from
    another language still finds something useful on the first try.
    """
    key = name.strip().lower()

    aliases = {
        "function": "task", "def": "task", "fn": "task",
        "print": "show", "println": "show",
        "elif": "if", "else": "if",
        "for-loop": "for", "loop": "while",
        "ai": "think", "llm": "think",
        "pipe": "|>", "optional": "?.",
    }
    key = aliases.get(key, key)

    return GLOSSARY.get(key)


def format_topic(name: str) -> str:
    """
    Render one glossary entry as a printable string. Returns a
    "not found" message (with near-miss suggestions) rather than
    raising, since this is meant to be forgiving for a beginner
    who might not remember the exact keyword spelling.
    """
    entry = get_topic(name)

    if entry is None:
        import difflib
        suggestions = difflib.get_close_matches(
            name.strip().lower(), list_topics(), n=3, cutoff=0.4
        )
        out = [f"{Color.YELLOW}No glossary entry for '{name}'.{Color.RESET}"]
        if suggestions:
            out.append(f"{Color.DIM}Did you mean: "
                        f"{', '.join(suggestions)}?{Color.RESET}")
        out.append(f"{Color.DIM}Run 'nekova help' to list every "
                    f"topic.{Color.RESET}")
        return "\n".join(out)

    lines = [
        f"{Color.CYAN}{Color.BOLD}{name}{Color.RESET}",
        f"  {entry['summary']}",
        "",
        f"  {Color.DIM}Example:{Color.RESET}",
    ]
    for line in entry["example"].splitlines():
        lines.append(f"  {Color.GREEN}{line}{Color.RESET}")
    if entry.get("see_also"):
        lines.append("")
        lines.append(f"  {Color.DIM}See also: "
                      f"{', '.join(entry['see_also'])}{Color.RESET}")
    return "\n".join(lines)


def format_topic_list() -> str:
    """Render the full list of glossary topics, grouped in columns."""
    topics = list_topics()
    lines = [f"{Color.CYAN}{Color.BOLD}NEKOVA Glossary{Color.RESET}",
             f"{Color.DIM}Run 'nekova help <topic>' for details on "
             f"any of these:{Color.RESET}", ""]
    # Simple 4-per-row layout — plenty readable for ~25 entries.
    row = []
    for topic in topics:
        row.append(f"{topic:<14}")
        if len(row) == 4:
            lines.append("  " + " ".join(row))
            row = []
    if row:
        lines.append("  " + " ".join(row))
    return "\n".join(lines)