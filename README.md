# Convertr

**Fast, clean media conversion for Windows.**

A modern Windows desktop app for converting video and audio files. Built around a "Smart Fast Mode" that remuxes whenever possible — so swapping containers (MKV → MP4, MOV → MP4, etc.) finishes in seconds instead of minutes.

[**Download the latest release**](https://github.com/NemohhTv/Convertr/releases/latest)

---

## Features

- Sleek dark UI with proper High-DPI scaling (no blurry text on 125% / 150% displays)
- **Smart Fast Mode** — remuxes when stream codecs are compatible with the target container, instead of re-encoding
- **Maximum Compatibility Mode** — re-encodes to safe, broadly-supported codecs
- Drag-and-drop files into the window
- Batch convert multiple files at once
- One-click FFmpeg installer in Settings — no PATH setup, no admin rights required for FFmpeg itself
- In-app updater that pulls new releases from GitHub
- System tray support — minimize instead of closing
- Conversion history with double-click to open
- Toast notification when a batch finishes

## Supported formats

| Type | Formats |
| ---- | ------- |
| Video | MP4, MKV, MOV, WEBM |
| Audio | M4A, AAC, MP3, WAV, FLAC |

## Installation

1. Download `Convertr-Setup-vX.Y.Z.exe` from the [latest release](https://github.com/NemohhTv/Convertr/releases/latest)
2. Run the installer (admin prompt — installs to Program Files)
3. Launch Convertr
4. Open **Settings → Install FFmpeg**

FFmpeg installs into `%LOCALAPPDATA%\Convertr\ffmpeg`, isolated from any system FFmpeg.

## Updating

Convertr checks for updates silently when it launches. If a new release is available, a banner appears at the top of the window — click **Update** and the new installer downloads and runs automatically. The running app closes itself before files are replaced.

You can also manually check from **Settings → Check for updates**, or disable auto-checking entirely.

## Build from source

Requirements:

- Windows 10 or later
- Python 3.11+
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (only needed if you want to build the installer)

```bat
:: install dependencies
install_python_requirements.bat

:: run from source
run_convertr_source.bat

:: build the EXE (uses PyInstaller)
build_windows_exe.bat
```

Output: `dist\Convertr\Convertr.exe`

## Releasing a new version

The repo's GitHub Actions workflow builds the installer and publishes a Release automatically when you push a version tag:

```bash
git tag v3.0.1
git push origin v3.0.1
```

`.github/workflows/release.yml` will:

1. Build `Convertr.exe` with PyInstaller on a `windows-latest` runner
2. Package it with Inno Setup into `Convertr-Setup-v3.0.1.exe`
3. Create a GitHub Release and attach the installer

The in-app updater reads from this Release endpoint, so users will see the new version on their next launch.

## How "Smart Fast Mode" works

When you convert a file, Convertr first runs `ffprobe` to read the source's stream codecs. It then checks each stream against a compatibility table for the target container:

- If **all streams** can be copied (e.g. an MKV with H.264 video + AAC audio → MP4), Convertr uses `ffmpeg -c copy`. This is a remux — no re-encoding, near-instant for any file size.
- If **only some streams** can be copied (e.g. MKV with H.264 video + Opus audio → MP4), Convertr copies the compatible streams and re-encodes only the rest.
- If **nothing fits**, Convertr falls back to a full re-encode using H.264 + AAC.

You'll see "Remuxed ✓" or "Converted ✓" in the status column so you know which path was taken.

## Project layout

```
Convertr/
├── app.py                          # entry point (used by source + PyInstaller)
├── Convertr.spec                   # PyInstaller config
├── requirements.txt                # runtime deps
├── requirements-build.txt          # build deps (adds pyinstaller)
├── installer/
│   └── Convertr.iss                # Inno Setup installer script
├── .github/workflows/
│   ├── ci.yml                      # smoke build on every push
│   └── release.yml                 # build + publish installer on tag
└── src/convertr/
    ├── __init__.py                 # version + repo constants
    ├── app.py                      # QApplication entry
    ├── core/
    │   ├── paths.py                # filesystem helpers
    │   ├── settings.py             # JSON settings + history
    │   ├── ffmpeg_installer.py     # download/install portable FFmpeg
    │   ├── converter.py            # ffmpeg invocation + smart-fast logic
    │   └── updater.py              # GitHub Releases updater
    ├── ui/
    │   ├── theme.py                # QSS stylesheet
    │   ├── workers.py              # QThread workers (no UI freezes)
    │   └── main_window.py          # tabs, drag-drop, tray
    └── resources/
        ├── icon.ico                # Windows icon (multi-resolution)
        ├── icon.png                # tray + window icon
        └── logo.png                # header logo
```

---

Made for fast, no-fuss media conversion.
