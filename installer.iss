[Setup]
AppName=AITranslator
AppVersion=10.0
DefaultDirName={autopf}\AITranslator
DefaultGroupName=AITranslator
OutputDir=D:\chrom\screenshot\AITranslator\Output
OutputBaseFilename=AITranslator_Setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=D:\chrom\screenshot\AITranslator\EXEimage.ico
UninstallDisplayIcon={app}\AITranslator.exe
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "D:\chrom\screenshot\AITranslator\dist\AITranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "D:\chrom\screenshot\AITranslator\vcredist_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall


[Icons]
Name: "{group}\AITranslator"; Filename: "{app}\AITranslator.exe"
Name: "{autodesktop}\AITranslator"; Filename: "{app}\AITranslator.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vcredist_x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated
Filename: "{app}\AITranslator.exe"; Description: "{cm:LaunchProgram,AITranslator}"; Flags: nowait postinstall skipifsilent runasoriginaluser
