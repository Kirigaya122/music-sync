import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "music.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def initialize_database():
    with get_connection() as conn:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS tracks(
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         title TEXT NOT NULL,
                         artist TEXT NOT NULL,
                         source TEXT NOT NULL,
                         source_id TEXT,
                         status TEXT NOT NULL DEFAULT'dicovered',
                         created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                         UNIQUE(source, source_id)
                     )
                     """)
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(tracks)")
        }

        if "normalized_title" not in columns:
            conn.execute(
                "ALTER TABLE tracks ADD COLUMN normalized_title TEXT"
            )

        if "normalized_artist" not in columns:
            conn.execute(
                "ALTER TABLE tracks ADD COLUMN normalized_artist TEXT"
            )