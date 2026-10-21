# =============================================================
# NEKOVA Sandbox - resource quotas
# Phase 29: kernel-enforced CPU / memory limits for run_sandboxed()
#
# run_sandboxed() runs every program in a supervised worker process.
# This module decides HOW that worker is confined on each platform:
#
#   Windows  -> Job Object        (enforced_by = "job-object")
#   Linux    -> setrlimit         (enforced_by = "rlimit")
#   other    -> polling watchdog  (enforced_by = "watchdog", best-effort)
#   fallback -> wall-clock only   (enforced_by = "wall-clock")
#
# Limit semantics (identical on every platform):
#   max_memory_mb    memory the PROGRAM may add on top of the bare
#                    interpreter's own footprint (measured by the worker
#                    after it has finished booting)
#   max_cpu_seconds  CPU time the PROGRAM may use on top of the
#                    worker's boot cost. POSIX rounds up to a whole
#                    second; the Windows check is periodic, so it can
#                    overshoot slightly.
# =============================================================

import ctypes
import math
import os
import signal
import sys
import threading
import time

# ── Limits ────────────────────────────────────────────────────

DEFAULT_LIMITS = {
    "max_time":        10,       # seconds, wall clock
    "max_output":      50_000,   # characters
    "max_iterations":  100_000,  # loop iterations (reserved)
    "max_memory_mb":   256,      # MB the program may add
    "max_cpu_seconds": 10,       # CPU seconds the program may use
}

# Smallest accepted max_memory_mb. Below this the interpreter itself
# cannot reliably run, so the limit would just produce confusing
# crashes instead of a clean "memory limit exceeded".
MIN_MEMORY_MB = 16

# Slack added to the memory ceiling for allocator arenas and
# bookkeeping, so a program that honestly fits in max_memory_mb is
# never killed by jitter.
_HEADROOM_MB = 16

_MB = 1024 * 1024


def normalize_limits(limits: dict | None) -> dict:
    """
    Merge user overrides over DEFAULT_LIMITS and validate them.

    Raises ValueError for unknown keys (a typo such as "max_memroy_mb"
    must never silently leave a run with no memory limit), for
    non-numeric or non-positive values, and for max_memory_mb below
    MIN_MEMORY_MB. Neither argument is mutated.
    """
    merged = dict(DEFAULT_LIMITS)
    for key, value in (limits or {}).items():
        if key not in DEFAULT_LIMITS:
            raise ValueError(
                f"Unknown sandbox limit {key!r}. "
                f"Valid limits: {', '.join(sorted(DEFAULT_LIMITS))}."
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"Sandbox limit {key!r} must be a number, got {value!r}."
            )
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"Sandbox limit {key!r} must be greater than 0, "
                f"got {value!r}."
            )
        merged[key] = value
    if merged["max_memory_mb"] < MIN_MEMORY_MB:
        raise ValueError(
            f"Sandbox limit 'max_memory_mb' must be at least "
            f"{MIN_MEMORY_MB} MB, got {merged['max_memory_mb']!r}."
        )
    return merged


# ── Win32 structures (platform-neutral so their layout can be
#    verified on any OS - see TestJobObjectLayout) ─────────────

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount",  ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount",   ctypes.c_uint64),
        ("WriteTransferCount",  ctypes.c_uint64),
        ("OtherTransferCount",  ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),    # LARGE_INTEGER
        ("PerJobUserTimeLimit",     ctypes.c_int64),    # LARGE_INTEGER
        ("LimitFlags",              ctypes.c_uint32),   # DWORD
        ("MinimumWorkingSetSize",   ctypes.c_size_t),   # SIZE_T
        ("MaximumWorkingSetSize",   ctypes.c_size_t),   # SIZE_T
        ("ActiveProcessLimit",      ctypes.c_uint32),   # DWORD
        ("Affinity",                ctypes.c_size_t),   # ULONG_PTR
        ("PriorityClass",           ctypes.c_uint32),   # DWORD
        ("SchedulingClass",         ctypes.c_uint32),   # DWORD
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo",                IO_COUNTERS),
        ("ProcessMemoryLimit",    ctypes.c_size_t),
        ("JobMemoryLimit",        ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed",     ctypes.c_size_t),
    ]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime",             ctypes.c_int64),
        ("TotalKernelTime",           ctypes.c_int64),
        ("ThisPeriodTotalUserTime",   ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount",       ctypes.c_uint32),
        ("TotalProcesses",            ctypes.c_uint32),
        ("ActiveProcesses",           ctypes.c_uint32),
        ("TotalTerminatedProcesses",  ctypes.c_uint32),
    ]


