# NEKOVA Package — csv
import csv as _csv
import os

def load() -> dict:
    return {
        "csv_read":      _read,
        "csv_write":     _write,
        "csv_append":    _append,
        "csv_to_dict":   _to_dict,
        "csv_from_dict": _from_dict,
        "csv_filter":    _filter_rows,
        "csv_columns":   _columns,
    }

def _read(filepath: str, has_header: bool = True) -> list:
    """Read a CSV file. Returns list of rows (list of strings)."""
    rows = []
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.reader(f)
        if has_header:
            next(reader, None)   # skip header
        for row in reader:
            rows.append(row)
    return rows

def _write(filepath: str, rows: list,
           headers: list = None) -> bool:
    """Write rows to a CSV file, overwriting if it exists."""
    try:
        with open(str(filepath), "w", encoding="utf-8",
                  newline="") as f:
            w = _csv.writer(f)
            if headers:
                w.writerow(headers)
            for row in rows:
                w.writerow(row if isinstance(row, list) else [row])
        return True
    except Exception:
        return False

def _append(filepath: str, row: list) -> bool:
    """Append a single row to an existing CSV file."""
    try:
        with open(str(filepath), "a", encoding="utf-8",
                  newline="") as f:
            _csv.writer(f).writerow(row)
        return True
    except Exception:
        return False

def _to_dict(filepath: str) -> list:
    """Read a CSV with header row into a list of dicts."""
    results = []
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            results.append(dict(row))
    return results

def _from_dict(filepath: str, data: list,
               fieldnames: list = None) -> bool:
    """Write a list of dicts to a CSV file."""
    if not data:
        return False
    try:
        fields = fieldnames or list(data[0].keys())
        with open(str(filepath), "w", encoding="utf-8",
                  newline="") as f:
            w = _csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
        return True
    except Exception:
        return False

def _filter_rows(filepath: str, column: int,
                 value: str) -> list:
    """Return rows where column index equals value."""
    rows = _read(filepath, has_header=False)
    return [r for r in rows
            if len(r) > int(column)
            and r[int(column)] == str(value)]

def _columns(filepath: str) -> list:
    """Return the header row (column names) of a CSV file."""
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.reader(f)
        return next(reader, [])
