# =============================================================
# NEKOVA Sandbox - run_sandboxed()
# Phase 19: Main API for sandboxed code execution
# Phase 29: every run executes in a supervised worker process, so
#           wall-clock, CPU, memory and output limits are enforced
#           from outside the program (see quota.py / worker.py)
# =============================================================

import json
import os
import queue
import subprocess
import sys
import threading
import time

from nekova.sandbox.result import SandboxResult
from nekova.sandbox.quota import (
    DEFAULT_LIMITS,
    EnforcerError,
    WallClockEnforcer,
    fallback_enforcer,
    normalize_limits,
    select_enforcer,
)

__all__ = ["run_sandboxed", "DEFAULT_LIMITS"]

_BOOT_TIMEOUT = 30         # seconds for the worker to start and say ready
_MAX_LINE = 256 * 1024     # longest frame the supervisor will accept
_STDERR_KEEP = 2000        # bytes of worker stderr kept for diagnostics

# directory that contains the `nekova` package, so the worker can import
# it even when the caller is running from a source checkout
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def _read_frames(stream, q, byte_cap):
    """Reader thread: parse the worker's JSON lines into a queue."""
    total = 0
    try:
        while True:
            line = stream.readline(_MAX_LINE + 1)
            if not line:
                break
            total += len(line)
            if len(line) > _MAX_LINE or total > byte_cap:
                q.put(("protocol", None))
                break
            try:
                q.put(("frame", json.loads(line)))
            except ValueError:
                q.put(("protocol", None))
                break
    except (OSError, ValueError):
        pass
    finally:
        q.put(None)  # end of stream


def _drain_stderr(stream, keep):
    """Reader thread: keep the tail of the worker's stderr."""
    try:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            keep.extend(chunk)
            if len(keep) > _STDERR_KEEP:
                del keep[:-_STDERR_KEEP]
    except (OSError, ValueError):
        pass


def _fmt(n):
    return f"{n:g}"


def _reap(proc, timeout=5):
    """Wait for the worker to exit, killing it if it will not."""
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass


