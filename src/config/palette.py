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

# Official DaVinci Resolve marker colors
RESOLVE_COLORS = [
    "Orange", "Apricot", "Yellow", "Lime", "Green", "Olive",
    "Teal", "Navy", "Blue", "Purple", "Violet",
    "Pink", "Tan", "Beige", "Brown", "Chocolate",
]

# Colors blocked from custom markers (reserved for silence/inaudible/system markers)
RESOLVE_COLORS_BLOCKED = {"Olive", "Violet", "Chocolate", "Navy", "Tan", "Green", "Blue"}

# HEX codes for DaVinci Resolve marker colors
RESOLVE_COLORS_HEX = {
    "Violet":    "#ed4245",
    "Navy":      "#2980b9",
    "Olive":     "#27ae60",
    "Orange":    "#eb6e00",
    "Apricot":   "#ffa833",
    "Yellow":    "#e2a91c",
    "Lime":      "#9fc615",
    "Teal":      "#009899",
    "Purple":    "#9973a0",
    "Pink":      "#e98cb5",
    "Beige":     "#c6a077",
    "Brown":     "#996600",
    "Green":     "#448f64",
    "Blue":      "#4376a1",
    "Tan":       "#D2B48C",
    "Chocolate": "#7B3F00",
}


# ==========================================
# COLOR PALETTE
# ==========================================

DARK_PALETTE = {
    "BG_COLOR": "#1c1c1c",
    "SIDEBAR_BG": "#262626",
    "INPUT_BG": "#333333",
    "INPUT_FG": "#ffffff",
    "FG_COLOR": "#d9d9d9",
    "NOTE_COL": "#808080",
    "SEPARATOR_COL": "#404040",
    "FOOTER_COLOR": "#1c1c1c",
    "DISCLAIMER_FG": "#555555",
    "SCROLL_BG": "#2b2b2b",
    "SCROLL_FG": "#555555",
    "SCROLL_ACTIVE": "#777777",
    "MENU_BG": "#2b2b2b",
    "MENU_FG": "#ffffff",
    "GEAR_COLOR": "#a0a0a0",
    "BTN_BG": "#23a559",
    "BTN_FG": "#ffffff",
    "BTN_ACTIVE": "#1e8f4c",
    "BTN_GHOST_BG": "#404040",
    "BTN_GHOST_ACTIVE": "#505050",
    "CANCEL_BG": "#b33a3a",
    "CANCEL_ACTIVE": "#8f2e2e",
    "CHECKBOX_BG": "white",
    "PROGRESS_HEIGHT": 24,
    "PROGRESS_TRACK_COLOR": "#333333",
    "PROGRESS_FILL_COLOR": "#23a559",
    "STATUS_TEXT_COLOR": "#eeeeee"
}

# Module-level defaults populated right away
for _k, _v in DARK_PALETTE.items():
    globals()[_k] = _v

# ── Title Bar (CSD) ────────────────────────────────────────────────────────
COLOR_TITLEBAR_BG    = "#191919"   # default title-bar background
COLOR_TITLEBAR_HOVER = "#2b2b2b"   # button hover (non-close)

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

