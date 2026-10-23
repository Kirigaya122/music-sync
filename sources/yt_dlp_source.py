import hashlib
from pathlib import Path
from typing import Optional
import yt_dlp

from utils import normalize_text
from .base import AudioSource, Candidate, AcquiredFile

class YtDlpSource(AudioSource):
    name = "yt-dlp"
    
    def search(self, title, artist, duration_seconds=None):
        # We specify ytsearch1: directly in the query to guarantee 1 result
        query = f"ytsearch1:{artist} - {title} audio"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }

        print(f"[yt-dlp] Searching: {query}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                
                if not info:
                    print("[yt-dlp] Search returned None (possible network block)")
                    return []
                    
                if 'entries' not in info or len(info['entries']) == 0:
                    print(f"[yt-dlp] Search returned no entries. Raw response: {info}")
                    return []
                    
                entry = info['entries'][0]
                
                # In normal mode (no extract_flat), the full URL is in entry['webpage_url']
                full_url = entry.get('webpage_url')
                if not full_url:
                    print(f"[yt-dlp] Found entry but no URL: {entry.get('id')}")
                    return []
                    
                video_title = entry.get('title', 'Unknown')

                print(f"[yt-dlp] Found: {video_title} ({full_url})")

                return [Candidate(
                    source_name=self.name,
                    locator=full_url,
                    confidence=0.9,
                    title=title,
                    artist=artist,
                    extra={"video_title": video_title}
                )]
            except Exception as e:
                print(f"[yt-dlp] Search exception: {e}")
        
        return []

    def acquire(self, candidate, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        safe_artist = candidate.artist.replace('/', '_')
        safe_title = candidate.title.replace('/', '_')
        outtmpl = str(dest_dir / f"{safe_artist} - {safe_title}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            # Force the Android client to bypass some bot checks
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }

        print(f"[yt-dlp] Downloading: {candidate.locator}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([candidate.locator])
                
                final_path = dest_dir / f"{safe_artist} - {safe_title}.mp3"
                
                if not final_path.exists():
                    print(f"[yt-dlp] Failed: File not found at {final_path} after download.")
                    return None

                print(f"[yt-dlp] Successfully saved: {final_path.name}")

                return AcquiredFile(
                    path=final_path,
                    sha256=self._hash_file(final_path),
                    title=candidate.title,
                    artist=candidate.artist,
                    album="Singles",
                    track_number=None,
                    duration_seconds=None,
                )
        except Exception as e:
            print(f"[yt-dlp] Download failed: {e}")
            return None

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()