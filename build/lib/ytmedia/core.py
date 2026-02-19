"""
core.py
=======
Pure download functions for ytmedia.

Rules:
  - No print() calls
  - No input() calls
  - No pip installs
  - No sys.exit()
  - Returns structured objects (DownloadResult / PlaylistResult)
  - Catches yt-dlp exceptions and re-raises as ytmedia exceptions
  - Safe to use inside FastAPI, GUIs, async apps, automation
"""

import itertools
import os
import threading
from pathlib import Path
from typing import Any, Optional

import yt_dlp
import yt_dlp.utils

from .env import get_js_runtimes, find_ffmpeg, has_ffmpeg
from .errors import DependencyMissing, DownloadFailed, MergeError
from .models import DownloadResult, PlaylistResult


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ydl_opts(output_dir: str, debug: bool = False) -> dict[str, Any]:
    """Base yt-dlp options — quiet by default, verbose in debug mode."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    opts: dict[str, Any] = {
        "outtmpl":     os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet":       not debug,
        "no_warnings": not debug,
        "verbose":     debug,
    }
    runtimes = get_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = {
            name: {"executable": path} for name, path in runtimes.items()
        }
    return opts


def _spinner_hooks() -> dict[str, Any]:
    """
    Postprocessor hooks that spin a braille animation during ffmpeg merge.
    Only used in non-debug mode. Returns yt-dlp hook dicts.
    """
    chars = itertools.cycle(["\u280b","\u2819","\u2839","\u2838",
                             "\u283c","\u2834","\u2826","\u2827",
                             "\u2807","\u280f"])
    stop = threading.Event()

    def _spin() -> None:
        while not stop.is_set():
            print(f"\r[Merger] {next(chars)} merging ...", end="", flush=True)
            stop.wait(0.1)
        print("\r[Merger] done.              ")

    def hook(d: dict[str, Any]) -> None:
        name   = d.get("postprocessor", "")
        status = d.get("status", "")
        if "Merger" not in name:
            return
        if status == "started":
            stop.clear()
            threading.Thread(target=_spin, daemon=True).start()
        elif status == "finished":
            stop.set()

    return {"postprocessor_hooks": [hook]}


def _progress_hook(d: dict[str, Any]) -> None:
    """Clean single-line progress display for non-debug mode."""
    if d.get("status") != "downloading":
        return
    filename = d.get("filename", "")
    ext      = os.path.splitext(filename)[-1].lstrip(".")
    label    = "[audio]" if ext in ("webm", "m4a", "opus") else "[video]"
    pct      = d.get("_percent_str", "?%").strip()
    speed    = d.get("_speed_str",   "?").strip()
    size     = d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str") or "?"
    eta      = d.get("_eta_str",     "?").strip()
    print(f"\r{label:10} {pct:>6} of {size:>10} at {speed:>12}  ETA {eta}   ",
          end="", flush=True)
    if d.get("status") == "finished":
        print()


def _resolution_str(info: dict[str, Any]) -> Optional[str]:
    """
    Return a resolution string like '1080p'.
    Uses the smaller of width/height as the resolution value since
    yt-dlp may return portrait-oriented dimensions (height > width).
    """
    w = info.get("width")
    h = info.get("height")
    if w and h:
        return f"{min(w, h)}p"
    if h:
        return f"{h}p"
    return None


def _build_result(info: dict[str, Any], output_dir: str, url: str) -> DownloadResult:
    """Build a DownloadResult from a yt-dlp info dict."""
    filename = Path(output_dir) / f"{info.get('title', 'download')}.mp4"
    # yt-dlp puts the final merged file at this path
    base  = Path(output_dir) / Path(info.get("_filename", "")).stem
    final = base.with_suffix(".mp4")
    if final.exists():
        filename = final

    return DownloadResult(
        path        = filename.resolve(),
        title       = info.get("title", ""),
        url         = url,
        resolution  = _resolution_str(info),
        video_codec = info.get("vcodec"),
        audio_codec = info.get("acodec"),
        filesize    = info.get("filesize") or info.get("filesize_approx"),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_mp4(
    url: str,
    output_dir: str = "downloads",
    resolution: str = "best",
    audio: bool = True,
    allow_playlist: bool = False,
    debug: bool = False,
) -> DownloadResult:
    """
    Download a YouTube video as MP4.

    Parameters
    ----------
    url            : YouTube video URL.
    output_dir     : Folder to save the file (created if needed).
    resolution     : 'best' or a height string like '1080', '720'.
    audio          : Include audio track (default True).
    allow_playlist : If True, download whole playlist. Default False.
    debug          : If True, show full yt-dlp logs.

    Returns
    -------
    DownloadResult

    Raises
    ------
    DependencyMissing   : ffmpeg not available (required for merging streams)
    DownloadFailed      : yt-dlp could not extract or download the video
    MergeError          : ffmpeg merge step failed
    """
    ffmpeg = find_ffmpeg()

    if audio and not ffmpeg:
        raise DependencyMissing(
            "ffmpeg",
            "ffmpeg is required for audio+video merging. "
            "Run `ytmedia doctor` or install ffmpeg manually."
        )

    if ffmpeg:
        if audio:
            fmt = ("bestvideo+bestaudio/best" if resolution == "best"
                   else f"bestvideo[height<={resolution}]+bestaudio"
                        f"/bestvideo[height<={resolution}]+bestaudio[ext=m4a]"
                        f"/best[height<={resolution}]")
        else:
            fmt = ("bestvideo/best" if resolution == "best"
                   else f"bestvideo[height<={resolution}]/bestvideo")
    else:
        fmt = ("best[ext=mp4]/best" if resolution == "best"
               else f"best[height<={resolution}][ext=mp4]/best[height<={resolution}]/best")

    opts = _ydl_opts(output_dir, debug=debug)
    opts.update({
        "format":               fmt,
        "noplaylist":           not allow_playlist,
        "merge_output_format":  "mp4",
    })

    if ffmpeg and audio:
        opts["postprocessor_args"] = {
            "merger": ["-c:v", "copy", "-c:a", "aac"]
        }

    if not debug:
        opts["progress_hooks"] = [_progress_hook]
        opts.update(_spinner_hooks())

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadFailed(url, str(e)) from e
    except yt_dlp.utils.PostProcessingError as e:
        raise MergeError(str(e)) from e

    return _build_result(info, output_dir, url)


def download_mp3(
    url: str,
    output_dir: str = "downloads",
    quality: str = "320",
    debug: bool = False,
) -> DownloadResult:
    """
    Download and extract audio as MP3.

    Parameters
    ----------
    url        : YouTube video URL.
    output_dir : Folder to save the file (created if needed).
    quality    : Bitrate in kbps — '320', '192', '128' (default '320').
    debug      : If True, show full yt-dlp logs.

    Returns
    -------
    DownloadResult

    Raises
    ------
    DependencyMissing : ffmpeg not available (required for MP3 conversion)
    DownloadFailed    : yt-dlp could not extract or download
    """
    if not find_ffmpeg():
        raise DependencyMissing(
            "ffmpeg",
            "ffmpeg is required for MP3 conversion. "
            "Run `ytmedia doctor` or install ffmpeg manually."
        )

    opts = _ydl_opts(output_dir, debug=debug)
    opts.update({
        "format":      "bestaudio/best",
        "noplaylist":  True,
        "postprocessors": [{
            "key":              "FFmpegExtractAudio",
            "preferredcodec":   "mp3",
            "preferredquality": quality,
        }],
    })

    if not debug:
        opts["progress_hooks"] = [_progress_hook]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadFailed(url, str(e)) from e

    title    = info.get("title", "download")
    mp3_path = (Path(output_dir) / title).with_suffix(".mp3").resolve()

    return DownloadResult(
        path        = mp3_path,
        title       = title,
        url         = url,
        audio_codec = "mp3",
        filesize    = info.get("filesize") or info.get("filesize_approx"),
    )


def download_playlist_mp4(
    playlist_url: str,
    output_dir: str = "downloads",
    resolution: str = "best",
    debug: bool = False,
) -> PlaylistResult:
    """
    Download all videos in a YouTube playlist as MP4.

    Parameters
    ----------
    playlist_url : YouTube playlist URL.
    output_dir   : Folder to save files.
    resolution   : 'best' or a height string like '1080'.
    debug        : If True, show full yt-dlp logs.

    Returns
    -------
    PlaylistResult

    Raises
    ------
    DependencyMissing : ffmpeg not available
    DownloadFailed    : entire playlist extraction failed
    """
    if not find_ffmpeg():
        raise DependencyMissing(
            "ffmpeg",
            "ffmpeg is required for audio+video merging. "
            "Run `ytmedia doctor` or install ffmpeg manually."
        )

    fmt = ("bestvideo+bestaudio/best" if resolution == "best"
           else f"bestvideo[height<={resolution}]+bestaudio"
                f"/bestvideo[height<={resolution}]+bestaudio[ext=m4a]"
                f"/best[height<={resolution}]")

    opts = _ydl_opts(output_dir, debug=debug)
    opts.update({
        "format":              fmt,
        "merge_output_format": "mp4",
        "ignoreerrors":        True,   # skip unavailable videos, don't abort
        "postprocessor_args":  {"merger": ["-c:v", "copy", "-c:a", "aac"]},
    })

    if not debug:
        opts["progress_hooks"] = [_progress_hook]
        opts.update(_spinner_hooks())

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(playlist_url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadFailed(playlist_url, str(e)) from e

    result = PlaylistResult(total=len(info.get("entries", [])))

    for entry in info.get("entries", []):
        if entry:
            result.downloads.append(_build_result(entry, output_dir, entry.get("webpage_url", "")))
        else:
            result.failed.append("unknown")

    return result


def get_info(url: str) -> dict[str, Any]:
    """
    Fetch metadata for a YouTube URL without downloading.

    Returns
    -------
    dict with keys: title, uploader, duration, formats, thumbnails, etc.

    Raises
    ------
    DownloadFailed : could not extract info
    """
    opts: dict[str, Any] = {"quiet": True, "no_warnings": True}
    runtimes = get_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = {
            name: {"executable": path} for name, path in runtimes.items()
        }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            return ydl.extract_info(url, download=False)  # type: ignore[return-value]
    except yt_dlp.utils.DownloadError as e:
        raise DownloadFailed(url, str(e)) from e