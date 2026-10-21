# =============================================================
# NEKOVA Sandbox - worker process
# Phase 29: the process a sandboxed program actually runs in
#
# Started by runner.run_sandboxed() as:  python -m nekova.sandbox.worker
#
# Protocol (one JSON object per line):
#   worker -> supervisor   {"t":"ready","pid":N,"mem":BYTES,"cpu":SECS}
#   supervisor -> worker   {"source":..., "mode":..., "limits":{...},
#                           "allow":[...]|null, "directives":{...}}
#   worker -> supervisor   {"t":"out","d":TEXT}     (program output)
#                          {"t":"ovf"}              (output cap reached)
#                          {"t":"res", ...}         (final result)
#
# The worker waits for the supervisor's go-ahead before touching the
# program, so the supervisor can attach resource limits first - there
# is no window in which user code runs unconfined.
#
# Everything global the old in-process runner patched (builtins.open,
# builtins.__import__, sys.stdout) is patched here, in a process that
# exists for exactly one run - concurrent runs cannot interfere.
# =============================================================

import io
import json
import os
import sys
import time

_CHUNK = 16_384          # max characters per "out" frame
_MAX_ERROR_CHARS = 10_000
_MAX_VIOLATIONS = 200


class _StreamingOutput:
    """
    Replacement for sys.stdout while the program runs.

    Forwards output to the supervisor line-by-line (so partial output
    survives a kill) and stops at `limit` characters, discarding the
    rest - memory use stays bounded no matter how much the program
    prints.
    """

    def __init__(self, send, limit):
        self._send = send
        self._limit = limit
        self._sent = 0
        self._buf = []
        self._buf_len = 0
        self.overflow = False
        self.encoding = "utf-8"
        self.errors = "strict"

    def write(self, s):
        if not isinstance(s, str):
            s = str(s)
        n = len(s)
        if self.overflow:
            return n
        room = self._limit - self._sent - self._buf_len
        if n > room:
            s = s[:max(room, 0)]
            self.overflow = True
        if s:
            self._buf.append(s)
            self._buf_len += len(s)
        if self.overflow or "\n" in s or self._buf_len >= _CHUNK:
            self._drain()
        if self.overflow:
            self._send({"t": "ovf"})
        return n

    def _drain(self):
        if not self._buf:
            return
        text = "".join(self._buf)
        self._buf = []
        self._buf_len = 0
        for i in range(0, len(text), _CHUNK):
            piece = text[i:i + _CHUNK]
            self._sent += len(piece)
            self._send({"t": "out", "d": piece})

    def flush(self):
        self._drain()

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def isatty(self):
        return False

    def writable(self):
        return True

    def fileno(self):
        raise io.UnsupportedOperation("sandboxed output has no file descriptor")


