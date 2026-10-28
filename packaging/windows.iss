#ifndef AppVersion
  #error AppVersion must be provided by build_windows.py
#endif

[Setup]
AppId={{99B5F51C-8A9E-4512-99A0-05C02CD06809}
AppName=ScreenDepresso
AppVersion={#AppVersion}
AppPublisher=ScreenDepresso
AppPublisherURL=https://github.com/NadsonJR/ScreenDepresso
DefaultDirName={localappdata}\Programs\ScreenDepresso
DefaultGroupName=ScreenDepresso
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\dist
OutputBaseFilename=screendepresso_{#AppVersion}_windows_amd64_setup
SetupIconFile=..\build\screendepresso.ico
UninstallDisplayIcon={app}\screendepresso.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=yes
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\screendepresso\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ScreenDepresso"; Filename: "{app}\screendepresso.exe"
Name: "{autodesktop}\ScreenDepresso"; Filename: "{app}\screendepresso.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\screendepresso.exe"; Description: "{cm:LaunchProgram,ScreenDepresso}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\screendepresso.exe"; Flags: nowait runasoriginaluser; Check: RestartAfterUpdate

[Code]
function RestartAfterUpdate: Boolean;
begin
  Result := ExpandConstant('{param:SCREENDEPRESSO_RESTART|0}') = '1';
end;
