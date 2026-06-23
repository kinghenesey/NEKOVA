# =============================================================
# NEKOVA — File Watcher  (Phase 12C)
# =============================================================
# Powers:  nekova run app.nk --watch
#          nekova run --watch          (uses nekova.toml entry)
#
# Watches the target .nk file and re-runs it on every save.
# Uses watchdog when available; falls back to polling.
# =============================================================

import os
import sys
import time
import subprocess
import threading

from nekova.config import Color, NEKOVA_VERSION


def _run_file(filepath: str, extra_args: list) -> int:
    """Run a .nk file via subprocess and return exit code."""
    root = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(root, "main.py"), filepath]
    result = subprocess.run(cmd, cwd=root)
    return result.returncode


def _separator(label: str = ""):
    w = 50
    if label:
        pad = (w - len(label) - 2) // 2
        line = chr(9472) * pad + " " + label + " " + chr(9472) * pad
    else:
        line = chr(9472) * w
    print("\n" + Color.DIM + "  " + line + Color.RESET)


def _timestamp() -> str:
    return time.strftime("%H:%M:%S")


# Watchdog-based watcher
def _watch_with_watchdog(filepath: str, extra_args: list):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    abs_path  = os.path.abspath(filepath)
    watch_dir = os.path.dirname(abs_path)
    _lock    = threading.Lock()
    _pending = [False]

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            changed = os.path.abspath(event.src_path)
            if changed == abs_path or changed.endswith(".nk"):
                with _lock:
                    _pending[0] = True

    handler  = _Handler()
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    print(Color.CYAN + "  Watching:" + Color.RESET + " " + filepath)
    print(Color.DIM + "  Ctrl+C to stop" + Color.RESET + "\n")

    _separator("run " + chr(183) + " " + _timestamp())
    _run_file(filepath, extra_args)

    try:
        while True:
            time.sleep(0.3)
            with _lock:
                if _pending[0]:
                    _pending[0] = False
                else:
                    continue
            _separator("rerun " + chr(183) + " " + _timestamp())
            _run_file(filepath, extra_args)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        print("\n" + Color.DIM + "  Watch stopped." + Color.RESET + "\n")


# Polling fallback
def _watch_with_polling(filepath: str, extra_args: list, interval: float = 0.5):
    abs_path = os.path.abspath(filepath)

    def _mtime():
        try:
            return os.path.getmtime(abs_path)
        except OSError:
            return 0

    print(Color.CYAN + "  Watching:" + Color.RESET + " " + filepath
          + " " + Color.DIM + "(polling)" + Color.RESET)
    print(Color.DIM + "  Ctrl+C to stop" + Color.RESET + "\n")

    last_mtime = _mtime()
    _separator("run " + chr(183) + " " + _timestamp())
    _run_file(filepath, extra_args)

    try:
        while True:
            time.sleep(interval)
            current = _mtime()
            if current != last_mtime:
                last_mtime = current
                _separator("rerun " + chr(183) + " " + _timestamp())
                _run_file(filepath, extra_args)
    except KeyboardInterrupt:
        print("\n" + Color.DIM + "  Watch stopped." + Color.RESET + "\n")


# Public entry point
def watch(filepath: str, extra_args: list = None):
    """Watch a .nk file and re-run it on every change."""
    extra_args = extra_args or []

    if not os.path.isfile(filepath):
        print(Color.RED + "  Error: file not found: " + filepath + Color.RESET)
        sys.exit(1)

    print("\n" + Color.CYAN + Color.BOLD + "  NEKOVA Watch Mode" + Color.RESET)
    print("  " + Color.DIM + chr(9472) * 40 + Color.RESET)
    print("  " + Color.DIM + "NEKOVA v" + NEKOVA_VERSION + " · auto-rerun on save" + Color.RESET)
    print("  " + Color.DIM + chr(9472) * 40 + Color.RESET)

    try:
        import watchdog  # noqa: F401
        _watch_with_watchdog(filepath, extra_args)
    except ImportError:
        _watch_with_polling(filepath, extra_args)