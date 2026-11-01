#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: slider_field.py
ROLE: GUI Widget
DESCRIPTION:
A labelled slider for a live setting: name and value on one line, the slider underneath.
Commits while dragging (debounced) and on release; double-click the value to reset.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider

import config
from gui.widgets.labels import QLabel


class SliderField(QWidget):
    committed = Signal(float)

    def __init__(self, label, value, lo, hi, step, default, unit="", decimals=1, tooltip="", parent=None):
        super().__init__(parent)
        self._lo, self._step, self._default = lo, step, default
        self._unit, self._decimals = unit, decimals
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(config.S(4))
        top = QHBoxLayout()
        top.setSpacing(config.S(6))
        self.lbl = QLabel(label)
        self.lbl.setStyleSheet(f"color: #a0a0a0; font-size: {config.FS(9)}pt; background: transparent;")
        self.val = QLabel("")
        self.val.setStyleSheet(f"color: #e6e6e6; font-size: {config.FS(9)}pt; font-weight: 600; background: transparent;")
        self.val.setToolTip(tooltip)
        self.val.mouseDoubleClickEvent = lambda e: self.set_value(self._default, commit=True)
        top.addWidget(self.lbl, 1)
        top.addWidget(self.val)
        lay.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, int(round((hi - lo) / step)))
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setToolTip(tooltip)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: {config.S(4)}px; background: #3a3a3a; border-radius: {config.S(2)}px; }}
            QSlider::sub-page:horizontal {{ background: #23a559; border-radius: {config.S(2)}px; }}
            QSlider::handle:horizontal {{ background: #f0f0f0; border: 1px solid #f0f0f0; width: {config.S(12)}px;
                height: {config.S(12)}px; margin: -{config.S(5)}px 0; border-radius: {config.S(6)}px; }}
            QSlider::handle:horizontal:hover {{ background: #ffffff; border-color: #ffffff; }}
        """)
        lay.addWidget(self.slider)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._commit)
        self.slider.valueChanged.connect(self._on_moved)
        self.slider.sliderReleased.connect(self._commit)
        self.set_value(value)

    def value(self):
        return round(self._lo + self.slider.value() * self._step, 4)

    def set_value(self, v, commit=False):
        self.slider.blockSignals(True)
        self.slider.setValue(int(round((float(v) - self._lo) / self._step)))
        self.slider.blockSignals(False)
        self._show()
        if commit:
            self._commit()

    def _show(self):
        self.val.setText(f"{self.value():.{self._decimals}f}{self._unit}")

    def _on_moved(self, _):
        self._show()
        self._debounce.start()

    def _commit(self):
        self._debounce.stop()
        self.committed.emit(self.value())