class _PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb",                         ctypes.c_uint32),
        ("PageFaultCount",             ctypes.c_uint32),
        ("PeakWorkingSetSize",         ctypes.c_size_t),
        ("WorkingSetSize",             ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage",    ctypes.c_size_t),
        ("QuotaPagedPoolUsage",        ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage",     ctypes.c_size_t),
        ("PagefileUsage",              ctypes.c_size_t),
        ("PeakPagefileUsage",          ctypes.c_size_t),
        ("PrivateUsage",               ctypes.c_size_t),
    ]


JOB_OBJECT_LIMIT_PROCESS_TIME       = 0x00000002
JOB_OBJECT_LIMIT_ACTIVE_PROCESS     = 0x00000008
JOB_OBJECT_LIMIT_PROCESS_MEMORY     = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE  = 0x00002000

_JobObjectBasicAccountingInformation = 1
_JobObjectExtendedLimitInformation   = 9

_PROCESS_TERMINATE          = 0x0001
_PROCESS_SET_QUOTA          = 0x0100
_PROCESS_QUERY_INFORMATION  = 0x0400


class EnforcerError(RuntimeError):
    """A backend could not confine the worker (caller falls back)."""


# ── Worker-side measurements and self-applied limits ──────────

def measure_memory_bytes() -> int:
    """
    The calling process's current footprint, in the unit its
    platform's limit is expressed in:
      Linux   - virtual address space (what RLIMIT_AS limits)
      Windows - committed private bytes (what Job Objects limit)
      other   - peak resident set size
    """
    if sys.platform == "win32":
        pmc = _PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = ctypes.sizeof(pmc)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        fn = getattr(kernel32, "K32GetProcessMemoryInfo", None)
        if fn is None:
            fn = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
        if not fn(kernel32.GetCurrentProcess(), ctypes.byref(pmc),
                  ctypes.sizeof(pmc)):
            raise OSError("GetProcessMemoryInfo failed")
        return int(pmc.PrivateUsage)
    if sys.platform.startswith("linux"):
        with open("/proc/self/statm", "rb") as f:
            pages = int(f.read().split()[0])
        return pages * os.sysconf("SC_PAGE_SIZE")
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is bytes on macOS, kilobytes on the BSDs
    return int(peak if sys.platform == "darwin" else peak * 1024)


def apply_directives(directives: dict | None) -> None:
    """
    Called inside the worker, just before the program runs, to apply
    limits a POSIX kernel only lets a process set on itself.
    """
    if not directives:
        return
    import resource

    def _clamp(res, wanted):
        # never ask for more than an already-lower hard limit allows
        _soft, hard = resource.getrlimit(res)
        if hard != resource.RLIM_INFINITY:
            wanted = min(wanted, hard)
        return wanted

    mem = directives.get("rlimit_as")
    if mem is not None:
        mem = _clamp(resource.RLIMIT_AS, int(mem))
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))

    cpu = directives.get("rlimit_cpu")
    if cpu is not None:
        # soft < hard on purpose: reaching the soft limit delivers
        # SIGXCPU (cleanly identifiable); soft == hard would be a
        # bare SIGKILL we could not tell apart from an OOM kill.
        soft = _clamp(resource.RLIMIT_CPU, int(cpu))
        hard = _clamp(resource.RLIMIT_CPU, soft + 2)
        resource.setrlimit(resource.RLIMIT_CPU, (soft, hard))


# ── Backends ──────────────────────────────────────────────────

