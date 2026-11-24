#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: settings_widgets.py
ROLE: GUI Helper Widgets & Search Engine for SettingsDialog
DESCRIPTION:
Elevated card containers, flash-highlightable setting rows, custom vector search input,
Brave-style ranked multi-language (+EN) search matcher with green HTML highlights,
support screenshot drop/paste gallery, and full-size screenshot preview lightbox.
"""

import html
import os
import tempfile
import unicodedata

from PySide6.QtCore import (
    Qt, QSize, Signal, QVariantAnimation, QEasingCurve, QRect, QPoint, QTimer
)
from PySide6.QtGui import (
    QColor, QPainter, QPixmap, QImage, QKeySequence, QFontMetrics
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSizePolicy, QApplication, QDialog
)

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import get_svg_icon, _center_on_screen


# ── Palette Constants (Native BadWords #1c1c1c Canvas + Elevated #242424 Cards) ─
SETTINGS_VIEWPORT_BG = "#1c1c1c"
SETTINGS_CARD_BG = "#242424"
SETTINGS_CARD_BORDER = "#323232"
SETTINGS_DIVIDER_COL = "#2f2f2f"
SETTINGS_INPUT_BG = "#1e1e1e"
SETTINGS_INPUT_BORDER = "#3c3c3c"
SETTINGS_HIGHLIGHT_GREEN = "#1f7a44"


# ── Vector SVG Icons (Zero system emojis) ───────────────────────────────────
SVG_SEARCH = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<circle cx="11" cy="11" r="7" stroke="#999999" stroke-width="2"/>'
    '<path d="M16.5 16.5L21 21" stroke="#999999" stroke-width="2" stroke-linecap="round"/>'
    '</svg>'
)

SVG_CLEAR_X = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M6 6L18 18M18 6L6 18" stroke="#aaaaaa" stroke-width="2.2" stroke-linecap="round"/>'
    '</svg>'
)

SVG_CLEAR_X_HOVER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M6 6L18 18M18 6L6 18" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"/>'
    '</svg>'
)

SVG_SHIELD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M12 2.5L4.5 5.8v5.7c0 4.9 3.2 9.4 7.5 10.5 4.3-1.1 7.5-5.6 7.5-10.5V5.8L12 2.5z" '
    'fill="#173d27" stroke="#23a559" stroke-width="1.8"/>'
    '<path d="M9 12.2l2.1 2.1 4.2-4.3" stroke="#39d377" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

SVG_COFFEE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M5 9h11v6a5 5 0 01-5 5H10a5 5 0 01-5-5V9z" stroke="#ffffff" stroke-width="1.8"/>'
    '<path d="M16 10h2a2.5 2.5 0 010 5h-2" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>'
    '<path d="M8 4.5c0 1 .8 1.5.8 2.5M12 4.5c0 1 .8 1.5.8 2.5" stroke="#39d377" stroke-width="1.7" stroke-linecap="round"/>'
    '</svg>'
)

SVG_GRIP_DOTS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 24" fill="none">'
    '<circle cx="5" cy="6" r="1.4" fill="#666666"/>'
    '<circle cx="11" cy="6" r="1.4" fill="#666666"/>'
    '<circle cx="5" cy="12" r="1.4" fill="#666666"/>'
    '<circle cx="11" cy="12" r="1.4" fill="#666666"/>'
    '<circle cx="5" cy="18" r="1.4" fill="#666666"/>'
    '<circle cx="11" cy="18" r="1.4" fill="#666666"/>'
    '</svg>'
)

SVG_IMAGE_PLUS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<rect x="3" y="4" width="18" height="16" rx="2.5" stroke="#8f8f8f" stroke-width="1.7"/>'
    '<circle cx="8.5" cy="9.5" r="1.5" fill="#8f8f8f"/>'
    '<path d="M4.5 17l4.5-4.5 3.5 3.5 2.8-2.8L19.5 17" stroke="#23a559" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

SVG_CHEVRON_RIGHT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M9 6l6 6-6 6" stroke="#777777" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

SVG_SEARCH_EMPTY = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<circle cx="11" cy="11" r="7" stroke="#555555" stroke-width="1.8"/>'
    '<path d="M16.5 16.5L21 21" stroke="#555555" stroke-width="1.8" stroke-linecap="round"/>'
    '<path d="M8.8 8.8l4.4 4.4M13.2 8.8l-4.4 4.4" stroke="#666666" stroke-width="1.6" stroke-linecap="round"/>'
    '</svg>'
)

SVG_TRASH = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M5 7h14M9.5 7V5.2c0-.7.5-1.2 1.2-1.2h2.6c.7 0 1.2.5 1.2 1.2V7" stroke="#c8c8c8" stroke-width="1.7" stroke-linecap="round"/>'
    '<path d="M7.2 7l.9 11.4c.1.9.8 1.6 1.7 1.6h4.4c.9 0 1.6-.7 1.7-1.6L16.8 7" stroke="#c8c8c8" stroke-width="1.7" stroke-linejoin="round"/>'
    '<path d="M10.2 10.8v5.4M13.8 10.8v5.4" stroke="#c8c8c8" stroke-width="1.5" stroke-linecap="round"/>'
    '</svg>'
)


def scope_transparent(widget: QWidget, border_none: bool = True) -> QWidget:
    """Applies transparent styling scoped strictly to the widget's objectName so child QSS is preserved."""
    if not widget.objectName():
        widget.setObjectName("bw_tbox")
    obj = widget.objectName()
    rule = "background: transparent; border: none;" if border_none else "background: transparent;"
    widget.setStyleSheet(f"#{obj} {{ {rule} }}")
    return widget


