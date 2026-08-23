# =============================================================
# NEKOVA AI Ecosystem — Agents Module
# =============================================================
# This is what gets loaded when you write "use agents" in NEKOVA.
# It exposes all agent and workflow functions.
#
# Usage in NEKOVA:
#   use agents
#   agent_create("researcher", "Research topics")
#   agent_tool("researcher", "search", "Search the web")
#   result = agent_run("researcher", "Tell me about Python")
#   show result

from nekova.ai.agents.agent import Agent
from nekova.ai.agents.agent_runner import AgentRunner
from nekova.ai.workflows.workflow import Workflow
from nekova.ai.providers import get_provider

import ast
import operator


# ----------------------------------------------------------
# Safe arithmetic evaluator for the "calculate" tool
# ----------------------------------------------------------
# The "calculate" tool used to be `eval(expr)` — and agent_runner.py's
# _run_with_tools() hands every registered tool the ENTIRE raw task
# string automatically, with no LLM decision or filtering in between.
# That meant any NEKOVA program wiring up a "calculate" tool and then
# calling agent_run(name, some_untrusted_string) — a web request body,
# user input, anything — ran that string as arbitrary Python. Confirmed
# exploitable, e.g. agent_run("bot", "__import__('os').system('...')").
#
# Fixed by parsing with ast.parse() and walking the resulting tree
# through an explicit whitelist: only numeric constants and the
# operators below are ever evaluated. Anything else — Name, Call,
# Attribute, Subscript, Import, comprehensions, lambdas, literally
# anything that isn't a number or one of these operators — is
# rejected before evaluation ever touches it, so there is no
# expression that can escape into arbitrary code execution.
_SAFE_BINOPS = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod:      operator.mod,
    ast.Pow:      operator.pow,
}
_SAFE_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
# Pow with a huge exponent (9**9**9**9) can hang or exhaust memory even
# though it's "just arithmetic" — cap exponents to something no
# legitimate calculator use needs.
_MAX_POW_EXPONENT = 1000


def _safe_calculate(expr: str) -> str:
    """
    Evaluate a plain arithmetic expression without using Python's
    eval(). Only numbers, + - * / // % **, parentheses, and unary
    +/- are permitted. Raises ValueError on anything else, including
    syntactically valid Python that isn't arithmetic.
    """
    text = str(expr).replace("^", "**")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise ValueError(
            f"'{expr}' is not a valid arithmetic expression."
        )

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError(
                "calculate() only accepts numbers, "
                f"got {node.value!r}."
            )
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
            left  = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POW_EXPONENT:
                raise ValueError(
                    "calculate() exponent is too large."
                )
            return _SAFE_BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARYOPS:
            return _SAFE_UNARYOPS[type(node.op)](_eval(node.operand))
        raise ValueError(
            f"'{expr}' isn't a plain arithmetic expression — "
            f"calculate() only supports numbers and + - * / // % **."
        )

    try:
        result = _eval(tree)
    except ZeroDivisionError:
        raise ValueError("calculate(): division by zero.")
    return str(result)


# Global state
_agents    = {}
_workflows = {}
_runner    = None


def load() -> dict:
    """
    Returns all agent functions to be loaded
    into the NEKOVA environment when 'use agents' is called.
    """
    return {
        # Agent management
        "agent_create":   _agent_create,
        "agent_tool":     _agent_tool,
        "agent_run":      _agent_run,
        "agent_memory":   _agent_memory,
        "agent_status":   _agent_status,
        "agent_list":     _agent_list,

        # Workflow management
        "workflow_create": _workflow_create,
        "workflow_step":   _workflow_step,
        "workflow_run":    _workflow_run,
        "workflow_result": _workflow_result,

        # Quick AI tasks
        "ai_research":    _ai_research,
        "ai_analyze":     _ai_analyze,
        "ai_plan":        _ai_plan,
    }


# ----------------------------------------------------------
# Agent management
# ----------------------------------------------------------

def _agent_create(name: str,
                  goal: str = "Complete tasks") -> str:
    """Create a new AI agent."""
    agent = Agent(name=str(name), goal=str(goal))
    _agents[str(name)] = agent

    from nekova.config import Color
    print(f"{Color.CYAN}✓ Agent '{name}' created{Color.RESET}")
    print(f"{Color.DIM}  Goal: {goal}{Color.RESET}")
    return name


