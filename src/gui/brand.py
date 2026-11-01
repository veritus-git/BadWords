#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: brand.py
ROLE: GUI Branding
DESCRIPTION:
StoryCraft's identity in the app: the mark (assets/brand/storycraft-mark.svg, built by
tools/brand/build_brand.py) and the two-tone wordmark ("Story" solid, "Craft" in the brand
gradient) set in Outfit. Brand colours stay fixed whatever the colour theme.
"""

import os

from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainterPath
from PySide6.QtSvg import QSvgRenderer

import config

CYAN = "#22d3ee"
VIOLET = "#a855f7"
WORDMARK_FONT = "Outfit"

_renderers = {}


def brand_dir():
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for d in (os.path.join(src_dir, "assets", "brand"), os.path.join(os.path.dirname(src_dir), "assets", "brand")):
        if os.path.isdir(d):
            return d
    return None


def _renderer(name):
    if name not in _renderers:
        d = brand_dir()
        path = os.path.join(d, name) if d else ""
        _renderers[name] = QSvgRenderer(path) if path and os.path.isfile(path) else None
    return _renderers[name]


def draw_mark(painter, rect, variant="storycraft-mark.svg"):
    """Paint the app mark into rect (QRectF, square)."""
    r = _renderer(variant)
    if r is not None and r.isValid():
        r.render(painter, rect)


def gradient(x0, x1):
    g = QLinearGradient(x0, 0, x1, 0)
    g.setColorAt(0.0, QColor(CYAN))
    g.setColorAt(1.0, QColor(VIOLET))
    return g


def wordmark_font(px):
    f = QFont(WORDMARK_FONT)
    f.setPixelSize(int(px))
    f.setWeight(QFont.Weight.DemiBold)
    return f


def wordmark_width(px):
    fm = QFontMetricsF(wordmark_font(px))
    return fm.horizontalAdvance("Story") + fm.horizontalAdvance("Craft")


def draw_wordmark(painter, x, baseline, px, solid="#ffffff"):
    """'Story' in `solid`, 'Craft' in the brand gradient; returns the width drawn.
    The name is fixed artwork: config.APP_NAME is used for plain text elsewhere."""
    f = wordmark_font(px)
    fm = QFontMetricsF(f)
    story_w = fm.horizontalAdvance("Story")
    craft_w = fm.horizontalAdvance("Craft")
    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    p1, p2 = QPainterPath(), QPainterPath()
    p1.addText(QPointF(x, baseline), f, "Story")
    p2.addText(QPointF(x + story_w, baseline), f, "Craft")
    # Variable fonts overlap their contours: odd-even filling would punch holes into the letters
    p1.setFillRule(Qt.WindingFill)
    p2.setFillRule(Qt.WindingFill)
    painter.fillPath(p1, QColor(solid))
    painter.fillPath(p2, gradient(x + story_w, x + story_w + craft_w))
    painter.restore()
    return story_w + craft_w


# ── Animated mark (loading) ──────────────────────────────────────────────────
# The same geometry as tools/brand/build_brand.py (512 x 512 grid): the S is traced as a story arc
# while the playhead glides over the clips.
_S_SEGMENTS = ((344, 148), (322, 116, 288, 102, 252, 102), (198, 102, 164, 134, 164, 178),
               (164, 226, 204, 242, 256, 256), (308, 270, 348, 288, 348, 336),
               (348, 382, 312, 410, 260, 410), (218, 410, 186, 394, 166, 362))
_BARS = ((190, 210, 150, False), (128, 246, 196, True), (204, 282, 150, False))  # x, y, width, hot
_CYCLE = 2.6  # seconds: trace 1.4, hold 0.8, fade 0.4


def _s_path():
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(*_S_SEGMENTS[0])
    for c in _S_SEGMENTS[1:]:
        path.cubicTo(QPointF(c[0], c[1]), QPointF(c[2], c[3]), QPointF(c[4], c[5]))
    return path


def draw_mark_animated(painter, rect, t):
    """Paint the mark into rect (QRectF, square) at time t (seconds since the animation started)."""
    from PySide6.QtGui import QPainterPath, QPen, QBrush
    import math
    phase = t % _CYCLE
    ease = lambda x: 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, x)))
    progress = ease(phase / 1.4)
    bright = 1.0 if phase < 2.2 else 1.0 - (phase - 2.2) / 0.4
    head_x = 150 + 196 * (0.5 - 0.5 * math.cos(2 * math.pi * t / _CYCLE))

    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 512.0, rect.height() / 512.0)
    tile = QLinearGradient(0, 0, 512, 512)
    tile.setColorAt(0, QColor("#1a1b2e"))
    tile.setColorAt(1, QColor("#0b0b14"))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(tile))
    painter.drawRoundedRect(QRectF(8, 8, 496, 496), 116, 116)
    rim = QLinearGradient(0, 0, 512, 512)
    c0, c1 = QColor(CYAN), QColor(VIOLET)
    c0.setAlphaF(0.55)
    c1.setAlphaF(0.55)
    rim.setColorAt(0, c0)
    rim.setColorAt(1, c1)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QBrush(rim), 3))
    painter.drawRoundedRect(QRectF(9.5, 9.5, 493, 493), 114.5, 114.5)

    path = _s_path()
    arc = QLinearGradient(164, 102, 348, 410)
    arc.setColorAt(0, QColor(CYAN))
    arc.setColorAt(1, QColor(VIOLET))
    dim = QPen(QColor(255, 255, 255, 34), 54, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(dim)
    painter.drawPath(path)
    if progress > 0.002 and bright > 0:
        traced = QPainterPath()
        n = max(2, int(140 * progress))
        traced.moveTo(path.pointAtPercent(0.0))
        for k in range(1, n + 1):
            traced.lineTo(path.pointAtPercent(progress * k / n))
        painter.setOpacity(bright)
        painter.setPen(QPen(QBrush(arc), 54, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(traced)
        painter.setOpacity(1.0)

    gap = QColor("#11121f")
    hot = QLinearGradient(112, 0, 348, 0)
    hot.setColorAt(0, QColor(CYAN))
    hot.setColorAt(1, QColor(VIOLET))
    for x, y, w, is_hot in _BARS:
        painter.setPen(Qt.NoPen)
        painter.setBrush(gap)
        painter.drawRoundedRect(QRectF(x - 5, y - 5, w + 10, 27), 13.5, 13.5)
        under = x <= head_x <= x + w
        painter.setBrush(QBrush(hot) if is_hot else QColor("#ffffff" if under else "#c9cbe0"))
        painter.drawRoundedRect(QRectF(x, y, w, 17), 8.5, 8.5)
        if is_hot and under:
            painter.setBrush(QColor(255, 255, 255, 60))
            painter.drawRoundedRect(QRectF(x, y, w, 17), 8.5, 8.5)
    painter.setBrush(gap)
    painter.drawRoundedRect(QRectF(head_x - 5, 176, 10, 150), 5, 5)
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(QRectF(head_x - 3, 180, 6, 142), 3, 3)
    painter.setPen(QPen(gap, 5))
    painter.drawEllipse(QPointF(head_x, 174), 11, 11)
    painter.restore()


def animated_mark_widget(size, parent=None):
    """A widget showing the animated mark; it only animates while visible."""
    import time
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QWidget

    class AnimatedMark(QWidget):
        def __init__(self):
            super().__init__(parent)
            self.setFixedSize(size, size)
            self._t0 = time.monotonic()
            self._timer = QTimer(self)
            self._timer.setInterval(16)
            self._timer.timeout.connect(self.update)

        def showEvent(self, e):
            self._t0 = time.monotonic()
            self._timer.start()
            super().showEvent(e)

        def hideEvent(self, e):
            self._timer.stop()
            super().hideEvent(e)

        def paintEvent(self, e):
            p = QPainter(self)
            draw_mark_animated(p, QRectF(0, 0, self.width(), self.height()), time.monotonic() - self._t0)
            p.end()

    return AnimatedMark()
