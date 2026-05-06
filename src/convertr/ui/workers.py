"""Background workers.

PySide6's main thread runs the event loop, so anything that blocks for more
than a frame (a download, an ffmpeg run, a probe) goes here. We use plain
``QThread`` subclasses because the QObject + ``moveToThread`` pattern is
overkill for these single-shot jobs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from ..core import converter, ffmpeg_installer, updater


class FFmpegInstallWorker(QThread):
    progress = Signal(int, int)   # downloaded_bytes, total_bytes
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            ffmpeg_installer.download_and_install(
                progress=lambda d, t: self.progress.emit(d, t),
                cancel_check=lambda: self._cancel,
            )
            if not self._cancel:
                self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class UpdateCheckWorker(QThread):
    """Silent check at startup. Emits the release info iff there's a newer one."""
    update_available = Signal(object)  # ReleaseInfo
    no_update = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            info = updater.fetch_latest()
            if info is None:
                self.no_update.emit()
                return
            if updater.is_newer(info):
                self.update_available.emit(info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.error.emit(str(e))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, int)
    finished_ok = Signal(object)  # Path to installer
    failed = Signal(str)

    def __init__(self, info) -> None:
        super().__init__()
        self._info = info
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            path = updater.download_installer(
                self._info,
                progress=lambda d, t: self.progress.emit(d, t),
                cancel_check=lambda: self._cancel,
            )
            if path is None and not self._cancel:
                self.failed.emit("Download failed.")
            elif path is not None:
                self.finished_ok.emit(path)
        except Exception as e:
            self.failed.emit(str(e))


class BatchConvertWorker(QThread):
    """Run a list of conversions sequentially.

    Emits progress for the current file and overall, and a per-file result
    so the UI can update each row's status as it finishes.
    """
    file_started = Signal(int, str)              # index, source path
    file_progress = Signal(int, float)           # index, percent
    file_finished = Signal(int, object)          # index, ConversionResult
    overall_progress = Signal(float)             # 0..100 across all files
    all_finished = Signal()

    def __init__(self, jobs: list[dict]) -> None:
        """Each job dict: {input, output, target_format, mode, overwrite}."""
        super().__init__()
        self._jobs = jobs
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        total = len(self._jobs) or 1
        for i, job in enumerate(self._jobs):
            if self._cancel:
                break
            self.file_started.emit(i, str(job["input"]))

            def on_progress(pct: float, idx: int = i):
                self.file_progress.emit(idx, pct)
                # Overall = (completed files + current file fraction) / total.
                overall = ((idx + pct / 100.0) / total) * 100.0
                self.overall_progress.emit(overall)

            try:
                result = converter.convert(
                    Path(job["input"]),
                    Path(job["output"]),
                    job["target_format"],
                    mode=job["mode"],
                    overwrite=job["overwrite"],
                    progress=on_progress,
                    cancel_check=lambda: self._cancel,
                )
            except converter.ConversionCancelled:
                break
            except Exception as e:
                result = converter.ConversionResult(
                    success=False,
                    output_path=Path(job["output"]),
                    mode_used="encode",
                    duration_seconds=0.0,
                    error_message=str(e),
                )

            self.file_finished.emit(i, result)
            self.overall_progress.emit(((i + 1) / total) * 100.0)

        self.all_finished.emit()
