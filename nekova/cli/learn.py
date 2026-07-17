# =============================================================
# NEKOVA CLI — nekova learn  (Phase 26b "Education Layer")
# =============================================================
# A guided, interactive tutorial that runs entirely in the
# terminal. Each lesson explains one concept, then asks for a
# real line of NEKOVA code and checks it against the real
# interpreter — not a canned string match against the input text,
# so paraphrased-but-correct answers ("let x = 5" vs "let  x=5")
# still pass.
#
# `run_lesson()` (checking logic) is kept separate from
# `cmd_learn()` (the interactive loop) specifically so lessons are
# unit-testable without an interactive terminal or input() calls.
# =============================================================

import io
import contextlib

from nekova.config import Color
from nekova.cli import print_error


class Lesson:
    __slots__ = ("title", "explanation", "task", "example_answer",
                 "hint", "check")

    def __init__(self, title, explanation, task, example_answer,
                 hint, check):
        self.title = title
        self.explanation = explanation
        self.task = task
        self.example_answer = example_answer
        self.hint = hint
        # check(code, output, interpreter) -> bool
        self.check = check


def _check_output_contains(*needles):
    def _check(code, output, interpreter):
        return all(n in output for n in needles)
    return _check


def _check_variable_equals(name, expected):
    def _check(code, output, interpreter):
        try:
            actual = interpreter.globals.get(name)
        except Exception:
            try:
                actual = interpreter.env.get(name)
            except Exception:
                return False
        return actual == expected
    return _check


LESSONS = [
    Lesson(
        title="Lesson 1 — Variables",
        explanation=(
            "NEKOVA variables are declared with 'let'. Try creating "
            "a variable called 'age' set to 25."
        ),
        task="Type a line that creates 'age' with the value 25.",
        example_answer="let age = 25",
        hint="It looks like:  let age = 25",
        check=_check_variable_equals("age", 25),
    ),
    Lesson(
        title="Lesson 2 — Printing",
        explanation=(
            "'show' prints a value to the terminal — NEKOVA's version "
            "of print. Try printing the text 'Hello, NEKOVA!'."
        ),
        task="Type a line that shows 'Hello, NEKOVA!'.",
        example_answer='show "Hello, NEKOVA!"',
        hint='It looks like:  show "Hello, NEKOVA!"',
        check=_check_output_contains("Hello, NEKOVA!"),
    ),
    Lesson(
        title="Lesson 3 — Conditionals",
        explanation=(
            "'if' branches on a condition, same as most languages. "
            "Try writing an if-statement that shows 'big' when a "
            "variable called 'n' (already set to 10 for you) is "
            "greater than 5."
        ),
        task="Type an if-statement that shows 'big' when n > 5.",
        example_answer='if n > 5: show "big"',
        hint='It looks like:  if n > 5: show "big"',
        check=_check_output_contains("big"),
    ),
    Lesson(
        title="Lesson 4 — Tasks",
        explanation=(
            "'task' declares a reusable function. Try declaring a "
            "task called 'double' that takes one argument and "
            "returns it multiplied by 2, all on one line."
        ),
        task="Type a one-line task 'double(x)' that returns x * 2.",
        example_answer="task double(x): return x * 2",
        hint="It looks like:  task double(x): return x * 2",
        check=None,  # set below to _check_lesson4 — needs a follow-up call
    ),
    Lesson(
        title="Lesson 5 — think",
        explanation=(
            "'think' is NEKOVA's AI-native keyword — it sends a "
            "prompt to an AI provider (the built-in mock provider, "
            "here) and returns the response, as a language keyword "
            "rather than a library you import. Try asking it "
            "something with 'as text'."
        ),
        task='Type a think call, e.g.  think "hello" as text',
        example_answer='think "hello" as text',
        hint='It looks like:  think "hello" as text',
        check=lambda code, output, interpreter: "think" in code,
    ),
]


