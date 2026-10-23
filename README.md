---

````markdown
# 🎵 Music Sync Pipeline

A self-hosted, automated music acquisition and organization system.

Discover a song using Shazam or Spotify, share it to your home server, and watch as it automatically downloads the audio, verifies it, embeds metadata, and organizes it into a clean `Artist / Album` folder structure.

## ✨ Features

- **Multi-Source Discovery:** Share directly from Shazam or Spotify.
- **Smart Parsing:** Extracts title, artist, and stable IDs directly from shared text or Spotify URLs (no API keys required).
- **Automated Downloading:** Uses `yt-dlp` and `ffmpeg` to fetch high-quality audio and convert it to MP3.
- **Deduplication:** Prevents downloading the same song twice using source IDs and metadata normalization.
- **Local Inbox Ingestion:** Drop manually downloaded files into an `inbox` folder, and the system will match them to your Shazam history and organize them.
- **Background Worker:** Processes downloads asynchronously with exponential backoff on failures.
- **Automated Library Management:** Embeds ID3 tags and organizes files into `~/Music/library/Artist/Singles/`.

## 🏗️ Architecture

1. **Android Phone:** Uses the `HTTP Shortcuts` app to POST shared text to the server over local Wi-Fi.
2. **FastAPI Server:** Validates the request, parses metadata, and queues a background job.
3. **Worker Thread:** Polls the database, searches for the track (via local inbox or YouTube), and downloads it.
4. **SQLite Database:** Tracks submissions, job statuses, file hashes, and library paths.

## 🛠️ Tech Stack

- **Backend:** Python 3, FastAPI, Uvicorn
- **Database:** SQLite
- **Download Engine:** `yt-dlp`, `ffmpeg`
- **Metadata Parsing:** `mutagen`, regex, and web scraping
- **Client:** Android + HTTP Shortcuts

## 🚀 Setup Instructions

### 1. Prerequisites (Ubuntu Server)

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg sqlite3
```
````

### 2. Project Installation

```bash
git clone https://github.com/yourusername/music-sync.git
cd music-sync

python3 -m venv .venv
source .venv/bin/activate

pip install fastapi "uvicorn[standard]" mutagen yt-dlp
```

### 3. Generate API Token

The server requires a Bearer token to authenticate incoming requests from your phone.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))" > token.txt
chmod 600 token.txt
```

### 4. Set Up Folders

Create the folders where the server will look for local files and store your organized library.

```bash
mkdir -p ~/Music/inbox ~/Music/library
```

### 5. Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

_Find your server's local IP address using `hostname -I` (e.g., `192.168.1.185`)._

## 📱 Android Setup (HTTP Shortcuts)

1. Install **HTTP Shortcuts** from the Google Play Store.
2. Create a new shortcut:
   - **Method:** POST
   - **URL:** `http://<YOUR_SERVER_IP>:8000/tracks`
   - **Headers:** `Authorization: Bearer <YOUR_TOKEN_FROM_TOKEN.TXT>`
   - **Body (JSON):**
     ```json
     {
       "source": "shazam",
       "raw_share": "{{shared_text}}"
     }
     ```
3. Go to **Global Variables**, create `shared_text`, and enable **"Allow Receiving Value from Share Dialog"**.
4. Share a song from Shazam or Spotify to HTTP Shortcuts.

## 📜 Utility Scripts

- `python scan_inbox.py`: Scan `~/Music/inbox` for new files and queue them for processing.
- `python reconcile_library.py`: Re-link existing files in the library folder to the database.
- `python clean_library.py`: Reorganize existing files into the proper `Artist/Singles` structure.

## ⚠️ Disclaimer

This project is for **personal use only**.

- The Spotify integration uses public web scraping to fetch metadata and does not bypass any DRM.
- Downloading copyrighted material from YouTube via `yt-dlp` may violate YouTube's Terms of Service or local copyright laws. Please use this tool responsibly and respect the rights of artists.

```

```
