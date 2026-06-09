# =============================================================
# NEKOVA Database — Connection Manager
# =============================================================
# Manages SQLite database connections.
# SQLite is built into Python — no installation needed.
#
# Why SQLite?
#   - Zero configuration
#   - Single file database
#   - Perfect for apps and prototypes
#   - Same SQL syntax as PostgreSQL/MySQL

import sqlite3
import os


class DatabaseConnection:
    """
    Manages a connection to a SQLite database.

    Usage:
        db = DatabaseConnection("myapp.db")
        db.connect()
        db.execute("CREATE TABLE users (name TEXT)")
        db.close()
    """

    def __init__(self, filepath: str = "nekova.db"):
        self.filepath   = filepath
        self.connection = None
        self.cursor     = None

    def connect(self):
        """Open a connection to the database."""
        try:
            self.connection = sqlite3.connect(self.filepath)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()

            # Enable foreign keys
            self.cursor.execute("PRAGMA foreign_keys = ON")

            from config import Color
            print(f"{Color.GREEN}✓ Database connected: "
                  f"'{self.filepath}'{Color.RESET}")

            return True

        except Exception as e:
            raise RuntimeError(
                f"Could not connect to database '{self.filepath}'.\n"
                f"  Error: {e}"
            )

    def execute(self, sql: str,
                params: tuple = ()) -> list:
        """
        Execute a SQL statement.
        Returns rows for SELECT, empty list for others.
        """
        if self.connection is None:
            raise RuntimeError(
                "Database not connected.\n"
                "  Call db_connect() first."
            )

        try:
            self.cursor.execute(sql, params)
            self.connection.commit()

            # Return rows for SELECT and PRAGMA statements
            sql_upper = sql.strip().upper()
            if (sql_upper.startswith("SELECT") or
                    sql_upper.startswith("PRAGMA")):
                rows = self.cursor.fetchall()
                if rows and len(rows) > 0:
                    # Get column names from cursor description
                    if self.cursor.description:
                        cols = [d[0] for d in
                                self.cursor.description]
                        return [dict(zip(cols, row))
                                for row in rows]
                return []

            return []

        except sqlite3.Error as e:
            raise RuntimeError(
                f"Database error: {e}\n"
                f"  SQL: {sql}"
            )

    def execute_many(self, sql: str,
                     params_list: list):
        """Execute a SQL statement with multiple param sets."""
        if self.connection is None:
            raise RuntimeError("Database not connected.")

        try:
            self.cursor.executemany(sql, params_list)
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}")

    def tables(self) -> list:
        """Return list of all table names."""
        rows = self.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        )
        return [row["name"] for row in rows]

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor     = None

    def __repr__(self):
        status = "connected" if self.connection else "disconnected"
        return f"DatabaseConnection('{self.filepath}', {status})"