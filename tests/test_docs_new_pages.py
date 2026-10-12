"""
Docs-site verification — Phase 28 pages.

The docs site's standing rule is that every code example is verified
against the real interpreter before publishing. That was a manual
discipline until now. This file makes it mechanical for the pages
written for Phase 28 (`schema`, Agents, and the call-site-spread
section of Functions & Tasks): every ```nekova block on them is

  1. executed through the real lexer/parser/interpreter, and
  2. parsed by BOTH the Python reference parser and the self-hosted
     parser.nk, asserting the two trees agree.

So a docs example that rots (a renamed builtin, a changed error, a
syntax tweak) turns the build red instead of quietly misleading a
reader, and the examples double as extra cross-parser parity inputs.

Only these pages are covered — most older pages deliberately contain
non-runnable fragments (network calls, real-API `think`, `serve`),
which can't be executed offline.
"""
import contextlib
import io
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CONTENT = os.path.join(REPO_ROOT, "docs-site", "content")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
FENCE = re.compile(r"```nekova\n(.*?)```", re.S)


def _read(rel):
    with open(os.path.join(CONTENT, rel), encoding="utf-8") as f:
        return f.read()


def _blocks(rel, section=None):
    """Every ```nekova block in a page — or only those under one `## `
    heading when `section` is given."""
    text = _read(rel)
    if section is not None:
        m = re.search(r"^## " + re.escape(section) + r"\n(.*?)(?=^## |\Z)",
                      text, re.S | re.M)
        assert m, f"section {section!r} not found in {rel}"
        text = m.group(1)
    return FENCE.findall(text)


def _run(source):
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter
    program = Parser(Lexer(source).tokenize()).parse()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(program)
    return ANSI.sub("", buf.getvalue())


def _parity(source):
    from tests.test_self_hosted_phase28_parity import _asts_match
    return _asts_match(source)


PAGES = [
    ("ai-native/schema.md", None),
    ("ai-native/agents.md", None),
    ("syntax/functions.md", "Spreading arguments into a call"),
]


class TestEveryExampleRuns(unittest.TestCase):
    def test_pages_have_examples(self):
        # Guards the extraction itself: an empty list would make the
        # loops below pass vacuously.
        for rel, section in PAGES:
            self.assertGreaterEqual(len(_blocks(rel, section)), 2, rel)

    def test_every_block_executes(self):
        for rel, section in PAGES:
            for i, src in enumerate(_blocks(rel, section)):
                with self.subTest(page=rel, block=i):
                    _run(src)  # must not raise

    def test_every_block_parses_identically_in_both_parsers(self):
        for rel, section in PAGES:
            for i, src in enumerate(_blocks(rel, section)):
                with self.subTest(page=rel, block=i):
                    same, py, nk = _parity(src)
                    self.assertTrue(same, "parsers disagree on a docs example")


class TestDocumentedOutputs(unittest.TestCase):
    """Where a page states what an example prints, assert it."""

    def test_schema_object_type(self):
        src = next(b for b in _blocks("ai-native/schema.md")
                   if "let alice" in b)
        self.assertEqual(_run(src).split(), ["Alice", "25.0"])

    def test_schema_as_ai_parser_returns_each_field(self):
        src = next(b for b in _blocks("ai-native/schema.md")
                   if "as Review" in b)
        out = _run(src).split()
        self.assertEqual(len(out), 2)           # verdict, score
        self.assertEqual(out[1], "42.0")        # mock number

    def test_schema_database_table_contains_the_row(self):
        src = next(b for b in _blocks("ai-native/schema.md")
                   if "db_create_from_schema" in b)
        out = _run(src)
        self.assertIn("Alice", out)
        self.assertIn("30", out)

    def test_soft_keyword_examples_print_their_values(self):
        out = _run('let schema = "just a variable"\nshow schema\n')
        self.assertEqual(out.strip(), "just a variable")
        out = _run('let agent = "just a variable"\nshow agent\n')
        self.assertEqual(out.strip(), "just a variable")

    def test_spread_totals(self):
        src = _blocks("syntax/functions.md", "Spreading arguments into a call")[0]
        self.assertEqual(_run(src).split(), ["10", "20"])

    def test_decorator_wraps_any_arity(self):
        src = _blocks("syntax/functions.md", "Spreading arguments into a call")[1]
        lines = [l for l in _run(src).splitlines() if l.strip()]
        self.assertEqual(lines, ["calling with 2 args", "11",
                                 "calling with 4 args", "10"])


class TestNavigation(unittest.TestCase):
    def test_every_nav_entry_points_at_a_real_file(self):
        with open(os.path.join(CONTENT, "nav.yaml"), encoding="utf-8") as f:
            files = re.findall(r"^\s+file:\s*(\S+)\s*$", f.read(), re.M)
        self.assertTrue(files)
        for rel in files:
            self.assertTrue(os.path.isfile(os.path.join(CONTENT, rel)),
                            f"nav.yaml points at missing file {rel}")

    def test_new_pages_are_in_the_nav(self):
        with open(os.path.join(CONTENT, "nav.yaml"), encoding="utf-8") as f:
            nav = f.read()
        self.assertIn("ai-native/schema.md", nav)
        self.assertIn("ai-native/agents.md", nav)

    def test_every_page_has_title_and_lede_frontmatter(self):
        for rel in ("ai-native/schema.md", "ai-native/agents.md"):
            head = _read(rel).split("---")[1]
            self.assertIn("title:", head)
            self.assertIn("lede:", head)


if __name__ == "__main__":
    unittest.main()