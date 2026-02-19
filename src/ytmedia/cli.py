"""
cli.py
======
Command-line interface for ytmedia.

Usage examples:
    ytmedia mp4 https://youtu.be/xxxx
    ytmedia mp3 https://youtu.be/xxxx
    ytmedia mp4 https://youtu.be/xxxx -o ./videos -r 1080
    ytmedia mp3 https://youtu.be/xxxx -o ./music -q 192
    ytmedia playlist https://youtube.com/playlist?list=xxxx
    ytmedia info https://youtu.be/xxxx
"""

import argparse
import json
import sys

from ytmedia import download_mp4, download_mp3, download_playlist_mp4, get_info


def main():
    parser = argparse.ArgumentParser(
        prog="ytmedia",
        description="Download MP4 and MP3 from YouTube at the highest possible quality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  ytmedia mp4 https://youtu.be/xxxx
  ytmedia mp4 https://youtu.be/xxxx -r 1080 -o ./videos
  ytmedia mp3 https://youtu.be/xxxx -q 192
  ytmedia playlist https://youtube.com/playlist?list=xxxx
  ytmedia info https://youtu.be/xxxx
        """,
    )

    parser.add_argument(
        "mode",
        choices=["mp4", "mp3", "playlist", "info"],
        help="Download mode: mp4, mp3, playlist (mp4), or info (metadata only)",
    )
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument(
        "-o", "--output",
        default="downloads",
        metavar="DIR",
        help="Output directory (default: ./downloads)",
    )
    parser.add_argument(
        "-r", "--resolution",
        default="best",
        metavar="HEIGHT",
        help="Video resolution height e.g. 1080, 720 (default: best)",
    )
    parser.add_argument(
        "-q", "--quality",
        default="320",
        metavar="KBPS",
        help="MP3 audio bitrate in kbps e.g. 320, 192, 128 (default: 320)",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        default=False,
        help="Download MP4 without audio track (video only)",
    )

    args = parser.parse_args()

    try:
        if args.mode == "mp4":
            download_mp4(
                args.url,
                output_dir=args.output,
                resolution=args.resolution,
                audio=not args.no_audio,
            )

        elif args.mode == "mp3":
            download_mp3(args.url, output_dir=args.output, quality=args.quality)

        elif args.mode == "playlist":
            download_playlist_mp4(args.url, output_dir=args.output, resolution=args.resolution)

        elif args.mode == "info":
            info = get_info(args.url)
            print(f"\nTitle    : {info.get('title')}")
            print(f"Uploader : {info.get('uploader')}")
            print(f"Duration : {info.get('duration_string', info.get('duration'))}s")
            print(f"Views    : {info.get('view_count'):,}" if info.get("view_count") else "")
            print(f"URL      : {info.get('webpage_url')}")
            print(f"\nAvailable formats: {len(info.get('formats', []))}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()