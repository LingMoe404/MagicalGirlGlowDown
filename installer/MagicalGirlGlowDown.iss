#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#ifndef SourceDir
  #define SourceDir "..\build\package\MagicalGirlGlowDown"
#endif

#ifndef OutputDir
  #define OutputDir "..\build\package"
#endif

#define MyAppName "MagicalGirlGlowDown"
#define MyAppDisplayName "MagicalGirlGlowDown"
#define MyAppExeName "MagicalGirlGlowDown.exe"
#define MyAppPublisher "泠萌404"
#define MyAppURL "https://github.com/LingMoe404/MagicalGirlGlowDown"

[Setup]
AppId={{8E4464EA-D1A2-4D1D-94AD-7E442C76780B}
AppName={#MyAppDisplayName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppDisplayName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\MagicalGirlGlowDown
DefaultGroupName=MagicalGirlGlowDown
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir={#OutputDir}
OutputBaseFilename=MagicalGirlGlowDown-v{#MyAppVersion}-Setup
SetupIconFile=..\src\magical_girl_glow_down\assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start {#MyAppDisplayName} when I sign in"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{sys}\schtasks.exe"; Parameters: "/Create /F /TN ""{#MyAppName}"" /SC ONLOGON /RL HIGHEST /IT /TR """"""{app}\{#MyAppExeName}"""""""; Flags: runhidden waituntilterminated; Tasks: autostart
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppDisplayName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""{#MyAppName}"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveAutostartTask"
