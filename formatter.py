# =============================================================
# NEKOVA Language — Code Formatter
# =============================================================
# Automatically formats .NEKOVA files:
#   - Consistent indentation (4 spaces)
#   - Spaces around operators
#   - Clean blank lines
#   - Consistent string quotes
#   - Removes trailing whitespace
#
# Usage:
#   python main.py format app.NEKOVA
#   python main.py format app.NEKOVA --check

import os
import re
from nekova.config import Color


class NEKOVAFormatter:
    """
    Formats NEKOVA source code to a consistent style.

    Usage:
        formatter = NEKOVAFormatter(source)
        formatted = formatter.format()
    """

    def __init__(self, source: str):
        self.source = source
        self.lines  = source.splitlines()

    def format(self) -> str:
        """Format the source code and return result."""
        lines = self.lines.copy()

        # Apply formatting passes
        lines = self._fix_indentation(lines)
        lines = self._fix_operators(lines)
        lines = self._fix_blank_lines(lines)
        lines = self._fix_trailing_whitespace(lines)
        lines = self._fix_string_quotes(lines)

        return "\n".join(lines)

    def diff(self) -> list:
        """Return list of changed lines."""
        original  = self.lines
        formatted = self.format().splitlines()
        changes   = []

        for i, (old, new) in enumerate(
                zip(original, formatted), 1):
            if old != new:
                changes.append({
                    "line":    i,
                    "before":  old,
                    "after":   new,
                })

        return changes

    # ----------------------------------------------------------
    # Formatting passes
    # ----------------------------------------------------------

    def _fix_indentation(self, lines: list) -> list:
        """Ensure consistent 4-space indentation."""
        result = []
        for line in lines:
            if not line.strip():
                result.append("")
                continue

            # Count leading spaces
            stripped    = line.lstrip()
            leading     = line[: len(line) - len(stripped)]

            # Convert tabs to 4 spaces
            leading     = leading.replace("\t", "    ")

            # Normalize to multiples of 4
            spaces      = len(leading)
            normalized  = (spaces // 4) * 4
            new_leading = " " * normalized

            result.append(new_leading + stripped)

        return result

    def _fix_operators(self, lines: list) -> list:
        """Add spaces around operators."""
        result = []
        for line in lines:
            # Skip comments and empty lines
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                result.append(line)
                continue

            # Get indentation
            indent = line[: len(line) - len(line.lstrip())]
            code   = line.strip()

            # Add spaces around = (but not ==, !=, <=, >=)
            code = re.sub(
                r'(?<![=!<>])=(?!=)',
                r' = ',
                code
            )

            # Add spaces around + - * / (but not **)
            code = re.sub(r'(?<!\*)\*(?!\*)', r' * ', code)
            code = re.sub(r'\*\*', r'**', code)
            code = re.sub(r'(?<![0-9])\+(?!["\'])',
                          r' + ', code)

            # Fix multiple spaces
            code = re.sub(r'  +', ' ', code)

            # Fix spaces in strings (restore)
            result.append(indent + code.strip())

        return result

    def _fix_blank_lines(self, lines: list) -> list:
        """
        Ensure consistent blank lines:
        - Max 2 consecutive blank lines
        - One blank line between tasks
        - No blank lines at start/end
        """
        result      = []
        blank_count = 0

        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 1:
                    result.append("")
            else:
                blank_count = 0
                result.append(line)

        # Remove leading/trailing blank lines
        while result and not result[0].strip():
            result.pop(0)
        while result and not result[-1].strip():
            result.pop()

        return result

    def _fix_trailing_whitespace(self,
                                  lines: list) -> list:
        """Remove trailing whitespace from all lines."""
        return [line.rstrip() for line in lines]

    def _fix_string_quotes(self,
                            lines: list) -> list:
        """
        Normalize string quotes to double quotes.
        Only for simple cases — preserves complex strings.
        """
        result = []
        for line in lines:
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("#"):
                result.append(line)
                continue

            # Replace single-quoted strings with double
            # Only simple cases: 'hello' → "hello"
            new_line = re.sub(
                r"'([^'\"\\]*)'",
                r'"\1"',
                line
            )
            result.append(new_line)

        return result


def format_file(filepath: str,
                check_only: bool = False,
                write: bool = True) -> bool:
    """
    Format an NEKOVA file.

    Args:
        filepath   — path to .NEKOVA file
        check_only — only check, don't write
        write      — write formatted code back to file

    Returns True if file was changed.
    """
    if not os.path.isfile(filepath):
        print(f"{Color.RED}✗ File not found: "
              f"'{filepath}'{Color.RESET}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    formatter = NEKOVAFormatter(original)
    formatted = formatter.format()
    changes   = formatter.diff()

    if not changes:
        print(f"{Color.GREEN}✓ '{filepath}' "
              f"is already formatted{Color.RESET}")
        return False

    if check_only:
        print(f"{Color.YELLOW}⚠ '{filepath}' "
              f"needs formatting "
              f"({len(changes)} changes){Color.RESET}")
        for change in changes[:5]:
            print(f"  {Color.DIM}Line {change['line']}:"
                  f"{Color.RESET}")
            print(f"  {Color.RED}- {change['before']}"
                  f"{Color.RESET}")
            print(f"  {Color.GREEN}+ {change['after']}"
                  f"{Color.RESET}")
        return True

    if write:
        with open(filepath, "w",
                  encoding="utf-8") as f:
            f.write(formatted)
        print(f"{Color.GREEN}✓ Formatted "
              f"'{filepath}' "
              f"({len(changes)} changes){Color.RESET}")

    return True


def format_directory(directory: str = ".") -> int:
    """Format all .NEKOVA files in a directory."""
    count = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs
                   if d not in ("venv", ".git",
                                "__pycache__")]
        for f in files:
            if f.endswith(".NEKOVA"):
                path = os.path.join(root, f)
                if format_file(path):
                    count += 1
    return count