class _Enforcer:
    """Interface every backend implements."""
    name = ""
    violation = None  # "memory_limit" | "cpu_limit" once a watchdog fires

    def attach(self, proc, pid, limits, baseline_bytes, baseline_cpu) -> dict:
        """Confine the worker. Returns directives the worker applies
        to itself (POSIX). Raises EnforcerError on failure."""
        raise NotImplementedError

    def classify_exit(self, returncode) -> str | None:
        """Map an abnormal worker exit to a limit violation, if any."""
        return self.violation

    def kill(self, proc) -> None:
        try:
            proc.kill()
        except OSError:
            pass

    def close(self) -> None:
        pass


class RlimitEnforcer(_Enforcer):
    """Linux: the worker applies RLIMIT_AS / RLIMIT_CPU to itself."""
    name = "rlimit"

    def attach(self, proc, pid, limits, baseline_bytes, baseline_cpu):
        ceiling = baseline_bytes + int(
            (limits["max_memory_mb"] + _HEADROOM_MB) * _MB)
        cpu = int(math.ceil(baseline_cpu + limits["max_cpu_seconds"]))
        return {"rlimit_as": ceiling, "rlimit_cpu": max(cpu, 1)}

    def classify_exit(self, returncode):
        if returncode is not None and returncode == -int(signal.SIGXCPU):
            return "cpu_limit"
        return None

    def kill(self, proc):
        try:
            # the worker leads its own session (start_new_session)
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, AttributeError):
            try:
                proc.kill()
            except OSError:
                pass


class JobObjectEnforcer(_Enforcer):
    """
    Windows: put the worker in a Job Object with a per-process memory
    ceiling, a per-process user-time limit, a one-process active
    limit (the worker cannot spawn children) and kill-on-close (the
    worker dies if the supervisor does).

    The Job Object is attached to the worker's self-reported PID, not
    to Popen's: a venv's python.exe is a launcher that spawns the real
    interpreter as a child, and limiting the launcher would leave the
    real interpreter unconstrained.
    """
    name = "job-object"

    def __init__(self):
        self._job = None
        self._proc_handle = None
        self._cpu_limit_100ns = None
        self._k32 = None

    def _kernel32(self):
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.restype = ctypes.c_void_p
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        k.SetInformationJobObject.restype = ctypes.c_int
        k.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        k.QueryInformationJobObject.restype = ctypes.c_int
        k.QueryInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_void_p]
        k.OpenProcess.restype = ctypes.c_void_p
        k.OpenProcess.argtypes = [
            ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k.AssignProcessToJobObject.restype = ctypes.c_int
        k.AssignProcessToJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p]
        k.TerminateJobObject.restype = ctypes.c_int
        k.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k.CloseHandle.restype = ctypes.c_int
        k.CloseHandle.argtypes = [ctypes.c_void_p]
        return k

    def attach(self, proc, pid, limits, baseline_bytes, baseline_cpu):
        if sys.platform != "win32":
            raise EnforcerError("Job Objects exist only on Windows")
        k = self._k32 = self._kernel32()

        job = k.CreateJobObjectW(None, None)
        if not job:
            raise EnforcerError(
                f"CreateJobObject failed (error {ctypes.get_last_error()})")
        self._job = job

        self._cpu_limit_100ns = int(
            (baseline_cpu + limits["max_cpu_seconds"]) * 10_000_000)
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        basic = info.BasicLimitInformation
        basic.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_PROCESS_TIME
        )
        basic.ActiveProcessLimit = 1
        basic.PerProcessUserTimeLimit = self._cpu_limit_100ns
        info.ProcessMemoryLimit = baseline_bytes + int(
            (limits["max_memory_mb"] + _HEADROOM_MB) * _MB)
        if not k.SetInformationJobObject(
                job, _JobObjectExtendedLimitInformation,
                ctypes.byref(info), ctypes.sizeof(info)):
            raise EnforcerError(
                f"SetInformationJobObject failed "
                f"(error {ctypes.get_last_error()})")

        handle = k.OpenProcess(
            _PROCESS_SET_QUOTA | _PROCESS_TERMINATE
            | _PROCESS_QUERY_INFORMATION, 0, pid)
        if not handle:
            raise EnforcerError(
                f"OpenProcess failed (error {ctypes.get_last_error()})")
        self._proc_handle = handle
        if not k.AssignProcessToJobObject(job, handle):
            raise EnforcerError(
                f"AssignProcessToJobObject failed "
                f"(error {ctypes.get_last_error()})")
        return {}

    def classify_exit(self, returncode):
        # The kernel terminates a process that passes its user-time
        # limit without any distinguishing exit code, so ask the job
        # how much user time its process really accumulated.
        if self._job and self._cpu_limit_100ns:
            acct = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            if self._k32.QueryInformationJobObject(
                    self._job, _JobObjectBasicAccountingInformation,
                    ctypes.byref(acct), ctypes.sizeof(acct), None):
                if acct.TotalUserTime >= self._cpu_limit_100ns * 0.9:
                    return "cpu_limit"
        return None

    def kill(self, proc):
        if self._job and self._k32:
            self._k32.TerminateJobObject(self._job, 1)
        try:
            proc.kill()  # the launcher process, if there is one
        except OSError:
            pass

    def close(self):
        k = self._k32
        if not k:
            return
        # closing the job handle also kills anything left in it
        # (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        for attr in ("_proc_handle", "_job"):
            h = getattr(self, attr)
            if h:
                k.CloseHandle(h)
                setattr(self, attr, None)


