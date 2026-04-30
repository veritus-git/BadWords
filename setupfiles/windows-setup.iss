; --- DEFINITIONS ---
#define MyAppName "BadWords"
#define MyAppVersion "app_version"
#define MyAppPublisher "Szymon Wolarz"
#define MyAppExeName "main.py"

; URLs (GPU is AUTO-DETECTED in setup_windows.bat - no user choice)
#define PythonUrl "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
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
english.StatusPython=Installing Python environment (required)...
english.StatusConfig=Configuring environment and AI libraries (this may take a while)...
english.StatusRemoving=Removing BadWords from this system...
english.ErrResolve=Could not find DaVinci Resolve scripts folder.
english.ErrConfig=Configuration failed (setup_windows.bat). Error code: %1
english.ModeTitle=Installation Mode
english.ModeDesc=Choose how you want to install BadWords
english.ModeSub=Choose installation type:
english.ModeUpdate=Standard Install/Update - Install or update the app. Keep your settings and models.
english.ModeClean=Repair Installation - Fix bugs by replacing core files. Keep your settings and models.
english.ModeMove=Move Installation - Change the BadWords folder (moves all your data).
english.ModeWipe=Complete Reset - Delete absolutely EVERYTHING and install from scratch.
english.ModeRemove=Remove Completely - Uninstall BadWords and delete ALL data, models and settings.

; --- POLISH ---
polish.StatusPython=Instalowanie środowiska Python (wymagane)...
polish.StatusConfig=Konfiguracja środowiska i bibliotek AI (to może chwilę potrwać)...
polish.StatusRemoving=Usuwanie BadWords z tego systemu...
polish.ErrResolve=Nie można znaleźć folderu skryptów DaVinci Resolve.
polish.ErrConfig=Błąd konfiguracji (setup_windows.bat). Kod błędu: %1
polish.ModeTitle=Tryb Instalacji
polish.ModeDesc=Wybierz sposób instalacji BadWords
polish.ModeSub=Wybierz typ instalacji:
polish.ModeUpdate=Standardowa Instalacja/Aktualizacja - Instaluje lub aktualizuje aplikację. Zachowuje Twoje ustawienia i modele.
polish.ModeClean=Naprawa Instalacji - Naprawia błędy poprzez zastąpienie plików rdzenia. Zachowuje Twoje ustawienia i modele.
polish.ModeMove=Przenieś Instalację - Zmień folder BadWords (przenosi wszystkie dane).
polish.ModeWipe=Pełny Reset - Usuwa absolutnie WSZYSTKO i instaluje aplikację od zera.
polish.ModeRemove=Usuń Całkowicie - Odinstaluj BadWords i usuń WSZYSTKIE dane, modele i ustawienia.

; --- GERMAN ---
german.StatusPython=Installiere Python-Umgebung (erforderlich)...
german.StatusConfig=Konfiguriere Umgebung und AI-Bibliotheken (dies kann eine Weile dauern)...
german.StatusRemoving=BadWords wird von diesem System entfernt...
german.ErrResolve=DaVinci Resolve Skriptordner wurde nicht gefunden.
german.ErrConfig=Konfiguration fehlgeschlagen (setup_windows.bat). Fehlercode: %1
german.ModeTitle=Installationsmodus
german.ModeDesc=Wählen Sie die Installationsart für BadWords
german.ModeSub=Wählen Sie den Installationstyp:
german.ModeUpdate=Standard-Installation/Update - Installiert oder aktualisiert die App. Einstellungen und Modelle bleiben erhalten.
german.ModeClean=Reparatur-Installation - Behebt Fehler durch Ersetzen der Kerndateien. Einstellungen und Modelle bleiben erhalten.
german.ModeMove=Installation verschieben - BadWords-Ordner ändern (alle Daten werden verschoben).
german.ModeWipe=Vollständiger Reset - Löscht absolut ALLES und installiert die App von Grund auf neu.
german.ModeRemove=Vollständig entfernen - BadWords deinstallieren und ALLE Daten, Modelle und Einstellungen löschen.

