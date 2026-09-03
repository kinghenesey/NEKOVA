# =============================================================
# NEKOVA AI Ecosystem — Agent Runner
# =============================================================
# Runs agents and manages their execution lifecycle.
#
# The runner:
#   1. Receives a task from the user
#   2. Lets the agent think about it
#   3. Executes the agent's plan using its tools
#   4. Returns the result
#
# In mock mode: returns simulated responses
# With API key: uses real Claude AI

from nekova.ai.agents.agent import Agent
from nekova.ai.providers import get_provider


class AgentRunner:
    """
    Manages the execution of NEKOVA agents.

    Usage:
        runner = AgentRunner()
        result = runner.run(agent, "Research Python")
    """

    def __init__(self):
        self.provider = get_provider()
        self.history  = []

    def run(self, agent: Agent, task: str) -> str:
        """
        Run an agent on a task.
        Returns the agent's response.
        """
        from nekova.config import Color

        print(f"{Color.CYAN}⚡ Agent '{agent.name}' "
              f"starting...{Color.RESET}")
        print(f"{Color.DIM}  Task: {task}{Color.RESET}")

        # Phase 28: apply this agent's model override, if any.
        # Unconditional (not "only if agent.model is set") because
        # self.provider is a long-lived singleton reused across every
        # agent_run() call (see agents_module._agent_run's module-level
        # `_runner`) — without resetting to None here, an earlier
        # agent's model choice would silently leak into an agent that
        # never asked for one.
        self.provider.model = getattr(agent, "model", None)

        agent.status = "running"

        try:
            # Step 1: Agent thinks about the task to form a plan
            plan = agent.think(task)

            # Step 2: Execute using the plan as context
            if agent.tools:
                result = self._run_with_tools(agent, plan or task)
            else:
                result = self._run_simple(agent, plan or task)

            # Store result
            agent.result = result
            agent.status = "done"
            agent.memory.remember("result", result)

            print(f"{Color.GREEN}✓ Agent '{agent.name}' "
                  f"complete{Color.RESET}")

            return result

        except Exception as e:
            agent.status = "error"
            error_msg = f"Agent error: {str(e)}"
            print(f"{Color.RED}✗ {error_msg}{Color.RESET}")
            return error_msg

    def _run_simple(self, agent: Agent,
                    task: str) -> str:
        """Run agent without tools — just AI response."""
        prompt = (
            f"You are an AI agent named '{agent.name}'.\n"
            f"Your goal is: {agent.goal}\n"
            f"Complete this task: {task}\n"
            f"Be concise and helpful."
        )
        return self.provider.ask(prompt)

    def _run_with_tools(self, agent: Agent,
                        task: str) -> str:
        """Run agent with tools available."""
        results = []

        # Try each relevant tool
        for tool_name, tool in agent.tools.items():
            try:
                tool_result = tool.run(task)
                results.append(
                    f"[{tool_name}]: {tool_result}"
                )
                agent.memory.remember(
                    "tool_result",
                    f"{tool_name}: {str(tool_result)[:100]}"
                )
            except Exception as e:
                results.append(
                    f"[{tool_name}]: Error — {e}"
                )

        if results:
            combined = "\n".join(results)
            # Summarize the results
            summary = self.provider.summarize(combined)
            return summary

        return self._run_simple(agent, task)

    def __repr__(self):
        return f"AgentRunner(provider={self.provider.name})"