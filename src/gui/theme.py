#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: theme.py
ROLE: GUI Theme layer
DESCRIPTION:
Selectable colour themes (StoryCraft, Graphite, Midnight, Studio). The UI is written against the
original ("classic") palette; this layer translates those colours at the point they are used:
every stylesheet passes through it (QWidget.setStyleSheet is wrapped once at startup) and painted
colours go through qc(). Greys move along the theme's tinted ramp, the brand green becomes the
theme's accent, corners get rounder. Marker and Resolve clip colours never change.
Switching theme re-applies every widget's original stylesheet, so it takes effect immediately.
"""

import colorsys
import os
import re

from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget

# Lightness anchors: (classic lightness, themed lightness), monotonic so the visual hierarchy holds
_DARK_RAMP_DEEP = [(0.0, 0.0), (0.10, 0.065), (0.15, 0.10), (0.25, 0.185), (0.45, 0.41), (0.70, 0.71), (1.0, 1.0)]
_DARK_RAMP = [(0.0, 0.0), (0.10, 0.075), (0.15, 0.112), (0.25, 0.20), (0.45, 0.42), (0.70, 0.71), (1.0, 1.0)]

_INK_RAMP = [(0.0, 0.0), (0.10, 0.055), (0.15, 0.09), (0.25, 0.165), (0.45, 0.40), (0.70, 0.70), (1.0, 1.0)]
# Light: the classic dark greys turn over. Background near-white, panels (#262626) white cards,
# surfaces on them (#2a2a2a) a light grey, lines (#333) soft, text (#d9d9d9, white) ink.
_LIGHT_RAMP = [(0.0, 0.80), (0.055, 0.90), (0.10, 0.955), (0.11, 0.965), (0.13, 0.985), (0.149, 1.0), (0.165, 0.94),
               (0.20, 0.89), (0.267, 0.80), (0.333, 0.70), (0.40, 0.60), (0.54, 0.46), (0.69, 0.33), (0.85, 0.16), (1.0, 0.08)]

THEMES = {
    "classic": None,  # the original BadWords look: kept as the reference the UI is written in, not offered
    # StoryCraft: the brand's ink (#0b0b14) with violet-tinted surfaces, brand violet accent
    "storycraft": {"name": "StoryCraft", "hue": 240, "sat_dark": 0.30, "sat_light": 0.14, "ramp": _INK_RAMP,
                   "accent": "#a855f7", "accent_text": "#ffffff", "radius": 1.6, "font": "Inter"},
    "storycraft_light": {"name": "StoryCraft Light", "light": True, "hue": 240, "sat_dark": 0.30, "sat_light": 0.20,
                         "ramp": _LIGHT_RAMP, "accent": "#7c3aed", "accent_text": "#ffffff", "radius": 1.6, "font": "Inter"},
    "graphite": {"name": "Graphite", "hue": 220, "sat_dark": 0.10, "sat_light": 0.04, "ramp": _DARK_RAMP_DEEP,
                 "accent": "#2dd4bf", "accent_text": "#042f2a", "radius": 1.35, "font": "Inter"},
    "midnight": {"name": "Midnight", "hue": 226, "sat_dark": 0.30, "sat_light": 0.12, "ramp": _DARK_RAMP_DEEP,
                 "accent": "#5b57e8", "accent_text": "#ffffff", "radius": 1.45, "font": "Geist"},
    "studio": {"name": "Studio", "hue": 30, "sat_dark": 0.11, "sat_light": 0.07, "ramp": _DARK_RAMP,
               "accent": "#f2762e", "accent_text": "#1d0d02", "radius": 1.25, "font": "Manrope"},
}
DISPLAY_NAMES = {"storycraft": "StoryCraft", "storycraft_light": "StoryCraft Light", "graphite": "Graphite",
                 "midnight": "Midnight", "studio": "Studio"}
PICKER = ["storycraft", "storycraft_light", "graphite", "midnight", "studio"]  # what Settings offers
DEFAULT = "storycraft"
_BRAND_L = 0.39  # lightness of the classic accent #23a559

_current = "classic"
_cache = {}
_protected = set()
_orig_set_stylesheet = QWidget.setStyleSheet
_installed = False
_classic_font = None      # the UI font the app was written with (config.UI_FONT_NAME)
_fonts_available = set()  # theme fonts that registered (assets/fonts, SIL Open Font License)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v * 255))) for v in rgb)


def _norm(hx):
    hx = hx.strip().lower()
    if len(hx) == 4:
        hx = "#" + "".join(ch * 2 for ch in hx[1:])
    return hx


def _ramp(ramp, l):
    for (a0, b0), (a1, b1) in zip(ramp, ramp[1:]):
        if l <= a1:
            return b0 + (b1 - b0) * ((l - a0) / (a1 - a0) if a1 > a0 else 0.0)
    return l


def _is_accent(h, l, s):
    return 0.25 < h < 0.48 and s > 0.35 and 0.12 < l < 0.75


def _map_rgb(r, g, b):
    """Classic rgb (0..1) -> themed rgb (0..1), or None when it stays."""
    t = THEMES.get(_current)
    if t is None:
        return None
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.10:  # a grey: along the theme's ramp, tinted
        nl = _ramp(t["ramp"], l)
        sat = t["sat_dark"] if l < 0.5 else t["sat_light"]
        if l <= 0.01 or (l >= 0.98 and not t.get("light")):
            return None  # pure black stays (shadows); pure white too, except on light themes (it's text there)
        return colorsys.hls_to_rgb(t["hue"] / 360.0, nl, sat)
    if _is_accent(h, l, s):  # the brand green and its shades -> the accent, same relative lightness
        a = _norm(t["accent"])
        ah, al, as_ = colorsys.rgb_to_hls(*(int(a[i:i + 2], 16) / 255 for i in (1, 3, 5)))
        return colorsys.hls_to_rgb(ah, max(0.12, min(0.85, al * l / _BRAND_L)), as_)
    return None


def color(value):
    """Map a classic colour (hex string) to the current theme's; anything else is returned as is."""
    if not isinstance(value, str) or not value.startswith("#") or len(value) not in (4, 7):
        return value
    hx = _norm(value)
    if _current == "classic" or hx in _protected:
        return value
    key = (_current, hx)
    if key not in _cache:
        m = _map_rgb(*(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)))
        _cache[key] = _hex(m) if m else value
    return _cache[key]