# ── Accent-Folding & Green HTML Highlighting ────────────────────────────────
_POLISH_FOLD = str.maketrans("łŁđĐøØß", "lLdDoOs")


def fold_accents_with_map(text: str) -> tuple[str, list[int]]:
    """
    Returns (folded_lowercase_str, index_map) where index_map[i] is the character
    index in the original *text* corresponding to folded_lowercase_str[i].
    """
    if not text:
        return "", []
    folded_chars = []
    idx_map = []
    for orig_idx, ch in enumerate(text):
        mapped = ch.translate(_POLISH_FOLD)
        decomposed = unicodedata.normalize("NFKD", mapped)
        for sub_ch in decomposed:
            if unicodedata.category(sub_ch) == "Mn":
                continue
            low = sub_ch.lower()
            for lc in low:
                folded_chars.append(lc)
                idx_map.append(orig_idx)
    return "".join(folded_chars), idx_map


def fold_accents(text: str) -> str:
    """Folds accents/diacritics and lowercases *text* for resilient search matching."""
    folded, _ = fold_accents_with_map(text)
    return folded


def highlight_text_html(text: str, query: str, fg_color: str = "#e6e6e6") -> str:
    """
    Safely escapes *text* to HTML and wraps every occurrence of *query* (and its
    space-separated tokens if >=2 chars) in a crisp BadWords green highlight span.
    Works accent-insensitively while preserving the original characters.
    """
    if not text:
        return ""
    raw_q = (query or "").strip()
    if not raw_q:
        return f'<span style="color: {fg_color};">{html.escape(text)}</span>'

    folded_text, idx_map = fold_accents_with_map(text)
    folded_q = fold_accents(raw_q)
    if not folded_text or not folded_q:
        return f'<span style="color: {fg_color};">{html.escape(text)}</span>'

    tokens = [folded_q]
    parts = [p for p in folded_q.split() if len(p) >= 2]
    if len(parts) > 1:
        tokens.extend(parts)

    # Mark matched original character indices
    hit_orig = [False] * len(text)
    for tok in tokens:
        if not tok:
            continue
        start = 0
        t_len = len(tok)
        while start <= len(folded_text) - t_len:
            pos = folded_text.find(tok, start)
            if pos == -1:
                break
            for k in range(pos, pos + t_len):
                orig_i = idx_map[k]
                if 0 <= orig_i < len(hit_orig):
                    hit_orig[orig_i] = True
            start = pos + 1

    if not any(hit_orig):
        return f'<span style="color: {fg_color};">{html.escape(text)}</span>'

    chunks = []
    i = 0
    n = len(text)
    while i < n:
        flag = hit_orig[i]
        j = i + 1
        while j < n and hit_orig[j] == flag:
            j += 1
        seg = html.escape(text[i:j])
        if flag:
            chunks.append(
                f'<span style="background-color: {SETTINGS_HIGHLIGHT_GREEN}; '
                f'color: #ffffff; font-weight: bold;">{seg}</span>'
            )
        else:
            chunks.append(f'<span style="color: {fg_color};">{seg}</span>')
        i = j
    return "".join(chunks)


