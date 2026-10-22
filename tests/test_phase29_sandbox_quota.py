"""
Phase 29 (step 1) - Sandbox resource quotas

run_sandboxed() now executes every run in a supervised worker process
so that wall-clock, CPU-time, memory and output limits are real,
kernel-enforced boundaries instead of a daemon thread that can never
be killed.

Covers:
  - limit validation / defaults            (TestLimitNormalization)
  - Windows Job Object struct layouts      (TestJobObjectLayout)
  - supervised-process behaviour           (TestSupervisedRun)
  - behaviour parity with the old runner   (TestParity)
  - hard limits actually enforced          (TestHardLimits)
  - the `nekova run --sandbox` CLI flags   (TestSandboxCLI)

Platform notes: the Job Object backend can only be exercised on
Windows. Everything else here runs on any OS, and TestHardLimits
asserts that the *hard* backend (rlimit / job-object) was really the
one that enforced the limit - a silent fall-back to the best-effort
watchdog on Linux or Windows is reported as a failure.
"""
import builtins
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from nekova.sandbox import run_sandboxed, SandboxResult

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ~25M interpreted iterations: far longer than any limit used below
BURN = (
    "let t = 0\n"
    "for i in range(5000):\n"
    "    for j in range(5000):\n"
    "        let t = t + 1\n"
    "show t\n"
)

# Doubles a string until it would need terabytes
MEMORY_BOMB = (
    'let s = "abcdefgh"\n'
    "for i in range(60):\n"
    "    let s = s + s\n"
    "show len(s)\n"
)

