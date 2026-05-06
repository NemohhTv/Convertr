#define MyAppName "Convertr"
#define MyAppVersion GetEnv('CONVERTR_VERSION')
#if MyAppVersion == ""
#define MyAppVersion "2.2.0"
#endif
#define MyAppPublisher "NemohhTv"
#define MyAppExeName "Convertr.exe"

[Setup]
AppId={{8C9C6A2E-0F41-4C7B-9E61-CONVERTR001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer-output
OutputBaseFilename=Convertr-Setup
SetupIconFile=
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\Convertr.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Convertr"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Convertr"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Convertr"; Flags: nowait postinstall skipifsilent
