; --- DEFINITIONS ---
#define MyAppName "BadWords"
#define MyAppVersion "app_version"
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
; Installer icon (must be in .ico format in the same folder as the script)
SetupIconFile=assets/icons/icon_default.ico

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
english.ModeMove=Move Installation - Change the BadWords folder (moves all your data).
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
polish.ModeMove=Przenieś Instalację - Zmień folder BadWords (przenosi wszystkie dane).
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
german.ModeMove=Installation verschieben - BadWords-Ordner ändern (alle Daten werden verschoben).
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
spanish.ModeSub=Elija el tipo de instalación:
spanish.ModeUpdate=Instalación/Actualización estándar - Instala o actualiza la aplicación. Mantenga sus ajustes y modelos.
spanish.ModeClean=Reparar instalación - Solucione errores reemplazando archivos principales. Mantenga sus ajustes y modelos.
spanish.ModeMove=Mover instalación - Cambiar la carpeta de BadWords (mueve todos sus datos).
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
french.ModeMove=Déplacer l'installation - Changer le dossier BadWords (déplace toutes vos données).
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
italian.ModeMove=Sposta installazione - Cambia la cartella BadWords (sposta tutti i dati).
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
portuguese.ModeMove=Mover instalação - Altere a pasta do BadWords (move todos os seus dados).
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
ukrainian.ModeMove=Перемістити інсталяцію - Змінити папку BadWords (переміщує всі дані).
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
dutch.ModeMove=Installatie verplaatsen - Wijzig de BadWords-map (verplaatst al uw gegevens).
dutch.ModeWipe=Volledige reset - Verwijdert absoluut ALLES en installeert vanaf nul.

; --- RUSSIAN ---
russian.GpuDesc=Версия с ускорением NVIDIA GPU (Рекомендуется)
russian.CpuDesc=Версия для CPU (Медленнее, совместимая)
russian.CompCore=Основные файлы программы
russian.CompNvidia=Библиотеки поддержки NVIDIA
russian.StatusPython=Установка среды Python (обязательно)...
russian.StatusConfig=Настройка venv и библиотек ИИ (это может занять время)...
russian.ErrResolve=Не удалось найти папку скриптів DaVinci Resolve.
russian.ErrConfig=Ошибка настройки (setup_windows.bat). Код ошибки: %1
russian.ModeTitle=Режим установки
russian.ModeDesc=Выберите способ установки BadWords
russian.ModeSub=Выберите тип установки:
russian.ModeUpdate=Стандартная установка/обновление - Устанавливает или обновляет приложение. Сохраняет настройки и модели.
russian.ModeClean=Восстановление установки - Исправляет ошибки путем замены основных файлов. Сохраняет настройки и модели.
russian.ModeMove=Переместить установку - Изменить папку BadWords (перемещает все данные).
russian.ModeWipe=Полный сброс - Удаляет абсолютно ВСЕ и устанавливает с нуля.

[Types]
Name: "gpu"; Description: "{cm:GpuDesc}"
Name: "cpu"; Description: "{cm:CpuDesc}"

[Components]
Name: "core"; Description: "{cm:CompCore}"; Types: gpu cpu; Flags: fixed
Name: "nvidia"; Description: "{cm:CompNvidia}"; Types: gpu

[Files]
Source: "src\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "assets\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "setup_windows.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "setupfiles\update-windows.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\bin"
Name: "{app}\models"
Name: "{app}\libs"

[Run]
Filename: "{tmp}\python_setup.exe"; Parameters: "/quiet PrependPath=1 Include_test=0"; StatusMsg: "{cm:StatusPython}"; Check: FileExists(ExpandConstant('{tmp}\python_setup.exe')); Flags: waituntilterminated

