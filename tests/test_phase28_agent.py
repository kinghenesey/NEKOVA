"""
Phase 28 — Agent System + Unified Schema (agent declaration, part 2)

Tests for the first-class `agent "Name": ...` declaration, which
compiles down to exactly the same agent_create()/agent_tool() calls
the older function-call API already used — see AgentDefinition's
docstring in nodes.py and _exec_AgentDefinition in interpreter.py.

Also covers a real bug found and fixed alongside this work:
AgentRunner's provider is a long-lived singleton reused across every
agent_run() call (agents_module._agent_run caches a single module-level
_runner). Without an unconditional reset, one agent's `model:` choice
would silently leak into the next agent's run if that next agent had
no model of its own configured.
"""
import io
import re
import sys
import unittest

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter
from nekova.interpreter.exceptions import NEKOVARuntimeError
from nekova.ai.agents_module import _agents, _runner
import nekova.ai.agents_module as agents_module

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def run(source: str) -> str:
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


class AgentTestBase(unittest.TestCase):
    """_agents (and the cached _runner) are module-level globals in
    agents_module.py — clear them between tests so one test's agents
    can't leak into another's, same precaution test_agents_security.py
    already takes."""

    def setUp(self):
        _agents.clear()
        agents_module._runner = None


class TestAgentDeclarationBasics(AgentTestBase):
    def test_let_captures_agent_name(self):
        out = run(
            'use agents\n'
            'let researcher = agent "Research Assistant":\n'
            '    tools: [summarize]\n'
            'show researcher\n'
        )
        self.assertIn("Research Assistant", out)

    def test_bare_statement_form_works(self):
        run(
            'use agents\n'
            'agent "Simple Bot":\n'
            '    tools: [summarize]\n'
        )
        self.assertIn("Simple Bot", _agents)

    def test_goal_field_applied(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    goal: "Do the thing"\n'
        )
        self.assertEqual(_agents["Bot"].goal, "Do the thing")

    def test_goal_defaults_when_omitted(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    tools: [summarize]\n'
        )
        self.assertEqual(_agents["Bot"].goal, "Complete tasks")

    def test_tools_field_registers_tools(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    tools: [summarize, calculate]\n'
        )
        self.assertEqual(set(_agents["Bot"].tools.keys()),
                          {"summarize", "calculate"})

    def test_agent_declared_without_tools_is_fine(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    goal: "Just talk"\n'
        )
        self.assertEqual(_agents["Bot"].tools, {})

    def test_model_field_sets_agent_model(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    model: "gpt-4o"\n'
        )
        self.assertEqual(_agents["Bot"].model, "gpt-4o")

    def test_no_model_field_leaves_model_none(self):
        run(
            'use agents\n'
            'agent "Bot":\n'
            '    tools: [summarize]\n'
        )
        self.assertIsNone(_agents["Bot"].model)

    def test_agent_as_ordinary_variable_still_works(self):
        """'agent' is a soft keyword — using it as a plain variable
        name must keep working, exactly like 'prompt'/'schema' do."""
        out = run('let agent = 5\nshow agent\n')
        self.assertEqual(out, "5")


class TestAgentDeclarationInterop(AgentTestBase):
    """Agents built via the new declaration must be fully usable
    through the old function-call API, and vice versa — both syntaxes
    share the same underlying _agents registry."""

    def test_declared_agent_works_with_agent_run(self):
        out = run(
            'use agents\n'
            'let bot = agent "Bot":\n'
            '    tools: [summarize]\n'
            'show agent_run(bot, "hello world")\n'
        )
        self.assertIn("summarize", out.lower())

    def test_declared_agent_works_with_agent_status(self):
        out = run(
            'use agents\n'
            'agent "Bot":\n'
            '    tools: [summarize]\n'
            'show agent_status("Bot")\n'
        )
        self.assertTrue(out.endswith("idle"))

    def test_function_call_agent_unaffected(self):
        """Plain old-style agent_create/agent_tool must still work
        exactly as before, unmodified by any of this."""
        out = run(
            'use agents\n'
            'agent_create("Classic", "old style")\n'
            'agent_tool("Classic", "summarize", "")\n'
            'show agent_status("Classic")\n'
        )
        self.assertTrue(out.endswith("idle"))


class TestAgentDeclarationErrors(AgentTestBase):
    def test_tools_must_be_a_list(self):
        with self.assertRaises(NEKOVARuntimeError):
            run(
                'use agents\n'
                'agent "Bot":\n'
                '    tools: "summarize"\n'
            )

    def test_tools_entry_must_be_name_or_call(self):
        with self.assertRaises(NEKOVARuntimeError):
            run(
                'use agents\n'
                'agent "Bot":\n'
                '    tools: [42]\n'
            )


class TestAgentModelDoesNotLeak(AgentTestBase):
    """Regression test for the AgentRunner singleton-provider bug:
    since agents_module._agent_run reuses one cached AgentRunner (and
    therefore one cached provider) across every call, an agent with no
    model of its own must never inherit a previous agent's choice."""

    def test_model_reset_between_agents(self):
        run(
            'use agents\n'
            'agent "First":\n'
            '    model: "gpt-4o"\n'
            'agent_run("First", "task one")\n'
            'agent "Second":\n'
            '    tools: [summarize]\n'
            'agent_run("Second", "task two")\n'
        )
        # After Second's run, the shared runner's provider must not
        # still be carrying First's model.
        self.assertIsNone(agents_module._runner.provider.model)


if __name__ == "__main__":
    unittest.main()