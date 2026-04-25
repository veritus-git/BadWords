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
TRANS = {'en': {}}

def get_trans(key, lang_code="en"):
    """
    Safely retrieves translation for a given key.
    Falls back to English if key/language missing.
    """
    lang_dict = TRANS.get(lang_code, TRANS["en"])
    return lang_dict.get(key, TRANS["en"].get(key, f"[{key}]"))