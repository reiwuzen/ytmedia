"""
cli.py
======
Command-line interface for ytmedia.
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .core import download_mp4, download_mp3, download_playlist_mp4, get_info
from .env import find_ffmpeg, find_node, find_deno, get_missing_dependencies, get_js_runtimes
from .errors import YtMediaError, DependencyMissing


# ---------------------------------------------------------------------------
# doctor — show environment status
# ---------------------------------------------------------------------------

def cmd_doctor() -> None:
    """Print environment health check."""
    print("=== ytmedia doctor ===\n")

    # ffmpeg
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        print(f"[ffmpeg]     OK  — {ffmpeg}")
    else:
        print("[ffmpeg]     MISSING")
        print("             Run: ytmedia install-deps")
        print("             Or install system-wide: winget install ffmpeg / brew install ffmpeg")

    # yt-dlp-ejs
    try:
        import yt_dlp_ejs  # noqa: F401
        print("[yt-dlp-ejs] OK")
    except ImportError:
        print("[yt-dlp-ejs] MISSING — Run: ytmedia install-deps")

    # JS runtimes
    node = find_node()
    deno = find_deno()
    if node:
        print(f"[node]       OK  — {node}")
    else:
        print("[node]       MISSING — install from https://nodejs.org")
    if deno:
        print(f"[deno]       OK  — {deno}")

    missing = get_missing_dependencies()
    print()
    if not missing:
        print("All dependencies satisfied.")
    else:
        print(f"Missing: {', '.join(missing)}")
        print("Run `ytmedia install-deps` to fix automatically.")

    print("\n=== done ===")


# ---------------------------------------------------------------------------
# install-deps — CLI-only environment mutation
# ---------------------------------------------------------------------------

def cmd_install_deps() -> None:
    """
    Interactive dependency installer.
    This is the ONLY place pip installs and input() are allowed.
    """
    print("=== ytmedia install-deps ===\n")

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
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        print(f"[ffmpeg]     already found at {ffmpeg}")
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
                # clear lru_cache so find_ffmpeg() re-checks
                from . import env
                env.find_ffmpeg.cache_clear()
                refreshed = find_ffmpeg()
                if refreshed:
                    print(f"[ffmpeg]     installed at {refreshed}")
                    print("[ffmpeg]     note: scoped to this Python environment.")
                else:
                    print("[ffmpeg]     installed — restart your terminal to activate.")
            except Exception as e:
                print(f"[ffmpeg]     failed: {e}")
                _print_ffmpeg_hint()

        elif choice == "2":
            print()
            _print_ffmpeg_hint()

        else:
            print("[ffmpeg]     skipped.")

    # 3 — JS runtime (user must install manually)
    runtimes = get_js_runtimes()
    if runtimes:
        for name, path in runtimes.items():
            print(f"[{name}]{'':>8} found at {path}")
    else:
        print(
            "[node]       not found — install from https://nodejs.org\n"
            "             Required for best YouTube format availability."
        )

    print("\n=== done ===")


def _print_ffmpeg_hint() -> None:
    system = platform.system()
    print("[ffmpeg] System-wide install:")
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
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ytmedia",
        description="Download MP4 and MP3 from YouTube at the highest possible quality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  ytmedia doctor                                       # check dependencies
  ytmedia install-deps                                 # install missing dependencies
  ytmedia mp4 https://youtu.be/xxxx                   # best quality MP4
  ytmedia mp4 https://youtu.be/xxxx -r 1080 -o ./vid  # 1080p
  ytmedia mp4 https://youtu.be/xxxx --no-audio        # video only
  ytmedia mp3 https://youtu.be/xxxx                   # 320kbps MP3
  ytmedia mp3 https://youtu.be/xxxx -q 192            # 192kbps MP3
  ytmedia playlist https://youtube.com/playlist?list=xxxx
  ytmedia info https://youtu.be/xxxx
  ytmedia mp4 https://youtu.be/xxxx --debug           # full yt-dlp logs
        """,
    )

    parser.add_argument(
        "mode",
        choices=["doctor", "install-deps", "mp4", "mp3", "playlist", "info"],
        help="Command to run",
    )
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument("-o", "--output",     default="downloads", metavar="DIR")
    parser.add_argument("-r", "--resolution", default="best",      metavar="HEIGHT")
    parser.add_argument("-q", "--quality",    default="320",       metavar="KBPS")
    parser.add_argument("--no-audio", action="store_true", default=False)
    parser.add_argument("--debug",    action="store_true", default=False)

    args = parser.parse_args()

    if args.mode not in ("doctor", "install-deps") and not args.url:
        parser.error(f"url is required for '{args.mode}' mode.")

    try:
        if args.mode == "doctor":
            cmd_doctor()

        elif args.mode == "install-deps":
            cmd_install_deps()

        elif args.mode == "mp4":
            result = download_mp4(
                args.url,
                output_dir=args.output,
                resolution=args.resolution,
                audio=not args.no_audio,
                debug=args.debug,
            )
            print(f"\nSaved: {result.path}")
            if result.resolution:
                print(f"       {result.resolution}  video={result.video_codec}  audio={result.audio_codec}")

        elif args.mode == "mp3":
            result = download_mp3(
                args.url,
                output_dir=args.output,
                quality=args.quality,
                debug=args.debug,
            )
            print(f"\nSaved: {result.path}")

        elif args.mode == "playlist":
            result = download_playlist_mp4(
                args.url,
                output_dir=args.output,
                resolution=args.resolution,
                debug=args.debug,
            )
            print(f"\n{result}")

        elif args.mode == "info":
            info = get_info(args.url)
            print(f"\nTitle    : {info.get('title')}")
            print(f"Uploader : {info.get('uploader')}")
            print(f"Duration : {info.get('duration_string', info.get('duration'))}s")
            if info.get("view_count"):
                print(f"Views    : {info.get('view_count'):,}")
            print(f"URL      : {info.get('webpage_url')}")
            print(f"\nAvailable formats: {len(info.get('formats', []))}")

    except DependencyMissing as e:
        print(f"\nMissing dependency: {e.dependency}")
        print(f"{e}")
        print("\nRun: ytmedia install-deps")
        sys.exit(1)
    except YtMediaError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()