def qc(*args):
    """QColor(...) through the theme: qc("#262626"), qc(config.BG_COLOR), qc(38, 38, 38[, a])."""
    if _current != "classic":
        if len(args) == 1 and isinstance(args[0], str):
            return QColor(color(args[0]))
        if 3 <= len(args) <= 4 and all(isinstance(v, int) for v in args):
            hx = "#%02x%02x%02x" % tuple(args[:3])
            if hx not in _protected:
                c = QColor(color(hx))
                if len(args) == 4:
                    c.setAlpha(args[3])
                return c
    return QColor(*args)


def is_light():
    """True when the current theme is a light one (dark text, dark-stroke icons)."""
    return bool((THEMES.get(_current) or {}).get("light"))


def accent_text():
    t = THEMES.get(_current)
    return t["accent_text"] if t else "#ffffff"


def _fonts_dir():
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for d in (os.path.join(src_dir, "assets", "fonts"), os.path.join(os.path.dirname(src_dir), "assets", "fonts")):
        if os.path.isdir(d):
            return d
    return None


def _register_fonts():
    d = _fonts_dir()
    if not d:
        return
    for name in sorted(os.listdir(d)):
        if name.lower().endswith((".ttf", ".otf")):
            fid = QFontDatabase.addApplicationFont(os.path.join(d, name))
            if fid >= 0:
                _fonts_available.update(QFontDatabase.applicationFontFamilies(fid))


def ui_font():
    """The UI font family for the current theme (falls back to the classic one if not available)."""
    t = THEMES.get(_current)
    if t and t.get("font") in _fonts_available:
        return t["font"]
    return _classic_font


def _apply_app_font():
    app = QApplication.instance()
    family = ui_font()
    if app is None or not family:
        return
    f = app.font()
    if f.family() != family:
        f.setFamily(family)
        app.setFont(f)


_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(,\s*[\d.]+%?\s*)?\)")
_RADIUS_RE = re.compile(r"(radius\s*:\s*)(\d+)px")
_BG_RE = re.compile(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)")
_WHITE_TEXT_RE = re.compile(r"(?<![-\w])color\s*:\s*(#fff\b|#ffffff\b|white\b)", re.I)


_TEXT_COLOR_RE = re.compile(r"((?<![-\w])color\s*:\s*)(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)")


