; ===========================================================================
; Inno Setup script — Convertr installer
; ---------------------------------------------------------------------------
; Builds Convertr-Setup-v{version}.exe from the PyInstaller output in
; ..\dist\Convertr. The version number can be overridden from the command
; line (the GitHub Actions workflow passes the release tag):
;
;     iscc /DAppVersion=3.0.1 installer\Convertr.iss
;
; Default target: Program Files (per-machine), shortcut on Start Menu and
; (optionally) the Desktop. CloseApplications=force lets the in-app updater
; replace the running EXE without manual intervention.
; ===========================================================================

#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif

#define AppName        "Convertr"
#define AppPublisher   "NemohhTv"
#define AppURL         "https://github.com/NemohhTv/Convertr"
#define AppExeName     "Convertr.exe"

[Setup]
AppId={{B4F1A2C3-7E8D-4D1B-9A6E-3C5D2A8F1234}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=Convertr-Setup-v{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\src\convertr\resources\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
CloseApplications=force
RestartApplications=no
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Pull in everything PyInstaller produced.
Source: "..\dist\Convertr\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Don't touch the user's settings/history/ffmpeg by default — they live in
; %LOCALAPPDATA%\Convertr and many users want to keep them across reinstalls.
; If we ever want to offer "remove all data", we can add a custom page later.
