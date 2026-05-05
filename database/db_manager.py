import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "ids.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        schema = SCHEMA_PATH.read_text()
        conn.executescript(schema)
        conn.commit()

    return db_path


def execute(query, params=None, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        cur = conn.execute(query, params or [])
        conn.commit()
        return cur


def fetch_all(query, params=None, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params or []).fetchall()
        return [dict(row) for row in rows]
