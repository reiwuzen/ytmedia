"""
core.py
=======
Core download functions for ytmedia.
Download MP4 (video+audio) and MP3 from YouTube URLs
using yt-dlp at the highest possible quality.
"""

import itertools
import os
import platform
import shutil
import subprocess
import sys
import threading
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


def _base_opts(output_dir: str, debug: bool = False) -> dict[str, Any]:
    """Shared yt-dlp options."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    opts: dict[str, Any] = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        # debug=False: suppress all yt-dlp internal logs, show only our clean output
        # debug=True:  show full yt-dlp logs for troubleshooting
        "quiet": not debug,
        "no_warnings": not debug,
        "verbose": debug,
    }
    runtimes = _get_js_runtimes()
    if runtimes:
        opts["js_runtimes"] = runtimes
    return opts


def _clean_progress_hook(d: dict[str, Any]) -> None:
    """
    Clean progress hook for non-debug mode.
    Shows a single updating line per stream: [video] or [audio] + % + speed.
    """
    if d.get("status") != "downloading":
        return

    # label stream type based on fragment or format info
    filename = d.get("filename", "")
    if ".f" in os.path.basename(filename):
        ext = os.path.splitext(filename)[-1].lstrip(".")
        label = "[audio]" if ext in ("webm", "m4a", "opus") else "[video]"
    else:
        label = "[download]"

    percent   = d.get("_percent_str", "?%").strip()
    speed     = d.get("_speed_str", "?").strip()
    size      = d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str") or "?"
    eta       = d.get("_eta_str", "?").strip()

    print(f"\r{label:10} {percent:>6} of {size:>10} at {speed:>12}  ETA {eta}   ",
          end="", flush=True)

    if d.get("status") == "finished":
        print()  # newline after stream finishes


def _merge_hooks() -> dict[str, Any]:
    """
    Postprocessor hooks that show an animated spinner during the ffmpeg merge step.
    A real progress % is not possible since yt-dlp does not expose ffmpeg's progress
    events -- so a spinner is used to show activity honestly.
    """
    spinner_chars = itertools.cycle(["\u280b", "\u2819", "\u2839", "\u2838",
                                     "\u283c", "\u2834", "\u2826", "\u2827",
                                     "\u2807", "\u280f"])
    stop_event = threading.Event()

    def _spin() -> None:
        while not stop_event.is_set():
            print(f"\r[Merger]   {next(spinner_chars)} merging video + audio ...",
                  end="", flush=True)
            stop_event.wait(0.1)
        print("\r[Merger]   done.                               ")

    def hook(d: dict[str, Any]) -> None:
        status = d.get("status", "")
        name   = d.get("postprocessor", "")
        if "Merger" not in name:
            return
        if status == "started":
            stop_event.clear()
            threading.Thread(target=_spin, daemon=True).start()
        elif status == "finished":
            stop_event.set()

    return {"progress_hooks": [], "postprocessor_hooks": [hook]}


# ---------------------------------------------------------------------------
# init — set up dependencies
# ---------------------------------------------------------------------------

def init() -> None:
    """
    Set up all required dependencies for ytmedia:
      - yt-dlp-ejs  : JS challenge solver scripts for full YouTube format support
      - static-ffmpeg : activates a bundled ffmpeg binary scoped to this Python
                        environment (NOT a system-wide install). For a permanent
                        system install use: winget install ffmpeg  /  brew install ffmpeg

    Safe to run multiple times -- skips anything already in place.
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

    # 2 — ffmpeg
    if _has_ffmpeg():
        print(f"[ffmpeg]     already found at {shutil.which('ffmpeg')}")
    else:
        print("[ffmpeg]     not found on PATH.")
        print()
        print("  How would you like to install ffmpeg?")
        print("  [1] Download for this Python environment only (via static-ffmpeg, easiest)")
        print("  [2] Show system-wide install instructions (winget / brew / apt)")
        print("  [s] Skip")
        print()

        choice = input("  Enter choice [1/2/s]: ").strip().lower()

        if choice == "1":
            print()
            print("[ffmpeg]     downloading bundled binary via static-ffmpeg ...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "static-ffmpeg"],
                    stdout=subprocess.DEVNULL,
                )
                import static_ffmpeg
                static_ffmpeg.add_paths()
                if _has_ffmpeg():
                    print(f"[ffmpeg]     installed at {shutil.which('ffmpeg')}")
                    print("[ffmpeg]     note: this is scoped to your Python environment,")
                    print("             not a system-wide install.")
                else:
                    print("[ffmpeg]     installed but PATH not updated yet -- restart your terminal.")
            except Exception as e:
                print(f"[ffmpeg]     failed: {e}")
                _print_ffmpeg_install_hint()

        elif choice == "2":
            print()
            _print_ffmpeg_install_hint()

        else:
            print("[ffmpeg]     skipped. Run ytmedia init again when ready.")

    # 3 — JS runtime check (Node.js / Deno -- must be installed by user)
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
    print("[ffmpeg] Please install ffmpeg manually:")
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
    debug: bool = False,
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
    debug          : If True, show full yt-dlp logs. Default False (clean output).

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

    opts = _base_opts(output_dir, debug=debug)
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

    if not debug:
        opts["progress_hooks"] = [_clean_progress_hook]
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
    debug: bool = False,
) -> str:
    """
    Download a YouTube video and extract audio as MP3.

    Parameters
    ----------
    url        : YouTube video URL.
    output_dir : Folder to save the file (created if it doesn't exist).
    quality    : Audio bitrate in kbps -- '320', '192', '128', etc. (default '320').
    debug      : If True, show full yt-dlp logs. Default False (clean output).

    Returns
    -------
    Path to the downloaded MP3 file.
    """
    opts = _base_opts(output_dir, debug=debug)
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

    if not debug:
        opts["progress_hooks"] = [_clean_progress_hook]

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
    debug: bool = False,
) -> list[str]:
    """
    Download all videos in a YouTube playlist as MP4 with audio.

    Parameters
    ----------
    playlist_url : YouTube playlist URL.
    output_dir   : Folder to save files.
    resolution   : 'best' or a specific height like '1080'.
    debug        : If True, show full yt-dlp logs. Default False (clean output).

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

    opts = _base_opts(output_dir, debug=debug)
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

    if not debug:
        opts["progress_hooks"] = [_clean_progress_hook]
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