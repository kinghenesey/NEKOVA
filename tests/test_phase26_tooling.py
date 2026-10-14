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
        with open(GRAMMAR_PATH, encoding="utf-8-sig") as f:
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
        with open(path, encoding="utf-8-sig") as f:
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
        with open(path, encoding="utf-8-sig") as f:
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


class TestHoverOnDefinitionNames(unittest.TestCase):
    """Hovering the *name* in a definition (and its uses), not just the
    keyword: `Person` in `schema Person:` and the quoted name in
    `agent "Research Assistant":`."""

    SCHEMA_SRC = (
        "schema Person:\n"
        "    name: text\n"
        "    age:  number\n"
        '    note: text = "none"\n'
        "    ok:   boolean = true\n"
        "\n"
        'let p = Person(name="A", age=1)\n'
        'let r = think "x" as Person\n'
    )

    def test_schema_name_at_definition_lists_fields(self):
        doc = _hover(self.SCHEMA_SRC, 0, 9)
        self.assertIn("schema Person", doc)
        self.assertIn("name: text", doc)
        self.assertIn("age: number", doc)

    def test_defaults_are_shown(self):
        doc = _hover(self.SCHEMA_SRC, 0, 9)
        self.assertIn('note: text = "none"', doc)
        self.assertIn("ok: boolean = true", doc)

    def test_schema_name_at_use_sites(self):
        for line, needle in ((6, "Person("), (7, "as Person")):
            col = (self.SCHEMA_SRC.split("\n")[line].index(needle)
                   + needle.index("Person") + 2)
            with self.subTest(line=line):
                doc = _hover(self.SCHEMA_SRC, line, col)
                self.assertIsNotNone(doc)
                self.assertIn("schema Person", doc)

    def test_schema_hover_mentions_all_three_uses(self):
        doc = _hover(self.SCHEMA_SRC, 0, 9)
        self.assertIn("db_create_from_schema", doc)
        self.assertIn("think", doc)

    def test_shape_gets_the_same_treatment(self):
        doc = _hover("shape User:\n    name str\n    age  int\n", 0, 7)
        self.assertIn("shape User", doc)
        self.assertIn("name str", doc)

    AGENT_SRC = (
        "use agents\n"
        'let helper = agent "Research Assistant":\n'
        '    goal:  "Summarize"\n'
        "    tools: [summarize, calculate(CalcInput)]\n"
        '    model: "mock"\n'
        'agent "Bare":\n'
        '    goal: "x"\n'
    )

    def test_agent_name_shows_goal_tools_model(self):
        doc = _hover(self.AGENT_SRC, 1, 20)
        self.assertIn('agent "Research Assistant"', doc)
        self.assertIn('goal:  "Summarize"', doc)
        self.assertIn("tools: summarize, calculate(CalcInput)", doc)
        self.assertIn('model: "mock"', doc)

    def test_agent_name_hover_covers_exactly_the_string(self):
        # `let helper = agent "Research Assistant":` — the string runs
        # from the opening quote (col 19) to the closing quote (col 38).
        line = self.AGENT_SRC.split("\n")[1]
        start, end = line.index('"'), line.rindex('"')
        self.assertIsNone(_hover(self.AGENT_SRC, 1, start - 1))   # the space before
        for col in (start, start + 1, end - 1, end):
            with self.subTest(col=col):
                self.assertIn('agent "Research Assistant"',
                              _hover(self.AGENT_SRC, 1, col))
        self.assertIsNone(_hover(self.AGENT_SRC, 1, end + 1))     # the colon

    def test_captured_agent_mentions_its_variable(self):
        doc = _hover(self.AGENT_SRC, 1, 20)
        self.assertIn("Captured as `helper`", doc)

    def test_bare_agent_hover(self):
        doc = _hover(self.AGENT_SRC, 5, 8)
        self.assertIn('agent "Bare"', doc)
        self.assertIn('agent_run("Bare"', doc)

    def test_string_after_a_variable_named_agent_shows_nothing(self):
        src = 'let agent = "plain"\nshow agent "x"\n'
        self.assertIsNone(_hover(src, 1, 12))

    def test_ordinary_strings_are_unaffected(self):
        self.assertIsNone(_hover('show "hello"\n', 0, 7))

    def test_hover_survives_a_syntax_error_elsewhere(self):
        # parse_best_effort: a definition must still be found while the
        # rest of the file is mid-edit.
        src = self.SCHEMA_SRC + "let broken = (\n"
        self.assertIn("schema Person", _hover(src, 0, 9))

    def test_existing_task_hover_still_works(self):
        doc = _hover("task add(a, b):\n    return a + b\nshow add(1, 2)\n", 0, 6)
        self.assertIn("add", doc)