; --- SPANISH ---
spanish.StatusPython=Instalando el entorno Python (requerido)...
spanish.StatusConfig=Configurando entorno y bibliotecas de IA (esto puede tardar)...
spanish.StatusRemoving=Eliminando BadWords de este sistema...
spanish.ErrResolve=No se pudo encontrar la carpeta de scripts de DaVinci Resolve.
spanish.ErrConfig=Error de configuración (setup_windows.bat). Código de error: %1
spanish.ModeTitle=Modo de instalación
spanish.ModeDesc=Elija cómo desea instalar BadWords
spanish.ModeSub=Elija el tipo de instalación:
spanish.ModeUpdate=Instalación/Actualización estándar - Instala o actualiza la aplicación. Mantenga sus ajustes y modelos.
spanish.ModeClean=Reparar instalación - Solucione errores reemplazando archivos principales. Mantenga sus ajustes y modelos.
spanish.ModeMove=Mover instalación - Cambiar la carpeta de BadWords (mueve todos sus datos).
spanish.ModeWipe=Restablecimiento completo - Elimine absolutamente TODO e instale desde cero.
spanish.ModeRemove=Eliminar completamente - Desinstalar BadWords y eliminar TODOS los datos, modelos y ajustes.

; --- FRENCH ---
french.StatusPython=Installation de l'environnement Python (requis)...
french.StatusConfig=Configuration de l'environnement et des bibliothèques d'IA (cela peut prendre du temps)...
french.StatusRemoving=Suppression de BadWords de ce système...
french.ErrResolve=Impossible de trouver le dossier des scripts DaVinci Resolve.
french.ErrConfig=Échec de la configuration (setup_windows.bat). Code d'erreur : %1
french.ModeTitle=Mode d'installation
french.ModeDesc=Choisissez comment vous souhaitez installer BadWords
french.ModeSub=Choisissez le type d'installation:
french.ModeUpdate=Installation/Mise à jour standard - Installe ou met à jour l'application. Conserve vos paramètres et modèles.
french.ModeClean=Réparer l'installation - Correction des bogues en remplaçant les fichiers principaux. Conserve vos paramètres et modèles.
french.ModeMove=Déplacer l'installation - Changer le dossier BadWords (déplace toutes vos données).
french.ModeWipe=Réinitialisation complète - Supprimez absolument TOUT et installez à partir de zéro.
french.ModeRemove=Supprimer complètement - Désinstaller BadWords et supprimer TOUTES les données, modèles et paramètres.

; --- ITALIAN ---
italian.StatusPython=Installazione dell'ambiente Python (richiesto)...
italian.StatusConfig=Configurazione dell'ambiente e librerie AI (potrebbe richiedere tempo)...
italian.StatusRemoving=Rimozione di BadWords da questo sistema...
italian.ErrResolve=Impossibile trovare la cartella degli script di DaVinci Resolve.
italian.ErrConfig=Configurazione fallita (setup_windows.bat). Codice errore: %1
italian.ModeTitle=Modalità di installazione
italian.ModeDesc=Scegli come desideri installare BadWords
italian.ModeSub=Scegli il tipo di installazione:
italian.ModeUpdate=Installazione/Aggiornamento standard - Installa o aggiorna l'app. Mantiene le impostazioni e i modelli.
italian.ModeClean=Ripara installazione - Risolve i bug sostituendo i file core. Mantiene le impostazioni e i modelli.
italian.ModeMove=Sposta installazione - Cambia la cartella BadWords (sposta tutti i dati).
italian.ModeWipe=Reset completo - Elimina assolutamente TUTTO e installa da zero.
italian.ModeRemove=Rimuovi completamente - Disinstalla BadWords ed elimina TUTTI i dati, modelli e impostazioni.

