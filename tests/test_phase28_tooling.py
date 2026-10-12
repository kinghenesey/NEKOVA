"""
Phase 28 tooling — editor and CLI awareness of `schema` / `agent`.

Phase 28 shipped the two soft keywords without teaching the tooling
about them. Found afterwards:

  * VS Code TextMate grammar: `schema` was in the plain keyword list,
    so it was highlighted as a keyword EVERYWHERE — including
    `let schema = 1` and `task f(schema):` — while `agent` was never
    highlighted at all.
  * LSP hover: no docs for either.
  * `nekova help`: no glossary entries for either, nor for `...`.

Both are *soft* keywords (still valid variable names), so the fix in
all three places is context-aware recognition that mirrors the
parser's own lookahead, not a plain keyword-list entry.
"""
import contextlib
import io
import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

GRAMMAR_PATH = os.path.join(REPO_ROOT, "nekova-vscode", "syntaxes",
                            "nekova.tmLanguage.json")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _hover(source, line, character):
    from nekova.lsp.hover import compute_hover
    result = compute_hover(source, line, character)
    return result["contents"]["value"] if result else None


class TestHoverSoftKeywords(unittest.TestCase):
    def test_schema_definition_shows_docs(self):
        doc = _hover("schema Person:\n    name: text\n", 0, 2)
        self.assertIsNotNone(doc)
        self.assertIn("typed record", doc)

    def test_agent_declaration_shows_docs(self):
        doc = _hover('agent "Bot":\n    goal: "x"\n', 0, 2)
        self.assertIsNotNone(doc)
        self.assertIn("AI agent", doc)

    def test_captured_agent_declaration_shows_docs(self):
        doc = _hover('let r = agent "Bot":\n    goal: "x"\n', 0, 10)
        self.assertIsNotNone(doc)
        self.assertIn("AI agent", doc)

    def test_variable_named_schema_shows_nothing(self):
        src = "let schema = 1\nshow schema\n"
        self.assertIsNone(_hover(src, 0, 5))
        self.assertIsNone(_hover(src, 1, 6))

    def test_variable_named_agent_shows_nothing(self):
        src = 'let agent = 2\nshow agent\n'
        self.assertIsNone(_hover(src, 0, 5))
        self.assertIsNone(_hover(src, 1, 6))

    def test_parameters_named_like_soft_keywords_show_nothing(self):
        src = "task f(schema, agent):\n    return schema\n"
        self.assertIsNone(_hover(src, 0, 8))
        self.assertIsNone(_hover(src, 0, 16))

    def test_assignment_to_schema_is_not_a_definition(self):
        # `schema = {}` is the exact case the parser's lookahead exists
        # to protect.
        self.assertIsNone(_hover("schema = {}\n", 0, 2))

    def test_inline_think_as_schema_is_not_a_definition(self):
        src = 'let u = think "x" as schema {"a": "text"}\n'
        self.assertIsNone(_hover(src, 0, src.index("schema") + 2))

    def test_existing_keyword_hover_is_unaffected(self):
        doc = _hover('let x = 1\n', 0, 1)
        self.assertIsNotNone(doc)

    def test_soft_keyword_agreement_with_the_parser(self):
        """Hover must call something a definition exactly when the
        parser does."""
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.parser.nodes import SchemaDefinition, AgentDefinition
        cases = [
            ("schema Person:\n    name: text\n", 0, 2, SchemaDefinition),
            ('agent "Bot":\n    goal: "x"\n', 0, 2, AgentDefinition),
            ("let schema = 1\n", 0, 5, None),
            ("let agent = 1\n", 0, 5, None),
        ]
        for src, line, ch, node_type in cases:
            with self.subTest(src=src):
                program = Parser(Lexer(src).tokenize()).parse()
                parsed_as_def = any(isinstance(s, node_type)
                                    for s in program.statements) \
                    if node_type else False
                self.assertEqual(_hover(src, line, ch) is not None,
                                 parsed_as_def)


class TestGlossary(unittest.TestCase):
    def test_entries_exist(self):
        from nekova.cli.glossary import get_topic
        for name in ("schema", "agent", "..."):
            with self.subTest(topic=name):
                entry = get_topic(name)
                self.assertIsNotNone(entry)
                self.assertTrue(entry["summary"])
                self.assertTrue(entry["example"])

    def test_spread_alias(self):
        from nekova.cli.glossary import get_topic
        self.assertIs(get_topic("spread"), get_topic("..."))

    def test_shape_points_at_schema(self):
        from nekova.cli.glossary import get_topic
        self.assertIn("schema", get_topic("shape")["see_also"])

    def test_format_topic_renders(self):
        from nekova.cli.glossary import format_topic
        for name in ("schema", "agent", "spread"):
            self.assertNotIn("No glossary entry", format_topic(name))

    def test_glossary_examples_actually_run(self):
        """Glossary entries are documented as 'real NEKOVA syntax' —
        enforce it for the new ones by executing them."""
        from nekova.cli.glossary import get_topic
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.interpreter.interpreter import Interpreter
        for name in ("schema", "agent"):
            with self.subTest(topic=name):
                program = Parser(Lexer(get_topic(name)["example"]).tokenize()).parse()
                with contextlib.redirect_stdout(io.StringIO()):
                    Interpreter().run(program)

    def test_spread_example_parses(self):
        from nekova.cli.glossary import get_topic
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        Parser(Lexer(get_topic("...")["example"]).tokenize()).parse()


