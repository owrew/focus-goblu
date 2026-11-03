#define AppVersion "0.3.0"
#define ProductName "Focus Goblin"

[Setup]
AppId={{36A479F4-282B-41CD-A69D-5B99FAC057A5}
AppName={#ProductName}
AppVersion={#AppVersion}
AppPublisher=Focus Goblin local project
DefaultDirName={localappdata}\Programs\FocusGoblin
DefaultGroupName={#ProductName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer
OutputBaseFilename=FocusGoblin-Setup-{#AppVersion}
SetupIconFile=..\focus_goblin\assets\goblin.ico
UninstallDisplayIcon={app}\FocusGoblin.exe
WizardStyle=modern
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
DisableProgramGroupPage=yes

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
Name: startup; Description: "Start the desktop pet at sign-in (camera stays off)"; Flags: unchecked

[Files]
Source: "..\dist\FocusGoblin-v0.3\FocusGoblin-v0.3.exe"; DestDir: "{app}"; DestName: "FocusGoblin.exe"; Flags: ignoreversion
Source: "..\dist\FocusGoblin-v0.3\*"; DestDir: "{app}"; Excludes: "FocusGoblin-v0.3.exe"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Focus Goblin"; Filename: "{app}\FocusGoblin.exe"
Name: "{autodesktop}\Focus Goblin"; Filename: "{app}\FocusGoblin.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FocusGoblin"; ValueData: """{app}\FocusGoblin.exe"" --pet-only"; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\FocusGoblin.exe"; Description: "Open Focus Goblin"; Flags: nowait postinstall skipifsilent

; User analytics/settings under LocalAppData\FocusGoblin are deliberately preserved.
