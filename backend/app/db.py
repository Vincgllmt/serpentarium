import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    filename TEXT NOT NULL,
    relpath TEXT NOT NULL UNIQUE,
    size INTEGER NOT NULL,
    crc32 TEXT,
    cover_url TEXT,
    year INTEGER,
    ss_id TEXT,
    scraped_at TEXT
);
"""


def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(SCHEMA)


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
