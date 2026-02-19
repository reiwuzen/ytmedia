"""
core.py
=======
Core download functions for ytmedia.
Download MP4 (video+audio) and MP3 from YouTube URLs
using yt-dlp at the highest possible quality.
"""

import os
import shutil
from pathlib import Path
from typing import Any

import yt_dlp


def _has_ffmpeg() -> bool:
    """Check if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def _get_js_runtimes() -> dict[str, Any]:
    """
    Build the js_runtimes dict for the yt-dlp Python API.
    yt-dlp requires this format: {'node': {'executable': '/path/to/node'}}

    Also checks for deno as a fallback.
    Returns an empty dict if nothing is found (yt-dlp will warn but still work).
    """
    runtimes: dict[str, Any] = {}

    node = shutil.which("node") or shutil.which("node.exe")
    if node:
        runtimes["node"] = {"executable": node}

    deno = shutil.which("deno")
    if deno:
        runtimes["deno"] = {"executable": deno}

    return runtimes


def _base_opts(output_dir: str) -> dict[str, Any]:
    """Shared yt-dlp options."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    opts: dict[str, Any] = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": False,
    }

    runtimes = _get_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = runtimes

    return opts


def download_mp4(
    url: str,
    output_dir: str = "downloads",
    resolution: str = "best",
    audio: bool = True,
    allow_playlist: bool = False,
) -> str:
    """
    Download a YouTube video as MP4 at the highest available resolution.

    Parameters
    ----------
    url            : YouTube video URL (playlist params in URL are ignored by default).
    output_dir     : Folder to save the file (created if it doesn't exist).
    resolution     : 'best' (default) or a specific height like '1080', '720', etc.
    audio          : Include audio track in the MP4 (default: True).
                     Set to False to download video-only (smaller file size).
    allow_playlist : If True, download the whole playlist. Default False (single video).

    Returns
    -------
    Path to the downloaded file.
    """
    ffmpeg = _has_ffmpeg()
    if not ffmpeg:
        print(
            "Warning: ffmpeg not found -- falling back to best single-stream MP4 "
            "(may be limited to 720p or lower).\n"
            "Install ffmpeg for full 1080p/4K quality."
        )

    if ffmpeg:
        if audio:
            # Download best video + best audio as separate streams, ffmpeg merges into mp4
            if resolution == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = (
                    f"bestvideo[height<={resolution}]+bestaudio"
                    f"/bestvideo[height<={resolution}]+bestaudio[ext=m4a]"
                    f"/best[height<={resolution}]"
                )
        else:
            # Video only -- no audio stream
            if resolution == "best":
                fmt = "bestvideo/best"
            else:
                fmt = f"bestvideo[height<={resolution}]/bestvideo"
    else:
        # No ffmpeg: request a pre-muxed single-file format only
        if not audio:
            print("Warning: audio=False ignored -- ffmpeg is required to strip the audio track.")
        if resolution == "best":
            fmt = "best[ext=mp4]/best"
        else:
            fmt = f"best[height<={resolution}][ext=mp4]/best[height<={resolution}]/best"

    opts = _base_opts(output_dir)
    opts.update(
        {
            "format": fmt,
            "noplaylist": not allow_playlist,
            "merge_output_format": "mp4",
        }
    )

    if ffmpeg and audio:
        # Force AAC audio during the ffmpeg merge step.
        # Without this, yt-dlp may embed Opus (webm audio) inside the MP4 container,
        # which Windows Media Player, QuickTime, and many phones will reject.
        #   -c:v copy  -> keep original video codec (no re-encode, fast)
        #   -c:a aac   -> convert audio to AAC (universally supported in MP4)
        opts["postprocessor_args"] = {
            "merger": ["-c:v", "copy", "-c:a", "aac"]
        }

    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # After merging, yt-dlp writes to .mp4 due to merge_output_format
        base = os.path.splitext(filename)[0]
        final = base + ".mp4"
        if os.path.exists(final):
            filename = final
        print(f"\nMP4 saved: {filename}")
        return filename


def download_mp3(
    url: str,
    output_dir: str = "downloads",
    quality: str = "320",
) -> str:
    """
    Download a YouTube video and extract audio as MP3.

    Parameters
    ----------
    url        : YouTube video URL.
    output_dir : Folder to save the file (created if it doesn't exist).
    quality    : Audio bitrate in kbps -- '320', '192', '128', etc. (default '320').

    Returns
    -------
    Path to the downloaded MP3 file.
    """
    opts = _base_opts(output_dir)
    opts.update(
        {
            "format": "bestaudio/best",
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
        }
    )

    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        mp3_filename = os.path.splitext(filename)[0] + ".mp3"
        print(f"\nMP3 saved: {mp3_filename}")
        return mp3_filename


def download_playlist_mp4(
    playlist_url: str,
    output_dir: str = "downloads",
    resolution: str = "best",
) -> list[str]:
    """
    Download all videos in a YouTube playlist as MP4 with audio.

    Parameters
    ----------
    playlist_url : YouTube playlist URL.
    output_dir   : Folder to save files.
    resolution   : 'best' or a specific height like '1080'.

    Returns
    -------
    List of downloaded file paths.
    """
    if resolution == "best":
        fmt = "bestvideo+bestaudio/best"
    else:
        fmt = (
            f"bestvideo[height<={resolution}]+bestaudio"
            f"/bestvideo[height<={resolution}]+bestaudio[ext=m4a]"
            f"/best[height<={resolution}]"
        )

    opts = _base_opts(output_dir)
    opts.update(
        {
            "format": fmt,
            "merge_output_format": "mp4",
            "ignoreerrors": True,
            "postprocessor_args": {
                "merger": ["-c:v", "copy", "-c:a", "aac"]
            },
        }
    )

    downloaded = []
    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(playlist_url, download=True)
        if "entries" in info:
            for entry in info["entries"]:
                if entry:
                    f = ydl.prepare_filename(entry)
                    if not os.path.exists(f):
                        f = os.path.splitext(f)[0] + ".mp4"
                    downloaded.append(f)
    print(f"\nPlaylist download complete. {len(downloaded)} file(s) saved.")
    return downloaded


def get_info(url: str) -> dict[str, Any]:
    """
    Fetch metadata for a YouTube URL without downloading.

    Returns a dict with keys like: title, uploader, duration,
    formats, thumbnails, etc.
    """
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
    }
    runtimes = _get_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = runtimes

    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=False)
    return info  # type: ignore[return-value]