; --- PORTUGUESE ---
portuguese.StatusPython=Instalando o ambiente Python (necessário)...
portuguese.StatusConfig=Configurando ambiente e bibliotecas de IA (isso pode levar um tempo)...
portuguese.StatusRemoving=Removendo BadWords deste sistema...
portuguese.ErrResolve=Não foi possível encontrar a pasta de scripts do DaVinci Resolve.
portuguese.ErrConfig=Falha na configuração (setup_windows.bat). Código de erro: %1
portuguese.ModeTitle=Modo de Instalação
portuguese.ModeDesc=Escolha como deseja instalar o BadWords
portuguese.ModeSub=Escolha o tipo de instalação:
portuguese.ModeUpdate=Instalação/Atualização padrão - Instala ou atualiza o app. Mantém suas configurações e modelos.
portuguese.ModeClean=Reparar Instalação - Corrige bugs substituindo arquivos principais. Mantém suas configurações e modelos.
portuguese.ModeMove=Mover instalação - Altere a pasta do BadWords (move todos os seus dados).
portuguese.ModeWipe=Reset Completo - Exclui absolutamente TUDO e instala do zero.
portuguese.ModeRemove=Remover Completamente - Desinstalar BadWords e excluir TODOS os dados, modelos e configurações.

; --- UKRAINIAN ---
ukrainian.StatusPython=Встановлення середовища Python (обов'язково)...
ukrainian.StatusConfig=Налаштування середовища та бібліотек ШІ (це може зайняти час)...
ukrainian.StatusRemoving=Видалення BadWords з цієї системи...
ukrainian.ErrResolve=Не вдалося знайти папку скриптів DaVinci Resolve.
ukrainian.ErrConfig=Помилка налаштування (setup_windows.bat). Код помилки: %1
ukrainian.ModeTitle=Режим інсталяції
ukrainian.ModeDesc=Виберіть спосіб інсталяції BadWords
ukrainian.ModeSub=Виберіть тип інсталяції:
ukrainian.ModeUpdate=Стандартна інсталяція/оновлення - Встановлює або оновлює програму. Зберігає ваші налаштування та моделі.
ukrainian.ModeClean=Відновлення інсталяції - Виправляє помилки, замінюючи основні файли. Зберігає ваші налаштування та моделі.
ukrainian.ModeMove=Перемістити інсталяцію - Змінити папку BadWords (переміщує всі дані).
ukrainian.ModeWipe=Повне скидання - Видаляє абсолютно ВСЕ і встановлює з нуля.
ukrainian.ModeRemove=Видалити повністю - Видалити BadWords та ВСІ дані, моделі та налаштування.

; --- DUTCH ---
dutch.StatusPython=Python-omgeving installeren (vereist)...
dutch.StatusConfig=Omgeving en AI-bibliotheken configureren (dit kan even duren)...
dutch.StatusRemoving=BadWords van dit systeem verwijderen...
dutch.ErrResolve=Kon de DaVinci Resolve scripts map niet vinden.
dutch.ErrConfig=Configuratie mislukt (setup_windows.bat). Foutcode: %1
dutch.ModeTitle=Installatiemodus
dutch.ModeDesc=Kies hoe u BadWords wilt installeren
dutch.ModeSub=Kies het installatietype:
dutch.ModeUpdate=Standaard installatie/update - Installeert of updatet de app. Behoudt uw instellingen en modellen.
dutch.ModeClean=Reparatie-installatie - Herstel fouten door kernbestanden te vervangen. Behoudt uw instellingen en modellen.
dutch.ModeMove=Installatie verplaatsen - Wijzig de BadWords-map (verplaatst al uw gegevens).
dutch.ModeWipe=Volledige reset - Verwijdert absoluut ALLES en installeert vanaf nul.
dutch.ModeRemove=Volledig verwijderen - BadWords verwijderen en ALLE gegevens, modellen en instellingen wissen.

; --- RUSSIAN ---
russian.StatusPython=Установка среды Python (обязательно)...
russian.StatusConfig=Настройка среды и библиотек ИИ (это может занять время)...
russian.StatusRemoving=Удаление BadWords с этой системы...
russian.ErrResolve=Не удалось найти папку скриптов DaVinci Resolve.
russian.ErrConfig=Ошибка настройки (setup_windows.bat). Код ошибки: %1
russian.ModeTitle=Режим установки
russian.ModeDesc=Выберите способ установки BadWords
russian.ModeSub=Выберите тип установки:
russian.ModeUpdate=Стандартная установка/обновление - Устанавливает или обновляет приложение. Сохраняет настройки и модели.
russian.ModeClean=Восстановление установки - Исправляет ошибки путем замены основных файлов. Сохраняет настройки и модели.
russian.ModeMove=Переместить установку - Изменить папку BadWords (перемещает все данные).
russian.ModeWipe=Полный сброс - Удаляет абсолютно ВСЕ и устанавливает с нуля.
russian.ModeRemove=Удалить полностью - Удалить BadWords и ВСЕ данные, модели и настройки.


[Files]
Source: "src\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs; Check: not IsRemoveMode()
Source: "assets\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs; Check: not IsRemoveMode()
Source: "setup_windows.bat"; DestDir: "{app}"; Flags: ignoreversion; Check: not IsRemoveMode()
Source: "setupfiles\update-windows.bat"; DestDir: "{app}"; Flags: ignoreversion; Check: not IsRemoveMode()

[Dirs]
Name: "{app}\bin"; Check: not IsRemoveMode()
Name: "{app}\models"; Check: not IsRemoveMode()
Name: "{app}\libs"; Check: not IsRemoveMode()

[Run]
Filename: "{tmp}\python_setup.exe"; Parameters: "/quiet PrependPath=1 Include_test=0"; StatusMsg: "{cm:StatusPython}"; Check: (not IsRemoveMode()) and FileExists(ExpandConstant('{tmp}\python_setup.exe')); Flags: waituntilterminated

[Code]
var
  InstallModePage: TInputOptionWizardPage;
  DownloadsQueued: Boolean;
  OldInstallPath: String;

// ── Helpers ──────────────────────────────────────────────────────────────────

function IsRemoveMode(): Boolean;
begin
  Result := (InstallModePage <> nil) and InstallModePage.Values[4];
end;

function IsAlreadyInstalled(): Boolean;
begin
  Result := (OldInstallPath <> '') and FileExists(OldInstallPath + '\main.py');
end;

function NeedsPythonInstallation(): Boolean;
var v10, v11, v12, v13: Boolean;
begin
  v10 := RegKeyExists(HKCU,'SOFTWARE\Python\PythonCore\3.10\InstallPath') or RegKeyExists(HKLM,'SOFTWARE\Python\PythonCore\3.10\InstallPath');
  v11 := RegKeyExists(HKCU,'SOFTWARE\Python\PythonCore\3.11\InstallPath') or RegKeyExists(HKLM,'SOFTWARE\Python\PythonCore\3.11\InstallPath');
  v12 := RegKeyExists(HKCU,'SOFTWARE\Python\PythonCore\3.12\InstallPath') or RegKeyExists(HKLM,'SOFTWARE\Python\PythonCore\3.12\InstallPath');
  v13 := RegKeyExists(HKCU,'SOFTWARE\Python\PythonCore\3.13\InstallPath') or RegKeyExists(HKLM,'SOFTWARE\Python\PythonCore\3.13\InstallPath');
  Result := not (v10 or v11 or v12 or v13);
end;

// ── Init ─────────────────────────────────────────────────────────────────────

procedure InitializeWizard;
begin
  idpDownloadAfter(wpReady);
  DownloadsQueued := False;

  OldInstallPath := '';
  RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1',
    'InstallLocation', OldInstallPath);
  // Trim trailing backslash Inno sometimes adds
  if (Length(OldInstallPath) > 0) and (OldInstallPath[Length(OldInstallPath)] = '\') then
    OldInstallPath := Copy(OldInstallPath, 1, Length(OldInstallPath) - 1);

  // Mode page inserted BEFORE wpSelectDir (after wpWelcome) so that
  // ShouldSkipPage(wpSelectDir) can read the already-chosen mode.
  InstallModePage := CreateInputOptionPage(wpWelcome,
    CustomMessage('ModeTitle'), CustomMessage('ModeDesc'),
    CustomMessage('ModeSub'), True, False);
  InstallModePage.Add(CustomMessage('ModeUpdate'));   // 0
  InstallModePage.Add(CustomMessage('ModeClean'));    // 1
  InstallModePage.Add(CustomMessage('ModeMove'));     // 2
  InstallModePage.Add(CustomMessage('ModeWipe'));     // 3
  InstallModePage.Add(CustomMessage('ModeRemove'));   // 4
  InstallModePage.Values[0] := True;
end;

// ── Page visibility ──────────────────────────────────────────────────────────

function ShouldSkipPage(PageID: Integer): Boolean;
var FFmpegCheckPath: String;
begin
  Result := False;
  if PageID = wpSelectDir then
  begin
    // Page order: Welcome -> Mode -> Dir -> ...
    // By the time ShouldSkipPage(wpSelectDir) is called, mode IS already chosen.
    if InstallModePage.Values[4] then Result := True   // Remove: no dir needed
    else if InstallModePage.Values[1] then Result := True  // Repair: use existing
    else if InstallModePage.Values[0] and IsAlreadyInstalled() then Result := True; // Update: use existing
  end;
  // Remove mode: skip wpReady (looks like installing, confuses user)
  if (PageID = wpReady) and IsRemoveMode() then Result := True;
end;

// ── Download queuing ─────────────────────────────────────────────────────────

function NextButtonClick(CurPageID: Integer): Boolean;
var FFmpegCheckPath: String;
begin
  Result := True;
  if (CurPageID = wpReady) and not DownloadsQueued then
  begin
    // No downloads for Remove mode
    if not IsRemoveMode() then
    begin
      if NeedsPythonInstallation() then
        idpAddFile('{#PythonUrl}', ExpandConstant('{tmp}\python_setup.exe'));

      // FFmpeg: check against actual existing install path, not default {app}
      if IsAlreadyInstalled() then
        FFmpegCheckPath := OldInstallPath + '\bin\ffmpeg.exe'
      else
        FFmpegCheckPath := ExpandConstant('{app}\bin\ffmpeg.exe');

      if InstallModePage.Values[3] or not FileExists(FFmpegCheckPath) then
        idpAddFile('{#FFmpegUrl}', ExpandConstant('{tmp}\ffmpeg.zip'));
    end;
    DownloadsQueued := True;
  end;
end;

// ── Smart cleanup helper ─────────────────────────────────────────────────────

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
          // Always keep Inno Setup uninstaller files
          if (CompareText(FileName,'unins000.exe')=0) or
             (CompareText(FileName,'unins000.dat')=0) then
          begin
            Log('[CLEANUP] Keeping InnoSetup tracker: ' + FileName);
          end
          else if KeepUserData and (
             (CompareText(FileName,'models')=0) or
             (CompareText(FileName,'saves')=0) or
             (CompareText(FileName,'pref.json')=0) or
             (CompareText(FileName,'user.json')=0) or
             (CompareText(FileName,'settings.json')=0) or
             (CompareText(FileName,'badwords_debug.log')=0)
          ) then
            Log('[CLEANUP] Keeping user data: ' + FileName)
          else if KeepEnv and (
             (CompareText(FileName,'venv')=0) or
             (CompareText(FileName,'bin')=0) or
             (CompareText(FileName,'libs')=0)
          ) then
            Log('[CLEANUP] Keeping environment: ' + FileName)
          else
          begin
            Log('[CLEANUP] Deleting: ' + FileName);
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

// ── Remove wrapper files ─────────────────────────────────────────────────────

procedure RemoveResolveWrappers;
var
  FindRec: TFindRec;
  StoreDir, ResolvePath: String;
begin
  // Standard install
  ResolvePath := ExpandConstant('{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py');
  if FileExists(ResolvePath) then DeleteFile(ResolvePath);
  // MS Store install
  StoreDir := ExpandConstant('{localappdata}\Packages\');
  if FindFirst(StoreDir + 'BlackmagicDesign.DaVinciResolve_*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          ResolvePath := StoreDir + FindRec.Name +
            '\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py';
          if FileExists(ResolvePath) then DeleteFile(ResolvePath);
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

// ── Main install steps ───────────────────────────────────────────────────────

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  FFmpegZip, WipeMode, OldDir: String;
begin
  if CurStep = ssInstall then
  begin
    // Clean ghost registry entries from old installs without GUID
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER,'Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords_is1');
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER,'Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords');

    if InstallModePage.Values[4] then // Remove Completely
    begin
      WizardForm.StatusLabel.Caption := CustomMessage('StatusRemoving');
      // Remove wrappers
      RemoveResolveWrappers;
      // Nuke everything
      SmartCleanup(False, False);
      if DirExists(ExpandConstant('{app}')) then
        DelTree(ExpandConstant('{app}'), True, True, True);
      // Clean registry (including keys ISS may have already written this session)
      RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER,'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1');
    end
    else if InstallModePage.Values[3] then // Complete Reset
    begin
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
        if FileExists(OldInstallPath + '\pref.json') then
          FileCopy(OldInstallPath + '\pref.json', ExpandConstant('{app}') + '\pref.json', False);
        if FileExists(OldInstallPath + '\user.json') then
          FileCopy(OldInstallPath + '\user.json', ExpandConstant('{app}') + '\user.json', False);
        if FileExists(OldInstallPath + '\settings.json') then
          FileCopy(OldInstallPath + '\settings.json', ExpandConstant('{app}') + '\settings.json', False);
        if FileExists(OldInstallPath + '\badwords_debug.log') then
          FileCopy(OldInstallPath + '\badwords_debug.log', ExpandConstant('{app}') + '\badwords_debug.log', False);
        DelTree(OldInstallPath, True, True, True);
      end;
      SmartCleanup(False, True);
    end
    else if InstallModePage.Values[1] then // Repair
      SmartCleanup(False, True)
    else // Standard Install/Update
      SmartCleanup(True, True);
  end;

  if CurStep = ssPostInstall then
  begin
    // Remove mode: cleanup already done in ssInstall, just delete ISS own key and exit
    if InstallModePage.Values[4] then
    begin
      RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER,
        'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1');
      Exit;
    end;

    // Restore JSONs after Complete Reset
    if InstallModePage.Values[3] then
    begin
      if FileExists(ExpandConstant('{tmp}\bw_user.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_user.json'), ExpandConstant('{app}\user.json'), False);
      if FileExists(ExpandConstant('{tmp}\bw_settings.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_settings.json'), ExpandConstant('{app}\settings.json'), False);
      if FileExists(ExpandConstant('{tmp}\bw_pref.json')) then
        FileCopy(ExpandConstant('{tmp}\bw_pref.json'), ExpandConstant('{app}\pref.json'), False);
    end;

    FFmpegZip := ExpandConstant('{tmp}\ffmpeg.zip');

    // WipeMode mapping: 0=Update, 1=Repair, 2=Move, 3=Reset
    if InstallModePage.Values[3] then WipeMode := '3'
    else if InstallModePage.Values[2] then WipeMode := '2'
    else if InstallModePage.Values[1] then WipeMode := '1'
    else WipeMode := '0';

    // OLD_INSTALL_DIR for Move mode
    if InstallModePage.Values[2] then OldDir := OldInstallPath
    else OldDir := '';

    WizardForm.StatusLabel.Caption := CustomMessage('StatusConfig');

    if not Exec(ExpandConstant('{app}\setup_windows.bat'),
        '"' + ExpandConstant('{app}') + '" "' + FFmpegZip + '" "' + WipeMode + '" "' + OldDir + '"',
        '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox(FmtMessage(CustomMessage('ErrConfig'), [IntToStr(ResultCode)]), mbError, MB_OK);
    end;
  end;
end;

// ── Uninstaller (standard Windows uninstall) ─────────────────────────────────

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppPath: String;
  FindRec: TFindRec;
  StoreDir, ResolvePath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    RemoveResolveWrappers;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    AppPath := ExpandConstant('{app}');
    if DirExists(AppPath) then
      DelTree(AppPath, True, True, True);
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1');
  end;
end;


