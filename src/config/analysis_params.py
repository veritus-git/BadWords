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
DEFAULT_BAD_WORDS = [
    "yyy", "eee", "aaa", "umm", "uh", "ah", "mhm",
    "uhm", "hmm", "hm", "mm", "mmm",
    "eh", "ehm", "uhh", "ahh", 
    "yy", "ee", "aa", 
    "ummm", "uhhh", "ahhh", "ehhh", "hmmm", "mmmm", 
    "mhmm", "yhm", "yhy"
]
SIMILARITY_THRESHOLD = 0.45

# Default filler/hesitation initial prompt for Whisper transcription
DEFAULT_WHISPER_PROMPT = "yyy, eee, uuu, yhm, yyyy, eeee, aaaa, mhm, aha, umm, uh, ah"

# GOLDEN Verbatim Initial Prompt — DO NOT CHANGE.
# This is the exact prompt from the validated src_old that forces Whisper into
# raw acoustic capture mode: stutters, withdrawals, and broken words are transcribed
# as-is instead of being smoothed into grammatical sentences.
# Used as the default for ai_initial_prompt.
GOLDEN_INITIAL_PROMPT = (
    "Mmm, uh... t-t-ta, ta, ta... "
    "na na... na na... o... ok, ok, ok. "
    "Da, da... d-d-da... mhm, mhm."
)

