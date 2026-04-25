#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: config.py
ROLE: Data Layer / Configuration
DESCRIPTION:
Stores constants, default settings, color palette,
translations (i18n), algorithm parameters, and supported languages data.
This is a pure data store, independent of GUI libraries.
"""

import platform

# ==========================================
# APPLICATION INFO
# ==========================================
APP_NAME = "BadWords"
VERSION = "2.0.2"
POSTHOG_API_KEY = "phc_gSONi06SQLOiNeagPaUobqvm98IyXiaF91PJ0Xu9lbx" 
POSTHOG_HOST = "https://eu.i.posthog.com" 

# ==========================================
# WINDOW & GUI SETTINGS
# ==========================================
# Base dimensions for 100% DPI (96 PPI)
CFG_WINDOW_W_BASE = 400
CFG_WINDOW_H_BASE = 740 

def get_system_font_name():
    """
    Returns preferred font depending on the operating system.
    Does not require GUI library (tkinter).
    """
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    if system == "Darwin": # macOS
        return "Helvetica Neue"
    # Linux / Fallback
    return "Noto Sans"

UI_FONT_NAME = get_system_font_name()

# ==========================================
# ANALYSIS PARAMETERS
# ==========================================
DEFAULT_BAD_WORDS = ["yyy", "eee", "aaa", "umm", "uh", "ah", "mhm"]
SIMILARITY_THRESHOLD = 0.45

# ==========================================
# COLOR PALETTE
# ==========================================
# Main Layout (Dark Theme)
BG_COLOR = "#1c1c1c"
SIDEBAR_BG = "#262626"
INPUT_BG = "#333333"
INPUT_FG = "#ffffff"
FG_COLOR = "#d9d9d9"
NOTE_COL = "#808080"
SEPARATOR_COL = "#404040"
FOOTER_COLOR = "#1c1c1c"
DISCLAIMER_FG = "#555555"

# Scrollbar
SCROLL_BG = "#2b2b2b"
SCROLL_FG = "#555555"
SCROLL_ACTIVE = "#777777"

# Menu
MENU_BG = "#2b2b2b"
MENU_FG = "#ffffff"
GEAR_COLOR = "#a0a0a0"

# Buttons
BTN_BG = "#5865F2"             # Blurple
BTN_FG = "#ffffff"
BTN_ACTIVE = "#4752c4"

BTN_GHOST_BG = "#404040"
BTN_GHOST_ACTIVE = "#505050"

CANCEL_BG = "#b33a3a"
CANCEL_ACTIVE = "#8f2e2e"

# Checkbox
CHECKBOX_BG = "white"

# Progress Bar
PROGRESS_HEIGHT = 24
PROGRESS_TRACK_COLOR = "#333333"
PROGRESS_FILL_COLOR = "#23a559" 
STATUS_TEXT_COLOR = "#eeeeee"

# --- Word Marking Colors ---
WORD_NORMAL_FG    = "#dcddde"
WORD_BAD_BG       = "#ed4245" # Red (Filler/Error)
WORD_BAD_FG       = "#ffffff"
WORD_REPEAT_BG    = "#2980b9" # Blue (Repeat)
WORD_REPEAT_FG    = "#ffffff"
WORD_TYPO_BG      = "#27ae60" # Green (Typo)
WORD_TYPO_FG      = "#ffffff"
WORD_HOVER_BG     = "#4f545c"
WORD_MISSING_BG   = "#f1c40f" # Yellow (Missing in audio)
WORD_MISSING_FG   = "#000000"
WORD_INAUDIBLE_BG = "#8B4513" # Brown (Inaudible)
WORD_INAUDIBLE_FG = "#ffffff"

# ==========================================
# SUPPORTED LANGUAGES (WHISPER)
# ==========================================
# Key: Whisper Code (ISO), Value: Native Name
SUPPORTED_LANGUAGES = {
    "Auto": "Auto",
    "af": "Afrikaans",
    "am": "አማርኛ", # Amharic
    "ar": "العربية", # Arabic
    "as": "অসমীয়া", # Assamese
    "az": "Azərbaycan", # Azerbaijani
    "ba": "Башҡортса", # Bashkir
    "be": "Беларуская", # Belarusian
    "bg": "Български", # Bulgarian
    "bn": "বাংলা", # Bengali
    "bo": "བོད་སྐད་", # Tibetan
    "br": "Brezhoneg", # Breton
    "bs": "Bosanski", # Bosnian
    "ca": "Català", # Catalan
    "cs": "Čeština", # Czech
    "cy": "Cymraeg", # Welsh
    "da": "Dansk", # Danish
    "de": "Deutsch", # German
    "el": "Ελληνικά", # Greek
    "en": "English",
    "es": "Español", # Spanish
    "et": "Eesti", # Estonian
    "eu": "Euskara", # Basque
    "fa": "فارسی", # Persian
    "fi": "Suomi", # Finnish
    "fo": "Føroyskt", # Faroese
    "fr": "Français", # French
    "gl": "Galego", # Galician
    "gu": "ગુજરાતી", # Gujarati
    "ha": "Hausa",
    "haw": "ʻŌlelo Hawaiʻi", # Hawaiian
    "he": "עברית", # Hebrew
    "hi": "हिन्दी", # Hindi
    "hr": "Hrvatski", # Croatian
    "ht": "Kreyòl Ayisyen", # Haitian Creole
    "hu": "Magyar", # Hungarian
    "hy": "Հայերեն", # Armenian
    "id": "Bahasa Indonesia", # Indonesian
    "is": "Íslenska", # Icelandic
    "it": "Italiano", # Italian
    "ja": "日本語", # Japanese
    "jw": "Basa Jawa", # Javanese
    "ka": "ქართული", # Georgian
    "kk": "Қазақша", # Kazakh
    "km": "ភាសាខ្មែរ", # Khmer
    "kn": "ಕನ್ನಡ", # Kannada
    "ko": "한국어", # Korean
    "la": "Latina", # Latin
    "lb": "Lëtzebuergesch", # Luxembourgish
    "ln": "Lingála", # Lingala
    "lo": "ພາສາລາວ", # Lao
    "lt": "Lietuvių", # Lithuanian
    "lv": "Latviešu", # Latvian
    "mg": "Malagasy",
    "mi": "Te Reo Māori", # Maori
    "mk": "Македонски", # Macedonian
    "ml": "മലയാളം", # Malayalam
    "mn": "Монгол", # Mongolian
    "mr": "मराठी", # Marathi
    "ms": "Bahasa Melayu", # Malay
    "mt": "Malti", # Maltese
    "my": "ဗမာစာ", # Myanmar
    "ne": "नेपाली", # Nepali
    "nl": "Nederlands", # Dutch
    "nn": "Norsk nynorsk", # Norwegian Nynorsk
    "no": "Norsk", # Norwegian
    "oc": "Occitan",
    "pa": "ਪੰਜਾਬੀ", # Punjabi
    "pl": "Polski", # Polish
    "ps": "پښتو", # Pashto
    "pt": "Português", # Portuguese
    "ro": "Română", # Romanian
    "ru": "Русский", # Russian
    "sa": "संस्कृतम्", # Sanskrit
    "sd": "سنڌي", # Sindhi
    "si": "සිංහල", # Sinhala
    "sk": "Slovenčina", # Slovak
    "sl": "Slovenščina", # Slovenian
    "sn": "ChiShona", # Shona
    "so": "Soomaali", # Somali
    "sq": "Shqip", # Albanian
    "sr": "Српски", # Serbian
    "su": "Basa Sunda", # Sundanese
    "sv": "Svenska", # Swedish
    "sw": "Kiswahili", # Swahili
    "ta": "தமிழ்", # Tamil
    "te": "తెలుగు", # Telugu
    "tg": "Тоҷикӣ", # Tajik
    "th": "ไทย", # Thai
    "tk": "Türkmen", # Turkmen
    "tl": "Tagalog",
    "tr": "Türkçe", # Turkish
    "tt": "Tatarça", # Tatar
    "uk": "Українська", # Ukrainian
    "ur": "اردو", # Urdu
    "uz": "Oʻzbek", # Uzbek
    "vi": "Tiếng Việt", # Vietnamese
    "yi": "ייִדיש", # Yiddish
    "yo": "Yorùbá", # Yoruba
    "zh": "中文", # Chinese
    "yue": "粵語", # Cantonese
}

# ==========================================
# TRANSLATIONS (I18N)
# ==========================================
# Supported Languages: English (en), Polish (pl), German (de), Spanish (es), 
# French (fr), Italian (it), Portuguese (pt), Ukrainian (uk), Dutch (nl), Russian (ru)

TRANS = {
    "en": {
        "name": "English",
        "title": "BadWords",
        "header_main": "BadWords Config",
        "sec_whisper": "WHISPER & MODEL",
        "lbl_lang": "Language:",
        "lbl_model": "Model:",
        "lbl_device": "Device:",
        "lbl_fillers": "Filler Words:",
        "btn_edit_fillers": "Edit list...",
        "title_edit_fillers": "Filler Words Editor",
        "lbl_fillers_instr": "Edit filler words (comma separated):",
        "sec_sync": "AUDIO SYNC (SECONDS)",
        "lbl_offset": "Offset (s):",
        "lbl_pad": "Padding (s):",
        "lbl_snap": "Snap Max (s):",
        "lbl_thresh": "Silence Thresh (dB):",
        "chk_reviewer": "Enable Script Reviewer",
        
        "btn_analyze": "ANALYZE",
        "btn_cancel": "Cancel",
        "btn_quit": "Quit",
        "btn_apply": "Apply",
        "btn_generate": "Assemble",
        "btn_import_proj": "Import Project",
        "btn_export_proj": "Export Project",
        "btn_dl_model": "Download Model",
        "lbl_model_installed": "Model Installed ✔️",
        "header_rev_script": "Original Script (Yellow = Missing in Audio)",
        "header_rev_trans": "Transcribed Audio (Work Area)",
        "header_rev_tools": "Tools",
        "lbl_mark_color": "Marking Mode:",
        "rb_mark_red": "RED (Cut/Filler)",
        "rb_mark_blue": "BLUE (Retake)",
        "rb_mark_green": "GREEN (Typo)",
        "rb_mark_white": "ERASER (Clear)",
        "chk_auto_filler": "Mark filler words automatically",
        "chk_auto_del": "Delete red clips automatically (may be imprecise)",
        "btn_import": "Import Script",
        "btn_compare": "Analyze (Compare)",
        "btn_standalone": "Analyze (Standalone)",
        "chk_silence_cut": "Detect and cut out silence",
        "chk_silence_mark": "Detect and mark silence (tan)",
        
        # Inaudible & Typos Checkboxes
        "chk_show_inaudible": "Show inaudible fragments",
        "chk_mark_inaudible": "Mark inaudible fragments with brown",
        "chk_show_typos": "Show detected typos",
        
        "btn_clear_trans": "Clear Transcript",
        "msg_confirm_clear": "Are you sure you want to clear all markings?",
        "btn_clear_confirm": "Clear",
        
        # Status Messages
        "status_ready": "Ready.",
        "status_initializing": "Initializing...",
        "status_render": "Rendering audio...",
        "status_norm": "Normalizing audio...",
        "status_silence": "Detecting silence...",
        "status_check_model": "Verifying/Downloading model {model}...",
        "status_whisper_run": "Transcribing audio ({model})...",
        "status_whisper_dl": "Downloading {model}...",
        "status_processing": "Processing data...",
        "status_generating": "Assembling timeline...",
        "status_cleanup": "Cleaning temporary files...",
        "status_done": "Done!",
        "status_comparing": "Comparing script with audio...",
        "status_reps": "Analyzing takes & gaps...",
        "status_standalone": "Running standalone analysis...",
        "status_compared": "Analysis done. Found {diffs} discrepancies.",
        
        # Misc UI
        "msg_success": "Timeline assembled successfully!",
        
        "msg_confirm_cancel": "Discard changes?",
        "msg_confirm_apply": "Save changes?",
        "msg_confirm_quit": "Are you sure you want to quit?\nUnsaved progress will be lost.",
        "title_confirm": "Confirm",
        "err_resolve": "DaVinci Resolve API not found.",
        "err_timeline": "Open Timeline before running.",
        "err_render": "Render failed.",
        "err_whisper": "Whisper failed. Check logs.",
        "err_nowords": "No words detected.",
        "err_tl_create": "Failed to create Timeline.",
        "err_num": "Invalid numbers in settings.",
        "err_noscript": "Please paste or import a script first.",
        "ph_script": "Paste script directly here or import using button...",
        "disclaimer": "DISCLAIMER: Transcriptions may be imprecise. Development version.",
        "file_types": "Text / Word / PDF",
        "err_dep": "Missing dependency: {dep}.",
        "lbl_page": "Page {current}/{total}",
        "btn_prev": "< Prev",
        "btn_next": "Next >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",

        # Model Names
        "model_tiny": "Tiny (Fast, <1GB VRAM)",
        "model_base": "Base (Balanced, 1GB VRAM)",
        "model_small": "Small (Good, 2GB VRAM)",
        "model_medium": "Medium (Best balance, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Fast & Precise, 6GB VRAM)",
        "model_large": "Large (Most Accurate, 10GB VRAM)",

        # Other
        "tooltip_dev": "Feature still in development",
        "title_model_missing": "Model Missing",
        "msg_model_missing": "The model '{model}' is not installed.\nDownload it now?",
        "btn_dl_analyze": "Download & Analyze",
        "status_downloading": "Downloading {model}...",
        "err_download": "Failed to download model.",
        "msg_dl_success": "Model '{model}' installed successfully.",
        
        # Language Search Placeholder
        "ph_lang_search": "Search language...",
        
        # TELEMETRY POPUP
        "title_telemetry": "BadWords Analytics",
        "msg_telemetry": "Hi! 👋\n\nTo help me improve BadWords, do you agree to send a one-time, 100% anonymous ping after installation / update?\n\nOnly the app version, OS type, and your general location (country/city) are sent. No audio files, scripts, or personal data are EVER collected.",
        "btn_telemetry_yes": "I Agree",
        "btn_telemetry_no": "No, thanks"
    },

    "pl": {
        "name": "Polski",
        "title": "BadWords",
        "header_main": "Konfiguracja BadWords",
        "sec_whisper": "WHISPER I MODEL",
        "lbl_lang": "Język:",
        "lbl_model": "Model:",
        "lbl_device": "Urządzenie:",
        "lbl_fillers": "Wypełniacze:",
        "btn_edit_fillers": "Edytuj listę...",
        "title_edit_fillers": "Edytor Słów-Wypełniaczy",
        "lbl_fillers_instr": "Edytuj słowa oddzielone przecinkami:",
        "sec_sync": "SYNCHRONIZACJA (SEKUNDY)",
        "lbl_offset": "Przesunięcie (s):",
        "lbl_pad": "Margines (s):",
        "lbl_snap": "Przyciąganie (s):",
        "lbl_thresh": "Próg Ciszy (dB):",
        "chk_reviewer": "Włącz Script Reviewer",
        
        "btn_analyze": "ANALIZUJ",
        "btn_cancel": "Anuluj",
        "btn_quit": "Wyjdź",
        "btn_apply": "Zastosuj",
        "btn_generate": "Montuj",
        "btn_import_proj": "Importuj",
        "btn_export_proj": "Eksportuj",
        "btn_dl_model": "Pobierz Model",
        "lbl_model_installed": "Model Zainstalowany ✔️",
        "header_rev_script": "Oryginalny Scenariusz (Żółty = Brak w Audio)",
        "header_rev_trans": "Transkrypcja Audio (Robocza)",
        "header_rev_tools": "Narzędzia",
        "lbl_mark_color": "Tryb zaznaczania:",
        "rb_mark_red": "CZERWONY (Złe/Wypełniacz)",
        "rb_mark_blue": "NIEBIESKI (Retake)",
        "rb_mark_green": "ZIELONY (Literówka)",
        "rb_mark_white": "GUMKA (Usuń)",
        "chk_auto_filler": "Oznaczaj wypełniacze automatycznie",
        "chk_auto_del": "Usuwaj czerwone klipy automatycznie",
        "btn_import": "Importuj Scenariusz",
        "btn_compare": "Analizuj (Porównaj)",
        "btn_standalone": "Analizuj (Bez Skryptu)",
        "chk_silence_cut": "Wykryj i wytnij ciszę",
        "chk_silence_mark": "Wykryj i oznacz ciszę (beżowy)",
        
        # Inaudible & Typos Checkboxes
        "chk_show_inaudible": "Pokaż niezrozumiałe fragmenty",
        "chk_mark_inaudible": "Oznaczaj niezrozumiałe fragmenty na brązowo",
        "chk_show_typos": "Pokaż wykryte literówki",
        
        "btn_clear_trans": "Wyczyść Transkrypt",
        "msg_confirm_clear": "Czy na pewno usunąć wszystkie oznaczenia?",
        "btn_clear_confirm": "Wyczyść",

        "status_ready": "Gotowy.",
        "status_initializing": "Inicjalizowanie...",
        "status_render": "Renderowanie audio...",
        "status_norm": "Normalizacja audio...",
        "status_silence": "Wykrywanie ciszy...",
        "status_check_model": "Weryfikacja/Pobieranie modelu {model}...",
        "status_whisper_run": "Transkrypcja ({model})...",
        "status_whisper_dl": "Pobieranie modelu {model}...",
        "status_processing": "Przetwarzanie danych...",
        "status_generating": "Montowanie timeline...",
        "status_cleanup": "Czyszczenie...",
        "status_done": "Zakończono!",
        "status_comparing": "Porównywanie scenariusza...",
        "status_reps": "Analiza powtórek...",
        "status_standalone": "Uruchamianie analizy solo...",
        "status_compared": "Analiza zakończona. Znaleziono {diffs} różnic.",
        
        "msg_success": "Timeline zmontowany pomyślnie!",
        
        "msg_confirm_cancel": "Porzucić zmiany?",
        "msg_confirm_apply": "Zapisać zmiany?",
        "msg_confirm_quit": "Na pewno wyjść?\nNiezapisane zmiany zostaną utracone.",
        "title_confirm": "Potwierdź",
        "err_resolve": "Brak API DaVinci Resolve.",
        "err_timeline": "Otwórz Timeline przed uruchomieniem.",
        "err_render": "Błąd renderowania.",
        "err_whisper": "Błąd Whisper. Sprawdź logi.",
        "err_nowords": "Nie wykryto słów.",
        "err_tl_create": "Błąd tworzenia Timeline.",
        "err_num": "Błędne dane liczbowe.",
        "err_noscript": "Najpierw wklej lub importuj scenariusz.",
        "ph_script": "Wklej skrypt tutaj lub importuj przyciskiem...",
        "disclaimer": "UWAGA: Transkrypcje mogą być nieprecyzyjne. Wersja deweloperska.",
        "file_types": "Tekst / Word / PDF",
        "err_dep": "Brak zależności: {dep}.",
        "lbl_page": "Strona {current}/{total}",
        "btn_prev": "< Poprz.",
        "btn_next": "Nast. >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "model_tiny": "Tiny (Szybki, <1GB VRAM)",
        "model_base": "Base (Zbalansowany, 1GB VRAM)",
        "model_small": "Small (Dobry, 2GB VRAM)",
        "model_medium": "Medium (Najlepszy balans, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Szybki i precyzyjny, 6GB VRAM)",
        "model_large": "Large (Najdokładniejszy, 10GB VRAM)",
        "tooltip_dev": "Funkcja wciąż w produkcji",
        "title_model_missing": "Brak Modelu",
        "msg_model_missing": "Model '{model}' nie jest zainstalowany.\nCzy pobrać go teraz?",
        "btn_dl_analyze": "Pobierz i Analizuj",
        "status_downloading": "Pobieranie {model}...",
        "err_download": "Błąd pobierania modelu.",
        "msg_dl_success": "Model '{model}' zainstalowany pomyślnie.",
        
        # Language Search Placeholder
        "ph_lang_search": "Szukaj języka...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Statystyki BadWords",
        "msg_telemetry": "Cześć! 👋\n\nAby pomóc mi w rozwoju BadWords, czy zgadzasz się na wysłanie jednorazowego, w 100% anonimowego pingu po instalacji / aktualizacji?\n\nWysyłana jest tylko wersja aplikacji, typ systemu (np. Windows) oraz Twoja ogólna lokalizacja (państwo/miasto). Żadne pliki audio, scenariusze ani dane osobiste NIGDY nie są zbierane.",
        "btn_telemetry_yes": "Zgadzam się",
        "btn_telemetry_no": "Nie, dzięki"
    },

    "de": {
        "name": "Deutsch",
        "title": "BadWords",
        "header_main": "BadWords Konfiguration",
        "sec_whisper": "WHISPER & MODELL",
        "lbl_lang": "Sprache:",
        "lbl_model": "Modell:",
        "lbl_device": "Gerät:",
        "lbl_fillers": "Füllwörter:",
        "btn_edit_fillers": "Liste bearbeiten...",
        "title_edit_fillers": "Füllwörter-Editor",
        "lbl_fillers_instr": "Wörter bearbeiten (kommagetrennt):",
        "sec_sync": "AUDIO-SYNC (SEKUNDEN)",
        "lbl_offset": "Versatz (s):",
        "lbl_pad": "Polster (s):",
        "lbl_snap": "Einrasten (s):",
        "lbl_thresh": "Stille-Schwelle (dB):",
        "chk_reviewer": "Skript-Reviewer aktivieren",
        
        "btn_analyze": "ANALYSIEREN",
        "btn_cancel": "Abbrechen",
        "btn_quit": "Beenden",
        "btn_apply": "Anwenden",
        "btn_generate": "Montieren",
        "btn_import_proj": "Importieren",
        "btn_export_proj": "Exportieren",
        "btn_dl_model": "Modell laden",
        "lbl_model_installed": "Modell installiert ✔️",
        "header_rev_script": "Originalskript (Gelb = Fehlt im Audio)",
        "header_rev_trans": "Transkription (Arbeitsbereich)",
        "header_rev_tools": "Werkzeuge",
        "lbl_mark_color": "Markierungsmodus:",
        "rb_mark_red": "ROT (Schnitt/Füller)",
        "rb_mark_blue": "BLAU (Retake)",
        "rb_mark_green": "GRÜN (Tippfehler)",
        "rb_mark_white": "RADIERER (Löschen)",
        "chk_auto_filler": "Füllwörter automatisch markieren",
        "chk_auto_del": "Rote Clips automatisch löschen",
        "btn_import": "Skript importieren",
        "btn_compare": "Analysieren (Vergleich)",
        "btn_standalone": "Analysieren (Ohne Skript)",
        
        "chk_show_inaudible": "Unhörbare Fragmente anzeigen",
        "chk_mark_inaudible": "Unhörbare Fragmente braun markieren",
        "chk_show_typos": "Erkannte Tippfehler anzeigen",

        "btn_clear_trans": "Transkript löschen",
        "msg_confirm_clear": "Alle Markierungen löschen?",
        "btn_clear_confirm": "Löschen",

        "status_ready": "Bereit.",
        "status_initializing": "Initialisiere...",
        "status_render": "Rendere Audio...",
        "status_norm": "Normalisiere Audio...",
        "status_silence": "Erkenne Stille...",
        "status_check_model": "Prüfe/Lade Modell {model}...",
        "status_whisper_run": "Transkribiere ({model})...",
        "status_whisper_dl": "Lade {model} herunter...",
        "status_processing": "Verarbeite Daten...",
        "status_generating": "Timeline wird montiert...",
        "status_cleanup": "Bereinige...",
        "status_done": "Fertig!",
        "status_comparing": "Vergleiche Skript...",
        "status_reps": "Analysiere Takes...",
        "status_standalone": "Starte Analyse...",
        "status_compared": "Analyse fertig. {diffs} Unterschiede.",
        
        "msg_success": "Timeline erfolgreich montiert!",
        
        "msg_confirm_cancel": "Änderungen verwerfen?",
        "msg_confirm_apply": "Änderungen speichern?",
        "msg_confirm_quit": "Möchten Sie wirklich beenden?",
        "title_confirm": "Bestätigen",
        "err_resolve": "DaVinci Resolve API nicht gefunden.",
        "err_timeline": "Bitte Timeline vor Start öffnen.",
        "err_render": "Render-Fehler.",
        "err_whisper": "Whisper fehlgeschlagen.",
        "err_nowords": "Keine Wörter erkannt.",
        "err_tl_create": "Fehler beim Erstellen der Timeline.",
        "err_num": "Ungültige Zahlen.",
        "err_noscript": "Bitte erst Skript einfügen.",
        "ph_script": "Skript hier einfügen...",
        "disclaimer": "HINWEIS: Transkriptionen können ungenau sein.",
        "file_types": "Text / Word / PDF",
        "err_dep": "Fehlende Abhängigkeit: {dep}.",
        "lbl_page": "Seite {current}/{total}",
        "btn_prev": "< Zurück",
        "btn_next": "Weiter >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Stille erkennen und schneiden",
        "chk_silence_mark": "Stille erkennen und markieren (braun)",
        "model_tiny": "Tiny (Schnell, <1GB VRAM)",
        "model_base": "Base (Ausgewogen, 1GB VRAM)",
        "model_small": "Small (Gut, 2GB VRAM)",
        "model_medium": "Medium (Beste Balance, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Schnell & Präzise, 6GB VRAM)",
        "model_large": "Large (Am genauesten, 10GB VRAM)",
        "tooltip_dev": "Funktion noch in Entwicklung",
        "title_model_missing": "Modell fehlt",
        "msg_model_missing": "Modell '{model}' fehlt.\nJetzt herunterladen?",
        "btn_dl_analyze": "Laden & Analysieren",
        "status_downloading": "Lade {model}...",
        "err_download": "Download fehlgeschlagen.",
        "msg_dl_success": "Modell '{model}' erfolgreich installiert.",

        # Language Search Placeholder
        "ph_lang_search": "Sprache suchen...",
        
        # TELEMETRY POPUP
        "title_telemetry": "BadWords Analytik",
        "msg_telemetry": "Hallo! 👋\n\nUm mir bei der Verbesserung von BadWords zu helfen, stimmen Sie zu, nach der Installation / dem Update einen einmaligen, 100% anonymen Ping zu senden?\n\nEs werden nur die App-Version, das Betriebssystem und Ihr allgemeiner Standort (Land/Stadt) gesendet. Es werden NIEMALS Audiodateien, Skripte oder persönliche Daten gesammelt.",
        "btn_telemetry_yes": "Ich stimme zu",
        "btn_telemetry_no": "Nein, danke"
    },

    "es": {
        "name": "Español",
        "title": "BadWords",
        "header_main": "Configuración BadWords",
        "sec_whisper": "WHISPER Y MODELO",
        "lbl_lang": "Idioma:",
        "lbl_model": "Modelo:",
        "lbl_device": "Dispositivo:",
        "lbl_fillers": "Muletillas:",
        "btn_edit_fillers": "Editar lista...",
        "title_edit_fillers": "Editor de Muletillas",
        "lbl_fillers_instr": "Editar palabras (separadas por comas):",
        "sec_sync": "SINCRONIZACIÓN DE AUDIO (SEGUNDOS)",
        "lbl_offset": "Desplazamiento (s):",
        "lbl_pad": "Margen (s):",
        "lbl_snap": "Ajuste Máx (s):",
        "lbl_thresh": "Umbral Silencio (dB):",
        "chk_reviewer": "Habilitar Revisor de Guion",
        
        "btn_analyze": "ANALIZAR",
        "btn_cancel": "Cancelar",
        "btn_quit": "Salir",
        "btn_apply": "Aplicar",
        "btn_generate": "Ensamblar",
        "btn_import_proj": "Importar",
        "btn_export_proj": "Exportar",
        "btn_dl_model": "Descargar Modelo",
        "lbl_model_installed": "Modelo Instalado ✔️",
        "header_rev_script": "Guion Original (Amarillo = Falta en Audio)",
        "header_rev_trans": "Transcripción de Audio",
        "header_rev_tools": "Herramientas",
        "lbl_mark_color": "Modo de marcado:",
        "rb_mark_red": "ROJO (Cortar/Relleno)",
        "rb_mark_blue": "AZUL (Retoma)",
        "rb_mark_green": "VERDE (Errata)",
        "rb_mark_white": "BORRADOR (Limpiar)",
        "chk_auto_filler": "Marcar muletillas automáticamente",
        "chk_auto_del": "Eliminar clips rojos automáticamente",
        "btn_import": "Importar Guion",
        "btn_compare": "Analizar (Comparar)",
        "btn_standalone": "Analizar (Independiente)",
        
        "chk_show_inaudible": "Mostrar fragmentos inaudibles",
        "chk_mark_inaudible": "Marcar fragmentos inaudibles de marrón",
        "chk_show_typos": "Mostrar erratas detectadas",

        "btn_clear_trans": "Borrar Transcripción",
        "msg_confirm_clear": "¿Borrar todas las marcas?",
        "btn_clear_confirm": "Borrar",

        "status_ready": "Listo.",
        "status_initializing": "Inicializando...",
        "status_render": "Renderizando audio...",
        "status_norm": "Normalizando audio...",
        "status_silence": "Detectando silencio...",
        "status_check_model": "Verificando modelo {model}...",
        "status_whisper_run": "Transcribiendo ({model})...",
        "status_whisper_dl": "Descargando {model}...",
        "status_processing": "Procesando datos...",
        "status_generating": "Ensamblando timeline...",
        "status_cleanup": "Limpiando...",
        "status_done": "¡Hecho!",
        "status_comparing": "Comparando guion...",
        "status_reps": "Analizando tomas...",
        "status_standalone": "Ejecutando análisis...",
        "status_compared": "Análisis listo. {diffs} discrepancias.",
        
        "msg_success": "¡Timeline ensamblada con éxito!",
        
        "msg_confirm_cancel": "¿Descartar cambios?",
        "msg_confirm_apply": "¿Guardar cambios?",
        "msg_confirm_quit": "¿Seguro que quieres salir?",
        "title_confirm": "Confirmar",
        "err_resolve": "API de DaVinci Resolve no encontrada.",
        "err_timeline": "Abre una Timeline antes de ejecutar.",
        "err_render": "Fallo en renderizado.",
        "err_whisper": "Fallo en Whisper.",
        "err_nowords": "No se detectaron palabras.",
        "err_tl_create": "Fallo al crear Timeline.",
        "err_num": "Números inválidos.",
        "err_noscript": "Por favor pega o importa un guion primero.",
        "ph_script": "Pega el guion aquí...",
        "disclaimer": "AVISO: Las transcripciones pueden ser imprecisas.",
        "file_types": "Texto / Word / PDF",
        "err_dep": "Falta dependencia: {dep}.",
        "lbl_page": "Pág {current}/{total}",
        "btn_prev": "< Ant",
        "btn_next": "Sig >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Detectar y cortar silencio",
        "chk_silence_mark": "Detectar y marcar silencio (tostado)",
        "model_tiny": "Tiny (Rápido, <1GB VRAM)",
        "model_base": "Base (Equilibrado, 1GB VRAM)",
        "model_small": "Small (Bueno, 2GB VRAM)",
        "model_medium": "Medium (Mejor, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Rápido y Preciso, 6GB VRAM)",
        "model_large": "Large (Más Preciso, 10GB VRAM)",
        "tooltip_dev": "Función en desarrollo",
        "title_model_missing": "Modelo Faltante",
        "msg_model_missing": "Modelo '{model}' no instalado.\n¿Descargarlo?",
        "btn_dl_analyze": "Descargar y Analizar",
        "status_downloading": "Descargando {model}...",
        "err_download": "Fallo en descarga.",
        "msg_dl_success": "Modelo '{model}' instalado con éxito.",

        # Language Search Placeholder
        "ph_lang_search": "Buscar idioma...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Analítica de BadWords",
        "msg_telemetry": "¡Hola! 👋\n\nPara ayudarme a mejorar BadWords, ¿aceptas enviar un ping único y 100% anónimo después de la instalación o actualización?\n\nSolo se envían la versión de la aplicación, el sistema operativo y tu ubicación general (país/ciudad). NUNCA se recopilan archivos de audio, guiones ni datos personales.",
        "btn_telemetry_yes": "Acepto",
        "btn_telemetry_no": "No, gracias"
    },

    "fr": {
        "name": "Français",
        "title": "BadWords",
        "header_main": "Configuration BadWords",
        "sec_whisper": "WHISPER ET MODÈLE",
        "lbl_lang": "Langue :",
        "lbl_model": "Modèle :",
        "lbl_device": "Périphérique :",
        "lbl_fillers": "Mots de remplissage :",
        "btn_edit_fillers": "Modifier la liste...",
        "title_edit_fillers": "Éditeur de mots de remplissage",
        "lbl_fillers_instr": "Modifier les mots (séparés par des virgules) :",
        "sec_sync": "SYNC AUDIO (SECONDES)",
        "lbl_offset": "Décalage (s) :",
        "lbl_pad": "Marge (s) :",
        "lbl_snap": "Alignement Max (s) :",
        "lbl_thresh": "Seuil Silence (dB) :",
        "chk_reviewer": "Activer le réviseur de script",
        
        "btn_analyze": "ANALYSER",
        "btn_cancel": "Annuler",
        "btn_quit": "Quitter",
        "btn_apply": "Appliquer",
        "btn_generate": "Assembler",
        "btn_import_proj": "Importer",
        "btn_export_proj": "Exporter",
        "btn_dl_model": "Télécharger Modèle",
        "lbl_model_installed": "Modèle Installé ✔️",
        "header_rev_script": "Script Original (Jaune = Manquant dans l'audio)",
        "header_rev_trans": "Audio Transcrit (Zone de travail)",
        "header_rev_tools": "Outils",
        "lbl_mark_color": "Mode de marquage :",
        "rb_mark_red": "ROUGE (Couper/Remplissage)",
        "rb_mark_blue": "BLEU (Reprise)",
        "rb_mark_green": "VERT (Coquille)",
        "rb_mark_white": "GOMME (Effacer)",
        "chk_auto_filler": "Marcar mots de remplissage auto",
        "chk_auto_del": "Supprimer les clips rouges auto",
        "btn_import": "Importer Script",
        "btn_compare": "Analyser (Comparer)",
        "btn_standalone": "Analyser (Autonome)",
        
        "chk_show_inaudible": "Afficher les fragments inaudibles",
        "chk_mark_inaudible": "Marquer les fragments inaudibles en brun",
        "chk_show_typos": "Afficher les coquilles détectées",

        "btn_clear_trans": "Effacer Transcription",
        "msg_confirm_clear": "Effacer tous les marquages ?",
        "btn_clear_confirm": "Effacer",

        "status_ready": "Prêt.",
        "status_initializing": "Initialisation...",
        "status_render": "Rendu audio...",
        "status_norm": "Normalisation audio...",
        "status_silence": "Détection silence...",
        "status_check_model": "Vérification modèle {model}...",
        "status_whisper_run": "Transcription ({model})...",
        "status_whisper_dl": "Téléchargement de {model}...",
        "status_processing": "Traitement des données...",
        "status_generating": "Assemblage de la timeline...",
        "status_cleanup": "Nettoyage...",
        "status_done": "Terminé !",
        "status_comparing": "Comparaison script...",
        "status_reps": "Analyse prises...",
        "status_standalone": "Analyse autonome...",
        "status_compared": "Analyse terminée. {diffs} différences.",
        
        "msg_success": "Timeline assemblée avec succès !",
        
        "msg_confirm_cancel": "Annuler les modifications ?",
        "msg_confirm_apply": "Enregistrer les modifications ?",
        "msg_confirm_quit": "Voulez-vous vraiment quitter ?",
        "title_confirm": "Confirmer",
        "err_resolve": "API DaVinci Resolve introuvable.",
        "err_timeline": "Ouvrez une Timeline avant de lancer.",
        "err_render": "Échec du rendu.",
        "err_whisper": "Échec Whisper.",
        "err_nowords": "Aucun mot détecté.",
        "err_tl_create": "Échec création Timeline.",
        "err_num": "Nombres invalides.",
        "err_noscript": "Veuillez d'abord coller un script.",
        "ph_script": "Collez le script ici...",
        "disclaimer": "AVERTISSEMENT : Transcriptions potentiellement imprécises.",
        "file_types": "Texte / Word / PDF",
        "err_dep": "Dépendance manquante : {dep}.",
        "lbl_page": "Page {current}/{total}",
        "btn_prev": "< Préc",
        "btn_next": "Suiv >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Détecter et couper le silence",
        "chk_silence_mark": "Détecter et marquer le silence (brun)",
        "model_tiny": "Tiny (Rapide, <1Go VRAM)",
        "model_base": "Base (Équilibré, 1Go VRAM)",
        "model_small": "Small (Bon, 2Go VRAM)",
        "model_medium": "Medium (Meilleur équilibre, 5Go VRAM)",
        "model_large_turbo": "Large Turbo (Rapide & Précis, 6Go VRAM)",
        "model_large": "Large (Plus précis, 10Go VRAM)",
        "tooltip_dev": "Fonctionnalité en développement",
        "title_model_missing": "Modèle Manquant",
        "msg_model_missing": "Modèle '{model}' non installé.\nLe télécharger ?",
        "btn_dl_analyze": "Télécharger & Analyser",
        "status_downloading": "Téléchargement {model}...",
        "err_download": "Échec du téléchargement.",
        "msg_dl_success": "Modèle '{model}' installé avec succès.",

        # Language Search Placeholder
        "ph_lang_search": "Rechercher une langue...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Analytique BadWords",
        "msg_telemetry": "Bonjour ! 👋\n\nPour m'aider à améliorer BadWords, acceptez-vous d'envoyer un ping unique et 100% anonyme après l'installation / la mise à jour ?\n\nSeuls la version de l'application, le système d'exploitation et votre emplacement général (pays/ville) sont envoyés. AUCUN fichier audio, script ou donnée personnelle n'est JAMAIS collecté.",
        "btn_telemetry_yes": "J'accepte",
        "btn_telemetry_no": "Non, merci"
    },

    "it": {
        "name": "Italiano",
        "title": "BadWords",
        "header_main": "Configurazione BadWords",
        "sec_whisper": "WHISPER & MODELLO",
        "lbl_lang": "Lingua:",
        "lbl_model": "Modello:",
        "lbl_device": "Dispositivo:",
        "lbl_fillers": "Riempitivi:",
        "btn_edit_fillers": "Modifica lista...",
        "title_edit_fillers": "Editor Parole Riempitive",
        "lbl_fillers_instr": "Modifica parole (separate da virgola):",
        "sec_sync": "SYNC AUDIO (SECONDI)",
        "lbl_offset": "Offset (s):",
        "lbl_pad": "Margine (s):",
        "lbl_snap": "Snap Max (s):",
        "lbl_thresh": "Soglia Silenzio (dB):",
        "chk_reviewer": "Abilita Revisore Script",
        
        "btn_analyze": "ANALIZZA",
        "btn_cancel": "Annulla",
        "btn_quit": "Esci",
        "btn_apply": "Applica",
        "btn_generate": "Assembla",
        "btn_import_proj": "Importa",
        "btn_export_proj": "Esporta",
        "btn_dl_model": "Scarica Modello",
        "lbl_model_installed": "Modello Installato ✔️",
        "header_rev_script": "Script Originale (Giallo = Mancante in Audio)",
        "header_rev_trans": "Audio Trascritto (Area di Lavoro)",
        "header_rev_tools": "Strumenti",
        "lbl_mark_color": "Modalità marcatura:",
        "rb_mark_red": "ROSSO (Taglio/Riempitivo)",
        "rb_mark_blue": "BLU (Ripetizione)",
        "rb_mark_green": "VERDE (Refuso)",
        "rb_mark_white": "GOMMA (Pulisci)",
        "chk_auto_filler": "Segna riempitivi automaticamente",
        "chk_auto_del": "Elimina clip rosse automaticamente",
        "btn_import": "Importa Script",
        "btn_compare": "Analizza (Confronta)",
        "btn_standalone": "Analizza (Indipendente)",
        
        "chk_show_inaudible": "Mostra frammenti inudibili",
        "chk_mark_inaudible": "Segna i frammenti inudibili in marrone",
        "chk_show_typos": "Mostra refusi rilevati",

        "btn_clear_trans": "Pulisci Trascrizione",
        "msg_confirm_clear": "Cancellare tutti i segni?",
        "btn_clear_confirm": "Pulisci",

        "status_ready": "Pronto.",
        "status_initializing": "Inizializzazione...",
        "status_render": "Rendering audio...",
        "status_norm": "Normalizzazione audio...",
        "status_silence": "Rilevamento silenzio...",
        "status_check_model": "Verifica modello {model}...",
        "status_whisper_run": "Trascrizione ({model})...",
        "status_whisper_dl": "Scaricamento {model}...",
        "status_processing": "Elaborazione dati...",
        "status_generating": "Assemblaggio timeline...",
        "status_cleanup": "Pulizia...",
        "status_done": "Fatto!",
        "status_comparing": "Confronto script...",
        "status_reps": "Analisi take...",
        "status_standalone": "Analisi autonoma...",
        "status_compared": "Analisi completata. {diffs} discrepanze.",
        
        "msg_success": "Timeline assemblata con successo!",
        
        "msg_confirm_cancel": "Scartare modifiche?",
        "msg_confirm_apply": "Salvare modifiche?",
        "msg_confirm_quit": "Sei sicuro di voler uscire?",
        "title_confirm": "Conferma",
        "err_resolve": "API DaVinci Resolve non trovata.",
        "err_timeline": "Apri una Timeline prima di avviare.",
        "err_render": "Rendering fallito.",
        "err_whisper": "Fallimento Whisper.",
        "err_nowords": "Nessuna parola rilevata.",
        "err_tl_create": "Creazione Timeline fallita.",
        "err_num": "Numeri non validi.",
        "err_noscript": "Per favore incolla o importa prima uno script.",
        "ph_script": "Incolla lo script qui...",
        "disclaimer": "AVVISO: Le trascrizioni possono essere imprecise.",
        "file_types": "Testo / Word / PDF",
        "err_dep": "Dipendenza mancante: {dep}.",
        "lbl_page": "Pagina {current}/{total}",
        "btn_prev": "< Prec",
        "btn_next": "Succ >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Rileva e taglia silenzio",
        "chk_silence_mark": "Rileva e segna silenzio",
        "model_tiny": "Tiny (Veloce, <1GB VRAM)",
        "model_base": "Base (Bilanciato, 1GB VRAM)",
        "model_small": "Small (Buono, 2GB VRAM)",
        "model_medium": "Medium (Miglior bilanciamento, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Veloce & Preciso, 6GB VRAM)",
        "model_large": "Large (Più accurato, 10GB VRAM)",
        "tooltip_dev": "Funzionalità in sviluppo",
        "title_model_missing": "Modello Mancante",
        "msg_model_missing": "Il modello '{model}' non è installato.\nScaricarlo ora?",
        "btn_dl_analyze": "Scarica e Analizza",
        "status_downloading": "Scaricamento {model}...",
        "err_download": "Scaricamento fallito.",
        "msg_dl_success": "Modello '{model}' installato con successo.",

        # Language Search Placeholder
        "ph_lang_search": "Cerca lingua...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Analitica BadWords",
        "msg_telemetry": "Ciao! 👋\n\nPer aiutarmi a migliorare BadWords, accetti di inviare un ping singolo e anonimo al 100% dopo l'installazione o l'aggiornamento?\n\nVengono inviati solo la versione dell'app, il sistema operativo e la tua posizione generale (paese/città). NON vengono MAI raccolti file audio, script o dati personali.",
        "btn_telemetry_yes": "Accetto",
        "btn_telemetry_no": "No, grazie"
    },

    "pt": {
        "name": "Português",
        "title": "BadWords",
        "header_main": "Configuração BadWords",
        "sec_whisper": "WHISPER E MODELO",
        "lbl_lang": "Idioma:",
        "lbl_model": "Modelo:",
        "lbl_device": "Dispositivo:",
        "lbl_fillers": "Palavras de preenchimento:",
        "btn_edit_fillers": "Editar lista...",
        "title_edit_fillers": "Editor de Preenchimentos",
        "lbl_fillers_instr": "Editar palavras (separadas por vírgula):",
        "sec_sync": "SYNC DE ÁUDIO (SEGUNDOS)",
        "lbl_offset": "Deslocamento (s):",
        "lbl_pad": "Margem (s):",
        "lbl_snap": "Ajuste Máx (s):",
        "lbl_thresh": "Limiar Silêncio (dB):",
        "chk_reviewer": "Habilitar Revisor de Script",
        
        "btn_analyze": "ANALISAR",
        "btn_cancel": "Cancelar",
        "btn_quit": "Sair",
        "btn_apply": "Aplicar",
        "btn_generate": "Montar",
        "btn_import_proj": "Importar",
        "btn_export_proj": "Exportar",
        "btn_dl_model": "Baixar Modelo",
        "lbl_model_installed": "Modelo Instalado ✔️",
        "header_rev_script": "Script Original (Amarelo = Faltando no Áudio)",
        "header_rev_trans": "Áudio Transcrito (Área de Trabalho)",
        "header_rev_tools": "Ferramentas",
        "lbl_mark_color": "Modo de marcação:",
        "rb_mark_red": "VERMELHO (Cortar/Preenchimento)",
        "rb_mark_blue": "AZUL (Retake)",
        "rb_mark_green": "VERDE (Erro)",
        "rb_mark_white": "BORRACHA (Limpar)",
        "chk_auto_filler": "Marcar preenchimentos automaticamente",
        "chk_auto_del": "Excluir clips vermelhos automaticamente",
        "btn_import": "Importar Script",
        "btn_compare": "Analisar (Comparar)",
        "btn_standalone": "Analisar (Independiente)",
        
        "chk_show_inaudible": "Mostrar fragmentos inaudíveis",
        "chk_mark_inaudible": "Marcar fragmentos inaudíveis de marrom",
        "chk_show_typos": "Mostrar erros de digitação detectados",

        "btn_clear_trans": "Limpar Transcrição",
        "msg_confirm_clear": "Limpar todas as marcações?",
        "btn_clear_confirm": "Limpar",

        "status_ready": "Pronto.",
        "status_initializing": "Inicializando...",
        "status_render": "Renderizando áudio...",
        "status_norm": "Normalizando áudio...",
        "status_silence": "Detectando silêncio...",
        "status_check_model": "Verificando modelo {model}...",
        "status_whisper_run": "Transcrevendo ({model})...",
        "status_whisper_dl": "Baixando {model}...",
        "status_processing": "Processando dados...",
        "status_generating": "Montando timeline...",
        "status_cleanup": "Limpando...",
        "status_done": "Concluído!",
        "status_comparing": "Comparando script...",
        "status_reps": "Analisando takes...",
        "status_standalone": "Executando análise...",
        "status_compared": "Análise pronta. {diffs} discrepancias.",
        
        "msg_success": "Timeline montada com sucesso!",
        
        "msg_confirm_cancel": "Descartar alterações?",
        "msg_confirm_apply": "Salvar alterações?",
        "msg_confirm_quit": "Tem certeza que deseja sair?",
        "title_confirm": "Confirmar",
        "err_resolve": "API do DaVinci Resolve não encontrada.",
        "err_timeline": "Abra uma Timeline antes de executar.",
        "err_render": "Falha na renderização.",
        "err_whisper": "Falha no Whisper.",
        "err_nowords": "Nenhuma palavra detectada.",
        "err_tl_create": "Falha ao criar Timeline.",
        "err_num": "Números inválidos.",
        "err_noscript": "Por favor cole um script.",
        "ph_script": "Cole o script aqui...",
        "disclaimer": "AVISO: As transcrições podem ser imprecisas.",
        "file_types": "Texto / Word / PDF",
        "err_dep": "Dependência faltando: {dep}.",
        "lbl_page": "Pág {current}/{total}",
        "btn_prev": "< Ant",
        "btn_next": "Próx >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Detectar e Cortar Silêncio",
        "chk_silence_mark": "Detectar e Marcar Silêncio",
        "model_tiny": "Tiny (Rápido, <1GB VRAM)",
        "model_base": "Base (Equilibrado, 1GB VRAM)",
        "model_small": "Small (Bom, 2GB VRAM)",
        "model_medium": "Medium (Melhor equilíbrio, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Rápido e Preciso, 6GB VRAM)",
        "model_large": "Large (Mais Preciso, 10GB VRAM)",
        "tooltip_dev": "Funcionalidade em desenvolvimento",
        "title_model_missing": "Modelo Faltando",
        "msg_model_missing": "O modelo '{model}' não está instalado.\nBaixá-lo agora?",
        "btn_dl_analyze": "Baixar e Analisar",
        "status_downloading": "Baixando {model}...",
        "err_download": "Falha no download.",
        "msg_dl_success": "Modelo '{model}' instalado com sucesso.",

        # Language Search Placeholder
        "ph_lang_search": "Pesquisar idioma...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Análise BadWords",
        "msg_telemetry": "Olá! 👋\n\nPara me ajudar a melhorar o BadWords, você concorda em enviar um ping único e 100% anônimo após a instalação / atualização?\n\nApenas a versão do aplicativo, o sistema operacional e sua localização geral (país/cidade) são enviados. NUNCA são coletados arquivos de áudio, scripts ou dados pessoais.",
        "btn_telemetry_yes": "Eu concordo",
        "btn_telemetry_no": "Não, obrigado"
    },

    "uk": {
        "name": "Українська",
        "title": "BadWords",
        "header_main": "Конфігурація BadWords",
        "sec_whisper": "WHISPER ТА МОДЕЛЬ",
        "lbl_lang": "Мова:",
        "lbl_model": "Модель:",
        "lbl_device": "Пристрій:",
        "lbl_fillers": "Слова-паразити:",
        "btn_edit_fillers": "Редагувати список...",
        "title_edit_fillers": "Редактор слів-паразитів",
        "lbl_fillers_instr": "Редагувати слова (через кому):",
        "sec_sync": "СИНХРОНІЗАЦІЯ АУДІО (СЕКУНДИ)",
        "lbl_offset": "Зсув (с):",
        "lbl_pad": "Відступ (с):",
        "lbl_snap": "Прилипання (с):",
        "lbl_thresh": "Поріг тиші (dB):",
        "chk_reviewer": "Увімкнути рецензента сценарію",
        
        "btn_analyze": "АНАЛІЗУВАТИ",
        "btn_cancel": "Скасувати",
        "btn_quit": "Вийти",
        "btn_apply": "Застосувати",
        "btn_generate": "Змонтувати",
        "btn_import_proj": "Імпорт",
        "btn_export_proj": "Експорт",
        "btn_dl_model": "Завантажити модель",
        "lbl_model_installed": "Модель встановлена ✔️",
        "header_rev_script": "Оригінальний сценарий (Жовтий = Відсутнє в аудіо)",
        "header_rev_trans": "Транскрибоване аудіо (Робоча зона)",
        "header_rev_tools": "Інструменти",
        "lbl_mark_color": "Режим позначення:",
        "rb_mark_red": "ЧЕРВОНИЙ (Вирізати/Сміття)",
        "rb_mark_blue": "СИНІЙ (Дубль)",
        "rb_mark_green": "ЗЕЛЕНИЙ (Помилка)",
        "rb_mark_white": "ГУМКА (Очистити)",
        "chk_auto_filler": "Автоматично позначати паразити",
        "chk_auto_del": "Авто-видаляти червоні кліпи",
        "btn_import": "Імпорт сценарію",
        "btn_compare": "Аналіз (Порівняння)",
        "btn_standalone": "Аналіз (Автономний)",
        
        "chk_show_inaudible": "Показати нерозбірливі фрагменти",
        "chk_mark_inaudible": "Позначати нерозбірливі фрагменти коричневим",
        "chk_show_typos": "Показати виявлені помилки",

        "btn_clear_trans": "Очистити Транскрипт",
        "msg_confirm_clear": "Видалити всі позначки?",
        "btn_clear_confirm": "Очистити",

        "chk_silence_cut": "Виявити та вирізати тишу",
        "chk_silence_mark": "Виявити та позначити тишу (бежевий)",
        "status_ready": "Готово.",
        "status_initializing": "Ініціалізація...",
        "status_render": "Рендеринг аудіо...",
        "status_norm": "Нормалізація аудіо...",
        "status_silence": "Виявлення тиші...",
        "status_check_model": "Перевірка/Завантаження моделі {model}...",
        "status_whisper_run": "Транскрибування ({model})...",
        "status_whisper_dl": "Завантаження {model}...",
        "status_processing": "Обробка даних...",
        "status_generating": "Монтаж таймлайну...",
        "status_cleanup": "Очищення...",
        "status_done": "Виконано!",
        "status_comparing": "Порівняння сценарію...",
        "status_reps": "Аналіз дублів...",
        "status_standalone": "Запуск автономного аналізу...",
        "status_compared": "Аналіз завершено. {diffs} розбіжностей.",
        
        "msg_success": "Таймлайн успішно змонтовано!",
        
        "msg_confirm_cancel": "Скасувати зміни?",
        "msg_confirm_apply": "Зберегти зміни?",
        "msg_confirm_quit": "Ви впевнені, що хочете вийти?",
        "title_confirm": "Підтвердження",
        "err_resolve": "API DaVinci Resolve не знайдено.",
        "err_timeline": "Відкрийте таймлайн перед запуском.",
        "err_render": "Помилка рендерингу.",
        "err_whisper": "Помилка Whisper.",
        "err_nowords": "Слів не виявлено.",
        "err_tl_create": "Помилка створення таймлайну.",
        "err_num": "Невірні числа.",
        "err_noscript": "Будь ласка, вставте сценарій.",
        "ph_script": "Вставте сценарій сюди...",
        "disclaimer": "УВАГА: Транскрипція може бути неточной.",
        "file_types": "Текст / Word / PDF",
        "err_dep": "Відсутня залежність: {dep}.",
        "lbl_page": "Стор. {current}/{total}",
        "btn_prev": "< Попер.",
        "btn_next": "Наст. >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "model_tiny": "Tiny (Швидкий, <1GB VRAM)",
        "model_base": "Base (Збалансированный, 1GB VRAM)",
        "model_small": "Small (Добре, 2GB VRAM)",
        "model_medium": "Medium (Найкращий баланс, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Швидкий і Точний, 6GB VRAM)",
        "model_large": "Large (Найточніший, 10GB VRAM)",
        "tooltip_dev": "Функция в розробці",
        "title_model_missing": "Модель відсутня",
        "msg_model_missing": "Модель '{model}' не встановлена.\nЗавантажити зараз?",
        "btn_dl_analyze": "Завантажити та Аналізувати",
        "status_downloading": "Завантаження {model}...",
        "err_download": "Помилка завантаження.",
        "msg_dl_success": "Модель '{model}' успішно встановлена.",

        # Language Search Placeholder
        "ph_lang_search": "Пошук мови...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Аналітика BadWords",
        "msg_telemetry": "Привіт! 👋\n\nЩоб допомогти мені покращити BadWords, чи погоджуєтесь ви надіслати одноразовий, 100% анонімний пінг після встановлення / оновлення?\n\nНадсилаються лише версія програми, тип ОС та ваше загальне місцезнаходження (країна/місто). Жодні аудіофайли, сценарії чи особисті дані НІКОЛИ не збираються.",
        "btn_telemetry_yes": "Я згоден",
        "btn_telemetry_no": "Ні, дякую"
    },

    "nl": {
        "name": "Nederlands",
        "title": "BadWords",
        "header_main": "BadWords Configuratie",
        "sec_whisper": "WHISPER & MODEL",
        "lbl_lang": "Taal:",
        "lbl_model": "Model:",
        "lbl_device": "Apparaat:",
        "lbl_fillers": "Opvulwoorden:",
        "btn_edit_fillers": "Lijst bewerken...",
        "title_edit_fillers": "Opvulwoorden Editor",
        "lbl_fillers_instr": "Bewerk woorden (komma gescheiden):",
        "sec_sync": "AUDIO SYNC (SECONDEN)",
        "lbl_offset": "Offset (s):",
        "lbl_pad": "Marge (s):",
        "lbl_snap": "Snap Max (s):",
        "lbl_thresh": "Stilte Drempel (dB):",
        "chk_reviewer": "Script Reviewer Inschakelen",
        
        "btn_analyze": "ANALYSEREN",
        "btn_cancel": "Annuleren",
        "btn_quit": "Afsluiten",
        "btn_apply": "Toepassen",
        "btn_generate": "Monteren",
        "btn_import_proj": "Importeren",
        "btn_export_proj": "Exporteren",
        "btn_dl_model": "Model Downloaden",
        "lbl_model_installed": "Model Geïnstalleerd ✔️",
        "header_rev_script": "Origineel Script (Geel = Ontbreekt in Audio)",
        "header_rev_trans": "Getranscribeerde Audio (Werkgebied)",
        "header_rev_tools": "Tools",
        "lbl_mark_color": "Markeermodus:",
        "rb_mark_red": "ROOD (Knippen/Opvulling)",
        "rb_mark_blue": "BLAUW (Opnieuw)",
        "rb_mark_green": "GROEN (Typfout)",
        "rb_mark_white": "GUM (Wissen)",
        "chk_auto_filler": "Opvulwoorden automatisch markieren",
        "chk_auto_del": "Rode clips automatisch verwijderen",
        "btn_import": "Script Importeren",
        "btn_compare": "Analysieren (Vergelijken)",
        "btn_standalone": "Analyseren (Losstaand)",
        
        "chk_show_inaudible": "Onhoorbare fragmenten tonen",
        "chk_mark_inaudible": "Markeer onhoorbare fragmenten met bruin",
        "chk_show_typos": "Gedetecteerde typfouten tonen",

        "btn_clear_trans": "Transcript Wissen",
        "msg_confirm_clear": "Alle markeringen wissen?",
        "btn_clear_confirm": "Wissen",

        "status_ready": "Klaar.",
        "status_initializing": "Initialiseren...",
        "status_render": "Audio renderen...",
        "status_norm": "Audio normaliseren...",
        "status_silence": "Stilte detecteren...",
        "status_check_model": "Model {model} verifiëren...",
        "status_whisper_run": "Transcriberen ({model})...",
        "status_whisper_dl": "{model} downloaden...",
        "status_processing": "Gegevens verwerken...",
        "status_generating": "Timeline monteren...",
        "status_cleanup": "Opruimen...",
        "status_done": "Klaar!",
        "status_comparing": "Script vergelijken...",
        "status_reps": "Takes analyseren...",
        "status_standalone": "Analyse uitvoeren...",
        "status_compared": "Analyse klaar. {diffs} verschillen.",
        
        "msg_success": "Timeline succesvol gemonteerd!",
        
        "msg_confirm_cancel": "Wijzigingen negeren?",
        "msg_confirm_apply": "Wijzigingen opslaan?",
        "msg_confirm_quit": "Weet je zeker dat je wilt afsluiten?",
        "title_confirm": "Bevestigen",
        "err_resolve": "DaVinci Resolve API niet gevonden.",
        "err_timeline": "Open een Timeline voor het starten.",
        "err_render": "Render mislukt.",
        "err_whisper": "Whisper mislukt.",
        "err_nowords": "Geen woorden gedetecteerd.",
        "err_tl_create": "Maken van Timeline mislukt.",
        "err_num": "Ongeldige getallen.",
        "err_noscript": "Plak eerst een script.",
        "ph_script": "Plak script hier...",
        "disclaimer": "DISCLAIMER: Transcripties kunnen onnauwkeurig zijn.",
        "file_types": "Tekst / Word / PDF",
        "err_dep": "Ontbrekende afhankelijkheid: {dep}.",
        "lbl_page": "Pag {current}/{total}",
        "btn_prev": "< Vorige",
        "btn_next": "Volgende >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "chk_silence_cut": "Stilte detecteren en knippen",
        "chk_silence_mark": "Stilte detecteren en markieren (tan)",
        "model_tiny": "Tiny (Snel, <1GB VRAM)",
        "model_base": "Base (Gebalanceerd, 1GB VRAM)",
        "model_small": "Small (Goed, 2GB VRAM)",
        "model_medium": "Medium (Beste balans, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Snel & Precies, 6GB VRAM)",
        "model_large": "Large (Meest Accuraat, 10GB VRAM)",
        "tooltip_dev": "Functie in ontwikkeling",
        "title_model_missing": "Model Ontbreekt",
        "msg_model_missing": "Het model '{model}' is niet geïnstalleerd.\nNu downloaden?",
        "btn_dl_analyze": "Downloaden & Analyseren",
        "status_downloading": "{model} downloaden...",
        "err_download": "Download mislukt.",
        "msg_dl_success": "Model '{model}' succesvol geïnstalleerd.",

        # Language Search Placeholder
        "ph_lang_search": "Taal zoeken...",
        
        # TELEMETRY POPUP
        "title_telemetry": "BadWords Analytica",
        "msg_telemetry": "Hallo! 👋\n\nOm me te helpen BadWords te verbeteren, ga je ermee akkoord om na de installatie / update een eenmalige, 100% anonieme ping te sturen?\n\nAlleen de app-versie, het besturingssysteem en je algemene locatie (land/stad) worden verzonden. Er worden NOOIT audiobestanden, scripts of persoonlijke gegevens verzameld.",
        "btn_telemetry_yes": "Ik ga akkoord",
        "btn_telemetry_no": "Nee, bedankt"
    },

    "ru": {
        "name": "Русский",
        "title": "BadWords",
        "header_main": "Настройки BadWords",
        "sec_whisper": "WHISPER И МОДЕЛЬ",
        "lbl_lang": "Язык:",
        "lbl_model": "Модель:",
        "lbl_device": "Устройство:",
        "lbl_fillers": "Слова-паразити:",
        "btn_edit_fillers": "Изменить список...",
        "title_edit_fillers": "Редактор слов-паразитов",
        "lbl_fillers_instr": "Измените слова (через запятую):",
        "sec_sync": "СИНХРОНИЗАЦИЯ АУДИО (СЕК)",
        "lbl_offset": "Сдвиг (с):",
        "lbl_pad": "Отступ (с):",
        "lbl_snap": "Прилипание (с):",
        "lbl_thresh": "Порог тишины (dB):",
        "chk_reviewer": "Включить рецензента сценария",
        
        "btn_analyze": "АНАЛИЗ",
        "btn_cancel": "Отмена",
        "btn_quit": "Выход",
        "btn_apply": "Применить",
        "btn_generate": "Собрать",
        "btn_import_proj": "Импорт",
        "btn_export_proj": "Экспорт",
        "btn_dl_model": "Скачать модель",
        "lbl_model_installed": "Модель установлена ✔️",
        "header_rev_script": "Оригинальный сценарий (Желтый = Нет в аудио)",
        "header_rev_trans": "Транскрибированное аудио (Рабочая зона)",
        "header_rev_tools": "Инструменти",
        "lbl_mark_color": "Режим маркировки:",
        "rb_mark_red": "КРАСНЫЙ (Вырезать/Мусор)",
        "rb_mark_blue": "СИНИЙ (Дубль)",
        "rb_mark_green": "ЗЕЛЕНИЙ (Опечатка)",
        "rb_mark_white": "ЛАСТИК (Стереть)",
        "chk_auto_filler": "Авто-пометка паразитов",
        "chk_auto_del": "Авто-удаление красных клипов",
        "btn_import": "Импорт сценария",
        "btn_compare": "Анализ (Сравнение)",
        "btn_standalone": "Анализ (Автономний)",
        
        "chk_show_inaudible": "Показать неразборчивые фрагменти",
        "chk_mark_inaudible": "Помечать неразборчивые фрагменты коричневым",
        "chk_show_typos": "Показать обнаруженные опечатки",

        "btn_clear_trans": "Очистить",
        "msg_confirm_clear": "Удалить все пометки?",
        "btn_clear_confirm": "Очистить",

        "chk_silence_cut": "Обнаружить и вырезать тишину",
        "chk_silence_mark": "Обнаружить и пометить тишину (бежевий)",
        "status_ready": "Готово.",
        "status_initializing": "Инициализация...",
        "status_render": "Рендеринг аудио...",
        "status_norm": "Нормализация аудио...",
        "status_silence": "Обнаружение тишины...",
        "status_check_model": "Проверка/Загрузка модели {model}...",
        "status_whisper_run": "Транскрибация ({model})...",
        "status_whisper_dl": "Скачивание {model}...",
        "status_processing": "Обработка данных...",
        "status_generating": "Сборка таймлайна...",
        "status_cleanup": "Очистка...",
        "status_done": "Выполнено!",
        "status_comparing": "Сравнение сценария...",
        "status_reps": "Анализ дублей...",
        "status_standalone": "Запуск автономного анализа...",
        "status_compared": "Анализ завершен. {diffs} расхождений.",
        
        "msg_success": "Таймлайн успешно собран!",
        
        "msg_confirm_cancel": "Отменить изменения?",
        "msg_confirm_apply": "Сохранить изменения?",
        "msg_confirm_quit": "Вы уверены, что хотите выйти?",
        "title_confirm": "Подтверждение",
        "err_resolve": "API DaVinci Resolve не найден.",
        "err_timeline": "Откройте таймлайн перед запуском.",
        "err_render": "Ошибка рендеринга.",
        "err_whisper": "Ошибка Whisper.",
        "err_nowords": "Слов не обнаружено.",
        "err_tl_create": "Ошибка создания таймлайна.",
        "err_num": "Неверные числа.",
        "err_noscript": "Пожалуйста, вставьте сценарий.",
        "ph_script": "Вставьте сценарий сюда...",
        "disclaimer": "ВНИМАНИЕ: Транскрипция может быть неточной.",
        "file_types": "Текст / Word / PDF",
        "err_dep": "Отсутствует зависимость: {dep}.",
        "lbl_page": "Стр. {current}/{total}",
        "btn_prev": "< Пред.",
        "btn_next": "След. >",
        "lbl_inaudible_tag": "(...)",
        "txt_inaudible": "(...)",
        "model_tiny": "Tiny (Быстрый, <1GB VRAM)",
        "model_base": "Base (Сбалансированный, 1GB VRAM)",
        "model_small": "Small (Хороший, 2GB VRAM)",
        "model_medium": "Medium (Лучший баланс, 5GB VRAM)",
        "model_large_turbo": "Large Turbo (Быстрый и точный, 6GB VRAM)",
        "model_large": "Large (Самый точный, 10GB VRAM)",
        "tooltip_dev": "Функция в разработке",
        "title_model_missing": "Модель отсутствует",
        "msg_model_missing": "Модель '{model}' не установлена.\nСкачать сейчас?",
        "btn_dl_analyze": "Скачать и Анализировать",
        "status_downloading": "Скачивание {model}...",
        "err_download": "Ошибка скачивания.",
        "msg_dl_success": "Модель '{model}' успешно установлена.",
        
        # Language Search Placeholder
        "ph_lang_search": "Поиск языка...",
        
        # TELEMETRY POPUP
        "title_telemetry": "Аналитика BadWords",
        "msg_telemetry": "Привет! 👋\n\nЧтобы помочь мне улучшить BadWords, согласны ли вы отправить одноразовый, 100% анонимный пинг после установки / обновления?\n\nОтправляются только версия приложения, тип ОС и ваше общее местоположение (страна/город). Аудиофайлы, сценарии или личные данные НИКОГДА не собираются.",
        "btn_telemetry_yes": "Я согласен",
        "btn_telemetry_no": "Нет, спасибо"
    }
}

def get_trans(key, lang_code="en"):
    """
    Safely retrieves translation for a given key.
    Falls back to English if key/language missing.
    """
    lang_dict = TRANS.get(lang_code, TRANS["en"])
    return lang_dict.get(key, TRANS["en"].get(key, f"[{key}]"))