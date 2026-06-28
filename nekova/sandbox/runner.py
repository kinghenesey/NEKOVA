# =============================================================
# NEKOVA Sandbox — run_sandboxed()
# Phase 19: Main API for sandboxed code execution
# =============================================================

import io
import sys
import time
import threading
import builtins

from nekova.sandbox.result import SandboxResult
from nekova.sandbox.environment import SandboxEnvironment, ALWAYS_BLOCKED
from nekova.interpreter.exceptions import NEKOVARuntimeError


# Default resource limits
DEFAULT_LIMITS = {
    "max_time":        10,       # seconds
    "max_output":      50_000,   # characters
    "max_iterations":  100_000,  # loop iterations
}


def run_sandboxed(
    source: str,
    mode: str = "strict",
    limits: dict | None = None,
    allow: set | None = None,
) -> SandboxResult:
    """
    Run NEKOVA source code in an isolated sandbox.

    Args:
        source   — NEKOVA source code string
        mode     — "strict" (default) | "relaxed"
        limits   — override default resource limits
        allow    — extra names to whitelist beyond the mode default

    Returns:
        SandboxResult with output, error, safe, duration, violations
    """
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter

    limits = {**DEFAULT_LIMITS, **(limits or {})}
    result = SandboxResult(mode=mode)
    start  = time.monotonic()

    # ── Parse phase ───────────────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
        ast    = Parser(tokens).parse()
    except Exception as e:
        result.error    = f"Parse error: {e}"
        result.safe     = False
        result.duration = time.monotonic() - start
        return result

    # ── Build restricted interpreter ──────────────────────────
    interp = Interpreter()

    # Replace the global env with a sandbox env
    custom_allowlist = None
    if allow:
        from nekova.sandbox.environment import STRICT_ALLOWLIST, RELAXED_ALLOWLIST
        base = RELAXED_ALLOWLIST if mode == "relaxed" else STRICT_ALLOWLIST
        custom_allowlist = base | allow

    sandbox_env = SandboxEnvironment(
        parent=interp.globals,
        mode=mode,
        custom_allowlist=custom_allowlist,
    )
    interp.env = sandbox_env

    # Tell the interpreter which sandbox mode is active
    # so keyword executors (think, speak, etc.) can self-guard
    interp._sandbox_mode = mode

    # ── Patch builtins to block file/system access ────────────
    original_open   = builtins.open
    original_import = builtins.__import__

    def _blocked_open(*args, **kwargs):
        result.violations.append({"operation": "open", "mode": mode})
        raise NEKOVARuntimeError(
            f"[sandbox:{mode}] File system access is blocked."
        )

    def _blocked_import(name, *args, **kwargs):
        dangerous = {"os", "sys", "subprocess", "socket", "shutil",
                     "pathlib", "tempfile", "ctypes", "importlib"}
        if name in dangerous:
            result.violations.append({"operation": f"import {name}", "mode": mode})
            raise NEKOVARuntimeError(
                f"[sandbox:{mode}] Importing '{name}' is blocked."
            )
        return original_import(name, *args, **kwargs)

    # Pre-warm stdlib .nk module cache before blocking os/imports
    # This allows `use math`, `use string` etc. to work inside strict sandbox
    try:
        from nekova.stdlib.nk_loader import has_nk_module, load_nk_module
        for _mod in ["math", "string", "file", "date"]:
            if has_nk_module(_mod):
                load_nk_module(_mod)  # warms the cache
    except Exception:
        pass  # best-effort

    if mode == "strict":
        builtins.open     = _blocked_open
        builtins.__import__ = _blocked_import

    # ── Output capture ────────────────────────────────────────
    output_buf  = io.StringIO()
    old_stdout  = sys.stdout
    sys.stdout  = output_buf

    # ── Timeout enforcement ───────────────────────────────────
    exec_error  = [None]

    def _run():
        try:
            interp.run(ast)
        except NEKOVARuntimeError as e:
            msg = str(e)
            exec_error[0] = msg
            # Sandbox violations and resource limit hits mark unsafe
            unsafe_signals = ("sandbox", "too many times", "timed out",
                              "blocked", "not permitted")
            if any(sig in msg.lower() for sig in unsafe_signals):
                result.safe = False
        except Exception as e:
            exec_error[0] = str(e)
            result.safe = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=limits["max_time"])

    # ── Restore builtins ──────────────────────────────────────
    builtins.open       = original_open
    builtins.__import__ = original_import
    sys.stdout          = old_stdout

    # ── Check timeout ─────────────────────────────────────────
    if thread.is_alive():
        result.safe  = False
        result.error = (
            f"[sandbox:{mode}] Execution timed out after "
            f"{limits['max_time']}s."
        )
        result.violations.append({
            "operation": "timeout",
            "mode": mode
        })
        result.output   = output_buf.getvalue()
        result.duration = time.monotonic() - start
        return result

    # ── Collect results ───────────────────────────────────────
    raw_output = output_buf.getvalue()

    # Enforce output size limit
    if len(raw_output) > limits["max_output"]:
        raw_output  = raw_output[:limits["max_output"]]
        result.safe = False
        result.violations.append({
            "operation": "output_overflow",
            "mode": mode
        })

    result.output   = raw_output
    result.duration = time.monotonic() - start

    # Merge violations from sandbox env and interpreter
    result.violations.extend(sandbox_env.violations)
    result.violations.extend(interp._sandbox_violations)

    if exec_error[0]:
        result.error = exec_error[0]

    return result