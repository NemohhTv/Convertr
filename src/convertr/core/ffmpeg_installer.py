"""FFmpeg install / detection.

Convertr ships without FFmpeg (LGPL/GPL distribution headaches and size).
Instead, the user clicks "Install FFmpeg" in Settings and we download a
portable Windows build into ``%LOCALAPPDATA%\\Convertr\\ffmpeg``.

The downloader supports progress callbacks so the UI can show a progress bar.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from .paths import ffmpeg_binary, ffmpeg_dir, ffprobe_binary

# gyan.dev's "essentials" build is a small, regularly-updated, statically-linked
# Windows FFmpeg distribution. The "latest" URL is a permanent redirect to the
# current build, so we don't have to chase version numbers.
FFMPEG_WINDOWS_URL = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)

ProgressCallback = Callable[[int, int], None]  # (downloaded_bytes, total_bytes)


def is_installed() -> bool:
    """Return True iff our private FFmpeg binary exists and runs."""
    bin_path = ffmpeg_binary()
    if not bin_path.exists():
        return False
    try:
        # CREATE_NO_WINDOW so we don't flash a console window on Windows.
        creationflags = 0x08000000 if sys.platform == "win32" else 0
        result = subprocess.run(
            [str(bin_path), "-version"],
            capture_output=True,
            timeout=5,
            creationflags=creationflags,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def installed_version() -> Optional[str]:
    """Parse the version string from ``ffmpeg -version``."""
    if not is_installed():
        return None
    try:
        creationflags = 0x08000000 if sys.platform == "win32" else 0
        out = subprocess.run(
            [str(ffmpeg_binary()), "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=creationflags,
        ).stdout
        # First line looks like: "ffmpeg version 6.1.1-essentials_build-www.gyan.dev ..."
        first = out.splitlines()[0] if out else ""
        parts = first.split()
        if len(parts) >= 3 and parts[0] == "ffmpeg" and parts[1] == "version":
            return parts[2]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        pass
    return None


def download_and_install(
    progress: Optional[ProgressCallback] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    """Download FFmpeg, extract it, and place it at the expected location.

    Raises an exception on failure so the caller can surface an error.
    Calls ``progress(downloaded, total)`` periodically when given.
    Returns early (and cleans up) if ``cancel_check()`` returns True.
    """
    target_dir = ffmpeg_dir()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "ffmpeg.zip"

        # --- download ---
        req = Request(FFMPEG_WINDOWS_URL, headers={"User-Agent": "Convertr/1.0"})
        with urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk = 1024 * 64
            with open(zip_path, "wb") as f:
                while True:
                    if cancel_check and cancel_check():
                        return
                    data = response.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress:
                        progress(downloaded, total)

        # --- extract ---
        # gyan zips look like ffmpeg-X.Y.Z-essentials_build/{bin,doc,...}
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        # Find the single top-level folder inside the zip.
        roots = [p for p in extract_dir.iterdir() if p.is_dir()]
        if not roots:
            raise RuntimeError("FFmpeg archive had no contents.")
        src_root = roots[0]

        # --- install: replace existing install atomically-ish ---
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        for child in src_root.iterdir():
            dest = target_dir / child.name
            if child.is_dir():
                shutil.copytree(child, dest)
            else:
                shutil.copy2(child, dest)

    # Sanity check.
    if not ffmpeg_binary().exists():
        raise RuntimeError(
            "FFmpeg install completed but the binary was not found where expected."
        )


def uninstall() -> None:
    """Remove the private FFmpeg install."""
    target = ffmpeg_dir()
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def ensure_paths() -> tuple[Path, Path]:
    """Return (ffmpeg, ffprobe) paths, raising if FFmpeg isn't installed."""
    if not is_installed():
        raise RuntimeError("FFmpeg is not installed. Open Settings to install it.")
    return ffmpeg_binary(), ffprobe_binary()
