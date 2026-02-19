"""
ytmedia
=======
Download MP4 (video + audio) and MP3 from YouTube URLs
at the highest possible quality using yt-dlp.
"""

from .core import download_mp4, download_mp3, download_playlist_mp4, get_info
from .env import check_ffmpeg, get_missing_dependencies, has_ffmpeg, has_js_runtime
from .errors import YtMediaError, DependencyMissing, DownloadFailed, UnsupportedFormat, MergeError
from .models import DownloadResult, PlaylistResult

__all__ = [
    # download
    "download_mp4",
    "download_mp3",
    "download_playlist_mp4",
    "get_info",
    # env checks (pure, no side effects)
    "check_ffmpeg",
    "has_ffmpeg",
    "has_js_runtime",
    "get_missing_dependencies",
    # exceptions
    "YtMediaError",
    "DependencyMissing",
    "DownloadFailed",
    "UnsupportedFormat",
    "MergeError",
    # models
    "DownloadResult",
    "PlaylistResult",
]

__version__ = "0.4.0"