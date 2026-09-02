#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: buttons.py
ROLE: GUI Widget
DESCRIPTION:
Custom button widgets tailored for the application interface.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config
from i18n import get_trans
import sys
import os

# Aliases for original standard classes we override
_QPushButton = QPushButton
_QLabel = QLabel
_QRadioButton = QRadioButton

class QPushButton(_QPushButton):
    """Patched QPushButton to support smooth marquee (scroll) effect on hover when text is squeezed."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_scroll)
        self._mq_timer.setInterval(16)  # ~60fps smooth scroll
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_state = "START_DELAY"
        self._mq_ticks = 0

    def setText(self, str_text):
        self.setProperty("_mq_original_text", str_text)
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        super().setText(str_text)

    def text(self):
        orig = self.property("_mq_original_text")
        if orig is not None:
            return orig
        return super().text()

    def _mq_text_area_width(self):
        """Returns the pixel width actually available for text rendering,
        derived from the widget's contentsRect (excludes QSS padding/margins)."""
        w = self.contentsRect().width()
        if not self.icon().isNull():
            w = max(0, w - self.iconSize().width() - 4)
        return w

    def enterEvent(self, event):
        super().enterEvent(event)
        orig = self.property("_mq_original_text")
        if orig is None:
            orig = super().text()
            self.setProperty("_mq_original_text", orig)

        self._mq_hovered = True
        try:
            if not orig or len(orig.strip()) <= 1:
                self._mq_is_squeezed = False
                return
            fm = self.fontMetrics()
            avail = self._mq_text_area_width()
            if avail > 0 and fm.horizontalAdvance(orig) > avail:
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
        orig = self.property("_mq_original_text")
        if not orig: return
        fm = self.fontMetrics()
        clip_w = self._mq_text_area_width()
        max_scroll = float(max(0, fm.horizontalAdvance(orig) - clip_w))

        if self._mq_state == "START_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:  # ~640ms
                self._mq_state = "SCROLL"
                self._mq_ticks = 0
        elif self._mq_state == "SCROLL":
            self._mq_pos += 0.5
            if self._mq_pos >= max_scroll:
                self._mq_pos = max_scroll
                self._mq_state = "END_DELAY"
                self._mq_ticks = 0
        elif self._mq_state == "END_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:
                self._mq_state = "FADEOUT"
                self._mq_ticks = 0
        elif self._mq_state == "FADEOUT":
            self._mq_alpha -= 0.05
            if self._mq_alpha <= 0.0:
                self._mq_alpha = 0.0
                self._mq_pos = 0.0
                self._mq_state = "FADEIN"
        elif self._mq_state == "FADEIN":
            self._mq_alpha += 0.05
            if self._mq_alpha >= 1.0:
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
        self.update()

    def paintEvent(self, event):
        if not self._mq_hovered or not self._mq_is_squeezed:
            super().paintEvent(event)
            return

        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        orig = self.property("_mq_original_text") or super().text() or ""
        opt.text = ""  # Hide native text to draw our own
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        self.style().drawControl(QStyle.CE_PushButton, opt, painter, self)

        cr = self.contentsRect()
        if not self.icon().isNull():
            icon_w = self.iconSize().width()
            cr.setLeft(cr.left() + icon_w + 4)
        painter.setClipRect(cr)

        color = opt.palette.buttonText().color()
        ss = self.styleSheet() or ""
        if "color:" in ss:
            import re
            m = re.search(r'(?:^|[;{])\s*color:\s*([^;!}]+)', ss)
            if m:
                qc = QColor(m.group(1).strip())
                if qc.isValid():
                    color = qc
        if color.name() == "#000000" or color.lightness() < 40:
            color = QColor(config.FG_COLOR)

        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))
        painter.setPen(color)
        painter.setFont(self.font())
        draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, orig)

class MarqueeRadioButton(_QRadioButton):
    """QRadioButton with smooth marquee (scroll) effect on hover when text is truncated.
    Uses QStyle.SE_RadioButtonContents to get the exact text rect Qt uses internally."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_scroll)
        self._mq_timer.setInterval(16)
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_state = "START_DELAY"
        self._mq_ticks = 0
        self._mq_original_text = None

    def setText(self, txt):
        self._mq_original_text = txt
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        super().setText(txt)

    def text(self):
        if self._mq_original_text is not None:
            return self._mq_original_text
        return super().text()

    def _mq_text_rect(self):
        """Returns the exact QRect where Qt would render the radio button text.
        Uses the style's SE_RadioButtonContents sub-element — 100% accurate,
        no magic offset constants, works with any style/DPI/font."""
        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        return self.style().subElementRect(QStyle.SE_RadioButtonContents, opt, self)

    def enterEvent(self, event):
        super().enterEvent(event)
        orig = self._mq_original_text
        if orig is None:
            orig = super().text()
            self._mq_original_text = orig

        self._mq_hovered = True
        try:
            if not orig or len(orig.strip()) <= 3:
                self._mq_is_squeezed = False
                return
            fm = self.fontMetrics()
            if fm.horizontalAdvance(orig) > self._mq_text_rect().width():
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
        orig = self._mq_original_text
        if not orig:
            return
        fm = self.fontMetrics()
        tr = self._mq_text_rect()
        max_scroll = float(max(0, fm.horizontalAdvance(orig) - tr.width()))

        if self._mq_state == "START_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:
                self._mq_state = "SCROLL"
                self._mq_ticks = 0
        elif self._mq_state == "SCROLL":
            self._mq_pos += 0.5
            if self._mq_pos >= max_scroll:
                self._mq_pos = max_scroll
                self._mq_state = "END_DELAY"
                self._mq_ticks = 0
        elif self._mq_state == "END_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:
                self._mq_state = "FADEOUT"
                self._mq_ticks = 0
        elif self._mq_state == "FADEOUT":
            self._mq_alpha -= 0.05
            if self._mq_alpha <= 0.0:
                self._mq_alpha = 0.0
                self._mq_pos = 0.0
                self._mq_state = "FADEIN"
        elif self._mq_state == "FADEIN":
            self._mq_alpha += 0.05
            if self._mq_alpha >= 1.0:
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
        self.update()

    def paintEvent(self, event):
        if not self._mq_hovered or not self._mq_is_squeezed:
            super().paintEvent(event)
            return

        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ""
        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_RadioButton, opt, painter, self)

        tr = self._mq_text_rect()
        painter.setClipRect(tr)

        color = opt.palette.buttonText().color()
        if color.name() == "#000000" or color.lightness() < 40:
            color = QColor(config.FG_COLOR)
        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))
        painter.setPen(color)
        painter.setFont(self.font())
        draw_rect = QRect(tr.left() - int(self._mq_pos), tr.top(), 9999, tr.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, self._mq_original_text or "")
class ReloadButton(QPushButton):
    """Button displaying reload.svg with hover effect (reload-hover.svg), perfectly centered."""
    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._btn_size = config.S(size)
        # 10% smaller icon inside the same button size
        self._icon_size = max(config.S(10), int(self._btn_size * 0.44))
        self.setFixedSize(self._btn_size, self._btn_size)
        
        from ..utils import get_layout_icon_path
        self._icon_normal = QIcon(get_layout_icon_path("reload.svg"))
        self._icon_hover = QIcon(get_layout_icon_path("reload-hover.svg"))
        
        self.setIcon(self._icon_normal)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid #444444;
                border-radius: {config.S(3)}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #2a2d2e;
                border-color: #666666;
            }}
            QPushButton:pressed {{
                background-color: #1a1a1a;
                border-color: #333333;
            }}
        """)

    def enterEvent(self, event):
        self.setIcon(self._icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._icon_normal)
        super().leaveEvent(event)


