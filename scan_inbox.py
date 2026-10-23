from pathlib import Path
from database import get_connection, initialize_database, enqueue_job
from utils import normalize_text
from sources.local import _read_tags

INBOX_DIR = Path.home() / "Music" / "inbox"

def main():
    if not INBOX_DIR.exists():
        print(f"Inbox directory not found: {INBOX_DIR}")
        return

    print(f"Scanning {INBOX_DIR}...")
    initialize_database()
    
    added = 0
    skipped = 0

    with get_connection() as conn:
        for path in INBOX_DIR.iterdir():
            if not path.is_file() or path.suffix.lower() not in {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}:
                continue

            # Get the best tag interpretation (using the logic from our LocalInboxSource)
            possible_tags = _read_tags(path)
            if not possible_tags:
                print(f"  [skip] Could not read tags: {path.name}")
                skipped += 1
                continue

            # Use the first interpretation (usually Title - Artist)
            tags = possible_tags[0]
            title = tags["title"]
            artist = tags["artist"]

            norm_title = normalize_text(title)
            norm_artist = normalize_text(artist)

            # Check if we already have this track in the DB
            existing = conn.execute(
                """
                SELECT id FROM tracks 
                WHERE normalized_title = ? AND normalized_artist = ?
                """,
                (norm_title, norm_artist)
            ).fetchone()

            if existing:
                track_id = existing["id"]
                # Check if there's already a pending job for it
                has_job = conn.execute(
                    "SELECT id FROM jobs WHERE track_id = ? AND status = 'queued'", 
                    (track_id,)
                ).fetchone()
                
                if not has_job:
                    enqueue_job(conn, track_id)
                    print(f"  [queued] Existing track found in DB: {artist} - {title}")
                else:
                    print(f"  [skip] Already queued: {artist} - {title}")
                skipped += 1
                continue

            # Insert as a new track
            cursor = conn.execute(
                """
                INSERT INTO tracks (
                    title, artist, source, source_id, status, normalized_title, normalized_artist
                ) VALUES (?, ?, 'local', NULL, 'discovered', ?, ?)
                """,
                (title, artist, norm_title, norm_artist)
            )
            track_id = cursor.lastrowid
            
            # Queue the job
            enqueue_job(conn, track_id)
            print(f"  [added] New track: {artist} - {title}")
            added += 1

    print(f"\nDone. Added {added} new tracks to the queue.")

if __name__ == "__main__":
    main()