// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Internationalization (i18n) module supporting 10 languages
//! English, Polish, German, Spanish, French, Italian, Dutch, Portuguese, Russian, Ukrainian

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Language {
    En,
    Pl,
    De,
    Es,
    Fr,
    It,
    Nl,
    Pt,
    Ru,
    Uk,
}

impl Language {
    pub const ALL: [Language; 10] = [
        Language::En,
        Language::Pl,
        Language::De,
        Language::Es,
        Language::Fr,
        Language::It,
        Language::Nl,
        Language::Pt,
        Language::Ru,
        Language::Uk,
    ];

    #[allow(dead_code)]
    pub fn code(&self) -> &'static str {
        match self {
            Language::En => "en",
            Language::Pl => "pl",
            Language::De => "de",
            Language::Es => "es",
            Language::Fr => "fr",
            Language::It => "it",
            Language::Nl => "nl",
            Language::Pt => "pt",
            Language::Ru => "ru",
            Language::Uk => "uk",
        }
    }

    pub fn display_name(&self) -> &'static str {
        match self {
            Language::En => "English",
            Language::Pl => "Polski",
            Language::De => "Deutsch",
            Language::Es => "Español",
            Language::Fr => "Français",
            Language::It => "Italiano",
            Language::Nl => "Nederlands",
            Language::Pt => "Português",
            Language::Ru => "Русский",
            Language::Uk => "Українська",
        }
    }

    pub fn auto_detect() -> Self {
        // Check standard locale environment variables
        for var in ["LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"] {
            if let Ok(val) = std::env::var(var) {
                let lower = val.to_lowercase();
                if lower.starts_with("pl") {
                    return Language::Pl;
                } else if lower.starts_with("de") {
                    return Language::De;
                } else if lower.starts_with("es") {
                    return Language::Es;
                } else if lower.starts_with("fr") {
                    return Language::Fr;
                } else if lower.starts_with("it") {
                    return Language::It;
                } else if lower.starts_with("nl") {
                    return Language::Nl;
                } else if lower.starts_with("pt") {
                    return Language::Pt;
                } else if lower.starts_with("ru") {
                    return Language::Ru;
                } else if lower.starts_with("uk") || lower.starts_with("ua") {
                    return Language::Uk;
                } else if lower.starts_with("en") {
                    return Language::En;
                }
            }
        }

        #[cfg(target_os = "windows")]
        {
            // Fallback for Windows PowerShell / CMD locale
            if let Ok(out) = std::process::Command::new("powershell")
                .args(["-NoProfile", "-Command", "[System.Globalization.CultureInfo]::InstalledUICulture.Name"])
                .output()
            {
                let s = String::from_utf8_lossy(&out.stdout).to_lowercase();
                if s.starts_with("pl") { return Language::Pl; }
                if s.starts_with("de") { return Language::De; }
                if s.starts_with("es") { return Language::Es; }
                if s.starts_with("fr") { return Language::Fr; }
                if s.starts_with("it") { return Language::It; }
                if s.starts_with("nl") { return Language::Nl; }
                if s.starts_with("pt") { return Language::Pt; }
                if s.starts_with("ru") { return Language::Ru; }
                if s.starts_with("uk") { return Language::Uk; }
            }
        }

        Language::En
    }

    pub fn t(&self) -> Translations {
        match self {
            Language::Pl => Translations {
                welcome_title: "Witamy w instalatorze BadWords",
                welcome_intro_prefix: "Ten kreator przeprowadzi Cię przez proces instalacji lub zarządzania BadWords w wersji",
                welcome_close_apps: "Zaleca się zamknięcie innych aplikacji przed kontynuowaniem.",
                welcome_prompt: "Kliknij Dalej, aby wybrać działanie, lub Anuluj, aby wyjść.",
                
                menu_title: "Opcje instalacji",
                menu_prompt: "Wybierz opcję za pomocą myszy, strzałek lub klawiszy numerycznych [1-5]:",
                opt_install_title: "Nowa instalacja / Aktualizacja",
                opt_install_desc: "Wdróż pliki, skonfiguruj środowisko Python venv, portable FFmpeg i utwórz skróty.",
                opt_repair_title: "Naprawa instalacji",
                opt_repair_desc: "Sprawdź integralność plików, zainstaluj brakujące zależności i napraw skróty.",
                opt_move_title: "Przenieś instalację",
                opt_move_desc: "Przenieś pliki BadWords oraz środowisko wirtualne do innego folderu.",
                opt_reset_title: "Reset aplikacji",
                opt_reset_desc: "Wyczyść istniejącą instalację, pamięć podręczną i zainstaluj czystą wersję.",
                opt_uninstall_title: "Odinstaluj BadWords",
                opt_uninstall_desc: "Usuń pliki aplikacji, izolowane środowisko venv, skróty i integracje.",
                
                select_path_title: "Wybierz folder instalacji",
                select_path_label: "Zainstaluj BadWords w następującym katalogu:",
                browse_btn: "Przeglądaj...",
                shortcut_desktop: "Utwórz skrót na Pulpicie",
                shortcut_menu: "Utwórz skrót w Menu Start / Aplikacjach",
                
                confirm_title: "Potwierdzenie operacji",
                confirm_uninstall_warn: "Ta operacja całkowicie usunie BadWords z systemu, w tym venv i integracje DaVinci Resolve.",
                confirm_reset_warn: "Ta operacja wyczyści obecną instalację i pobierze/zainstaluje czystą wersję 4.0.0.",
                confirm_repair_info: "Instalator zweryfikuje wszystkie pliki aplikacji, zależności i naprawi uszkodzone elementy.",
                
                complete_title: "Operacja zakończona",
                launch_checkbox: "Uruchom BadWords teraz",
                
                btn_next: "Dalej >",
                btn_back: "< Wstecz",
                btn_cancel: "Anuluj",
                btn_finish: "Zakończ",
                btn_reset: "Resetuj i instaluj",
                btn_uninstall: "Odinstaluj",
                btn_repair: "Napraw",
                btn_move: "Przenieś",
                
                terminal_tooltip: "Otwórz/Zamknij konsolę logów na żywo (T)",
                minimize_tooltip: "Minimalizuj",
                close_tooltip: "Zamknij",
            },

            Language::De => Translations {
                welcome_title: "Willkommen beim BadWords Setup",
                welcome_intro_prefix: "Dieser Assistent führt Sie durch die Installation oder Verwaltung von BadWords Version",
                welcome_close_apps: "Es wird empfohlen, vor dem Fortfahren alle anderen Anwendungen zu schließen.",
                welcome_prompt: "Klicken Sie auf Weiter, um eine Aktion zu wählen, oder auf Abbrechen zum Beenden.",
                
                menu_title: "Installationsoptionen",
                menu_prompt: "Wählen Sie eine Option mit Maus, Pfeiltasten oder Ziffern [1-5]:",
                opt_install_title: "Neuinstallation / Aktualisierung",
                opt_install_desc: "Anwendungsdateien bereitstellen, Python venv, portables FFmpeg einrichten & Verknüpfungen erstellen.",
                opt_repair_title: "Installation reparieren",
                opt_repair_desc: "Dateintegrität prüfen, fehlende Abhängigkeiten neu installieren & Verknüpfungen reparieren.",
                opt_move_title: "Installation verschieben",
                opt_move_desc: "BadWords-Dateien und die virtuelle Umgebung in einen anderen Ordner verschieben.",
                opt_reset_title: "Anwendung zurücksetzen",
                opt_reset_desc: "Bestehende Installation & Cache löschen und frische Version installieren.",
                opt_uninstall_title: "BadWords deinstallieren",
                opt_uninstall_desc: "Anwendungsdateien, venv-Umgebung, Verknüpfungen und Integrationen entfernen.",
                
                select_path_title: "Installationsordner wählen",
                select_path_label: "BadWords in folgendes Verzeichnis installieren:",
                browse_btn: "Durchsuchen...",
                shortcut_desktop: "Desktop-Verknüpfung erstellen",
                shortcut_menu: "Startmenü / Anwendungsmenü-Verknüpfung erstellen",
                
                confirm_title: "Aktion bestätigen",
                confirm_uninstall_warn: "Dieser Vorgang entfernt BadWords, venv und DaVinci Resolve Integrationen vollständig vom System.",
                confirm_reset_warn: "Dieser Vorgang löscht die aktuelle Installation und installiert die Version 4.0.0 neu.",
                confirm_repair_info: "Das Setup überprüft alle Anwendungsdateien und repariert beschädigte Komponenten.",
                
                complete_title: "Vorgang abgeschlossen",
                launch_checkbox: "BadWords jetzt starten",
                
                btn_next: "Weiter >",
                btn_back: "< Zurück",
                btn_cancel: "Abbrechen",
                btn_finish: "Fertigstellen",
                btn_reset: "Zurücksetzen & Installieren",
                btn_uninstall: "Deinstallieren",
                btn_repair: "Reparieren",
                btn_move: "Verschieben",
                
                terminal_tooltip: "Live-Terminalkonsole öffnen/schließen (T)",
                minimize_tooltip: "Minimieren",
                close_tooltip: "Schließen",
            },

            Language::Es => Translations {
                welcome_title: "Bienvenido al Instalador de BadWords",
                welcome_intro_prefix: "Este asistente le guiará a través de la instalación o gestión de BadWords versión",
                welcome_close_apps: "Se recomienda cerrar todas las demás aplicaciones antes de continuar.",
                welcome_prompt: "Haga clic en Siguiente para elegir una acción, o en Cancelar para salir.",
                
                menu_title: "Opciones de instalación",
                menu_prompt: "Seleccione una opción con el ratón, flechas o teclas numéricas [1-5]:",
                opt_install_title: "Instalación limpia / Actualización",
                opt_install_desc: "Desplegar archivos, configurar Python venv, FFmpeg portable y accesos directos.",
                opt_repair_title: "Reparar instalación",
                opt_repair_desc: "Verificar integridad de archivos, reinstalar dependencias y reparar accesos directos.",
                opt_move_title: "Mover instalación",
                opt_move_desc: "Mover los archivos de BadWords y el entorno virtual a otra carpeta.",
                opt_reset_title: "Restablecer aplicación",
                opt_reset_desc: "Borrar instalación existente, caché e instalar una versión limpia.",
                opt_uninstall_title: "Desinstalar BadWords",
                opt_uninstall_desc: "Eliminar archivos de la aplicación, venv aislado, accesos directos e integraciones.",
                
                select_path_title: "Seleccionar carpeta de instalación",
                select_path_label: "Instalar BadWords en el siguiente directorio:",
                browse_btn: "Examinar...",
                shortcut_desktop: "Crear acceso directo en el Escritorio",
                shortcut_menu: "Crear acceso directo en el Menú Inicio",
                
                confirm_title: "Confirmar acción",
                confirm_uninstall_warn: "Esta operación eliminará completamente BadWords, el venv y las integraciones de DaVinci Resolve.",
                confirm_reset_warn: "Esta operación borrará la instalación actual e instalará una copia limpia de la versión 4.0.0.",
                confirm_repair_info: "El instalador verificará los archivos de la aplicación y reparará los componentes dañados.",
                
                complete_title: "Operación completada",
                launch_checkbox: "Iniciar BadWords ahora",
                
                btn_next: "Siguiente >",
                btn_back: "< Atrás",
                btn_cancel: "Cancelar",
                btn_finish: "Finalizar",
                btn_reset: "Restablecer e instalar",
                btn_uninstall: "Desinstalar",
                btn_repair: "Reparar",
                btn_move: "Mover",
                
                terminal_tooltip: "Abrir/Cerrar consola de terminal en vivo (T)",
                minimize_tooltip: "Minimizar",
                close_tooltip: "Cerrar",
            },

            Language::Fr => Translations {
                welcome_title: "Bienvenue dans l'assistant BadWords",
                welcome_intro_prefix: "Cet assistant vous guidera dans l'installation ou la gestion de BadWords version",
                welcome_close_apps: "Il est recommandé de fermer toutes les autres applications avant de continuer.",
                welcome_prompt: "Cliquez sur Suivant pour choisir une action, ou sur Annuler pour quitter.",
                
                menu_title: "Options d'installation",
                menu_prompt: "Sélectionnez une option à la souris, aux flèches ou touches numériques [1-5] :",
                opt_install_title: "Nouvelle installation / Mise à jour",
                opt_install_desc: "Déployer les fichiers, configurer Python venv, FFmpeg portable & créer les raccourcis.",
                opt_repair_title: "Réparer l'installation",
                opt_repair_desc: "Vérifier l'intégrité des fichiers, réinstaller les dépendances et réparer les raccourcis.",
                opt_move_title: "Déplacer l'installation",
                opt_move_desc: "Déplacer les fichiers BadWords et l'environnement virtuel vers un autre dossier.",
                opt_reset_title: "Réinitialiser l'application",
                opt_reset_desc: "Effacer l'installation actuelle, le cache et installer une version propre.",
                opt_uninstall_title: "Désinstaller BadWords",
                opt_uninstall_desc: "Supprimer les fichiers de l'application, le venv, les raccourcis et intégrations.",
                
                select_path_title: "Choisir le dossier d'installation",
                select_path_label: "Installer BadWords dans le répertoire suivant :",
                browse_btn: "Parcourir...",
                shortcut_desktop: "Créer un raccourci sur le Bureau",
                shortcut_menu: "Créer un raccourci dans le Menu Démarrer / Applications",
                
                confirm_title: "Confirmer l'action",
                confirm_uninstall_warn: "Cette action supprimera complètement BadWords, le venv et les intégrations DaVinci Resolve.",
                confirm_reset_warn: "Cette action effacera l'installation actuelle et réinstallera la version 4.0.0.",
                confirm_repair_info: "L'assistant vérifiera tous les fichiers de l'application et réparera les composants endommagés.",
                
                complete_title: "Opération terminée",
                launch_checkbox: "Lancer BadWords maintenant",
                
                btn_next: "Suivant >",
                btn_back: "< Retour",
                btn_cancel: "Annuler",
                btn_finish: "Terminer",
                btn_reset: "Réinitialiser & Installer",
                btn_uninstall: "Désinstaller",
                btn_repair: "Réparer",
                btn_move: "Déplacer",
                
                terminal_tooltip: "Ouvrir/Fermer la console de terminal en direct (T)",
                minimize_tooltip: "Réduire",
                close_tooltip: "Fermer",
            },

            Language::It => Translations {
                welcome_title: "Benvenuti nell'installazione di BadWords",
                welcome_intro_prefix: "Questa procedura guidata vi aiuterà a installare o gestire BadWords versione",
                welcome_close_apps: "Si consiglia di chiudere tutte le altre applicazioni prima di continuare.",
                welcome_prompt: "Fare clic su Avanti per scegliere un'azione, o Annulla per uscire.",
                
                menu_title: "Opzioni di installazione",
                menu_prompt: "Seleziona un'opzione con mouse, frecce o tasti numerici [1-5]:",
                opt_install_title: "Nuova installazione / Aggiornamento",
                opt_install_desc: "Distribuisci file, configura Python venv, FFmpeg portatile e crea collegamenti.",
                opt_repair_title: "Ripara installazione",
                opt_repair_desc: "Verifica l'integrità dei file, reinstalla le dipendenze e ripara i collegamenti.",
                opt_move_title: "Sposta installazione",
                opt_move_desc: "Sposta i file di BadWords e l'ambiente virtuale in un'altra cartella.",
                opt_reset_title: "Ripristina applicazione",
                opt_reset_desc: "Cancella l'installazione esistente, la cache e installa una versione pulita.",
                opt_uninstall_title: "Disinstalla BadWords",
                opt_uninstall_desc: "Rimuovi file dell'applicazione, venv isolato, collegamenti e integrazioni.",
                
                select_path_title: "Seleziona cartella di installazione",
                select_path_label: "Installa BadWords nella seguente cartella:",
                browse_btn: "Sfoglia...",
                shortcut_desktop: "Crea collegamento sul Desktop",
                shortcut_menu: "Crea collegamento nel Menu Start",
                
                confirm_title: "Conferma azione",
                confirm_uninstall_warn: "Questa operazione rimuoverà completamente BadWords, il venv e le integrazioni DaVinci Resolve.",
                confirm_reset_warn: "Questa operazione cancellerà l'installazione corrente e installerà la versione 4.0.0.",
                confirm_repair_info: "Il programma di installazione verificherà i file e riparerà i componenti danneggiati.",
                
                complete_title: "Operazione completata",
                launch_checkbox: "Avvia BadWords adesso",
                
                btn_next: "Avanti >",
                btn_back: "< Indietro",
                btn_cancel: "Annulla",
                btn_finish: "Fine",
                btn_reset: "Ripristina e Installa",
                btn_uninstall: "Disinstalla",
                btn_repair: "Ripara",
                btn_move: "Sposta",
                
                terminal_tooltip: "Apri/Chiudi console terminale live (T)",
                minimize_tooltip: "Riduci a icona",
                close_tooltip: "Chiudi",
            },

            Language::Nl => Translations {
                welcome_title: "Welkom bij BadWords Setup",
                welcome_intro_prefix: "Deze wizard leidt u door de installatie of het beheer van BadWords versie",
                welcome_close_apps: "Het wordt aanbevolen om alle andere toepassingen te sluiten alvorens door te gaan.",
                welcome_prompt: "Klik op Volgende om een actie te kiezen, of op Annuleren om af te sluiten.",
                
                menu_title: "Installatie-opties",
                menu_prompt: "Kies een optie met muis, pijltjestoetsen of cijfers [1-5]:",
                opt_install_title: "Schone installatie / Update",
                opt_install_desc: "Bestanden implementeren, Python venv, draagbare FFmpeg instellen & snelkoppelingen maken.",
                opt_repair_title: "Installatie herstellen",
                opt_repair_desc: "Bestandsintegriteit controleren, ontbrekende pakketten herinstalleren & snelkoppelingen herstellen.",
                opt_move_title: "Installatie verplaatsen",
                opt_move_desc: "BadWords-bestanden en de virtuele omgeving naar een andere map verplaatsen.",
                opt_reset_title: "Applicatie resetten",
                opt_reset_desc: "Bestaande installatie & cache wissen en een schone versie installeren.",
                opt_uninstall_title: "BadWords verwijderen",
                opt_uninstall_desc: "Applicatiebestanden, venv-omgeving, snelkoppelingen en integraties verwijderen.",
                
                select_path_title: "Installatiemap selecteren",
                select_path_label: "Installeer BadWords in de volgende map:",
                browse_btn: "Bladeren...",
                shortcut_desktop: "Bureaublad-snelkoppeling maken",
                shortcut_menu: "Startmenu / Toepassingsmenu snelkoppeling maken",
                
                confirm_title: "Actie bevestigen",
                confirm_uninstall_warn: "Hiermee verwijdert u BadWords, venv en DaVinci Resolve integraties volledig van het systeem.",
                confirm_reset_warn: "Hiermee wist u de huidige installatie en installeert u een schone versie 4.0.0.",
                confirm_repair_info: "Setup controleert de bestanden en herstelt beschadigde componenten.",
                
                complete_title: "Bewerking voltooid",
                launch_checkbox: "BadWords nu starten",
                
                btn_next: "Volgende >",
                btn_back: "< Terug",
                btn_cancel: "Annuleren",
                btn_finish: "Voltooien",
                btn_reset: "Resetten & Installeren",
                btn_uninstall: "Verwijderen",
                btn_repair: "Herstellen",
                btn_move: "Verplaatsen",
                
                terminal_tooltip: "Live terminalconsole openen/sluiten (T)",
                minimize_tooltip: "Minimaliseren",
                close_tooltip: "Sluiten",
            },

            Language::Pt => Translations {
                welcome_title: "Bem-vindo ao Instalador BadWords",
                welcome_intro_prefix: "Este assistente irá guiá-lo na instalação ou gestão do BadWords versão",
                welcome_close_apps: "Recomenda-se fechar todas as outras aplicações antes de continuar.",
                welcome_prompt: "Clique em Avançar para escolher uma ação, ou Cancelar para sair.",
                
                menu_title: "Opções de Instalação",
                menu_prompt: "Selecione uma opção com o rato, setas ou teclas numéricas [1-5]:",
                opt_install_title: "Instalação Limpa / Atualização",
                opt_install_desc: "Implementar ficheiros, configurar Python venv, FFmpeg portátil e criar atalhos.",
                opt_repair_title: "Reparar Instalação",
                opt_repair_desc: "Verificar integridade dos ficheiros, reinstalar dependências e reparar atalhos.",
                opt_move_title: "Mover Instalação",
                opt_move_desc: "Mover os ficheiros do BadWords e o ambiente virtual para outra pasta.",
                opt_reset_title: "Repor Aplicação",
                opt_reset_desc: "Limpar instalação existente, cache e instalar uma versão limpa.",
                opt_uninstall_title: "Desinstalar BadWords",
                opt_uninstall_desc: "Remover ficheiros da aplicação, venv isolado, atalhos e integrações.",
                
                select_path_title: "Selecionar Pasta de Instalação",
                select_path_label: "Instalar o BadWords no seguinte diretório:",
                browse_btn: "Procurar...",
                shortcut_desktop: "Criar atalho no Ambiente de Trabalho",
                shortcut_menu: "Criar atalho no Menu Iniciar",
                
                confirm_title: "Confirmar Ação",
                confirm_uninstall_warn: "Esta operação irá remover completamente o BadWords, venv e integrações do DaVinci Resolve.",
                confirm_reset_warn: "Esta operação irá limpar a instalação atual e instalar uma cópia limpa da versão 4.0.0.",
                confirm_repair_info: "O instalador verificará os ficheiros e reparará os componentes danificados.",
                
                complete_title: "Operação Concluída",
                launch_checkbox: "Iniciar o BadWords agora",
                
                btn_next: "Avançar >",
                btn_back: "< Voltar",
                btn_cancel: "Cancelar",
                btn_finish: "Concluir",
                btn_reset: "Repor & Instalar",
                btn_uninstall: "Desinstalar",
                btn_repair: "Reparar",
                btn_move: "Mover",
                
                terminal_tooltip: "Abrir/Fechar consola de terminal em direto (T)",
                minimize_tooltip: "Minimizar",
                close_tooltip: "Fechar",
            },

            Language::Ru => Translations {
                welcome_title: "Добро пожаловать в установщик BadWords",
                welcome_intro_prefix: "Этот мастер поможет вам установить или управлять BadWords версии",
                welcome_close_apps: "Перед продолжением рекомендуется закрыть все другие приложения.",
                welcome_prompt: "Нажмите Далее, чтобы выбрать действие, или Отмена для выхода.",
                
                menu_title: "Параметры установки",
                menu_prompt: "Выберите вариант мышью, стрелками или цифрами [1-5]:",
                opt_install_title: "Чистая установка / Обновление",
                opt_install_desc: "Развернуть файлы, настроить Python venv, портативный FFmpeg и создать ярлыки.",
                opt_repair_title: "Восстановление установки",
                opt_repair_desc: "Проверить целостность файлов, переустановить зависимости и восстановить ярлыки.",
                opt_move_title: "Перемещение установки",
                opt_move_desc: "Переместить файлы BadWords и виртуальное окружение в другую папку.",
                opt_reset_title: "Сброс приложения",
                opt_reset_desc: "Очистить текущую установку, кэш и установить чистую версию.",
                opt_uninstall_title: "Удалить BadWords",
                opt_uninstall_desc: "Удалить файлы приложения, изолированный venv, ярлыки и интеграции.",
                
                select_path_title: "Выбор папки установки",
                select_path_label: "Установить BadWords в следующий каталог:",
                browse_btn: "Обзор...",
                shortcut_desktop: "Создать ярлык на Рабочем столе",
                shortcut_menu: "Создать ярлык в Меню Пуск / Приложениях",
                
                confirm_title: "Подтверждение действия",
                confirm_uninstall_warn: "Эта операция полностью удалит BadWords, venv и интеграции с DaVinci Resolve.",
                confirm_reset_warn: "Эта операция очистит текущую установку и установит чистую версию 4.0.0.",
                confirm_repair_info: "Установщик проверит файлы приложения и восстановит поврежденные компоненты.",
                
                complete_title: "Операция завершена",
                launch_checkbox: "Запустить BadWords сейчас",
                
                btn_next: "Далее >",
                btn_back: "< Назад",
                btn_cancel: "Отмена",
                btn_finish: "Готово",
                btn_reset: "Сбросить и установить",
                btn_uninstall: "Удалить",
                btn_repair: "Восстановить",
                btn_move: "Переместить",
                
                terminal_tooltip: "Открыть/Закрыть консоль логов в реальном времени (T)",
                minimize_tooltip: "Свернуть",
                close_tooltip: "Закрыть",
            },

            Language::Uk => Translations {
                welcome_title: "Ласкаво просимо до установника BadWords",
                welcome_intro_prefix: "Цей майстер допоможе вам встановити або керувати BadWords версії",
                welcome_close_apps: "Перед продовженням рекомендується закрити всі інші програми.",
                welcome_prompt: "Натисніть Далі, щоб вибрати дію, або Скасувати для виходу.",
                
                menu_title: "Параметри встановлення",
                menu_prompt: "Виберіть варіант мишею, стрілками або цифрами [1-5]:",
                opt_install_title: "Чисте встановлення / Оновлення",
                opt_install_desc: "Розгорнути файли, налаштувати Python venv, портативний FFmpeg та створити ярлики.",
                opt_repair_title: "Відновлення встановлення",
                opt_repair_desc: "Перевірити цілісність файлів, перевстановити залежності та відновити ярлики.",
                opt_move_title: "Переміщення встановлення",
                opt_move_desc: "Перемістити файли BadWords та віртуальне середовище в іншу папку.",
                opt_reset_title: "Скидання програми",
                opt_reset_desc: "Очистити поточне встановлення, кеш та встановити чисту версію.",
                opt_uninstall_title: "Видалити BadWords",
                opt_uninstall_desc: "Видалити файли програми, ізольований venv, ярлики та інтеграції.",
                
                select_path_title: "Вибір папки встановлення",
                select_path_label: "Встановити BadWords у наступний каталог:",
                browse_btn: "Огляд...",
                shortcut_desktop: "Створити ярлик на Робочому столі",
                shortcut_menu: "Створити ярлик у Меню Пуск / Програмах",
                
                confirm_title: "Підтвердження дії",
                confirm_uninstall_warn: "Ця дія повністю видалить BadWords, venv та інтеграції з DaVinci Resolve.",
                confirm_reset_warn: "Ця дія очистить поточне встановлення та встановить чисту копію версії 4.0.0.",
                confirm_repair_info: "Установник перевірить файли програми та відновить пошкоджені компоненти.",
                
                complete_title: "Операцію завершено",
                launch_checkbox: "Запустити BadWords зараз",
                
                btn_next: "Далі >",
                btn_back: "< Назад",
                btn_cancel: "Скасувати",
                btn_finish: "Готово",
                btn_reset: "Скинути та встановити",
                btn_uninstall: "Видалити",
                btn_repair: "Відновити",
                btn_move: "Перемістити",
                
                terminal_tooltip: "Відкрити/Закрити консоль логів у реальному часі (T)",
                minimize_tooltip: "Згорнути",
                close_tooltip: "Закрити",
            },

            Language::En => Translations {
                welcome_title: "Welcome to BadWords Setup",
                welcome_intro_prefix: "This wizard will guide you through the installation or management of BadWords version",
                welcome_close_apps: "It is recommended that you close all other applications before continuing.",
                welcome_prompt: "Click Next to choose an action, or Cancel to exit Setup.",
                
                menu_title: "Installation Options",
                menu_prompt: "Select an option with mouse, arrow keys or numbers [1-5]:",
                opt_install_title: "Fresh Install / Update",
                opt_install_desc: "Deploy application files, set up Python venv, portable FFmpeg & create shortcuts.",
                opt_repair_title: "Repair Installation",
                opt_repair_desc: "Verify application integrity, reinstall corrupted dependencies & repair shortcuts.",
                opt_move_title: "Move Installation",
                opt_move_desc: "Relocate BadWords files and virtual environment to a different folder.",
                opt_reset_title: "Reset Application",
                opt_reset_desc: "Wipe existing installation, cache & clean install fresh release.",
                opt_uninstall_title: "Uninstall BadWords",
                opt_uninstall_desc: "Remove application files, isolated virtual environment, shortcuts & integrations.",
                
                select_path_title: "Select Installation Folder",
                select_path_label: "Install BadWords to the following directory:",
                browse_btn: "Browse...",
                shortcut_desktop: "Create Desktop Shortcut",
                shortcut_menu: "Create Start Menu / Application Menu Shortcut",
                
                confirm_title: "Confirm Action",
                confirm_uninstall_warn: "This operation will completely remove BadWords from your system, including its venv and DaVinci Resolve integrations.",
                confirm_reset_warn: "This operation will wipe your current installation and download/install a fresh copy of version 4.0.0.",
                confirm_repair_info: "Setup will verify all application files, dependencies, and repair any damaged components.",
                
                complete_title: "Operation Completed",
                launch_checkbox: "Launch BadWords now",
                
                btn_next: "Next >",
                btn_back: "< Back",
                btn_cancel: "Cancel",
                btn_finish: "Finish",
                btn_reset: "Reset & Install",
                btn_uninstall: "Uninstall",
                btn_repair: "Repair",
                btn_move: "Move",
                
                terminal_tooltip: "Open/Close Live Terminal Logs (T)",
                minimize_tooltip: "Minimize",
                close_tooltip: "Close",
            },
        }
    }
}

