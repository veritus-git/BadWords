; --- DEFINITIONS ---
#define MyAppName "BadWords"
#define MyAppVersion "2.0"
#define MyAppPublisher "Szymon Wolarz"
#define MyAppExeName "main.py"

; URLs
#define PythonUrl "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe"
#define FFmpegUrl "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

; Include IDP (Must be installed in Inno Setup)
#include <idp.iss>

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; ZMIANA: Instalacja na poziomie uzytkownika (AppData), bez Admina
PrivilegesRequired=lowest
OutputBaseFilename=BadWords Setup {#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[CustomMessages]
english.GpuDesc=Version with NVIDIA GPU acceleration (Recommended)
english.CpuDesc=CPU Version (Slower, compatible)
english.CompCore=Core program files
english.CompNvidia=NVIDIA support libraries
english.StatusPython=Installing Python environment (required)...
english.StatusConfig=Configuring venv and AI libraries (this may take a while)...
english.ErrResolve=Could not find DaVinci Resolve scripts folder.
english.ErrConfig=Configuration failed (setup_windows.bat). Error code: %1

polish.GpuDesc=Wersja z akceleracją NVIDIA GPU (Zalecane)
polish.CpuDesc=Wersja CPU (Wolniejsza, kompatybilna)
polish.CompCore=Główne pliki programu
polish.CompNvidia=Biblioteki wsparcia NVIDIA
polish.StatusPython=Instalowanie środowiska Python (wymagane)...
polish.StatusConfig=Konfiguracja venv i bibliotek AI (to może chwilę potrwać)...
polish.ErrResolve=Nie można znaleźć folderu skryptów DaVinci Resolve.
polish.ErrConfig=Błąd konfiguracji (setup_windows.bat). Kod błędu: %1

; (Pozostałe języki skrócone dla czytelności, zachowaj je w pliku wynikowym)
german.GpuDesc=Version mit NVIDIA GPU-Beschleunigung (Empfohlen)
german.CpuDesc=CPU-Version (Langsamer, kompatibel)
german.CompCore=Hauptprogrammdateien
german.CompNvidia=NVIDIA-Unterstützungsbibliotheken
german.StatusPython=Installiere Python-Umgebung (erforderlich)...
german.StatusConfig=Konfiguriere venv und AI-Bibliotheken...
german.ErrResolve=DaVinci Resolve Skript-Ordner nicht gefunden.
german.ErrConfig=Konfigurationsfehler. Fehlercode: %1

spanish.GpuDesc=Versión con aceleración NVIDIA GPU
spanish.CpuDesc=Versión CPU
spanish.CompCore=Archivos principales
spanish.CompNvidia=Bibliotecas NVIDIA
spanish.StatusPython=Instalando Python...
spanish.StatusConfig=Configurando venv...
spanish.ErrResolve=No se encontró carpeta de scripts.
spanish.ErrConfig=Error de configuración: %1

french.GpuDesc=Version avec accélération GPU NVIDIA
french.CpuDesc=Version CPU
french.CompCore=Fichiers principaux
french.CompNvidia=Bibliothèques NVIDIA
french.StatusPython=Installation Python...
french.StatusConfig=Configuration venv...
french.ErrResolve=Dossier scripts introuvable.
french.ErrConfig=Erreur de configuration : %1

italian.GpuDesc=Versione con accelerazione GPU NVIDIA
italian.CpuDesc=Versione CPU
italian.CompCore=File principali
italian.CompNvidia=Librerie NVIDIA
italian.StatusPython=Installazione Python...
italian.StatusConfig=Configurazione venv...
italian.ErrResolve=Cartella script non trovata.
italian.ErrConfig=Errore configurazione: %1

portuguese.GpuDesc=Versão com aceleração NVIDIA GPU
portuguese.CpuDesc=Versão CPU
portuguese.CompCore=Arquivos principais
portuguese.CompNvidia=Bibliotecas NVIDIA
portuguese.StatusPython=Instalando Python...
portuguese.StatusConfig=Configurando venv...
portuguese.ErrResolve=Pasta de scripts não encontrada.
portuguese.ErrConfig=Erro na configuração: %1

dutch.GpuDesc=Versie met NVIDIA GPU-versnelling
dutch.CpuDesc=CPU-versie
dutch.CompCore=Kernbestanden
dutch.CompNvidia=NVIDIA-bibliotheken
dutch.StatusPython=Python installeren...
dutch.StatusConfig=Venv configureren...
dutch.ErrResolve=Scripts map niet gevonden.
dutch.ErrConfig=Configuratiefout: %1

russian.GpuDesc=Версия с ускорением NVIDIA GPU
russian.CpuDesc=Версия CPU
russian.CompCore=Основные файлы
russian.CompNvidia=Библиотеки NVIDIA
russian.StatusPython=Установка Python...
russian.StatusConfig=Настройка venv...
russian.ErrResolve=Папка скриптов не найдена.
russian.ErrConfig=Ошибка конфигурации: %1

ukrainian.GpuDesc=Версія з прискоренням NVIDIA GPU
ukrainian.CpuDesc=Версія CPU
ukrainian.CompCore=Основні файли
ukrainian.CompNvidia=Бібліотеки NVIDIA
ukrainian.StatusPython=Встановлення Python...
ukrainian.StatusConfig=Налаштування venv...
ukrainian.ErrResolve=Папка скриптів не знайдена.
ukrainian.ErrConfig=Помилка конфігурації: %1

[Types]
Name: "gpu"; Description: "{cm:GpuDesc}"
Name: "cpu"; Description: "{cm:CpuDesc}"

[Components]
Name: "core"; Description: "{cm:CompCore}"; Types: gpu cpu; Flags: fixed
Name: "nvidia"; Description: "{cm:CompNvidia}"; Types: gpu

[Files]
; Source Code
Source: "src\*.py"; DestDir: "{app}"; Flags: ignoreversion
; Config Script
Source: "setup_windows.bat"; DestDir: "{app}"; Flags: ignoreversion
; Note: FFmpeg is NOT bundled here, it's downloaded via IDP

[Dirs]
Name: "{app}\bin"
Name: "{app}\models"
Name: "{app}\libs"

[Run]
; ZMIANA: Usunięto "InstallAllUsers=1", dodano "PrependPath=1"
; To instaluje Pythona w AppData i dodaje go do PATH uzytkownika
Filename: "{tmp}\python_setup.exe"; Parameters: "/quiet PrependPath=1 Include_test=0"; StatusMsg: "{cm:StatusPython}"; Check: FileExists(ExpandConstant('{tmp}\python_setup.exe')); Flags: waituntilterminated

[Code]
var
  ResolveScriptDir: String;
  PythonNeeded: Boolean;

function NeedsPythonInstallation(): Boolean;
var
  v10, v11, v12: Boolean;
begin
  // Sprawdzamy glownie HKCU (Current User) bo instalujemy jako user
  v10 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.10\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath');
  v11 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.11\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath');
  v12 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.12\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath');
  
  if v10 or v11 or v12 then
  begin
    Log('Compatible Python found.');
    Result := False;
  end
  else
  begin
    Log('Compatible Python not found. Download required.');
    Result := True;
  end;
end;

procedure InitializeWizard;
begin
  idpDownloadAfter(wpReady);
  
  PythonNeeded := NeedsPythonInstallation();
  if PythonNeeded then
  begin
    idpAddFile('{#PythonUrl}', ExpandConstant('{tmp}\python_setup.exe'));
  end;

  idpAddFile('{#FFmpegUrl}', ExpandConstant('{tmp}\ffmpeg.zip'));
end;

function GetResolveScriptDir(Param: String): String;
begin
  Result := ExpandConstant('{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility');
  if not DirExists(Result) then
  begin
    ForceDirectories(Result);
  end;
end;

procedure GenerateResolveWrapper;
var
  WrapperPath: String;
  Lines: TArrayOfString;
  AppDir: String;
begin
  ResolveScriptDir := GetResolveScriptDir('');
  
  if not DirExists(ResolveScriptDir) then
  begin
    Log('Resolve Script Dir not found.');
    Exit;
  end;

  AppDir := ExpandConstant('{app}');
  StringChange(AppDir, '\', '\\');
  
  WrapperPath := ResolveScriptDir + '\BadWords.py';
  
  SetArrayLength(Lines, 20);
  Lines[0] := 'import sys';
  Lines[1] := 'import os';
  Lines[2] := 'import traceback';
  Lines[3] := '';
  Lines[4] := 'INSTALL_DIR = r"' + AppDir + '"';
  Lines[5] := 'LIBS_DIR = os.path.join(INSTALL_DIR, "libs")';
  Lines[6] := 'MAIN_SCRIPT = os.path.join(INSTALL_DIR, "main.py")';
  Lines[7] := '';
  Lines[8] := 'if os.path.exists(LIBS_DIR):';
  Lines[9] := '    if LIBS_DIR not in sys.path:';
  Lines[10] := '        sys.path.insert(0, LIBS_DIR)';
  Lines[11] := '';
  Lines[12] := 'if INSTALL_DIR not in sys.path:';
  Lines[13] := '    sys.path.append(INSTALL_DIR)';
  Lines[14] := '';
  Lines[15] := 'if os.path.exists(MAIN_SCRIPT):';
  Lines[16] := '    try:';
  Lines[17] := '        with open(MAIN_SCRIPT, "r", encoding="utf-8") as f:';
  Lines[18] := '            exec(f.read(), globals())';
  Lines[19] := '    except Exception as e: print(e)';
  
  SaveStringsToFile(WrapperPath, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  GpuFlag: String;
  FFmpegZip: String;
begin
  if CurStep = ssPostInstall then
  begin
    GenerateResolveWrapper();
    
    if IsComponentSelected('nvidia') then GpuFlag := '1' else GpuFlag := '0';
    
    FFmpegZip := ExpandConstant('{tmp}\ffmpeg.zip');
      
    WizardForm.StatusLabel.Caption := CustomMessage('StatusConfig');
    
    // Run setup_windows.bat
    if not Exec(ExpandConstant('{app}\setup_windows.bat'), 
                '"' + ExpandConstant('{app}') + '" "' + GpuFlag + '" "' + FFmpegZip + '"', 
                '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox(FmtMessage(CustomMessage('ErrConfig'), [IntToStr(ResultCode)]), mbError, MB_OK);
    end;
  end;
end;