#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: labels.py
ROLE: GUI Widget
DESCRIPTION:
Custom text label widgets.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config
from gui.vsync import get_refresh_interval_ms

# Aliases for original standard classes we override
_QPushButton = QPushButton
_QLabel = QLabel
_QRadioButton = QRadioButton

class QLabel(_QLabel):
    """Patched QLabel — shows a smooth marquee on hover whenever its text is wider
    than the label's display area (single-line labels only; wordWrap ignored)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_scroll)
        self._mq_timer.setInterval(get_refresh_interval_ms())
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_state = "START_DELAY"
        self.setMouseTracking(True)

    def _get_text_color(self):
        if hasattr(self, '_custom_color') and self._custom_color:
            return QColor(self._custom_color)
        ss = self.styleSheet()
        if 'color:' in ss:
            import re
            m = re.search(r'color:\s*([^;]+);', ss)
            if m:
                c = QColor(m.group(1).strip())
                if c.isValid() and c != QColor("#000000"):
                    return c
        return QColor("#ffffff")

    def _mq_get_text(self):
        t = super().text()
        # Strip HTML tags for advance measurement
        import re as _re
        return _re.sub(r'<[^>]+>', '', t)

    def _mq_active(self):
        """Only run marquee for single-line, non-wrapping labels with enough text."""
        if self.wordWrap():
            return False
        t = self._mq_get_text()
        return bool(t) and len(t.strip()) > 3

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self._mq_active():
            return
        self._mq_hovered = True
        try:
            fm = self.fontMetrics()
            avail = self.contentsRect().width()
            if fm.horizontalAdvance(self._mq_get_text()) > avail:
                self._mq_is_squeezed = True
                self._mq_pos = 0.0
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
                self._mq_timer.start()
            else:
                self._mq_is_squeezed = False
        except Exception:
            pass

    def leaveEvent(self, event):
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_timer.stop()
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self.update()
        super().leaveEvent(event)

    def _mq_scroll(self):
        fm = self.fontMetrics()
        avail = self.contentsRect().width()
        text = self._mq_get_text()
        max_scroll = float(max(0, fm.horizontalAdvance(text) - avail))

        iv = max(1, self._mq_timer.interval())
        delay_threshold = int(round(640 / iv))
        scroll_step = 31.25 * (iv / 1000.0)
        fade_step = 0.05 * (iv / 16.0)

        if self._mq_state == "START_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > delay_threshold:
                self._mq_state = "SCROLL"
                self._mq_ticks = 0
        elif self._mq_state == "SCROLL":
            self._mq_pos += scroll_step
            if self._mq_pos >= max_scroll:
                self._mq_pos = max_scroll
                self._mq_state = "END_DELAY"
                self._mq_ticks = 0
        elif self._mq_state == "END_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > delay_threshold:
                self._mq_state = "FADEOUT"
                self._mq_ticks = 0
        elif self._mq_state == "FADEOUT":
            self._mq_alpha -= fade_step
            if self._mq_alpha <= 0.0:
                self._mq_alpha = 0.0
                self._mq_pos = 0.0
                self._mq_state = "FADEIN"
        elif self._mq_state == "FADEIN":
            self._mq_alpha += fade_step
            if self._mq_alpha >= 1.0:
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
        self.update()

    def paintEvent(self, event):
        if not self._mq_hovered or not self._mq_is_squeezed:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        cr = self.contentsRect()
        painter.setClipRect(cr)

        if self._mq_alpha < 1.0:
            painter.setOpacity(max(0.0, min(1.0, self._mq_alpha)))

        raw_text = super().text()
        if "<" in raw_text and ">" in raw_text:
            from PySide6.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setDefaultFont(self.font())
            color_name = self.palette().windowText().color().name()
            doc.setHtml(f"<div style='color: {color_name};'>{raw_text}</div>")
            doc.setDocumentMargin(0)
            
            y_pos = cr.top() + (cr.height() - doc.size().height()) / 2
            painter.translate(cr.left() - int(self._mq_pos), y_pos)
            doc.drawContents(painter)
        else:
            color = self.palette().windowText().color()
            painter.setPen(color)
            painter.setFont(self.font())
            text = self._mq_get_text()
            draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
            painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

class IDETooltip(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWordWrap(True)
        self.pad_v = config.S(5)
        self.pad_h = config.S(7)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: {config.S(4)}px;
                padding: {self.pad_v}px {self.pad_h}px;
                font-family: '{config.UI_FONT_NAME}', sans-serif;
                font-size: 9pt;
            }}
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def prepare_content(self, text: str):
        import re
        if not text:
            self.setText("")
            self.setFixedWidth(config.S(100))
            self.adjustSize()
            return

        # 1. Explicit raw formatting override (<!-- raw --> or <raw width=...>)
        raw_match = re.match(
            r'^\s*(?:<!--\s*raw(?:\s+width=(\d+))?\s*-->|<raw(?:\s+width=(\d+))?>)(.*?)(?:</raw>)?$',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
        if raw_match:
            custom_w = raw_match.group(1) or raw_match.group(2)
            content = raw_match.group(3).strip()
            target_w = config.S(int(custom_w)) if custom_w else config.S(400)
            self.setFixedWidth(target_w)
            self.setText(content)
            self.adjustSize()
            return

        # 2. Clean input
        clean_input = text.strip()
        outer_div_match = re.match(r'^<div\s+style=[\'"][^\'"]*[\'"]>(.*)</div>$', clean_input, flags=re.DOTALL | re.IGNORECASE)
        if outer_div_match:
            clean_input = outer_div_match.group(1).strip()

        t = clean_input.replace('\r\n', '\n').replace('\r', '\n')
        t = re.sub(r'</p>\s*<p[^>]*>', '\n\n', t, flags=re.IGNORECASE)
        t = re.sub(r'</?p[^>]*>', '\n\n', t, flags=re.IGNORECASE)
        t = re.sub(r'(?:<br\s*/?>\s*){2,}', '\n\n', t, flags=re.IGNORECASE)
        raw_paras = [p.strip() for p in re.split(r'\n\s*\n+', t) if p.strip()]

        cleaned_paras = []
        total_plain_chars = 0
        for p in raw_paras:
            # Detect bullet list lines separated by either \n or <br>
            p_lines = [l.strip() for l in re.split(r'(?:<br\s*/?>|\n)', p) if l.strip()]
            is_bullet_list = any(l.startswith(('-', '•', '*')) for l in p_lines)
            if is_bullet_list:
                cleaned_lines = [re.sub(r'\s+', ' ', l).strip() for l in p_lines]
                p_clean = '<br>'.join(cleaned_lines)
            else:
                p_sub = re.sub(r'<br\s*/?>', ' ', p, flags=re.IGNORECASE)
                p_clean = re.sub(r'\s+', ' ', p_sub).strip()
            plain_len = len(re.sub(r'<[^>]+>', '', p_clean))
            cleaned_paras.append(p_clean)
            total_plain_chars += plain_len

        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setDocumentMargin(0)

        # Using <br><br> between paragraphs ensures even top/bottom padding without block-level div inflation
        full_html = '<br><br>'.join(cleaned_paras)
        doc.setHtml(full_html)

        pad = 2 * self.pad_h + 4
        ideal_w = doc.idealWidth()

        max_w_wide = config.S(540)
        max_w_normal = config.S(400)

        if len(cleaned_paras) == 1:
            if ideal_w + pad <= max_w_wide:
                target_w = int(ideal_w) + pad
            elif total_plain_chars <= 140:
                target_w = min(max_w_wide, config.S(480))
            else:
                target_w = max_w_normal
        else:
            if ideal_w + pad <= max_w_normal:
                target_w = int(ideal_w) + pad
            else:
                target_w = max_w_normal

        self.setFixedWidth(target_w)
        self.setText(full_html)
        self.adjustSize()

    def show_at(self, widget, text, is_right_side=False):
        self.prepare_content(text)
        self.show_beside(widget, is_right_side=is_right_side)

    def show_beside(self, widget, is_right_side=False):
        rect = widget.rect()
        global_pos = widget.mapToGlobal(rect.topLeft())

        if not is_right_side:
            x = global_pos.x() + rect.width() + 5
        else:
            x = global_pos.x() - self.width() - 5

        y = global_pos.y() + (rect.height() - self.height()) // 2
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        if x + self.width() > screen.right() - 10:
            x = max(10, screen.right() - self.width() - 10)
        if y + self.height() > screen.bottom() - 10:
            y = max(10, screen.bottom() - self.height() - 10)
        if y < screen.top() + 10:
            y = screen.top() + 10
        self.move(x, y)
        self.show()

    def show_global(self, text, pos):
        self.prepare_content(text)
        x = pos.x()
        y = pos.y() + 15
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        if x + self.width() > screen.right() - 10:
            x = max(10, screen.right() - self.width() - 10)
        if y + self.height() > screen.bottom() - 10:
            y = max(10, pos.y() - self.height() - 10)
        if y < screen.top() + 10:
            y = screen.top() + 10
        self.move(x, y)
        self.show()

class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self._mq_timer = QTimer(self)
        self._mq_timer.setInterval(get_refresh_interval_ms())
        self._mq_timer.timeout.connect(self._scroll_step)
        self._mq_pos = 0.0
        self._hovered = False
        self.setMouseTracking(True)
        self.setStyleSheet("color: #d4d4d4; font-size: 9.5pt;")

    def setText(self, text):
        self._full_text = text
        self._mq_pos = 0.0
        super().setText(text)
        self.update()

    def text(self):
        return self._full_text

    def enterEvent(self, event):
        self._hovered = True
        if self._is_truncated():
            self._mq_timer.setInterval(get_refresh_interval_ms())
            self._mq_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._mq_timer.stop()
        self._mq_pos = 0.0
        self.update()
        super().leaveEvent(event)

    def _is_truncated(self):
        fm = self.fontMetrics()
        return fm.horizontalAdvance(self._full_text) > self.width()

    def _scroll_step(self):
        fm = self.fontMetrics()
        txt_w = fm.horizontalAdvance(self._full_text)
        iv = max(1, self._mq_timer.interval())
        step = 48.0 * (iv / 1000.0)
        self._mq_pos += step
        if self._mq_pos > txt_w + 20:
            self._mq_pos = -self.width()
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        from PySide6.QtCore import Qt

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fm = self.fontMetrics()

        if self._hovered and self._is_truncated() and self._mq_timer.isActive():
            p.setPen(QColor("#ffffff"))
            p.drawText(int(-self._mq_pos), fm.ascent() + (self.height() - fm.height()) // 2, self._full_text)
        else:
            elided = fm.elidedText(self._full_text, Qt.ElideRight, max(1, self.width()))
            p.setPen(QColor("#d4d4d4"))
            p.drawText(0, fm.ascent() + (self.height() - fm.height()) // 2, elided)
