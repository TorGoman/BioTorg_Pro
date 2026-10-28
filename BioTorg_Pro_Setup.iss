; Script generated for BioTorg Pro by Ahmed TorGoman
#define MyAppName "BioTorg Pro"
#define MyAppVersion "2.2.1"
#define MyAppPublisher "Ahmed TorGoman"
#define MyAppContact "@torgoman0"
#define MyAppExeName "BioTorg_Pro.exe"

[Setup]
AppId={{D374092E-8E5A-4B69-A118-B54929D3A891}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/TorGoman/BioTorg_Pro
AppSupportURL=https://t.me/torgoman0
AppUpdatesURL=https://github.com/TorGoman/BioTorg_Pro/releases
DefaultDirName={localappdata}\Programs\BioTorg_Pro
DisableProgramGroupPage=yes
OutputDir=dist_installer
OutputBaseFilename=BioTorg_Pro_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; الملفات الأساسية والمكتبات البرمجية
Source: "dist\BioTorg_Pro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "attendance_config.json,attendance_adjustments.json"
; ملفات الإعدادات والبيانات لا يتم استبدالها في حال كانت موجودة مسبقاً لحماية بيانات المستخدم
Source: "attendance_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "attendance_adjustments.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