def _agent_tool(agent_name: str,
                tool_name: str,
                description: str = "") -> str:
    """Add a tool to an agent."""
    agent = _get_agent(agent_name)
    provider = get_provider()

    # Built-in tool functions
    tools = {
        "search": lambda query: provider.ask(
            f"Search for information about: {query}"
        ),
        "summarize": lambda text: provider.summarize(
            str(text)
        ),
        "generate": lambda prompt: provider.generate(
            str(prompt)
        ),
        "classify": lambda text: provider.classify(
            str(text), ["positive", "negative", "neutral"]
        ),
        "save": lambda content: _save_to_file(
            str(agent_name), str(content)
        ),
        "calculate": lambda expr: _safe_calculate(expr),
    }

    if tool_name in tools:
        agent.add_tool(
            str(tool_name),
            str(description) or tool_name,
            tools[tool_name]
        )
    else:
        # Custom tool — just use AI
        agent.add_tool(
            str(tool_name),
            str(description),
            lambda x: get_provider().ask(
                f"{tool_name}: {x}"
            )
        )

    return tool_name


def _agent_run(agent_name: str, task: str) -> str:
    """Run an agent on a task."""
    global _runner
    agent = _get_agent(agent_name)

    if _runner is None:
        _runner = AgentRunner()

    return _runner.run(agent, str(task))


def _agent_memory(agent_name: str) -> str:
    """Get an agent's memory summary."""
    agent = _get_agent(agent_name)
    return agent.memory.summary()


def _agent_status(agent_name: str) -> str:
    """Get an agent's current status."""
    agent = _get_agent(agent_name)
    return agent.status


def _agent_list() -> str:
    """List all created agents."""
    if not _agents:
        return "No agents created yet."
    lines = []
    for name, agent in _agents.items():
        tools = ", ".join(agent.tools.keys()) or "none"
        lines.append(
            f"  {name}: {agent.status} "
            f"(tools: {tools})"
        )
    return "\n".join(lines)


# ----------------------------------------------------------
# Workflow management
# ----------------------------------------------------------

def _workflow_create(name: str,
                     description: str = "") -> str:
    """Create a new workflow."""
    wf = Workflow(
        name=str(name),
        description=str(description)
    )
    _workflows[str(name)] = wf

    from nekova.config import Color
    print(f"{Color.CYAN}✓ Workflow '{name}' "
          f"created{Color.RESET}")
    return name


def _workflow_step(workflow_name: str,
                   step_name: str,
                   action: str,
                   data: str = "") -> str:
    """Add a step to a workflow."""
    if workflow_name not in _workflows:
        raise RuntimeError(
            f"Workflow '{workflow_name}' not found.\n"
            f"  Create it first with: "
            f"workflow_create('{workflow_name}')"
        )

    wf       = _workflows[workflow_name]
    provider = get_provider()

    # Map action to function
    action_map = {
        "ask":       lambda: provider.ask(data),
        "summarize": lambda: provider.summarize(data),
        "generate":  lambda: provider.generate(data),
        "save":      lambda: _save_to_file(
                         workflow_name, data),
        "print":     lambda: print(data) or data,
    }

    fn = action_map.get(
        str(action),
        lambda: provider.ask(f"{action}: {data}")
    )

    wf.add_step(str(step_name), fn)
    return step_name


def _workflow_run(workflow_name: str) -> str:
    """Run a workflow."""
    if workflow_name not in _workflows:
        raise RuntimeError(
            f"Workflow '{workflow_name}' not found."
        )

    wf      = _workflows[workflow_name]
    results = wf.run()

    # Return last meaningful result
    for result in reversed(results):
        if result is not None:
            return str(result)
    return "Workflow complete."


def _workflow_result(workflow_name: str) -> str:
    """Get the last result of a workflow."""
    if workflow_name not in _workflows:
        return "Workflow not found."

    wf = _workflows[workflow_name]
    result = wf.last_result()
    return str(result) if result else "No result yet."


# ----------------------------------------------------------
# Quick AI tasks
# ----------------------------------------------------------

def _ai_research(topic: str) -> str:
    """Research a topic using AI."""
    provider = get_provider()
    prompt   = (
        f"Research the following topic and provide a "
        f"clear, structured summary:\n\n{topic}"
    )
    return provider.ask(prompt)


def _ai_analyze(data: str) -> str:
    """Analyze data using AI."""
    provider = get_provider()
    prompt   = (
        f"Analyze the following and provide insights:\n\n"
        f"{data}"
    )
    return provider.ask(prompt)


def _ai_plan(goal: str) -> str:
    """Generate an action plan for a goal."""
    provider = get_provider()
    prompt   = (
        f"Create a clear step-by-step action plan "
        f"to achieve this goal:\n\n{goal}"
    )
    return provider.generate(prompt)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _get_agent(name: str) -> Agent:
    """Get an agent by name."""
    if str(name) not in _agents:
        raise RuntimeError(
            f"Agent '{name}' not found.\n"
            f"  Create it first with: "
            f"agent_create('{name}', 'goal')"
        )
    return _agents[str(name)]


def _save_to_file(name: str, content: str) -> str:
    """Save content to a file."""
    filename = f"{name}_output.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Saved to {filename}"