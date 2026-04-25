[Setup]
; --- ALAPADATOK ---
AppId={{B7A5C1D2-E4F5-4A3B-B8C9-D0E1F2A3B4C5}
AppName=ProLog Turatervezo
AppVersion=1.0
DefaultDirName={userlocalappdata}\ProLog_Turatervezo
DefaultGroupName=ProLog Turatervezo
; Ez tiltja le a rendszergazdai jelszót:
PrivilegesRequired=lowest
OutputDir=userdesktop
OutputBaseFilename=Turatervezo_Telepito
SetupIconFile=C:\Users\szilv\Desktop\Python2\Turatervezo-main\szallitas.ico
Compression=lzma
SolidCompression=yes

[Files]
; 1. A fő EXE fájl
Source: "C:\Users\szilv\Desktop\Python2\Turatervezo-main\dist\tervezo_stabil\tervezo_stabil.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. A legfontosabb: A modulokat és könyvtárakat tartalmazó mappa (DestDir végén ott az \_internal!)
Source: "C:\Users\szilv\Desktop\Python2\Turatervezo-main\dist\tervezo_stabil\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; 3. Az ikon és az adatfájlok (ha a mappában vannak)
Source: "C:\Users\szilv\Desktop\Python2\Turatervezo-main\dist\tervezo_stabil\szallitas.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\szilv\Desktop\Python2\Turatervezo-main\dist\tervezo_stabil\*.xlsx"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\szilv\Desktop\Python2\Turatervezo-main\dist\tervezo_stabil\*.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Asztali parancsikon a saját ikonoddal
Name: "{autodesktop}\ProLog Turatervezo"; Filename: "{app}\tervezo_stabil.exe"; IconFilename: "{app}\szallitas.ico"

[Run]
; Telepítés utáni indítás (üzenetek nélkül)
Filename: "{app}\tervezo_stabil.exe"; Description: "Program inditasa"; Flags: nowait postinstall skipifsilent