class StarFavoriteButton(QPushButton):
    """Button displaying star icons (star-empty, star-checked, star-hover) with NO border box."""
    def __init__(self, size: int = 18, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._btn_size = config.S(size)
        self._icon_size = max(config.S(10), int(self._btn_size * 0.65))
        self.setFixedSize(self._btn_size, self._btn_size)
        
        from ..utils import get_layout_icon_path
        self._icon_empty = QIcon(get_layout_icon_path("star-empty.svg"))
        self._icon_hover = QIcon(get_layout_icon_path("star-hover.svg"))
        self._icon_checked = QIcon(get_layout_icon_path("star-checked.svg"))
        
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: transparent;
                border: none;
            }
            QPushButton:pressed {
                background-color: transparent;
                border: none;
            }
        """)
        self.toggled.connect(self._update_icon)
        self._update_icon()

    def _update_icon(self):
        if self.isChecked():
            self.setIcon(self._icon_checked)
        else:
            self.setIcon(self._icon_empty)

    def enterEvent(self, event):
        if not self.isChecked():
            self.setIcon(self._icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_icon()
        super().leaveEvent(event)


class CloseIconButton(QPushButton):
    """Button displaying x.svg with hover effect (x-hover.svg) and standard border."""
    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._btn_size = config.S(size)
        self._icon_size = max(config.S(9), int(self._btn_size * 0.42))
        self.setFixedSize(self._btn_size, self._btn_size)
        
        from ..utils import get_layout_icon_path
        self._icon_normal = QIcon(get_layout_icon_path("x.svg"))
        self._icon_hover = QIcon(get_layout_icon_path("x-hover.svg"))
        
        self.setIcon(self._icon_normal)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid #444444;
                border-radius: {config.S(3)}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #2a2d2e;
                border-color: #666666;
            }}
            QPushButton:pressed {{
                background-color: #1a1a1a;
                border-color: #333333;
            }}
        """)

    def enterEvent(self, event):
        self.setIcon(self._icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._icon_normal)
        super().leaveEvent(event)