def _check_lesson4(code, output, interpreter):
    """Lesson 4 needs the task to actually exist and behave right,
    checked separately since it needs a follow-up call."""
    try:
        from nekova.parser.nodes import TaskStatement, TypedTaskStatement
        task = interpreter.globals.get("double")
    except Exception:
        return False
    if task is None:
        return False
    try:
        if hasattr(task, "params"):
            result = interpreter._call_task(task, [5]) \
                if not isinstance(task, TypedTaskStatement) \
                else interpreter._call_typed_task(task, [5])
            return result == 10
    except Exception:
        return False
    return False


LESSONS[3].check = _check_lesson4


def run_lesson(lesson: Lesson, code: str):
    """
    Execute `code` against a fresh interpreter (with lesson-specific
    setup for lessons that reference a pre-set variable), capture
    its stdout, and report whether the lesson's check passed.

    Returns (passed: bool, output: str, error: str).
    Pure w.r.t. the outside world except for the interpreter run
    itself — no input() calls — so this is directly unit-testable.
    """
    from nekova.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter

    interpreter = Interpreter()
    # Lesson 3 references a pre-set 'n' — set it up before the
    # learner's own code runs, same as the lesson text promises.
    if lesson is LESSONS[2]:
        interpreter.globals.set("n", 10)

    output = ""
    error = ""
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tokens = Lexer(code).tokenize()
            program = Parser(tokens).parse()
            interpreter.execute(program, filepath="<learn>")
        output = buf.getvalue()
    except Exception as e:
        error = str(e)
        return False, output, error

    try:
        passed = lesson.check(code, output, interpreter)
    except Exception:
        passed = False

    return passed, output, error


def cmd_learn():
    """
    Run the full interactive tutorial. Each lesson gets up to 3
    attempts before moving on with the example answer shown, so a
    stuck beginner isn't blocked from seeing the rest of the
    tutorial.
    """
    print(f"\n{Color.CYAN}{Color.BOLD}NEKOVA Interactive Tutorial"
          f"{Color.RESET}")
    print(f"{Color.DIM}Type real NEKOVA code at each prompt — it runs "
          f"against the actual interpreter. Ctrl+C or Ctrl+D to stop "
          f"any time.{Color.RESET}\n")

    completed = 0
    for lesson in LESSONS:
        print(f"{Color.CYAN}{Color.BOLD}{lesson.title}{Color.RESET}")
        print(f"  {lesson.explanation}")
        print(f"  {Color.DIM}{lesson.task}{Color.RESET}\n")

        solved = False
        for attempt in range(3):
            try:
                code = input(f"  {Color.GREEN}nekova>{Color.RESET} ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Color.YELLOW}Stopping tutorial.{Color.RESET}")
                _print_summary(completed, len(LESSONS))
                return

            if not code.strip():
                continue

            passed, output, error = run_lesson(lesson, code)
            if passed:
                print(f"  {Color.GREEN}✓ Correct!{Color.RESET}\n")
                solved = True
                completed += 1
                break
            else:
                remaining = 2 - attempt
                if error:
                    print(f"  {Color.YELLOW}That raised an error: "
                          f"{error}{Color.RESET}")
                else:
                    print(f"  {Color.YELLOW}Not quite.{Color.RESET}")
                if remaining > 0:
                    print(f"  {Color.DIM}Hint: {lesson.hint} "
                          f"({remaining} attempt(s) left){Color.RESET}\n")

        if not solved:
            print(f"  {Color.DIM}Moving on — the answer was: "
                  f"{lesson.example_answer}{Color.RESET}\n")

    _print_summary(completed, len(LESSONS))


def _print_summary(completed: int, total: int):
    print(f"{Color.CYAN}{Color.BOLD}Tutorial complete: "
          f"{completed}/{total} lessons solved.{Color.RESET}")
    if completed == total:
        print(f"{Color.GREEN}Nice work — you've covered variables, "
              f"printing, conditionals, tasks, and think.{Color.RESET}")
    print(f"{Color.DIM}Run 'nekova help <topic>' any time for a "
          f"refresher on a specific keyword.{Color.RESET}\n")