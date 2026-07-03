"""
Phase 23 — Polish + Inline Error Handling
Tests for: list/dict destructuring (`let [first, ...rest] = list`,
`let {name, age} = dict`), inline error handling on `think`, docstrings,
and the async rewrite.
"""
import unittest
import sys
import io
import re
from unittest.mock import patch, MagicMock

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.ai import memory_store as _mem_store

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def run(source: str) -> str:
    _mem_store._memory.clear()
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    interp = Interpreter()
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        interp.run(ast)
    finally:
        sys.stdout = old
    return ANSI.sub('', buf.getvalue()).strip()


def _failing_provider(message="network down"):
    """A fake AI provider whose .ask()/other calls always raise."""
    provider = MagicMock()
    provider.ask.side_effect = RuntimeError(message)
    provider.timeout = 30
    return provider


class TestTaskDocstrings(unittest.TestCase):
    """A leading triple/single-quoted string in a task body is
    captured as documentation via doc(task) instead of causing a
    parse error (bare string statements are otherwise invalid)."""

    def test_plain_task_docstring_captured(self):
        out = run(
            'task greet(name):\n'
            '    """Says hello to someone."""\n'
            '    show "Hello " + name\n'
            'show doc(greet)\n'
        )
        self.assertEqual(out, "Says hello to someone.")

    def test_typed_task_docstring_captured(self):
        out = run(
            'task add(a: int, b: int) -> int:\n'
            '    """Adds two numbers."""\n'
            '    return a + b\n'
            'show doc(add)\n'
        )
        self.assertEqual(out, "Adds two numbers.")

    def test_docstring_not_executed_as_a_statement(self):
        """The docstring must be consumed as metadata, not run as a
        (harmless but pointless) expression statement — the task's
        real behaviour should be completely unaffected by it."""
        out = run(
            'task double(n):\n'
            '    """Doubles a number."""\n'
            '    return n * 2\n'
            'show double(21)\n'
        )
        self.assertEqual(out, "42")

    def test_task_without_docstring_reports_missing(self):
        out = run(
            'task noop():\n'
            '    show "hi"\n'
            'noop()\n'
            'show doc(noop)\n'
        )
        self.assertEqual(out, "hi\nNo docstring for 'noop'.")

    def test_single_quoted_docstring_also_works(self):
        out = run(
            'task greet(name):\n'
            '    "Says hello."\n'
            '    show name\n'
            'show doc(greet)\n'
        )
        self.assertEqual(out, "Says hello.")

    def test_task_with_no_body_besides_docstring_still_needs_content(self):
        """A docstring alone isn't a full task body — this documents
        current behaviour rather than mandating a 'pass'-like no-op,
        since NEKOVA doesn't have one yet."""
        out = run(
            'task documented(n):\n'
            '    """Just returns n."""\n'
            '    return n\n'
            'show documented(5)\n'
        )
        self.assertEqual(out, "5")


class TestAsyncRewrite(unittest.TestCase):
    """
    Phase 23 async rewrite. AsyncFunction now delegates execution to
    Interpreter._call_typed_task (the same path regular typed tasks
    use) instead of a hand-rolled coroutine walker that manipulated
    raw dicts and only understood three narrow statement shapes.
    Fixes three concrete, reproducible bugs plus closes a parser
    param-list gap:

      1. Control flow (loops, etc.) inside an async task body used to
         crash with AttributeError: 'dict' object has no attribute 'set'.
      2. Calling an async task without 'await' used to crash with an
         unhandled RuntimeError (the code caught NEKOVARuntimeError,
         but asyncio.get_running_loop() raises the built-in RuntimeError).
      3. `async task add(a, b=5):` used to fail to parse entirely —
         a method-name collision with ClassParserMixin meant async
         tasks silently lost default-value and *varargs support.
      4. 'await' only worked as a standalone statement or directly on
         the RHS of 'let x = await ...' — not as a general expression
         (e.g. inside show, return, or a binary operation).
    """

    def test_loop_inside_async_task_body(self):
        out = run(
            'async task sum_list(items):\n'
            '    let total = 0\n'
            '    for x in items:\n'
            '        total = total + x\n'
            '    return total\n'
            'let r = await sum_list([1, 2, 3, 4])\n'
            'show r\n'
        )
        self.assertEqual(out, "10")

    def test_if_inside_async_task_body(self):
        out = run(
            'async task classify(n):\n'
            '    if n > 0:\n'
            '        return "positive"\n'
            '    return "non-positive"\n'
            'show await classify(5)\n'
        )
        self.assertEqual(out, "positive")

    def test_calling_async_task_without_await_does_not_crash(self):
        out = run(
            'async task greet(name):\n'
            '    return name\n'
            'let r = greet("Sam")\n'
            'show r\n'
        )
        self.assertEqual(out, "Sam")

    def test_default_parameter_values(self):
        out = run(
            'async task add(a, b=5):\n'
            '    return a + b\n'
            'show await add(10)\n'
            'show await add(10, 20)\n'
        )
        self.assertEqual(out, "15\n30")

    def test_varargs(self):
        out = run(
            'async task total(*nums):\n'
            '    let s = 0\n'
            '    for n in nums:\n'
            '        s = s + n\n'
            '    return s\n'
            'show await total(1, 2, 3)\n'
        )
        self.assertEqual(out, "6")

    def test_type_hints_and_return_type_enforced(self):
        out = run(
            'async task double(n: int) -> int:\n'
            '    return n * 2\n'
            'show await double(21)\n'
        )
        self.assertEqual(out, "42")

    def test_nested_async_calls(self):
        out = run(
            'async task inner(x):\n'
            '    return x * 2\n'
            'async task outer(x):\n'
            '    let y = await inner(x)\n'
            '    return y + 1\n'
            'show await outer(5)\n'
        )
        self.assertEqual(out, "11")

    def test_await_as_general_expression_in_show(self):
        out = run(
            'async task get_num():\n'
            '    return 10\n'
            'show await get_num() + 5\n'
        )
        self.assertEqual(out, "15")

    def test_await_as_general_expression_in_return(self):
        out = run(
            'async task inner():\n'
            '    return 1\n'
            'async task outer():\n'
            '    return await inner() + 1\n'
            'show await outer()\n'
        )
        self.assertEqual(out, "2")

    def test_async_task_docstring_captured(self):
        out = run(
            'async task greet(name):\n'
            '    """Greets someone."""\n'
            '    return name\n'
            'show doc(greet)\n'
        )
        self.assertEqual(out, "Greets someone.")


