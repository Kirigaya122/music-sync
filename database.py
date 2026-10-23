import sqlite3
import time
from pathlib import Path

from utils import normalize_text

DB_PATH = Path(__file__).parent / "music.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT,
                status TEXT NOT NULL DEFAULT 'discovered',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        """)

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tracks)")}

        for col in ("normalized_title", "normalized_artist"):
            if col not in columns:
                conn.execute(f"ALTER TABLE tracks ADD COLUMN {col} TEXT")

        if "raw_share" not in columns:
            conn.execute("ALTER TABLE tracks ADD COLUMN raw_share TEXT")

        if "library_path" not in columns:
            conn.execute("ALTER TABLE tracks ADD COLUMN library_path TEXT")

        if "file_sha256" not in columns:
            conn.execute("ALTER TABLE tracks ADD COLUMN file_sha256 TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'queued',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                next_attempt_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_next_attempt
            ON jobs(status, next_attempt_at)
        """)

        # Backfill normalized fields for legacy rows
        rows = conn.execute("""
            SELECT id, title, artist FROM tracks
            WHERE normalized_title IS NULL OR normalized_artist IS NULL
        """).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE tracks SET normalized_title = ?, normalized_artist = ? WHERE id = ?",
                (normalize_text(row["title"]), normalize_text(row["artist"]), row["id"]),
            )

        # Fix the old typo if any rows have it
        conn.execute("UPDATE tracks SET status = 'discovered' WHERE status = 'dicovered'")


def enqueue_job(conn, track_id: int):
    now = int(time.time())
    conn.execute(
        "INSERT INTO jobs (track_id, status, next_attempt_at, created_at, updated_at) "
        "VALUES (?, 'queued', ?, ?, ?)",
        (track_id, now, now, now),
    )