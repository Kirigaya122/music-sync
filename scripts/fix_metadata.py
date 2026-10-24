import os
import re
import requests
from pathlib import Path
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture

import sys
sys.path.append(str(Path(__file__).parent.parent))
from sources.local import _clean_for_matching 

LIBRARY_DIR = Path.home() / "Music" / "library"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac"}
FAKE_ARTISTS = {"nightcore", "amv", "playlist", "music", "lyrics", "unknown", "extended"}

def search_itunes(title, artist):
    query = f"{artist} {title}".strip()
    url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&entity=song&limit=1"
    
    try:
        response = requests.get(url, timeout=10).json()
        if response.get("resultCount", 0) > 0:
            result = response["results"][0]
            artwork_url = result.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
            return {
                "title": result.get("trackName"),
                "artist": result.get("artistName"),
                "album": result.get("collectionName"),
                "artwork_url": artwork_url
            }
    except Exception:
        pass
    return None

def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None

def fix_file(path: Path):
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        return

    if audio is None:
        return

    title = (audio.get("title") or [None])[0]
    artist = (audio.get("artist") or [None])[0]
    
    # Smarter filename parsing
    if not title or not artist:
        stem = path.stem
        # Replace hyphens without spaces with " - " to make splitting easier
        clean_stem = re.sub(r'(?<!\s)-(?!\s)', ' - ', stem)
        
        if " - " in clean_stem:
            # Split on the FIRST hyphen (usually Artist - Title)
            left, _, right = clean_stem.partition(" - ")
            artist = artist or left.strip()
            title = title or right.strip()
        else:
            title = title or clean_stem

    clean_title = _clean_for_matching(title)
    clean_artist = _clean_for_matching(artist)
    
    # If the artist is garbage, try searching just the title
    if clean_artist and clean_artist.lower() in FAKE_ARTISTS:
        clean_artist = ""
    if not clean_artist and not clean_title:
        return

    meta = search_itunes(clean_title, clean_artist)
    
    # If it fails, try searching with the original uncleaned title
    if not meta:
        meta = search_itunes(title, artist)

    if not meta:
        print(f"  [-] No match found for: {title} - {artist}")
        return

    print(f"  [+] Fixing: {meta['artist']} - {meta['title']} ({meta['album']})")
    
    art_data = None
    if meta["artwork_url"]:
        art_data = download_image(meta["artwork_url"])

    try:
        if path.suffix.lower() == ".mp3":
            try:
                tags = ID3(path)
            except Exception:
                tags = ID3() 
            
            tags.add(TIT2(encoding=3, text=meta['title']))
            tags.add(TPE1(encoding=3, text=meta['artist']))
            tags.add(TALB(encoding=3, text=meta['album']))
            if art_data:
                tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=art_data))
            tags.save(path, v2_version=3)

        elif path.suffix.lower() == ".m4a":
            audio = MP4(path)
            audio["\xa9nam"] = [meta['title']]
            audio["\xa9ART"] = [meta['artist']]
            audio["\xa9alb"] = [meta['album']]
            if art_data:
                audio["covr"] = [MP4Cover(art_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

        elif path.suffix.lower() == ".flac":
            audio = FLAC(path)
            audio["title"] = meta['title']
            audio["artist"] = meta['artist']
            audio["album"] = meta['album']
            if art_data:
                pic = Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                pic.data = art_data
                audio.add_picture(pic)
            audio.save()
    except Exception:
        pass 

def main():
    print(f"Scanning {LIBRARY_DIR} for missing metadata and artwork...")
    count = 0
    
    for path in LIBRARY_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            has_art = False
            try:
                if path.suffix.lower() == ".mp3":
                    tags = ID3(path)
                    has_art = any(k.startswith('APIC') for k in tags.keys())
                elif path.suffix.lower() == ".m4a":
                    has_art = bool(MP4(path).get("covr"))
                elif path.suffix.lower() == ".flac":
                    has_art = bool(FLAC(path).pictures)
            except Exception:
                pass 

            if not has_art:
                fix_file(path)
                count += 1

    print(f"\nDone. Processed {count} files.")

if __name__ == "__main__":
    main()