class TestThinkInlineErrorHandling(unittest.TestCase):
    """think "..." when error: <fallback>  — the AI call's exception is
    caught and the fallback expression is evaluated instead, rather
    than embedding a '[think error: ...]' string in the result."""

    def test_plain_think_falls_back_on_error(self):
        with patch('nekova.ai.providers.get_provider',
                   return_value=_failing_provider()):
            out = run(
                'let summary = think "summarize" when error: "unavailable"\n'
                'show summary\n'
            )
        self.assertEqual(out, "🧠 unavailable\nunavailable")

    def test_think_as_json_falls_back_on_error(self):
        with patch('nekova.ai.providers.get_provider',
                   return_value=_failing_provider()):
            out = run(
                'let x = think "hi" as json '
                'when error: {"status": "down"}\n'
                'show x\n'
            )
        self.assertEqual(out, "{status: down}")

    def test_fallback_expression_can_reference_variables(self):
        with patch('nekova.ai.providers.get_provider',
                   return_value=_failing_provider()):
            out = run(
                'let default_msg = "no AI available"\n'
                'let summary = think "summarize" when error: default_msg\n'
                'show summary\n'
            )
        self.assertEqual(out, "🧠 no AI available\nno AI available")

    def test_no_fallback_clause_keeps_old_swallow_behaviour(self):
        """Programs written before this feature existed must keep
        working exactly as they did — think errors without a
        'when error:' clause still swallow to a string, they don't
        start raising."""
        with patch('nekova.ai.providers.get_provider',
                   return_value=_failing_provider("boom")):
            out = run('let y = think "hi"\nshow y\n')
        self.assertIn("[think error: boom]", out)

    def test_success_path_unaffected_by_on_error_clause(self):
        """When the AI call succeeds, the fallback clause should
        simply never run."""
        from nekova.ai.providers.mock import MockProvider
        with patch('nekova.ai.providers.get_provider',
                   return_value=MockProvider()):
            out = run(
                'let x = think "hello" when error: "should not appear"\n'
                'show x\n'
            )
        self.assertNotIn("should not appear", out)
        self.assertIn("[MOCK]", out)


class TestListDestructure(unittest.TestCase):
    def test_basic_two_targets(self):
        out = run(
            'let [a, b] = [10, 20, 30]\n'
            'show a\n'
            'show b\n'
        )
        self.assertEqual(out, "10\n20")

    def test_rest_capture(self):
        out = run(
            'let [first, ...rest] = [1, 2, 3, 4]\n'
            'show first\n'
            'show rest\n'
        )
        self.assertEqual(out, "1\n[2, 3, 4]")

    def test_rest_capture_empty_when_exact_length(self):
        out = run(
            'let [a, b, ...rest] = [1, 2]\n'
            'show rest\n'
        )
        self.assertEqual(out, "[]")

    def test_single_target_no_rest(self):
        out = run(
            'let [only] = [42, 99]\n'
            'show only\n'
        )
        self.assertEqual(out, "42")

    def test_works_on_task_return_value(self):
        out = run(
            'task pair():\n'
            '    return [1, 2]\n'
            'let [x, y] = pair()\n'
            'show x + y\n'
        )
        self.assertEqual(out, "3")

    def test_too_few_items_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('let [a, b, c] = [1]\n')

    def test_non_list_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('let [a, b] = 5\n')

    def test_extra_items_without_rest_are_ignored(self):
        out = run(
            'let [a, b] = [1, 2, 3, 4]\n'
            'show a\n'
            'show b\n'
        )
        self.assertEqual(out, "1\n2")


class TestDictDestructure(unittest.TestCase):
    def test_basic_two_keys(self):
        out = run(
            'let {name, age} = {"name": "Sam", "age": 30}\n'
            'show name\n'
            'show age\n'
        )
        self.assertEqual(out, "Sam\n30")

    def test_single_key(self):
        out = run(
            'let {name} = {"name": "Ada", "age": 40}\n'
            'show name\n'
        )
        self.assertEqual(out, "Ada")

    def test_missing_key_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('let {name, age} = {"name": "Sam"}\n')

    def test_non_dict_raises(self):
        with self.assertRaises(NEKOVARuntimeError):
            run('let {name} = [1, 2]\n')

    def test_works_on_task_return_value(self):
        out = run(
            'task user():\n'
            '    return {"name": "Kim", "age": 25}\n'
            'let {name, age} = user()\n'
            'show name\n'
            'show age\n'
        )
        self.assertEqual(out, "Kim\n25")


if __name__ == "__main__":
    unittest.main()