def _text_color(value):
    hx = _norm(value)
    t = THEMES.get(_current)
    if t is None or hx in _protected:
        return value
    h, l, s = colorsys.rgb_to_hls(*(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    if not _is_accent(h, l, s):
        return color(value)
    a = _norm(t["accent"])
    ah, al, as_ = colorsys.rgb_to_hls(*(int(a[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    return _hex(colorsys.hls_to_rgb(ah, max(al, min(0.85, al * l / _BRAND_L)), as_))


def _rgb_sub(m):
    hx = "#%02x%02x%02x" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    mapped = color(hx)
    if mapped == hx:
        return m.group(0)
    r, g, b = (int(mapped[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}{m.group(4) or ', 255'})" if m.group(4) else f"rgb({r}, {g}, {b})"


def _block(text, scale_radius=True):
    # White text on an accent background: the theme says which text colour reads on its accent
    # (set after the mapping below, which on a light theme would turn white text dark)
    for m in _BG_RE.finditer(text):
        hx = _norm(m.group(1))
        if hx not in _protected and _is_accent(*colorsys.rgb_to_hls(*(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)))):
            text = _WHITE_TEXT_RE.sub(lambda w: w.group(0)[:w.start(1) - w.start(0)] + "__ACCENT_TEXT__", text)
            break
    # Text in an accent shade stays at least as bright as the accent itself, so it reads on dark.
    # Mapped text colours are parked as tokens so the general pass below doesn't map them twice
    # (a light theme turns greys over: a second pass would flip them back).
    parked = []

    def _park(m):
        parked.append(_text_color(m.group(2)))
        return f"{m.group(1)}__TXT{len(parked) - 1}__"
    text = _TEXT_COLOR_RE.sub(_park, text)
    text = _HEX_RE.sub(lambda m: color(m.group(0)), text)
    text = _RGB_RE.sub(_rgb_sub, text)
    for i, c in enumerate(parked):
        text = text.replace(f"__TXT{i}__", c)
    t = THEMES.get(_current)
    if t and scale_radius:
        # Only small corners get rounder; large radii already make pills and circles (a radius
        # beyond half the height makes Qt drop the rounding altogether)
        text = _RADIUS_RE.sub(lambda m: m.group(0) if int(m.group(2)) > 6 else
                              f"{m.group(1)}{round(int(m.group(2)) * t['radius'])}px", text)
        family = ui_font()
        if _classic_font and family and family != _classic_font:
            text = re.sub(r"(font-family\s*:\s*)(['\"]?)" + re.escape(_classic_font) + r"\2", lambda m: f"{m.group(1)}'{family}'", text)
    return text.replace("__ACCENT_TEXT__", accent_text())


def qss(text):
    """A classic stylesheet -> the current theme's."""
    if not text or _current == "classic":
        return text
    if "{" not in text:
        return _block(text)
    out, pos = [], 0
    for m in re.finditer(r"\{[^{}]*\}", text):
        selector = text[pos:m.start()]
        out.append(selector)
        # Slider knobs are circles sized by their own radius: leave those alone
        out.append(_block(m.group(0), scale_radius="::handle" not in selector))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _themed_set_stylesheet(widget, text):
    widget.setProperty("_bw_classic_qss", text or "")
    _orig_set_stylesheet(widget, qss(text or ""))


def current():
    return _current


def install(name=None, protected=(), ui_font_name=None):
    """Call once, after the QApplication and before any widget exists.
    protected: colours that must never change (markers). ui_font_name: the classic UI font."""
    global _installed, _current, _classic_font
    for c in protected:
        if isinstance(c, str) and c.startswith("#") and len(c) in (4, 7):
            hx = _norm(c)
            # Only colours that mean something (markers, Resolve clips) are locked; a grey in the
            # list (normal text, backgrounds) must follow the theme, or it vanishes on a light one
            if colorsys.rgb_to_hls(*(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)))[2] >= 0.10:
                _protected.add(hx)
    if ui_font_name:
        _classic_font = ui_font_name
    if not _installed:
        QWidget.setStyleSheet = _themed_set_stylesheet
        _register_fonts()
        _installed = True
    _current = name if name in THEMES and name != "classic" else DEFAULT
    _apply_app_font()


def set_theme(name):
    """Switch live: every widget's original stylesheet is translated again, then everything repaints."""
    global _current
    if name not in THEMES or name == _current:
        return
    _current = name
    app = QApplication.instance()
    if app is None:
        return
    _apply_app_font()
    classic_app = app.property("_bw_classic_qss")
    if classic_app is not None:
        app.setStyleSheet(qss(classic_app))
    for w in app.allWidgets():
        original = w.property("_bw_classic_qss")
        if original is not None:
            _orig_set_stylesheet(w, qss(original))
        if hasattr(w, "_needs_pixmap_rebuild"):
            w._needs_pixmap_rebuild = True
        w.update()


def set_app_stylesheet(app, text):
    """QApplication-wide stylesheet through the theme (kept for live switching)."""
    app.setProperty("_bw_classic_qss", text or "")
    app.setStyleSheet(qss(text or ""))