class SquareIconButton(QPushButton):
    """
    App icon button in Settings General tab.
    Maintains a 1:1 aspect ratio on any resolution, filling available space,
    with no green border and larger icon size.
    """
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.icon_name = name
        self.setProperty("icon_name", name)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        import os
        from gui.utils import get_icon_path
        icon_path = get_icon_path(name)
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            
        self.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                border: none; 
                border-radius: {config.S(6)}px; 
                padding: {config.S(2)}px; 
            }}
            QPushButton:hover {{ 
                background-color: #262626; 
                border: none; 
            }}
            QPushButton:checked {{ 
                background-color: #383838; 
                border: none; 
            }}
            QPushButton:checked:hover {{ 
                background-color: #424242; 
                border: none; 
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w > 20:
            if self.height() != w:
                self.setFixedHeight(w)
            icon_s = max(16, w - config.S(12))
            self.setIconSize(QSize(icon_s, icon_s))


class CustomNumberInput(QWidget):
    """
    Sleek, unified number input replacing standard QSpinBox and QDoubleSpinBox.
    - Exactly config.INPUT_HEIGHT (30px)
    - Clean typography (Ubuntu Sans)
    - Dark theme (#1e1e1e, border #3a3a3a, focus green border)
    - Left-aligned text
    - Supports int and float (with decimals/step)
    - Supports keyboard typing, mouse wheel scrolling, and Up/Down keys
    - No ugly native stepper arrows!
    """
    valueChanged = Signal(object)

    def __init__(self, val=0, min_val=0, max_val=100, step=1, decimals=0, suffix="", prefix="", parent=None):
        super().__init__(parent)
        self._decimals = decimals
        self._is_float = decimals > 0 or isinstance(val, float) or isinstance(step, float)
        self._step = float(step) if self._is_float else int(step)
        self._min_val = float(min_val) if self._is_float else int(min_val)
        self._max_val = float(max_val) if self._is_float else int(max_val)
        self._suffix = suffix
        self._prefix = prefix
        
        parsed_val = float(val) if self._is_float else int(val)
        self._val = max(self._min_val, min(self._max_val, parsed_val))
        
        self.setFixedHeight(config.INPUT_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._edit = QLineEdit(self._format_display(self._val), self)
        self._edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._edit.setFixedHeight(config.INPUT_HEIGHT)
        self._edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px;
                padding: 0px {config.S(8)}px;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QLineEdit:focus {{
                border-color: {config.BTN_BG};
            }}
        """)
        self._edit.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self._edit)

    def _format_display(self, v) -> str:
        if self._is_float:
            dec = self._decimals if self._decimals > 0 else 2
            formatted = f"{float(v):.{dec}f}"
        else:
            formatted = str(int(round(v)))
        return f"{self._prefix}{formatted}{self._suffix}"

    def _parse_input(self, text: str):
        cleaned = text.strip()
        if self._prefix and cleaned.startswith(self._prefix):
            cleaned = cleaned[len(self._prefix):].strip()
        if self._suffix and cleaned.endswith(self._suffix):
            cleaned = cleaned[:-len(self._suffix)].strip()
        try:
            return float(cleaned) if self._is_float else int(round(float(cleaned)))
        except ValueError:
            return self._val

    def _on_editing_finished(self):
        val = self._parse_input(self._edit.text())
        val = max(self._min_val, min(self._max_val, val))
        self.setValue(val)

    def value(self):
        return float(self._val) if self._is_float else int(round(self._val))

    def setValue(self, v):
        parsed = float(v) if self._is_float else int(round(float(v)))
        v = max(self._min_val, min(self._max_val, parsed))
        changed = (abs(self._val - v) > 1e-6 if self._is_float else self._val != v)
        self._val = v
        formatted = self._format_display(v)
        if self._edit.text() != formatted:
            self._edit.setText(formatted)
        if changed:
            self.valueChanged.emit(self.value())

    def setRange(self, min_v, max_v):
        self._min_val = float(min_v) if self._is_float else int(min_v)
        self._max_val = float(max_v) if self._is_float else int(max_v)
        self.setValue(self._val)

    def setSingleStep(self, step):
        self._step = float(step) if self._is_float else int(step)

    def setDecimals(self, decimals: int):
        self._decimals = decimals
        if decimals > 0:
            self._is_float = True
        self.setValue(self._val)

    def setSuffix(self, suffix: str):
        self._suffix = suffix
        self._edit.setText(self._format_display(self._val))

    def setPrefix(self, prefix: str):
        self._prefix = prefix
        self._edit.setText(self._format_display(self._val))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.setValue(self._val + self._step)
        elif delta < 0:
            self.setValue(self._val - self._step)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.setValue(self._val + self._step)
            event.accept()
        elif event.key() == Qt.Key_Down:
            self.setValue(self._val - self._step)
            event.accept()
        else:
            super().keyPressEvent(event)


class ToggleSwitch(QWidget):
    """
    iOS-style animated toggle switch inheriting from QWidget.
    """
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(config.S(36), config.S(20))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_checked = False

        # Internal animation states
        self._thumb_x = float(config.S(2))
        self._bg_color = QColor("#555555")
        
        # Animators
        self._anim_group = QPropertyAnimation(self, b"thumb_x", self)
        self._anim_group.setDuration(150)
        
        self._color_anim = QPropertyAnimation(self, b"bg_color", self)
        self._color_anim.setDuration(150)

    @Property(float)
    def thumb_x(self):
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, value):
        self._thumb_x = value
        self.update()
        
    @Property(QColor)
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = value
        self.update()

    def isChecked(self) -> bool:
        return self._is_checked

    def setChecked(self, checked: bool, animated: bool = True):
        if self._is_checked == checked:
            return
        self._is_checked = checked

        if animated:
            self._update_animation()
        else:
            self._bg_color = QColor("#1ed760") if checked else QColor("#555555")
            thumb_size = config.S(16)
            self._thumb_x = float(self.width() - thumb_size - config.S(2)) if checked else float(config.S(2))
            self.update()
        
        self.toggled.emit(self._is_checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_checked = not self._is_checked
            self._update_animation()
            self.toggled.emit(self._is_checked)
        super().mouseReleaseEvent(event)

    def _update_animation(self):
        self._anim_group.stop()
        self._color_anim.stop()
        
        thumb_size = config.S(16)
        end_x = float(self.width() - thumb_size - config.S(2)) if self._is_checked else float(config.S(2))
        end_color = QColor("#1ed760") if self._is_checked else QColor("#555555")
        
        self._anim_group.setStartValue(self._thumb_x)
        self._anim_group.setEndValue(float(end_x))
        
        self._color_anim.setStartValue(self._bg_color)
        self._color_anim.setEndValue(end_color)
        
        self._anim_group.start()
        self._color_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Draw background capsule
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_color)
        rect = QRect(0, 0, self.width(), self.height())
        p.drawRoundedRect(rect, config.S(10), config.S(10))
        
        # Draw white thumb
        p.setBrush(QColor("white"))
        thumb_size = config.S(16)
        thumb_rect = QRect(int(self._thumb_x), config.S(2), thumb_size, thumb_size)
        p.drawEllipse(thumb_rect)

class ShortcutCaptureButton(QPushButton):
    """
    Key-capture widget that visually matches standard inputs.
    - Idle:      dark background (#1e1e1e), subtle border (#3a3a3a)
    - Listening: same background, green border (#23a559), text = "..."
    - Conflict:  red border (#ed4245) while another button has the same sequence
    - Uses native keyPressEvent to reliably capture single keys and combos.
    - Focus loss reverts to previous sequence without clearing.
    """
    sequence_changed = Signal(str)

    _BASE_SS = """
        QPushButton {{
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid {border};
            border-radius: {radius}px;
            padding: 0px {pad_x}px;
            min-height: {h}px;
            max-height: {h}px;
            text-align: center;
            font-family: monospace;
            font-size: {font_size}pt;
        }}
        QPushButton:hover {{
            background-color: #252525;
        }}
    """

    def __init__(self, current_sequence, display_only=False, parent=None):
        super().__init__(parent)
        self.current_seq = current_sequence or ""
        self.capturing = False
        self.display_only = display_only
        self._conflict = False

        self.setCursor(Qt.PointingHandCursor if not display_only else Qt.ArrowCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMaximumWidth(config.S(220))
        self.setMinimumWidth(config.S(60))
        self.setFixedHeight(config.INPUT_HEIGHT)
        self._apply_style()
        self._update_label()

        if not display_only:
            self.clicked.connect(self.start_capture)

    def _apply_style(self):
        if self._conflict:
            border = "#ed4245"
        elif self.capturing:
            border = "#23a559"
        else:
            border = "#3a3a3a"
        pad_x = config.S(8)
        self.setStyleSheet(self._BASE_SS.format(
            border=border,
            radius=config.S(3),
            pad_x=pad_x,
            h=config.INPUT_HEIGHT - 2,
            font_size=config.FS(9.5)
        ))
        self.setMaximumWidth(config.S(220))
        self.setMinimumWidth(config.S(60))
        self.setFixedHeight(config.INPUT_HEIGHT)

    def _update_label(self):
        if self.display_only:
            self.setText(self.current_seq if self.current_seq else "—")
        else:
            if self.capturing:
                self.setText("...")
            else:
                self.setText(self.current_seq if self.current_seq else "(none)")

    def start_capture(self):
        if self.display_only:
            return
        self.capturing = True
        self._conflict = False
        self._apply_style()
        self._update_label()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self.capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        # Ignore modifiers if pressed alone
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_unknown):
            return

        from PySide6.QtGui import QKeySequence
        # Qt6-safe way to get the combination of modifiers and key
        combo = event.keyCombination()
        seq = QKeySequence(combo).toString(QKeySequence.PortableText)
        
        self.current_seq = seq
        self.capturing = False
        self._apply_style()
        self._update_label()
        self.clearFocus()
        self.sequence_changed.emit(seq)

    def focusOutEvent(self, event):
        if self.capturing:
            # Revert to old sequence on cancel
            self.capturing = False
            self._apply_style()
            self._update_label()
        super().focusOutEvent(event)

    def get_sequence(self) -> str:
        return self.current_seq

    def set_sequence(self, seq: str):
        self.current_seq = seq or ""
        self._update_label()

    def set_conflict(self, conflict: bool):
        if self._conflict != conflict:
            self._conflict = conflict
            if not self.capturing:
                self._apply_style()

class MouseShortcutCaptureButton(ShortcutCaptureButton):
    def __init__(self, current_sequence, key_map, display_only=False, parent=None):
        self.key_map = key_map
        super().__init__(current_sequence, display_only, parent)

    def _update_label(self):
        if self.display_only:
            self.setText(self.key_map.get(self.current_seq, self.current_seq) if self.current_seq else "—")
        else:
            if self.capturing:
                self.setText("...")
            else:
                self.setText(self.key_map.get(self.current_seq, self.current_seq) if self.current_seq else "(none)")

    def mousePressEvent(self, event):
        from PySide6.QtCore import Qt
        if not self.capturing:
            super().mousePressEvent(event)
            return

        mods = event.modifiers()
        btn = event.button()

        mod_str = None
        if mods & Qt.KeyboardModifier.ControlModifier:
            mod_str = "opt_ctrl"
        elif mods & Qt.KeyboardModifier.AltModifier:
            mod_str = "opt_alt"
        elif mods & Qt.KeyboardModifier.ShiftModifier:
            mod_str = "opt_shift"

        btn_str = None
        if btn == Qt.LeftButton:
            btn_str = "lmb"
        elif btn == Qt.RightButton:
            btn_str = "rmb"

        if mod_str and btn_str:
            seq = f"{mod_str}_{btn_str}"
            if seq in self.key_map:
                self.current_seq = seq
                self.capturing = False
                self._apply_style()
                self._update_label()
                self.clearFocus()
                self.sequence_changed.emit(seq)

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt
        if not self.capturing:
            super().keyPressEvent(event)
            return
            
        if event.key() == Qt.Key_Escape:
            self.capturing = False
            self._apply_style()
            self._update_label()
            self.clearFocus()

class AnimatedPlayerButton(QPushButton):
    def __init__(self, icon_name, button_size=32, icon_size=24, parent=None):
        super().__init__(parent)
        from PySide6.QtCore import QSize, QPropertyAnimation
        
        self.base_icon_size = icon_size
        self.setFixedSize(button_size, button_size)
        self.setIconSize(QSize(icon_size, icon_size))
        
        self._anim = QPropertyAnimation(self, b"iconSize")
        self._anim.setDuration(100)
        
        self.update_icon(icon_name)

    def update_icon(self, icon_name):
        from PySide6.QtGui import QIcon
        from ..utils import get_layout_icon_path
        path = get_layout_icon_path(icon_name)
        
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(self.base_icon_size * 2, self.base_icon_size * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setIcon(QIcon(pix))
        else:
            self.setIcon(QIcon(path))

    def mousePressEvent(self, e):
        from PySide6.QtCore import QSize
        self._anim.stop()
        self._anim.setEndValue(QSize(int(self.base_icon_size * 0.75), int(self.base_icon_size * 0.75)))
        self._anim.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        from PySide6.QtCore import QSize
        self._anim.stop()
        self._anim.setEndValue(QSize(self.base_icon_size, self.base_icon_size))
        self._anim.start()
        super().mouseReleaseEvent(e)

class AudioToggleTab(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.hovered = False
        self.setFixedHeight(16)
        self.setFixedWidth(130)
        from PySide6.QtCore import Qt
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("background: transparent; border: none;")

    def set_collapsed(self, collapsed: bool):
        if self.is_collapsed != collapsed:
            self.is_collapsed = collapsed
            self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QBrush
        from PySide6.QtCore import Qt, QPointF
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        w = float(self.width())
        h = float(self.height())
        
        # Smooth trapezoid path with sloped, curved sides
        path = QPainterPath()
        path.moveTo(0.0, h)
        path.cubicTo(12.0, h, 15.0, 0.0, 25.0, 0.0)
        path.lineTo(w - 25.0, 0.0)
        path.cubicTo(w - 15.0, 0.0, w - 12.0, h, w, h)
        path.closeSubpath()
        
        # Fill matches the player background (#191919) seamlessly! Hover gives subtle highlight.
        bg_col = QColor("#262626") if self.hovered else QColor("#191919")
        border_col = QColor("#444444") if self.hovered else QColor("#2a2a2a")
        
        p.fillPath(path, QBrush(bg_col))
        
        # Top & side border outline (if collapsed, close bottom edge for floating tab look)
        border_path = QPainterPath()
        border_path.moveTo(0.5, h)
        border_path.cubicTo(12.0, h - 0.5, 15.0, 0.5, 25.0, 0.5)
        border_path.lineTo(w - 25.0, 0.5)
        border_path.cubicTo(w - 15.0, 0.5, w - 12.0, h - 0.5, w - 0.5, h)
        if self.is_collapsed:
            border_path.lineTo(0.5, h)
        
        p.setPen(QPen(border_col, 1.0))
        p.drawPath(border_path)
        
        cx = w / 2.0
        cy = h / 2.0
        
        chevron_col = QColor("#ffffff") if self.hovered else QColor("#999999")
        pen_chevron = QPen(chevron_col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen_chevron)
        
        half_w = 5.0
        offset_y = 2.5
        
        if self.is_collapsed:
            # Arrow pointing UP (▲)
            p.drawLine(QPointF(cx - half_w, cy + offset_y - 0.5), QPointF(cx, cy - offset_y - 0.5))
            p.drawLine(QPointF(cx, cy - offset_y - 0.5), QPointF(cx + half_w, cy + offset_y - 0.5))
        else:
            # Arrow pointing DOWN (▼)
            p.drawLine(QPointF(cx - half_w, cy - offset_y + 0.5), QPointF(cx, cy + offset_y + 0.5))
            p.drawLine(QPointF(cx, cy + offset_y + 0.5), QPointF(cx + half_w, cy - offset_y + 0.5))

class SidebarButton(QPushButton):
    """
    Static sidebar item with a fixed 40x40 size and VS Code style static tooltip.
    Now draggable to allow panel repositioning.
    """
    def __init__(self, icon_text: str, label_text: str, activity_id: str, tooltip_widget=None, is_right_side: bool = False, is_draggable: bool = True, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        
        self.activity_id = activity_id
        
        image_name = ""
        if activity_id == "script_analysis":
            image_name = "script.png"
        elif activity_id == "silence":
            image_name = "silence.png"
        elif activity_id == "fillers":
            image_name = "fillers.png"
        elif activity_id == "main_panel":
            image_name = "main.png"
        elif activity_id == "assembly":
            image_name = "assembly.png"
        elif activity_id == "settings":
            image_name = "settings.png"
            
        from ..utils import get_layout_icon_path
        icon_path = get_layout_icon_path(image_name) if image_name else ""
        
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(config.S(24), config.S(24)))
        else:
            self.setText(icon_text)
        self.setFixedSize(config.S(40), config.S(40))
        self.setCursor(Qt.PointingHandCursor)
        self.custom_tooltip_text = label_text
        self.is_right_side = is_right_side
        self.is_draggable = is_draggable
        self.tooltip_widget = tooltip_widget
        self.drag_start_pos = None
        
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_tooltip)
        
        self.is_active = False
        self.set_active(False)

    def set_active(self, is_active: bool):
        self.is_active = is_active
        if is_active:
            border_css = "border-left" if self.is_right_side else "border-right"
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: {config.FS(16)}pt; 
                    background-color: #333333; 
                    border-radius: {config.S(4)}px;
                    border: none;
                    {border_css}: {config.S(2)}px solid {config.BTN_BG};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: {config.FS(16)}pt; 
                    background: transparent; 
                    border-radius: {config.S(4)}px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {config.BTN_GHOST_BG};
                }}
            """)

    def enterEvent(self, event):
        self.tooltip_timer.start(750)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.tooltip_timer.stop()
        if self.tooltip_widget:
            self.tooltip_widget.hide()
        super().leaveEvent(event)

    def _show_tooltip(self):
        if self.tooltip_widget:
            self.tooltip_widget.show_at(self, self.custom_tooltip_text, self.is_right_side)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_draggable: return
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QGuiApplication.styleHints().startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.activity_id)
        drag.setMimeData(mime)
        
        self._drag_was_active = self.is_active
        
        was_active = self.is_active
        if was_active:
            self.set_active(False)  # Temporarily remove active CSS (green border)
            self.style().polish(self) # Force CSS update
        
        btn_pixmap = self.grab() # Take the perfect 40x40 photo without border
        
        if was_active:
            self.set_active(True) # Restore state
            self.style().polish(self)
        
        if self.is_active:
            panel_widget = self.window().activities.get(self.activity_id)
            if panel_widget:
                panel_pixmap = panel_widget.grab()
                scaled_panel = panel_pixmap.scaledToWidth(160, Qt.SmoothTransformation)
                composite = QPixmap(scaled_panel.size())
                composite.fill(Qt.transparent)
                p = QPainter(composite)
                p.setOpacity(0.6)
                p.drawPixmap(0, 0, scaled_panel)
                p.setOpacity(1.0)
                p.drawPixmap(0, 0, btn_pixmap)
                p.end()
                drag.setPixmap(composite)
                drag.setHotSpot(event.position().toPoint())
            else:
                drag.setPixmap(btn_pixmap)
                drag.setHotSpot(event.position().toPoint())
        else:
            # Snapshot the button for the drag icon
            drag.setPixmap(btn_pixmap)
            drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        if self._drag_was_active and self.window() and hasattr(self.window(), "_toggle_activity"):
            self.window()._toggle_activity(self.activity_id)
            
        self.hide()
        drag.exec(Qt.MoveAction)
        self.show()

def _popup_scrollbar_css():
    return f"""
        QScrollBar:vertical {{
            background: {config.SCROLL_BG};
            width: {config.S(6)}px;
            border: none;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {config.SCROLL_FG};
            border-radius: {config.S(3)}px;
            min-height: {config.S(16)}px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {config.SCROLL_ACTIVE};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            height: 0px;
            background: none;
            border: none;
        }}
    """

class CustomDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None, options_getter=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.options_getter = options_getter
        self.max_visible_items = 5
        self.setText(self.txt("txt_select"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: {config.S(4)}px {config.S(8)}px;
                border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px;
                min-height: {config.S(20)}px;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        popup = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: {config.S(3)}px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        btn_h = self.height()
        btn_w = self.width()

        fake_header = QPushButton(self.text())
        fake_header.setFixedHeight(btn_h)
        fake_header.setCursor(Qt.PointingHandCursor)
        fake_header.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: {config.S(4)}px {config.S(8)}px;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                border-radius: 0px;
                min-height: {config.S(20)}px;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; background-color: #2a2d2e; }}
        """)
        fake_header.clicked.connect(popup.close)
        layout.addWidget(fake_header)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        from gui.widgets.delegates import MarqueeItemDelegate
        list_widget.setItemDelegate(MarqueeItemDelegate(list_widget))
        items = self.options_getter() if (hasattr(self, 'options_getter') and callable(self.options_getter)) else self.options_list
        list_widget.addItems(items)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                padding: 0px;
                margin: 0px;
                outline: none;
                background: transparent;
                color: #d4d4d4;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QListWidget::item {{
                padding: 0px {config.S(8)}px;
                min-height: {config.S(26)}px;
                height: {config.S(26)}px;
                border: none;
            }}
            QListWidget::item:selected {{ background-color: #333333; color: #ffffff; }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover {{ background-color: #333333; color: #ffffff; }}
            {_popup_scrollbar_css()}
        """)
        list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, popup))
        layout.addWidget(list_widget)
        
        row_h = config.S(26)
        display_count = min(self.max_visible_items, list_widget.count())
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        
        total_h = list_height + btn_h + 2
        popup.setFixedHeight(total_h)
        popup.setFixedWidth(btn_w)

        global_pos = self.mapToGlobal(QPoint(0, 0))
        popup.setGeometry(global_pos.x(), global_pos.y(), btn_w, total_h)
        popup.show()
        popup.move(global_pos)

    def setValue(self, text):
        self.setText(text)
        self.valueChanged.emit(text)

    def _on_item_clicked(self, item, popup):
        self.setValue(item.text())
        popup.close()

    def currentText(self):
        return self.text()

class TitleDropdown(CustomDropdown):
    def __init__(self, options_list, parent=None):
        super().__init__(options_list, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #aaaaaa;
                text-align: center;
                border: none;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(9)}pt;
                padding: {config.S(2)}px {config.S(6)}px;
            }}
            QPushButton:hover {{ color: #ffffff; }}
            QPushButton:pressed {{ background: transparent; color: #ffffff; }}
        """)

    def setText(self, text):
        # Always append the down arrow for the title drop down
        if text is None:
            text = ""
        clean_text = str(text).replace("  ▾", "")
        super().setText(f"{clean_text}  ▾")
        if getattr(self.window(), '_update_mac_chapter_menu', None):
            self.window()._update_mac_chapter_menu()

    def currentText(self):
        return super().currentText().replace("  ▾", "")

    def mousePressEvent(self, event):
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: {config.S(6)}px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        from gui.widgets.delegates import MarqueeItemDelegate
        list_widget.setItemDelegate(MarqueeItemDelegate(list_widget))
        list_widget.addItems(self.options_list)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                padding: 0px;
                margin: 0px;
                outline: none;
                background: transparent;
                color: #b0b0b0;
                font-size: {config.FS(9)}pt;
            }}
            QListWidget::item {{
                height: {config.S(26)}px;
                padding: 0px {config.S(8)}px;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: #171717;
                color: #1ed760;
                font-weight: bold;
            }}
            QListWidget::item:focus {{
                border: none;
                outline: none;
            }}
            QListWidget::item:hover {{
                background-color: #222222;
                color: #ffffff;
            }}
            QListWidget::item:selected:hover {{
                background-color: #171717;
                color: #1ed760;
            }}
            {_popup_scrollbar_css()}
        """)
        
        cur = self.currentText()
        for row in range(list_widget.count()):
            if list_widget.item(row).text() == cur:
                list_widget.setCurrentRow(row)
                break

        list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, popup))
        layout.addWidget(list_widget)
        
        row_h = config.S(26)
        display_count = list_widget.count()
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)
        
        global_pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()

class SpeedDropdown(QPushButton):
    currentTextChanged = Signal(str)
    valueChanged = Signal(str)

    def __init__(self, options_list=None, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list) if options_list else []
        self._current_text = ""
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-weight: 600;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(9)}pt;
                padding: {config.S(4)}px;
                text-align: center;
            }}
            QPushButton:hover {{
                color: #1ed760;
            }}
        """)

    def addItems(self, items):
        self.options_list.extend(items)
        if items and not self._current_text:
            self.setCurrentText(items[0])

    def setCurrentText(self, text):
        self._current_text = text
        self.setText(text)
        self.currentTextChanged.emit(text)
        self.valueChanged.emit(text)

    def currentText(self):
        return self._current_text if self._current_text else self.text()

    def mousePressEvent(self, event):
        if not self.options_list:
            return
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: {config.S(6)}px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.addItems(self.options_list)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                padding: 0px;
                margin: 0px;
                outline: none;
                background: transparent;
                color: #b0b0b0;
                font-size: {config.FS(9)}pt;
            }}
            QListWidget::item {{
                height: {config.S(26)}px;
                padding: 0px {config.S(8)}px;
                border: none;
                text-align: center;
            }}
            QListWidget::item:selected {{
                background-color: #171717;
                color: #1ed760;
                font-weight: bold;
            }}
            QListWidget::item:focus {{
                border: none;
                outline: none;
            }}
            QListWidget::item:hover {{
                background-color: #222222;
                color: #ffffff;
            }}
            QListWidget::item:selected:hover {{
                background-color: #171717;
                color: #1ed760;
            }}
        """)
        
        cur = self.currentText()
        for row in range(list_widget.count()):
            if list_widget.item(row).text() == cur:
                list_widget.setCurrentRow(row)
                break

        def _on_item_clicked(item):
            self.setCurrentText(item.text())
            popup.close()

        list_widget.itemClicked.connect(_on_item_clicked)
        layout.addWidget(list_widget)
        
        row_h = config.S(26)
        display_count = list_widget.count()
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)
        
        popup_w = max(self.width(), config.S(64))
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        popup_x = global_pos.x() + (self.width() - popup_w) // 2
        popup_y = global_pos.y() - (list_height + 2)
        
        popup.setGeometry(popup_x, popup_y, popup_w, list_height + 2)
        popup.show()

