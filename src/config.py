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

SUPPORTED_LANGS = {'en': 'English'}
TRANS = {
    'en': {
        "btn_analyze": "Analyze",
        "btn_analyze_compare": "Analyze & Compare",
        "btn_analyze_standalone": "Analyze Standalone",
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
        "lbl_ripple_delete_red_clips": "Ripple delete red clips",
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
    }
}

def get_trans(key, lang_code="en"):
    """
    Safely retrieves translation for a given key.
    Falls back to English if key/language missing.
    """
    lang_dict = TRANS.get(lang_code, TRANS["en"])
    return lang_dict.get(key, TRANS["en"].get(key, f"[{key}]"))