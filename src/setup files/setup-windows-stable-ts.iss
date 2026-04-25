; --- DEFINITIONS ---
#define MyAppName "BadWords"
#define MyAppVersion "2.0.2"
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
PrivilegesRequired=lowest
OutputBaseFilename=BadWords Setup {#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Ikona instalatora (musi być w formacie .ico w tym samym folderze co skrypt)
SetupIconFile=icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
; --- ENGLISH ---
english.GpuDesc=Version with NVIDIA GPU acceleration (Recommended)
english.CpuDesc=CPU Version (Slower, compatible)
english.CompCore=Core program files
english.CompNvidia=NVIDIA support libraries
english.StatusPython=Installing Python environment (required)...
english.StatusConfig=Configuring venv and AI libraries (this may take a while)...
english.ErrResolve=Could not find DaVinci Resolve scripts folder.
english.ErrConfig=Configuration failed (setup_windows.bat). Error code: %1
english.ModeTitle=Installation Mode
english.ModeDesc=Choose how you want to install BadWords
english.ModeSub=Choose installation type:
english.ModeUpdate=Standard Install/Update - Install or update the app. Keep your settings and models.
english.ModeClean=Repair Installation - Fix bugs by replacing core files. Keep your settings and models.
english.ModeWipe=Complete Reset - Delete absolutely EVERYTHING and install from scratch.

; --- POLISH ---
polish.GpuDesc=Wersja z akceleracją NVIDIA GPU (Zalecane)
polish.CpuDesc=Wersja CPU (Wolniejsza, kompatybilna)
polish.CompCore=Główne pliki programu
polish.CompNvidia=Biblioteki wsparcia NVIDIA
polish.StatusPython=Instalowanie środowiska Python (wymagane)...
polish.StatusConfig=Konfiguracja venv i bibliotek AI (to może chwilę potrwać)...
polish.ErrResolve=Nie można znaleźć folderu skryptów DaVinci Resolve.
polish.ErrConfig=Błąd konfiguracji (setup_windows.bat). Kod błędu: %1
polish.ModeTitle=Tryb Instalacji
polish.ModeDesc=Wybierz sposób instalacji BadWords
polish.ModeSub=Wybierz typ instalacji:
polish.ModeUpdate=Standardowa Instalacja/Aktualizacja - Instaluje lub aktualizuje aplikację. Zachowuje Twoje ustawienia i modele.
polish.ModeClean=Naprawa Instalacji - Naprawia błędy poprzez zastąpienie plików rdzenia. Zachowuje Twoje ustawienia i modele.
polish.ModeWipe=Pełny Reset - Usuwa absolutnie WSZYSTKO i instaluje aplikację od zera.

; --- GERMAN ---
german.GpuDesc=Version mit NVIDIA GPU-Beschleunigung (Empfohlen)
german.CpuDesc=CPU-Version (Langsamer, kompatibel)
german.CompCore=Kernprogrammdateien
german.CompNvidia=NVIDIA-Supportbibliotheken
german.StatusPython=Installiere Python-Umgebung (erforderlich)...
german.StatusConfig=Konfiguriere venv und AI-Bibliotheken (dies kann eine Weile dauern)...
german.ErrResolve=DaVinci Resolve Skriptordner wurde nicht gefunden.
german.ErrConfig=Konfiguration fehlgeschlagen (setup_windows.bat). Fehlercode: %1
german.ModeTitle=Installationsmodus
german.ModeDesc=Wählen Sie die Installationsart für BadWords
german.ModeSub=Wählen Sie den Installationstyp:
german.ModeUpdate=Standard-Installation/Update - Installiert oder aktualisiert die App. Einstellungen und Modelle bleiben erhalten.
german.ModeClean=Reparatur-Installation - Behebt Fehler durch Ersetzen der Kerndateien. Einstellungen und Modelle bleiben erhalten.
german.ModeWipe=Vollständiger Reset - Löscht absolut ALLES und installiert die App von Grund auf neu.

; --- SPANISH ---
spanish.GpuDesc=Versión con aceleración de GPU NVIDIA (Recomendado)
spanish.CpuDesc=Versión de CPU (Más lenta, compatible)
spanish.CompCore=Archivos principales del programa
spanish.CompNvidia=Bibliotecas de soporte NVIDIA
spanish.StatusPython=Instalando el entorno Python (requerido)...
spanish.StatusConfig=Configurando venv y bibliotecas de IA (esto puede tardar)...
spanish.ErrResolve=No se pudo encontrar la carpeta de scripts de DaVinci Resolve.
spanish.ErrConfig=Error de configuración (setup_windows.bat). Código de error: %1
spanish.ModeTitle=Modo de instalación
spanish.ModeDesc=Elija cómo desea instalar BadWords
spanish.ModeSub=Elija el tipo de instalación (Si es su primera vez, elija 1):
spanish.ModeUpdate=Instalación/Actualización estándar - Instala o actualiza la aplicación. Mantenga sus ajustes y modelos.
spanish.ModeClean=Reparar instalación - Solucione errores reemplazando archivos principales. Mantenga sus ajustes y modelos.
spanish.ModeWipe=Restablecimiento completo - Elimine absolutamente TODO e instale desde cero.

; --- FRENCH ---
french.GpuDesc=Version avec accélération GPU NVIDIA (Recommandé)
french.CpuDesc=Version CPU (Plus lente, compatible)
french.CompCore=Fichiers principaux du programme
french.CompNvidia=Bibliothèques de support NVIDIA
french.StatusPython=Installation de l'environnement Python (requis)...
french.StatusConfig=Configuration du venv et des bibliothèques d'IA (cela peut prendre du temps)...
french.ErrResolve=Impossible de trouver le dossier des scripts DaVinci Resolve.
french.ErrConfig=Échec de la configuration (setup_windows.bat). Code d'erreur : %1
french.ModeTitle=Mode d'installation
french.ModeDesc=Choisissez comment vous souhaitez installer BadWords
french.ModeSub=Choisissez le type d'installation:
french.ModeUpdate=Installation/Mise à jour standard - Installe ou met à jour l'application. Conserve vos paramètres et modèles.
french.ModeClean=Réparer l'installation - Correction des bogues en remplaçant les fichiers principaux. Conserve vos paramètres et modèles.
french.ModeWipe=Réinitialisation complète - Supprimez absolument TOUT et installez à partir de zéro.

; --- ITALIAN ---
italian.GpuDesc=Versione con accelerazione GPU NVIDIA (Consigliato)
italian.CpuDesc=Versione CPU (Più lenta, compatibile)
italian.CompCore=File core del programma
italian.CompNvidia=Librerie di supporto NVIDIA
italian.StatusPython=Installazione dell'ambiente Python (richiesto)...
italian.StatusConfig=Configurazione di venv e librerie AI (potrebbe richiedere tempo)...
italian.ErrResolve=Impossibile trovare la cartella degli script di DaVinci Resolve.
italian.ErrConfig=Configurazione fallita (setup_windows.bat). Codice errore: %1
italian.ModeTitle=Modalità di installazione
italian.ModeDesc=Scegli come desideri installare BadWords
italian.ModeSub=Scegli il tipo di installazione:
italian.ModeUpdate=Installazione/Aggiornamento standard - Installa o aggiorna l'app. Mantiene le impostazioni e i modelli.
italian.ModeClean=Ripara installazione - Risolve i bug sostituendo i file core. Mantiene le impostazioni e i modelli.
italian.ModeWipe=Reset completo - Elimina assolutamente TUTTO e installa da zero.

; --- PORTUGUESE ---
portuguese.GpuDesc=Versão com aceleração de GPU NVIDIA (Recomendado)
portuguese.CpuDesc=Versão CPU (Mais lenta, compatível)
portuguese.CompCore=Arquivos principais do programa
portuguese.CompNvidia=Bibliotecas de suporte NVIDIA
portuguese.StatusPython=Instalando o ambiente Python (necessário)...
portuguese.StatusConfig=Configurando venv e bibliotecas de IA (isso pode levar um tempo)...
portuguese.ErrResolve=Não foi possível encontrar a pasta de scripts do DaVinci Resolve.
portuguese.ErrConfig=Falha na configuração (setup_windows.bat). Código de erro: %1
portuguese.ModeTitle=Modo de Instalação
portuguese.ModeDesc=Escolha como deseja instalar o BadWords
portuguese.ModeSub=Escolha o tipo de instalação:
portuguese.ModeUpdate=Instalação/Atualização padrão - Instala ou atualiza o app. Mantém suas configurações e modelos.
portuguese.ModeClean=Reparar Instalação - Corrige bugs substituindo arquivos principais. Mantém suas configurações e modelos.
portuguese.ModeWipe=Reset Completo - Exclui absolutamente TUDO e instala do zero.

; --- UKRAINIAN ---
ukrainian.GpuDesc=Версія з прискоренням NVIDIA GPU (Рекомендовано)
ukrainian.CpuDesc=Версія для CPU (Повільніша, сумісна)
ukrainian.CompCore=Основні файли програми
ukrainian.CompNvidia=Бібліотеки підтримки NVIDIA
ukrainian.StatusPython=Встановлення середовища Python (обов'язково)...
ukrainian.StatusConfig=Налаштування venv та бібліотек ШІ (це може зайняти час)...
ukrainian.ErrResolve=Не вдалося знайти папку скриптів DaVinci Resolve.
ukrainian.ErrConfig=Помилка налаштування (setup_windows.bat). Код помилки: %1
ukrainian.ModeTitle=Режим інсталяції
ukrainian.ModeDesc=Виберіть спосіб інсталяції BadWords
ukrainian.ModeSub=Виберіть тип інсталяції:
ukrainian.ModeUpdate=Стандартна інсталяція/оновлення - Встановлює або оновлює програму. Зберігає ваші налаштування та моделі.
ukrainian.ModeClean=Відновлення інсталяції - Виправляє помилки, замінюючи основні файли. Зберігає ваші налаштування та моделі.
ukrainian.ModeWipe=Повне скидання - Видаляє абсолютно ВСЕ і встановлює з нуля.

; --- DUTCH ---
dutch.GpuDesc=Versie met NVIDIA GPU-versnelling (Aanbevolen)
dutch.CpuDesc=CPU-versie (Langzamer, compatibel)
dutch.CompCore=Kernbestanden van het programma
dutch.CompNvidia=NVIDIA-ondersteuningsbibliotheken
dutch.StatusPython=Python-omgeving installeren (vereist)...
dutch.StatusConfig=Venv en AI-bibliotheken configureren (dit kan even duren)...
dutch.ErrResolve=Kon de DaVinci Resolve scripts map niet vinden.
dutch.ErrConfig=Configuratie mislukt (setup_windows.bat). Foutcode: %1
dutch.ModeTitle=Installatiemodus
dutch.ModeDesc=Kies hoe u BadWords wilt installeren
dutch.ModeSub=Kies het installatietype:
dutch.ModeUpdate=Standaard installatie/update - Installeert of updatet de app. Behoudt uw instellingen en modellen.
dutch.ModeClean=Reparatie-installatie - Herstel fouten door kernbestanden te vervangen. Behoudt uw instellingen en modellen.
dutch.ModeWipe=Volledige reset - Verwijdert absoluut ALLES en installeert vanaf nul.

; --- RUSSIAN ---
russian.GpuDesc=Версия с ускорением NVIDIA GPU (Рекомендуется)
russian.CpuDesc=Версия для CPU (Медленнее, совместимая)
russian.CompCore=Основные файлы программы
russian.CompNvidia=Библиотеки поддержки NVIDIA
russian.StatusPython=Установка среды Python (обязательно)...
russian.StatusConfig=Настройка venv и библиотек ИИ (это может занять время)...
russian.ErrResolve=Не удалось найти папку скриптов DaVinci Resolve.
russian.ErrConfig=Ошибка настройки (setup_windows.bat). Код ошибки: %1
russian.ModeTitle=Режим установки
russian.ModeDesc=Выберите способ установки BadWords
russian.ModeSub=Выберите тип установки:
russian.ModeUpdate=Стандартная установка/обновление - Устанавливает или обновляет приложение. Сохраняет настройки и модели.
russian.ModeClean=Восстановление установки - Исправляет ошибки путем замены основных файлов. Сохраняет настройки и модели.
russian.ModeWipe=Полный сброс - Удаляет абсолютно ВСЕ и устанавливает с нуля.

[Types]
Name: "gpu"; Description: "{cm:GpuDesc}"
Name: "cpu"; Description: "{cm:CpuDesc}"

[Components]
Name: "core"; Description: "{cm:CompCore}"; Types: gpu cpu; Flags: fixed
Name: "nvidia"; Description: "{cm:CompNvidia}"; Types: gpu

[Files]
Source: "src\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "setup_windows.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\bin"
Name: "{app}\models"
Name: "{app}\libs"

[Run]
Filename: "{tmp}\python_setup.exe"; Parameters: "/quiet PrependPath=1 Include_test=0"; StatusMsg: "{cm:StatusPython}"; Check: FileExists(ExpandConstant('{tmp}\python_setup.exe')); Flags: waituntilterminated

[Code]
var
  ResolveScriptDir: String;
  PythonNeeded: Boolean;
  InstallModePage: TInputOptionWizardPage;

function NeedsPythonInstallation(): Boolean;
var
  v10, v11, v12: Boolean;
begin
  v10 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.10\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath');
  v11 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.11\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath');
  v12 := RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.12\InstallPath') or RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath');
  
  if v10 or v11 or v12 then Result := False
  else Result := True;
end;

procedure InitializeWizard;
begin
  idpDownloadAfter(wpReady);
  
  PythonNeeded := NeedsPythonInstallation();
  if PythonNeeded then idpAddFile('{#PythonUrl}', ExpandConstant('{tmp}\python_setup.exe'));

  idpAddFile('{#FFmpegUrl}', ExpandConstant('{tmp}\ffmpeg.zip'));

  InstallModePage := CreateInputOptionPage(wpSelectComponents,
    CustomMessage('ModeTitle'), CustomMessage('ModeDesc'),
    CustomMessage('ModeSub'), True, False);
  InstallModePage.Add(CustomMessage('ModeUpdate'));
  InstallModePage.Add(CustomMessage('ModeClean'));
  InstallModePage.Add(CustomMessage('ModeWipe'));
  InstallModePage.Values[0] := True; // Default to Standard Update
end;

function GetResolveScriptDir(Param: String): String;
begin
  Result := ExpandConstant('{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility');
  if not DirExists(Result) then ForceDirectories(Result);
end;

procedure GenerateResolveWrapper;
var
  WrapperPath: String;
  Lines: TArrayOfString;
  AppDir: String;
begin
  ResolveScriptDir := GetResolveScriptDir('');
  if not DirExists(ResolveScriptDir) then Exit;

  AppDir := ExpandConstant('{app}');
  StringChange(AppDir, '\', '\\');
  WrapperPath := ResolveScriptDir + '\BadWords.py';
  
  SetArrayLength(Lines, 20);
  Lines[0] := 'import sys';
  Lines[1] := 'import os';
  Lines[2] := 'import traceback';
  Lines[4] := 'INSTALL_DIR = r"' + AppDir + '"';
  Lines[5] := 'LIBS_DIR = os.path.join(INSTALL_DIR, "libs")';
  Lines[6] := 'MAIN_SCRIPT = os.path.join(INSTALL_DIR, "main.py")';
  Lines[8] := 'if os.path.exists(LIBS_DIR): sys.path.insert(0, LIBS_DIR)';
  Lines[12] := 'if INSTALL_DIR not in sys.path: sys.path.append(INSTALL_DIR)';
  Lines[15] := 'if os.path.exists(MAIN_SCRIPT):';
  Lines[16] := '    try:';
  Lines[17] := '        with open(MAIN_SCRIPT, "r", encoding="utf-8") as f: exec(f.read(), globals())';
  Lines[19] := '    except Exception as e: print(e)';
  
  SaveStringsToFile(WrapperPath, Lines, False);
end;

procedure CleanAppFolder_CleanInstall;
var
  FindRec: TFindRec;
  AppPath, FileName: String;
begin
  AppPath := ExpandConstant('{app}');
  if not DirExists(AppPath) then Exit;

  if FindFirst(AppPath + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          FileName := FindRec.Name;
          
          if (CompareText(FileName, 'models') = 0) or
             (CompareText(FileName, 'saves') = 0) or
             (CompareText(FileName, 'pref.json') = 0) then
          begin
            Log('[REPAIR INSTALL] Keeping userdata: ' + FileName);
          end
          else
          begin
            Log('[REPAIR INSTALL] Deleting: ' + FileName);
            if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
              DelTree(AppPath + '\' + FileName, True, True, True)
            else
              DeleteFile(AppPath + '\' + FileName);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  GpuFlag: String;
  FFmpegZip: String;
  WipeMode: String;
begin
  if CurStep = ssInstall then
  begin
    if InstallModePage.Values[2] then // Complete Reset
    begin
      DelTree(ExpandConstant('{app}'), True, True, True);
    end
    else if InstallModePage.Values[1] then // Repair Installation
    begin
      CleanAppFolder_CleanInstall(); 
    end
  end;

  if CurStep = ssPostInstall then
  begin
    GenerateResolveWrapper();
    
    // Zmieniono IsComponentSelected na WizardIsComponentSelected
    if WizardIsComponentSelected('nvidia') then GpuFlag := '1' else GpuFlag := '0';
    FFmpegZip := ExpandConstant('{tmp}\ffmpeg.zip');

    if InstallModePage.Values[2] then WipeMode := '2'
    else if InstallModePage.Values[1] then WipeMode := '1'
    else WipeMode := '0';
      
    WizardForm.StatusLabel.Caption := CustomMessage('StatusConfig');
    
    if not Exec(ExpandConstant('{app}\setup_windows.bat'), 
                '"' + ExpandConstant('{app}') + '" "' + GpuFlag + '" "' + FFmpegZip + '" "' + WipeMode + '"', 
                '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox(FmtMessage(CustomMessage('ErrConfig'), [IntToStr(ResultCode)]), mbError, MB_OK);
    end;
  end;
end;