[Code]
var
  InstallModePage: TInputOptionWizardPage;
  DownloadsQueued: Boolean;
  OldInstallPath: String;

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
  DownloadsQueued := False;

  OldInstallPath := '';
  RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1',
    'InstallLocation', OldInstallPath);

  InstallModePage := CreateInputOptionPage(wpSelectComponents,
    CustomMessage('ModeTitle'), CustomMessage('ModeDesc'),
    CustomMessage('ModeSub'), True, False);
  InstallModePage.Add(CustomMessage('ModeUpdate'));
  InstallModePage.Add(CustomMessage('ModeClean'));
  InstallModePage.Add(CustomMessage('ModeMove'));
  InstallModePage.Add(CustomMessage('ModeWipe'));
  InstallModePage.Values[0] := True; // Default to Standard Update
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  // Queue packages for download right before the "Ready to install" page (wpReady)
  if (CurPageID = wpReady) and not DownloadsQueued then
  begin
    if NeedsPythonInstallation() then 
      idpAddFile('{#PythonUrl}', ExpandConstant('{tmp}\python_setup.exe'));
      
    // SMART FFmpeg: Download ONLY if Wipe is chosen or ffmpeg doesn't exist
    if InstallModePage.Values[3] or not FileExists(ExpandConstant('{app}\bin\ffmpeg.exe')) then
      idpAddFile('{#FFmpegUrl}', ExpandConstant('{tmp}\ffmpeg.zip'));
      
    DownloadsQueued := True;
  end;
end;

