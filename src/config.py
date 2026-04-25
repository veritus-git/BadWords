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
VERSION = "2.0.3"
POSTHOG_API_KEY = "phc_NRFaTKhPJJE8cBa3o9gXYo2mlktR5qup5tn7PdxuRsr" 
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
BTN_BG = "#23a559"             
BTN_FG = "#ffffff"
BTN_ACTIVE = "#1e8f4c"

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

SUPPORTED_LANGS = {
    'en': 'English',
    'pl': 'Polski',
    'de': 'Deutsch',
    'es': 'Español',
    'fr': 'Français',
    'it': 'Italiano',
    'pt': 'Português',
    'uk': 'Українська',
    'nl': 'Nederlands',
    'ru': 'Русский'
}
TRANS = {
    'en': {
        "btn_analyze": "Analyze",
        "btn_analyze_compare": "Analyze (Compare)",
        "btn_analyze_standalone": "Analyze (Standalone)",
        "btn_apply": "Apply",
        "btn_assemble": "Assemble",
        "btn_clear": "Clear",
        "btn_close": "Close",
        "btn_export_project": "Export Project",
        "btn_fast_silence_detection": "Fast Silence Detection",
        "btn_import_project": "Import Project",
        "btn_import_script": "Import Script",
        "btn_restart_later": "Restart Later",
        "btn_restart_now": "Restart Now",
        "btn_restore_defaults": "Restore Defaults",
        "btn_run_fast_silence": "Run Fast Silence",
        "btn_save": "Save",
        "btn_back_to_transcription": "Back to Transcription",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Add Custom Marker",
        "lbl_cut_silence_directly": "Cut silence directly",
        "lbl_detect_and_cut_silence": "Detect and cut silence",
        "lbl_detect_and_mark_silence": "Detect and mark silence",
        "lbl_device": "Device",
        "lbl_display_mode": "Display Mode",
        "lbl_fast_silence_workspace": "Fast Silence Workspace",
        "lbl_font_size_pt": "Font size (pt)",
        "lbl_initializing": "Initializing...",
        "lbl_lang": "Language",
        "lbl_language": "Language",
        "lbl_line_spacing_px": "Line spacing (px)",
        "lbl_loading": "Loading...",
        "lbl_mark_filler_words_automat": "Mark filler words automatically",
        "lbl_mark_inaudible_fragments": "Mark inaudible fragments",
        "lbl_mark_silence_with_color": "Mark silence with color",
        "lbl_marking_mode": "Marking Mode",
        "lbl_model": "Model",
        "lbl_offset_s": "Offset (s)",
        "lbl_padding_s": "Padding (s)",
        "lbl_pinned_favorites": "Pinned Favorites",
        "lbl_ripple_delete_red_clips": "<span style='color: #ed4245;'>Ripple Delete</span> red clips",
        "lbl_show_detected_typos": "Show detected typos",
        "lbl_show_inaudible_fragments": "Show inaudible fragments",
        "lbl_silence_threshold_db": "Silence threshold (dB)",
        "lbl_snap_max_s": "Snap max (s)",
        "lbl_threshold_db": "Threshold (dB)",
        "lbl_timeline_selection": "Timeline Selection",
        "lbl_tracks_selection": "Track/s Selection",
        "lbl_transcript_font": "Transcript font",
        "lbl_transcription_workspace": "Transcription Workspace",
        "lbl_words": "words",
        "msg_analysis_failed": "Analysis failed.",
        "msg_fast_silence": "Fast Silence",
        "msg_fast_silence_processing_c": "Fast silence processing complete.",
        "msg_no_active_transcription_t": "No active transcription timeline detected.",
        "msg_no_silence_segments_detec": "No silence segments detected.",
        "msg_please_import_or_paste_a": "Please import or paste a script first.",
        "msg_restart_lang": "Language changed. Please restart BadWords.",
        "msg_success": "Success",
        "msg_the_transcription_process": "The transcription process has finished.",
        "msg_timeline_assembled_succes": "Timeline assembled successfully.",
        "msg_title_language_changed": "Language Changed",
        "msg_warning": "Warning",
        "opt_segmented_blocks": "Segmented blocks",
        "ph_paste_script_here": "Paste script here...",
        "ph_search": "Search...",
        "rad_blue_retake": "Blue: Retake",
        "rad_eraser_clear": "Eraser: Clear",
        "rad_green_typo": "Green: Typo",
        "rad_red_cut_filler": "Red: Cut / Filler",
        "tab_appearance": "Appearance",
        "tab_audio_sync": "Audio Sync",
        "tab_general": "General",
        "tool_assembly": "Assembly",
        "tool_filler_words": "Filler Words",
        "tool_main_panel": "Main Panel",
        "tool_mark_inaudible": "Mark Inaudible",
        "tool_quit": "Quit",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Script Analysis",
        "tool_settings": "Settings",
        "tool_show_inaudible": "Show Inaudible",
        "tool_show_typos": "Show Typos",
        "tool_silence": "Silence",
        "tooltip_clear_all_markings": "Clear all markings",
        "tooltip_dev": "Feature in development",
        "tt_revert_to_default": "Revert to default",
        "txt_assembling_timeline": "Assembling timeline...",
        "txt_finishing": "Finishing...",
        "txt_initializing_analysis": "Initializing analysis...",
        "txt_initializing_assembly": "Initializing assembly...",
        "txt_initializing_fast_silence": "Initializing Fast Silence...",
        "txt_save": "Save",
        "txt_saved": "Saved",
        "txt_select": "Select...",
        "txt_select_tracks": "Select tracks..."
    },
    'pl': {
        "btn_analyze": "Analizuj",
        "btn_analyze_compare": "Analizuj (Porównaj)",
        "btn_analyze_standalone": "Analizuj (Bez Skryptu)",
        "btn_apply": "Zastosuj",
        "btn_assemble": "Montuj",
        "btn_clear": "Wyczyść",
        "btn_close": "Zamknij",
        "btn_export_project": "Eksportuj Projekt",
        "btn_fast_silence_detection": "Szybkie Wykrywanie Ciszy",
        "btn_import_project": "Importuj Projekt",
        "btn_import_script": "Importuj Scenariusz",
        "btn_restart_later": "Uruchom Ponownie Później",
        "btn_restart_now": "Uruchom Ponownie Teraz",
        "btn_restore_defaults": "Przywróć Domyślne",
        "btn_run_fast_silence": "Uruchom Szybką Ciszę",
        "btn_save": "Zapisz",
        "btn_back_to_transcription": "Powrót do Transkrypcji",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Dodaj Własny Znacznik",
        "lbl_cut_silence_directly": "Wytnij ciszę bezpośrednio",
        "lbl_detect_and_cut_silence": "Wykryj i wytnij ciszę",
        "lbl_detect_and_mark_silence": "Wykryj i oznacz ciszę",
        "lbl_device": "Urządzenie",
        "lbl_display_mode": "Tryb Wyświetlania",
        "lbl_fast_silence_workspace": "Przestrzeń Robocza Ciszy",
        "lbl_font_size_pt": "Rozmiar czcionki (pt)",
        "lbl_initializing": "Inicjalizowanie...",
        "lbl_lang": "Język",
        "lbl_language": "Język",
        "lbl_line_spacing_px": "Odstępy linii (px)",
        "lbl_loading": "Ładowanie...",
        "lbl_mark_filler_words_automat": "Oznaczaj wypełniacze automatycznie",
        "lbl_mark_inaudible_fragments": "Oznaczaj niezrozumiałe fragmenty",
        "lbl_mark_silence_with_color": "Oznacz ciszę kolorem",
        "lbl_marking_mode": "Tryb Zaznaczania",
        "lbl_model": "Model",
        "lbl_offset_s": "Przesunięcie (s)",
        "lbl_padding_s": "Margines (s)",
        "lbl_pinned_favorites": "Przypięte Narzędzia",
        "lbl_ripple_delete_red_clips": "Usuń ze zsuwaniem (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Pokaż wykryte literówki",
        "lbl_show_inaudible_fragments": "Pokaż niezrozumiałe fragmenty",
        "lbl_silence_threshold_db": "Próg ciszy (dB)",
        "lbl_snap_max_s": "Przyciąganie maks. (s)",
        "lbl_threshold_db": "Próg (dB)",
        "lbl_timeline_selection": "Wybór Osi Czasu",
        "lbl_tracks_selection": "Wybór Ścieżek",
        "lbl_transcript_font": "Czcionka transkryptu",
        "lbl_transcription_workspace": "Przestrzeń Transkrypcji",
        "lbl_words": "słów",
        "msg_analysis_failed": "Analiza nie powiodła się.",
        "msg_fast_silence": "Szybka Cisza",
        "msg_fast_silence_processing_c": "Przetwarzanie ciszy zakończone.",
        "msg_no_active_transcription_t": "Nie wykryto aktywnej osi czasu.",
        "msg_no_silence_segments_detec": "Nie wykryto segmentów ciszy.",
        "msg_please_import_or_paste_a": "Najpierw zaimportuj lub wklej scenariusz.",
        "msg_restart_lang": "Zmieniono język. Uruchom BadWords ponownie.",
        "msg_success": "Sukces",
        "msg_the_transcription_process": "Proces transkrypcji został zakończony.",
        "msg_timeline_assembled_succes": "Timeline zmontowany pomyślnie.",
        "msg_title_language_changed": "Zmieniono Język",
        "msg_warning": "Ostrzeżenie",
        "opt_segmented_blocks": "Podzielone bloki",
        "ph_paste_script_here": "Wklej scenariusz tutaj...",
        "ph_search": "Szukaj...",
        "rad_blue_retake": "Niebieski: Dubel (Retake)",
        "rad_eraser_clear": "Gumka: Wyczyść",
        "rad_green_typo": "Zielony: Literówka",
        "rad_red_cut_filler": "Czerwony: Cięcie / Wypełniacz",
        "tab_appearance": "Wygląd",
        "tab_audio_sync": "Synchronizacja",
        "tab_general": "Ogólne",
        "tool_assembly": "Montaż",
        "tool_filler_words": "Wypełniacze",
        "tool_main_panel": "Panel Główny",
        "tool_mark_inaudible": "Oznacz Niezrozumiałe",
        "tool_quit": "Wyjdź",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Analiza Skryptu",
        "tool_settings": "Ustawienia",
        "tool_show_inaudible": "Pokaż Niezrozumiałe",
        "tool_show_typos": "Pokaż Literówki",
        "tool_silence": "Cisza",
        "tooltip_clear_all_markings": "Wyczyść wszystkie oznaczenia",
        "tooltip_dev": "Funkcja wciąż w produkcji",
        "tt_revert_to_default": "Przywróć domyślne",
        "txt_assembling_timeline": "Montowanie timeline...",
        "txt_finishing": "Kończenie...",
        "txt_initializing_analysis": "Inicjalizacja analizy...",
        "txt_initializing_assembly": "Inicjalizacja montażu...",
        "txt_initializing_fast_silence": "Inicjalizacja Szybkiej Ciszy...",
        "txt_save": "Zapisz",
        "txt_saved": "Zapisano",
        "txt_select": "Wybierz...",
        "txt_select_tracks": "Wybierz ścieżki..."
},
    'de': {
        "btn_analyze": "Analysieren",
        "btn_analyze_compare": "Analysieren (Vergleichen)",
        "btn_analyze_standalone": "Analysieren (Ohne Skript)",
        "btn_apply": "Anwenden",
        "btn_assemble": "Montieren",
        "btn_clear": "Löschen",
        "btn_close": "Schließen",
        "btn_export_project": "Projekt exportieren",
        "btn_fast_silence_detection": "Schnelle Stille-Erkennung",
        "btn_import_project": "Projekt importieren",
        "btn_import_script": "Skript importieren",
        "btn_restart_later": "Später neu starten",
        "btn_restart_now": "Jetzt neu starten",
        "btn_restore_defaults": "Standard wiederherstellen",
        "btn_run_fast_silence": "Schnelle Stille starten",
        "btn_save": "Speichern",
        "btn_back_to_transcription": "Zurück zur Transkription",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Eigenen Marker hinzufügen",
        "lbl_cut_silence_directly": "Stille direkt schneiden",
        "lbl_detect_and_cut_silence": "Stille erkennen und schneiden",
        "lbl_detect_and_mark_silence": "Stille erkennen und markieren",
        "lbl_device": "Gerät",
        "lbl_display_mode": "Anzeigemodus",
        "lbl_fast_silence_workspace": "Stille-Arbeitsbereich",
        "lbl_font_size_pt": "Schriftgröße (pt)",
        "lbl_initializing": "Initialisiere...",
        "lbl_lang": "Sprache",
        "lbl_language": "Sprache",
        "lbl_line_spacing_px": "Zeilenabstand (px)",
        "lbl_loading": "Lade...",
        "lbl_mark_filler_words_automat": "Füllwörter automatisch markieren",
        "lbl_mark_inaudible_fragments": "Unhörbare Fragmente markieren",
        "lbl_mark_silence_with_color": "Stille farbig markieren",
        "lbl_marking_mode": "Markierungsmodus",
        "lbl_model": "Modell",
        "lbl_offset_s": "Versatz (s)",
        "lbl_padding_s": "Polster (s)",
        "lbl_pinned_favorites": "Angeheftete Favoriten",
        "lbl_ripple_delete_red_clips": "Rote Clips automatisch löschen (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Erkannte Tippfehler anzeigen",
        "lbl_show_inaudible_fragments": "Unhörbare Fragmente anzeigen",
        "lbl_silence_threshold_db": "Stille-Schwelle (dB)",
        "lbl_snap_max_s": "Einrasten (s)",
        "lbl_threshold_db": "Schwelle (dB)",
        "lbl_timeline_selection": "Timeline-Auswahl",
        "lbl_tracks_selection": "Spur-Auswahl",
        "lbl_transcript_font": "Transkript-Schriftart",
        "lbl_transcription_workspace": "Transkriptions-Arbeitsbereich",
        "lbl_words": "Wörter",
        "msg_analysis_failed": "Analyse fehlgeschlagen.",
        "msg_fast_silence": "Schnelle Stille",
        "msg_fast_silence_processing_c": "Stille-Verarbeitung abgeschlossen.",
        "msg_no_active_transcription_t": "Keine aktive Transkriptions-Timeline erkannt.",
        "msg_no_silence_segments_detec": "Keine Stille-Segmente erkannt.",
        "msg_please_import_or_paste_a": "Bitte zuerst ein Skript einfügen oder importieren.",
        "msg_restart_lang": "Sprache geändert. Bitte BadWords neu starten.",
        "msg_success": "Erfolg",
        "msg_the_transcription_process": "Der Transkriptionsprozess ist abgeschlossen.",
        "msg_timeline_assembled_succes": "Timeline erfolgreich montiert.",
        "msg_title_language_changed": "Sprache geändert",
        "msg_warning": "Warnung",
        "opt_segmented_blocks": "Segmentierte Blöcke",
        "ph_paste_script_here": "Skript hier einfügen...",
        "ph_search": "Suchen...",
        "rad_blue_retake": "Blau: Retake",
        "rad_eraser_clear": "Radierer: Löschen",
        "rad_green_typo": "Grün: Tippfehler",
        "rad_red_cut_filler": "Rot: Schnitt / Füller",
        "tab_appearance": "Aussehen",
        "tab_audio_sync": "Audio-Sync",
        "tab_general": "Allgemein",
        "tool_assembly": "Montage",
        "tool_filler_words": "Füllwörter",
        "tool_main_panel": "Hauptpanel",
        "tool_mark_inaudible": "Unhörbare markieren",
        "tool_quit": "Beenden",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Skript-Analyse",
        "tool_settings": "Einstellungen",
        "tool_show_inaudible": "Unhörbare anzeigen",
        "tool_show_typos": "Tippfehler anzeigen",
        "tool_silence": "Stille",
        "tooltip_clear_all_markings": "Alle Markierungen löschen",
        "tooltip_dev": "Funktion noch in Entwicklung",
        "tt_revert_to_default": "Auf Standard zurücksetzen",
        "txt_assembling_timeline": "Timeline wird montiert...",
        "txt_finishing": "Abschließen...",
        "txt_initializing_analysis": "Initialisiere Analyse...",
        "txt_initializing_assembly": "Initialisiere Montage...",
        "txt_initializing_fast_silence": "Initialisiere Schnelle Stille...",
        "txt_save": "Speichern",
        "txt_saved": "Gespeichert",
        "txt_select": "Auswählen...",
        "txt_select_tracks": "Spuren auswählen..."
},
    'es': {
        "btn_analyze": "Analizar",
        "btn_analyze_compare": "Analizar (Comparar)",
        "btn_analyze_standalone": "Analizar (Independiente)",
        "btn_apply": "Aplicar",
        "btn_assemble": "Ensamblar",
        "btn_clear": "Borrar",
        "btn_close": "Cerrar",
        "btn_export_project": "Exportar Proyecto",
        "btn_fast_silence_detection": "Detección Rápida de Silencio",
        "btn_import_project": "Importar Proyecto",
        "btn_import_script": "Importar Guion",
        "btn_restart_later": "Reiniciar más tarde",
        "btn_restart_now": "Reiniciar ahora",
        "btn_restore_defaults": "Restaurar Predeterminados",
        "btn_run_fast_silence": "Ejecutar Silencio Rápido",
        "btn_save": "Guardar",
        "btn_back_to_transcription": "Volver a Transcripción",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Añadir Marcador Personalizado",
        "lbl_cut_silence_directly": "Cortar silencio directamente",
        "lbl_detect_and_cut_silence": "Detectar y cortar silencio",
        "lbl_detect_and_mark_silence": "Detectar y marcar silencio",
        "lbl_device": "Dispositivo",
        "lbl_display_mode": "Modo de Visualización",
        "lbl_fast_silence_workspace": "Espacio de Silencio Rápido",
        "lbl_font_size_pt": "Tamaño de fuente (pt)",
        "lbl_initializing": "Inicializando...",
        "lbl_lang": "Idioma",
        "lbl_language": "Idioma",
        "lbl_line_spacing_px": "Interlineado (px)",
        "lbl_loading": "Cargando...",
        "lbl_mark_filler_words_automat": "Marcar muletillas automáticamente",
        "lbl_mark_inaudible_fragments": "Marcar fragmentos inaudibles",
        "lbl_mark_silence_with_color": "Marcar silencio con color",
        "lbl_marking_mode": "Modo de Marcado",
        "lbl_model": "Modelo",
        "lbl_offset_s": "Desplazamiento (s)",
        "lbl_padding_s": "Margen (s)",
        "lbl_pinned_favorites": "Favoritos Anclados",
        "lbl_ripple_delete_red_clips": "Eliminar clips rojos (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Mostrar erratas detectadas",
        "lbl_show_inaudible_fragments": "Mostrar fragmentos inaudibles",
        "lbl_silence_threshold_db": "Umbral de silencio (dB)",
        "lbl_snap_max_s": "Ajuste máx. (s)",
        "lbl_threshold_db": "Umbral (dB)",
        "lbl_timeline_selection": "Selección de Timeline",
        "lbl_tracks_selection": "Selección de Pistas",
        "lbl_transcript_font": "Fuente de transcripción",
        "lbl_transcription_workspace": "Espacio de Transcripción",
        "lbl_words": "palabras",
        "msg_analysis_failed": "Análisis fallido.",
        "msg_fast_silence": "Silencio Rápido",
        "msg_fast_silence_processing_c": "Procesamiento de silencio completo.",
        "msg_no_active_transcription_t": "No se detectó timeline de transcripción activa.",
        "msg_no_silence_segments_detec": "No se detectaron segmentos de silencio.",
        "msg_please_import_or_paste_a": "Por favor, importa o pega un guion primero.",
        "msg_restart_lang": "Idioma cambiado. Por favor, reinicia BadWords.",
        "msg_success": "Éxito",
        "msg_the_transcription_process": "El proceso de transcripción ha terminado.",
        "msg_timeline_assembled_succes": "Timeline ensamblada con éxito.",
        "msg_title_language_changed": "Idioma Cambiado",
        "msg_warning": "Advertencia",
        "opt_segmented_blocks": "Bloques segmentados",
        "ph_paste_script_here": "Pega el guion aquí...",
        "ph_search": "Buscar...",
        "rad_blue_retake": "Azul: Retoma",
        "rad_eraser_clear": "Borrador: Limpiar",
        "rad_green_typo": "Verde: Errata",
        "rad_red_cut_filler": "Rojo: Cortar / Relleno",
        "tab_appearance": "Apariencia",
        "tab_audio_sync": "Sincronización",
        "tab_general": "General",
        "tool_assembly": "Ensamblaje",
        "tool_filler_words": "Muletillas",
        "tool_main_panel": "Panel Principal",
        "tool_mark_inaudible": "Marcar Inaudible",
        "tool_quit": "Salir",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Análisis de Guion",
        "tool_settings": "Configuración",
        "tool_show_inaudible": "Mostrar Inaudible",
        "tool_show_typos": "Mostrar Erratas",
        "tool_silence": "Silencio",
        "tooltip_clear_all_markings": "Borrar todas las marcas",
        "tooltip_dev": "Función en desarrollo",
        "tt_revert_to_default": "Volver a predeterminado",
        "txt_assembling_timeline": "Ensamblando timeline...",
        "txt_finishing": "Finalizando...",
        "txt_initializing_analysis": "Inicializando análisis...",
        "txt_initializing_assembly": "Inicializando ensamblaje...",
        "txt_initializing_fast_silence": "Inicializando Silencio Rápido...",
        "txt_save": "Guardar",
        "txt_saved": "Guardado",
        "txt_select": "Seleccionar...",
        "txt_select_tracks": "Seleccionar pistas..."
    },
    'fr': {
        "btn_analyze": "Analyser",
        "btn_analyze_compare": "Analyser (Comparer)",
        "btn_analyze_standalone": "Analyser (Autonome)",
        "btn_apply": "Appliquer",
        "btn_assemble": "Assembler",
        "btn_clear": "Effacer",
        "btn_close": "Fermer",
        "btn_export_project": "Exporter le Projet",
        "btn_fast_silence_detection": "Détection Rapide de Silence",
        "btn_import_project": "Importer le Projet",
        "btn_import_script": "Importer le Script",
        "btn_restart_later": "Redémarrer plus tard",
        "btn_restart_now": "Redémarrer maintenant",
        "btn_restore_defaults": "Restaurer par défaut",
        "btn_run_fast_silence": "Lancer Silence Rapide",
        "btn_save": "Enregistrer",
        "btn_back_to_transcription": "Retour à la Transcription",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Ajouter un marqueur personnalisé",
        "lbl_cut_silence_directly": "Couper le silence directement",
        "lbl_detect_and_cut_silence": "Détecter et couper le silence",
        "lbl_detect_and_mark_silence": "Détecter et marquer le silence",
        "lbl_device": "Périphérique",
        "lbl_display_mode": "Mode d'affichage",
        "lbl_fast_silence_workspace": "Espace Silence Rapide",
        "lbl_font_size_pt": "Taille de police (pt)",
        "lbl_initializing": "Initialisation...",
        "lbl_lang": "Langue",
        "lbl_language": "Langue",
        "lbl_line_spacing_px": "Espacement des lignes (px)",
        "lbl_loading": "Chargement...",
        "lbl_mark_filler_words_automat": "Marquer les mots de remplissage auto",
        "lbl_mark_inaudible_fragments": "Marquer les fragments inaudibles",
        "lbl_mark_silence_with_color": "Marquer le silence en couleur",
        "lbl_marking_mode": "Mode de marquage",
        "lbl_model": "Modèle",
        "lbl_offset_s": "Décalage (s)",
        "lbl_padding_s": "Marge (s)",
        "lbl_pinned_favorites": "Favoris épinglés",
        "lbl_ripple_delete_red_clips": "Supprimer avec raccord (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Afficher les coquilles détectées",
        "lbl_show_inaudible_fragments": "Afficher les fragments inaudibles",
        "lbl_silence_threshold_db": "Seuil de silence (dB)",
        "lbl_snap_max_s": "Alignement max (s)",
        "lbl_threshold_db": "Seuil (dB)",
        "lbl_timeline_selection": "Sélection de la Timeline",
        "lbl_tracks_selection": "Sélection des Pistes",
        "lbl_transcript_font": "Police de transcription",
        "lbl_transcription_workspace": "Espace de Transcription",
        "lbl_words": "mots",
        "msg_analysis_failed": "L'analyse a échoué.",
        "msg_fast_silence": "Silence Rapide",
        "msg_fast_silence_processing_c": "Traitement du silence terminé.",
        "msg_no_active_transcription_t": "Aucune timeline de transcription active détectée.",
        "msg_no_silence_segments_detec": "Aucun segment de silence détecté.",
        "msg_please_import_or_paste_a": "Veuillez d'abord importer ou coller un script.",
        "msg_restart_lang": "Langue modifiée. Veuillez redémarrer BadWords.",
        "msg_success": "Succès",
        "msg_the_transcription_process": "Le processus de transcription est terminé.",
        "msg_timeline_assembled_succes": "Timeline assemblée avec succès.",
        "msg_title_language_changed": "Langue modifiée",
        "msg_warning": "Avertissement",
        "opt_segmented_blocks": "Blocs segmentés",
        "ph_paste_script_here": "Collez le script ici...",
        "ph_search": "Rechercher...",
        "rad_blue_retake": "Bleu : Reprise",
        "rad_eraser_clear": "Gomme : Effacer",
        "rad_green_typo": "Vert : Coquille",
        "rad_red_cut_filler": "Rouge : Couper / Remplissage",
        "tab_appearance": "Apparence",
        "tab_audio_sync": "Sync Audio",
        "tab_general": "Général",
        "tool_assembly": "Assemblage",
        "tool_filler_words": "Mots de remplissage",
        "tool_main_panel": "Panneau principal",
        "tool_mark_inaudible": "Marquer inaudible",
        "tool_quit": "Quitter",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Analyse de Script",
        "tool_settings": "Paramètres",
        "tool_show_inaudible": "Afficher inaudible",
        "tool_show_typos": "Afficher les coquilles",
        "tool_silence": "Silence",
        "tooltip_clear_all_markings": "Effacer toutes les marques",
        "tooltip_dev": "Fonctionnalité en développement",
        "tt_revert_to_default": "Restaurer par défaut",
        "txt_assembling_timeline": "Assemblage de la timeline...",
        "txt_finishing": "Finalisation...",
        "txt_initializing_analysis": "Initialisation de l'analyse...",
        "txt_initializing_assembly": "Initialisation de l'assemblage...",
        "txt_initializing_fast_silence": "Initialisation du Silence Rapide...",
        "txt_save": "Enregistrer",
        "txt_saved": "Enregistré",
        "txt_select": "Sélectionner...",
        "txt_select_tracks": "Sélectionner les pistes..."
    },
    'it': {
        "btn_analyze": "Analizza",
        "btn_analyze_compare": "Analizza (Confronta)",
        "btn_analyze_standalone": "Analizza (Indipendente)",
        "btn_apply": "Applica",
        "btn_assemble": "Assembla",
        "btn_clear": "Pulisci",
        "btn_close": "Chiudi",
        "btn_export_project": "Esporta Progetto",
        "btn_fast_silence_detection": "Rilevamento Rapido Silenzio",
        "btn_import_project": "Importa Progetto",
        "btn_import_script": "Importa Script",
        "btn_restart_later": "Riavvia più tardi",
        "btn_restart_now": "Riavvia ora",
        "btn_restore_defaults": "Ripristina Predefiniti",
        "btn_run_fast_silence": "Avvia Silenzio Rapido",
        "btn_save": "Salva",
        "btn_back_to_transcription": "Torna alla Trascrizione",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Aggiungi Marcatore Personalizzato",
        "lbl_cut_silence_directly": "Taglia silenzio direttamente",
        "lbl_detect_and_cut_silence": "Rileva e taglia silenzio",
        "lbl_detect_and_mark_silence": "Rileva e segna silenzio",
        "lbl_device": "Dispositivo",
        "lbl_display_mode": "Modalità di Visualizzazione",
        "lbl_fast_silence_workspace": "Area di Lavoro Silenzio",
        "lbl_font_size_pt": "Dimensione carattere (pt)",
        "lbl_initializing": "Inizializzazione...",
        "lbl_lang": "Lingua",
        "lbl_language": "Lingua",
        "lbl_line_spacing_px": "Interlinea (px)",
        "lbl_loading": "Caricamento...",
        "lbl_mark_filler_words_automat": "Segna riempitivi automaticamente",
        "lbl_mark_inaudible_fragments": "Segna frammenti inudibili",
        "lbl_mark_silence_with_color": "Segna silenzio con colore",
        "lbl_marking_mode": "Modalità Marcatura",
        "lbl_model": "Modello",
        "lbl_offset_s": "Offset (s)",
        "lbl_padding_s": "Margine (s)",
        "lbl_pinned_favorites": "Preferiti Fissati",
        "lbl_ripple_delete_red_clips": "Elimina clip rosse (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Mostra refusi rilevati",
        "lbl_show_inaudible_fragments": "Mostra frammenti inudibili",
        "lbl_silence_threshold_db": "Soglia di silenzio (dB)",
        "lbl_snap_max_s": "Snap max (s)",
        "lbl_threshold_db": "Soglia (dB)",
        "lbl_timeline_selection": "Selezione Timeline",
        "lbl_tracks_selection": "Selezione Tracce",
        "lbl_transcript_font": "Carattere trascrizione",
        "lbl_transcription_workspace": "Area di Trascrizione",
        "lbl_words": "parole",
        "msg_analysis_failed": "Analisi fallita.",
        "msg_fast_silence": "Silenzio Rapido",
        "msg_fast_silence_processing_c": "Elaborazione silenzio completata.",
        "msg_no_active_transcription_t": "Nessuna timeline di trascrizione attiva rilevata.",
        "msg_no_silence_segments_detec": "Nessun segmento di silenzio rilevato.",
        "msg_please_import_or_paste_a": "Per favore importa o incolla prima uno script.",
        "msg_restart_lang": "Lingua cambiata. Per favore riavvia BadWords.",
        "msg_success": "Successo",
        "msg_the_transcription_process": "Il processo di trascrizione è terminato.",
        "msg_timeline_assembled_succes": "Timeline assemblata con successo.",
        "msg_title_language_changed": "Lingua Cambiata",
        "msg_warning": "Avviso",
        "opt_segmented_blocks": "Blocchi segmentati",
        "ph_paste_script_here": "Incolla lo script qui...",
        "ph_search": "Cerca...",
        "rad_blue_retake": "Blu: Rifare",
        "rad_eraser_clear": "Gomma: Pulisci",
        "rad_green_typo": "Verde: Refuso",
        "rad_red_cut_filler": "Rosso: Taglio / Riempitivo",
        "tab_appearance": "Aspetto",
        "tab_audio_sync": "Sync Audio",
        "tab_general": "Generale",
        "tool_assembly": "Assemblaggio",
        "tool_filler_words": "Parole Riempitive",
        "tool_main_panel": "Pannello Principale",
        "tool_mark_inaudible": "Segna Inudibile",
        "tool_quit": "Esci",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Analisi Script",
        "tool_settings": "Impostazioni",
        "tool_show_inaudible": "Mostra Inudibile",
        "tool_show_typos": "Mostra Refusi",
        "tool_silence": "Silenzio",
        "tooltip_clear_all_markings": "Cancella tutti i segni",
        "tooltip_dev": "Funzionalità in sviluppo",
        "tt_revert_to_default": "Ripristina predefinito",
        "txt_assembling_timeline": "Assemblaggio timeline...",
        "txt_finishing": "Completamento...",
        "txt_initializing_analysis": "Inizializzazione analisi...",
        "txt_initializing_assembly": "Inizializzazione assemblaggio...",
        "txt_initializing_fast_silence": "Inizializzazione Silenzio Rapido...",
        "txt_save": "Salva",
        "txt_saved": "Salvato",
        "txt_select": "Seleziona...",
        "txt_select_tracks": "Seleziona tracce..."
    },
    'pt': {
        "btn_analyze": "Analisar",
        "btn_analyze_compare": "Analisar (Comparar)",
        "btn_analyze_standalone": "Analisar (Independente)",
        "btn_apply": "Aplicar",
        "btn_assemble": "Montar",
        "btn_clear": "Limpar",
        "btn_close": "Fechar",
        "btn_export_project": "Exportar Projeto",
        "btn_fast_silence_detection": "Detecção Rápida de Silêncio",
        "btn_import_project": "Importar Projeto",
        "btn_import_script": "Importar Script",
        "btn_restart_later": "Reiniciar mais tarde",
        "btn_restart_now": "Reiniciar agora",
        "btn_restore_defaults": "Restaurar Padrões",
        "btn_run_fast_silence": "Executar Silêncio Rápido",
        "btn_save": "Salvar",
        "btn_back_to_transcription": "Voltar para Transcrição",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Adicionar Marcador Personalizado",
        "lbl_cut_silence_directly": "Cortar silêncio diretamente",
        "lbl_detect_and_cut_silence": "Detectar e cortar silêncio",
        "lbl_detect_and_mark_silence": "Detectar e marcar silêncio",
        "lbl_device": "Dispositivo",
        "lbl_display_mode": "Modo de Exibição",
        "lbl_fast_silence_workspace": "Espaço de Silêncio Rápido",
        "lbl_font_size_pt": "Tamanho da fonte (pt)",
        "lbl_initializing": "Inicializando...",
        "lbl_lang": "Idioma",
        "lbl_language": "Idioma",
        "lbl_line_spacing_px": "Espaçamento de linha (px)",
        "lbl_loading": "Carregando...",
        "lbl_mark_filler_words_automat": "Marcar preenchimentos automaticamente",
        "lbl_mark_inaudible_fragments": "Marcar fragmentos inaudíveis",
        "lbl_mark_silence_with_color": "Marcar silêncio com cor",
        "lbl_marking_mode": "Modo de Marcação",
        "lbl_model": "Modelo",
        "lbl_offset_s": "Deslocamento (s)",
        "lbl_padding_s": "Margem (s)",
        "lbl_pinned_favorites": "Favoritos Fixados",
        "lbl_ripple_delete_red_clips": "Excluir clipes vermelhos (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Mostrar erros de digitação detectados",
        "lbl_show_inaudible_fragments": "Mostrar fragmentos inaudíveis",
        "lbl_silence_threshold_db": "Limiar de silêncio (dB)",
        "lbl_snap_max_s": "Ajuste máx (s)",
        "lbl_threshold_db": "Limiar (dB)",
        "lbl_timeline_selection": "Seleção da Timeline",
        "lbl_tracks_selection": "Seleção de Faixas",
        "lbl_transcript_font": "Fonte da transcrição",
        "lbl_transcription_workspace": "Espaço de Transcrição",
        "lbl_words": "palavras",
        "msg_analysis_failed": "A análise falhou.",
        "msg_fast_silence": "Silêncio Rápido",
        "msg_fast_silence_processing_c": "Processamento de silêncio concluído.",
        "msg_no_active_transcription_t": "Nenhuma timeline de transcrição ativa detectada.",
        "msg_no_silence_segments_detec": "Nenhum segmento de silêncio detectado.",
        "msg_please_import_or_paste_a": "Por favor, importe ou cole um script primeiro.",
        "msg_restart_lang": "Idioma alterado. Por favor, reinicie o BadWords.",
        "msg_success": "Sucesso",
        "msg_the_transcription_process": "O processo de transcrição foi concluído.",
        "msg_timeline_assembled_succes": "Timeline montada com sucesso.",
        "msg_title_language_changed": "Idioma Alterado",
        "msg_warning": "Aviso",
        "opt_segmented_blocks": "Blocos segmentados",
        "ph_paste_script_here": "Cole o script aqui...",
        "ph_search": "Pesquisar...",
        "rad_blue_retake": "Azul: Retake",
        "rad_eraser_clear": "Borracha: Limpar",
        "rad_green_typo": "Verde: Erro (Typo)",
        "rad_red_cut_filler": "Vermelho: Cortar / Preenchimento",
        "tab_appearance": "Aparência",
        "tab_audio_sync": "Sincronização",
        "tab_general": "Geral",
        "tool_assembly": "Montagem",
        "tool_filler_words": "Preenchimentos",
        "tool_main_panel": "Painel Principal",
        "tool_mark_inaudible": "Marcar Inaudível",
        "tool_quit": "Sair",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Análise de Script",
        "tool_settings": "Configurações",
        "tool_show_inaudible": "Mostrar Inaudível",
        "tool_show_typos": "Mostrar Erros (Typos)",
        "tool_silence": "Silêncio",
        "tooltip_clear_all_markings": "Limpar todas as marcações",
        "tooltip_dev": "Recurso em desenvolvimento",
        "tt_revert_to_default": "Restaurar para o padrão",
        "txt_assembling_timeline": "Montando timeline...",
        "txt_finishing": "Finalizando...",
        "txt_initializing_analysis": "Inicializando análise...",
        "txt_initializing_assembly": "Inicializando montagem...",
        "txt_initializing_fast_silence": "Inicializando Silêncio Rápido...",
        "txt_save": "Salvar",
        "txt_saved": "Salvo",
        "txt_select": "Selecionar...",
        "txt_select_tracks": "Selecionar faixas..."
    }

,
    'uk': {
        "btn_analyze": "Аналізувати",
        "btn_analyze_compare": "Аналіз (Порівняння)",
        "btn_analyze_standalone": "Аналіз (Автономний)",
        "btn_apply": "Застосувати",
        "btn_assemble": "Змонтувати",
        "btn_clear": "Очистити",
        "btn_close": "Закрити",
        "btn_export_project": "Експорт Проєкту",
        "btn_fast_silence_detection": "Швидке Виявлення Тиші",
        "btn_import_project": "Імпорт Проєкту",
        "btn_import_script": "Імпорт Сценарію",
        "btn_restart_later": "Перезапустити пізніше",
        "btn_restart_now": "Перезапустити зараз",
        "btn_restore_defaults": "Відновити типові",
        "btn_run_fast_silence": "Запуск Швидкої Тиші",
        "btn_save": "Зберегти",
        "btn_back_to_transcription": "Назад до Транскрипції",
        "lbl_font_preview": "Аа Бб Вв",
        "lbl_add_custom_marker": "Додати Власний Маркер",
        "lbl_cut_silence_directly": "Вирізати тишу безпосередньо",
        "lbl_detect_and_cut_silence": "Виявити та вирізати тишу",
        "lbl_detect_and_mark_silence": "Виявити та позначити тишу",
        "lbl_device": "Пристрій",
        "lbl_display_mode": "Режим Відображення",
        "lbl_fast_silence_workspace": "Простір Швидкої Тиші",
        "lbl_font_size_pt": "Розмір шрифту (pt)",
        "lbl_initializing": "Ініціалізація...",
        "lbl_lang": "Мова",
        "lbl_language": "Мова",
        "lbl_line_spacing_px": "Міжрядковий інтервал (px)",
        "lbl_loading": "Завантаження...",
        "lbl_mark_filler_words_automat": "Автоматично позначати паразити",
        "lbl_mark_inaudible_fragments": "Позначати нерозбірливі фрагменти",
        "lbl_mark_silence_with_color": "Позначати тишу кольором",
        "lbl_marking_mode": "Режим Позначення",
        "lbl_model": "Модель",
        "lbl_offset_s": "Зсув (с)",
        "lbl_padding_s": "Відступ (с)",
        "lbl_pinned_favorites": "Закріплені Інструменти",
        "lbl_ripple_delete_red_clips": "Видалити червоні кліпи (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Показати виявлені помилки",
        "lbl_show_inaudible_fragments": "Показати нерозбірливі фрагменти",
        "lbl_silence_threshold_db": "Поріг тиші (dB)",
        "lbl_snap_max_s": "Прилипання макс. (с)",
        "lbl_threshold_db": "Поріг (dB)",
        "lbl_timeline_selection": "Вибір Таймлайну",
        "lbl_tracks_selection": "Вибір Доріжок",
        "lbl_transcript_font": "Шрифт транскрипту",
        "lbl_transcription_workspace": "Простір Транскрипції",
        "lbl_words": "слів",
        "msg_analysis_failed": "Аналіз не вдався.",
        "msg_fast_silence": "Швидка Тиша",
        "msg_fast_silence_processing_c": "Обробка тиші завершена.",
        "msg_no_active_transcription_t": "Не виявлено активного таймлайну.",
        "msg_no_silence_segments_detec": "Сегментів тиші не виявлено.",
        "msg_please_import_or_paste_a": "Будь ласка, спочатку імпортуйте або вставте сценарій.",
        "msg_restart_lang": "Мову змінено. Перезапустіть BadWords.",
        "msg_success": "Успіх",
        "msg_the_transcription_process": "Процес транскрипції завершено.",
        "msg_timeline_assembled_succes": "Таймлайн успішно змонтовано.",
        "msg_title_language_changed": "Мову Змінено",
        "msg_warning": "Попередження",
        "opt_segmented_blocks": "Сегментовані блоки",
        "ph_paste_script_here": "Вставте сценарій сюди...",
        "ph_search": "Пошук...",
        "rad_blue_retake": "Синій: Дубль (Retake)",
        "rad_eraser_clear": "Гумка: Очистити",
        "rad_green_typo": "Зелений: Помилка",
        "rad_red_cut_filler": "Червоний: Вирізати / Сміття",
        "tab_appearance": "Вигляд",
        "tab_audio_sync": "Синхронізація",
        "tab_general": "Загальні",
        "tool_assembly": "Монтаж",
        "tool_filler_words": "Слова-паразити",
        "tool_main_panel": "Головна Панель",
        "tool_mark_inaudible": "Позначити Нерозбірливе",
        "tool_quit": "Вийти",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Аналіз Сценарію",
        "tool_settings": "Налаштування",
        "tool_show_inaudible": "Показати Нерозбірливе",
        "tool_show_typos": "Показати Помилки",
        "tool_silence": "Тиша",
        "tooltip_clear_all_markings": "Очистити всі позначки",
        "tooltip_dev": "Функція в розробці",
        "tt_revert_to_default": "Повернути типові",
        "txt_assembling_timeline": "Монтування таймлайну...",
        "txt_finishing": "Завершення...",
        "txt_initializing_analysis": "Ініціалізація аналізу...",
        "txt_initializing_assembly": "Ініціалізація монтажу...",
        "txt_initializing_fast_silence": "Ініціалізація Швидкої Тиші...",
        "txt_save": "Зберегти",
        "txt_saved": "Збережено",
        "txt_select": "Обрати...",
        "txt_select_tracks": "Обрати доріжки..."
    },
    'nl': {
        "btn_analyze": "Analyseren",
        "btn_analyze_compare": "Analyseren (Vergelijken)",
        "btn_analyze_standalone": "Analyseren (Losstaand)",
        "btn_apply": "Toepassen",
        "btn_assemble": "Monteren",
        "btn_clear": "Wissen",
        "btn_close": "Sluiten",
        "btn_export_project": "Project Exporteren",
        "btn_fast_silence_detection": "Snelle Stiltedetectie",
        "btn_import_project": "Project Importeren",
        "btn_import_script": "Script Importeren",
        "btn_restart_later": "Later opnieuw opstarten",
        "btn_restart_now": "Nu opnieuw opstarten",
        "btn_restore_defaults": "Standaard Herstellen",
        "btn_run_fast_silence": "Snelle Stilte Uitvoeren",
        "btn_save": "Opslaan",
        "btn_back_to_transcription": "Terug naar Transcriptie",
        "lbl_font_preview": "Aa Bb Cc",
        "lbl_add_custom_marker": "Aangepaste Markering Toevoegen",
        "lbl_cut_silence_directly": "Stilte direct knippen",
        "lbl_detect_and_cut_silence": "Stilte detecteren en knippen",
        "lbl_detect_and_mark_silence": "Stilte detecteren en markeren",
        "lbl_device": "Apparaat",
        "lbl_display_mode": "Weergavemodus",
        "lbl_fast_silence_workspace": "Snelle Stilte Werkruimte",
        "lbl_font_size_pt": "Lettergrootte (pt)",
        "lbl_initializing": "Initialiseren...",
        "lbl_lang": "Taal",
        "lbl_language": "Taal",
        "lbl_line_spacing_px": "Regelafstand (px)",
        "lbl_loading": "Laden...",
        "lbl_mark_filler_words_automat": "Opvulwoorden automatisch markeren",
        "lbl_mark_inaudible_fragments": "Onhoorbare fragmenten markeren",
        "lbl_mark_silence_with_color": "Stilte markeren met kleur",
        "lbl_marking_mode": "Markeermodus",
        "lbl_model": "Model",
        "lbl_offset_s": "Offset (s)",
        "lbl_padding_s": "Marge (s)",
        "lbl_pinned_favorites": "Vastgepelde Favorieten",
        "lbl_ripple_delete_red_clips": "Rode clips verwijderen (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Gedetecteerde typfouten tonen",
        "lbl_show_inaudible_fragments": "Onhoorbare fragmenten tonen",
        "lbl_silence_threshold_db": "Stiltedrempel (dB)",
        "lbl_snap_max_s": "Snap max (s)",
        "lbl_threshold_db": "Drempel (dB)",
        "lbl_timeline_selection": "Timeline Selectie",
        "lbl_tracks_selection": "Tracks Selectie",
        "lbl_transcript_font": "Transcript lettertype",
        "lbl_transcription_workspace": "Transcriptie Werkruimte",
        "lbl_words": "woorden",
        "msg_analysis_failed": "Analyse mislukt.",
        "msg_fast_silence": "Snelle Stilte",
        "msg_fast_silence_processing_c": "Stilteverwerking voltooid.",
        "msg_no_active_transcription_t": "Geen actieve transcriptie-timeline gedetecteerd.",
        "msg_no_silence_segments_detec": "Geen stiltesegmenten gedetecteerd.",
        "msg_please_import_or_paste_a": "Importeer of plak eerst een script.",
        "msg_restart_lang": "Taal gewijzigd. Start BadWords opnieuw op.",
        "msg_success": "Succes",
        "msg_the_transcription_process": "Het transcriptieproces is voltooid.",
        "msg_timeline_assembled_succes": "Timeline succesvol gemonteerd.",
        "msg_title_language_changed": "Taal Gewijzigd",
        "msg_warning": "Waarschuwing",
        "opt_segmented_blocks": "Gesegmenteerde blokken",
        "ph_paste_script_here": "Plak script hier...",
        "ph_search": "Zoeken...",
        "rad_blue_retake": "Blauw: Retake",
        "rad_eraser_clear": "Gum: Wissen",
        "rad_green_typo": "Groen: Typfout",
        "rad_red_cut_filler": "Rood: Knippen / Opvulling",
        "tab_appearance": "Uiterlijk",
        "tab_audio_sync": "Audio Sync",
        "tab_general": "Algemeen",
        "tool_assembly": "Montage",
        "tool_filler_words": "Opvulwoorden",
        "tool_main_panel": "Hoofdvenster",
        "tool_mark_inaudible": "Onhoorbaar Markeren",
        "tool_quit": "Afsluiten",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Scriptanalyse",
        "tool_settings": "Instellingen",
        "tool_show_inaudible": "Toon Onhoorbaar",
        "tool_show_typos": "Toon Typfouten",
        "tool_silence": "Stilte",
        "tooltip_clear_all_markings": "Alle markeringen wissen",
        "tooltip_dev": "Functie in ontwikkeling",
        "tt_revert_to_default": "Standaard herstellen",
        "txt_assembling_timeline": "Timeline monteren...",
        "txt_finishing": "Afronden...",
        "txt_initializing_analysis": "Analyse initialiseren...",
        "txt_initializing_assembly": "Montage initialiseren...",
        "txt_initializing_fast_silence": "Snelle Stilte Initialiseren...",
        "txt_save": "Opslaan",
        "txt_saved": "Opgeslagen",
        "txt_select": "Selecteren...",
        "txt_select_tracks": "Tracks selecteren..."
    },
    'ru': {
        "btn_analyze": "Анализ",
        "btn_analyze_compare": "Анализ (Сравнение)",
        "btn_analyze_standalone": "Анализ (Автономный)",
        "btn_apply": "Применить",
        "btn_assemble": "Собрать",
        "btn_clear": "Очистить",
        "btn_close": "Закрыть",
        "btn_export_project": "Экспорт Проекта",
        "btn_fast_silence_detection": "Быстрое Обнаружение Тишины",
        "btn_import_project": "Импорт Проекта",
        "btn_import_script": "Импорт Сценария",
        "btn_restart_later": "Перезапустить позже",
        "btn_restart_now": "Перезапустить сейчас",
        "btn_restore_defaults": "По умолчанию",
        "btn_run_fast_silence": "Запуск Быстрой Тишины",
        "btn_save": "Сохранить",
        "btn_back_to_transcription": "Назад к Транскрипции",
        "lbl_font_preview": "Аа Бб Вв",
        "lbl_add_custom_marker": "Добавить Пользовательский Маркер",
        "lbl_cut_silence_directly": "Вырезать тишину напрямую",
        "lbl_detect_and_cut_silence": "Обнаружить и вырезать тишину",
        "lbl_detect_and_mark_silence": "Обнаружить и пометить тишину",
        "lbl_device": "Устройство",
        "lbl_display_mode": "Режим Отображения",
        "lbl_fast_silence_workspace": "Пространство Быстрой Тишины",
        "lbl_font_size_pt": "Размер шрифта (pt)",
        "lbl_initializing": "Инициализация...",
        "lbl_lang": "Язык",
        "lbl_language": "Язык",
        "lbl_line_spacing_px": "Межстрочный интервал (px)",
        "lbl_loading": "Загрузка...",
        "lbl_mark_filler_words_automat": "Автоматически помечать слова-паразиты",
        "lbl_mark_inaudible_fragments": "Помечать неразборчивые фрагменты",
        "lbl_mark_silence_with_color": "Помечать тишину цветом",
        "lbl_marking_mode": "Режим Пометки",
        "lbl_model": "Модель",
        "lbl_offset_s": "Сдвиг (с)",
        "lbl_padding_s": "Отступ (с)",
        "lbl_pinned_favorites": "Закрепленные Инструменты",
        "lbl_ripple_delete_red_clips": "Удалить красные клипы (<span style='color: #ed4245;'>Ripple Delete</span>)",
        "lbl_show_detected_typos": "Показать обнаруженные опечатки",
        "lbl_show_inaudible_fragments": "Показать неразборчивые фрагменты",
        "lbl_silence_threshold_db": "Порог тишины (dB)",
        "lbl_snap_max_s": "Прилипание макс. (с)",
        "lbl_threshold_db": "Порог (dB)",
        "lbl_timeline_selection": "Выбор Таймлайна",
        "lbl_tracks_selection": "Выбор Дорожек",
        "lbl_transcript_font": "Шрифт транскрипта",
        "lbl_transcription_workspace": "Пространство Транскрипции",
        "lbl_words": "слов",
        "msg_analysis_failed": "Анализ не удался.",
        "msg_fast_silence": "Быстрая Тишина",
        "msg_fast_silence_processing_c": "Обработка тишины завершена.",
        "msg_no_active_transcription_t": "Активный таймлайн не обнаружен.",
        "msg_no_silence_segments_detec": "Сегменты тишины не обнаружены.",
        "msg_please_import_or_paste_a": "Пожалуйста, сначала импортируйте или вставьте сценарий.",
        "msg_restart_lang": "Язык изменен. Перезапустите BadWords.",
        "msg_success": "Успех",
        "msg_the_transcription_process": "Процесс транскрипции завершен.",
        "msg_timeline_assembled_succes": "Таймлайн успешно собран.",
        "msg_title_language_changed": "Язык Изменен",
        "msg_warning": "Предупреждение",
        "opt_segmented_blocks": "Сегментированные блоки",
        "ph_paste_script_here": "Вставьте сценарий сюда...",
        "ph_search": "Поиск...",
        "rad_blue_retake": "Синий: Дубль (Retake)",
        "rad_eraser_clear": "Ластик: Очистить",
        "rad_green_typo": "Зеленый: Опечатка",
        "rad_red_cut_filler": "Красный: Вырезать / Мусор",
        "tab_appearance": "Внешний вид",
        "tab_audio_sync": "Синхронизация",
        "tab_general": "Общие",
        "tool_assembly": "Сборка",
        "tool_filler_words": "Слова-паразиты",
        "tool_main_panel": "Главная Панель",
        "tool_mark_inaudible": "Пометить Неразборчивое",
        "tool_quit": "Выход",
        "tool_ripple_delete": "Ripple Delete",
        "tool_script_analysis": "Анализ Сценария",
        "tool_settings": "Настройки",
        "tool_show_inaudible": "Показать Неразборчивое",
        "tool_show_typos": "Показать Опечатки",
        "tool_silence": "Тишина",
        "tooltip_clear_all_markings": "Очистить все пометки",
        "tooltip_dev": "Функция в разработке",
        "tt_revert_to_default": "Вернуть по умолчанию",
        "txt_assembling_timeline": "Сборка таймлайна...",
        "txt_finishing": "Завершение...",
        "txt_initializing_analysis": "Инициализация анализа...",
        "txt_initializing_assembly": "Инициализация сборки...",
        "txt_initializing_fast_silence": "Инициализация Быстрой Тишины...",
        "txt_save": "Сохранить",
        "txt_saved": "Сохранено",
        "txt_select": "Выбрать...",
        "txt_select_tracks": "Выбрать дорожки..."
    }
}

def get_trans(key, lang_code="en"):
    """
    Safely retrieves translation for a given key.
    Falls back to English if key/language missing.
    """
    lang_dict = TRANS.get(lang_code, TRANS["en"])
    return lang_dict.get(key, TRANS["en"].get(key, f"[{key}]"))