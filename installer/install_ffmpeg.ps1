$ErrorActionPreference = 'Stop'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Convertr'
if (-not (Test-Path $installRoot)) {
  $installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$binDir = Join-Path $installRoot 'bin'
$tempDir = Join-Path $env:TEMP 'convertr-ffmpeg-install'
$zipPath = Join-Path $tempDir 'ffmpeg.zip'
$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'

if (Test-Path $tempDir) {
  Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
New-Item -ItemType Directory -Path $binDir -Force | Out-Null

Write-Host 'Downloading FFmpeg...'
Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing

Write-Host 'Extracting FFmpeg...'
Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

$ffmpegRoot = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like 'ffmpeg*' } | Select-Object -First 1
if (-not $ffmpegRoot) {
  throw 'Could not find extracted FFmpeg folder.'
}

Copy-Item -Path (Join-Path $ffmpegRoot.FullName 'bin\ffmpeg.exe') -Destination (Join-Path $binDir 'ffmpeg.exe') -Force
Copy-Item -Path (Join-Path $ffmpegRoot.FullName 'bin\ffprobe.exe') -Destination (Join-Path $binDir 'ffprobe.exe') -Force

Remove-Item $tempDir -Recurse -Force
Write-Host 'FFmpeg installed for Convertr.'
