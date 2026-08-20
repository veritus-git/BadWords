#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: config.py
ROLE: Data Layer / Configuration
DESCRIPTION:
Stores constants, default settings, color palette,
"""

import platform

# ==========================================
# SUPPORTED LANGUAGES (WHISPER)
# ==========================================
# Languages that naturally read from Right to Left
RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'}

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