def _chain_has(exc, kind):
    """True if `exc` or anything it was raised from/while handling is `kind`."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, kind):
            return True
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return False


def main():
    # Keep a private handle on the real stdout/stdin: the program only
    # ever sees the replacements installed further down.
    out_stream = sys.stdout.buffer
    in_stream = sys.stdin.buffer

    def send(obj):
        out_stream.write(
            (json.dumps(obj, ensure_ascii=True) + "\n").encode("ascii"))
        out_stream.flush()

    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter
    from nekova.interpreter.exceptions import NEKOVARuntimeError
    from nekova.sandbox.environment import (
        SandboxEnvironment, STRICT_ALLOWLIST, RELAXED_ALLOWLIST)
    from nekova.sandbox.quota import measure_memory_bytes, apply_directives

    # Pre-warm the stdlib .nk module cache before any import guards are
    # armed, so `use math`, `use string` etc. work inside a strict run.
    try:
        from nekova.stdlib.nk_loader import has_nk_module, load_nk_module
        for _mod in ["math", "string", "file", "date"]:
            if has_nk_module(_mod):
                load_nk_module(_mod)
    except Exception:
        pass  # best-effort

    send({"t": "ready", "pid": os.getpid(),
          "mem": measure_memory_bytes(), "cpu": time.process_time()})

    line = in_stream.readline()
    if not line:
        os._exit(3)  # supervisor went away before sending the program
    go = json.loads(line.decode("utf-8"))
    sys.stdin = io.StringIO("")  # the program gets no input channel

    source = go["source"]
    mode = go["mode"]
    limits = go["limits"]
    allow = go.get("allow")

    apply_directives(go.get("directives"))

    def finish(error, safe, violations, memory_limit=False):
        if error is not None and len(error) > _MAX_ERROR_CHARS:
            error = error[:_MAX_ERROR_CHARS] + "..."
        send({"t": "res", "error": error, "safe": safe,
              "violations": violations[:_MAX_VIOLATIONS],
              "memory_limit": memory_limit})
        out_stream.flush()
        os._exit(0)

    # ── Parse phase ───────────────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
    except MemoryError:
        finish(None, False, [], memory_limit=True)
    except Exception as e:
        finish(f"Parse error: {e}", False, [])

    # ── Build restricted interpreter ──────────────────────────
    interp = Interpreter()

    custom_allowlist = None
    if allow:
        base = RELAXED_ALLOWLIST if mode == "relaxed" else STRICT_ALLOWLIST
        custom_allowlist = base | set(allow)

    sandbox_env = SandboxEnvironment(
        parent=interp.globals,
        mode=mode,
        custom_allowlist=custom_allowlist,
    )
    interp.env = sandbox_env
    interp._sandbox_mode = mode

    # The while-loop cap is read lazily from nekova.toml the first time
    # a loop runs. Resolve it now, before the open() guard is armed -
    # otherwise that harmless read is recorded as a sandbox violation
    # on every strict run that contains a while loop.
    try:
        interp._get_max_loop_iterations()
    except Exception:
        pass

    # ── Block file/system access ──────────────────────────────
    import builtins
    patch_violations = []
    original_import = builtins.__import__

    def _blocked_open(*args, **kwargs):
        patch_violations.append({"operation": "open", "mode": mode})
        raise NEKOVARuntimeError(
            f"[sandbox:{mode}] File system access is blocked."
        )

    def _blocked_import(name, *args, **kwargs):
        dangerous = {"os", "sys", "subprocess", "socket", "shutil",
                     "pathlib", "tempfile", "ctypes", "importlib"}
        if name in dangerous:
            patch_violations.append(
                {"operation": f"import {name}", "mode": mode})
            raise NEKOVARuntimeError(
                f"[sandbox:{mode}] Importing '{name}' is blocked."
            )
        return original_import(name, *args, **kwargs)

    if mode == "strict":
        builtins.open = _blocked_open
        builtins.__import__ = _blocked_import

    # ── Run ───────────────────────────────────────────────────
    output = _StreamingOutput(send, int(limits["max_output"]))
    sys.stdout = output

    error = None
    safe = True
    memory_limit = False
    try:
        interp.run(ast)
    except NEKOVARuntimeError as e:
        if _chain_has(e, MemoryError):
            memory_limit = True
        else:
            msg = str(e)
            error = msg
            # Sandbox violations and resource limit hits mark unsafe
            unsafe_signals = ("sandbox", "too many times", "timed out",
                              "blocked", "not permitted")
            if any(sig in msg.lower() for sig in unsafe_signals):
                safe = False
    except MemoryError:
        memory_limit = True
    except SystemExit:
        pass  # the program called exit() - a normal end, not a failure
    except Exception as e:
        error = str(e) or type(e).__name__
        safe = False

    if memory_limit:
        # drop everything the program built so reporting has room
        interp = ast = tokens = sandbox_env = None
        import gc
        gc.collect()
        output.flush()
        finish(None, False, patch_violations, memory_limit=True)

    output.flush()

    violations = list(patch_violations)
    if output.overflow:
        safe = False
        violations.append({"operation": "output_overflow", "mode": mode})
    violations.extend(sandbox_env.violations)
    violations.extend(interp._sandbox_violations)
    finish(error, safe, violations)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        os._exit(2)