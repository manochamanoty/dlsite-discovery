import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dlsite_app.config import settings
from dlsite_app.db import get_db_connection


def check_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(works)")
    columns = cursor.fetchall()
    print(f"Database: {settings.db_path}")
    print("Works Table Columns:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
