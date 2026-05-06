"""GitHub Releases-based updater.

On launch the app pings the GitHub API for the latest release. If its tag
is newer than the running version, the UI shows a non-intrusive banner.
The user can download and run the installer from inside the app — the
installer's own ``CloseApplications=force`` directive replaces the running
copy cleanly.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from .. import __github_repo__, __version__

API_LATEST = f"https://api.github.com/repos/{__github_repo__}/releases/latest"

ProgressCallback = Callable[[int, int], None]


@dataclass
class ReleaseInfo:
    tag: str           # e.g. "v3.0.1"
    version: str       # e.g. "3.0.1"
    name: str
    body: str
    installer_url: Optional[str]
    installer_name: Optional[str]


def _parse_version(s: str) -> tuple[int, ...]:
    """Convert '3.0.1' or 'v3.0.1' to (3, 0, 1) for comparison.

    Non-numeric segments are dropped — pre-release suffixes like
    ``-beta`` aren't compared semantically because we don't ship them yet.
    """
    s = s.strip().lstrip("vV")
    parts = re.split(r"[.\-+]", s)
    nums: list[int] = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
        else:
            break
    return tuple(nums) if nums else (0,)


def fetch_latest() -> Optional[ReleaseInfo]:
    """Return the latest release on GitHub, or None on any failure.

    Updater errors should never crash the app — we swallow exceptions and
    let the caller treat ``None`` as "no update available".
    """
    try:
        req = Request(
            API_LATEST,
            headers={
                "User-Agent": "Convertr-Updater",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    tag = data.get("tag_name") or ""
    if not tag:
        return None

    installer_url = None
    installer_name = None
    for asset in data.get("assets") or []:
        name = asset.get("name") or ""
        # The release workflow names the main installer
        # ``Convertr-Setup-vX.Y.Z.exe`` — match any setup .exe to be safe.
        if name.lower().endswith(".exe") and "setup" in name.lower() and "ffmpeg" not in name.lower():
            installer_url = asset.get("browser_download_url")
            installer_name = name
            break

    return ReleaseInfo(
        tag=tag,
        version=tag.lstrip("vV"),
        name=data.get("name") or tag,
        body=data.get("body") or "",
        installer_url=installer_url,
        installer_name=installer_name,
    )


def is_newer(remote: ReleaseInfo, current: str = __version__) -> bool:
    return _parse_version(remote.version) > _parse_version(current)


def download_installer(
    info: ReleaseInfo,
    progress: Optional[ProgressCallback] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Optional[Path]:
    """Download the installer EXE to a temp folder and return its path."""
    if not info.installer_url or not info.installer_name:
        return None

    tmp_dir = Path(tempfile.mkdtemp(prefix="convertr_update_"))
    out_path = tmp_dir / info.installer_name

    try:
        req = Request(info.installer_url, headers={"User-Agent": "Convertr-Updater"})
        with urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk = 1024 * 64
            with open(out_path, "wb") as f:
                while True:
                    if cancel_check and cancel_check():
                        # Clean up the partial download.
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                        return None
                    data = response.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress:
                        progress(downloaded, total)
        return out_path
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None


def run_installer_and_exit(installer_path: Path) -> None:
    """Launch the installer and immediately quit, so it can replace this binary.

    ``/SILENT`` runs without prompts but still shows progress; the Inno Setup
    script is configured with ``CloseApplications=force`` so the running
    Convertr is closed automatically before files are overwritten.
    """
    if sys.platform != "win32":
        return
    try:
        subprocess.Popen(
            [str(installer_path), "/SILENT"],
            creationflags=0x00000008,  # DETACHED_PROCESS
        )
    finally:
        sys.exit(0)
