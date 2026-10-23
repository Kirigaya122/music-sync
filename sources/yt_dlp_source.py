import hashlib
from pathlib import Path
import yt_dlp

from .base import AudioSource, Candidate, AcquiredFile

class YtDlpSource(AudioSource):
    name = "yt-dlp"

    def _get_ydl_opts(self, **kwargs):
        """Base options for both search and download."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            # Cookies are intentionally omitted here to prevent YouTube format blocks.
            # If you get bot-check errors in the future, we can add the 'cookiefile' option.
        }
        opts.update(kwargs)
        return opts

    def search(self, title, artist, duration_seconds=None):
        query = f"ytsearch1:{artist} - {title} audio"
        ydl_opts = self._get_ydl_opts()

        print(f"[yt-dlp] Searching: {query}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if not info or 'entries' not in info or not info['entries']:
                    print("[yt-dlp] Search returned no entries.")
                    return []
                
                entry = info['entries'][0]
                full_url = entry.get('webpage_url')
                if not full_url:
                    print("[yt-dlp] Found entry but no URL.")
                    return []

                print(f"[yt-dlp] Found: {entry.get('title')} ({full_url})")
                return [Candidate(
                    source_name=self.name,
                    locator=full_url,
                    confidence=0.9,
                    title=title,
                    artist=artist,
                    extra={"video_title": entry.get('title')}
                )]
            except Exception as e:
                print(f"[yt-dlp] Search exception: {e}")
        return []

    def acquire(self, candidate, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_artist = candidate.artist.replace('/', '_')
        safe_title = candidate.title.replace('/', '_')
        outtmpl = str(dest_dir / f"{safe_artist} - {safe_title}.%(ext)s")

        ydl_opts = self._get_ydl_opts(
            format='bestaudio/best',
            postprocessors=[
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {
                    'key': 'FFmpegMetadata', # Embeds title/artist into the MP3 ID3 tags
                    'add_metadata': True,
                }
            ],
            outtmpl=outtmpl,
        )

        print(f"[yt-dlp] Downloading: {candidate.locator}")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([candidate.locator])
                final_path = dest_dir / f"{safe_artist} - {safe_title}.mp3"
                
                if not final_path.exists():
                    print(f"[yt-dlp] Failed: File not found.")
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