"""
ytmedia
=======
Download MP4 (video + audio) and MP3 from YouTube URLs
at the highest possible quality using yt-dlp.
"""

from .core import (
    download_mp4,
    download_mp3,
    download_playlist_mp4,
    get_info,
    init
)

__all__ = [
    "download_mp4",
    "download_mp3",
    "download_playlist_mp4",
    "get_info",
    "init",
]

__version__ = "0.2.0"