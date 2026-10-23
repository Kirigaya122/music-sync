import hashlib
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile

from utils import normalize_text
from .base import AudioSource, Candidate, AcquiredFile

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}
MATCH_THRESHOLD = 0.85

# Words to ignore when comparing titles
NOISE_WORDS = {
    "official", "lyric", "video", "audio", "music", "hd", "hq", 
    "visualizer", "remastered", "remaster", "explicit", "clean"
}

def _clean_for_matching(text: str) -> str:
    """Remove common YouTube/filename noise from normalized text."""
    if not text:
        return ""
    words = text.split()
    cleaned = [w for w in words if w not in NOISE_WORDS]
    return " ".join(cleaned)

def _read_tags(path: Path) -> list[dict]:
    """Read tags via mutagen. Returns a list of possible interpretations."""
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None

    title = None
    artist = None
    album = None
    track_number = None
    duration = None

    if audio is not None:
        title = (audio.get("title") or [None])[0]
        artist = (audio.get("artist") or [None])[0]
        album = (audio.get("album") or [None])[0]
        track_number_raw = (audio.get("tracknumber") or [None])[0]
        duration = getattr(audio.info, "length", None)
        
        try:
            track_number = int(str(track_number_raw).split("/")[0]) if track_number_raw else None
        except (ValueError, TypeError):
            track_number = None

    # If tags are complete, return them as the single truth
    if title and artist:
        return [{
            "title": title,
            "artist": artist,
            "album": album,
            "track_number": track_number,
            "duration_seconds": duration,
        }]

    # Fallback: parse filename
    stem = path.stem
    # Remove bracketed text like (Official Video) or [Lyric Video] from filename
    clean_stem = re.sub(r'[\(\[].*?[\)\]]', '', stem).strip()
    
    results = []
    
    # Try splitting by " - "
    if " - " in clean_stem:
        left, _, right = clean_stem.partition(" - ")
        left, right = left.strip(), right.strip()
        
        # Interpretation 1: Title - Artist
        results.append({
            "title": title or left,
            "artist": artist or right,
            "album": album,
            "track_number": track_number,
            "duration_seconds": duration,
        })
        
        # Interpretation 2: Artist - Title (if both tags are missing)
        if not title or not artist:
            results.append({
                "title": right,
                "artist": left,
                "album": album,
                "track_number": track_number,
                "duration_seconds": duration,
            })
    else:
        results.append({
            "title": title or clean_stem,
            "artist": artist or "Unknown Artist",
            "album": album,
            "track_number": track_number,
            "duration_seconds": duration,
        })

    return results


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _similarity(a: str, b: str) -> float:
    """Fuzzy match with a boost for subset containment."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
        
    a_words = set(a.split())
    b_words = set(b.split())
    
    if not a_words or not b_words:
        return 0.0
        
    # If all words of one are in the other (e.g. "laodicea" inside "laodicea official video")
    if a_words.issubset(b_words) or b_words.issubset(a_words):
        return 0.95
        
    return SequenceMatcher(None, a, b).ratio()


class LocalInboxSource(AudioSource):
    name = "local"

    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def search(self, title, artist, duration_seconds=None):
        want_title = _clean_for_matching(normalize_text(title))
        want_artist = _clean_for_matching(normalize_text(artist))

        candidates: list[Candidate] = []
        
        for path in self.inbox_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
                
            possible_tags = _read_tags(path)
            if not possible_tags:
                continue
                
            best_score = 0.0
            best_tags = possible_tags[0]
            
            # Test all interpretations (Title-Artist and Artist-Title)
            for tags in possible_tags:
                got_title = _clean_for_matching(normalize_text(tags["title"]))
                got_artist = _clean_for_matching(normalize_text(tags["artist"]))

                t_score = _similarity(want_title, got_title)
                a_score = _similarity(want_artist, got_artist)
                score = (t_score * 0.6) + (a_score * 0.4)
                
                if score > best_score:
                    best_score = score
                    best_tags = tags

            if best_score < MATCH_THRESHOLD:
                continue

            candidates.append(Candidate(
                source_name=self.name,
                locator=str(path),
                confidence=best_score,
                title=best_tags["title"],
                artist=best_tags["artist"],
                duration_seconds=best_tags["duration_seconds"],
                extra={"path": path, "album": best_tags["album"], "track_number": best_tags["track_number"]},
            ))

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates

    def acquire(self, candidate, dest_dir):
        source_path = Path(candidate.extra["path"])
        if not source_path.exists():
            return None

        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / source_path.name
        try:
            shutil.move(str(source_path), str(target))
        except OSError:
            return None

        return AcquiredFile(
            path=target,
            sha256=_hash_file(target),
            title=candidate.title,
            artist=candidate.artist,
            album=candidate.extra.get("album"),
            track_number=candidate.extra.get("track_number"),
            duration_seconds=candidate.duration_seconds,
        )