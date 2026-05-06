# Convertr

Convertr is a sleek Windows desktop app for fast video and audio file conversion while preserving the original source details whenever possible.

## Features

- Modern dark desktop UI
- No command prompt window when using the built EXE
- Built-in Settings window with local FFmpeg install and update
- Batch conversion for multiple files
- Video outputs: MP4, MKV, MOV, WEBM
- Audio outputs: M4A, AAC, MP3, WAV, FLAC
- Smart Fast Mode for near-instant remuxing when codecs are already compatible
- Maximum Compatibility Mode for safer full conversion when needed
- Preserves source resolution, aspect ratio, frame rate, and metadata where supported
- Optional custom output folder

## Conversion modes

### Smart Fast

Smart Fast is the default. It tries to avoid re-encoding whenever possible:

- MP4 with compatible H.264, HEVC, MPEG-4 video gets video stream copy
- Compatible audio is copied when possible
- Incompatible audio is converted to AAC while video is copied
- MKV and MOV use stream copy when possible
- WEBM uses VP9 and Opus when required

### Maximum Compatibility

Maximum Compatibility uses safer encoding choices for files that need broader playback support.

## Run locally

1. Install Python 3.11+
2. Run `install_python_requirements.bat`
3. Launch `run_convertr_windows.vbs`
4. In the app, open **Settings** and click **Install / Update FFmpeg**

## Build EXE

Run:

```bat
build_windows_exe.bat
```

The build will output:

```text
dist\Convertr.exe
```

## GitHub Actions build

Push to `main` and GitHub Actions will build a Windows EXE artifact named `Convertr-Windows-EXE`.
