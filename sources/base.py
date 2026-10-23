from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Candidate:
    """A possible audio file for a track. Returned by source.search()."""
    source_name: str
    locator: str              # URL for network sources; file path for local
    confidence: float         # 0.0 .. 1.0 — higher is better match
    title: str
    artist: str
    duration_seconds: Optional[float] = None
    extra: dict = field(default_factory=dict)


@dataclass
class AcquiredFile:
    """Result of a successful source.acquire()."""
    path: Path
    sha256: str
    title: str
    artist: str
    album: Optional[str] = None
    track_number: Optional[int] = None
    duration_seconds: Optional[float] = None


class AudioSource(ABC):
    name: str = "abstract"

    @abstractmethod
    def search(
        self,
        title: str,
        artist: str,
        duration_seconds: Optional[float] = None,
    ) -> list[Candidate]:
        """Find candidates for this track. Return an empty list if nothing matches."""

    @abstractmethod
    def acquire(self, candidate: Candidate, dest_dir: Path) -> Optional[AcquiredFile]:
        """Fetch the candidate's file into dest_dir.

        Return None on failure (the worker will try the next candidate or source).
        On success, the file must be at the returned path with a valid hash.
        """