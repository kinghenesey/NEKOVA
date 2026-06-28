# =============================================================
# NEKOVA Database — Query Builder (Bug 16 fix: SQL injection)
# =============================================================
# Builds SQL queries from simple NEKOVA-friendly commands.
# All identifiers (table names, column names) are validated.
# WHERE clauses with user values use parameterised queries.
# =============================================================

import re
from nekova.database.connection import DatabaseConnection


def _safe_identifier(name: str) -> str:
    """
    Validate a SQL identifier (table/column name).
    Only allows alphanumeric + underscore to prevent injection.
    Raises ValueError for anything suspicious.
    """
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', str(name)):
        raise ValueError(
            f"Invalid SQL identifier '{name}'.\n"
            "  Table and column names may only contain letters, "
            "digits, and underscores."
        )
    return str(name)


class QueryBuilder:
    """
    Builds and executes SQL queries from simple commands.

    Usage:
        qb = QueryBuilder(connection)
        qb.create_table("users", {"name": "TEXT", "age": "INTEGER"})
        qb.insert("users", {"name": "Emmanuel", "age": 20})
        rows = qb.select("users", where=("age > ?", [18]))
    """

    def __init__(self, connection: DatabaseConnection):
        self.db = connection

    # ── Table management ─────────────────────────────────────

    def create_table(self, table: str, columns: dict) -> bool:
        table = _safe_identifier(table)
        col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for col_name, col_type in columns.items():
            col_name = _safe_identifier(col_name)
            # Whitelist allowed types
            allowed = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC",
                       "BOOLEAN", "FLOAT", "VARCHAR", "DATETIME",
                       "NUMBER", "CHAR", "NVARCHAR", "DOUBLE"}
            col_type_up = str(col_type).upper()
            if col_type_up not in allowed:
                raise ValueError(
                    f"Unsupported column type '{col_type}'.\n"
                    f"  Allowed: {', '.join(sorted(allowed))}"
                )
            col_defs.append(f"{col_name} {col_type_up}")

        sql = (f"CREATE TABLE IF NOT EXISTS {table} "
               f"({', '.join(col_defs)})")
        self.db.execute(sql)
        return True

    def drop_table(self, table: str) -> bool:
        table = _safe_identifier(table)
        self.db.execute(f"DROP TABLE IF EXISTS {table}")
        return True

    def table_exists(self, table: str) -> bool:
        table = _safe_identifier(table)
        rows = self.db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name=?",
            (table,)
        )
        return len(rows) > 0

    # ── CRUD operations ──────────────────────────────────────

    def insert(self, table: str, data: dict) -> int:
        table = _safe_identifier(table)
        safe_data = {_safe_identifier(k): v for k, v in data.items()}
        columns      = ", ".join(safe_data.keys())
        placeholders = ", ".join(["?"] * len(safe_data))
        values       = tuple(safe_data.values())
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.db.execute(sql, values)
        rows = self.db.execute("SELECT last_insert_rowid()")
        return rows[0]["last_insert_rowid()"] if rows else 0

    def select(self, table: str,
               where=None,
               order_by: str = None,
               limit: int = None) -> list:
        """
        Select rows from a table.

        where may be:
          - None                    → no filter
          - str                     → raw SQL (legacy, kept for compat)
          - (str, list)             → parameterised: ("age > ?", [18])
          - dict                    → equality filter: {"name": "Alice"}
        """
        table = _safe_identifier(table)
        sql    = f"SELECT * FROM {table}"
        params: tuple = ()

        if where is not None:
            if isinstance(where, dict):
                # Safe dict-based equality filter
                safe_where = {_safe_identifier(k): v for k, v in where.items()}
                clause  = " AND ".join(f"{k} = ?" for k in safe_where)
                params  = tuple(safe_where.values())
                sql    += f" WHERE {clause}"
            elif isinstance(where, (list, tuple)) and len(where) == 2:
                # Parameterised: ("col = ?", [value])
                clause, vals = where
                params = tuple(vals)
                sql   += f" WHERE {clause}"
            else:
                # Legacy raw string — kept for back-compat, no user values
                sql += f" WHERE {where}"

        if order_by:
            # Validate order_by: allow "col ASC" / "col DESC"
            match = re.match(
                r'^([A-Za-z_][A-Za-z0-9_]*)\s*(ASC|DESC)?$',
                str(order_by).strip(), re.I
            )
            if not match:
                raise ValueError(f"Invalid ORDER BY clause: {order_by!r}")
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        return self.db.execute(sql, params) if params else self.db.execute(sql)

    def update(self, table: str, data: dict, where=None) -> bool:
        table     = _safe_identifier(table)
        safe_data = {_safe_identifier(k): v for k, v in data.items()}
        set_clause = ", ".join(f"{col} = ?" for col in safe_data.keys())
        values     = list(safe_data.values())

        sql = f"UPDATE {table} SET {set_clause}"

        if where is None:
            self.db.execute(sql, tuple(values))
        elif isinstance(where, dict):
            safe_where = {_safe_identifier(k): v for k, v in where.items()}
            clause = " AND ".join(f"{k} = ?" for k in safe_where)
            values += list(safe_where.values())
            self.db.execute(sql + f" WHERE {clause}", tuple(values))
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            clause, wvals = where
            values += list(wvals)
            self.db.execute(sql + f" WHERE {clause}", tuple(values))
        else:
            # Legacy raw string
            self.db.execute(sql + f" WHERE {where}", tuple(values))

        return True

    def delete(self, table: str, where=None) -> bool:
        table = _safe_identifier(table)
        sql   = f"DELETE FROM {table}"

        if where is None:
            self.db.execute(sql)
        elif isinstance(where, dict):
            safe_where = {_safe_identifier(k): v for k, v in where.items()}
            clause = " AND ".join(f"{k} = ?" for k in safe_where)
            self.db.execute(sql + f" WHERE {clause}", tuple(safe_where.values()))
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            clause, wvals = where
            self.db.execute(sql + f" WHERE {clause}", tuple(wvals))
        else:
            self.db.execute(sql + f" WHERE {where}")

        return True

    def count(self, table: str, where=None) -> int:
        table = _safe_identifier(table)
        sql   = f"SELECT COUNT(*) as total FROM {table}"

        if where is None:
            rows = self.db.execute(sql)
        elif isinstance(where, dict):
            safe_where = {_safe_identifier(k): v for k, v in where.items()}
            clause = " AND ".join(f"{k} = ?" for k in safe_where)
            rows = self.db.execute(
                sql + f" WHERE {clause}", tuple(safe_where.values())
            )
        else:
            rows = self.db.execute(sql + f" WHERE {where}")

        return rows[0]["total"] if rows else 0

    def find_by_id(self, table: str, id: int) -> dict:
        table = _safe_identifier(table)
        rows = self.db.execute(
            f"SELECT * FROM {table} WHERE id = ?", (int(id),)
        )
        return rows[0] if rows else None

    def find_one(self, table: str, where=None) -> dict:
        rows = self.select(table, where=where, limit=1)
        return rows[0] if rows else None

    def __repr__(self):
        return f"QueryBuilder({self.db})"