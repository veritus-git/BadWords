#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: i18n/__loader__.py
ROLE: Module
DESCRIPTION:
Lazy loads JSON translations and provides get_trans() backward compatibility.
"""

import os
import json

SUPPORTED_LANGS = {
    'en': 'English', 'pl': 'Polski', 'de': 'Deutsch', 'es': 'Español',
    'fr': 'Français', 'it': 'Italiano', 'pt': 'Português', 'nl': 'Nederlands',
    'uk': 'Українська', 'ru': 'Русский'
}

TRANS = {}

def load_translations(lang_code):
    if lang_code in TRANS:
        return
    json_path = os.path.join(os.path.dirname(__file__), f"{lang_code}.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            TRANS[lang_code] = json.load(f)
    else:
        TRANS[lang_code] = {}

def get_trans(key, lang_code="en"):
    if lang_code not in TRANS:
        load_translations(lang_code)
    
    if key in TRANS.get(lang_code, {}):
        return TRANS[lang_code][key]
    
    if "en" not in TRANS:
        load_translations("en")
        
    return TRANS.get("en", {}).get(key, key)

# Pre-load english as fallback
load_translations("en")
