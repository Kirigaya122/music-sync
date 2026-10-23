import shutil
from pathlib import Path
from database import get_connection, initialize_database
from worker import Worker

LIBRARY_DIR = Path.home() / "Music" / "library"

def main():
    initialize_database()
    worker = Worker(sources=[], library_dir=LIBRARY_DIR)

    moved = 0

    with get_connection() as conn:
        tracks = conn.execute(
            "SELECT id, title, artist, library_path FROM tracks WHERE library_path IS NOT NULL"
        ).fetchall()

        for track in tracks:
            current_path = Path(track["library_path"])
            if not current_path.exists():
                continue

            # Calculate where it SHOULD be using our new clean logic
            dest_dir = worker._build_dest_dir(track["artist"], album=None)
            target_path = dest_dir / current_path.name

            if current_path.parent != dest_dir:
                print(f"Moving: {current_path.parent.name}/{current_path.name}")
                print(f"    -> {target_path.parent.name}/")
                
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current_path), str(target_path))

                conn.execute(
                    "UPDATE tracks SET library_path = ? WHERE id = ?",
                    (str(target_path), track["id"])
                )
                moved += 1
                
                # Delete the old folder if it's now empty (e.g., MUNN or "Lyrical Video...")
                try:
                    current_path.parent.rmdir()
                    print(f"    (Deleted empty folder: {current_path.parent.name})")
                except OSError:
                    pass

    print(f"\nCleanup complete. Moved {moved} files into clean artist folders.")

if __name__ == "__main__":
    main()