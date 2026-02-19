"""
errors.py
=========
Stable exception hierarchy for ytmedia.
All yt-dlp exceptions are caught internally and re-raised as these,
so your API surface stays stable even if yt-dlp changes.
"""


class YtMediaError(Exception):
    """Base exception for all ytmedia errors."""


class DependencyMissing(YtMediaError):
    """
    A required external dependency (ffmpeg, Node.js) is not available.

    Attributes
    ----------
    dependency : name of the missing dependency e.g. 'ffmpeg', 'nodejs'
    """
    def __init__(self, dependency: str, message: str = "") -> None:
        self.dependency = dependency
        super().__init__(message or f"Missing dependency: {dependency}")


class DownloadFailed(YtMediaError):
    """
    Download or extraction failed.

    Attributes
    ----------
    url : the URL that failed
    """
    def __init__(self, url: str, reason: str = "") -> None:
        self.url = url
        super().__init__(f"Download failed for {url!r}: {reason}" if reason else f"Download failed for {url!r}")


class UnsupportedFormat(YtMediaError):
    """Requested format or resolution is not available for this video."""


class MergeError(YtMediaError):
    """ffmpeg merge step failed."""