// Unified Smart Cleanup to absolutely protect installer files
procedure SmartCleanup(KeepEnv: Boolean; KeepUserData: Boolean);
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
          
          // 1. ZAWSZE CHRONIMY PLIKI INSTALATORA INNO SETUP (Kluczowe dla dzialania deinstalacji)
          if (CompareText(FileName, 'unins000.exe') = 0) or
             (CompareText(FileName, 'unins000.dat') = 0) then
          begin
            Log('[CLEANUP] Keeping InnoSetup tracker: ' + FileName);
          end
          // 2. CHRONIMY DANE UZYTKOWNIKA
          else if KeepUserData and (
             (CompareText(FileName, 'models') = 0) or
             (CompareText(FileName, 'saves') = 0) or
             (CompareText(FileName, 'pref.json') = 0) or
             (CompareText(FileName, 'user.json') = 0) or
             (CompareText(FileName, 'settings.json') = 0) or
             (CompareText(FileName, 'badwords_debug.log') = 0)
          ) then
          begin
            Log('[CLEANUP] Keeping user data: ' + FileName);
          end
          // 3. CHRONIMY SRODOWISKO (Tylko dla trybu Update)
          else if KeepEnv and (
             (CompareText(FileName, 'venv') = 0) or
             (CompareText(FileName, 'bin') = 0) or
             (CompareText(FileName, 'libs') = 0)
          ) then
          begin
            Log('[CLEANUP] Keeping environment: ' + FileName);
          end
          // 4. USUWAMY STARE PLIKI I SKRYPTY
          else
          begin
            Log('[CLEANUP] Deleting obsolete item: ' + FileName);
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
    // ANTI-GHOST REGISTRY WIPE (Usuwamy z rejestru sieroty ze starych wersji bez GUID)
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords_is1');
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords');

    if InstallModePage.Values[3] then // Complete Reset
    begin
      // Backup user data before full wipe
      if FileExists(ExpandConstant('{app}\user.json')) then
        FileCopy(ExpandConstant('{app}\user.json'), ExpandConstant('{tmp}\bw_user.json'), False);
      if FileExists(ExpandConstant('{app}\settings.json')) then
        FileCopy(ExpandConstant('{app}\settings.json'), ExpandConstant('{tmp}\bw_settings.json'), False);
      if FileExists(ExpandConstant('{app}\pref.json')) then
        FileCopy(ExpandConstant('{app}\pref.json'), ExpandConstant('{tmp}\bw_pref.json'), False);
      SmartCleanup(False, False);
    end
    else if InstallModePage.Values[2] then // Move Installation
    begin
      if (OldInstallPath <> '') and
         (CompareText(OldInstallPath, ExpandConstant('{app}')) <> 0) and
         DirExists(OldInstallPath) then
      begin
        Log('[MOVE] Moving from ' + OldInstallPath + ' to ' + ExpandConstant('{app}'));
        Exec(ExpandConstant('{sys}\robocopy.exe'),
             '"' + OldInstallPath + '\venv" "' + ExpandConstant('{app}') + '\venv" /E /MOVE /NP /NJH /NJS',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Exec(ExpandConstant('{sys}\robocopy.exe'),
             '"' + OldInstallPath + '\models" "' + ExpandConstant('{app}') + '\models" /E /MOVE /NP /NJH /NJS',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Exec(ExpandConstant('{sys}\robocopy.exe'),
             '"' + OldInstallPath + '\bin" "' + ExpandConstant('{app}') + '\bin" /E /MOVE /NP /NJH /NJS',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Exec(ExpandConstant('{sys}\robocopy.exe'),
             '"' + OldInstallPath + '\saves" "' + ExpandConstant('{app}') + '\saves" /E /MOVE /NP /NJH /NJS',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        // Move user data files
        if FileExists(OldInstallPath + '\pref.json') then
          FileCopy(OldInstallPath + '\pref.json', ExpandConstant('{app}') + '\pref.json', False);
        if FileExists(OldInstallPath + '\user.json') then
          FileCopy(OldInstallPath + '\user.json', ExpandConstant('{app}') + '\user.json', False);
        if FileExists(OldInstallPath + '\settings.json') then
          FileCopy(OldInstallPath + '\settings.json', ExpandConstant('{app}') + '\settings.json', False);
        if FileExists(OldInstallPath + '\badwords_debug.log') then
          FileCopy(OldInstallPath + '\badwords_debug.log', ExpandConstant('{app}') + '\badwords_debug.log', False);
        // Remove old directory
        DelTree(OldInstallPath, True, True, True);
      end;
      SmartCleanup(False, True); // treat rest as Repair
    end
    else if InstallModePage.Values[1] then // Repair Installation
      SmartCleanup(False, True)
    else // Standard Update
      SmartCleanup(True, True);
  end;

  if CurStep = ssPostInstall then
  begin
    // Restore user data after Full Wipe + fresh install
    if InstallModePage.Values[3] then
    begin
      if FileExists(ExpandConstant('{tmp}\bw_user.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_user.json'), ExpandConstant('{app}\user.json'), False);
      if FileExists(ExpandConstant('{tmp}\bw_settings.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_settings.json'), ExpandConstant('{app}\settings.json'), False);
      if FileExists(ExpandConstant('{tmp}\bw_pref.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_pref.json'), ExpandConstant('{app}\pref.json'), False);
    end;

    if WizardIsComponentSelected('nvidia') then GpuFlag := '1' else GpuFlag := '0';
    FFmpegZip := ExpandConstant('{tmp}\ffmpeg.zip');

    if InstallModePage.Values[3] then WipeMode := '3'
    else if InstallModePage.Values[2] then WipeMode := '2'
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

// ==========================================
// FULL UNINSTALLER LOGIC
// ==========================================
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppPath, ResolvePath, StoreDir: String;
  FindRec: TFindRec;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Delete standard Resolve script
    ResolvePath := ExpandConstant('{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py');
    if FileExists(ResolvePath) then DeleteFile(ResolvePath);

    // Delete Windows Store Resolve script
    StoreDir := ExpandConstant('{localappdata}\Packages\');
    if FindFirst(StoreDir + 'BlackmagicDesign.DaVinciResolve_*', FindRec) then
    begin
      try
        repeat
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          begin
            ResolvePath := StoreDir + FindRec.Name + '\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py';
            if FileExists(ResolvePath) then DeleteFile(ResolvePath);
          end;
        until not FindNext(FindRec);
      finally
        FindClose(FindRec);
      end;
    end;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    // Scorched Earth: Complete destruction of AppData footprint
    AppPath := ExpandConstant('{app}');
    if DirExists(AppPath) then
    begin
      DelTree(AppPath, True, True, True);
    end;
    
    // Explicitly destroy current registry keys to be 100% sure
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1');
  end;
end;