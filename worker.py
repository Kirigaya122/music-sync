import threading
import time
from pathlib import Path
from typing import Optional

from database import get_connection
from sources.base import AudioSource

MAX_ATTEMPTS = 20
RETRY_DELAYS = [30, 60, 300, 900, 1800, 3600]  # 30s, 1m, 5m, 15m, 30m, then 1h


class Worker:
    def __init__(
        self,
        sources: list[AudioSource],
        library_dir: Path,
        poll_interval: int = 10,
    ):
        self.sources = sources
        self.library_dir = library_dir
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                print(f"[worker] tick failed: {exc}")
            self._stop.wait(self.poll_interval)

    def _tick(self):
        now = int(time.time())
        with get_connection() as conn:
            job = conn.execute(
                """
                SELECT j.*, t.title, t.artist
                FROM jobs j
                JOIN tracks t ON t.id = j.track_id
                WHERE j.status = 'queued' AND j.next_attempt_at <= ?
                ORDER BY j.next_attempt_at
                LIMIT 1
                """,
                (now,),
            ).fetchone()

            if not job:
                return

            print(f"[worker] attempting track {job['track_id']}: {job['title']} - {job['artist']}")

            self._process_job(conn, job)

    def _process_job(self, conn, job):
        # Find a candidate across all sources
        candidate = None
        for source in self.sources:
            try:
                candidates = source.search(job["title"], job["artist"])
            except Exception as exc:
                print(f"[worker] source {source.name} search failed: {exc}")
                continue
            if candidates:
                candidate = (source, candidates[0])
                break

        if candidate is None:
            self._fail_attempt(conn, job, "no candidates found")
            return

        source, cand = candidate
        dest_dir = self._build_dest_dir(cand.artist, cand.extra.get("album"))
        acquired = source.acquire(cand, dest_dir)

        if acquired is None:
            self._fail_attempt(conn, job, f"acquire failed from {source.name}")
            return

        # Hash collision check
        dup = conn.execute(
            "SELECT id FROM tracks WHERE file_sha256 = ? AND id != ?",
            (acquired.sha256, job["track_id"]),
        ).fetchone()

        if dup:
            # Same audio as another track — don't duplicate on disk
            acquired.path.unlink(missing_ok=True)
            conn.execute(
                """
                UPDATE tracks
                SET status = 'library', library_path = (
                    SELECT library_path FROM tracks WHERE id = ?
                ), file_sha256 = ?
                WHERE id = ?
                """,
                (dup["id"], acquired.sha256, job["track_id"]),
            )
        else:
            conn.execute(
                """
                UPDATE tracks
                SET status = 'library', library_path = ?, file_sha256 = ?
                WHERE id = ?
                """,
                (str(acquired.path), acquired.sha256, job["track_id"]),
            )

        conn.execute(
            "UPDATE jobs SET status = 'complete', updated_at = ? WHERE id = ?",
            (int(time.time()), job["id"]),
        )
        print(f"[worker] track {job['track_id']} → {acquired.path}")

    def _fail_attempt(self, conn, job, reason):
        attempts = job["attempts"] + 1
        now = int(time.time())

        if attempts >= MAX_ATTEMPTS:
            conn.execute(
                "UPDATE jobs SET status = 'needs_source', attempts = ?, last_error = ?, updated_at = ? WHERE id = ?",
                (attempts, reason, now, job["id"]),
            )
            conn.execute(
                "UPDATE tracks SET status = 'needs_source' WHERE id = ?",
                (job["track_id"],),
            )
            print(f"[worker] track {job['track_id']} needs_source after {attempts} attempts")
            return

        delay_idx = min(attempts - 1, len(RETRY_DELAYS) - 1)
        next_at = now + RETRY_DELAYS[delay_idx]
        conn.execute(
            "UPDATE jobs SET attempts = ?, last_error = ?, next_attempt_at = ?, updated_at = ? WHERE id = ?",
            (attempts, reason, next_at, now, job["id"]),
        )

    def _build_dest_dir(self, artist: str, album: Optional[str]) -> Path:
        safe_artist = self._safe(artist)
        safe_album = self._safe(album or "Singles")
        return self.library_dir / safe_artist / safe_album

    @staticmethod
    def _safe(name: str) -> str:
        for ch in '/\\:*?"<>|':
            name = name.replace(ch, "_")
        return name.strip() or "Unknown"