# ytmedia

Download MP4 (video + audio) and MP3 from YouTube at the highest possible quality, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

## Installation

```bash
pip install ytmedia
```

Or install from source (for development):

```bash
git clone https://github.com/yourusername/ytmedia
cd ytmedia
pip install -e .
```

---

## Quick Setup

After installing, check your environment and install any missing dependencies:

```bash
# Check what's installed
ytmedia doctor

# Install missing dependencies interactively
ytmedia install-deps
```

> **Note:** For best quality (1080p/4K), Node.js is recommended.
> Install from [nodejs.org](https://nodejs.org) if you don't have it.

---

## Requirements

- Python 3.10+
- ffmpeg — required for 1080p/4K and MP3 conversion (`ytmedia install-deps` can set this up)
- Node.js (recommended) — for full YouTube format support

---

## Usage

### As a Python library

```python
from ytmedia import download_mp4, download_mp3, download_playlist_mp4, get_info
from ytmedia import DownloadResult, DependencyMissing, DownloadFailed

# Download best quality MP4 (video + audio)
result = download_mp4("https://youtu.be/xxxx")
print(result.path)        # Path to saved file
print(result.resolution)  # e.g. '1080p'
print(result.audio_codec) # e.g. 'aac'

# Download MP4 capped at 1080p
result = download_mp4("https://youtu.be/xxxx", resolution="1080")

# Download to a specific folder
result = download_mp4("https://youtu.be/xxxx", output_dir="./videos")

# Download MP4 without audio (video only)
result = download_mp4("https://youtu.be/xxxx", audio=False)

# Download MP3 at 320kbps
result = download_mp3("https://youtu.be/xxxx")

# Download MP3 at a lower bitrate
result = download_mp3("https://youtu.be/xxxx", quality="192", output_dir="./music")

# Download an entire playlist as MP4
playlist = download_playlist_mp4("https://youtube.com/playlist?list=xxxx")
print(playlist)  # PlaylistResult(12/12 downloaded, 0 failed)

# Get video metadata without downloading
info = get_info("https://youtu.be/xxxx")
print(info["title"], info["duration"])
```

### Error handling

```python
from ytmedia import download_mp4, DependencyMissing, DownloadFailed, YtMediaError

try:
    result = download_mp4("https://youtu.be/xxxx")
    print(f"Saved to {result.path}")
except DependencyMissing as e:
    print(f"Missing: {e.dependency}")  # e.g. 'ffmpeg'
except DownloadFailed as e:
    print(f"Download failed: {e}")
except YtMediaError as e:
    print(f"Error: {e}")
```

### Environment checks

```python
from ytmedia import has_ffmpeg, has_js_runtime, get_missing_dependencies

# Quick checks — cached, no repeated PATH probing
if not has_ffmpeg():
    print("ffmpeg not found — run: ytmedia install-deps")

missing = get_missing_dependencies()
if missing:
    print(f"Missing dependencies: {missing}")
```

### As a CLI tool

After installation, the `ytmedia` command is available globally:

```bash
# Check environment
ytmedia doctor

# Install missing dependencies
ytmedia install-deps

# Download MP4 (best quality)
ytmedia mp4 https://youtu.be/xxxx

# Download MP4 at 1080p into a specific folder
ytmedia mp4 https://youtu.be/xxxx -r 1080 -o ./videos

# Download MP4 without audio
ytmedia mp4 https://youtu.be/xxxx --no-audio

# Download MP3 at 320kbps
ytmedia mp3 https://youtu.be/xxxx

# Download MP3 at 192kbps into a specific folder
ytmedia mp3 https://youtu.be/xxxx -q 192 -o ./music

# Download an entire playlist
ytmedia playlist https://youtube.com/playlist?list=xxxx

# Print video metadata
ytmedia info https://youtu.be/xxxx

# Show full yt-dlp logs (for troubleshooting)
ytmedia mp4 https://youtu.be/xxxx --debug
```

#### CLI options

| Flag | Description | Default |
|---|---|---|
| `-o`, `--output` | Output directory | `./downloads` |
| `-r`, `--resolution` | Max video height e.g. `1080`, `720` | `best` |
| `-q`, `--quality` | MP3 bitrate in kbps e.g. `320`, `192` | `320` |
| `--no-audio` | Download MP4 without audio track | off |
| `--debug` | Show full yt-dlp internal logs | off |

---

## Notes

- URLs containing `&list=` (e.g. from YouTube autoplay) are treated as single-video downloads
  by default. Use `ytmedia playlist <url>` or pass `allow_playlist=True` in Python to download
  the full playlist.
- MP4 audio is re-encoded to **AAC** during the merge step, ensuring compatibility with
  Windows Media Player, QuickTime, and mobile devices.
- Without ffmpeg, `download_mp4(audio=True)` raises `DependencyMissing`. Run
  `ytmedia install-deps` to fix.
- MP3 conversion always requires ffmpeg.

---

## License

MIT