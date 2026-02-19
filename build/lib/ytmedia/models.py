"""
models.py
=========
Return value types for ytmedia public API.
Functions return structured objects instead of printing and returning raw strings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DownloadResult:
    """
    Result of a single video or audio download.

    Attributes
    ----------
    path        : absolute path to the downloaded file
    title       : video title
    url         : source URL
    resolution  : video resolution e.g. '1080p' (None for audio-only)
    video_codec : video codec e.g. 'h264', 'vp9' (None for audio-only)
    audio_codec : audio codec e.g. 'aac', 'mp3' (None for video-only)
    filesize    : file size in bytes (may be None if unavailable)
    """
    path:        Path
    title:       str
    url:         str
    resolution:  Optional[str]       = None
    video_codec: Optional[str]       = None
    audio_codec: Optional[str]       = None
    filesize:    Optional[int]       = None

    def __str__(self) -> str:
        parts = [f"'{self.title}'", f"-> {self.path}"]
        if self.resolution:
            parts.append(f"[{self.resolution}]")
        if self.audio_codec:
            parts.append(f"audio={self.audio_codec}")
        return " ".join(parts)


@dataclass
class PlaylistResult:
    """
    Result of a playlist download.

    Attributes
    ----------
    downloads   : list of successfully downloaded DownloadResult objects
    failed      : list of URLs that failed (skipped due to ignoreerrors)
    total       : total number of entries attempted
    """
    downloads:  list[DownloadResult] = field(default_factory=list)
    failed:     list[str]            = field(default_factory=list)
    total:      int                  = 0

    @property
    def success_count(self) -> int:
        return len(self.downloads)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    def __str__(self) -> str:
        return f"PlaylistResult({self.success_count}/{self.total} downloaded, {self.failed_count} failed)"