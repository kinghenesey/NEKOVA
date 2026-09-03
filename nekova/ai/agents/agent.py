# =============================================================
# NEKOVA AI Ecosystem — Agent Class
# =============================================================
# An Agent is an AI entity with a goal, tools, and memory.
# It can plan, execute tasks, and remember past interactions.
#
# Agents are the foundation of AI automation in NEKOVA.
# They can search, summarize, write files, and chain tasks.

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class AgentMemory:
    """
    Stores an agent's conversation and task history.
    Agents use memory to maintain context across tasks.
    """
    entries: List[Dict] = field(default_factory=list)

    def remember(self, role: str, content: str):
        """Add an entry to memory."""
        self.entries.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat(),
        })

    def recall(self, last_n: int = 5) -> List[Dict]:
        """Recall the last N memory entries."""
        return self.entries[-last_n:]

    def clear(self):
        """Clear all memory."""
        self.entries = []

    def summary(self) -> str:
        """Return a text summary of memory."""
        if not self.entries:
            return "No memory yet."
        lines = []
        for entry in self.entries[-5:]:
            lines.append(
                f"[{entry['role']}]: {entry['content'][:100]}"
            )
        return "\n".join(lines)

    def __repr__(self):
        return f"AgentMemory({len(self.entries)} entries)"


@dataclass
class AgentTool:
    """
    A tool an agent can use to accomplish tasks.

    Tools are functions the agent can call:
        - search: look up information
        - summarize: condense text
        - save: write to a file
        - calculate: do math
    """
    name:        str
    description: str
    function:    Any  # callable

    def run(self, *args, **kwargs):
        """Execute this tool."""
        return self.function(*args, **kwargs)

    def __repr__(self):
        return f"Tool({self.name})"


class Agent:
    """
    An AI agent that can plan and execute tasks.

    Usage:
        agent = Agent("researcher", "Research topics")
        agent.add_tool("search", search_fn)
        result = agent.run("Tell me about Python")
    """

    def __init__(self, name: str, goal: str = "", model: str = None):
        self.name   = name
        self.goal   = goal
        self.tools  = {}
        self.memory = AgentMemory()
        self.status = "idle"
        self.result = None
        # Phase 28: per-agent model override, set via the `agent
        # "Name": model: "..."` declaration. None means "use whatever
        # the global `model "..."` statement (or auto-detection)
        # would pick" — see AgentRunner.run(), which applies this
        # unconditionally (including resetting to None) on every run,
        # since the runner's provider is a long-lived singleton
        # shared across every agent_run() call, not a fresh one per
        # call — without an explicit reset, one agent's model choice
        # would otherwise leak into the next agent's run.
        self.model  = model

    def add_tool(self, name: str,
                 description: str, function):
        """Add a tool to this agent."""
        self.tools[name] = AgentTool(
            name=name,
            description=description,
            function=function
        )

    def use_tool(self, tool_name: str, *args):
        """Use a tool by name."""
        if tool_name not in self.tools:
            available = ", ".join(self.tools.keys())
            raise RuntimeError(
                f"Agent '{self.name}' has no tool "
                f"'{tool_name}'.\n"
                f"  Available tools: {available}"
            )

        tool   = self.tools[tool_name]
        result = tool.run(*args)
        self.memory.remember(
            "tool",
            f"Used {tool_name}: {str(result)[:100]}"
        )
        return result

    def think(self, task: str) -> str:
        """
        Think about how to approach a task.
        Returns a plan as a string.
        """
        self.memory.remember("user", task)

        tool_list = ", ".join(self.tools.keys())
        plan = (
            f"Agent '{self.name}' thinking about: {task}\n"
            f"Goal: {self.goal}\n"
            f"Available tools: {tool_list or 'none'}\n"
            f"Plan: Process the task using available tools "
            f"and return a result."
        )

        self.memory.remember("agent", f"Thinking: {task}")
        return plan

    def __repr__(self):
        return (f"Agent('{self.name}', "
                f"goal='{self.goal[:30]}', "
                f"tools={list(self.tools.keys())})")