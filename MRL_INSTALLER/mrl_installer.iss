; ================================
; MRL.hi Installer (Windows)
; Author: Mr. Rathore
; ================================

[Setup]
AppName=MRL.hi
AppVersion=1.0
AppPublisher=Mr. Rathore
DefaultDirName={commonpf64}\MRL
DefaultGroupName=MRL.hi
OutputDir=output
OutputBaseFilename=MRL_hi_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\build_assets\mrl.ico
UninstallDisplayIcon={app}\mrl.exe
VersionInfoCompany=Mr. Rathore
VersionInfoDescription=MRL Windows Setup
VersionInfoVersion=3.0.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop icon banaye"; Flags: unchecked
Name: "addpath"; Description: "MRL.hi ko PATH me add kare (recommended)"; Flags: checkedonce

[Files]
Source: "installer_files\mrl.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MRL.hi"; Filename: "{app}\mrl.exe"
Name: "{commondesktop}\MRL.hi"; Filename: "{app}\mrl.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\mrl.exe"; Description: "MRL.hi chalaye"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Tasks: addpath; Flags: preservestringtype
