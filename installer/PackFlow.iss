; PackFlow installer (Inno Setup 6). A normal Windows installer, no questions about servers or databases.
; Build: run build.bat first (creates dist\PackFlow), then build_installer.bat -> installer\Output\PackFlow-Setup.exe
; Silent install: PackFlow-Setup.exe /VERYSILENT
; User data lives in %APPDATA%\PackFlow and is never touched by installing, updating or uninstalling.
#define AppName "PackFlow"
#define AppVersion "2.0"

[Setup]
AppId={{6C1F6E0A-6D3B-4F0B-9B7B-4D5C3F1A2E10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Factory IT
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=PackFlow-Setup
SetupIconFile=..\resources\icon.ico
UninstallDisplayIcon={app}\PackFlow.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Installs for the current user without administrator rights; the dialog lets an administrator install for all users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
CloseApplications=yes
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\PackFlow\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PackFlow.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\PackFlow.exe"

[Run]
Filename: "{app}\PackFlow.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