#[allow(dead_code)]
pub struct Translations {
    pub welcome_title: &'static str,
    pub welcome_intro_prefix: &'static str,
    pub welcome_close_apps: &'static str,
    pub welcome_prompt: &'static str,
    
    pub menu_title: &'static str,
    pub menu_prompt: &'static str,
    pub opt_install_title: &'static str,
    pub opt_install_desc: &'static str,
    pub opt_repair_title: &'static str,
    pub opt_repair_desc: &'static str,
    pub opt_move_title: &'static str,
    pub opt_move_desc: &'static str,
    pub opt_reset_title: &'static str,
    pub opt_reset_desc: &'static str,
    pub opt_uninstall_title: &'static str,
    pub opt_uninstall_desc: &'static str,
    
    pub select_path_title: &'static str,
    pub select_path_label: &'static str,
    pub browse_btn: &'static str,
    pub shortcut_desktop: &'static str,
    pub shortcut_menu: &'static str,
    
    pub confirm_title: &'static str,
    pub confirm_uninstall_warn: &'static str,
    pub confirm_reset_warn: &'static str,
    pub confirm_repair_info: &'static str,
    
    pub complete_title: &'static str,
    pub launch_checkbox: &'static str,
    
    pub btn_next: &'static str,
    pub btn_back: &'static str,
    pub btn_cancel: &'static str,
    pub btn_finish: &'static str,
    pub btn_reset: &'static str,
    pub btn_uninstall: &'static str,
    pub btn_repair: &'static str,
    pub btn_move: &'static str,
    