def score_search_entry(query: str, entry: dict, gui_lang: str) -> tuple[int, bool, str]:
    """
    Scores a search index entry strictly against active *gui_lang* and English ('en').
    Never matches against unrelated third languages.
    Returns (score, matched_via_english_fallback, matched_en_snippet).
    Score == 0 means no match.
    """
    folded_q = fold_accents(query.strip())
    if not folded_q:
        return 0, False, ""

    tokens = [t for t in folded_q.split() if t]
    if not tokens:
        return 0, False, ""

    t_loc = fold_accents(entry.get("title_loc", ""))
    c_loc = fold_accents(entry.get("category_loc", ""))
    d_loc = fold_accents(entry.get("desc_loc", ""))
    opts_loc = [fold_accents(o) for o in entry.get("options_loc", [])]

    t_en = fold_accents(entry.get("title_en", ""))
    c_en = fold_accents(entry.get("category_en", ""))
    d_en = fold_accents(entry.get("desc_en", ""))
    opts_en = [fold_accents(o) for o in entry.get("options_en", [])]
    kw_en = fold_accents(entry.get("keywords_en", ""))

    def _score_phrase(q_str: str) -> tuple[int, bool, str]:
        sc = 0
        via_en = False
        en_snip = ""

        # Active language tiers (highest priority)
        if t_loc:
            if t_loc == q_str:
                sc = max(sc, 1000)
            elif t_loc.startswith(q_str):
                sc = max(sc, 820)
            elif any(w.startswith(q_str) for w in t_loc.split()):
                sc = max(sc, 680)
            elif q_str in t_loc:
                sc = max(sc, 520)

        if any(q_str in opt for opt in opts_loc if opt):
            sc = max(sc, 420)
        if c_loc and q_str in c_loc:
            sc = max(sc, 320)
        if d_loc and q_str in d_loc:
            sc = max(sc, 220)

        # English fallback (active even when UI != 'en', and NEVER other 9 languages)
        en_hit_score = 0
        if t_en:
            if t_en == q_str:
                en_hit_score = max(en_hit_score, 460)
                en_snip = entry.get("title_en", "")
            elif t_en.startswith(q_str):
                en_hit_score = max(en_hit_score, 400)
                en_snip = entry.get("title_en", "")
            elif any(w.startswith(q_str) for w in t_en.split()):
                en_hit_score = max(en_hit_score, 340)
                en_snip = entry.get("title_en", "")
            elif q_str in t_en:
                en_hit_score = max(en_hit_score, 280)
                en_snip = entry.get("title_en", "")

        if en_hit_score == 0:
            for idx, opt in enumerate(opts_en):
                if opt and q_str in opt:
                    en_hit_score = 210
                    raw_opts = entry.get("options_en", [])
                    en_snip = raw_opts[idx] if idx < len(raw_opts) else ""
                    break
        if en_hit_score == 0 and c_en and q_str in c_en:
            en_hit_score = 170
            en_snip = entry.get("category_en", "")
        if en_hit_score == 0 and kw_en and q_str in kw_en:
            en_hit_score = 150
            en_snip = entry.get("title_en", "")
        if en_hit_score == 0 and d_en and q_str in d_en:
            en_hit_score = 120
            en_snip = entry.get("title_en", "")

        if sc == 0 and en_hit_score > 0:
            sc = en_hit_score
            if gui_lang != "en":
                via_en = True

        return sc, via_en, en_snip

    score, via_en, en_snip = _score_phrase(folded_q)
    if score > 0:
        return score, via_en, en_snip

    # Multi-word query: require EVERY token to match somewhere in local OR English corpus
    if len(tokens) > 1:
        loc_blob = " ".join([t_loc, c_loc, d_loc] + opts_loc)
        en_blob = " ".join([t_en, c_en, d_en, kw_en] + opts_en)
        if all(tok in loc_blob for tok in tokens):
            title_hits = sum(1 for tok in tokens if tok in t_loc)
            return 260 + title_hits * 80, False, ""
        if all(tok in (loc_blob + " " + en_blob) for tok in tokens):
            title_hits = sum(1 for tok in tokens if (tok in t_loc or tok in t_en))
            is_en_only = not all(tok in loc_blob for tok in tokens) and gui_lang != "en"
            return 160 + title_hits * 50, is_en_only, entry.get("title_en", "")

    return 0, False, ""


