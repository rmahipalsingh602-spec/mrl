; ==========================================
; MRL Official Installer
; Multi Runtime Language
; ==========================================

#define ProductName "MRL"
#define ProductDisplayName "MRL - Multi Runtime Language"
#define PublisherName "Mr. Rathore"
#ifndef ReleaseVersion
  #define ReleaseVersion "3.1.0"
#endif
#ifndef ReleaseVersionQuad
  #define ReleaseVersionQuad "3.1.0.0"
#endif
#ifndef OutputBaseName
  #define OutputBaseName "mrl-windows-x64-setup"
#endif

[Setup]
AppId={{8A8F3B77-D8D8-4384-93F3-4A6A48069544}
AppName={#ProductDisplayName}
AppVersion={#ReleaseVersion}
AppPublisher={#PublisherName}
DefaultDirName={commonpf64}\MRL
DefaultGroupName=MRL
OutputDir=output
OutputBaseFilename={#OutputBaseName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes
ChangesAssociations=yes
SetupIconFile=build_assets\mrl.ico
UninstallDisplayIcon={app}\mrl.exe
VersionInfoCompany={#PublisherName}
VersionInfoDescription=MRL Windows Setup
VersionInfoVersion={#ReleaseVersionQuad}
VersionInfoTextVersion={#ReleaseVersion}
VersionInfoProductName={#ProductName}
VersionInfoProductVersion={#ReleaseVersion}
VersionInfoProductTextVersion={#ReleaseVersion}
VersionInfoOriginalFileName={#OutputBaseName}.exe

[Files]
Source: "dist\mrl.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MRL"; Filename: "{app}\mrl.exe"
Name: "{group}\Uninstall MRL"; Filename: "{uninstallexe}"

[Registry]
Root: HKCR; Subkey: ".mrl"; ValueType: string; ValueName: ""; ValueData: "MRLFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: ".hi"; ValueType: string; ValueName: ""; ValueData: "MRLFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "MRLFile"; ValueType: string; ValueName: ""; ValueData: "MRL Source File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "MRLFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\mrl.exe,0"
Root: HKCR; Subkey: "MRLFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\mrl.exe"" ""%1"""
Root: HKCR; Subkey: "MRLFile\shell\edit"; ValueType: string; ValueName: ""; ValueData: "Open in VS Code"
Root: HKCR; Subkey: "MRLFile\shell\edit\command"; ValueType: string; ValueName: ""; ValueData: """{cmd}"" /c code ""%1"""
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}')); Tasks: addtopath

[Tasks]
Name: "addtopath"; Description: "Add MRL to system PATH"; GroupDescription: "Additional tasks:"

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  PathValue: string;
begin
  if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', PathValue) then
  begin
    Result := True;
    exit;
  end;

  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(PathValue) + ';') = 0;
end;
