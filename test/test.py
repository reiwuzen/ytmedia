"""
test.py
=======
Basic smoke tests for ytmedia v0.4.0
"""

from ytmedia import (
    download_mp4,
    download_mp3,
    get_info,
    has_ffmpeg,
    has_js_runtime,
    get_missing_dependencies,
    DownloadResult,
    DependencyMissing,
    DownloadFailed,
)

URL = "https://www.youtube.com/watch?v=BcYKQUy9iY0"

# ---------------------------------------------------------------------------
# 1 — environment check
# ---------------------------------------------------------------------------
print("=== Environment ===")
print(f"ffmpeg      : {'OK' if has_ffmpeg() else 'MISSING'}")
print(f"JS runtime  : {'OK' if has_js_runtime() else 'MISSING'}")
missing = get_missing_dependencies()
if missing:
    print(f"Missing deps: {missing}")
    print("Run: ytmedia install-deps")
else:
    print("All dependencies OK")
print()

# ---------------------------------------------------------------------------
# 2 — metadata fetch
# ---------------------------------------------------------------------------
print("=== get_info ===")
try:
    info = get_info(URL)
    print(f"height   : {info.get("width")}")   # e.g. 1920
    print(f"width    : {info.get("height")}")  # e.g. 1080
    print(f"Title    : {info.get('title')}")
    print(f"Uploader : {info.get('uploader')}")
    print(f"Duration : {info.get('duration_string')}s")
    print(f"Formats  : {len(info.get('formats', []))}")
except DownloadFailed as e:
    print(f"get_info failed: {e}")
print()

# ---------------------------------------------------------------------------
# 3 — MP4 download
# ---------------------------------------------------------------------------
print("=== download_mp4 ===")
try:
    result = download_mp4(URL, output_dir="downloads")
    assert isinstance(result, DownloadResult), "Expected DownloadResult"
    print(f"path       : {result.path}")
    print(f"title      : {result.title}")
    print(f"resolution : {result.resolution}")
    print(f"video codec: {result.video_codec}")
    print(f"audio codec: {result.audio_codec}")
    print(f"filesize   : {result.filesize}")
except DependencyMissing as e:
    print(f"Skipped -- missing dependency: {e.dependency}")
    print("Run: ytmedia install-deps")
except DownloadFailed as e:
    print(f"download_mp4 failed: {e}")
print()

# ---------------------------------------------------------------------------
# 4 — MP3 download
# ---------------------------------------------------------------------------
print("=== download_mp3 ===")
try:
    result = download_mp3(URL, output_dir="downloads", quality="192")
    assert isinstance(result, DownloadResult), "Expected DownloadResult"
    print(f"path       : {result.path}")
    print(f"title      : {result.title}")
    print(f"audio codec: {result.audio_codec}")
except DependencyMissing as e:
    print(f"Skipped -- missing dependency: {e.dependency}")
    print("Run: ytmedia install-deps")
except DownloadFailed as e:
    print(f"download_mp3 failed: {e}")
print()

print("=== all tests done ===")