def _sample_process(pid):
    """(resident bytes, cpu seconds) of a process, or None if gone."""
    try:
        if sys.platform.startswith("linux"):
            with open(f"/proc/{pid}/statm", "rb") as f:
                rss = int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
            with open(f"/proc/{pid}/stat", "rb") as f:
                fields = f.read().rsplit(b")", 1)[1].split()
            ticks = int(fields[11]) + int(fields[12])  # utime + stime
            return rss, ticks / os.sysconf("SC_CLK_TCK")
        import subprocess
        out = subprocess.run(
            ["ps", "-o", "rss=,time=", "-p", str(pid)],
            capture_output=True, text=True, timeout=2).stdout.split()
        if len(out) < 2:
            return None
        cpu = 0.0
        for part in out[1].replace("-", ":").split(":"):
            cpu = cpu * 60 + float(part)
        return int(out[0]) * 1024, cpu
    except (OSError, ValueError, IndexError):
        return None


class WatchdogEnforcer(_Enforcer):
    """
    Best-effort fallback (macOS, or a hard backend that failed): a
    thread samples the worker every 20 ms and kills it when it is over
    limit. Unlike the hard backends, memory can spike between samples,
    so SandboxResult.enforced_by says "watchdog" and callers must not
    treat it as a guarantee.
    """
    name = "watchdog"
    _POLL = 0.02

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None
        self._proc = None

    def attach(self, proc, pid, limits, baseline_bytes, baseline_cpu):
        self._proc = proc
        mem_ceiling = baseline_bytes + int(
            (limits["max_memory_mb"] + _HEADROOM_MB) * _MB)
        cpu_ceiling = baseline_cpu + limits["max_cpu_seconds"]

        def watch():
            while not self._stop.wait(self._POLL):
                sample = _sample_process(pid)
                if sample is None:
                    return
                rss, cpu = sample
                if rss > mem_ceiling:
                    self.violation = "memory_limit"
                elif cpu > cpu_ceiling:
                    self.violation = "cpu_limit"
                else:
                    continue
                self.kill(proc)
                return

        self._thread = threading.Thread(target=watch, daemon=True)
        self._thread.start()
        return {}

    def kill(self, proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, AttributeError):
            try:
                proc.kill()
            except OSError:
                pass

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)


class WallClockEnforcer(_Enforcer):
    """Last resort: only the supervisor's wall-clock timeout applies."""
    name = "wall-clock"

    def attach(self, proc, pid, limits, baseline_bytes, baseline_cpu):
        return {}


def select_enforcer() -> _Enforcer:
    """The strongest backend this platform offers."""
    if sys.platform == "win32":
        return JobObjectEnforcer()
    if sys.platform.startswith("linux"):
        return RlimitEnforcer()
    return WatchdogEnforcer()


def fallback_enforcer() -> _Enforcer:
    """Used when select_enforcer()'s backend fails to attach."""
    if sys.platform == "win32":
        return WallClockEnforcer()
    return WatchdogEnforcer()