# ==========================================
# PER-LANGUAGE VERBATIM INITIAL PROMPTS
# ==========================================
# Each prompt is tailored to its language's native hesitation/filler phonemes.
# This prevents Whisper from hallucinating foreign filler sounds when operating
# in a specific language mode, and forces raw acoustic capture (stutters, withdrawals,
# broken words) instead of grammatically smoothed output.
# Follows the same philosophy as GOLDEN_INITIAL_PROMPT.
# Key: Whisper ISO language code. "Auto" → falls back to GOLDEN_INITIAL_PROMPT.
WHISPER_PROMPTS = {
    # Afrikaans — generated native fillers
    "af": "uh, uhm... uh-uh-uh, uh, uh... uhm uhm... uhm uhm... uh... uh, uh, uh... mhm.",
    # Amharic — generated native fillers
    "am": "እህ, እም... እህ-እህ-እህ, እህ, እህ... እም እም... እም እም... እህ... እህ, እህ, እህ... mhm.",
    # Arabic
    "ar": "يعني،, آه،... يعني،-يعني،-يعني،, يعني،, يعني،... آه، آه،... آه، آه،... يعني،... يعني،, يعني،, يعني،... mhm.",
    # Assamese — generated native fillers
    "as": "উম, এহ... উম-উম-উম, উম, উম... এহ এহ... এহ এহ... উম... উম, উম, উম... mhm.",
    # Azerbaijani — generated native fillers
    "az": "ıı, eee... ıı-ıı-ıı, ıı, ıı... eee eee... eee eee... ıı... ıı, ıı, ıı... mhm.",
    # Bashkir — generated native fillers
    "ba": "эээ, ммм... эээ-эээ-эээ, эээ, эээ... ммм ммм... ммм ммм... эээ... эээ, эээ, эээ... mhm.",
    # Belarusian — generated native fillers
    "be": "эээ, ммм... эээ-эээ-эээ, эээ, эээ... ммм ммм... ммм ммм... эээ... эээ, эээ, эээ... mhm.",
    # Bulgarian — generated native fillers
    "bg": "ааа, ъъъ... ааа-ааа-ааа, ааа, ааа... ъъъ ъъъ... ъъъ ъъъ... ааа... ааа, ааа, ааа... mhm.",
    # Bengali — generated native fillers
    "bn": "উম, এহ... উম-উম-উম, উম, উম... এহ এহ... এহ এহ... উম... উম, উম, উম... mhm.",
    # Tibetan — generated native fillers
    "bo": "ཨ, མ... ཨ-ཨ-ཨ, ཨ, ཨ... མ མ... མ མ... ཨ... ཨ, ཨ, ཨ... mhm.",
    # Breton — generated native fillers
    "br": "euh, bah... euh-euh-euh, euh, euh... bah bah... bah bah... euh... euh, euh, euh... mhm.",
    # Bosnian — generated native fillers
    "bs": "ehm, pa... ehm-ehm-ehm, ehm, ehm... pa pa... pa pa... ehm... ehm, ehm, ehm... mhm.",
    # Catalan — generated native fillers
    "ca": "eh, hmm... eh-eh-eh, eh, eh... hmm hmm... hmm hmm... eh... eh, eh, eh... mhm.",
    # Czech
    "cs": "ehm, no... ehm-ehm-ehm, ehm, ehm... no no... no no... ehm... ehm, ehm, ehm... mhm.",
    # Welsh — generated native fillers
    "cy": "ym, ych... ym-ym-ym, ym, ym... ych ych... ych ych... ym... ym, ym, ym... mhm.",
    # Danish
    "da": "øh, altså... øh-øh-øh, øh, øh... altså altså... altså altså... øh... øh, øh, øh... mhm.",
    # German
    "de": "Ähm, äh... d-d-das, das, das... a-also... also, es ist... es ist... j-j-ja, ja, ja. N-n-nein... mhm.",
    # Greek
    "el": "εμ, δηλαδή... εμ-εμ-εμ, εμ, εμ... δηλαδή δηλαδή... δηλαδή δηλαδή... εμ... εμ, εμ, εμ... mhm.",
    # English
    "en": "Umm, yyy... th-the, the, the... I mean... I mean, it is... it is just... wha... what... o-o-ok. So, so, so... mhm.",
    # Spanish
    "es": "Eh, mmm... e-e-el, el, el... o sea... o sea, es que... es que... b-b-bueno, bueno, bueno. S-s-si... mhm.",
    # Estonian — generated native fillers
    "et": "ee, mm... ee-ee-ee, ee, ee... mm mm... mm mm... ee... ee, ee, ee... mhm.",
    # Basque — generated native fillers
    "eu": "eh, ba... eh-eh-eh, eh, eh... ba ba... ba ba... eh... eh, eh, eh... mhm.",
    # Persian — generated native fillers
    "fa": "um, eh... um-um-um, um, um... eh eh... eh eh... um... um, um, um... mhm.",
    # Finnish
    "fi": "öö, tota... öö-öö-öö, öö, öö... tota tota... tota tota... öö... öö, öö, öö... mhm.",
    # Faroese — generated native fillers
    "fo": "øh, hmm... øh-øh-øh, øh, øh... hmm hmm... hmm hmm... øh... øh, øh, øh... mhm.",
    # French
    "fr": "Euh, mmm... l-l-le, le, le... c'est... c'est-à-dire... c'est-à-dire, c'est... c'est... o-o-oui, oui, oui. N-n-non... mhm.",
    # Galician — generated native fillers
    "gl": "eh, hmm... eh-eh-eh, eh, eh... hmm hmm... hmm hmm... eh... eh, eh, eh... mhm.",
    # Gujarati — generated native fillers
    "gu": "ઉમ, એહ... ઉમ-ઉમ-ઉમ, ઉમ, ઉમ... એહ એહ... એહ એહ... ઉમ... ઉમ, ઉમ, ઉમ... mhm.",
    # Hausa — generated native fillers
    "ha": "uhm, toh... uhm-uhm-uhm, uhm, uhm... toh toh... toh toh... uhm... uhm, uhm, uhm... mhm.",
    # Hawaiian — generated native fillers
    "haw": "ʻō, um... ʻō-ʻō-ʻō, ʻō, ʻō... um um... um um... ʻō... ʻō, ʻō, ʻō... mhm.",
    # Hebrew
    "he": "אמ, כלומר... אמ-אמ-אמ, אמ, אמ... כלומר כלומר... כלומר כלומר... אמ... אמ, אמ, אמ... mhm.",
    # Hindi
    "hi": "मतलब, ह... मतलब-मतलब-मतलब, मतलब, मतलब... ह ह... ह ह... मतलब... मतलब, मतलब, मतलब... mhm.",
    # Croatian — generated native fillers
    "hr": "ehm, pa... ehm-ehm-ehm, ehm, ehm... pa pa... pa pa... ehm... ehm, ehm, ehm... mhm.",
    # Haitian Creole — generated native fillers
    "ht": "en, um... en-en-en, en, en... um um... um um... en... en, en, en... mhm.",
    # Hungarian
    "hu": "hm, tehát... hm-hm-hm, hm, hm... tehát tehát... tehát tehát... hm... hm, hm, hm... mhm.",
    # Armenian — generated native fillers
    "hy": "ըըը, մմմ... ըըը-ըըը-ըըը, ըըը, ըըը... մմմ մմմ... մմմ մմմ... ըըը... ըըը, ըըը, ըըը... mhm.",
    # Indonesian — generated native fillers
    "id": "anu, em... anu-anu-anu, anu, anu... em em... em em... anu... anu, anu, anu... mhm.",
    # Icelandic — generated native fillers
    "is": "öh, hmm... öh-öh-öh, öh, öh... hmm hmm... hmm hmm... öh... öh, öh, öh... mhm.",
    # Italian
    "it": "Ehm, mmm... i-i-il, il, il... c-cioè... cioè, è che... è che... s-s-si, si, si. N-n-no... mhm.",
    # Japanese
    "ja": "えーと, あの... えーと-えーと-えーと, えーと, えーと... あの あの... あの あの... えーと... えーと, えーと, えーと... mhm.",
    # Javanese — generated native fillers
    "jw": "anu, em... anu-anu-anu, anu, anu... em em... em em... anu... anu, anu, anu... mhm.",
    # Georgian — generated native fillers
    "ka": "აა, მმ... აა-აა-აა, აა, აა... მმ მმ... მმ მმ... აა... აა, აა, აა... mhm.",
    # Kazakh — generated native fillers
    "kk": "эээ, ммм... эээ-эээ-эээ, эээ, эээ... ммм ммм... ммм ммм... эээ... эээ, эээ, эээ... mhm.",
    # Khmer — generated native fillers
    "km": "អ, អ... អ-អ-អ, អ, អ... អ អ... អ អ... អ... អ, អ, អ... mhm.",
    # Kannada — generated native fillers
    "kn": "ಉಮ, ಎಹ... ಉಮ-ಉಮ-ಉಮ, ಉಮ, ಉಮ... ಎಹ ಎಹ... ಎಹ ಎಹ... ಉಮ... ಉಮ, ಉಮ, ಉಮ... mhm.",
    # Korean
    "ko": "음, 어... 음-음-음, 음, 음... 어 어... 어 어... 음... 음, 음, 음... mhm.",
    # Latin — generated native fillers
    "la": "ehem, um... ehem-ehem-ehem, ehem, ehem... um um... um um... ehem... ehem, ehem, ehem... mhm.",
    # Luxembourgish — generated native fillers
    "lb": "ehm, majo... ehm-ehm-ehm, ehm, ehm... majo majo... majo majo... ehm... ehm, ehm, ehm... mhm.",
    # Lingala — generated native fillers
    "ln": "euh, um... euh-euh-euh, euh, euh... um um... um um... euh... euh, euh, euh... mhm.",
    # Lao — generated native fillers
    "lo": "ເອ, ອ... ເອ-ເອ-ເອ, ເອ, ເອ... ອ ອ... ອ ອ... ເອ... ເອ, ເອ, ເອ... mhm.",
    # Lithuanian — generated native fillers
    "lt": "ėė, mm... ėė-ėė-ėė, ėė, ėė... mm mm... mm mm... ėė... ėė, ėė, ėė... mhm.",
    # Latvian — generated native fillers
    "lv": "ēē, mm... ēē-ēē-ēē, ēē, ēē... mm mm... mm mm... ēē... ēē, ēē, ēē... mhm.",
    # Malagasy — generated native fillers
    "mg": "euh, um... euh-euh-euh, euh, euh... um um... um um... euh... euh, euh, euh... mhm.",
    # Maori — generated native fillers
    "mi": "ā, um... ā-ā-ā, ā, ā... um um... um um... ā... ā, ā, ā... mhm.",
    # Macedonian — generated native fillers
    "mk": "ааа, еее... ааа-ааа-ааа, ааа, ааа... еее еее... еее еее... ааа... ааа, ааа, ааа... mhm.",
    # Malayalam — generated native fillers
    "ml": "ഉ, ഏഹ... ഉ-ഉ-ഉ, ഉ, ഉ... ഏഹ ഏഹ... ഏഹ ഏഹ... ഉ... ഉ, ഉ, ഉ... mhm.",
    # Mongolian — generated native fillers
    "mn": "ээ, мм... ээ-ээ-ээ, ээ, ээ... мм мм... мм мм... ээ... ээ, ээ, ээ... mhm.",
    # Marathi — generated native fillers
    "mr": "उम, एह... उम-उम-उम, उम, उम... एह एह... एह एह... उम... उम, उम, उम... mhm.",
    # Malay — generated native fillers
    "ms": "anu, em... anu-anu-anu, anu, anu... em em... em em... anu... anu, anu, anu... mhm.",
    # Maltese — generated native fillers
    "mt": "ehm, mela... ehm-ehm-ehm, ehm, ehm... mela mela... mela mela... ehm... ehm, ehm, ehm... mhm.",
    # Myanmar — generated native fillers
    "my": "အင, အ... အင-အင-အင, အင, အင... အ အ... အ အ... အင... အင, အင, အင... mhm.",
    # Nepali — generated native fillers
    "ne": "उम, एह... उम-उम-उम, उम, उम... एह एह... एह एह... उम... उम, उम, उम... mhm.",
    # Dutch
    "nl": "Ehm, mmm... d-d-de, de, de... i-ik bedoel... ik bedoel, het is... het is... j-j-ja, ja, ja. N-n-nee... mhm.",
    # Norwegian Nynorsk — generated native fillers
    "nn": "øhm, liksom... øhm-øhm-øhm, øhm, øhm... liksom liksom... liksom liksom... øhm... øhm, øhm, øhm... mhm.",
    # Norwegian
    "no": "øhm, eh... øhm-øhm-øhm, øhm, øhm... eh eh... eh eh... øhm... øhm, øhm, øhm... mhm.",
    # Occitan — generated native fillers
    "oc": "euh, ben... euh-euh-euh, euh, euh... ben ben... ben ben... euh... euh, euh, euh... mhm.",
    # Punjabi — generated native fillers
    "pa": "ਉਮ, ਏਹ... ਉਮ-ਉਮ-ਉਮ, ਉਮ, ਉਮ... ਏਹ ਏਹ... ਏਹ ਏਹ... ਉਮ... ਉਮ, ਉਮ, ਉਮ... mhm.",
    # Polish
    "pl": "Yyy, eee... t-t-to, to, to... z-znaczy... znaczy, to jest... to jest... ta... tak, tak, tak. N-n-nie... mhm.",
    # Pashto — generated native fillers
    "ps": "امم, اې... امم-امم-امم, امم, امم... اې اې... اې اې... امم... امم, امم, امم... mhm.",
    # Portuguese
    "pt": "É, mmm... o-o-o, o, o... q-quer dizer... quer dizer, é que... é que... s-s-sim, sim, sim. N-n-não... mhm.",
    # Romanian
    "ro": "ăă, deci... ăă-ăă-ăă, ăă, ăă... deci deci... deci deci... ăă... ăă, ăă, ăă... mhm.",
    # Russian
    "ru": "Эм, ммм... э-э-это, это, это... з-значит... значит, это... это... д-д-да, да, да. Н-н-нет... угу.",
    # Sanskrit — generated native fillers
    "sa": "उम, एह... उम-उम-उम, उम, उम... एह एह... एह एह... उम... उम, उम, उम... mhm.",
    # Sindhi — generated native fillers
    "sd": "امم, اې... امم-امم-امم, امم, امم... اې اې... اې اې... امم... امم, امم, امم... mhm.",
    # Sinhala — generated native fillers
    "si": "උම, එහ... උම-උම-උම, උම, උම... එහ එහ... එහ එහ... උම... උම, උම, උම... mhm.",
    # Slovak
    "sk": "ehm, no... ehm-ehm-ehm, ehm, ehm... no no... no no... ehm... ehm, ehm, ehm... mhm.",
    # Slovenian — generated native fillers
    "sl": "um, eh... um-um-um, um, um... eh eh... eh eh... um... um, um, um... mhm.",
    # Shona — generated native fillers
    "sn": "ehm, um... ehm-ehm-ehm, ehm, ehm... um um... um um... ehm... ehm, ehm, ehm... mhm.",
    # Somali — generated native fillers
    "so": "ee, um... ee-ee-ee, ee, ee... um um... um um... ee... ee, ee, ee... mhm.",
    # Albanian — generated native fillers
    "sq": "ëëë, hmm... ëëë-ëëë-ëëë, ëëë, ëëë... hmm hmm... hmm hmm... ëëë... ëëë, ëëë, ëëë... mhm.",
    # Serbian — generated native fillers
    "sr": "ehm, pa... ehm-ehm-ehm, ehm, ehm... pa pa... pa pa... ehm... ehm, ehm, ehm... mhm.",
    # Sundanese — generated native fillers
    "su": "euh, em... euh-euh-euh, euh, euh... em em... em em... euh... euh, euh, euh... mhm.",
    # Swedish
    "sv": "öh, eh... öh-öh-öh, öh, öh... eh eh... eh eh... öh... öh, öh, öh... mhm.",
    # Swahili — generated native fillers
    "sw": "eh, um... eh-eh-eh, eh, eh... um um... um um... eh... eh, eh, eh... mhm.",
    # Tamil — generated native fillers
    "ta": "உம, ஏஹ... உம-உம-உம, உம, உம... ஏஹ ஏஹ... ஏஹ ஏஹ... உம... உம, உம, உம... mhm.",
    # Telugu — generated native fillers
    "te": "ఉమ, ఏహ... ఉమ-ఉమ-ఉమ, ఉమ, ఉమ... ఏహ ఏహ... ఏహ ఏహ... ఉమ... ఉమ, ఉమ, ఉమ... mhm.",
    # Tajik — generated native fillers
    "tg": "эээ, ммм... эээ-эээ-эээ, эээ, эээ... ммм ммм... ммм ммм... эээ... эээ, эээ, эээ... mhm.",
    # Thai — generated native fillers
    "th": "เอ้อ, อืม... เอ้อ-เอ้อ-เอ้อ, เอ้อ, เอ้อ... อืม อืม... อืม อืม... เอ้อ... เอ้อ, เอ้อ, เอ้อ... mhm.",
    # Turkmen — generated native fillers
    "tk": "eee, mmm... eee-eee-eee, eee, eee... mmm mmm... mmm mmm... eee... eee, eee, eee... mhm.",
    # Tagalog — generated native fillers
    "tl": "ano, um... ano-ano-ano, ano, ano... um um... um um... ano... ano, ano, ano... mhm.",
    # Turkish
    "tr": "şey, yani... şey-şey-şey, şey, şey... yani yani... yani yani... şey... şey, şey, şey... mhm.",
    # Tatar — generated native fillers
    "tt": "эээ, ммм... эээ-эээ-эээ, эээ, эээ... ммм ммм... ммм ммм... эээ... эээ, эээ, эээ... mhm.",
    # Ukrainian
    "uk": "Еее, ммм... ц-ц-це, це, це... з-значить... значить, це... це... т-т-так, так, так. Н-н-ні... угу.",
    # Urdu — generated native fillers
    "ur": "اُم،, اے... اُم،-اُم،-اُم،, اُم،, اُم،... اے اے... اے اے... اُم،... اُم،, اُم،, اُم،... mhm.",
    # Uzbek — generated native fillers
    "uz": "eee, mmm... eee-eee-eee, eee, eee... mmm mmm... mmm mmm... eee... eee, eee, eee... mhm.",
    # Vietnamese — generated native fillers
    "vi": "ờ, ừm... ờ-ờ-ờ, ờ, ờ... ừm ừm... ừm ừm... ờ... ờ, ờ, ờ... mhm.",
    # Yiddish — generated native fillers
    "yi": "אהם, עה... אהם-אהם-אהם, אהם, אהם... עה עה... עה עה... אהם... אהם, אהם, אהם... mhm.",
    # Yoruba — generated native fillers
    "yo": "ẹn, um... ẹn-ẹn-ẹn, ẹn, ẹn... um um... um um... ẹn... ẹn, ẹn, ẹn... mhm.",
    # Chinese
    "zh": "那个, 就是... 那个-那个-那个, 那个, 那个... 就是 就是... 就是 就是... 那个... 那个, 那个, 那个... mhm.",
    # Cantonese — generated native fillers
    "yue": "嗰個, 呢... 嗰個-嗰個-嗰個, 嗰個, 嗰個... 呢 呢... 呢 呢... 嗰個... 嗰個, 嗰個, 嗰個... mhm.",
}

def get_whisper_prompt_for_lang(lang, user_custom_prompt=None):
    """
    Returns the appropriate Whisper initial prompt for a given transcription language.

    Priority:
      1. User's custom prompt (ai_initial_prompt from settings) — if set and non-empty.
      2. Per-language prompt from WHISPER_PROMPTS — if lang is a known ISO code.
      3. GOLDEN_INITIAL_PROMPT — universal English-based fallback (for Auto or unknown langs).

    Args:
        lang: Whisper ISO language code (e.g. 'pl', 'en', 'de') or None/'Auto' for auto-detect.
        user_custom_prompt: The user's custom ai_initial_prompt value from settings.

    Returns:
        str: The resolved initial prompt string.
    """
    # 1. User has set a non-empty custom prompt — always respect it
    if user_custom_prompt and user_custom_prompt.strip():
        return user_custom_prompt.strip()

    # 2. Specific language selected — look up per-language prompt
    if lang and lang not in (None, "Auto", "auto", "None", ""):
        lang_code = str(lang).lower().strip()
        if lang_code in WHISPER_PROMPTS:
            return WHISPER_PROMPTS[lang_code]

    # 3. Auto-detect or unknown language — use the universal GOLDEN baseline
    return GOLDEN_INITIAL_PROMPT

