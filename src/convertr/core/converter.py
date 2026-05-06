"""Conversion engine.

Two modes:

* **Smart Fast** — probe the input with ffprobe, decide whether each stream
  can be copied (remuxed) into the target container, and only re-encode the
  streams that have to change. A 4 GB MKV → MP4 with H.264/AAC takes seconds.

* **Maximum Compatibility** — always re-encode to safe, broadly-supported
  codecs (H.264/AAC for video targets, native codecs for audio targets).

Both modes run ffmpeg in a subprocess, parse progress lines, and emit
percentage updates via a callback so the UI can show a live progress bar.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .ffmpeg_installer import ensure_paths

# --- format definitions -----------------------------------------------------

VIDEO_FORMATS = ("mp4", "mkv", "mov", "webm")
AUDIO_FORMATS = ("m4a", "aac", "mp3", "wav", "flac")
ALL_FORMATS = VIDEO_FORMATS + AUDIO_FORMATS

# Which video codecs each container will tolerate as a stream copy.
# (Anything not listed forces a re-encode in Smart Fast mode.)
CONTAINER_VIDEO_COMPAT: dict[str, set[str]] = {
    "mp4": {"h264", "hevc", "mpeg4", "av1"},
    "mkv": {"h264", "hevc", "mpeg4", "av1", "vp9", "vp8", "mpeg2video"},
    "mov": {"h264", "hevc", "mpeg4", "prores"},
    "webm": {"vp9", "vp8", "av1"},
}

CONTAINER_AUDIO_COMPAT: dict[str, set[str]] = {
    "mp4": {"aac", "mp3", "ac3", "eac3"},
    "mkv": {"aac", "mp3", "ac3", "eac3", "flac", "opus", "vorbis", "pcm_s16le"},
    "mov": {"aac", "mp3", "ac3", "pcm_s16le"},
    "webm": {"opus", "vorbis"},
}

# Re-encode targets when Smart Fast needs to convert a stream.
DEFAULT_VIDEO_ENCODER = "libx264"
DEFAULT_AUDIO_ENCODER_FOR_CONTAINER = {
    "mp4": "aac",
    "mkv": "aac",
    "mov": "aac",
    "webm": "libopus",
}

# Audio-only output: what codec/extension pair to use.
AUDIO_OUTPUT_ENCODER = {
    "m4a": ("aac", "m4a"),
    "aac": ("aac", "aac"),
    "mp3": ("libmp3lame", "mp3"),
    "wav": ("pcm_s16le", "wav"),
    "flac": ("flac", "flac"),
}

# --- progress / cancellation -----------------------------------------------

ProgressCallback = Callable[[float], None]  # value in 0..100


@dataclass
class ConversionResult:
    success: bool
    output_path: Path
    mode_used: str  # "remux" or "encode"
    duration_seconds: float
    error_message: Optional[str] = None


class ConversionCancelled(Exception):
    pass


# --- probing ---------------------------------------------------------------

def _no_window_flags() -> int:
    """Subprocess flag to suppress the console window on Windows."""
    return 0x08000000 if sys.platform == "win32" else 0


def _probe(input_path: Path) -> dict:
    """Run ffprobe on a file and return its JSON output as a dict."""
    _, ffprobe = ensure_paths()
    cmd = [
        str(ffprobe),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=_no_window_flags(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip() or 'unknown error'}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe returned invalid JSON: {e}")


def _duration_seconds(probe_data: dict) -> float:
    """Extract media duration from probe data; 0.0 if unavailable."""
    fmt = probe_data.get("format") or {}
    try:
        return float(fmt.get("duration", 0.0))
    except (TypeError, ValueError):
        return 0.0


# --- command building ------------------------------------------------------

def _build_command(
    ffmpeg: Path,
    input_path: Path,
    output_path: Path,
    target_format: str,
    mode: str,
    probe_data: dict,
    overwrite: bool,
) -> tuple[list[str], str]:
    """Build the ffmpeg argv plus a label of the mode actually used."""
    target = target_format.lower().lstrip(".")
    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    base = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-stats"]
    if overwrite:
        base.append("-y")
    else:
        base.append("-n")
    base.extend(["-i", str(input_path)])

    is_audio_target = target in AUDIO_FORMATS

    # ---- audio output --------------------------------------------------
    if is_audio_target:
        encoder, _ext = AUDIO_OUTPUT_ENCODER[target]
        # We don't even try to stream-copy into a different audio container —
        # the speedup is negligible and the failure modes are surprising.
        cmd = base + [
            "-vn",
            "-c:a", encoder,
            "-map_metadata", "0",
            str(output_path),
        ]
        return cmd, "encode"

    # ---- video output --------------------------------------------------
    video_compat = CONTAINER_VIDEO_COMPAT.get(target, set())
    audio_compat = CONTAINER_AUDIO_COMPAT.get(target, set())

    can_copy_video = bool(video_streams) and all(
        s.get("codec_name") in video_compat for s in video_streams
    )
    can_copy_audio = (not audio_streams) or all(
        s.get("codec_name") in audio_compat for s in audio_streams
    )

    if mode == "smart_fast" and can_copy_video and can_copy_audio:
        # Pure remux. Copy all streams; just rewrap the container.
        # Use 0:V (video) and 0:a (audio) specifiers instead of 0 so that
        # non-AV streams (timecode tracks, data tracks with codec=none) are
        # silently skipped rather than causing a "codec not supported in
        # container" error.
        cmd = base + [
            "-map", "0:V", "-map", "0:a",
            "-c", "copy",
            "-map_metadata", "0",
            str(output_path),
        ]
        return cmd, "remux"

    if mode == "smart_fast" and can_copy_video:
        # Copy video, transcode audio only.
        audio_enc = DEFAULT_AUDIO_ENCODER_FOR_CONTAINER.get(target, "aac")
        cmd = base + [
            "-map", "0:V", "-map", "0:a",
            "-c:v", "copy",
            "-c:a", audio_enc,
            "-map_metadata", "0",
            str(output_path),
        ]
        return cmd, "encode"

    # Fallback: full re-encode. Used by max_compat mode and by smart_fast
    # whenever the source video codec doesn't fit the target container.
    audio_enc = DEFAULT_AUDIO_ENCODER_FOR_CONTAINER.get(target, "aac")
    cmd = base + [
        "-map", "0:V", "-map", "0:a",
        "-c:v", DEFAULT_VIDEO_ENCODER,
        "-preset", "medium",
        "-crf", "20",
        "-c:a", audio_enc,
        "-map_metadata", "0",
        str(output_path),
    ]
    return cmd, "encode"


# --- runner ----------------------------------------------------------------

# ffmpeg's `-stats` output gives lines like:
#   frame=  120 fps= 60 q=-1.0 size=  512kB time=00:00:02.00 bitrate=...
# We just need the time= value for progress.
_TIME_RE = re.compile(r"time=(\d+):(\d{2}):(\d{2}\.\d+)")


def _parse_time(line: str) -> Optional[float]:
    m = _TIME_RE.search(line)
    if not m:
        return None
    h, mm, ss = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(ss)


def convert(
    input_path: Path,
    output_path: Path,
    target_format: str,
    mode: str = "smart_fast",
    overwrite: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> ConversionResult:
    """Convert one file. See module docstring."""
    ffmpeg, _ = ensure_paths()

    probe_data = _probe(input_path)
    total_duration = _duration_seconds(probe_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd, mode_used = _build_command(
        ffmpeg, input_path, output_path, target_format, mode, probe_data, overwrite,
    )

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered so progress lines arrive promptly
        creationflags=_no_window_flags(),
    )

    last_pct = 0.0
    error_lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if cancel_check and cancel_check():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                # Best-effort cleanup of partial output file.
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except OSError:
                        pass
                raise ConversionCancelled()

            t = _parse_time(line)
            if t is not None and total_duration > 0 and progress:
                pct = min(99.0, (t / total_duration) * 100.0)
                if pct - last_pct >= 0.5:  # throttle UI updates
                    progress(pct)
                    last_pct = pct
            else:
                # Hold onto everything that didn't look like a progress line —
                # it's our best bet for an error message if ffmpeg fails.
                stripped = line.strip()
                if stripped and t is None:
                    error_lines.append(stripped)
    finally:
        proc.wait()

    if proc.returncode != 0:
        msg = "\n".join(error_lines[-6:]) or f"ffmpeg exited with code {proc.returncode}"
        return ConversionResult(
            success=False,
            output_path=output_path,
            mode_used=mode_used,
            duration_seconds=total_duration,
            error_message=msg,
        )

    if progress:
        progress(100.0)

    return ConversionResult(
        success=True,
        output_path=output_path,
        mode_used=mode_used,
        duration_seconds=total_duration,
    )
