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

from ai.agents.agent import Agent
from ai.providers import get_provider


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
        from config import Color

        print(f"{Color.CYAN}⚡ Agent '{agent.name}' "
              f"starting...{Color.RESET}")
        print(f"{Color.DIM}  Task: {task}{Color.RESET}")

        agent.status = "running"

        try:
            # Step 1: Agent thinks about the task
            plan = agent.think(task)

            if agent.tools:
                result = self._run_with_tools(
                    agent, task)
            else:
                result = self._run_simple(agent, task)

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