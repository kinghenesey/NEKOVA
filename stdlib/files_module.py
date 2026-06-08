# =============================================================
# NEKOVA Standard Library — Files Module
# =============================================================
# Usage in NEKOVA:
#   use files
#   write_file("hello.txt", "Hello NEKOVA")
#   content = read_file("hello.txt")
#   show content                → Hello NEKOVA
#   show file_exists("hello.txt")  → true

import os


def load() -> dict:
    """
    Returns all file functions to be loaded
    into the NEKOVA environment.
    """
    return {
        # Reading
        "read_file": _read_file,
        "read_lines": _read_lines,

        # Writing
        "write_file":  _write_file,
        "append_file": _append_file,

        # Checking
        "file_exists": lambda path: os.path.isfile(str(path)),
        "dir_exists":  lambda path: os.path.isdir(str(path)),

        # Info
        "file_size":   lambda path: os.path.getsize(str(path)),
        "file_name":   lambda path: os.path.basename(str(path)),
        "file_ext":    lambda path: os.path.splitext(str(path))[1],

        # Management
        "delete_file": lambda path: os.remove(str(path)),
        "make_dir":    lambda path: os.makedirs(
                           str(path), exist_ok=True),
        "list_dir":    lambda path=".": os.listdir(str(path)),
    }


def _read_file(path: str) -> str:
    """Read entire file and return as string."""
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(
            f"File '{path}' was not found.\n"
            f"  Check the path and try again."
        )
    except PermissionError:
        raise RuntimeError(
            f"Permission denied reading '{path}'."
        )


def _read_lines(path: str) -> list:
    """Read file and return list of lines."""
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f.readlines()]
    except FileNotFoundError:
        raise RuntimeError(
            f"File '{path}' was not found.\n"
            f"  Check the path and try again."
        )


def _write_file(path: str, content: str):
    """Write content to a file, creating it if needed."""
    try:
        with open(str(path), "w", encoding="utf-8") as f:
            f.write(str(content))
    except PermissionError:
        raise RuntimeError(
            f"Permission denied writing to '{path}'."
        )


def _append_file(path: str, content: str):
    """Append content to an existing file."""
    try:
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(str(content))
    except PermissionError:
        raise RuntimeError(
            f"Permission denied writing to '{path}'."
        )