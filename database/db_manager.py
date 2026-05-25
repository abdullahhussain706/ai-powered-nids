import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "ids.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(Path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        schema = SCHEMA_PATH.read_text()
        conn.executescript(schema)
        ensure_alert_columns(conn)
        conn.commit()

    return db_path


def ensure_alert_columns(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(alerts)").fetchall()
    }

    if "source" not in columns:
        conn.execute("ALTER TABLE alerts ADD COLUMN source TEXT")


def execute(query, params=None, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        cur = conn.execute(query, params or [])
        conn.commit()
        return cur


def fetch_all(query, params=None, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params or []).fetchall()
        return [dict(row) for row in rows]
