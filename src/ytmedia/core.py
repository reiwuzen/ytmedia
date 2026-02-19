"""
core.py
=======
Core download functions for ytmedia.
Download MP4 (video+audio) and MP3 from YouTube URLs
using yt-dlp at the highest possible quality.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yt_dlp


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_ffmpeg() -> bool:
    """Check if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def _get_js_runtimes() -> dict[str, Any]:
    """
    Build the js_runtimes dict for the yt-dlp Python API.
    Checks for node first, then deno as a fallback.
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


def _merge_hooks() -> dict[str, Any]:
    """
    Progress hooks that show a % progress bar for the ffmpeg merge step.
    yt-dlp fires 'post_process' hooks with status 'started' and 'finished'.
    We fake a simple progress line since ffmpeg merge duration is unknown.
    """
    def hook(d: dict[str, Any]) -> None:
        if d.get("postprocessor") != "MoveFiles":
            status = d.get("status", "")
            name   = d.get("postprocessor", "")
            if status == "started" and "Merger" in name:
                print("\r[Merger]   0% — merging video + audio ...", end="", flush=True)
            elif status == "finished" and "Merger" in name:
                print("\r[Merger] 100% — done.                    ")
    return {"progress_hooks": [], "postprocessor_hooks": [hook]}


# ---------------------------------------------------------------------------
# init — download all required binaries
# ---------------------------------------------------------------------------

def init() -> None:
    """
    Download and configure all required external dependencies:
      - ffmpeg  (via static-ffmpeg, cross-platform prebuilt binary)
      - yt-dlp-ejs  (JS challenge solver scripts for full YouTube support)

    Safe to run multiple times — skips anything already installed.
    """
    print("=== ytmedia init ===\n")

    # 1 — yt-dlp-ejs
    try:
        import yt_dlp_ejs  # noqa: F401
        print("[yt-dlp-ejs] already installed.")
    except ImportError:
        print("[yt-dlp-ejs] installing ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "yt-dlp-ejs"],
            stdout=subprocess.DEVNULL,
        )
        print("[yt-dlp-ejs] installed.")

    # 2 — ffmpeg via static-ffmpeg (prebuilt binary, no system install needed)
    if _has_ffmpeg():
        print(f"[ffmpeg]     already found at {shutil.which('ffmpeg')}")
    else:
        print("[ffmpeg]     not found on PATH — installing via static-ffmpeg ...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "static-ffmpeg"],
                stdout=subprocess.DEVNULL,
            )
            import static_ffmpeg
            static_ffmpeg.add_paths()  # adds ffmpeg binary to PATH for this session
            if _has_ffmpeg():
                print(f"[ffmpeg]     installed at {shutil.which('ffmpeg')}")
            else:
                print("[ffmpeg]     installed but not yet on PATH — restart your terminal.")
        except Exception as e:
            print(f"[ffmpeg]     failed to auto-install: {e}")
            _print_ffmpeg_install_hint()

    # 3 — JS runtime check (Node.js / Deno — must be installed by user)
    runtimes = _get_js_runtimes()
    if runtimes:
        for name, info in runtimes.items():
            print(f"[JS runtime] {name} found at {info['executable']}")
    else:
        print(
            "[JS runtime] WARNING: no Node.js or Deno found.\n"
            "             yt-dlp needs a JS runtime for full YouTube format support.\n"
            "             Install Node.js from https://nodejs.org (recommended)\n"
            "             or Deno from https://deno.com"
        )

    print("\n=== init complete ===")


def _print_ffmpeg_install_hint() -> None:
    """Print platform-specific ffmpeg install instructions as a fallback."""
    system = platform.system()
    print("\n[ffmpeg] Please install ffmpeg manually:")
    if system == "Windows":
        print("         winget install ffmpeg")
        print("         or: https://www.gyan.dev/ffmpeg/builds/")
    elif system == "Darwin":
        print("         brew install ffmpeg")
    else:
        print("         sudo apt install ffmpeg   # Debian/Ubuntu")
        print("         sudo dnf install ffmpeg   # Fedora")
        print("         sudo pacman -S ffmpeg     # Arch")


# ---------------------------------------------------------------------------
# Public download functions
# ---------------------------------------------------------------------------

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
            "Run ytmedia.init() or install ffmpeg for full 1080p/4K quality."
        )

    if ffmpeg:
        if audio:
            if resolution == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = (
                    f"bestvideo[height<={resolution}]+bestaudio"
                    f"/bestvideo[height<={resolution}]+bestaudio[ext=m4a]"
                    f"/best[height<={resolution}]"
                )
        else:
            if resolution == "best":
                fmt = "bestvideo/best"
            else:
                fmt = f"bestvideo[height<={resolution}]/bestvideo"
    else:
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

    # Show merge progress
    opts.update(_merge_hooks())

    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
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
    opts.update(_merge_hooks())

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