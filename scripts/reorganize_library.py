import shutil
from pathlib import Path
from database import get_connection, initialize_database
from worker import Worker

LIBRARY_DIR = Path.home() / "Music" / "library"

def main():
    initialize_database()
    # We just need the worker's safe naming logic
    worker = Worker(sources=[], library_dir=LIBRARY_DIR)

    moved = 0

    with get_connection() as conn:
        # Find all tracks that have a file on disk
        tracks = conn.execute(
            "SELECT id, title, artist, library_path FROM tracks WHERE library_path IS NOT NULL"
        ).fetchall()

        for track in tracks:
            current_path = Path(track["library_path"])
            if not current_path.exists():
                continue

            # Determine where it SHOULD be based on DB metadata
            # (If album is missing, it falls back to 'Singles')
            dest_dir = worker._build_dest_dir(track["artist"], album=None)
            target_path = dest_dir / current_path.name

            if current_path != target_path:
                print(f"Moving: {current_path.parent.name}/{current_path.name}")
                print(f"    -> {target_path.parent.name}/{target_path.name}")
                
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current_path), str(target_path))

                # Update the DB with the new path
                conn.execute(
                    "UPDATE tracks SET library_path = ? WHERE id = ?",
                    (str(target_path), track["id"])
                )
                moved += 1
                
                # Clean up the old folder if it's now empty
                try:
                    current_path.parent.rmdir()
                except OSError:
                    pass # Folder wasn't empty (other songs in it)

    print(f"\nReorganization complete. Moved {moved} files into correct artist folders.")

if __name__ == "__main__":
    main()