<div align="center">

# Convertr

### Fast, clean file conversion for Windows

Convertr is a modern Windows desktop app for converting video and audio files while keeping the original source details intact whenever possible.

[Download the latest release](https://github.com/NemohhTv/Convertr/releases/latest)

</div>

---

## Downloads

The release page provides two Windows installers:

| Installer | What it does |
|---|---|
| `Convertr-Setup-v2.2.1.exe` | Installs the Convertr desktop app |
| `Convertr-FFmpeg-Setup-v2.2.1.exe` | Installs FFmpeg locally for Convertr |

Install Convertr first. Then either install FFmpeg from inside the app through **Settings**, or download and run the standalone FFmpeg installer from the release page.

## Why Convertr?

Convertr is built for quick format changes without wrecking quality. When a file can be repackaged instead of re-encoded, Convertr uses **Smart Fast Mode** to remux the file, which is dramatically faster than a full conversion.

For example, an MKV with compatible H.264 video and AAC audio can be changed to MP4 without re-encoding the video.

## Features

- Sleek dark Windows desktop UI
- Simple installer EXE from GitHub Releases
- Separate FFmpeg installer EXE from GitHub Releases
- No command prompt window when running the installed app
- Batch convert multiple files at once
- Built-in FFmpeg installer and updater
- Built-in app updater from GitHub Releases
- Smart Fast Mode for near-instant remuxing when possible
- Maximum Compatibility Mode for safer conversions
- Optional custom output folder
- Preserves source resolution, aspect ratio, frame rate, and metadata where supported

## Supported outputs

| Type | Formats |
|---|---|
| Video | MP4, MKV, MOV, WEBM |
| Audio | M4A, AAC, MP3, WAV, FLAC |

## Conversion modes

### Smart Fast

Default mode. Best for speed.

Smart Fast tries to avoid re-encoding:

- Copies compatible video streams
- Copies compatible audio streams
- Converts only the audio when video can stay untouched
- Uses full conversion only when the source codec requires it

### Maximum Compatibility

Best when you need files that work broadly across players, editors, and devices. This mode uses safer encoding choices, but it can take longer.

## Installation

1. Open the [latest release](https://github.com/NemohhTv/Convertr/releases/latest)
2. Download `Convertr-Setup-v2.2.1.exe`
3. Run the installer
4. Open Convertr
5. Install FFmpeg from **Settings**, or run `Convertr-FFmpeg-Setup-v2.2.1.exe`

FFmpeg installs locally for Convertr. You do not need to set up system PATH.

## Updating

Inside Convertr:

1. Open **Settings**
2. Click **Check / Install App Update**
3. Convertr downloads the newest GitHub Release and starts the installer

## Build from source

Requirements:

- Windows
- Python 3.11+
- Inno Setup, only needed for installer builds

Install dependencies:

```bat
install_python_requirements.bat
```

Build the app EXE:

```bat
build_windows_exe.bat
```

The app EXE will be created in:

```text
dist\Convertr.exe
```

## Release process

GitHub Actions builds both installers and publishes them on the release page:

```text
Convertr-Setup-v2.2.1.exe
Convertr-FFmpeg-Setup-v2.2.1.exe
```

---

<div align="center">

Made for fast, no-fuss media conversion.

</div>