class TestTextMateGrammar(unittest.TestCase):
    """The TextMate engine (Oniguruma) isn't available to the Python
    suite, but these rules use only constructs Python's `re` shares
    (\\b, lookahead, non-capturing groups), so the match regexes can be
    exercised directly. The grammar was also verified against the real
    vscode-textmate engine when this was written."""

    @classmethod
    def setUpClass(cls):
        with open(GRAMMAR_PATH, encoding="utf-8") as f:
            cls.grammar = json.load(f)
        cls.repo = cls.grammar["repository"]

    def _rx(self, rule):
        return re.compile(self.repo[rule]["match"])

    def test_schema_definition_matches_definitions_only(self):
        rx = self._rx("schema_definition")
        self.assertTrue(rx.search("schema Person:"))
        self.assertTrue(rx.search("schema Person :"))
        self.assertEqual(rx.search("schema Person:").group(2), "Person")
        for not_a_def in ("let schema = 1", "show schema", "schema = {}",
                          "task f(schema, agent):",
                          'think "x" as schema {"a": "text"}',
                          'think "x" as Person'):
            with self.subTest(line=not_a_def):
                self.assertIsNone(rx.search(not_a_def))

    def test_agent_definition_matches_definitions_only(self):
        rx = self._rx("agent_definition")
        for a_def in ('agent "Research Assistant":', "agent 'Bot':",
                      'let r = agent "Bot":', 'agent f"Bot {n}":'):
            with self.subTest(line=a_def):
                self.assertTrue(rx.search(a_def))
        for not_a_def in ('agent = "x"', "show agent", "let agent = 1",
                          'agent("x")', "task f(agent):"):
            with self.subTest(line=not_a_def):
                self.assertIsNone(rx.search(not_a_def))

    def test_schema_is_no_longer_a_plain_keyword(self):
        # The original bug: `schema` here highlighted every use of the
        # word as a keyword, including plain variables.
        plain = self.repo["keywords_declaration"]["match"]
        self.assertNotIn("schema", plain)
        self.assertNotIn("agent", plain)

    def test_rules_are_wired_in_before_the_generic_rules(self):
        order = [p.get("include") for p in self.grammar["patterns"]]
        for rule in ("#schema_definition", "#agent_definition"):
            self.assertIn(rule, order)
            self.assertLess(order.index(rule), order.index("#keywords_declaration"))
            self.assertLess(order.index(rule), order.index("#variables"))

    def test_keyword_scope_is_the_declaration_scope(self):
        self.assertEqual(self.repo["agent_definition"]["name"],
                         "keyword.declaration.nekova")
        self.assertEqual(
            self.repo["schema_definition"]["captures"]["1"]["name"],
            "keyword.declaration.nekova")

    def test_think_as_schema_clause_still_handled(self):
        rx = re.compile(self.repo["think_as_clause"]["match"])
        self.assertTrue(rx.search('think "x" as schema {"a": "text"}'))


class TestSnippets(unittest.TestCase):
    def test_new_snippets_exist_and_are_valid(self):
        path = os.path.join(REPO_ROOT, "nekova-vscode", "snippets", "nekova.json")
        with open(path, encoding="utf-8") as f:
            snippets = json.load(f)
        prefixes = set()
        for s in snippets.values():
            pre = s["prefix"]
            prefixes.update(pre if isinstance(pre, list) else [pre])
        self.assertIn("schema", prefixes)
        self.assertIn("agentdecl", prefixes)
        # The pre-existing pipeline snippet keeps its prefix.
        self.assertIn("agent", prefixes)

    def test_snippet_bodies_expand_to_parseable_nekova(self):
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        path = os.path.join(REPO_ROOT, "nekova-vscode", "snippets", "nekova.json")
        with open(path, encoding="utf-8") as f:
            snippets = json.load(f)
        for snippet in snippets.values():
            pre = snippet["prefix"]
            pre = pre if isinstance(pre, list) else [pre]
            if not set(pre) & {"schema", "agentdecl"}:
                continue
            body = "\n".join(snippet["body"])
            # Expand ${n:default} placeholders to their defaults.
            expanded = re.sub(r"\$\{\d+:([^}]*)\}", r"\1", body)
            with self.subTest(prefix=pre):
                Parser(Lexer(expanded).tokenize()).parse()


if __name__ == "__main__":
    unittest.main()