# =============================================================
# NEKOVA Database — DB Module
# =============================================================
# NEKOVA Database — DB Module
# =============================================================
# This is what gets loaded when you write "use database" in NEKOVA.
# It exposes all database functions to your NEKOVA programs.
#
# Usage in NEKOVA:
#   use database
#   db_connect("myapp.db")
#   db_create("users", "name text, age integer")
#   db_insert("users", "Emmanuel, 20")
#   results = db_find("users", "all")
#   show results

from database.connection import DatabaseConnection
from database.query import QueryBuilder


# Global database state
_connection = None
_query      = None


def load() -> dict:
    """
    Returns all database functions to be loaded
    into the NEKOVA environment when 'use database' is called.
    """
    return {
        # Connection
        "db_connect":   _db_connect,
        "db_close":     _db_close,
        "db_tables":    _db_tables,

        # Table management
        "db_create":    _db_create,
        "db_drop":      _db_drop,
        "db_exists":    _db_exists,

        # CRUD
        "db_insert":    _db_insert,
        "db_find":      _db_find,
        "db_find_one":  _db_find_one,
        "db_find_id":   _db_find_id,
        "db_update":    _db_update,
        "db_delete":    _db_delete,
        "db_count":     _db_count,
    }


# ----------------------------------------------------------
# Connection management
# ----------------------------------------------------------

def _db_connect(filepath: str = "nekova.db"):
    """Connect to a SQLite database."""
    global _connection, _query

    _connection = DatabaseConnection(str(filepath))
    _connection.connect()
    _query = QueryBuilder(_connection)
    return filepath


def _db_close():
    """Close the database connection."""
    global _connection, _query
    if _connection:
        _connection.close()
        _connection = None
        _query      = None


def _db_tables() -> list:
    """Return list of all tables."""
    _require_connection()
    return _connection.tables()


# ----------------------------------------------------------
# Table management
# ----------------------------------------------------------

def _db_create(table: str, schema: str):
    """
    Create a table from a schema string.

    Usage:
        db_create("users", "name text, email text, age integer")

    Supported types:
        text, integer, real, boolean
    """
    _require_connection()

    # Parse schema string into columns dict
    columns = {}
    for part in schema.split(","):
        part = part.strip()
        if not part:
            continue
        pieces = part.split()
        if len(pieces) >= 2:
            col_name = pieces[0].strip()
            col_type = pieces[1].strip().upper()
            columns[col_name] = col_type
        elif len(pieces) == 1:
            columns[pieces[0].strip()] = "TEXT"

    _query.create_table(table, columns)

    print(f"✓ Table '{table}' ready")
    return table


def _db_drop(table: str):
    """Drop a table."""
    _require_connection()
    _query.drop_table(str(table))
    return table


def _db_exists(table: str) -> bool:
    """Check if a table exists."""
    _require_connection()
    return _query.table_exists(str(table))


# ----------------------------------------------------------
# CRUD operations
# ----------------------------------------------------------

def _db_insert(table: str, values: str) -> int:
    """
    Insert a row into a table.

    Usage:
        db_insert("users", "Emmanuel, emma@nekova.dev, 20")

    Values are matched to columns in order of creation.
    Returns the ID of the new row.
    """
    _require_connection()

    # Get table columns (excluding id)
    rows = _connection.execute(
        f"PRAGMA table_info({table})"
    )
    columns = [
        row["name"] for row in rows
        if row["name"] != "id"
    ]

    # If PRAGMA didn't work, try alternate method
    if not columns:
        rows = _connection.execute(
            f"SELECT * FROM {table} LIMIT 0"
        )
        # Get column names from cursor description
        desc = _connection.cursor.description or []
        columns = [
            d[0] for d in desc
            if d[0] != "id"
        ]

    # Parse values string
    raw_values = [v.strip() for v in values.split(",")]

    if len(raw_values) != len(columns):
        raise RuntimeError(
            f"Table '{table}' has {len(columns)} columns "
            f"but {len(raw_values)} values were provided.\n"
            f"  Columns: {', '.join(columns)}"
        )

    # Build data dict
    data = {}
    for col, val in zip(columns, raw_values):
        try:
            if "." in val:
                data[col] = float(val)
            else:
                data[col] = int(val)
        except ValueError:
            data[col] = val

    row_id = _query.insert(table, data)
    return row_id


def _db_find(table: str,
             where: str = "all",
             order: str = None) -> list:
    """
    Find rows in a table.

    Usage:
        db_find("users", "all")
        db_find("users", "age > 18")
        db_find("users", "name = 'Emmanuel'")
    """
    _require_connection()

    where_clause = None if where == "all" else where
    rows = _query.select(
        str(table),
        where=where_clause,
        order_by=order
    )

    return _format_rows(rows)


def _db_find_one(table: str, where: str) -> str:
    """Find a single row matching a condition."""
    _require_connection()
    row = _query.find_one(str(table), str(where))
    if row is None:
        return "null"
    return _format_row(row)


def _db_find_id(table: str, id: int) -> str:
    """Find a row by its ID."""
    _require_connection()
    row = _query.find_by_id(str(table), int(id))
    if row is None:
        return "null"
    return _format_row(row)


def _db_update(table: str,
               values: str,
               where: str = None) -> bool:
    """
    Update rows in a table.

    Usage:
        db_update("users", "age = 21", "name = 'Emmanuel'")
    """
    _require_connection()

    # Parse "col = val, col2 = val2" format
    data = {}
    for part in values.split(","):
        if "=" in part:
            col, val = part.split("=", 1)
            col = col.strip()
            val = val.strip().strip("'\"")
            try:
                if "." in val:
                    data[col] = float(val)
                else:
                    data[col] = int(val)
            except ValueError:
                data[col] = val

    _query.update(str(table), data,
                  where=str(where) if where else None)
    return True


def _db_delete(table: str,
               where: str = None) -> bool:
    """
    Delete rows from a table.

    Usage:
        db_delete("users", "id = 1")
        db_delete("users", "all")
    """
    _require_connection()

    where_clause = (None if not where or where == "all"
                    else str(where))
    _query.delete(str(table), where=where_clause)
    return True


def _db_count(table: str,
              where: str = None) -> int:
    """Count rows in a table."""
    _require_connection()
    where_clause = (None if not where or where == "all"
                    else str(where))
    return _query.count(str(table), where=where_clause)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _require_connection():
    """Ensure database is connected."""
    if _connection is None:
        raise RuntimeError(
            "Database not connected.\n"
            "  Call db_connect('myapp.db') first."
        )


def _format_row(row: dict) -> str:
    """Format a single row as a readable string."""
    parts = [f"{k}: {v}" for k, v in row.items()]
    return " | ".join(parts)


def _format_rows(rows: list) -> str:
    """Format a list of rows as a readable string."""
    if not rows:
        return "No records found."
    lines = [_format_row(row) for row in rows]
    return "\n".join(lines)