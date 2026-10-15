import re
from dataclasses import dataclass

SHAZAM_URL_RE = re.compile(
    r"https?://(?:www\.)?shazam\.com/\S+",
    re.IGNORECASE,
)
SHAZAM_TRACK_ID_RE = re.compile(r"/track/(\d+)", re.IGNORECASE)


@dataclass
class ParsedShare:
    title: str
    artist: str | None
    url: str | None
    source_id: str | None


def parse_shazam_share(raw: str) -> ParsedShare:
    """Parse a Shazam share string into structured fields.

    Expected format:
        <title> by <artist> <url>

    Both " by <artist>" and the URL are optional in practice,
    so the parser degrades gracefully if either is missing.
    """
    raw = raw.strip()

    # 1. Pull out the first URL that looks like a Shazam link.
    url_match = SHAZAM_URL_RE.search(raw)
    url = url_match.group(0) if url_match else None

    # 2. Remove the URL from the string; whatever's left is "title by artist".
    text = SHAZAM_URL_RE.sub("", raw).strip()

    # 3. Split on the LAST occurrence of " by " so a title containing the word "by" doesn't get chopped in the wrong place.
    title = text
    artist = None
    if " by " in text:
        title, _, artist = text.rpartition(" by ")
        title = title.strip()
        artist = artist.strip() or None

    # 4. Extract the numeric track ID from the URL. This is stable across slug and query-string changes, so it's the best source_id we can derive from a Shazam share.
    source_id = None
    if url:
        id_match = SHAZAM_TRACK_ID_RE.search(url)
        if id_match:
            source_id = id_match.group(1)

    return ParsedShare(title=title, artist=artist, url=url, source_id=source_id)