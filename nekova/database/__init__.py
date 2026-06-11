# =============================================================
# NEKOVA Database — Package Init
# =============================================================
# Makes the database module importable from anywhere like:
#   from database import load_db_module

from nekova.database.db_module import load
from nekova.database.connection import DatabaseConnection
from nekova.database.query import QueryBuilder


def load_db_module() -> dict:
    """Load all database functions into the NEKOVA environment."""
    return load()
