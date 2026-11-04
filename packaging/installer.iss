#define AppVersion "0.4.0"
#define ProductName "Focus Goblu"

[Setup]
AppId={{36A479F4-282B-41CD-A69D-5B99FAC057A5}
AppName={#ProductName}
AppVersion={#AppVersion}
AppPublisher=Focus Goblu local project
DefaultDirName={localappdata}\Programs\FocusGoblin
DefaultGroupName={#ProductName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer
OutputBaseFilename=FocusGoblu-Setup-{#AppVersion}
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
Source: "..\dist\FocusGoblu-v0.4\FocusGoblu-v0.4.exe"; DestDir: "{app}"; DestName: "FocusGoblin.exe"; Flags: ignoreversion
Source: "..\dist\FocusGoblu-v0.4\*"; DestDir: "{app}"; Excludes: "FocusGoblu-v0.4.exe"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: files; Name: "{autoprograms}\Focus Goblin.lnk"
Type: files; Name: "{autodesktop}\Focus Goblin.lnk"

[Icons]
Name: "{autoprograms}\Focus Goblu"; Filename: "{app}\FocusGoblin.exe"
Name: "{autodesktop}\Focus Goblu"; Filename: "{app}\FocusGoblin.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FocusGoblin"; ValueData: """{app}\FocusGoblin.exe"" --pet-only"; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\FocusGoblin.exe"; Description: "Open Focus Goblu"; Flags: nowait postinstall skipifsilent

; User analytics/settings under LocalAppData\FocusGoblin are deliberately preserved.
