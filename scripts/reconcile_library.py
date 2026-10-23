import time
from pathlib import Path

from database import get_connection, initialize_database
from utils import normalize_text
from sources.local import _read_tags, _hash_file, AUDIO_EXTENSIONS

LIBRARY_DIR = Path.home() / "Music" / "library"

def main():
    if not LIBRARY_DIR.exists():
        print(f"Library directory not found: {LIBRARY_DIR}")
        return

    print(f"Scanning library: {LIBRARY_DIR}...")
    initialize_database()

    linked_count = 0
    already_linked = 0
    missing_in_db = 0

    # rglob("*") recursively finds everything in subfolders
    for path in LIBRARY_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        # 1. Read the tags of the file on disk
        possible_tags = _read_tags(path)
        if not possible_tags:
            print(f"  [skip] Could not read tags: {path.name}")
            continue
        
        tags = possible_tags[0]
        norm_title = normalize_text(tags["title"])
        norm_artist = normalize_text(tags["artist"])

        with get_connection() as conn:
            # 2. Look for a track in the DB missing a library path
            track = conn.execute(
                """
                SELECT id, title, artist FROM tracks 
                WHERE normalized_title = ? AND normalized_artist = ? 
                  AND library_path IS NULL
                LIMIT 1
                """,
                (norm_title, norm_artist)
            ).fetchone()

            if not track:
                # Check if it's already linked (maybe the worker just finished it)
                existing = conn.execute(
                    "SELECT id FROM tracks WHERE normalized_title = ? AND normalized_artist = ? AND library_path IS NOT NULL",
                    (norm_title, norm_artist)
                ).fetchone()
                
                if existing:
                    already_linked += 1
                else:
                    print(f"  [orphan] File on disk not found in DB: {tags['artist']} - {tags['title']}")
                    missing_in_db += 1
                continue

            # 3. Calculate the hash and update the DB
            print(f"  [linking] {track['artist']} - {track['title']}")
            file_hash = _hash_file(path)
            now = int(time.time())

            conn.execute(
                """
                UPDATE tracks 
                SET library_path = ?, file_sha256 = ?, status = 'library' 
                WHERE id = ?
                """,
                (str(path), file_hash, track["id"])
            )
            
            # Mark any pending jobs for this track as complete
            conn.execute(
                "UPDATE jobs SET status = 'complete', updated_at = ? WHERE track_id = ? AND status != 'complete'",
                (now, track["id"])
            )
            linked_count += 1

    print("\n--- Reconciliation Complete ---")
    print(f"Linked:          {linked_count}")
    print(f"Already linked:  {already_linked}")
    print(f"Orphans (no DB): {missing_in_db}")

if __name__ == "__main__":
    main()