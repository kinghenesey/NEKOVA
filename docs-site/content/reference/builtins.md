---
title: Built-in Functions
lede: Every global function NEKOVA registers automatically, grouped by purpose.
---

## Type conversion

| Function | Description |
|---|---|
| `int(x)` | Convert to an integer. Raises a clear error on an unparsable string. |
| `float(x)` | Convert to a decimal number. Same clean-error behavior as `int()`. |
| `str(x)` | Convert to text. |
| `bool(x)` | Convert to a boolean. |
| `list(x)` | Convert to a list. |
| `dict()` | Create an empty dict. |
| `to_number(x)` | Convert to a number, tolerant of numeric strings. |
| `to_text(x)` | Convert to text. |
| `type_of(x)` | Returns the value's type as a string — `"int"`, `"str"`, `"list"`, `"dict"`, `"set"`, etc. |
| `isinstance(x, type)` | Check a value's type. |
| `callable(x)` | Check whether a value can be called. |

## Math

| Function | Description |
|---|---|
| `abs(x)` | Absolute value. |
| `round(x)` | Round to the nearest integer. |
| `floor(x)` / `ceil(x)` | Round down / up. |
| `pow(x, y)` | `x` to the power of `y`. |
| `sqrt(x)` | Square root. |
| `sin(x)` / `cos(x)` / `tan(x)` | Trigonometric functions. |
| `log(x)` / `log10(x)` | Natural log / base-10 log. |
| `divmod(a, b)` | Returns `(quotient, remainder)` — pairs naturally with [tuple destructuring](../syntax/destructuring.html). |
| `min(...)` / `max(...)` | Minimum / maximum of a list or arguments. |
| `sum(iterable)` | Sum of a list. |
| `random_num(a, b)` | A random number between `a` and `b`. |

## Collections

| Function | Description |
|---|---|
| `len(x)` / `length(x)` | Length of a list, string, or dict — two names for the same thing. |
| `range(n)` | A range of numbers from 0 to `n - 1`. |
| `sorted(x)` | A sorted copy of a list. |
| `reversed(x)` | A reversed copy of a list. |
| `enumerate(x)` | Pairs of `(index, value)`. |
| `zip(a, b)` | Pairs values from two lists together. |
| `map(fn, x)` / `filter(fn, x)` | Transform / filter a list. |
| `all(x)` / `any(x)` | Whether every / any item is truthy. |
| `set_union(a, b)` / `set_intersection(a, b)` / `set_difference(a, b)` | [Set operations](../syntax/data-structures.html). |

## Text

| Function | Description |
|---|---|
| `chr(n)` / `ord(c)` | Character ↔ code point. |
| `hex(n)` / `oct(n)` / `bin(n)` | Number to hex/octal/binary string. |

## Dates

| Function | Description |
|---|---|
| `date_now()` / `date_today()` | Current date/time. |
| `date_timestamp()` | Current Unix timestamp. |
| `date_format(d, fmt)` | Format a date. |
| `date_day_of_week(d)` | Day of the week for a date. |
| `date_add_days(d, n)` | Add `n` days to a date. |
| `date_diff_days(a, b)` | Days between two dates. |

## Files

| Function | Description |
|---|---|
| `file_read(path)` | Read a file's contents. |
| `file_write(path, contents)` | Write to a file. |
| `file_append(path, contents)` | Append to a file. |
| `file_delete(path)` | Delete a file. |
| `file_exists(path)` | Whether a file exists. |

Inside a [sandbox](../advanced/sandbox.html), file access follows the sandbox's mode — `strict` blocks it entirely, `relaxed` allows reads.

## Other

| Function | Description |
|---|---|
| `doc(x)` / `doc(x, "name")` | Read a task, class, `init`, or method's [docstring](../syntax/functions.html#docstrings). |
| `print(x)` | Raw output, without NEKOVA's `show` formatting. |
| `input()` / `ask(prompt)` | Read a line from the user. |
| `sleep(seconds)` | Pause execution. |
| `connect(path)` | Open a database connection. |
| `sandbox_run(code)` | Run code inside a sandbox from within a running program. |
| `args` | Access command-line arguments passed to the running script. |