    pub terminal_tooltip: &'static str,
    pub minimize_tooltip: &'static str,
    pub close_tooltip: &'static str,
}

/// Translates engine progress status titles and details into the chosen language in real time
pub fn translate_phrase(text: &str, lang: Language) -> String {
    if text.is_empty() {
        return String::new();
    }

    // Exact matches for status titles and fixed details
    let exact_match: Option<&'static str> = match (text, lang) {
        ("Ready to begin.", Language::Pl) => Some("Gotowy do rozpoczęcia."),
        ("Ready to begin.", Language::De) => Some("Bereit zum Start."),
        ("Ready to begin.", Language::Es) => Some("Listo para comenzar."),
        ("Ready to begin.", Language::Fr) => Some("Prêt à commencer."),
        ("Ready to begin.", Language::It) => Some("Pronto per iniziare."),
        ("Ready to begin.", Language::Nl) => Some("Klaar om te beginnen."),
        ("Ready to begin.", Language::Pt) => Some("Pronto para começar."),
        ("Ready to begin.", Language::Ru) => Some("Готов к началу."),
        ("Ready to begin.", Language::Uk) => Some("Готовий до початку."),

        ("Click Next to choose an action.", Language::Pl) => Some("Kliknij Dalej, aby wybrać działanie."),
        ("Click Next to choose an action.", Language::De) => Some("Klicken Sie auf Weiter, um eine Aktion auszuwählen."),
        ("Click Next to choose an action.", Language::Es) => Some("Haga clic en Siguiente para elegir una acción."),
        ("Click Next to choose an action.", Language::Fr) => Some("Cliquez sur Suivant pour choisir une action."),
        ("Click Next to choose an action.", Language::It) => Some("Fai clic su Avanti per scegliere un'azione."),
        ("Click Next to choose an action.", Language::Nl) => Some("Klik op Volgende om een actie te kiezen."),
        ("Click Next to choose an action.", Language::Pt) => Some("Clique em Avançar para escolher uma ação."),
        ("Click Next to choose an action.", Language::Ru) => Some("Нажмите Далее, чтобы выбрать действие."),
        ("Click Next to choose an action.", Language::Uk) => Some("Натисніть Далі, щоб вибрати дію."),

        ("Checking environment...", Language::Pl) => Some("Sprawdzanie środowiska..."),
        ("Checking environment...", Language::De) => Some("Umgebung wird überprüft..."),
        ("Checking environment...", Language::Es) => Some("Comprobando entorno..."),
        ("Checking environment...", Language::Fr) => Some("Vérification de l'environnement..."),
        ("Checking environment...", Language::It) => Some("Controllo dell'ambiente..."),
        ("Checking environment...", Language::Nl) => Some("Omgeving controleren..."),
        ("Checking environment...", Language::Pt) => Some("Verificando ambiente..."),
        ("Checking environment...", Language::Ru) => Some("Проверка окружения..."),
        ("Checking environment...", Language::Uk) => Some("Перевірка оточення..."),

        ("Detecting Python runtime & GPU hardware", Language::Pl) => Some("Wykrywanie środowiska Python i GPU"),
        ("Detecting Python runtime & GPU hardware", Language::De) => Some("Erkennung von Python & GPU-Hardware"),
        ("Detecting Python runtime & GPU hardware", Language::Es) => Some("Detectando entorno Python y GPU"),
        ("Detecting Python runtime & GPU hardware", Language::Fr) => Some("Détection du runtime Python et du GPU"),
        ("Detecting Python runtime & GPU hardware", Language::It) => Some("Rilevamento runtime Python e GPU"),
        ("Detecting Python runtime & GPU hardware", Language::Nl) => Some("Python-runtime en GPU detecteren"),
        ("Detecting Python runtime & GPU hardware", Language::Pt) => Some("Detectando runtime Python e GPU"),
        ("Detecting Python runtime & GPU hardware", Language::Ru) => Some("Обнаружение Python и оборудования GPU"),
        ("Detecting Python runtime & GPU hardware", Language::Uk) => Some("Виявлення середовища Python та GPU"),

        ("Creating directories...", Language::Pl) => Some("Tworzenie katalogów..."),
        ("Creating directories...", Language::De) => Some("Verzeichnisse erstellen..."),
        ("Creating directories...", Language::Es) => Some("Creando directorios..."),
        ("Creating directories...", Language::Fr) => Some("Création des dossiers..."),
        ("Creating directories...", Language::It) => Some("Creazione cartelle..."),
        ("Creating directories...", Language::Nl) => Some("Mappen aanmaken..."),
        ("Creating directories...", Language::Pt) => Some("Criando diretórios..."),
        ("Creating directories...", Language::Ru) => Some("Создание папок..."),
        ("Creating directories...", Language::Uk) => Some("Створення папок..."),

        ("Setting up application folders", Language::Pl) => Some("Konfigurowanie folderów aplikacji"),
        ("Setting up application folders", Language::De) => Some("Anwendungsordner einrichten"),
        ("Setting up application folders", Language::Es) => Some("Configurando carpetas de la aplicación"),
        ("Setting up application folders", Language::Fr) => Some("Configuration des dossiers d'application"),
        ("Setting up application folders", Language::It) => Some("Configurazione cartelle dell'applicazione"),
        ("Setting up application folders", Language::Nl) => Some("Toepassingsmappen instellen"),
        ("Setting up application folders", Language::Pt) => Some("Configurando pastas do aplicativo"),
        ("Setting up application folders", Language::Ru) => Some("Настройка папок приложения"),
        ("Setting up application folders", Language::Uk) => Some("Налаштування папок програми"),

        ("Deploying application files...", Language::Pl) => Some("Wdrażanie plików aplikacji..."),
        ("Deploying application files...", Language::De) => Some("Anwendungsdateien bereitstellen..."),
        ("Deploying application files...", Language::Es) => Some("Implementando archivos de la aplicación..."),
        ("Deploying application files...", Language::Fr) => Some("Déploiement des fichiers de l'application..."),
        ("Deploying application files...", Language::It) => Some("Distribuzione dei file dell'applicazione..."),
        ("Deploying application files...", Language::Nl) => Some("Toepassingsbestanden implementeren..."),
        ("Deploying application files...", Language::Pt) => Some("Implantando arquivos do aplicativo..."),
        ("Deploying application files...", Language::Ru) => Some("Развертывание файлов приложения..."),
        ("Deploying application files...", Language::Uk) => Some("Розгортання файлів програми..."),

        ("Copying BadWords source and assets", Language::Pl) => Some("Kopiowanie kodu źródłowego i zasobów BadWords"),
        ("Copying BadWords source and assets", Language::De) => Some("Kopieren von BadWords-Quellcode und Assets"),
        ("Copying BadWords source and assets", Language::Es) => Some("Copiando código fuente y recursos de BadWords"),
        ("Copying BadWords source and assets", Language::Fr) => Some("Copie du code source et des ressources de BadWords"),
        ("Copying BadWords source and assets", Language::It) => Some("Copia del codice sorgente e delle risorse"),
        ("Copying BadWords source and assets", Language::Nl) => Some("BadWords-broncode en assets kopiëren"),
        ("Copying BadWords source and assets", Language::Pt) => Some("Copiando código-fonte e recursos do BadWords"),
        ("Copying BadWords source and assets", Language::Ru) => Some("Копирование исходного кода и ресурсов BadWords"),
        ("Copying BadWords source and assets", Language::Uk) => Some("Копіювання вихідного коду та ресурсів BadWords"),

        ("Checking FFmpeg...", Language::Pl) => Some("Sprawdzanie FFmpeg..."),
        ("Checking FFmpeg...", Language::De) => Some("FFmpeg überprüfen..."),
        ("Checking FFmpeg...", Language::Es) => Some("Comprobando FFmpeg..."),
        ("Checking FFmpeg...", Language::Fr) => Some("Vérification de FFmpeg..."),
        ("Checking FFmpeg...", Language::It) => Some("Controllo di FFmpeg..."),
        ("Checking FFmpeg...", Language::Nl) => Some("FFmpeg controleren..."),
        ("Checking FFmpeg...", Language::Pt) => Some("Verificando FFmpeg..."),
        ("Checking FFmpeg...", Language::Ru) => Some("Проверка FFmpeg..."),
        ("Checking FFmpeg...", Language::Uk) => Some("Перевірка FFmpeg..."),

        ("Configuring portable media engine", Language::Pl) => Some("Konfigurowanie przenośnego silnika multimediów"),
        ("Configuring portable media engine", Language::De) => Some("Portables Medien-Engine konfigurieren"),
        ("Configuring portable media engine", Language::Es) => Some("Configurando motor multimedia portátil"),
        ("Configuring portable media engine", Language::Fr) => Some("Configuration du moteur multimédia portable"),
        ("Configuring portable media engine", Language::It) => Some("Configurazione del motore multimediale"),
        ("Configuring portable media engine", Language::Nl) => Some("Draagbare media-engine configureren"),
        ("Configuring portable media engine", Language::Pt) => Some("Configurando mecanismo de mídia portátil"),
        ("Configuring portable media engine", Language::Ru) => Some("Настройка портативного медиа-движка"),
        ("Configuring portable media engine", Language::Uk) => Some("Налаштування портативного медіа-рушія"),

        ("Configuring Python environment...", Language::Pl) => Some("Konfigurowanie środowiska Python..."),
        ("Configuring Python environment...", Language::De) => Some("Python-Umgebung konfigurieren..."),
        ("Configuring Python environment...", Language::Es) => Some("Configurando entorno Python..."),
        ("Configuring Python environment...", Language::Fr) => Some("Configuration de l'environnement Python..."),
        ("Configuring Python environment...", Language::It) => Some("Configurazione dell'ambiente Python..."),
        ("Configuring Python environment...", Language::Nl) => Some("Python-omgeving configureren..."),
        ("Configuring Python environment...", Language::Pt) => Some("Configurando ambiente Python..."),
        ("Configuring Python environment...", Language::Ru) => Some("Настройка окружения Python..."),
        ("Configuring Python environment...", Language::Uk) => Some("Налаштування середовища Python..."),

        ("Setting up isolated virtual environment", Language::Pl) => Some("Tworzenie izolowanego środowiska wirtualnego"),
        ("Setting up isolated virtual environment", Language::De) => Some("Isolierte virtuelle Umgebung einrichten"),
        ("Setting up isolated virtual environment", Language::Es) => Some("Configurando entorno virtual aislado"),
        ("Setting up isolated virtual environment", Language::Fr) => Some("Configuration d'un environnement virtuel"),
        ("Setting up isolated virtual environment", Language::It) => Some("Configurazione dell'ambiente virtuale"),
        ("Setting up isolated virtual environment", Language::Nl) => Some("Geïsoleerde virtuele omgeving instellen"),
        ("Setting up isolated virtual environment", Language::Pt) => Some("Configurando ambiente virtual isolado"),
        ("Setting up isolated virtual environment", Language::Ru) => Some("Настройка изолированного виртуального окружения"),
        ("Setting up isolated virtual environment", Language::Uk) => Some("Налаштування ізольованого віртуального середовища"),

        ("Configuring Python packages...", Language::Pl) => Some("Konfigurowanie pakietów Python..."),
        ("Configuring Python packages...", Language::De) => Some("Python-Pakete konfigurieren..."),
        ("Configuring Python packages...", Language::Es) => Some("Configurando paquetes de Python..."),
        ("Configuring Python packages...", Language::Fr) => Some("Configuration des paquets Python..."),
        ("Configuring Python packages...", Language::It) => Some("Configurazione dei pacchetti Python..."),
        ("Configuring Python packages...", Language::Nl) => Some("Python-pakketten configureren..."),
        ("Configuring Python packages...", Language::Pt) => Some("Configurando pacotes Python..."),
        ("Configuring Python packages...", Language::Ru) => Some("Настройка пакетов Python..."),
        ("Configuring Python packages...", Language::Uk) => Some("Налаштування пакетів Python..."),

        ("Upgrading pip, setuptools & wheel", Language::Pl) => Some("Aktualizowanie pip, setuptools i wheel"),
        ("Upgrading pip, setuptools & wheel", Language::De) => Some("Pip, setuptools & wheel aktualisieren"),
        ("Upgrading pip, setuptools & wheel", Language::Es) => Some("Actualizando pip, setuptools y wheel"),
        ("Upgrading pip, setuptools & wheel", Language::Fr) => Some("Mise à jour de pip, setuptools et wheel"),
        ("Upgrading pip, setuptools & wheel", Language::It) => Some("Aggiornamento di pip, setuptools e wheel"),
        ("Upgrading pip, setuptools & wheel", Language::Nl) => Some("Pip, setuptools & wheel bijwerken"),
        ("Upgrading pip, setuptools & wheel", Language::Pt) => Some("Atualizando pip, setuptools e wheel"),
        ("Upgrading pip, setuptools & wheel", Language::Ru) => Some("Обновление pip, setuptools и wheel"),
        ("Upgrading pip, setuptools & wheel", Language::Uk) => Some("Оновлення pip, setuptools та wheel"),

        ("Installing GUI framework...", Language::Pl) => Some("Instalowanie interfejsu graficznego..."),
        ("Installing GUI framework...", Language::De) => Some("GUI-Framework installieren..."),
        ("Installing GUI framework...", Language::Es) => Some("Instalando interfaz gráfica GUI..."),
        ("Installing GUI framework...", Language::Fr) => Some("Installation du framework GUI..."),
        ("Installing GUI framework...", Language::It) => Some("Installazione del framework GUI..."),
        ("Installing GUI framework...", Language::Nl) => Some("GUI-framework installeren..."),
        ("Installing GUI framework...", Language::Pt) => Some("Instalando framework GUI..."),
        ("Installing GUI framework...", Language::Ru) => Some("Установка графического интерфейса GUI..."),
        ("Installing GUI framework...", Language::Uk) => Some("Встановлення графічного інтерфейсу GUI..."),

        ("Downloading and installing PySide6 Qt framework", Language::Pl) => Some("Pobieranie i instalowanie biblioteki PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::De) => Some("Herunterladen und Installieren von PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Es) => Some("Descargando e instalando PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Fr) => Some("Téléchargement et installation de PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::It) => Some("Download e installazione di PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Nl) => Some("Downloaden en installeren van PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Pt) => Some("Baixando e instalando PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Ru) => Some("Скачивание и установка PySide6 Qt"),
        ("Downloading and installing PySide6 Qt framework", Language::Uk) => Some("Завантаження та встановлення PySide6 Qt"),

        ("Installing AI speech engine...", Language::Pl) => Some("Instalowanie silnika mowy AI..."),
        ("Installing AI speech engine...", Language::De) => Some("KI-Sprach-Engine installieren..."),
        ("Installing AI speech engine...", Language::Es) => Some("Instalando motor de voz IA..."),
        ("Installing AI speech engine...", Language::Fr) => Some("Installation du moteur vocal IA..."),
        ("Installing AI speech engine...", Language::It) => Some("Installazione del motore vocale IA..."),
        ("Installing AI speech engine...", Language::Nl) => Some("AI-spraakengine installeren..."),
        ("Installing AI speech engine...", Language::Pt) => Some("Instalando mecanismo de voz de IA..."),
        ("Installing AI speech engine...", Language::Ru) => Some("Установка речевого движка ИИ..."),
        ("Installing AI speech engine...", Language::Uk) => Some("Встановлення мовного рушія ШІ..."),

        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Pl) => Some("Pobieranie silnika Faster-Whisper i biblioteki PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::De) => Some("Herunterladen der Faster-Whisper KI-Engine & PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Es) => Some("Descargando motor Faster-Whisper IA y PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Fr) => Some("Téléchargement du moteur Faster-Whisper IA et PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::It) => Some("Download del motore Faster-Whisper IA e PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Nl) => Some("Faster-Whisper AI-engine & PyPDF downloaden"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Pt) => Some("Baixando mecanismo Faster-Whisper IA e PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Ru) => Some("Скачивание движка Faster-Whisper ИИ и PyPDF"),
        ("Downloading Faster-Whisper AI engine & PyPDF", Language::Uk) => Some("Завантаження рушія Faster-Whisper ШІ та PyPDF"),

        ("Installing GPU acceleration...", Language::Pl) => Some("Instalowanie akceleracji GPU..."),
        ("Installing GPU acceleration...", Language::De) => Some("GPU-Beschleunigung installieren..."),
        ("Installing GPU acceleration...", Language::Es) => Some("Instalando aceleración GPU..."),
        ("Installing GPU acceleration...", Language::Fr) => Some("Installation de l'accélération GPU..."),
        ("Installing GPU acceleration...", Language::It) => Some("Installazione dell'accelerazione GPU..."),
        ("Installing GPU acceleration...", Language::Nl) => Some("GPU-versnelling installeren..."),
        ("Installing GPU acceleration...", Language::Pt) => Some("Instalando aceleração por GPU..."),
        ("Installing GPU acceleration...", Language::Ru) => Some("Установка ускорения GPU..."),
        ("Installing GPU acceleration...", Language::Uk) => Some("Встановлення прискорення GPU..."),

        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Pl) => Some("Pobieranie bibliotek NVIDIA CUDA 12 (cuBLAS, cuDNN)"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::De) => Some("Herunterladen von NVIDIA CUDA 12 Bibliotheken"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Es) => Some("Descargando bibliotecas NVIDIA CUDA 12 (cuBLAS, cuDNN)"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Fr) => Some("Téléchargement des bibliothèques NVIDIA CUDA 12"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::It) => Some("Download delle librerie NVIDIA CUDA 12"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Nl) => Some("NVIDIA CUDA 12-bibliotheken downloaden"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Pt) => Some("Baixando bibliotecas NVIDIA CUDA 12"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Ru) => Some("Скачивание библиотек NVIDIA CUDA 12 (cuBLAS, cuDNN)"),
        ("Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)", Language::Uk) => Some("Завантаження бібліотек NVIDIA CUDA 12 (cuBLAS, cuDNN)"),

        ("Creating library links...", Language::Pl) => Some("Tworzenie dowiązań bibliotek..."),
        ("Creating library links...", Language::De) => Some("Bibliotheksverknüpfungen erstellen..."),
        ("Creating library links...", Language::Es) => Some("Creando enlaces de bibliotecas..."),
        ("Creating library links...", Language::Fr) => Some("Création des liens de bibliothèques..."),
        ("Creating library links...", Language::It) => Some("Creazione dei collegamenti alle librerie..."),
        ("Creating library links...", Language::Nl) => Some("Bibliotheekkoppelingen maken..."),
        ("Creating library links...", Language::Pt) => Some("Criando links de bibliotecas..."),
        ("Creating library links...", Language::Ru) => Some("Создание ссылок на библиотеки..."),
        ("Creating library links...", Language::Uk) => Some("Створення посилань на бібліотеки..."),

        ("Linking site-packages for DaVinci Resolve integration", Language::Pl) => Some("Łączenie pakietów dla integracji z DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::De) => Some("Site-packages für DaVinci Resolve verknüpfen"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Es) => Some("Enlazando site-packages para DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Fr) => Some("Liaison des site-packages pour DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::It) => Some("Collegamento site-packages per DaVinci"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Nl) => Some("Site-packages koppelen voor DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Pt) => Some("Vinculando site-packages para DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Ru) => Some("Привязка site-packages для DaVinci Resolve"),
        ("Linking site-packages for DaVinci Resolve integration", Language::Uk) => Some("Прив'язка site-packages для DaVinci Resolve"),

        ("Configuring DaVinci Resolve...", Language::Pl) => Some("Konfigurowanie DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::De) => Some("DaVinci Resolve konfigurieren..."),
        ("Configuring DaVinci Resolve...", Language::Es) => Some("Configurando DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::Fr) => Some("Configuration de DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::It) => Some("Configurazione di DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::Nl) => Some("DaVinci Resolve configureren..."),
        ("Configuring DaVinci Resolve...", Language::Pt) => Some("Configurando DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::Ru) => Some("Настройка DaVinci Resolve..."),
        ("Configuring DaVinci Resolve...", Language::Uk) => Some("Налаштування DaVinci Resolve..."),

        ("Writing Fusion utility script wrappers", Language::Pl) => Some("Zapisywanie skryptów integracji dla Fusion"),
        ("Writing Fusion utility script wrappers", Language::De) => Some("Fusion-Utility-Skript-Wrapper schreiben"),
        ("Writing Fusion utility script wrappers", Language::Es) => Some("Escribiendo scripts de integración para Fusion"),
        ("Writing Fusion utility script wrappers", Language::Fr) => Some("Écriture des wrappers de script Fusion"),
        ("Writing Fusion utility script wrappers", Language::It) => Some("Scrittura dei wrapper di script per Fusion"),
        ("Writing Fusion utility script wrappers", Language::Nl) => Some("Fusion-hulpscriptwrappers schrijven"),
        ("Writing Fusion utility script wrappers", Language::Pt) => Some("Escrevendo wrappers para o Fusion"),
        ("Writing Fusion utility script wrappers", Language::Ru) => Some("Запись скриптов интеграции для Fusion"),
        ("Writing Fusion utility script wrappers", Language::Uk) => Some("Запис скриптів інтеграції для Fusion"),

        ("Creating shortcuts...", Language::Pl) => Some("Tworzenie skrótów..."),
        ("Creating shortcuts...", Language::De) => Some("Verknüpfungen erstellen..."),
        ("Creating shortcuts...", Language::Es) => Some("Creando accesos directos..."),
        ("Creating shortcuts...", Language::Fr) => Some("Création des raccourcis..."),
        ("Creating shortcuts...", Language::It) => Some("Creazione collegamenti..."),
        ("Creating shortcuts...", Language::Nl) => Some("Snelkoppelingen maken..."),
        ("Creating shortcuts...", Language::Pt) => Some("Criando atalhos..."),
        ("Creating shortcuts...", Language::Ru) => Some("Создание ярлыков..."),
        ("Creating shortcuts...", Language::Uk) => Some("Створення ярликів..."),

        ("Registering application in OS", Language::Pl) => Some("Rejestrowanie aplikacji w systemie"),
        ("Registering application in OS", Language::De) => Some("Anwendung im Betriebssystem registrieren"),
        ("Registering application in OS", Language::Es) => Some("Registrando aplicación en el sistema"),
        ("Registering application in OS", Language::Fr) => Some("Enregistrement de l'application dans le système"),
        ("Registering application in OS", Language::It) => Some("Registrazione dell'applicazione nel sistema"),
        ("Registering application in OS", Language::Nl) => Some("Applicatie registreren in besturingssysteem"),
        ("Registering application in OS", Language::Pt) => Some("Registrando aplicativo no sistema"),
        ("Registering application in OS", Language::Ru) => Some("Регистрация приложения в системе"),
        ("Registering application in OS", Language::Uk) => Some("Реєстрація програми в системі"),

        ("Transferring files...", Language::Pl) => Some("Przenoszenie plików..."),
        ("Transferring files...", Language::De) => Some("Dateien übertragen..."),
        ("Transferring files...", Language::Es) => Some("Transfiriendo archivos..."),
        ("Transferring files...", Language::Fr) => Some("Transfert des fichiers..."),
        ("Transferring files...", Language::It) => Some("Trasferimento dei file..."),
        ("Transferring files...", Language::Nl) => Some("Bestanden overdragen..."),
        ("Transferring files...", Language::Pt) => Some("Transferindo arquivos..."),
        ("Transferring files...", Language::Ru) => Some("Перенос файлов..."),
        ("Transferring files...", Language::Uk) => Some("Перенесення файлів..."),

        ("Reconfiguring Python environment...", Language::Pl) => Some("Aktualizowanie ścieżek środowiska Python..."),
        ("Reconfiguring Python environment...", Language::De) => Some("Python-Umgebungspfad anpassen..."),
        ("Reconfiguring Python environment...", Language::Es) => Some("Reconfigurando rutas de Python..."),
        ("Reconfiguring Python environment...", Language::Fr) => Some("Reconfiguration des chemins Python..."),
        ("Reconfiguring Python environment...", Language::It) => Some("Riconfigurazione dei percorsi Python..."),
        ("Reconfiguring Python environment...", Language::Nl) => Some("Python-omgevingspaden bijwerken..."),
        ("Reconfiguring Python environment...", Language::Pt) => Some("Reconfigurando caminhos do Python..."),
        ("Reconfiguring Python environment...", Language::Ru) => Some("Обновление путей среды Python..."),
        ("Reconfiguring Python environment...", Language::Uk) => Some("Оновлення шляхів середовища Python..."),

        ("Updating virtual environment paths", Language::Pl) => Some("Aktualizowanie ścieżek środowiska wirtualnego"),
        ("Updating virtual environment paths", Language::De) => Some("Pfade der virtuellen Umgebung aktualisieren"),
        ("Updating virtual environment paths", Language::Es) => Some("Actualizando rutas del entorno virtual"),
        ("Updating virtual environment paths", Language::Fr) => Some("Mise à jour des chemins d'environnement virtuel"),
        ("Updating virtual environment paths", Language::It) => Some("Aggiornamento percorsi ambiente virtuale"),
        ("Updating virtual environment paths", Language::Nl) => Some("Paden van virtuele omgeving bijwerken"),
        ("Updating virtual environment paths", Language::Pt) => Some("Atualizando caminhos do ambiente virtual"),
        ("Updating virtual environment paths", Language::Ru) => Some("Обновление путей виртуального окружения"),
        ("Updating virtual environment paths", Language::Uk) => Some("Оновлення шляхів віртуального середовища"),

        ("Updating wrappers...", Language::Pl) => Some("Aktualizowanie skryptów DaVinci..."),
        ("Updating wrappers...", Language::De) => Some("DaVinci-Wrapper aktualisieren..."),
        ("Updating wrappers...", Language::Es) => Some("Actualizando wrappers de DaVinci..."),
        ("Updating wrappers...", Language::Fr) => Some("Mise à jour des wrappers DaVinci..."),
        ("Updating wrappers...", Language::It) => Some("Aggiornamento wrapper DaVinci..."),
        ("Updating wrappers...", Language::Nl) => Some("DaVinci-wrappers bijwerken..."),
        ("Updating wrappers...", Language::Pt) => Some("Atualizando wrappers do DaVinci..."),
        ("Updating wrappers...", Language::Ru) => Some("Обновление скриптов DaVinci..."),
        ("Updating wrappers...", Language::Uk) => Some("Оновлення скриптів DaVinci..."),

        ("Updating DaVinci Resolve script paths", Language::Pl) => Some("Aktualizowanie ścieżek integracji z DaVinci"),
        ("Updating DaVinci Resolve script paths", Language::De) => Some("Skriptpfade für DaVinci Resolve aktualisieren"),
        ("Updating DaVinci Resolve script paths", Language::Es) => Some("Actualizando rutas de script de DaVinci"),
        ("Updating DaVinci Resolve script paths", Language::Fr) => Some("Mise à jour des chemins DaVinci Resolve"),
        ("Updating DaVinci Resolve script paths", Language::It) => Some("Aggiornamento percorsi script DaVinci"),
        ("Updating DaVinci Resolve script paths", Language::Nl) => Some("DaVinci Resolve-scriptpaden bijwerken"),
        ("Updating DaVinci Resolve script paths", Language::Pt) => Some("Atualizando caminhos de script do DaVinci"),
        ("Updating DaVinci Resolve script paths", Language::Ru) => Some("Обновление путей скриптов DaVinci"),
        ("Updating DaVinci Resolve script paths", Language::Uk) => Some("Оновлення шляхів скриптів DaVinci"),

        ("Cleaning old directory...", Language::Pl) => Some("Czyszczenie starej lokalizacji..."),
        ("Cleaning old directory...", Language::De) => Some("Altes Verzeichnis bereinigen..."),
        ("Cleaning old directory...", Language::Es) => Some("Limpiando directorio antiguo..."),
        ("Cleaning old directory...", Language::Fr) => Some("Nettoyage de l'ancien dossier..."),
        ("Cleaning old directory...", Language::It) => Some("Pulizia della vecchia cartella..."),
        ("Cleaning old directory...", Language::Nl) => Some("Oude map opschonen..."),
        ("Cleaning old directory...", Language::Pt) => Some("Limpando diretório antigo..."),
        ("Cleaning old directory...", Language::Ru) => Some("Очистка старого каталога..."),
        ("Cleaning old directory...", Language::Uk) => Some("Очищення старого каталогу..."),

        ("Removing old installation files", Language::Pl) => Some("Usuwanie plików ze starej lokalizacji"),
        ("Removing old installation files", Language::De) => Some("Alte Installationsdateien entfernen"),
        ("Removing old installation files", Language::Es) => Some("Eliminando archivos de la instalación anterior"),
        ("Removing old installation files", Language::Fr) => Some("Suppression des anciens fichiers d'installation"),
        ("Removing old installation files", Language::It) => Some("Rimozione dei vecchi file di installazione"),
        ("Removing old installation files", Language::Nl) => Some("Oude installatiebestanden verwijderen"),
        ("Removing old installation files", Language::Pt) => Some("Removendo arquivos da instalação antiga"),
        ("Removing old installation files", Language::Ru) => Some("Удаление файлов старой установки"),
        ("Removing old installation files", Language::Uk) => Some("Видалення файлів старої установки"),

        ("Removing files...", Language::Pl) => Some("Usuwanie plików..."),
        ("Removing files...", Language::De) => Some("Dateien entfernen..."),
        ("Removing files...", Language::Es) => Some("Eliminando archivos..."),
        ("Removing files...", Language::Fr) => Some("Suppression des fichiers..."),
        ("Removing files...", Language::It) => Some("Rimozione dei file..."),
        ("Removing files...", Language::Nl) => Some("Bestanden verwijderen..."),
        ("Removing files...", Language::Pt) => Some("Removendo arquivos..."),
        ("Removing files...", Language::Ru) => Some("Удаление файлов..."),
        ("Removing files...", Language::Uk) => Some("Видалення файлів..."),

        ("Deleting installation folder", Language::Pl) => Some("Usuwanie folderu instalacji"),
        ("Deleting installation folder", Language::De) => Some("Installationsordner löschen"),
        ("Deleting installation folder", Language::Es) => Some("Eliminando carpeta de instalación"),
        ("Deleting installation folder", Language::Fr) => Some("Suppression du dossier d'installation"),
        ("Deleting installation folder", Language::It) => Some("Eliminazione della cartella di installazione"),
        ("Deleting installation folder", Language::Nl) => Some("Installatiemap verwijderen"),
        ("Deleting installation folder", Language::Pt) => Some("Excluindo pasta de instalação"),
        ("Deleting installation folder", Language::Ru) => Some("Удаление папки установки"),
        ("Deleting installation folder", Language::Uk) => Some("Видалення папки встановлення"),

        ("Removing integrations...", Language::Pl) => Some("Usuwanie integracji..."),
        ("Removing integrations...", Language::De) => Some("Integrationen entfernen..."),
        ("Removing integrations...", Language::Es) => Some("Eliminando integraciones..."),
        ("Removing integrations...", Language::Fr) => Some("Suppression des intégrations..."),
        ("Removing integrations...", Language::It) => Some("Rimozione delle integrazioni..."),
        ("Removing integrations...", Language::Nl) => Some("Integraties verwijderen..."),
        ("Removing integrations...", Language::Pt) => Some("Removendo integrações..."),
        ("Removing integrations...", Language::Ru) => Some("Удаление интеграций..."),
        ("Removing integrations...", Language::Uk) => Some("Видалення інтеграцій..."),

        ("Deleting DaVinci Resolve wrappers", Language::Pl) => Some("Usuwanie skryptów z DaVinci Resolve"),
        ("Deleting DaVinci Resolve wrappers", Language::De) => Some("DaVinci Resolve-Wrapper löschen"),
        ("Deleting DaVinci Resolve wrappers", Language::Es) => Some("Eliminando scripts de DaVinci Resolve"),
        ("Deleting DaVinci Resolve wrappers", Language::Fr) => Some("Suppression des wrappers DaVinci"),
        ("Deleting DaVinci Resolve wrappers", Language::It) => Some("Eliminazione dei wrapper DaVinci"),
        ("Deleting DaVinci Resolve wrappers", Language::Nl) => Some("DaVinci Resolve-wrappers verwijderen"),
        ("Deleting DaVinci Resolve wrappers", Language::Pt) => Some("Excluindo wrappers do DaVinci Resolve"),
        ("Deleting DaVinci Resolve wrappers", Language::Ru) => Some("Удаление скриптов DaVinci Resolve"),
        ("Deleting DaVinci Resolve wrappers", Language::Uk) => Some("Видалення скриптів DaVinci Resolve"),

        ("Cleaning system entries...", Language::Pl) => Some("Czyszczenie wpisów systemowych..."),
        ("Cleaning system entries...", Language::De) => Some("Systemeinträge bereinigen..."),
        ("Cleaning system entries...", Language::Es) => Some("Limpiando entradas del sistema..."),
        ("Cleaning system entries...", Language::Fr) => Some("Nettoyage des entrées système..."),
        ("Cleaning system entries...", Language::It) => Some("Pulizia delle voci di sistema..."),
        ("Cleaning system entries...", Language::Nl) => Some("Systeemvermeldingen opschonen..."),
        ("Cleaning system entries...", Language::Pt) => Some("Limpando entradas do sistema..."),
        ("Cleaning system entries...", Language::Ru) => Some("Очистка записей в системе..."),
        ("Cleaning system entries...", Language::Uk) => Some("Очищення системних записів..."),

        ("Removing desktop launchers and shortcuts", Language::Pl) => Some("Usuwanie skrótów pulpitu i menu start"),
        ("Removing desktop launchers and shortcuts", Language::De) => Some("Desktop-Starter & Verknüpfungen entfernen"),
        ("Removing desktop launchers and shortcuts", Language::Es) => Some("Eliminando accesos directos del escritorio"),
        ("Removing desktop launchers and shortcuts", Language::Fr) => Some("Suppression des raccourcis du bureau"),
        ("Removing desktop launchers and shortcuts", Language::It) => Some("Rimozione collegamenti sul desktop"),
        ("Removing desktop launchers and shortcuts", Language::Nl) => Some("Bureaubladsnelkoppelingen verwijderen"),
        ("Removing desktop launchers and shortcuts", Language::Pt) => Some("Removendo atalhos da área de trabalho"),
        ("Removing desktop launchers and shortcuts", Language::Ru) => Some("Удаление ярлыков с рабочего стола"),
        ("Removing desktop launchers and shortcuts", Language::Uk) => Some("Видалення ярликів із робочого столу"),

        _ => None,
    };

    if let Some(m) = exact_match {
        return m.to_string();
    }

    // Dynamic prefix translations (e.g. "Copying: ...", "Removing: ...", "Downloading ...")
    if let Some(rest) = text.strip_prefix("Copying: ") {
        let prefix = match lang {
            Language::Pl => "Kopiowanie: ",
            Language::De => "Kopieren: ",
            Language::Es => "Copiando: ",
            Language::Fr => "Copie : ",
            Language::It => "Copia: ",
            Language::Nl => "Kopiëren: ",
            Language::Pt => "Copiando: ",
            Language::Ru => "Копирование: ",
            Language::Uk => "Копіювання: ",
            _ => "Copying: ",
        };
        return format!("{}{}", prefix, rest);
    }

    if let Some(rest) = text.strip_prefix("Removing: ") {
        let prefix = match lang {
            Language::Pl => "Usuwanie: ",
            Language::De => "Entfernen: ",
            Language::Es => "Eliminando: ",
            Language::Fr => "Suppression : ",
            Language::It => "Rimozione: ",
            Language::Nl => "Verwijderen: ",
            Language::Pt => "Removendo: ",
            Language::Ru => "Удаление: ",
            Language::Uk => "Видалення: ",
            _ => "Removing: ",
        };
        return format!("{}{}", prefix, rest);
    }

    if let Some(rest) = text.strip_prefix("Downloading ") {
        let prefix = match lang {
            Language::Pl => "Pobieranie ",
            Language::De => "Herunterladen ",
            Language::Es => "Descargando ",
            Language::Fr => "Téléchargement ",
            Language::It => "Download ",
            Language::Nl => "Downloaden ",
            Language::Pt => "Baixando ",
            Language::Ru => "Скачивание ",
            Language::Uk => "Завантаження ",
            _ => "Downloading ",
        };
        return format!("{}{}", prefix, rest);
    }

    text.to_string()
}