def run_sandboxed(
    source: str,
    mode: str = "strict",
    limits: dict | None = None,
    allow: set | None = None,
) -> SandboxResult:
    """
    Run NEKOVA source code in an isolated, resource-limited sandbox.

    The program runs in its own worker process. The supervisor (this
    function) enforces:

        max_time         wall-clock seconds the program may run
        max_cpu_seconds  CPU seconds the program may use
        max_memory_mb    MB of memory the program may add
        max_output       characters of output kept

    A program that exceeds a limit is killed outright - the worker is
    a process, so unlike a thread it can always be stopped.

    Args:
        source   - NEKOVA source code string
        mode     - "strict" (default) | "relaxed"
        limits   - override DEFAULT_LIMITS (unknown keys raise ValueError)
        allow    - extra names to whitelist beyond the mode default

    Returns:
        SandboxResult with output, error, safe, duration, violations,
        plus worker_pid and enforced_by.
    """
    limits = normalize_limits(limits)
    result = SandboxResult(mode=mode)
    started = time.monotonic()
    max_output = int(limits["max_output"])

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # From a source checkout the worker needs the package root on its path
    # so it imports the same code as this process. When NEKOVA is pip
    # installed it is already importable, and putting site-packages ahead
    # of the standard library could shadow it, so leave the path alone.
    if not any(tag in _PKG_ROOT for tag in ("site-packages", "dist-packages")):
        env["PYTHONPATH"] = os.pathsep.join(
            [_PKG_ROOT] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

    popen_kw = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, env=env)
    if sys.platform == "win32":
        popen_kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    else:
        popen_kw["start_new_session"] = True    # own process group

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "nekova.sandbox.worker"], **popen_kw)
    except OSError as e:
        result.error = f"[sandbox:{mode}] Could not start worker: {e}"
        result.safe = False
        result.violations.append({"operation": "worker_crash", "mode": mode})
        result.duration = time.monotonic() - started
        return result

    frames = queue.Queue()
    stderr_tail = bytearray()
    byte_cap = max_output * 6 + 1024 * 1024
    threading.Thread(target=_read_frames, daemon=True,
                     args=(proc.stdout, frames, byte_cap)).start()
    threading.Thread(target=_drain_stderr, daemon=True,
                     args=(proc.stderr, stderr_tail)).start()

    enforcer = WallClockEnforcer()
    try:
        # ── 1. wait for the worker to finish booting ──────────
        ready = None
        boot_deadline = time.monotonic() + _BOOT_TIMEOUT
        while ready is None:
            try:
                item = frames.get(
                    timeout=max(boot_deadline - time.monotonic(), 0.01))
            except queue.Empty:
                break
            if item is None or item[0] == "protocol":
                break
            if item[1].get("t") == "ready":
                ready = item[1]

        if ready is None:
            enforcer.kill(proc)
            _reap(proc)
            tail = bytes(stderr_tail).decode("utf-8", "replace").strip()
            result.error = (f"[sandbox:{mode}] Worker failed to start."
                            + (f"\n  {tail}" if tail else ""))
            result.safe = False
            result.violations.append(
                {"operation": "worker_crash", "mode": mode})
            result.duration = time.monotonic() - started
            return result

        pid = int(ready["pid"])
        result.worker_pid = pid

        # ── 2. confine the worker BEFORE it sees the program ──
        directives = {}
        for candidate in (select_enforcer(), fallback_enforcer(),
                          WallClockEnforcer()):
            try:
                directives = candidate.attach(
                    proc, pid, limits, int(ready["mem"]),
                    float(ready["cpu"]))
                enforcer = candidate
                break
            except (EnforcerError, OSError):
                candidate.close()
        result.enforced_by = enforcer.name

        # ── 3. send the program ───────────────────────────────
        go = {
            "source": source,
            "mode": mode,
            "limits": {"max_output": max_output},
            "allow": sorted(allow) if allow else None,
            "directives": directives,
        }
        t_go = time.monotonic()
        try:
            proc.stdin.write(
                (json.dumps(go, ensure_ascii=True) + "\n").encode("ascii"))
            proc.stdin.flush()
            proc.stdin.close()
        except (OSError, ValueError):
            pass  # worker already gone; handled as a crash below

        # ── 4. supervise ──────────────────────────────────────
        parts = []
        overflow = False
        final = None
        timed_out = False
        protocol_error = False
        deadline = t_go + limits["max_time"]

        while True:
            if enforcer.violation:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                item = frames.get(timeout=min(remaining, 0.1))
            except queue.Empty:
                continue
            if item is None:
                break
            kind, frame = item
            if kind == "protocol":
                protocol_error = True
                break
            tag = frame.get("t")
            if tag == "out":
                parts.append(frame.get("d", ""))
            elif tag == "ovf":
                overflow = True
            elif tag == "res":
                final = frame
                break

        # ── 5. stop the worker and read what is left ──────────
        if final is None:
            enforcer.kill(proc)
        _reap(proc)
        # drain output the worker produced before it stopped
        while True:
            try:
                item = frames.get(timeout=0.5)
            except queue.Empty:
                break
            if item is None or item[0] == "protocol":
                break
            tag = item[1].get("t")
            if tag == "out":
                parts.append(item[1].get("d", ""))
            elif tag == "ovf":
                overflow = True
            elif tag == "res" and final is None and not timed_out:
                final = item[1]

        result.duration = time.monotonic() - t_go
        joined = "".join(parts)
        result.output = joined[:max_output]
        if len(joined) > max_output:
            overflow = True

        # ── 6. build the verdict ──────────────────────────────
        limit_hit = enforcer.violation
        if limit_hit is None and final is None and not timed_out:
            limit_hit = enforcer.classify_exit(proc.returncode)
        if final is not None and final.get("memory_limit"):
            limit_hit = "memory_limit"

        if timed_out:
            result.safe = False
            result.error = (f"[sandbox:{mode}] Execution timed out after "
                            f"{_fmt(limits['max_time'])}s.")
            result.violations.append({"operation": "timeout", "mode": mode})
        elif limit_hit == "memory_limit":
            result.safe = False
            result.error = (f"[sandbox:{mode}] Memory limit exceeded "
                            f"({_fmt(limits['max_memory_mb'])} MB).")
            result.violations.append(
                {"operation": "memory_limit", "mode": mode})
        elif limit_hit == "cpu_limit":
            result.safe = False
            result.error = (f"[sandbox:{mode}] CPU time limit exceeded "
                            f"({_fmt(limits['max_cpu_seconds'])}s).")
            result.violations.append({"operation": "cpu_limit", "mode": mode})
        elif final is not None:
            result.safe = bool(final.get("safe", False))
            result.error = final.get("error")
            result.violations.extend(final.get("violations", []))
        else:
            tail = bytes(stderr_tail).decode("utf-8", "replace").strip()
            why = ("sent an invalid message" if protocol_error else
                   f"terminated unexpectedly (exit code {proc.returncode})")
            result.safe = False
            result.error = (f"[sandbox:{mode}] Worker {why}."
                            + (f"\n  {tail}" if tail else ""))
            result.violations.append(
                {"operation": "worker_crash", "mode": mode})

        if overflow and "output_overflow" not in [
                v.get("operation") for v in result.violations]:
            result.safe = False
            result.violations.append(
                {"operation": "output_overflow", "mode": mode})
        return result

    finally:
        # never leave a worker, a pipe or a Job Object behind - this
        # also covers KeyboardInterrupt and any bug above
        if proc.poll() is None:
            enforcer.kill(proc)
        _reap(proc)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except (OSError, ValueError):
                pass
        enforcer.close()