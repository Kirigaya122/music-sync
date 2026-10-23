import re
import json
import urllib.request

def get_spotify_track_from_embed(track_id: str) -> dict | None:
    """Fetch track metadata from the public embed page, no auth needed."""
    url = f"https://open.spotify.com/embed/track/{track_id}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # The embed page is a Next.js app and contains a JSON blob in a script tag.
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if not match:
            print("[spotify-scraper] Could not find __NEXT_DATA__ in page")
            return None

        data = json.loads(match.group(1))
        track = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
        
        if not track:
            print("[spotify-scraper] Could not find track entity in JSON")
            return None

        artists = [a.get("name") for a in track.get("artists", []) if a.get("name")]
        artist_str = ", ".join(artists) if artists else "Unknown Artist"

        return {
            "title": track.get("name", "Unknown Title"),
            "artist": artist_str,
            "album": track.get("album", {}).get("name") if track.get("album") else None,
            "duration_ms": track.get("duration", 0),
        }
    except Exception as e:
        print(f"[spotify-scraper] Error fetching embed page: {e}")
        return None