class MultiSelectDropdown(QPushButton):
    valueChanged = Signal(list)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.selected_items = set(self.options_list)
        self.setText(self.txt("txt_all_tracks"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e; color: #d4d4d4; text-align: left;
                padding: {config.S(4)}px {config.S(8)}px; border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px; min-height: {config.S(20)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.options_list:
            return
        popup = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"QFrame {{ background-color: #1e1e1e; border: 1px solid #444; border-radius: {config.S(3)}px; padding: 0px; margin: 0px; }}")

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setStyleSheet(f"""
            QListWidget {{ border: none; outline: none; background: transparent; }}
            QListWidget::item {{ border: none; outline: none; }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover {{ background-color: #2a2d2e; }}
            {_popup_scrollbar_css()}
        """)


        class CustomCheckItemWidget(QWidget):
            def __init__(self, text, checked=False, parent=None):
                super().__init__(parent)
                from PySide6.QtWidgets import QHBoxLayout
                from gui.widgets.labels import QLabel
                from PySide6.QtCore import Qt
                super().__init__(parent)
                self.is_checked = checked
                self.opt_text = text
                
                lay = QHBoxLayout(self)
                lay.setContentsMargins(config.S(8), 0, config.S(8), 0)
                lay.setSpacing(config.S(8))
                
                self.tick_box = QLabel()
                self.tick_box.setFixedSize(config.S(14), config.S(14))
                self.tick_box.setAlignment(Qt.AlignCenter)
                
                self.lbl = QLabel(text)
                self.lbl.setStyleSheet(f"border: none; outline: none; color: #d4d4d4; font-size: {config.FS(9.5)}pt; background: transparent;")
                
                lay.addWidget(self.tick_box)
                lay.addWidget(self.lbl)
                lay.addStretch()
                self.update_ui()
                
            def update_ui(self):
                if self.is_checked:
                    self.tick_box.setText("✔")
                    self.tick_box.setStyleSheet(f"background: #111; border: 1px solid #1a7a3e; color: #1a7a3e; font-weight: bold; font-size: {config.S(10)}px; border-radius: {config.S(2)}px;")
                else:
                    self.tick_box.setText("")
                    self.tick_box.setStyleSheet(f"background: #111; border: 1px solid #333; border-radius: {config.S(2)}px;")
                    
            def toggle(self):
                self.is_checked = not self.is_checked
                self.update_ui()

        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QSizePolicy
        for opt in self.options_list:
            item = QListWidgetItem(list_widget)
            item.setSizeHint(QSize(0, config.S(28)))
            widget = CustomCheckItemWidget(opt, opt in self.selected_items)
            widget.setCursor(Qt.PointingHandCursor)
            list_widget.setItemWidget(item, widget)

        layout.addWidget(list_widget)
        
        # Enable clicking anywhere on the item to toggle the checkbox
        def _on_item_clicked(it):
            w = list_widget.itemWidget(it)
            if w:
                w.toggle()
                self._on_toggled(w.opt_text, w.is_checked)
        list_widget.itemClicked.connect(_on_item_clicked)
        # PERFECT HEIGHT MATH
        display_count = min(5, len(self.options_list))
        list_height = display_count * config.S(28)
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)

        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.setGeometry(global_pos.x(), global_pos.y(), self.width(), list_height + 2)
        popup.show()
        popup.move(global_pos)

    def _on_toggled(self, text, checked):
        if checked: self.selected_items.add(text)
        else: self.selected_items.discard(text)

        if not self.selected_items or len(self.selected_items) == len(self.options_list):
            self.setText(self.txt("txt_all_tracks"))
        else:
            self.setText(", ".join(sorted(self.selected_items)))
        self.valueChanged.emit(list(self.selected_items))

class SearchableDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self._options_source = options_list
        if callable(options_list):
            self.options_list = []
        else:
            self.options_list = list(options_list)
        self.setText(self.txt("txt_select"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: {config.S(4)}px {config.S(8)}px;
                border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px;
                min-height: {config.S(20)}px;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        if callable(self._options_source) and not self.options_list:
            self.options_list = list(self._options_source())

        self.popup = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_DeleteOnClose)
        self.popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: {config.S(3)}px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        from gui.widgets.delegates import MarqueeItemDelegate
        self.list_widget.setItemDelegate(MarqueeItemDelegate(self.list_widget))
        self.list_widget.addItems(self.options_list)
        
        rtl_names = [config.SUPPORTED_LANGUAGES.get(code, code) for code in getattr(config, 'RTL_LANGUAGES', set())]
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() in rtl_names:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                padding: 0px;
                margin: 0px;
                outline: none;
                background: transparent;
                color: #d4d4d4;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QListWidget::item {{
                padding: 0px {config.S(5)}px;
                min-height: {config.S(26)}px;
                border: none;
            }}
            QListWidget::item:selected {{ background-color: #333333; color: #ffffff; }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover {{ background-color: #333333; color: #ffffff; }}
            {_popup_scrollbar_css()}
        """)
        self.list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, self.popup))
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(self.txt("ph_search"))
        self.line_edit.setFixedHeight(self.height())
        self.line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                border-bottom: 1px solid #3a3a3a;
                padding: {config.S(6)}px;
                color: #d4d4d4;
                background: transparent;
                outline: none;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS(9.5)}pt;
            }}
            QLineEdit:focus {{
                border-bottom: 1px solid #555555;
            }}
        """)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.installEventFilter(self)
        layout.addWidget(self.line_edit)
        
        layout.addWidget(self.list_widget)
        
        self._update_height(self.list_widget.count(), False)
        
        self.line_edit.setFocus()
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self.popup.setGeometry(global_pos.x(), global_pos.y(), self.width(), self.popup.height())
        self.popup.show()
        self.popup.move(global_pos)

    def _on_text_changed(self, text):
        search_str = text.lower()
        visible_count = 0
        first_visible = None
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if search_str in item.text().lower():
                item.setHidden(False)
                visible_count += 1
                if not first_visible:
                    first_visible = item
            else:
                item.setHidden(True)
                
        if first_visible:
            self.list_widget.setCurrentItem(first_visible)
                
        self._update_height(visible_count, is_searching=bool(text.strip()))

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        if obj == self.line_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self._move_selection(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self._move_selection(1)
                return True
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self._select_current_visible(self.popup)
                return True
        return super().eventFilter(obj, event)

    def _move_selection(self, step):
        visible_items = [self.list_widget.item(i) for i in range(self.list_widget.count()) if not self.list_widget.item(i).isHidden()]
        if not visible_items:
            return
        
        current = self.list_widget.currentItem()
        if current in visible_items:
            idx = visible_items.index(current)
            new_idx = max(0, min(len(visible_items) - 1, idx + step))
            self.list_widget.setCurrentItem(visible_items[new_idx])
        else:
            self.list_widget.setCurrentItem(visible_items[0])

    def _select_current_visible(self, popup):
        current = self.list_widget.currentItem()
        if current and not current.isHidden():
            self.setText(current.text())
            self.valueChanged.emit(current.text())
            popup.close()
            return
        self._select_first_visible(popup)

    def _update_height(self, visible_count, is_searching):
        row_h = config.S(26)
        
        if is_searching:
            display_count = max(1, min(5, visible_count))
        else:
            display_count = min(5, self.list_widget.count())

        if display_count < 5:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
        list_height = display_count * row_h
        self.list_widget.setFixedHeight(list_height)
        
        total_popup_height = self.height() + list_height
        self.popup.setFixedSize(self.width(), total_popup_height)

    def _select_first_visible(self, popup):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.setText(item.text())
                self.valueChanged.emit(item.text())
                popup.close()
                return
        popup.close()

    def setValue(self, text):
        self.setText(text)
        self.valueChanged.emit(text)

    def _on_item_clicked(self, item, popup):
        self.setValue(item.text())
        popup.close()

    def currentText(self):
        return self.text()

class AssembleArrowButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_open = False
        self.hovered = False
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("background: transparent; border: none;")

    def set_open(self, open_state: bool):
        if self.is_open != open_state:
            self.is_open = open_state
            self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen
        from PySide6.QtCore import Qt, QPointF

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        if self.hovered:
            p.fillRect(0, 0, int(w), int(h), QColor(255, 255, 255, 25))

        chevron_col = QColor("#ffffff") if self.hovered else QColor("#e0e0e0")
        pen_chevron = QPen(chevron_col, float(config.S(1.8)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen_chevron)

        half_w = float(config.S(4.5))
        offset_y = float(config.S(2.0))

        if self.is_open:
            # Arrow pointing UP (▲)
            p.drawLine(QPointF(cx - half_w, cy + offset_y), QPointF(cx, cy - offset_y))
            p.drawLine(QPointF(cx, cy - offset_y), QPointF(cx + half_w, cy + offset_y))
        else:
            # Arrow pointing DOWN (▼)
            p.drawLine(QPointF(cx - half_w, cy - offset_y), QPointF(cx, cy + offset_y))
            p.drawLine(QPointF(cx, cy + offset_y), QPointF(cx + half_w, cy - offset_y))

class AssembleSplitButton(QFrame):
    assembleClicked = Signal()
    toggleDrawerClicked = Signal()

    def __init__(self, text, parent_gui, parent=None):
        super().__init__(parent)
        self.parent_gui = parent_gui
        self.is_open = False
        self.setFixedHeight(config.S(35))

        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QFrame
        from PySide6.QtCore import Qt

        self.setObjectName("AssembleSplitButtonFrame")
        self.update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_main = QPushButton(text)
        self.btn_main.setFixedHeight(config.S(33))
        self.btn_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #ffffff;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
                border: none;
                padding-left: {config.S(14)}px;
                padding-right: {config.S(10)}px;
                text-align: center;
            }}
        """)
        self.btn_main.clicked.connect(self.assembleClicked)

        self.sep = QFrame()
        self.sep.setFixedWidth(config.S(1))
        self.sep.setFixedHeight(config.S(18))
        self.sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.3); border: none;")

        self.btn_arrow = AssembleArrowButton(self)
        self.btn_arrow.setFixedSize(config.S(32), config.S(33))
        self.btn_arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_arrow.clicked.connect(self._on_arrow_click)

        layout.addWidget(self.btn_main, 1)
        layout.addWidget(self.sep)
        layout.addWidget(self.btn_arrow)

    def _on_arrow_click(self):
        self.set_open(not self.is_open)
        self.toggleDrawerClicked.emit()

    def set_open(self, is_open: bool):
        self.is_open = is_open
        self.btn_arrow.set_open(is_open)
        self.update_style()

    def update_style(self):
        r = config.S(4)
        if self.is_open:
            self.setStyleSheet(f"""
                QFrame#AssembleSplitButtonFrame {{
                    background-color: #11703c;
                    border-top-left-radius: {r}px;
                    border-top-right-radius: {r}px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    border: 1px solid #11703c;
                    border-bottom: none;
                }}
                QFrame#AssembleSplitButtonFrame:hover {{
                    background-color: #168f4d;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#AssembleSplitButtonFrame {{
                    background-color: #11703c;
                    border-radius: {r}px;
                    border: 1px solid #0a4d28;
                }}
                QFrame#AssembleSplitButtonFrame:hover {{
                    background-color: #168f4d;
                }}
            """)

