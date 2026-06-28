# =============================================================
# NEKOVA AI Ecosystem — Workflow System
# =============================================================
# A Workflow is a sequence of automated steps.
# Each step can use AI, files, databases, or any NEKOVA module.
#
# Example:
#   workflow daily_report:
#       step 1: fetch data
#       step 2: summarize with AI
#       step 3: save to file

from dataclasses import dataclass, field
from typing import List, Any, Callable
from datetime import datetime


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Attributes:
        name     — step name
        function — callable to execute
        args     — arguments to pass
    """
    name:     str
    function: Callable
    args:     List[Any] = field(default_factory=list)

    def run(self):
        """Execute this step."""
        return self.function(*self.args)

    def __repr__(self):
        return f"Step({self.name})"


class Workflow:
    """
    A sequence of automated steps.

    Usage:
        wf = Workflow("daily_report")
        wf.add_step("fetch", fetch_fn)
        wf.add_step("summarize", summarize_fn)
        result = wf.run()
    """

    def __init__(self, name: str,
                 description: str = ""):
        self.name        = name
        self.description = description
        self.steps       = []
        self.results     = []
        self.status      = "idle"
        self.started_at  = None
        self.finished_at = None

    def add_step(self, name: str,
                 function: Callable,
                 *args):
        """Add a step to this workflow."""
        step = WorkflowStep(
            name=name,
            function=function,
            args=list(args)
        )
        self.steps.append(step)
        return self

    def run(self) -> List[Any]:
        """
        Execute all steps in order.
        Each step's result is available to the next.
        Returns list of all step results.
        """
        from nekova.config import Color

        self.status     = "running"
        self.started_at = datetime.now()
        self.results    = []

        print(f"{Color.CYAN}⚡ Workflow '{self.name}' "
              f"starting...{Color.RESET}")
        print(f"{Color.DIM}  {len(self.steps)} steps "
              f"to execute{Color.RESET}")

        for i, step in enumerate(self.steps, 1):
            print(f"{Color.DIM}  Step {i}/{len(self.steps)}: "
                  f"{step.name}...{Color.RESET}",
                  end=" ")

            try:
                result = step.run()
                self.results.append(result)
                print(f"{Color.GREEN}done{Color.RESET}")

            except Exception as e:
                self.status = "error"
                print(f"{Color.RED}failed: {e}{Color.RESET}")
                self.results.append(None)

        self.finished_at = datetime.now()
        self.status      = "done"

        elapsed = (self.finished_at -
                   self.started_at).total_seconds()

        print(f"{Color.GREEN}✓ Workflow '{self.name}' "
              f"complete in {elapsed:.2f}s{Color.RESET}")

        return self.results

    def last_result(self):
        """Return the result of the last step."""
        return self.results[-1] if self.results else None

    def __repr__(self):
        return (f"Workflow('{self.name}', "
                f"{len(self.steps)} steps, "
                f"status={self.status})")