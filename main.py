import sqlite3
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from database import get_connection, initialize_database, enqueue_job
from sources.local import LocalInboxSource
from worker import Worker
from utils import normalize_text
from auth import require_token
from parsers import parse_shazam_share
from sources.yt_dlp_source import YtDlpSource


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()

    inbox = Path.home() / "Music" / "inbox"
    library = Path.home() / "Music" / "library"
    library.mkdir(parents=True, exist_ok=True)

    worker = Worker(
        sources=[
            LocalInboxSource(inbox),
            YtDlpSource()          # <-- Add the network source here
        ],
        library_dir=library,
        poll_interval=10,
    )
    worker.start()
    app.state.worker = worker

    yield

    worker.stop()

app = FastAPI(
    title="Music Sync",
    description="Personal music discovery and library API",
    version="0.2.1",
    lifespan=lifespan,
)

class TrackSubmission(BaseModel):
    title: str | None = Field(default=None, max_length=2000)
    artist: str | None = Field(default=None, max_length=300)
    source: Literal["shazam", "spotify", "manual"]
    source_id: str | None = Field(default=None, max_length=300)
    raw_share: str | None = Field(default=None, max_length=5000)

def get_track(conn, track_id: int):
    row = conn.execute(
        "SELECT * FROM tracks WHERE id = ?",
        (track_id,),
    ).fetchone()
    return dict(row) if row else None

@app.get("/")
def home():
    return {"service": "Music Sync", "status": "running"}

@app.post("/tracks", status_code=201)
def submit_track(
    track: TrackSubmission,
    _: None = Depends(require_token),
):
    title = track.title.strip() if track.title else None
    artist = track.artist.strip() if track.artist else None
    source_id = track.source_id

    # If this is a raw Shazam share, parse it server-side.
    if track.source == "shazam" and track.raw_share:
        parsed = parse_shazam_share(track.raw_share)
        title = parsed.title
        artist = parsed.artist or "Unknown Artist"
        if parsed.source_id:
            source_id = parsed.source_id

    if not title or not artist:
        raise HTTPException(
            status_code=422,
            detail="Could not determine title and artist from the submission",
        )

    normalized_title = normalize_text(title)
    normalized_artist = normalize_text(artist)

    with get_connection() as conn:
        # 1. Exact duplicate from the same source.
        if source_id is not None:
            existing = conn.execute(
                """
                SELECT * FROM tracks
                WHERE source = ? AND source_id = ?
                """,
                (track.source, source_id),
            ).fetchone()

            if existing:
                return {
                    "message": "Track already registered by this source",
                    "duplicate": True,
                    "match_type": "source_id",
                    "track": dict(existing),
                }

        # 2. Potential duplicate across different sources.
        candidates = conn.execute(
            """
            SELECT * FROM tracks
            WHERE normalized_title = ?
              AND normalized_artist = ?
            ORDER BY id
            """,
            (normalized_title, normalized_artist),
        ).fetchall()

        if candidates:
            return {
                "message": "Possible existing track; no new record created",
                "duplicate": True,
                "match_type": "artist_title",
                "review_required": True,
                "existing_tracks": [dict(row) for row in candidates],
            }

        # 3. Register a new discovery.
        try:
            cursor = conn.execute(
                """
                INSERT INTO tracks (
                    title,
                    artist,
                    source,
                    source_id,
                    normalized_title,
                    normalized_artist,
                    raw_share
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    artist,
                    track.source,
                    source_id,
                    normalized_title,
                    normalized_artist,
                    track.raw_share,
                ),
            )
        except sqlite3.IntegrityError:
            if source_id is not None:
                existing = conn.execute(
                    """
                    SELECT * FROM tracks
                    WHERE source = ? AND source_id = ?
                    """,
                    (track.source, source_id),
                ).fetchone()

                if existing:
                    return {
                        "message": "Track already registered",
                        "duplicate": True,
                        "match_type": "source_id",
                        "track": dict(existing),
                    }

            raise

        saved = get_track(conn, cursor.lastrowid)
        enqueue_job(conn, cursor.lastrowid)

        return {
            "message": "Track registered",
            "duplicate": False,
            "match_type": None,
            "job_queued": True,
            "track": saved,
        }

@app.get("/tracks")
def list_tracks():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tracks ORDER BY id DESC"
        ).fetchall()

        return {
            "count": len(rows),
            "tracks": [dict(row) for row in rows],
        }
        
@app.get("/jobs")
def list_jobs():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT j.*, t.title, t.artist, t.status AS track_status
            FROM jobs j
            JOIN tracks t ON t.id = j.track_id
            ORDER BY j.id DESC
            LIMIT 100
        """).fetchall()
        return {"count": len(rows), "jobs": [dict(r) for r in rows]}