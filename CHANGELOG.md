# Changelog

All notable changes to ytmedia will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.2] — 2026-02-19

### Added
- `init()` now prompts the user when ffmpeg is missing with three options:
  - `[1]` Download bundled binary via static-ffmpeg (Python environment only)
  - `[2]` Show system-wide install instructions (winget / brew / apt)
  - `[s]` Skip

### Fixed
- Version bump to resolve PyPI filename reuse error (0.2.1 upload failed mid-upload)
- Corrected misleading documentation — `init()` installs a bundled ffmpeg scoped to
  the Python environment, not a system-wide install

---

## [0.2.1] — 2026-02-19

### Added
- Animated spinner (`⠹`) shown during ffmpeg merge step instead of static 0%/100% text

### Changed
- Removed `static-ffmpeg` from core dependencies to avoid pulling in `twine` and its
  large dependency chain on every `pip install ytmedia`

---

## [0.2.0] — 2026-02-19

### Added
- `init()` — sets up yt-dlp-ejs and a bundled ffmpeg binary for the Python environment
- `ytmedia init` CLI command
- Cross-platform ffmpeg install instructions printed as fallback when auto-setup fails
- Merge progress display during ffmpeg video+audio merge step
- AAC audio encoding during merge — fixes Opus codec incompatibility with Windows
  Media Player and QuickTime
- `--no-audio` CLI flag for video-only MP4 downloads
- Auto-detection of Node.js and Deno JS runtimes for full YouTube format support

### Fixed
- MP4 downloads missing audio due to Opus codec being embedded in MP4 container
- Playlist URLs (e.g. `&list=...`) being downloaded as full playlists instead of single video
- ffmpeg not found when Node.js is installed in a non-standard PATH location

### Changed
- `static-ffmpeg` and `yt-dlp-ejs` moved to core dependencies (previously optional)
- `download_mp4()` now accepts `audio: bool = True` parameter

---

## [0.1.0] — 2026-02-19

### Added
- `download_mp4()` — download YouTube videos as MP4 at highest available resolution
- `download_mp3()` — extract and convert audio to MP3 at up to 320kbps
- `download_playlist_mp4()` — download entire YouTube playlists as MP4
- `get_info()` — fetch video metadata without downloading
- CLI tool (`ytmedia`) with `mp4`, `mp3`, `playlist`, and `info` commands
- `-r` / `--resolution` flag to cap video height (e.g. `1080`, `720`)
- `-q` / `--quality` flag to set MP3 bitrate (e.g. `320`, `192`, `128`)
- `-o` / `--output` flag to set output directory

### Notes
- Requires Python 3.10+
- ffmpeg must be installed manually in this version — see README