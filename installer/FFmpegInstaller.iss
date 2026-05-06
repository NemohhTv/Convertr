#define MyAppName "Convertr FFmpeg Installer"
#define MyAppVersion GetEnv('CONVERTR_VERSION')
#if MyAppVersion == ""
#define MyAppVersion "2.2.1"
#endif
#define MyAppPublisher "NemohhTv"

[Setup]
AppId={{21B8FA2E-699F-4977-A87E-6E6B9D451111}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Convertr
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=..\installer-output
OutputBaseFilename=Convertr-FFmpeg-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
CloseApplications=no
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "install_ffmpeg.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\install_ffmpeg.ps1"""; StatusMsg: "Downloading and installing FFmpeg for Convertr..."; Flags: runhidden waituntilterminated
