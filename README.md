# 🎵 Music Sync Pipeline

A self-hosted, automated music acquisition and organization ecosystem.

Discover a song using Shazam or Spotify, share it to your home server, and watch as it automatically downloads the audio, embeds high-res metadata and album art, and organizes it into a clean `Artist / Album` folder structure.

## ✨ Features

- **Multi-Source Discovery:** Share directly from Shazam or Spotify.
- **Smart Parsing:** Extracts title, artist, and stable IDs directly from shared text or Spotify URLs (no API keys required, uses public web scraping).
- **Automated Downloading:** Uses `yt-dlp` and `ffmpeg` to fetch high-quality audio and convert it to MP3.
- **Deduplication:** Prevents downloading the same song twice using source IDs and metadata normalization.
- **Local Inbox Ingestion:** Drop manually downloaded files into an `inbox` folder, and the system will match them to your Shazam history.
- **Metadata & Artwork Fixing:** Scrapes the iTunes API to automatically fetch missing tags and 600x600 album art for your local files.
- **Background Worker:** Processes downloads asynchronously with exponential backoff on failures.
- **Native Android App:** A custom Kotlin app with offline queueing, sync history, and a native share-target.

## 🏗️ Architecture

1. **Android Phone:** The custom Kotlin app (in `/android`) sends shared text to the server over local Wi-Fi.
2. **FastAPI Server:** Validates the request, parses metadata, and queues a background job in the database.
3. **Worker Thread:** Polls the SQLite database, searches for the track (via local inbox or `yt-dlp`), and downloads it.
4. **Library Organization:** Files are moved to `~/Music/library/Artist/Singles/` and tagged via `mutagen`.

## 🛠️ Tech Stack

- **Backend:** Python 3, FastAPI, Uvicorn
- **Database:** SQLite
- **Download Engine:** `yt-dlp`, `ffmpeg`
- **Metadata Parsing:** `mutagen`, `requests`, web scraping
- **Client:** Kotlin (Android), OkHttp

## 🚀 Server Setup

### 1. Prerequisites (Ubuntu Server)

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg sqlite3
```

### 2. Project Installation

```bash
git clone https://github.com/kirigaya122/music-sync.git
cd music-sync

python3 -m venv .venv
source .venv/bin/activate

pip install fastapi "uvicorn[standard]" mutagen yt-dlp requests
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

## 🛠️ Utility Scripts

The `scripts/` folder contains powerful tools to maintain your library:

- `python -m scripts.scan_inbox` : Scan `~/Music/inbox` for new files and queue them.
- `python -m scripts.reconcile_library` : Re-link existing files in the library folder to the database.
- `python -m scripts.clean_library` : Reorganize files into the proper `Artist/Singles` structure and fix folder names.
- `python -m scripts.fix_metadata` : Automatically fetch missing ID3 tags and album art from iTunes for your whole library.
- `python -m scripts.cleanup_junk` : Move corrupted or untaggable files into a `~/Music/Needs_Review` folder.

## 📱 Android App Setup (Kotlin)

The repository includes a custom Kotlin Android app in the `android/` directory. It acts as a native Share Target and a dashboard for managing your library.

### Features

- **Native Share Menu:** Share directly from Shazam or Spotify.
- **Offline Queueing:** If the server is unreachable, the app saves the track locally and automatically syncs when you are back on Wi-Fi.
- **Dashboard:** View sync history, manage pending offline items, and edit raw share text if the metadata parser needs a nudge.
- **Silent Execution:** Sends the payload in the background and disappears instantly.

### How to Build

1. Open the `android/` folder in **Android Studio**.
2. Update the IP address in `android/app/src/main/res/xml/network_security_config.xml` to match your server's local IP.
3. Build and install the APK on your phone.
4. Open the app, enter your Server URL (e.g., `http://192.168.1.185:8000`) and your Bearer Token.
5. Share a song from Shazam or Spotify!

## ⚠️ Disclaimer

This project is for **personal use only**.

- The Spotify integration uses public web scraping to fetch metadata and does not bypass any DRM.
- Downloading copyrighted material from YouTube via `yt-dlp` may violate YouTube's Terms of Service or local copyright laws. Please use this tool responsibly and respect the rights of artists.
