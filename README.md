# ytmedia

Download MP4 (video + audio) and MP3 from YouTube at the highest possible quality, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

## Requirements

- Python 3.10+
- **ffmpeg** — required for 1080p/4K video and MP3 conversion

### Installing ffmpeg

| OS | Command |
|----|---------|
| Windows | `winget install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |

> **Don't want to install ffmpeg manually?**
> Install with the bundled ffmpeg option:
> ```bash
> pip install "ytmedia[ffmpeg]"
> ```

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

## Usage

### As a Python library

```python
from ytmedia import download_mp4, download_mp3, download_playlist_mp4, get_info

# Download best quality MP4 (video + audio)
download_mp4("https://youtu.be/xxxx")

# Download MP4 capped at 1080p
download_mp4("https://youtu.be/xxxx", resolution="1080")

# Download to a specific folder
download_mp4("https://youtu.be/xxxx", output_dir="./videos")

# Download MP3 at 320kbps
download_mp3("https://youtu.be/xxxx")

# Download MP3 at a lower bitrate
download_mp3("https://youtu.be/xxxx", quality="192", output_dir="./music")

# Download an entire playlist as MP4
download_playlist_mp4("https://youtube.com/playlist?list=xxxx")

# Get video metadata without downloading
info = get_info("https://youtu.be/xxxx")
print(info["title"], info["duration"])
```

### As a CLI tool

After installation, the `ytmedia` command is available globally:

```bash
# Download MP4 (best quality)
ytmedia mp4 https://youtu.be/xxxx

# Download MP4 at 1080p into a specific folder
ytmedia mp4 https://youtu.be/xxxx -r 1080 -o ./videos

# Download MP3 at 320kbps
ytmedia mp3 https://youtu.be/xxxx

# Download MP3 at 192kbps
ytmedia mp3 https://youtu.be/xxxx -q 192 -o ./music

# Download an entire playlist
ytmedia playlist https://youtube.com/playlist?list=xxxx

# Print video metadata
ytmedia info https://youtu.be/xxxx
```

#### CLI options

| Flag | Description | Default |
|---|---|---|
| `-o`, `--output` | Output directory | `./downloads` |
| `-r`, `--resolution` | Max video height (e.g. `1080`, `720`) | `best` |
| `-q`, `--quality` | MP3 bitrate in kbps (e.g. `320`, `192`) | `320` |

---

## Notes

- URLs containing `&list=` (e.g. from YouTube autoplay) are treated as single-video downloads by default. Use `ytmedia playlist <url>` or pass `allow_playlist=True` in Python to download the full playlist.
- Without ffmpeg, MP4 downloads fall back to a pre-merged single stream, which is usually capped at 720p.
- MP3 conversion always requires ffmpeg.

---

## License

MIT