# ── Layout & Card Building Blocks ───────────────────────────────────────────

class SettingsPageHeader(QWidget):
    """Consistent category page title and concise 1-line subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        scope_transparent(self, border_none=True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, config.S(4))
        lay.setSpacing(config.S(3))

        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet(
            f"color: #ffffff; font-family: '{config.UI_FONT_NAME}', sans-serif; "
            f"font-size: {config.FS_PX(14.5)}px; font-weight: bold; background: transparent; border: none;"
        )
        lay.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_sub = QLabel(subtitle, self)
            self.lbl_sub.setWordWrap(True)
            self.lbl_sub.setStyleSheet(
                f"color: #909090; font-family: '{config.UI_FONT_NAME}', sans-serif; "
                f"font-size: {config.FS_PX(9.5)}px; background: transparent; border: none;"
            )
            lay.addWidget(self.lbl_sub)


class SettingsSectionLabel(QLabel):
    """Muted section caption placed directly above an elevated card."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: #b8b8b8; font-family: '{config.UI_FONT_NAME}', sans-serif; "
            f"font-size: {config.FS_PX(9.5)}px; font-weight: bold; "
            f"background: transparent; border: none; padding-left: {config.S(2)}px;"
        )


class SettingsRowWidget(QFrame):
    """
    A single horizontal option row inside a SettingsCard, supporting smooth
    1.5s green highlight flash when navigated to from search.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsRowWidget")
        self._flash_alpha = 0.0
        self._divider = None
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1500)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_flash_tick)
        self.setStyleSheet("QFrame#SettingsRowWidget { background: transparent; border: none; }")

    def _on_flash_tick(self, val):
        self._flash_alpha = float(val)
        self.update()

    def flash_highlight(self):
        self._anim.stop()
        self._anim.setStartValue(0.32)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def paintEvent(self, event):
        if self._flash_alpha > 0.005:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setPen(Qt.NoPen)
            col = QColor(35, 165, 89, int(round(255 * self._flash_alpha)))
            p.setBrush(col)
            p.drawRoundedRect(self.rect().adjusted(2, 1, -2, -1), config.S(6), config.S(6))
            p.end()
        super().paintEvent(event)


class SettingsCard(QFrame):
    """
    Elevated Brave-inspired card container (#212121, 1px #2e2e2e border, 8px radius)
    with clean hairline dividers between option rows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsCard")
        self._flash_alpha = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1500)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_flash_tick)
        self.setStyleSheet(
            f"QFrame#SettingsCard {{ background-color: {SETTINGS_CARD_BG}; "
            f"border: 1px solid {SETTINGS_CARD_BORDER}; border-radius: {config.S(8)}px; }}"
        )
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self._items = []

    def _on_flash_tick(self, val):
        self._flash_alpha = float(val)
        self.update()

    def flash_highlight(self):
        self._anim.stop()
        self._anim.setStartValue(0.28)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._flash_alpha > 0.005:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setPen(QColor(35, 165, 89, int(round(255 * min(1.0, self._flash_alpha * 2.5)))))
            p.setBrush(QColor(35, 165, 89, int(round(255 * self._flash_alpha * 0.45))))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), config.S(8), config.S(8))
            p.end()

    def add_divider(self):
        div = QFrame(self)
        div.setObjectName("SettingsCardDivider")
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {SETTINGS_DIVIDER_COL}; border: none; margin: 0px;")
        self._lay.addWidget(div)
        return div

    def add_content_widget(self, widget: QWidget, margins: tuple = None):
        wrap = QWidget(self)
        scope_transparent(wrap, border_none=True)
        wl = QVBoxLayout(wrap)
        if margins is None:
            wl.setContentsMargins(config.S(16), config.S(12), config.S(16), config.S(12))
        else:
            wl.setContentsMargins(*margins)
        wl.setSpacing(0)
        wl.addWidget(widget)
        self._lay.addWidget(wrap)
        return wrap


