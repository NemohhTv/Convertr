"""Application entry point.

Run this directly during development::

    python -m convertr.app

PyInstaller wraps this same module into ``Convertr.exe``.

We set High-DPI rounding policy *before* QApplication is constructed so the
window scales cleanly on monitors with non-integer DPI factors (125%, 150%).
"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from . import __app_name__
from .core.paths import resource_path
from .ui.main_window import MainWindow
from .ui.theme import STYLESHEET


def main() -> int:
    # High-DPI support: render at native pixel density and use fractional
    # scaling without pixel snapping (otherwise text gets blurry at 125%).
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("Convertr")
    app.setStyle("Fusion")  # consistent baseline before our QSS overrides
    app.setStyleSheet(STYLESHEET)

    # Tray-aware quit handling: don't let the app exit when the last window
    # closes, since we may be hiding to the tray.
    app.setQuitOnLastWindowClosed(False)

    icon_path = resource_path("resources", "icon.png")
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
