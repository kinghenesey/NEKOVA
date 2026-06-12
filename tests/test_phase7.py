# =============================================================
# NEKOVA — Phase 7 Tests (AI Runtime)
# =============================================================
# Run with: python tests/test_phase7.py

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.ai.providers.mock import MockProvider
from nekova.ai.providers import get_provider, get_provider_by_name
from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """Helper — run NEKOVA source and capture printed output."""
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


class TestMockProvider(unittest.TestCase):

    def setUp(self):
        self.provider = MockProvider()

    def test_provider_name(self):
        self.assertEqual(self.provider.name, "mock")

    def test_provider_available(self):
        self.assertTrue(self.provider.is_available)

    def test_ask_returns_string(self):
        result = self.provider.ask("What is NEKOVA?")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_ask_nigeria_capital(self):
        result = self.provider.ask("What is the capital of Nigeria?")
        self.assertIn("Abuja", result)

    def test_ask_hello(self):
        result = self.provider.ask("Hello!")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_summarize_returns_string(self):
        result = self.provider.summarize("This is a long text about NEKOVA.")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_summarize_contains_word_count(self):
        result = self.provider.summarize("one two three four five")
        self.assertIn("5", result)

    def test_generate_poem(self):
        result = self.provider.generate("Write a poem")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_function(self):
        result = self.provider.generate("Write a function")
        self.assertIn("task", result)

    def test_classify_positive(self):
        result = self.provider.classify(
            "I love NEKOVA!", ["positive", "negative"]
        )
        self.assertEqual(result, "positive")

    def test_classify_negative(self):
        result = self.provider.classify(
            "This is terrible!", ["positive", "negative"]
        )
        self.assertEqual(result, "negative")

    def test_classify_default(self):
        result = self.provider.classify(
            "Some neutral text.", ["positive", "negative"]
        )
        self.assertIn(result, ["positive", "negative"])


class TestProviderRegistry(unittest.TestCase):

    def test_get_provider_returns_provider(self):
        provider = get_provider()
        self.assertIsNotNone(provider)
        self.assertTrue(provider.is_available)

    def test_get_mock_by_name(self):
        provider = get_provider_by_name("mock")
        self.assertEqual(provider.name, "mock")

    def test_invalid_provider_name(self):
        with self.assertRaises(ValueError):
            get_provider_by_name("invalid_provider")


class TestAIInNEKOVA(unittest.TestCase):

    def test_ai_ask(self):
        source = (
            'use ai\n'
            'answer = ai_ask("What is the capital of Nigeria?")\n'
            'show answer'
        )
        output = run(source)
        self.assertIn("Abuja", output)

    def test_ai_provider_name(self):
        source = (
            'use ai\n'
            'provider = ai_provider()\n'
            'show provider'
        )
        output = run(source)
        self.assertIn("mock", output)

    def test_ai_summarize(self):
        source = (
            'use ai\n'
            'summary = ai_summarize("Hello world this is NEKOVA")\n'
            'show summary'
        )
        output = run(source)
        self.assertIsInstance(output, str)
        self.assertGreater(len(output), 0)

    def test_ai_generate(self):
        source = (
            'use ai\n'
            'result = ai_generate("Write a poem")\n'
            'show result'
        )
        output = run(source)
        self.assertIsInstance(output, str)
        self.assertGreater(len(output), 0)

    def test_ai_classify(self):
        source = (
            'use ai\n'
            'label = ai_classify("I love this!", "positive,negative")\n'
            'show label'
        )
        output = run(source)
        self.assertEqual(output.strip().split("\n")[-1], "positive")


if __name__ == "__main__":
    print("=" * 50)
    print("  NEKOVA Phase 7 — AI Runtime Test Suite")
    print("=" * 50)
    unittest.main(verbosity=2)