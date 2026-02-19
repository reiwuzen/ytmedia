"""
env.py
======
Environment detection helpers.
Results are cached at module level so detection only runs once per process.
"""

import functools
import shutil
from typing import Optional


@functools.lru_cache(maxsize=None)
def find_ffmpeg() -> Optional[str]:
    """
    Return the path to ffmpeg if available on PATH, else None.
    Result is cached — detection only runs once per process.
    """
      # Check system PATH first — no download needed if already installed
    found = shutil.which("ffmpeg")
    if found:
        return found

    # Only fall back to static_ffmpeg if system ffmpeg is missing
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass
    return shutil.which("ffmpeg")


@functools.lru_cache(maxsize=None)
def find_node() -> Optional[str]:
    """
    Return the path to node if available on PATH, else None.
    Result is cached — detection only runs once per process.
    """
    return shutil.which("node") or shutil.which("node.exe")


@functools.lru_cache(maxsize=None)
def find_deno() -> Optional[str]:
    """
    Return the path to deno if available on PATH, else None.
    Result is cached — detection only runs once per process.
    """
    return shutil.which("deno")


def has_ffmpeg() -> bool:
    """Return True if ffmpeg is available."""
    return find_ffmpeg() is not None


def has_js_runtime() -> bool:
    """Return True if at least one supported JS runtime is available."""
    return find_node() is not None or find_deno() is not None


def get_js_runtimes() -> dict[str, str]:
    """
    Return a dict of available JS runtimes and their paths.
    e.g. {'node': '/usr/bin/node'}
    """
    runtimes: dict[str, str] = {}
    node = find_node()
    if node:
        runtimes["node"] = node
    deno = find_deno()
    if deno:
        runtimes["deno"] = deno
    return runtimes


def get_missing_dependencies() -> list[str]:
    """
    Return a list of missing required dependencies.
    Empty list means everything is available.

    Usage
    -----
    missing = get_missing_dependencies()
    if missing:
        print(f"Missing: {missing}")
    """
    missing = []
    if not has_ffmpeg():
        missing.append("ffmpeg")
    if not has_js_runtime():
        missing.append("nodejs")
    return missing


def check_ffmpeg() -> bool:
    """
    Return True if ffmpeg is available, False otherwise.
    Useful for a quick pre-flight check before downloading.
    """
    return has_ffmpeg()