class TestMoneyLiteralHighlighting(unittest.TestCase):
    """`$0.01` (Phase 26c budgets) was lexed as one MONEY token but
    highlighted as a plain `$` followed by a separately-coloured
    number. One rule now covers the whole literal."""

    @classmethod
    def setUpClass(cls):
        with open(GRAMMAR_PATH, encoding="utf-8-sig") as f:
            grammar = json.load(f)
        rules = grammar["repository"]["numbers"]["patterns"]
        cls.rule = rules[0]
        cls.rx = re.compile(cls.rule["match"])

    def test_money_rule_is_first_so_it_beats_the_digit_rules(self):
        self.assertEqual(self.rule["name"], "constant.numeric.money.nekova")

    def test_matches_what_the_lexer_calls_money(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        for lit in ("$5", "$0.01", "$12.50", "$100"):
            with self.subTest(lit=lit):
                self.assertIsNotNone(self.rx.fullmatch(lit))
                toks = [t for t in Lexer(f"let x = {lit}").tokenize()
                        if t.type == TokenType.MONEY]
                self.assertEqual(len(toks), 1)

    def test_agrees_with_the_lexer_on_trailing_dot(self):
        # `$5.` — the lexer takes `$5` as money and `.` separately.
        self.assertEqual(self.rx.search("$5.").group(0), "$5")

    def test_does_not_match_a_bare_dollar_or_other_numbers(self):
        for s in ("$", "$abc", "5", "3.14", "0x1F"):
            with self.subTest(s=s):
                self.assertIsNone(self.rx.search(s))


class TestShippedJsonHasNoBom(unittest.TestCase):
    """A UTF-8 BOM in a JSON file is invalid JSON: JSON.parse and the
    TextMate engine both reject it, which would break highlighting (or
    `npm`/`vsce`, for the manifests) in the published extension. Windows
    PowerShell's file writers add one by default; this was caught after
    a patch was applied that way, before 2.1.0 shipped."""

    def test_extension_json_files_are_bom_free(self):
        ext = os.path.join(REPO_ROOT, "nekova-vscode")
        checked = 0
        for dirpath, dirnames, filenames in os.walk(ext):
            dirnames[:] = [d for d in dirnames if d != "node_modules"]
            for fname in filenames:
                if fname.endswith(".json"):
                    path = os.path.join(dirpath, fname)
                    with open(path, "rb") as f:
                        head = f.read(3)
                    checked += 1
                    self.assertNotEqual(
                        head, b"\xef\xbb\xbf",
                        f"{os.path.relpath(path, REPO_ROOT)} starts with a "
                        "UTF-8 BOM; strip it (python strip_bom.py). Apply "
                        "patches with `git apply`, not PowerShell redirection")
        self.assertGreaterEqual(checked, 4)

    def test_packaging_is_guarded_by_a_prepublish_check(self):
        """`vsce package` / `vsce publish` run the `vscode:prepublish`
        script first, so wiring the BOM check there makes a BOM'd JSON
        file impossible to publish — independent of anyone remembering
        to run this test suite. (Verified end-to-end with the real vsce:
        with a BOM the build aborts; clean, it packages.)"""
        ext = os.path.join(REPO_ROOT, "nekova-vscode")
        with open(os.path.join(ext, "package.json"), encoding="utf-8-sig") as f:
            scripts = json.load(f).get("scripts", {})
        self.assertIn("vscode:prepublish", scripts)
        self.assertIn("check-json-bom", scripts["vscode:prepublish"])
        script = os.path.join(ext, "scripts", "check-json-bom.js")
        self.assertTrue(os.path.isfile(script), "prepublish script is missing")
        with open(script, encoding="utf-8") as f:
            body = f.read()
        self.assertIn("0xef", body)           # actually inspects the BOM bytes
        self.assertIn("process.exit(1)", body)  # and actually fails the build

    def test_dev_script_is_kept_out_of_the_vsix(self):
        path = os.path.join(REPO_ROOT, "nekova-vscode", ".vscodeignore")
        with open(path, encoding="utf-8-sig") as f:
            lines = [l.strip() for l in f]
        self.assertIn("scripts/", lines)


if __name__ == "__main__":
    unittest.main()