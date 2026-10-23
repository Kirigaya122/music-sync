import re
from dataclasses import dataclass
from spotify_scraper import get_spotify_track_from_embed

SHAZAM_URL_RE = re.compile(r"https?://(?:www\.)?shazam\.com/\S+", re.IGNORECASE)
SHAZAM_TRACK_ID_RE = re.compile(r"/track/(\d+)", re.IGNORECASE)
SPOTIFY_URL_RE = re.compile(r"spotify\.com/track/([a-zA-Z0-9]+)")

@dataclass
class ParsedShare:
    title: str
    artist: str | None
    url: str | None
    source_id: str | None

def parse_shazam_share(raw: str) -> ParsedShare:
    raw = raw.strip()
    url_match = SHAZAM_URL_RE.search(raw)
    url = url_match.group(0) if url_match else None

    text = SHAZAM_URL_RE.sub("", raw).strip()
    title = text
    artist = None
    if " by " in text:
        title, _, artist = text.rpartition(" by ")
        title, artist = title.strip(), artist.strip() or None

    source_id = None
    if url:
        id_match = SHAZAM_TRACK_ID_RE.search(url)
        if id_match:
            source_id = id_match.group(1)

    return ParsedShare(title=title, artist=artist, url=url, source_id=source_id)


def parse_spotify_share(raw: str) -> ParsedShare | None:
    """Parse a Spotify URL, fetch metadata from the embed page, and return a ParsedShare."""
    match = SPOTIFY_URL_RE.search(raw)
    if not match:
        return None

    track_id = match.group(1)
    print(f"[spotify] Fetching metadata via embed page for ID: {track_id}")

    meta = get_spotify_track_from_embed(track_id)
    if not meta:
        return None

    return ParsedShare(
        title=meta["title"],
        artist=meta["artist"],
        url=raw,
        source_id=track_id
    )