KNOWN_BACKENDS = {"rlimit", "job-object", "watchdog", "wall-clock"}


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid is still running (not a zombie)."""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        handle = kernel32.OpenProcess(0x1000, 0, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(ctypes.c_void_p(handle),
                                               ctypes.byref(code)):
                return True
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open("/proc/%d/stat" % pid, "rb") as f:
            state = f.read().rsplit(b")", 1)[1].split()[0]
        return state != b"Z"
    except (OSError, IndexError):
        return True


def _wait_dead(pid: int, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return not _pid_alive(pid)


# ── limit validation ─────────────────────────────────────────

class TestLimitNormalization(unittest.TestCase):

    def setUp(self):
        from nekova.sandbox import quota
        self.quota = quota

    def test_defaults_include_memory_and_cpu(self):
        d = self.quota.DEFAULT_LIMITS
        self.assertIn("max_memory_mb", d)
        self.assertIn("max_cpu_seconds", d)
        # the three original limits are unchanged
        self.assertEqual(d["max_time"], 10)
        self.assertEqual(d["max_output"], 50_000)
        self.assertEqual(d["max_iterations"], 100_000)

    def test_runner_still_exports_default_limits(self):
        from nekova.sandbox.runner import DEFAULT_LIMITS
        self.assertEqual(DEFAULT_LIMITS, self.quota.DEFAULT_LIMITS)

    def test_overrides_merge_over_defaults(self):
        out = self.quota.normalize_limits({"max_memory_mb": 64})
        self.assertEqual(out["max_memory_mb"], 64)
        self.assertEqual(out["max_time"], self.quota.DEFAULT_LIMITS["max_time"])

    def test_none_gives_defaults(self):
        self.assertEqual(self.quota.normalize_limits(None),
                         self.quota.DEFAULT_LIMITS)

    def test_does_not_mutate_inputs(self):
        before = dict(self.quota.DEFAULT_LIMITS)
        given = {"max_time": 3}
        self.quota.normalize_limits(given)
        self.assertEqual(self.quota.DEFAULT_LIMITS, before)
        self.assertEqual(given, {"max_time": 3})

    def test_unknown_key_rejected(self):
        # a typo like max_memroy_mb must not be silently ignored -
        # that would leave the run with no memory limit at all
        with self.assertRaises(ValueError) as cm:
            self.quota.normalize_limits({"max_memroy_mb": 64})
        self.assertIn("max_memroy_mb", str(cm.exception))

    def test_non_positive_rejected(self):
        for key in ("max_time", "max_output", "max_memory_mb",
                    "max_cpu_seconds"):
            for bad in (0, -1):
                with self.assertRaises(ValueError, msg="%s=%r" % (key, bad)):
                    self.quota.normalize_limits({key: bad})

    def test_non_numeric_rejected(self):
        for bad in ("64", None, [64], True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.quota.normalize_limits({"max_memory_mb": bad})

    def test_memory_floor_enforced(self):
        with self.assertRaises(ValueError):
            self.quota.normalize_limits(
                {"max_memory_mb": self.quota.MIN_MEMORY_MB - 1})
        # the floor itself is accepted
        self.quota.normalize_limits(
            {"max_memory_mb": self.quota.MIN_MEMORY_MB})

    def test_run_sandboxed_rejects_bad_limits_before_spawning(self):
        with self.assertRaises(ValueError):
            run_sandboxed("show 1", limits={"max_memroy_mb": 64})

    def test_select_enforcer_matches_platform(self):
        name = self.quota.select_enforcer().name
        self.assertIn(name, KNOWN_BACKENDS)
        if sys.platform == "win32":
            self.assertEqual(name, "job-object")
        elif sys.platform.startswith("linux"):
            self.assertEqual(name, "rlimit")


# ── Windows Job Object struct layouts (checkable on any OS) ──

@unittest.skipUnless(ctypes.sizeof(ctypes.c_void_p) == 8,
                     "layout constants below are for 64-bit")
class TestJobObjectLayout(unittest.TestCase):
    """
    A wrong ctypes layout makes SetInformationJobObject fail or, worse,
    silently apply garbage limits. These sizes are the documented
    64-bit Win32 sizes and can be verified without a Windows machine.
    """

    def setUp(self):
        from nekova.sandbox import quota
        self.q = quota

    def test_io_counters(self):
        self.assertEqual(ctypes.sizeof(self.q.IO_COUNTERS), 48)

    def test_basic_limit_information(self):
        self.assertEqual(
            ctypes.sizeof(self.q.JOBOBJECT_BASIC_LIMIT_INFORMATION), 64)

    def test_extended_limit_information(self):
        self.assertEqual(
            ctypes.sizeof(self.q.JOBOBJECT_EXTENDED_LIMIT_INFORMATION), 144)

    def test_basic_accounting_information(self):
        self.assertEqual(
            ctypes.sizeof(self.q.JOBOBJECT_BASIC_ACCOUNTING_INFORMATION), 48)

    def test_extended_field_offsets(self):
        ext = self.q.JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        self.assertEqual(ext.BasicLimitInformation.offset, 0)
        self.assertEqual(ext.IoInfo.offset, 64)
        self.assertEqual(ext.ProcessMemoryLimit.offset, 112)
        self.assertEqual(ext.JobMemoryLimit.offset, 120)

    def test_limit_flag_values(self):
        # documented Win32 constants
        self.assertEqual(self.q.JOB_OBJECT_LIMIT_PROCESS_TIME, 0x2)
        self.assertEqual(self.q.JOB_OBJECT_LIMIT_ACTIVE_PROCESS, 0x8)
        self.assertEqual(self.q.JOB_OBJECT_LIMIT_PROCESS_MEMORY, 0x100)
        self.assertEqual(self.q.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, 0x2000)


class _FakeKernel32:
    """Stands in for kernel32 so the Job Object CPU watcher's logic can
    be exercised on any OS. Each poll reports more CPU time."""

    def __init__(self, ticks_per_poll, alive=True):
        self.polls = 0
        self.ticks = ticks_per_poll
        self.alive = alive
        self.terminated = False

    def QueryInformationJobObject(self, job, info_class, ref, size, ret):
        if not self.alive:
            return 0
        self.polls += 1
        ref._obj.TotalUserTime = self.polls * self.ticks
        return 1

    def TerminateJobObject(self, job, code):
        self.terminated = True
        return 1


class _FakeProc:
    killed = False

    def kill(self):
        self.killed = True


class TestJobObjectCpuWatcher(unittest.TestCase):
    """
    The kernel checks a Job Object's time limit only periodically, so
    the supervisor polls CPU accounting itself. The Win32 calls cannot
    run off Windows, but the watcher's decisions can be tested.
    """

    def _enforcer(self, fake):
        from nekova.sandbox.quota import JobObjectEnforcer
        e = JobObjectEnforcer()
        e._POLL = 0.001
        e._k32 = fake
        e._job = 1234
        return e

    def test_terminates_the_job_when_the_budget_is_spent(self):
        fake, proc = _FakeKernel32(ticks_per_poll=100), _FakeProc()
        e = self._enforcer(fake)
        e._watch_cpu(proc, budget_100ns=1000)  # reached on the 10th poll
        self.assertEqual(e.violation, "cpu_limit")
        self.assertTrue(fake.terminated)
        self.assertTrue(proc.killed)
        self.assertEqual(fake.polls, 10)

    def test_does_nothing_while_under_budget(self):
        fake, proc = _FakeKernel32(ticks_per_poll=1), _FakeProc()
        e = self._enforcer(fake)
        e._stop.set()  # the supervisor is done before the budget is hit
        e._watch_cpu(proc, budget_100ns=10 ** 12)
        self.assertIsNone(e.violation)
        self.assertFalse(fake.terminated)
        self.assertFalse(proc.killed)

    def test_exits_quietly_when_the_job_is_gone(self):
        fake, proc = _FakeKernel32(1, alive=False), _FakeProc()
        e = self._enforcer(fake)
        e._watch_cpu(proc, budget_100ns=1)
        self.assertIsNone(e.violation)
        self.assertFalse(proc.killed)


# ── supervised-process behaviour (all platforms) ─────────────

class TestSupervisedRun(unittest.TestCase):

    def test_result_reports_worker_and_backend(self):
        r = run_sandboxed("show 1")
        self.assertIsInstance(r, SandboxResult)
        self.assertIsInstance(r.worker_pid, int)
        self.assertIn(r.enforced_by, KNOWN_BACKENDS)

    def test_runs_in_a_separate_process(self):
        r = run_sandboxed("show 1")
        self.assertNotEqual(r.worker_pid, os.getpid())

    def test_worker_exits_after_normal_run(self):
        r = run_sandboxed("show 1")
        self.assertTrue(_wait_dead(r.worker_pid),
                        "worker %s still alive after a normal run"
                        % r.worker_pid)

    def test_timeout_kills_the_worker_process(self):
        start = time.monotonic()
        r = run_sandboxed(BURN, limits={"max_time": 1})
        took = time.monotonic() - start
        self.assertFalse(r.safe)
        self.assertIn("timed out", (r.error or "").lower())
        self.assertIn("timeout", [v["operation"] for v in r.violations])
        self.assertLess(took, 8)
        self.assertTrue(_wait_dead(r.worker_pid),
                        "timed-out worker %s was left running" % r.worker_pid)

    def test_timeout_leaks_no_threads(self):
        before = threading.active_count()
        run_sandboxed(BURN, limits={"max_time": 1})
        time.sleep(1.5)
        self.assertLessEqual(threading.active_count(), before)

    def test_parent_builtins_never_patched_during_a_run(self):
        orig_open = builtins.open
        orig_import = builtins.__import__
        orig_stdout = sys.stdout
        box = {}

        def go():
            box["r"] = run_sandboxed(BURN, limits={"max_time": 2})

        t = threading.Thread(target=go)
        t.start()
        try:
            time.sleep(0.8)  # the run is mid-flight here
            self.assertIs(builtins.open, orig_open)
            self.assertIs(builtins.__import__, orig_import)
            self.assertIs(sys.stdout, orig_stdout)
        finally:
            t.join(30)
        self.assertIs(builtins.open, orig_open)
        self.assertIs(builtins.__import__, orig_import)
        self.assertIs(sys.stdout, orig_stdout)

    def test_concurrent_runs_do_not_mix_output(self):
        prog_a = 'for i in range(50):\n    show "AAA"\n'
        prog_b = 'for i in range(50):\n    show "BBB"\n'
        results = {}

        def go(key, src):
            results[key] = run_sandboxed(src)

        for _ in range(3):
            ta = threading.Thread(target=go, args=("a", prog_a))
            tb = threading.Thread(target=go, args=("b", prog_b))
            ta.start(); tb.start()
            ta.join(60); tb.join(60)
            self.assertEqual(results["a"].output.split(), ["AAA"] * 50)
            self.assertEqual(results["b"].output.split(), ["BBB"] * 50)
            self.assertNotEqual(results["a"].worker_pid,
                                results["b"].worker_pid)

    def test_output_limit_is_exact_and_flagged(self):
        r = run_sandboxed(
            'for i in range(100000):\n    show "x" * 1000\n',
            limits={"max_output": 1000, "max_time": 6},
        )
        self.assertLessEqual(len(r.output), 1000)
        self.assertFalse(r.safe)
        self.assertIn("output_overflow",
                      [v["operation"] for v in r.violations])

    def test_parent_survives_a_worker_that_dies(self):
        # whatever happens inside the worker, the caller gets a result
        r = run_sandboxed(MEMORY_BOMB, limits={"max_memory_mb": 64})
        self.assertIsInstance(r, SandboxResult)
        self.assertFalse(r.ok)
        self.assertEqual(run_sandboxed("show 7").output.strip(), "7")


# ── behaviour parity with the previous in-process runner ─────

class TestParity(unittest.TestCase):
    """Goldens recorded from the in-process runner before the move."""

    def test_arithmetic(self):
        r = run_sandboxed("show 1 + 1")
        self.assertEqual(r.output, "2\n")
        self.assertTrue(r.ok)
        self.assertEqual(r.violations, [])

    def test_multiple_outputs_in_order(self):
        r = run_sandboxed('show 1\nshow "two"\nshow 3')
        self.assertEqual(r.output, "1\ntwo\n3\n")

    def test_relaxed_mode(self):
        r = run_sandboxed("show 6 * 7", mode="relaxed")
        self.assertEqual(r.output.strip(), "42")
        self.assertEqual(r.mode, "relaxed")
        self.assertTrue(r.ok)

    def test_parse_error(self):
        r = run_sandboxed("this is not valid !!!@@@")
        self.assertFalse(r.safe)
        self.assertTrue(r.error.startswith("Parse error:"))
        self.assertEqual(r.output, "")

    def test_runtime_error_message_preserved(self):
        r = run_sandboxed("show undefined_variable_xyz")
        self.assertFalse(r.safe)
        self.assertIn("undefined_variable_xyz", r.error)

    def test_strict_blocks_file_read(self):
        r = run_sandboxed('let c = file_read("nekova.toml")\nshow c')
        self.assertFalse(r.ok)
        self.assertIn("File system access is blocked", r.error)
        self.assertIn("open", [v["operation"] for v in r.violations])

    def test_strict_blocks_python_open(self):
        r = run_sandboxed('let f = open("nekova.toml")')
        self.assertFalse(r.ok)
        self.assertIn("Access to 'open' is blocked", r.error)

    def test_strict_blocks_think(self):
        r = run_sandboxed('let a = think "hi"\nshow a')
        self.assertFalse(r.ok)
        self.assertIn("'think' is blocked in strict mode", r.error)
        self.assertIn("think", [v["operation"] for v in r.violations])

    def test_use_math_still_works_in_strict(self):
        r = run_sandboxed("use math\nshow factorial(5)")
        self.assertEqual(r.output.strip(), "120")
        self.assertTrue(r.ok)

    def test_call_depth_limit(self):
        r = run_sandboxed("task f(n):\n    return f(n + 1)\nshow f(0)")
        self.assertFalse(r.safe)
        self.assertIn("exceeded the maximum call depth", r.error)

    def test_while_loop_cap_still_stops_runaway_loops(self):
        r = run_sandboxed("let i = 0\nwhile true:\n    let i = i + 1\n",
                          limits={"max_time": 5})
        self.assertFalse(r.ok)
        self.assertIn("ran too many times", r.error)

    def test_plain_while_loop_records_no_phantom_open_violation(self):
        # The loop cap is read lazily from nekova.toml; that read used
        # to trip the blocked-open guard and show up as a bogus
        # violation on every strict run containing a while loop.
        r = run_sandboxed("let i = 0\nwhile i < 3:\n    let i = i + 1\nshow i")
        self.assertEqual(r.output.strip(), "3")
        self.assertTrue(r.ok)
        self.assertEqual(r.violations, [])

    def test_allow_parameter_accepted(self):
        r = run_sandboxed("show 1", allow={"some_name"})
        self.assertTrue(r.ok)


# ── while-loop cap is the sandbox's own, not the host project's ──

class TestLoopCapIndependence(unittest.TestCase):
    """
    A project's nekova.toml can raise the while-loop cap to millions
    (this repo's own does) or set 0 for "unbounded". A strict sandbox
    must not inherit that: its loop guard is part of the sandbox, not
    of the project it happens to run inside.
    """

    COUNT_TO_50K = ("let i = 0\nwhile i < 50000:\n"
                    "    let i = i + 1\nshow i")

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        os.chdir(self.cwd)  # release the directory before deleting it
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _project_with_cap(self, cap):
        with open(os.path.join(self.tmpdir, "nekova.toml"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("[run]\nmax_loop_iterations = %d\n" % cap)
        with open(os.path.join(self.tmpdir, "main.nk"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("show 1\n")
        os.chdir(self.tmpdir)

    def test_strict_ignores_a_raised_project_cap(self):
        self._project_with_cap(2_000_000)
        r = run_sandboxed(self.COUNT_TO_50K, limits={"max_time": 20})
        self.assertFalse(r.ok)
        self.assertIn("ran too many times", r.error)

    def test_strict_ignores_an_unbounded_project_cap(self):
        self._project_with_cap(0)  # 0 means "no cap" for the project
        r = run_sandboxed(self.COUNT_TO_50K, limits={"max_time": 20})
        self.assertFalse(r.ok)
        self.assertIn("ran too many times", r.error)

    def test_relaxed_still_follows_the_project_cap(self):
        self._project_with_cap(2_000_000)
        r = run_sandboxed(self.COUNT_TO_50K, mode="relaxed",
                          limits={"max_time": 60})
        self.assertTrue(r.ok, r.error)
        self.assertEqual(r.output.strip(), "50000")


# ── hard limits actually enforced ────────────────────────────

class TestHardLimits(unittest.TestCase):

    def _hard_backend(self):
        return {"win32": "job-object", "linux": "rlimit"}.get(
            "linux" if sys.platform.startswith("linux") else sys.platform)

    def test_memory_limit_stops_a_memory_bomb(self):
        start = time.monotonic()
        r = run_sandboxed(MEMORY_BOMB, limits={"max_memory_mb": 96,
                                               "max_time": 20})
        took = time.monotonic() - start
        self.assertFalse(r.safe)
        self.assertIn("memory_limit", [v["operation"] for v in r.violations])
        self.assertIn("memory", (r.error or "").lower())
        self.assertLess(took, 15)
        self.assertTrue(_wait_dead(r.worker_pid))
        want = self._hard_backend()
        if want:
            self.assertEqual(r.enforced_by, want)

    def test_memory_limit_allows_programs_that_fit(self):
        r = run_sandboxed('let s = "abcdefgh"\nfor i in range(10):\n'
                          "    let s = s + s\nshow len(s)",
                          limits={"max_memory_mb": 96})
        self.assertTrue(r.ok, r.error)
        self.assertEqual(r.output.strip(), str(8 * 2 ** 10))
        self.assertEqual(r.violations, [])

    def test_cpu_limit_stops_a_cpu_burner_before_the_wall_clock(self):
        r = run_sandboxed(BURN, limits={"max_cpu_seconds": 1,
                                        "max_time": 30})
        self.assertFalse(r.safe)
        self.assertIn("cpu_limit", [v["operation"] for v in r.violations])
        self.assertIn("cpu", (r.error or "").lower())
        # r.duration is the program's own run time (worker startup is
        # excluded - it is slow on Windows). 1 CPU-second must stop the
        # program long before the 30 s wall-clock limit would.
        self.assertLess(r.duration, 10,
                        "ran %.1fs - the wall-clock limit, not the CPU "
                        "limit, is what stopped it" % r.duration)
        self.assertTrue(_wait_dead(r.worker_pid))

    def test_cpu_limit_is_not_hit_by_a_quick_program(self):
        r = run_sandboxed("show 1", limits={"max_cpu_seconds": 5})
        self.assertTrue(r.ok)


# ── sandbox_run() builtin forwards limits ────────────────────

class TestSandboxRunBuiltin(unittest.TestCase):
    """
    sandbox_run(code, mode, max_time=...) used to accept keyword
    limits and silently ignore them. With real quotas that would let
    someone believe max_memory_mb was enforced when it was not.
    """

    def _nekova(self, source):
        import io
        from nekova.lexer.lexer import Lexer
        from nekova.parser.parser import Parser
        from nekova.interpreter.interpreter import Interpreter
        interp = Interpreter()
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            interp.run(Parser(Lexer(source).tokenize()).parse())
        finally:
            sys.stdout = old
        return buf.getvalue()

    def test_plain_call_unchanged(self):
        out = self._nekova('let r = sandbox_run("show 42")\nshow r["output"]')
        self.assertIn("42", out)

    def test_limits_are_forwarded(self):
        prog = ("let t = 0\\nfor i in range(5000):\\n"
                "    for j in range(5000):\\n        let t = t + 1\\n")
        start = time.monotonic()
        out = self._nekova(
            'let r = sandbox_run("%s", "strict", max_time=1)\n'
            'show r["error"]' % prog)
        self.assertIn("timed out after 1s", out)
        self.assertLess(time.monotonic() - start, 8)

    def test_unknown_limit_is_a_catchable_error(self):
        out = self._nekova(
            'try:\n'
            '    let r = sandbox_run("show 1", "strict", max_memroy_mb=64)\n'
            'catch e:\n'
            '    show e\n')
        self.assertIn("max_memroy_mb", out)


# ── CLI: nekova run --sandbox ────────────────────────────────

class TestSandboxCLI(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, name, text):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return name

    def _cli(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "main.py"), *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=self.tmpdir, timeout=90,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_sandboxed_program_still_runs(self):
        self._write("ok.nk", "show 6 * 7\n")
        p = self._cli("run", "ok.nk", "--sandbox", "--quiet")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("42", p.stdout)

    def test_max_memory_flag_stops_a_memory_bomb(self):
        self._write("bomb.nk", MEMORY_BOMB)
        p = self._cli("run", "bomb.nk", "--sandbox", "--quiet",
                      "--max-memory", "96", "--max-time", "20")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("memory", (p.stdout + p.stderr).lower())

    def test_max_cpu_flag_stops_a_cpu_burner(self):
        self._write("burn.nk", BURN)
        p = self._cli("run", "burn.nk", "--sandbox", "--quiet",
                      "--max-cpu", "1", "--max-time", "30")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("cpu", (p.stdout + p.stderr).lower())

    def test_max_time_flag(self):
        self._write("burn.nk", BURN)
        start = time.monotonic()
        p = self._cli("run", "burn.nk", "--sandbox", "--quiet",
                      "--max-time", "1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("timed out", (p.stdout + p.stderr).lower())
        self.assertLess(time.monotonic() - start, 30)

    def test_flag_value_is_not_mistaken_for_the_file(self):
        # `--max-memory 128` before the file must not make "128" the
        # script path or a script argument
        self._write("ok.nk", "show 5\n")
        p = self._cli("run", "--sandbox", "--quiet",
                      "--max-memory", "128", "ok.nk")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("5", p.stdout)

    def test_bad_flag_value_is_a_clean_error(self):
        self._write("ok.nk", "show 1\n")
        for flag, val in (("--max-memory", "abc"), ("--max-cpu", "-3"),
                          ("--max-time", "0")):
            p = self._cli("run", "ok.nk", "--sandbox", "--quiet", flag, val)
            out = p.stdout + p.stderr
            self.assertNotEqual(p.returncode, 0, "%s %s" % (flag, val))
            self.assertIn(flag, out)
            self.assertNotIn("Traceback", out)

    def test_limit_flags_without_sandbox_are_rejected(self):
        # silently ignoring them would give the user a false sense of
        # safety
        self._write("ok.nk", "show 1\n")
        p = self._cli("run", "ok.nk", "--quiet", "--max-memory", "128")
        out = p.stdout + p.stderr
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--sandbox", out)

    def test_help_lists_the_flags(self):
        p = self._cli("--help", "--quiet")
        out = p.stdout + p.stderr
        for flag in ("--max-memory", "--max-cpu", "--max-time"):
            self.assertIn(flag, out)


if __name__ == "__main__":
    unittest.main()