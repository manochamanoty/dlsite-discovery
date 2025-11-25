import sqlite3
from contextlib import contextmanager

from dlsite_app.config import settings


def get_db_connection():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_connection():
    """Context manager wrapper to ensure connections are closed."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
