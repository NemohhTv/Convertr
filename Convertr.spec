# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building Convertr.exe.

Build with:
    pyinstaller Convertr.spec

Notes:
  * ``console=False`` -> no command prompt window when launched.
  * ``onedir`` (the default below) is used over ``onefile`` because the
    Inno Setup installer copies the whole directory and then the app starts
    instantly — onefile would extract to a temp dir on every launch.
  * Bundled data: the resources folder (logo + icon) so the running app
    can find ``logo.png`` and ``icon.png`` via ``resource_path()``.
"""
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve()  # noqa: F821  (SPECPATH provided by PyInstaller)

datas = [
    (str(ROOT / "src" / "convertr" / "resources"), "resources"),
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # We don't ship Qt's web stack or QML; cuts ~100 MB off the install.
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Convertr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX trips antivirus heuristics; not worth the size win
    console=False,        # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "src" / "convertr" / "resources" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Convertr",
)
