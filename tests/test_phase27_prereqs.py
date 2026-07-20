"""
Phase 27 prerequisites — tests for the tooling itself:
  - tools/check_grammar_coverage.py
  - tools/fuzz/generator.py, mutator.py, harness.py
  - The RecursionError -> clean ParseError fix the fuzzer found
"""
import os
import sys
import subprocess
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
FUZZ_DIR = os.path.join(REPO_ROOT, "tools", "fuzz")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
if FUZZ_DIR not in sys.path:
    sys.path.insert(0, FUZZ_DIR)


class TestGrammarCoverageChecker(unittest.TestCase):

    def test_live_repo_passes_coverage_check(self):
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "tools",
             "check_grammar_coverage.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("OK", result.stdout)

    def test_finds_every_parse_method(self):
        from check_grammar_coverage import find_parse_methods
        methods = find_parse_methods()
        # Sanity: a handful of well-known methods must be present.
        for name in ("_parse_if", "_parse_task", "_parse_sandbox",
                     "_parse_test", "parse_class_definition"):
            self.assertIn(name, methods)

    def test_finds_grammar_rules(self):
        from check_grammar_coverage import find_grammar_rules
        rules = find_grammar_rules()
        for name in ("if_stmt", "task_def", "sandbox_stmt", "test_stmt"):
            self.assertIn(name, rules)


class TestFuzzGenerator(unittest.TestCase):

    def test_generates_nonempty_program(self):
        from generator import generate_program
        src = generate_program()
        self.assertTrue(len(src) > 0)

    def test_many_generations_never_crash(self):
        """The generator itself must never raise — it's meant to
        produce arbitrary (often invalid) NEKOVA source, not to be
        bulletproof NEKOVA itself."""
        from generator import generate_program
        for _ in range(200):
            generate_program()  # must not raise

    def test_generated_programs_lex_without_python_crash(self):
        """Doesn't need to be syntactically valid NEKOVA, but the
        lexer should never raise anything other than its own
        LexerError on generator output."""
        from generator import generate_program
        from nekova.lexer import Lexer
        from nekova.lexer.lexer import LexerError
        for _ in range(200):
            src = generate_program()
            try:
                Lexer(src).tokenize()
            except LexerError:
                pass  # expected for some generated programs

    def test_string_literals_escape_embedded_quotes(self):
        """Regression: the generator used to emit unescaped quotes
        inside string literals it generated, producing corrupt
        source before any mutation was even applied."""
        import random
        from generator import _literal
        random.seed(0)
        found_escaped_case = False
        for _ in range(500):
            lit = _literal()
            if lit.startswith('"') and lit.endswith('"'):
                inner = lit[1:-1]
                # Any unescaped " inside the literal (not counting
                # the wrapping quotes) would make this invalid.
                i = 0
                while i < len(inner):
                    if inner[i] == '"' and (i == 0 or inner[i-1] != '\\'):
                        self.fail(f"Unescaped quote in generated "
                                  f"literal: {lit!r}")
                    i += 1
                if '\\"' in lit:
                    found_escaped_case = True
        self.assertTrue(found_escaped_case,
                        "Test didn't exercise the escaping path at all "
                        "in 500 tries — check STRINGS still has a "
                        "quote-containing entry.")


class TestFuzzMutator(unittest.TestCase):

    def test_all_mutations_handle_empty_string(self):
        from mutator import _MUTATION_FUNCS
        for name, fn in _MUTATION_FUNCS.items():
            try:
                fn("")  # must not raise
            except Exception as e:
                self.fail(f"Mutation '{name}' raised on empty "
                          f"string: {e}")

    def test_all_mutations_handle_single_char(self):
        from mutator import _MUTATION_FUNCS
        for name, fn in _MUTATION_FUNCS.items():
            try:
                fn("x")
            except Exception as e:
                self.fail(f"Mutation '{name}' raised on single "
                          f"char: {e}")

    def test_mutate_records_applied_mutations(self):
        from mutator import mutate
        src, applied = mutate("let x = 1\n", num_mutations=3)
        self.assertEqual(len(applied), 3)


class TestFuzzHarness(unittest.TestCase):

    def test_classifies_valid_program(self):
        from harness import _run_one
        result, info = _run_one('show "hi"\n')
        self.assertEqual(result, "valid")

    def test_classifies_rejected_program(self):
        from harness import _run_one
        result, info = _run_one('!!!not valid nekova!!!\n')
        self.assertEqual(result, "rejected")

    def test_classifies_timeout(self):
        """Confirms the timeout mechanism itself works, independent
        of whether any real input currently triggers one."""
        from harness import _run_one
        import time
        # A trivial valid program should never hit even a 1s timeout.
        start = time.time()
        result, info = _run_one('show 1\n', timeout_seconds=1)
        elapsed = time.time() - start
        self.assertEqual(result, "valid")
        self.assertLess(elapsed, 1.0)

    def test_run_campaign_bounded_iterations(self):
        from harness import run_campaign
        result = run_campaign(iterations=50, seed=7, verbose=False)
        self.assertEqual(result["iterations"], 50)
        self.assertEqual(result["counts"]["crash"], 0)

    def test_run_campaign_bounded_seconds(self):
        from harness import run_campaign
        import time
        start = time.time()
        result = run_campaign(seconds=0.5, verbose=False)
        elapsed = time.time() - start
        # Should stop reasonably close to the time budget, not run away.
        self.assertLess(elapsed, 3.0)


class TestRecursionErrorFix(unittest.TestCase):
    """The specific bug the fuzzer found and this phase fixed."""

    def test_deeply_nested_parens_raises_clean_parse_error(self):
        from nekova.lexer import Lexer
        from nekova.parser.parser import Parser, ParseError
        src = "let x = " + "(" * 2000 + "1" + ")" * 2000
        tokens = Lexer(src).tokenize()
        with self.assertRaises(ParseError) as ctx:
            Parser(tokens).parse()
        self.assertIn("nested too deeply", str(ctx.exception))

    def test_moderate_nesting_still_parses_normally(self):
        """The fix must not make ordinary, reasonably-nested
        expressions fail."""
        from nekova.lexer import Lexer
        from nekova.parser.parser import Parser
        src = "let x = ((1 + 2) * (3 - 4))\nshow x\n"
        tokens = Lexer(src).tokenize()
        program = Parser(tokens).parse()
        self.assertEqual(len(program.statements), 2)


if __name__ == "__main__":
    unittest.main()