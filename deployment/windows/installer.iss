#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId=atomic_structure_explorer
AppName=Atomic Structure Explorer
AppVersion={#AppVersion}
AppVerName=Atomic Structure Explorer {#AppVersion}
AppPublisher=Atomic Structure Explorer contributors
DefaultDirName={localappdata}\Programs\Atomic Structure Explorer
DefaultGroupName=Atomic Structure Explorer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\release
OutputBaseFilename=AtomicStructureExplorer-Windows-x64-Setup
SetupIconFile=..\..\build\icons\app-icon.ico
UninstallDisplayIcon={app}\AtomicStructureExplorer.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE

[Files]
Source: "..\..\dist\AtomicStructureExplorer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Atomic Structure Explorer"; Filename: "{app}\AtomicStructureExplorer.exe"
Name: "{autodesktop}\Atomic Structure Explorer"; Filename: "{app}\AtomicStructureExplorer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\AtomicStructureExplorer.exe"; Description: "Launch Atomic Structure Explorer"; Flags: nowait postinstall skipifsilent
