import shutil
from pathlib import Path
from mutagen import File as MutagenFile

LIBRARY_DIR = Path.home() / "Music" / "library"
REVIEW_DIR = Path.home() / "Music" / "Needs_Review"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac"}

def main():
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    moved_count = 0

    print(f"Scanning {LIBRARY_DIR} for unfixable/junk files...")

    for path in LIBRARY_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            try:
                audio = MutagenFile(path, easy=True)
                
                # If mutagen can't read it, or it's missing title/artist tags entirely
                if audio is None or not audio.get("title") or not audio.get("artist"):
                    print(f"  [Moving] {path.name}")
                    
                    # Move to Needs_Review
                    target = REVIEW_DIR / path.name
                    shutil.move(str(path), str(target))
                    moved_count += 1
                    
                    # Clean up the empty folder it left behind
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass # Folder wasn't empty
            except Exception:
                # If it's a corrupted file (like the fake MP3s), move it too
                print(f"  [Moving Corrupted] {path.name}")
                shutil.move(str(path), str(REVIEW_DIR / path.name))
                moved_count += 1

    print(f"\nDone. Moved {moved_count} junk files to {REVIEW_DIR}")

if __name__ == "__main__":
    main()