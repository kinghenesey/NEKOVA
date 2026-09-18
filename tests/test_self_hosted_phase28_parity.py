"""
Self-hosted parser — Phase 28 parity (schema / agent).

parser.nk was written during Phase 27, before the `schema` and
`agent` keywords existed. Nothing updated it when Phase 28 shipped
them, so any program using either failed under `--self-hosted` with
"Expected '=' or '(' after 'schema'". Found during a broad
test-everything-in-the-language QA sweep, by cross-checking
tools/diff_parsers.py against a wider variety of programs than just
parser.nk parsing its own source.

Both are *soft* keywords — matched by identifier value plus lookahead,
the way 'prompt' already was — rather than dedicated lexer tokens like
SHAPE. That's why they needed real new dispatch infrastructure in
parser.nk rather than a one-line addition to its existing
parse_field_list_def helper.

The last test class here is the important one long-term: it walks
every .nk file in the repo and asserts both parsers agree, so the
NEXT time a language feature lands in parser.py without a matching
parser.nk update, a test fails instead of the drift going unnoticed.
tools/check_grammar_coverage.py only ever verified the *Python*
parser against GRAMMAR.md — nothing checked the self-hosted parser
stayed in sync with it, which is exactly how this gap survived.
"""
import glob
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _asts_match(source: str):
    """Parse `source` with both the Python reference parser and the
    self-hosted parser, and compare the resulting trees structurally
    (ignoring line numbers) — the same comparison
    tools/diff_parsers.py performs, done in-process."""
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.parser.rehydrate import parse_self_hosted

    py_program = Parser(Lexer(source).tokenize()).parse()
    nk_program = parse_self_hosted(source)

    def serialize(value):
        if hasattr(value, "__dict__"):
            out = {"type": type(value).__name__}
            for key, sub in vars(value).items():
                if key == "line":
                    continue
                out[key] = serialize(sub)
            return out
        if isinstance(value, dict):
            return {k: serialize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [serialize(v) for v in value]
        return value

    return serialize(py_program) == serialize(nk_program), \
        serialize(py_program), serialize(nk_program)


class TestSchemaParity(unittest.TestCase):

    def test_basic_schema(self):
        ok, _, _ = _asts_match(
            'schema Person:\n'
            '    name: text\n'
            '    age:  number\n'
        )
        self.assertTrue(ok)

    def test_schema_with_default(self):
        ok, _, _ = _asts_match(
            'schema Person:\n'
            '    name: text\n'
            '    note: text = "none"\n'
        )
        self.assertTrue(ok)

    def test_schema_soft_keyword_as_variable(self):
        """'schema' used as an ordinary variable name must still
        parse identically in both — the soft-keyword lookahead has to
        agree across the two implementations, not just the happy
        path."""
        ok, _, _ = _asts_match('let schema = 5\nshow schema\n')
        self.assertTrue(ok)


class TestAgentParity(unittest.TestCase):

    def test_bare_agent_statement(self):
        ok, _, _ = _asts_match(
            'agent "Bot":\n'
            '    tools: [summarize]\n'
        )
        self.assertTrue(ok)

    def test_agent_with_all_fields(self):
        ok, _, _ = _asts_match(
            'agent "Bot":\n'
            '    goal:  "Do things"\n'
            '    tools: [summarize, calculate]\n'
            '    model: "gpt-4o"\n'
        )
        self.assertTrue(ok)

    def test_agent_model_field_uses_keyword_token(self):
        """'model' is also a real keyword token (the top-level
        `model "..."` statement), so an agent field key is either an
        IDENTIFIER or that token — both parsers must handle it."""
        ok, _, _ = _asts_match(
            'agent "Bot":\n'
            '    model: "gpt-4o"\n'
        )
        self.assertTrue(ok)

    def test_let_captured_agent(self):
        ok, _, _ = _asts_match(
            'let researcher = agent "Research Assistant":\n'
            '    tools: [summarize]\n'
        )
        self.assertTrue(ok)

    def test_schema_typed_tool_in_agent(self):
        ok, _, _ = _asts_match(
            'schema CalcInput:\n'
            '    expression: text\n'
            'agent "Bot":\n'
            '    tools: [calculate(CalcInput)]\n'
        )
        self.assertTrue(ok)

    def test_agent_soft_keyword_as_variable(self):
        ok, _, _ = _asts_match('let agent = "hello"\nshow agent\n')
        self.assertTrue(ok)


class TestSelfHostedExecution(unittest.TestCase):
    """Parsing agreement isn't the whole story — the rehydrated AST
    has to actually execute correctly through the interpreter too."""

    def test_schema_and_agent_run_under_self_hosted(self):
        source = (
            'use agents\n'
            'schema Person:\n'
            '    name: text\n'
            'let p = Person(name="Alice")\n'
            'show p["name"]\n'
            'agent "Bot":\n'
            '    tools: [summarize]\n'
            'show agent_status("Bot")\n'
        )
        import io
        import contextlib
        from nekova.parser.rehydrate import parse_self_hosted
        from nekova.interpreter.interpreter import Interpreter

        program = parse_self_hosted(source)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            Interpreter().run(program)
        out = buf.getvalue()
        self.assertIn("Alice", out)
        self.assertIn("idle", out)


class TestNoParserDriftAcrossRepo(unittest.TestCase):
    """
    Regression guard for the whole class of bug this file exists for.

    Walks every .nk file actually checked into the repo and asserts
    both parsers produce the same AST. If a future language feature
    lands in parser.py (and gets used in a real .nk file) without a
    matching parser.nk update, this fails — rather than the drift
    sitting unnoticed until someone happens to run --self-hosted.
    """

    def test_every_repo_nk_file_parses_identically(self):
        patterns = [
            os.path.join(REPO_ROOT, "nekova", "stdlib", "nk", "*.nk"),
            os.path.join(REPO_ROOT, "examples", "**", "*.nk"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        self.assertTrue(files, "no .nk files found to check")

        failures = []
        for path in sorted(files):
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            try:
                ok, _, _ = _asts_match(source)
                if not ok:
                    failures.append(f"{os.path.relpath(path, REPO_ROOT)}: AST mismatch")
            except Exception as e:
                failures.append(
                    f"{os.path.relpath(path, REPO_ROOT)}: {type(e).__name__}: {e}"
                )

        self.assertEqual(
            failures, [],
            "Self-hosted parser (parser.nk) disagrees with the Python "
            "reference parser on these files:\n  " + "\n  ".join(failures)
        )


if __name__ == "__main__":
    unittest.main()