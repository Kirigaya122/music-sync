import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from database import get_connection, initialize_database
from utils import normalize_text
from auth import require_token
from parsers import parse_shazam_share

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield

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
        if track.source_id is not None:
            existing = conn.execute(
                """
                SELECT * FROM tracks
                WHERE source = ? AND source_id = ?
                """,
                (track.source, track.source_id),
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
                    track.source_id,
                    normalized_title,
                    normalized_artist,
                    track.raw_share,
                ),
            )
        except sqlite3.IntegrityError:
            if track.source_id is not None:
                existing = conn.execute(
                    """
                    SELECT * FROM tracks
                    WHERE source = ? AND source_id = ?
                    """,
                    (track.source, track.source_id),
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

        return {
            "message": "Track registered",
            "duplicate": False,
            "match_type": None,
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