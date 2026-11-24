#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: palette.py
ROLE: Configuration
DESCRIPTION:
Application color palettes and themes.
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
    "PROGRESS_HEIGHT": 8,
    "PROGRESS_TRACK_COLOR": "#2b2b2b",
    "PROGRESS_FILL_COLOR": "#23a559",
    "STATUS_TEXT_COLOR": "#eeeeee"
}

# Module-level defaults populated right away
for _k, _v in DARK_PALETTE.items():
    globals()[_k] = _v


def build_dark_palette():
    """
    Constructs a complete dark QPalette immune to host OS Light Mode themes
    (Windows 11, Linux KDE/Breeze/GTK, macOS) across Active, Inactive, and Disabled states.
    """
    from PySide6.QtGui import QPalette, QColor

    pal = QPalette()

    c_win = QColor(BG_COLOR)          # #1c1c1c
    c_base = QColor("#181818")
    c_alt_base = QColor("#222222")
    c_btn = QColor(SIDEBAR_BG)        # #262626
    c_text = QColor(FG_COLOR)         # #d9d9d9
    c_bright = QColor("#ffffff")
    c_muted = QColor(NOTE_COL)        # #808080
    c_disabled_fg = QColor("#5c5c5c")
    c_disabled_bg = QColor("#161616")
    c_tooltip_bg = QColor("#1e1e1e")
    c_tooltip_fg = QColor("#d4d4d4")
    c_highlight = QColor(BTN_BG)      # #23a559
    c_link = QColor("#39d377")
    c_placeholder = QColor("#707070")

    for grp in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        pal.setColor(grp, QPalette.ColorRole.Window, c_win)
        pal.setColor(grp, QPalette.ColorRole.WindowText, c_text)
        pal.setColor(grp, QPalette.ColorRole.Base, c_base)
        pal.setColor(grp, QPalette.ColorRole.AlternateBase, c_alt_base)
        pal.setColor(grp, QPalette.ColorRole.ToolTipBase, c_tooltip_bg)
        pal.setColor(grp, QPalette.ColorRole.ToolTipText, c_tooltip_fg)
        pal.setColor(grp, QPalette.ColorRole.Text, c_text)
        pal.setColor(grp, QPalette.ColorRole.Button, c_btn)
        pal.setColor(grp, QPalette.ColorRole.ButtonText, c_text)
        pal.setColor(grp, QPalette.ColorRole.BrightText, c_bright)
        pal.setColor(grp, QPalette.ColorRole.Link, c_link)
        pal.setColor(grp, QPalette.ColorRole.LinkVisited, c_link)
        pal.setColor(grp, QPalette.ColorRole.Highlight, c_highlight)
        pal.setColor(grp, QPalette.ColorRole.HighlightedText, c_bright)
        if hasattr(QPalette.ColorRole, "PlaceholderText"):
            pal.setColor(grp, QPalette.ColorRole.PlaceholderText, c_placeholder)

    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, c_win)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, c_disabled_fg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, c_disabled_bg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.AlternateBase, c_disabled_bg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, c_disabled_fg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, c_disabled_bg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, c_disabled_fg)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#2a2a2a"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, c_muted)

    # Borders/bevels for Fusion widgets (menus, separators, inputs)
    pal.setColor(QPalette.ColorRole.Light, QColor("#3a3a3a"))
    pal.setColor(QPalette.ColorRole.Midlight, QColor("#2c2c2c"))
    pal.setColor(QPalette.ColorRole.Dark, QColor("#121212"))
    pal.setColor(QPalette.ColorRole.Mid, QColor("#242424"))
    pal.setColor(QPalette.ColorRole.Shadow, QColor("#0c0c0c"))
    return pal


def apply_dark_app_theme(app) -> None:
    """
    Enforces cross-platform Fusion widget style, complete dark QPalette, and Qt Dark colorScheme
    on Windows, Linux (KDE/GTK), and macOS so host Light Mode themes never bleed into BadWords.
    # INVARIANT: Fusion + build_dark_palette() protects standard menus, popups, and custom painters
    # from OS Light Mode black-on-dark or white-menu leaks across Windows, Linux, and macOS.
    """
    if app is None:
        return
    try:
        app.setStyle("Fusion")
    except Exception:
        pass
    try:
        app.setPalette(build_dark_palette())
    except Exception:
        pass
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "setColorScheme") and hasattr(Qt, "ColorScheme"):
            hints.setColorScheme(Qt.ColorScheme.Dark)
    except Exception:
        pass

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


def scrollbar_qss(size=8, bg=None, fg=None, active=None):
    from .app_constants import S
    w = S(size)
    r = S(size // 2)
    s_bg = bg or globals().get("SCROLL_BG", "#2b2b2b")
    s_fg = fg or globals().get("SCROLL_FG", "#555555")
    s_active = active or globals().get("SCROLL_ACTIVE", "#777777")
    return f"""
        /* Vertical Scrollbar */
        QScrollBar:vertical {{
            background: {s_bg};
            width: {w}px;
            border: none;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {s_fg};
            border-radius: {r}px;
            min-height: {S(16)}px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {s_active};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        /* Horizontal Scrollbar */
        QScrollBar:horizontal {{
            background: {s_bg};
            height: {w}px;
            border: none;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {s_fg};
            border-radius: {r}px;
            min-width: {S(16)}px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {s_active};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        /* Corner junction */
        QScrollBar::corner {{
            background: transparent;
        }}
    """


