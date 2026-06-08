# =============================================================
# NEKOVA Database — Query Builder
# =============================================================
# Builds SQL queries from simple NEKOVA-friendly commands.
# Hides the complexity of SQL from NEKOVA programmers.
#
# Example:
#   query.insert("users", {"name": "Emmanuel", "age": 20})
#   → INSERT INTO users (name, age) VALUES (?, ?)
#
# This is called a "query builder" — same pattern used by
# Django ORM, Laravel Eloquent, and Prisma.

from database.connection import DatabaseConnection


class QueryBuilder:
    """
    Builds and executes SQL queries from simple commands.

    Usage:
        qb = QueryBuilder(connection)
        qb.create_table("users", {"name": "TEXT", "age": "INTEGER"})
        qb.insert("users", {"name": "Emmanuel", "age": 20})
        rows = qb.select("users")
    """

    def __init__(self, connection: DatabaseConnection):
        self.db = connection

    # ----------------------------------------------------------
    # Table management
    # ----------------------------------------------------------

    def create_table(self, table: str,
                     columns: dict) -> bool:
        """
        Create a table with the given columns.

        Args:
            table   — table name
            columns — dict of column_name: type
                      e.g. {"name": "TEXT", "age": "INTEGER"}
        """
        # Always add an auto-increment ID
        col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        for col_name, col_type in columns.items():
            col_defs.append(f"{col_name} {col_type.upper()}")

        sql = (f"CREATE TABLE IF NOT EXISTS {table} "
               f"({', '.join(col_defs)})")

        self.db.execute(sql)
        return True

    def drop_table(self, table: str) -> bool:
        """Drop a table if it exists."""
        self.db.execute(f"DROP TABLE IF EXISTS {table}")
        return True

    def table_exists(self, table: str) -> bool:
        """Check if a table exists."""
        rows = self.db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name=?",
            (table,)
        )
        return len(rows) > 0

    # ----------------------------------------------------------
    # CRUD operations
    # ----------------------------------------------------------

    def insert(self, table: str, data: dict) -> int:
        """
        Insert a row into a table.
        Returns the ID of the inserted row.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" ] * len(data))
        values  = tuple(data.values())

        sql = (f"INSERT INTO {table} ({columns}) "
               f"VALUES ({placeholders})")

        self.db.execute(sql, values)

        # Get last inserted ID
        rows = self.db.execute("SELECT last_insert_rowid()")
        return rows[0]["last_insert_rowid()"] if rows else 0

    def select(self, table: str,
               where: str = None,
               order_by: str = None,
               limit: int = None) -> list:
        """
        Select rows from a table.

        Args:
            table    — table name
            where    — WHERE clause e.g. "age > 18"
            order_by — ORDER BY clause e.g. "name ASC"
            limit    — max number of rows to return
        """
        sql = f"SELECT * FROM {table}"

        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"

        return self.db.execute(sql)

    def update(self, table: str,
               data: dict,
               where: str = None) -> bool:
        """
        Update rows in a table.

        Args:
            table — table name
            data  — dict of column: new_value
            where — WHERE clause e.g. "id = 1"
        """
        set_clause = ", ".join(
            [f"{col} = ?" for col in data.keys()]
        )
        values = tuple(data.values())

        sql = f"UPDATE {table} SET {set_clause}"
        if where:
            sql += f" WHERE {where}"

        self.db.execute(sql, values)
        return True

    def delete(self, table: str,
               where: str = None) -> bool:
        """
        Delete rows from a table.

        Args:
            table — table name
            where — WHERE clause e.g. "id = 1"
                    If None, deletes ALL rows (use with care!)
        """
        sql = f"DELETE FROM {table}"
        if where:
            sql += f" WHERE {where}"

        self.db.execute(sql)
        return True

    def count(self, table: str,
              where: str = None) -> int:
        """Count rows in a table."""
        sql = f"SELECT COUNT(*) as total FROM {table}"
        if where:
            sql += f" WHERE {where}"

        rows = self.db.execute(sql)
        return rows[0]["total"] if rows else 0

    def find_by_id(self, table: str,
                   id: int) -> dict:
        """Find a single row by its ID."""
        rows = self.select(table, where=f"id = {int(id)}")
        return rows[0] if rows else None

    def find_one(self, table: str,
                 where: str) -> dict:
        """Find the first row matching a condition."""
        rows = self.select(table, where=where, limit=1)
        return rows[0] if rows else None

    def __repr__(self):
        return f"QueryBuilder({self.db})"