# =============================================================
# NEKOVA — Fuzz Mutator  (Phase 27 prerequisite)
# =============================================================
# Takes a source string (usually from generator.py, but works on
# any .nk source) and deliberately corrupts it, the way a human
# typo, a bad merge, or truncated file transfer actually would.
# No external dependency (no atheris/hypothesis) — deliberately
# dependency-free so this runs anywhere NEKOVA's own test suite
# already runs, with nothing extra to install in CI.
# =============================================================

import random
import string

MUTATIONS = [
    "delete_char", "delete_line", "duplicate_line", "swap_lines",
    "insert_garbage_char", "insert_random_token", "truncate",
    "corrupt_indentation", "unbalance_bracket", "unbalance_quote",
    "swap_keyword", "insert_unicode", "insert_null_byte",
    "deeply_nest_brackets", "very_long_identifier", "empty_the_file",
]

GARBAGE_CHARS = "!@#$%^&*()[]{}|\\<>~`"
KEYWORDS_TO_SWAP = ["if", "while", "for", "task", "let", "const",
                    "show", "think", "sandbox", "test", "class"]
BRACKETS = ["(", ")", "[", "]", "{", "}"]
QUOTES = ['"', "'"]


def delete_char(src):
    if not src:
        return src
    i = random.randrange(len(src))
    return src[:i] + src[i + 1:]


def delete_line(src):
    lines = src.splitlines()
    if not lines:
        return src
    i = random.randrange(len(lines))
    del lines[i]
    return "\n".join(lines) + "\n"


def duplicate_line(src):
    lines = src.splitlines()
    if not lines:
        return src
    i = random.randrange(len(lines))
    lines.insert(i, lines[i])
    return "\n".join(lines) + "\n"


def swap_lines(src):
    lines = src.splitlines()
    if len(lines) < 2:
        return src
    i, j = random.sample(range(len(lines)), 2)
    lines[i], lines[j] = lines[j], lines[i]
    return "\n".join(lines) + "\n"


def insert_garbage_char(src):
    if not src:
        return random.choice(GARBAGE_CHARS)
    i = random.randrange(len(src))
    return src[:i] + random.choice(GARBAGE_CHARS) + src[i:]


def insert_random_token(src):
    lines = src.splitlines()
    if not lines:
        return src
    i = random.randrange(len(lines))
    token = "".join(random.choices(string.ascii_letters, k=random.randint(1, 8)))
    lines[i] = lines[i] + " " + token
    return "\n".join(lines) + "\n"


def truncate(src):
    if not src:
        return src
    cut = random.randrange(len(src))
    return src[:cut]


def corrupt_indentation(src):
    lines = src.splitlines()
    if not lines:
        return src
    i = random.randrange(len(lines))
    line = lines[i]
    if random.random() < 0.5:
        # Add random extra leading spaces
        lines[i] = " " * random.randint(1, 7) + line
    else:
        # Mix tabs into leading whitespace
        stripped = line.lstrip(" ")
        n_stripped = len(line) - len(stripped)
        lines[i] = "\t" * random.randint(1, 3) + " " * n_stripped + stripped
    return "\n".join(lines) + "\n"


def unbalance_bracket(src):
    i = random.randrange(len(src) + 1)
    return src[:i] + random.choice(BRACKETS) + src[i:]


def unbalance_quote(src):
    i = random.randrange(len(src) + 1)
    return src[:i] + random.choice(QUOTES) + src[i:]


def swap_keyword(src):
    for kw in random.sample(KEYWORDS_TO_SWAP, len(KEYWORDS_TO_SWAP)):
        if kw in src:
            replacement = random.choice(
                [k for k in KEYWORDS_TO_SWAP if k != kw])
            return src.replace(kw, replacement, 1)
    return src


def insert_unicode(src):
    weird = ["\u200b", "\u200e", "\ufeff", "😀", "日本語", "\u0000",
             "\u2028", "\u2029"]
    if not src:
        return random.choice(weird)
    i = random.randrange(len(src))
    return src[:i] + random.choice(weird) + src[i:]


def insert_null_byte(src):
    if not src:
        return "\x00"
    i = random.randrange(len(src))
    return src[:i] + "\x00" + src[i:]


def deeply_nest_brackets(src):
    depth = random.randint(50, 500)
    return "[" * depth + "1" + "]" * random.randint(0, depth)


def very_long_identifier(src):
    long_name = "x" * random.randint(1000, 50000)
    return f"let {long_name} = 1\n" + src


def empty_the_file(src):
    return random.choice(["", "\n", "   ", "\n\n\n", "\t\t\t"])


_MUTATION_FUNCS = {
    "delete_char": delete_char,
    "delete_line": delete_line,
    "duplicate_line": duplicate_line,
    "swap_lines": swap_lines,
    "insert_garbage_char": insert_garbage_char,
    "insert_random_token": insert_random_token,
    "truncate": truncate,
    "corrupt_indentation": corrupt_indentation,
    "unbalance_bracket": unbalance_bracket,
    "unbalance_quote": unbalance_quote,
    "swap_keyword": swap_keyword,
    "insert_unicode": insert_unicode,
    "insert_null_byte": insert_null_byte,
    "deeply_nest_brackets": deeply_nest_brackets,
    "very_long_identifier": very_long_identifier,
    "empty_the_file": empty_the_file,
}


def mutate(src: str, num_mutations: int = 1) -> tuple:
    """
    Apply `num_mutations` random mutations to src in sequence.
    Returns (mutated_source, [mutation_names_applied]) — the list
    is what gets recorded alongside a saved regression, so a future
    reader can see exactly what corruption reproduced a crash.
    """
    applied = []
    for _ in range(num_mutations):
        name = random.choice(MUTATIONS)
        src = _MUTATION_FUNCS[name](src)
        applied.append(name)
    return src, applied