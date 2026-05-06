"""Main window.

Three tabs:

* **Convert** — drop files, pick target format, hit Convert. Supports batch.
* **History** — recent conversions; double-click to open.
* **Settings** — output folder, mode, FFmpeg install, app update, toggles.

The window uses a system tray icon (when enabled) so closing the window
just hides it. Real quit goes through File → Exit or the tray menu.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..core import converter as conv_mod
from ..core import ffmpeg_installer
from ..core.paths import resource_path, user_data_dir
from ..core.settings import (
    HistoryEntry,
    Settings,
    append_history,
    clear_history,
    load_history,
)
from .theme import STYLESHEET
from .workers import (
    BatchConvertWorker,
    FFmpegInstallWorker,
    UpdateCheckWorker,
    UpdateDownloadWorker,
)


def _format_bytes(n: int) -> str:
    if n <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _format_duration(seconds: float) -> str:
    if seconds < 1:
        return "<1s"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Convert tab
# ---------------------------------------------------------------------------

class DropZone(QFrame):
    """Big dashed-border area that accepts dragged files."""

    def __init__(self, on_files_dropped) -> None:
        super().__init__()
        self.setObjectName("drop_zone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self._on_files_dropped = on_files_dropped

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(6)

        title = QLabel("Drop files here")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e8eaed;")

        sub = QLabel("or click below to browse")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setProperty("role", "muted")
        sub.setStyleSheet("color: #9aa0a6; font-size: 12px;")

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", "true")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("dragging", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent) -> None:
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(Path(url.toLocalFile()))
        self.setProperty("dragging", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if files:
            self._on_files_dropped(files)


class ConvertTab(QWidget):
    """The main 'do work' tab."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self._window = window
        self._files: list[Path] = []
        self._worker: Optional[BatchConvertWorker] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # --- drop zone + browse ----------------------------------------
        self.drop_zone = DropZone(self._add_files)
        root.addWidget(self.drop_zone)

        browse_row = QHBoxLayout()
        browse_row.setSpacing(8)
        self.browse_btn = QPushButton("  Browse files…")
        self.browse_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.browse_btn.clicked.connect(self._browse)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("role", "ghost")
        self.clear_btn.clicked.connect(self._clear_files)
        browse_row.addWidget(self.browse_btn)
        browse_row.addWidget(self.clear_btn)
        browse_row.addStretch()
        root.addLayout(browse_row)

        # --- file table -------------------------------------------------
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["File", "Size", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(160)
        root.addWidget(self.table, 1)

        # --- output controls -------------------------------------------
        controls = QFrame()
        controls.setObjectName("card")
        c_layout = QVBoxLayout(controls)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        fmt_label = QLabel("Convert to")
        fmt_label.setProperty("role", "muted")
        fmt_label.setMinimumWidth(80)
        self.format_combo = QComboBox()
        for f in conv_mod.ALL_FORMATS:
            label = f.upper()
            kind = "Video" if f in conv_mod.VIDEO_FORMATS else "Audio"
            self.format_combo.addItem(f"{label}   ·   {kind}", f)
        self.format_combo.setMinimumWidth(180)
        row.addWidget(fmt_label)
        row.addWidget(self.format_combo)
        row.addStretch()
        c_layout.addLayout(row)

        # Progress bar (hidden until converting).
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setVisible(False)
        c_layout.addWidget(self.overall_progress)

        self.progress_label = QLabel("")
        self.progress_label.setProperty("role", "muted")
        self.progress_label.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        self.progress_label.setVisible(False)
        c_layout.addWidget(self.progress_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("role", "danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setProperty("role", "primary")
        self.convert_btn.setMinimumWidth(140)
        self.convert_btn.clicked.connect(self._start_convert)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.convert_btn)
        c_layout.addLayout(action_row)

        root.addWidget(controls)

    # -- file list helpers --------------------------------------------------

    def _browse(self) -> None:
        last = self._window.settings.last_input_folder or str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to convert",
            last,
            "Media files (*.mp4 *.mkv *.mov *.webm *.avi *.flv *.wmv *.m4v "
            "*.mp3 *.wav *.flac *.aac *.m4a *.ogg *.opus);;All files (*)",
        )
        if files:
            paths = [Path(f) for f in files]
            self._window.settings.last_input_folder = str(paths[0].parent)
            self._window.settings.save()
            self._add_files(paths)

    def _add_files(self, files: list[Path]) -> None:
        existing = {str(f) for f in self._files}
        for f in files:
            if str(f) in existing or not f.is_file():
                continue
            self._files.append(f)
            self._append_row(f)

    def _append_row(self, path: Path) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(path.name)
        name_item.setToolTip(str(path))
        size_item = QTableWidgetItem(_format_bytes(path.stat().st_size))
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_item = QTableWidgetItem("Ready")
        status_item.setForeground(Qt.GlobalColor.gray)

        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, size_item)
        self.table.setItem(row, 2, status_item)

    def _clear_files(self) -> None:
        if self._worker and self._worker.isRunning():
            return  # don't clear during a run
        self._files.clear()
        self.table.setRowCount(0)

    # -- conversion ---------------------------------------------------------

    def _start_convert(self) -> None:
        if not self._files:
            QMessageBox.information(self, "No files", "Add some files first.")
            return

        if not ffmpeg_installer.is_installed():
            answer = QMessageBox.question(
                self,
                "FFmpeg required",
                "FFmpeg isn't installed yet. Install it now?\n\n"
                "It downloads to your user folder — no admin needed.",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._window.tabs.setCurrentIndex(2)  # jump to Settings
                self._window.settings_tab.start_ffmpeg_install()
            return

        target_format = self.format_combo.currentData()
        settings = self._window.settings
        out_folder = Path(settings.output_folder) if settings.output_folder else None

        jobs: list[dict] = []
        for f in self._files:
            base_dir = out_folder if out_folder else f.parent
            base_dir.mkdir(parents=True, exist_ok=True)
            out_path = base_dir / f"{f.stem}.{target_format}"
            # If overwrite is off, append a counter to avoid clobbering.
            if not settings.overwrite and out_path.exists():
                i = 1
                while True:
                    candidate = base_dir / f"{f.stem} ({i}).{target_format}"
                    if not candidate.exists():
                        out_path = candidate
                        break
                    i += 1
            jobs.append({
                "input": f,
                "output": out_path,
                "target_format": target_format,
                "mode": settings.mode,
                "overwrite": settings.overwrite,
            })

        # UI state: disable inputs, show progress.
        self.convert_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.overall_progress.setVisible(True)
        self.overall_progress.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting…")

        # Reset per-row statuses.
        for row in range(self.table.rowCount()):
            self.table.item(row, 2).setText("Queued")
            self.table.item(row, 2).setForeground(Qt.GlobalColor.gray)

        self._jobs = jobs  # remember for history saving
        self._batch_started_at = time.time()

        self._worker = BatchConvertWorker(jobs)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.file_finished.connect(self._on_file_finished)
        self._worker.overall_progress.connect(self._on_overall_progress)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.progress_label.setText("Cancelling…")

    def _on_file_started(self, idx: int, source: str) -> None:
        self.table.item(idx, 2).setText("Converting…")
        self.progress_label.setText(f"Converting {Path(source).name}")

    def _on_file_progress(self, idx: int, pct: float) -> None:
        # Per-row progress is shown as a percentage in the status column.
        self.table.item(idx, 2).setText(f"Converting {pct:.0f}%")

    def _on_file_finished(self, idx: int, result: conv_mod.ConversionResult) -> None:
        item = self.table.item(idx, 2)
        if result.success:
            tag = "Remuxed ✓" if result.mode_used == "remux" else "Converted ✓"
            item.setText(tag)
            item.setForeground(Qt.GlobalColor.green)
            try:
                append_history(HistoryEntry(
                    source=str(self._jobs[idx]["input"]),
                    output=str(result.output_path),
                    target_format=self._jobs[idx]["target_format"],
                    mode_used=result.mode_used,
                    duration_seconds=result.duration_seconds,
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                ))
            except Exception:
                # History writes shouldn't block real work.
                pass
        else:
            item.setText("Failed")
            item.setForeground(Qt.GlobalColor.red)
            item.setToolTip(result.error_message or "")

    def _on_overall_progress(self, pct: float) -> None:
        self.overall_progress.setValue(int(pct))

    def _on_all_finished(self) -> None:
        elapsed = time.time() - self._batch_started_at
        succeeded = sum(
            1 for r in range(self.table.rowCount())
            if self.table.item(r, 2).text() in ("Remuxed ✓", "Converted ✓")
        )
        total = self.table.rowCount()
        self.progress_label.setText(
            f"Done — {succeeded}/{total} succeeded in {_format_duration(elapsed)}"
        )

        # Re-enable controls.
        self.convert_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

        # Keep the bar at 100 briefly, then hide.
        self.overall_progress.setValue(100)
        QTimer.singleShot(2500, lambda: self.overall_progress.setVisible(False))

        # Refresh history tab so the new entries show up immediately.
        self._window.history_tab.refresh()

        if self._window.settings.notify_on_complete and self._window.tray:
            self._window.tray.showMessage(
                "Convertr",
                f"Batch finished — {succeeded}/{total} succeeded.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )


# ---------------------------------------------------------------------------
# History tab
# ---------------------------------------------------------------------------

class HistoryTab(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self._window = window

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Recent conversions")
        title.setProperty("role", "title")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        header_row.addWidget(title)
        header_row.addStretch()
        self.clear_btn = QPushButton("Clear history")
        self.clear_btn.setProperty("role", "ghost")
        self.clear_btn.clicked.connect(self._clear)
        header_row.addWidget(self.clear_btn)
        root.addLayout(header_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File", "Format", "Mode", "When"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._open_output)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        root.addWidget(self.table, 1)

        self.empty_label = QLabel("No conversions yet. Files you convert will show up here.")
        self.empty_label.setProperty("role", "muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #9aa0a6; padding: 40px;")
        root.addWidget(self.empty_label)

        self.refresh()

    def refresh(self) -> None:
        entries = list(reversed(load_history()))
        self.table.setRowCount(0)
        for e in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(Path(e.output).name)
            name_item.setToolTip(e.output)
            name_item.setData(Qt.ItemDataRole.UserRole, e.output)
            fmt_item = QTableWidgetItem(e.target_format.upper())
            mode_item = QTableWidgetItem("Remux" if e.mode_used == "remux" else "Encode")
            try:
                ts = datetime.fromisoformat(e.timestamp).strftime("%b %d, %I:%M %p")
            except ValueError:
                ts = e.timestamp
            time_item = QTableWidgetItem(ts)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, fmt_item)
            self.table.setItem(row, 2, mode_item)
            self.table.setItem(row, 3, time_item)

        has_entries = self.table.rowCount() > 0
        self.table.setVisible(has_entries)
        self.empty_label.setVisible(not has_entries)

    def _open_output(self, row: int, _col: int) -> None:
        path = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _show_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        path_str = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        path = Path(path_str)

        menu = QMenu(self)
        open_action = menu.addAction("Open file")
        show_action = menu.addAction("Show in folder")
        open_action.setEnabled(path.exists())
        show_action.setEnabled(path.parent.exists())

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == open_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        elif chosen == show_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _clear(self) -> None:
        if QMessageBox.question(self, "Clear history", "Remove all history entries?") \
                == QMessageBox.StandardButton.Yes:
            clear_history()
            self.refresh()


# ---------------------------------------------------------------------------
# Settings tab
# ---------------------------------------------------------------------------

class SettingsTab(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self._window = window
        self._ffmpeg_worker: Optional[FFmpegInstallWorker] = None
        self._update_dl_worker: Optional[UpdateDownloadWorker] = None
        s = window.settings

        # Outer layout holds a single scroll area so the cards never get
        # squashed below their sizeHint — they just scroll if the window
        # is shorter than the content needs.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        outer.addWidget(scroll)

        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        scroll.setWidget(scroll_inner)

        root = QVBoxLayout(scroll_inner)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ---- Output ---------------------------------------------------
        out_card = self._make_card("OUTPUT")

        self.output_edit = QLineEdit(s.output_folder)
        self.output_edit.setPlaceholderText("Same folder as input file")
        self.output_edit.editingFinished.connect(self._save_output)
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse_output)
        clear = QPushButton("Default")
        clear.setProperty("role", "ghost")
        clear.clicked.connect(self._clear_output)
        out_card.layout().addWidget(
            self._row([(self.output_edit, 1), browse, clear])
        )

        root.addWidget(out_card)

        # ---- Conversion ----------------------------------------------
        conv_card = self._make_card("CONVERSION")

        mode_label = QLabel("Mode")
        mode_label.setMinimumWidth(80)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Smart Fast — remux when possible", "smart_fast")
        self.mode_combo.addItem("Maximum Compatibility — always re-encode", "max_compat")
        self.mode_combo.setCurrentIndex(0 if s.mode == "smart_fast" else 1)
        self.mode_combo.currentIndexChanged.connect(self._save_mode)
        conv_card.layout().addWidget(
            self._row([mode_label, (self.mode_combo, 1)])
        )

        self.overwrite_check = QCheckBox("Overwrite output if it already exists")
        self.overwrite_check.setChecked(s.overwrite)
        self.overwrite_check.toggled.connect(self._save_overwrite)
        conv_card.layout().addWidget(self.overwrite_check)

        root.addWidget(conv_card)

        # ---- FFmpeg ---------------------------------------------------
        self.ffmpeg_card = self._make_card("FFMPEG")
        self.ffmpeg_status = QLabel()
        self.ffmpeg_status.setWordWrap(True)
        self.ffmpeg_card.layout().addWidget(self.ffmpeg_status)

        self.ffmpeg_progress = QProgressBar()
        self.ffmpeg_progress.setVisible(False)
        self.ffmpeg_card.layout().addWidget(self.ffmpeg_progress)

        self.ffmpeg_uninstall_btn = QPushButton("Remove")
        self.ffmpeg_uninstall_btn.setProperty("role", "ghost")
        self.ffmpeg_uninstall_btn.clicked.connect(self._uninstall_ffmpeg)
        self.ffmpeg_install_btn = QPushButton("Install FFmpeg")
        self.ffmpeg_install_btn.setProperty("role", "primary")
        self.ffmpeg_install_btn.clicked.connect(self.start_ffmpeg_install)
        self.ffmpeg_card.layout().addWidget(
            self._row(
                ["stretch", self.ffmpeg_uninstall_btn, self.ffmpeg_install_btn]
            )
        )
        self._refresh_ffmpeg_status()

        root.addWidget(self.ffmpeg_card)

        # ---- App update ----------------------------------------------
        self.update_card = self._make_card("APP UPDATES")
        self.update_status = QLabel(f"Convertr v{__version__}")
        self.update_status.setWordWrap(True)
        self.update_card.layout().addWidget(self.update_status)

        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_card.layout().addWidget(self.update_progress)

        self.auto_update_check = QCheckBox("Check for updates automatically on launch")
        self.auto_update_check.setChecked(s.auto_check_updates)
        self.auto_update_check.toggled.connect(self._save_auto_update)
        self.update_btn = QPushButton("Check for updates")
        self.update_btn.clicked.connect(self._check_updates_manual)
        self.update_card.layout().addWidget(
            self._row([self.auto_update_check, "stretch", self.update_btn])
        )
        root.addWidget(self.update_card)

        # ---- Behavior -------------------------------------------------
        behavior_card = self._make_card("BEHAVIOR")
        self.tray_check = QCheckBox("Minimize to system tray instead of closing")
        self.tray_check.setChecked(s.minimize_to_tray)
        self.tray_check.toggled.connect(self._save_tray)
        behavior_card.layout().addWidget(self.tray_check)

        self.notify_check = QCheckBox("Show a notification when a batch finishes")
        self.notify_check.setChecked(s.notify_on_complete)
        self.notify_check.toggled.connect(self._save_notify)
        behavior_card.layout().addWidget(self.notify_check)
        root.addWidget(behavior_card)

        root.addStretch()

    # ---- helpers ---------------------------------------------------------

    def _make_card(self, section_label: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)
        title = QLabel(section_label)
        title.setProperty("role", "section")
        title.setStyleSheet(
            "color: #9aa0a6; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;"
        )
        v.addWidget(title)
        return card

    def _row(self, items) -> QWidget:
        """Wrap an horizontal arrangement in a real QWidget.

        Without this, ``QVBoxLayout.addLayout(QHBoxLayout)`` doesn't propagate
        size hints from styled inner widgets correctly — at high DPI / under
        custom QSS, rows can collapse and overlap their neighbors. Wrapping
        in a QWidget gives the parent vbox a real geometry to measure.

        ``items`` is a list whose entries are either:
          * a widget (added with stretch=0)
          * a (widget, stretch) tuple
          * the string ``"stretch"`` to insert ``addStretch()``
        """
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(wrapper)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        max_child_h = 0
        for item in items:
            if item == "stretch":
                h.addStretch()
                continue
            if isinstance(item, tuple):
                widget, stretch = item
                h.addWidget(widget, stretch)
            else:
                widget = item
                h.addWidget(widget)
            # Track the tallest child so we can pin the wrapper's minimum
            # height. Without this, the parent vbox routinely squashes the
            # wrapper to 16 px and clips styled buttons / combo boxes.
            sh = widget.sizeHint().height()
            if sh > max_child_h:
                max_child_h = sh

        if max_child_h > 0:
            wrapper.setMinimumHeight(max_child_h)
        return wrapper

    # ---- output ----------------------------------------------------------

    def _browse_output(self) -> None:
        start = self.output_edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Choose output folder", start)
        if chosen:
            self.output_edit.setText(chosen)
            self._save_output()

    def _clear_output(self) -> None:
        self.output_edit.setText("")
        self._save_output()

    def _save_output(self) -> None:
        self._window.settings.output_folder = self.output_edit.text().strip()
        self._window.settings.save()

    # ---- conversion settings --------------------------------------------

    def _save_mode(self) -> None:
        self._window.settings.mode = self.mode_combo.currentData()
        self._window.settings.save()

    def _save_overwrite(self, checked: bool) -> None:
        self._window.settings.overwrite = checked
        self._window.settings.save()

    # ---- behavior toggles ------------------------------------------------

    def _save_auto_update(self, checked: bool) -> None:
        self._window.settings.auto_check_updates = checked
        self._window.settings.save()

    def _save_tray(self, checked: bool) -> None:
        self._window.settings.minimize_to_tray = checked
        self._window.settings.save()

    def _save_notify(self, checked: bool) -> None:
        self._window.settings.notify_on_complete = checked
        self._window.settings.save()

    # ---- FFmpeg --------------------------------------------------------

    def _refresh_ffmpeg_status(self) -> None:
        if ffmpeg_installer.is_installed():
            v = ffmpeg_installer.installed_version() or "unknown"
            self.ffmpeg_status.setText(
                f"<span style='color:#5fd068;'>✓ Installed</span><br>"
                f"<span style='color:#9aa0a6;'>Version {v} · "
                f"{ffmpeg_installer.ffmpeg_dir()}</span>"
            )
            self.ffmpeg_install_btn.setText("Reinstall")
            self.ffmpeg_uninstall_btn.setVisible(True)
        else:
            self.ffmpeg_status.setText(
                "<span style='color:#ef5b5b;'>Not installed</span><br>"
                "<span style='color:#9aa0a6;'>Convertr needs FFmpeg to run "
                "conversions. About 90 MB.</span>"
            )
            self.ffmpeg_install_btn.setText("Install FFmpeg")
            self.ffmpeg_uninstall_btn.setVisible(False)

    def start_ffmpeg_install(self) -> None:
        if self._ffmpeg_worker and self._ffmpeg_worker.isRunning():
            return
        self.ffmpeg_install_btn.setEnabled(False)
        self.ffmpeg_uninstall_btn.setEnabled(False)
        self.ffmpeg_progress.setVisible(True)
        self.ffmpeg_progress.setRange(0, 0)  # indeterminate until headers arrive
        self.ffmpeg_status.setText("Downloading FFmpeg…")

        self._ffmpeg_worker = FFmpegInstallWorker()
        self._ffmpeg_worker.progress.connect(self._on_ffmpeg_progress)
        self._ffmpeg_worker.finished_ok.connect(self._on_ffmpeg_done)
        self._ffmpeg_worker.failed.connect(self._on_ffmpeg_failed)
        self._ffmpeg_worker.start()

    def _on_ffmpeg_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self.ffmpeg_progress.setRange(0, 100)
            self.ffmpeg_progress.setValue(int(downloaded * 100 / total))
            self.ffmpeg_status.setText(
                f"Downloading FFmpeg — {_format_bytes(downloaded)} / {_format_bytes(total)}"
            )

    def _on_ffmpeg_done(self) -> None:
        self.ffmpeg_progress.setVisible(False)
        self.ffmpeg_install_btn.setEnabled(True)
        self.ffmpeg_uninstall_btn.setEnabled(True)
        self._refresh_ffmpeg_status()

    def _on_ffmpeg_failed(self, message: str) -> None:
        self.ffmpeg_progress.setVisible(False)
        self.ffmpeg_install_btn.setEnabled(True)
        self.ffmpeg_uninstall_btn.setEnabled(True)
        QMessageBox.warning(self, "FFmpeg install failed", message)
        self._refresh_ffmpeg_status()

    def _uninstall_ffmpeg(self) -> None:
        if QMessageBox.question(
            self, "Remove FFmpeg",
            "Remove the FFmpeg install? You'll need to reinstall to convert files.",
        ) == QMessageBox.StandardButton.Yes:
            ffmpeg_installer.uninstall()
            self._refresh_ffmpeg_status()

    # ---- app updates ----------------------------------------------------

    def _check_updates_manual(self) -> None:
        self.update_btn.setEnabled(False)
        self.update_status.setText("Checking for updates…")
        self._check_worker = UpdateCheckWorker()
        self._check_worker.update_available.connect(self._on_update_available_manual)
        self._check_worker.no_update.connect(self._on_no_update_manual)
        self._check_worker.error.connect(self._on_update_error_manual)
        self._check_worker.start()

    def _on_update_available_manual(self, info) -> None:
        self.update_btn.setEnabled(True)
        self._offer_update(info)

    def _on_no_update_manual(self) -> None:
        self.update_btn.setEnabled(True)
        self.update_status.setText(
            f"Convertr v{__version__} — you're on the latest version."
        )

    def _on_update_error_manual(self, msg: str) -> None:
        self.update_btn.setEnabled(True)
        self.update_status.setText(
            f"Convertr v{__version__} — update check failed: {msg}"
        )

    def _offer_update(self, info) -> None:
        self.update_status.setText(
            f"<b>Update available:</b> v{info.version}<br>"
            f"<span style='color:#9aa0a6;'>Currently running v{__version__}</span>"
        )
        if not info.installer_url:
            self.update_status.setText(
                self.update_status.text()
                + "<br><span style='color:#ef5b5b;'>No installer in this release.</span>"
            )
            return
        ans = QMessageBox.question(
            self,
            "Update available",
            f"Convertr v{info.version} is available.\n\nDownload and install now?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.update_progress.setVisible(True)
        self.update_progress.setRange(0, 100)
        self._update_dl_worker = UpdateDownloadWorker(info)
        self._update_dl_worker.progress.connect(self._on_update_dl_progress)
        self._update_dl_worker.finished_ok.connect(self._on_update_dl_done)
        self._update_dl_worker.failed.connect(self._on_update_dl_failed)
        self._update_dl_worker.start()

    def _on_update_dl_progress(self, d: int, t: int) -> None:
        if t > 0:
            self.update_progress.setValue(int(d * 100 / t))

    def _on_update_dl_done(self, installer_path) -> None:
        from ..core import updater as updater_mod
        self.update_progress.setVisible(False)
        QMessageBox.information(
            self, "Updating",
            "The installer will now run. Convertr will close, update, and "
            "you can reopen it when the installer finishes.",
        )
        updater_mod.run_installer_and_exit(installer_path)

    def _on_update_dl_failed(self, msg: str) -> None:
        self.update_progress.setVisible(False)
        QMessageBox.warning(self, "Update failed", msg)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()

        self.setWindowTitle(f"{__app_name__}")
        self.setMinimumSize(720, 540)
        self.resize(900, 680)

        # Icon for window + taskbar.
        icon_path = resource_path("resources", "icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Central widget with header + tabs.
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header strip with logo.
        header = QFrame()
        header.setStyleSheet("background-color: #15181c; border-bottom: 1px solid #2a2f37;")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 8, 20, 8)
        h_layout.setSpacing(12)

        logo_path = resource_path("resources", "logo.png")
        if logo_path.exists():
            logo_label = QLabel()
            pix = QPixmap(str(logo_path))
            # Scale logo to a sensible header height while keeping aspect.
            pix = pix.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
            h_layout.addWidget(logo_label)
        else:
            fallback = QLabel(__app_name__)
            fallback.setStyleSheet("font-size: 20px; font-weight: 700; color: #ffffff;")
            h_layout.addWidget(fallback)

        h_layout.addStretch()
        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet("color: #5a6068; font-size: 11px;")
        h_layout.addWidget(version_label)
        layout.addWidget(header)

        # Update banner (hidden until check finds something).
        self.update_banner = QFrame()
        self.update_banner.setObjectName("update_banner")
        self.update_banner.setVisible(False)
        ub = QHBoxLayout(self.update_banner)
        ub.setContentsMargins(16, 10, 16, 10)
        ub.setSpacing(10)
        self.update_banner_label = QLabel("")
        self.update_banner_label.setStyleSheet("color: #c8e6c9; font-size: 13px;")
        ub.addWidget(self.update_banner_label, 1)
        update_now_btn = QPushButton("Update")
        update_now_btn.setProperty("role", "primary")
        update_now_btn.clicked.connect(self._open_settings_for_update)
        dismiss_btn = QPushButton("Later")
        dismiss_btn.setProperty("role", "ghost")
        dismiss_btn.clicked.connect(lambda: self.update_banner.setVisible(False))
        ub.addWidget(update_now_btn)
        ub.addWidget(dismiss_btn)

        banner_wrap = QWidget()
        bw = QVBoxLayout(banner_wrap)
        bw.setContentsMargins(20, 10, 20, 0)
        bw.addWidget(self.update_banner)
        layout.addWidget(banner_wrap)

        # Tabs.
        self.tabs = QTabWidget()
        self.convert_tab = ConvertTab(self)
        self.history_tab = HistoryTab(self)
        self.settings_tab = SettingsTab(self)
        self.tabs.addTab(self.convert_tab, "Convert")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.settings_tab, "Settings")
        layout.addWidget(self.tabs, 1)

        # Status bar.
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)
        sb.showMessage("Ready")

        # System tray.
        self.tray: Optional[QSystemTrayIcon] = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._setup_tray()

        # Silent update check on startup (if enabled).
        self._latest_release = None
        if self.settings.auto_check_updates:
            QTimer.singleShot(800, self._silent_update_check)

    # ---- update banner --------------------------------------------------

    def _silent_update_check(self) -> None:
        self._update_check_worker = UpdateCheckWorker()
        self._update_check_worker.update_available.connect(self._show_update_banner)
        self._update_check_worker.start()

    def _show_update_banner(self, info) -> None:
        self._latest_release = info
        self.update_banner_label.setText(
            f"Convertr v{info.version} is available — you're on v{__version__}."
        )
        self.update_banner.setVisible(True)

    def _open_settings_for_update(self) -> None:
        self.update_banner.setVisible(False)
        self.tabs.setCurrentIndex(2)
        if self._latest_release:
            self.settings_tab._offer_update(self._latest_release)

    # ---- tray -----------------------------------------------------------

    def _setup_tray(self) -> None:
        icon_path = resource_path("resources", "icon.png")
        icon = QIcon(str(icon_path)) if icon_path.exists() else self.windowIcon()
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip(__app_name__)

        menu = QMenu()
        show_action = QAction("Open Convertr", self)
        show_action.triggered.connect(self._show_from_tray)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    # ---- close behavior -------------------------------------------------

    def closeEvent(self, event) -> None:
        # Minimize to tray if enabled and tray is available; otherwise quit.
        if (self.settings.minimize_to_tray and self.tray
                and self.tray.isVisible()):
            event.ignore()
            self.hide()
            self.tray.showMessage(
                __app_name__,
                "Convertr is still running in the tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            event.accept()