# ── Modern Search Bar (Zero native clear button) ────────────────────────────

class SettingsSearchBar(QFrame):
    """
    Modern rounded search box with left vector magnifying glass and custom right
    vector 'X' clear button (completely replacing Qt's native clear icon).
    """
    textChanged = Signal(str)
    returnPressed = Signal()

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsSearchBox")
        self.setFixedHeight(config.S(34))
        self._focused = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(config.S(10), 0, config.S(6), 0)
        lay.setSpacing(config.S(6))

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedSize(config.S(15), config.S(15))
        self.lbl_icon.setPixmap(get_svg_icon(SVG_SEARCH, size=14).pixmap(config.S(14), config.S(14)))
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.lbl_icon)

        self.line_edit = QLineEdit(self)
        self.line_edit.setObjectName("SettingsSearchEdit")
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setClearButtonEnabled(False)
        self.line_edit.setFrame(False)
        self.line_edit.setStyleSheet(
            f"QLineEdit#SettingsSearchEdit {{ "
            f"background: transparent; border: none; color: #f0f0f0; "
            f"padding: 0px; margin: 0px; "
            f"font-family: '{config.UI_FONT_NAME}', sans-serif; "
            f"font-size: {config.FS_PX(9.5)}px; "
            f"}}"
        )
        self.line_edit.installEventFilter(self)
        self.line_edit.textChanged.connect(self._on_inner_text_changed)
        self.line_edit.returnPressed.connect(self.returnPressed.emit)
        lay.addWidget(self.line_edit, 1)

        self.btn_clear = QPushButton(self)
        self.btn_clear.setObjectName("SettingsSearchClear")
        self.btn_clear.setFixedSize(config.S(22), config.S(22))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFocusPolicy(Qt.NoFocus)
        self._ic_normal = get_svg_icon(SVG_CLEAR_X, size=11)
        self._ic_hover = get_svg_icon(SVG_CLEAR_X_HOVER, size=11)
        self.btn_clear.setIcon(self._ic_normal)
        self.btn_clear.setIconSize(QSize(config.S(11), config.S(11)))
        self.btn_clear.setStyleSheet(
            f"QPushButton#SettingsSearchClear {{ "
            f"background: transparent; border: none; border-radius: {config.S(11)}px; padding: 0px; "
            f"}} "
            f"QPushButton#SettingsSearchClear:hover {{ background-color: #444444; }}"
        )
        self.btn_clear.hide()
        self.btn_clear.clicked.connect(self.clear)
        self.btn_clear.installEventFilter(self)
        lay.addWidget(self.btn_clear)

        self._apply_box_style()

    def _apply_box_style(self):
        bg = "#272727" if self._focused else "#303030"
        border = config.BTN_BG if self._focused else "#424242"
        self.setStyleSheet(
            f"QFrame#SettingsSearchBox {{ "
            f"background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: {config.S(8)}px; "
            f"}}"
        )

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.line_edit:
            if event.type() == QEvent.FocusIn:
                self._focused = True
                self._apply_box_style()
            elif event.type() == QEvent.FocusOut:
                self._focused = False
                self._apply_box_style()
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                if self.line_edit.text():
                    self.clear()
                    return True
        elif obj is self.btn_clear:
            if event.type() == QEvent.Enter:
                self.btn_clear.setIcon(self._ic_hover)
            elif event.type() == QEvent.Leave:
                self.btn_clear.setIcon(self._ic_normal)
        return super().eventFilter(obj, event)

    def _on_inner_text_changed(self, txt: str):
        self.btn_clear.setVisible(bool(txt))
        self.textChanged.emit(txt)

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)

    def setFocus(self):
        self.line_edit.setFocus()


# ── Search Result Card ──────────────────────────────────────────────────────

class SearchResultCard(QFrame):
    """Clickable Brave-style search result row with green highlighted text."""
    clicked = Signal()

    def __init__(
        self,
        title_html: str,
        category_text: str,
        desc_html: str = "",
        en_hint_html: str = "",
        badge_text: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("SearchResultCard")
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self._apply_style()

        root = QHBoxLayout(self)
        root.setContentsMargins(config.S(16), config.S(12), config.S(14), config.S(12))
        root.setSpacing(config.S(12))

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(config.S(3))

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(config.S(8))

        lbl_title = QLabel(title_html, self)
        lbl_title.setTextFormat(Qt.RichText)
        lbl_title.setWordWrap(True)
        lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lbl_title.setStyleSheet(
            f"font-family: '{config.UI_FONT_NAME}', sans-serif; "
            f"font-size: {config.FS_PX(10.5)}px; font-weight: 600; "
            f"background: transparent; border: none;"
        )
        top_row.addWidget(lbl_title, 1)

        if badge_text:
            lbl_badge = QLabel(badge_text, self)
            lbl_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl_badge.setStyleSheet(
                f"background-color: #173524; color: #5ce091; border: 1px solid #24593a; "
                f"border-radius: {config.S(4)}px; padding: {config.S(1)}px {config.S(6)}px; "
                f"font-size: {config.FS_PX(8)}px; font-weight: bold;"
            )
            top_row.addWidget(lbl_badge, 0, Qt.AlignRight | Qt.AlignVCenter)

        left.addLayout(top_row)

        meta_txt = html.escape(category_text)
        if en_hint_html:
            meta_txt = f"{meta_txt}  ·  {en_hint_html}"
        lbl_meta = QLabel(meta_txt, self)
        lbl_meta.setTextFormat(Qt.RichText)
        lbl_meta.setWordWrap(True)
        lbl_meta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lbl_meta.setStyleSheet(
            f"color: #8f8f8f; font-family: '{config.UI_FONT_NAME}', sans-serif; "
            f"font-size: {config.FS_PX(8.8)}px; background: transparent; border: none;"
        )
        left.addWidget(lbl_meta)

        if desc_html:
            lbl_desc = QLabel(desc_html, self)
            lbl_desc.setTextFormat(Qt.RichText)
            lbl_desc.setWordWrap(True)
            lbl_desc.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl_desc.setStyleSheet(
                f"color: #a6a6a6; font-family: '{config.UI_FONT_NAME}', sans-serif; "
                f"font-size: {config.FS_PX(9)}px; background: transparent; border: none;"
            )
            left.addWidget(lbl_desc)

        root.addLayout(left, 1)

        lbl_arrow = QLabel(self)
        lbl_arrow.setFixedSize(config.S(16), config.S(16))
        lbl_arrow.setPixmap(get_svg_icon(SVG_CHEVRON_RIGHT, size=14).pixmap(config.S(14), config.S(14)))
        lbl_arrow.setStyleSheet("background: transparent; border: none;")
        lbl_arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        root.addWidget(lbl_arrow, 0, Qt.AlignVCenter)

    def _apply_style(self):
        bg = "#2d2d2d" if self._hovered else SETTINGS_CARD_BG
        border = "#454545" if self._hovered else SETTINGS_CARD_BORDER
        self.setStyleSheet(
            f"QFrame#SearchResultCard {{ "
            f"background-color: {bg}; border: 1px solid {border}; border-radius: {config.S(8)}px; "
            f"}}"
        )

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


# ── Support Screenshot Dropzone, Thumbnails & Lightbox ──────────────────────

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ScreenshotPreviewDialog(FramelessWindowMixin, _BaseDialog):
    """Frameless dark modal lightbox showing a full-resolution screenshot preview."""

    def __init__(self, image_path: str, title: str, parent=None):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)

        self.setStyleSheet(
            f"QDialog {{ background-color: {config.BG_COLOR}; }} "
            f"#MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #2e2e2e; }}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        outer.addWidget(self.inner_frame)

        root = QVBoxLayout(self.inner_frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        lang = "en"
        if parent and hasattr(parent, "engine"):
            try:
                lang = (parent.engine.load_preferences() or {}).get("gui_lang", "en")
            except Exception:
                pass
        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, "_is_win", False) and hasattr(self, "setTitleBar"):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        self._tb.set_title(f"{title} - {os.path.basename(image_path)}")
        root.addWidget(self._tb)

        body = QVBoxLayout()
        body.setContentsMargins(config.S(16), config.S(14), config.S(16), config.S(14))
        body.setSpacing(config.S(10))

        pix = QPixmap(image_path)
        scr = (parent.screen() if parent else None) or QApplication.primaryScreen()
        avail = scr.availableGeometry() if scr else QRect(0, 0, 1280, 800)
        max_w = max(config.S(420), int(avail.width() * 0.72))
        max_h = max(config.S(320), int(avail.height() * 0.72))

        lbl_img = QLabel(self.inner_frame)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setStyleSheet("background-color: #121212; border: 1px solid #2a2a2a; padding: 4px;")
        if not pix.isNull():
            scaled = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_img.setPixmap(scaled)
            lbl_info = QLabel(
                f"{os.path.basename(image_path)}  ({pix.width()} x {pix.height()})",
                self.inner_frame,
            )
        else:
            lbl_img.setText(os.path.basename(image_path))
            lbl_info = QLabel(image_path, self.inner_frame)

        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setStyleSheet(f"color: #9a9a9a; font-size: {config.FS_PX(9)}px; background: transparent;")
        body.addWidget(lbl_img, 1)
        body.addWidget(lbl_info)
        root.addLayout(body)

        self.adjustSize()
        _center_on_screen(self, self.width(), self.height(), reference_window=parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


class AttachmentThumbCard(QFrame):
    """Visual image thumbnail tile with filename, resolution, click-to-preview, and remove X."""
    removeRequested = Signal(str)
    previewRequested = Signal(str)

    def __init__(self, image_path: str, preview_tooltip: str = "", parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setObjectName("AttachmentThumbCard")
        self.setFixedSize(config.S(118), config.S(102))
        self.setCursor(Qt.PointingHandCursor)
        if preview_tooltip:
            self.setToolTip(preview_tooltip)
        self.setStyleSheet(
            f"QFrame#AttachmentThumbCard {{ "
            f"background-color: #1e1e1e; border: 1px solid #383838; border-radius: {config.S(6)}px; "
            f"}} "
            f"QFrame#AttachmentThumbCard:hover {{ border-color: {config.BTN_BG}; background-color: #262626; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(config.S(6), config.S(6), config.S(6), config.S(5))
        lay.setSpacing(config.S(4))

        pix = QPixmap(image_path)
        thumb_lbl = QLabel(self)
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setFixedHeight(config.S(62))
        thumb_lbl.setStyleSheet(
            f"background-color: #161616; border: 1px solid #2c2c2c; border-radius: {config.S(4)}px;"
        )
        thumb_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        dims_str = ""
        if not pix.isNull():
            dims_str = f"{pix.width()}x{pix.height()}"
            scaled = pix.scaled(
                config.S(104), config.S(60),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            thumb_lbl.setPixmap(scaled)
        else:
            thumb_lbl.setText("IMG")
        lay.addWidget(thumb_lbl)

        base_name = os.path.basename(image_path)
        fm = QFontMetrics(config.make_font(config.UI_FONT_NAME, 8))
        elided_name = fm.elidedText(base_name, Qt.ElideMiddle, config.S(104))
        lbl_name = QLabel(elided_name, self)
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lbl_name.setStyleSheet(
            f"color: #d4d4d4; font-size: {config.FS_PX(8)}px; background: transparent; border: none;"
        )
        lay.addWidget(lbl_name)

        if dims_str:
            lbl_dim = QLabel(dims_str, self)
            lbl_dim.setAlignment(Qt.AlignCenter)
            lbl_dim.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lbl_dim.setStyleSheet(
                f"color: #777777; font-size: {config.FS_PX(7.5)}px; background: transparent; border: none;"
            )
            lay.addWidget(lbl_dim)

        # Floating top-right remove button
        btn_del = QPushButton(self)
        btn_del.setFixedSize(config.S(20), config.S(20))
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setIcon(get_svg_icon(SVG_CLEAR_X_HOVER, size=10))
        btn_del.setIconSize(QSize(config.S(10), config.S(10)))
        btn_del.setStyleSheet(
            f"QPushButton {{ background-color: rgba(20, 20, 20, 220); "
            f"border: 1px solid #484848; border-radius: {config.S(10)}px; padding: 0px; }} "
            f"QPushButton:hover {{ background-color: #9e2a2b; border-color: #ed4245; }}"
        )
        btn_del.move(self.width() - config.S(24), config.S(4))
        btn_del.raise_()
        btn_del.clicked.connect(lambda: self.removeRequested.emit(self.image_path))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.previewRequested.emit(self.image_path)
        super().mouseReleaseEvent(event)


class SupportDropZone(QFrame):
    """Interactive screenshot dropzone supporting file drag-drop, click-browse, and Ctrl+V paste."""
    filesDropped = Signal(list)
    browseClicked = Signal()

    def __init__(self, hint_text: str, btn_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SupportDropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self._dragging = False
        self._apply_style()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(config.S(12), config.S(10), config.S(12), config.S(10))
        lay.setSpacing(config.S(10))

        lbl_ic = QLabel(self)
        lbl_ic.setFixedSize(config.S(22), config.S(22))
        lbl_ic.setPixmap(get_svg_icon(SVG_IMAGE_PLUS, size=20).pixmap(config.S(20), config.S(20)))
        lbl_ic.setStyleSheet("background: transparent; border: none;")
        lbl_ic.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(lbl_ic)

        self.lbl_hint = QLabel(hint_text, self)
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_hint.setStyleSheet(
            f"color: #9a9a9a; font-size: {config.FS_PX(8.8)}px; "
            f"font-family: '{config.UI_FONT_NAME}', sans-serif; background: transparent; border: none;"
        )
        lay.addWidget(self.lbl_hint, 1)

        btn_pick = QPushButton(btn_text, self)
        btn_pick.setObjectName("btn_secondary")
        btn_pick.setFixedHeight(config.S(28))
        btn_pick.setCursor(Qt.PointingHandCursor)
        btn_pick.clicked.connect(self.browseClicked.emit)
        lay.addWidget(btn_pick)

    def _apply_style(self):
        border = config.BTN_BG if self._dragging else "#404040"
        bg = "#1e2e24" if self._dragging else "#1e1e1e"
        self.setStyleSheet(
            f"QFrame#SupportDropZone {{ "
            f"background-color: {bg}; border: 1px dashed {border}; border-radius: {config.S(6)}px; "
            f"}} "
            f"QFrame#SupportDropZone:hover {{ border-color: #5a5a5a; background-color: #252525; }}"
        )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.browseClicked.emit()
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for u in mime.urls():
                if os.path.splitext(u.toLocalFile())[1].lower() in _IMG_EXTS:
                    self._dragging = True
                    self._apply_style()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._dragging = False
        self._apply_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._dragging = False
        self._apply_style()
        mime = event.mimeData()
        paths = []
        if mime and mime.hasUrls():
            for u in mime.urls():
                lp = u.toLocalFile()
                if lp and os.path.isfile(lp) and os.path.splitext(lp)[1].lower() in _IMG_EXTS:
                    paths.append(lp)
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


def save_clipboard_image_temp(image: QImage) -> str | None:
    """Saves a QImage pasted from clipboard to a temporary PNG file and returns its path."""
    if image is None or image.isNull():
        return None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="bw_clip_")
        os.close(fd)
        if image.save(tmp_path, "PNG"):
            return tmp_path
    except Exception:
        pass
    return None
