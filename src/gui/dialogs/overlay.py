#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: overlay.py
ROLE: GUI Overlay & Drag/Drop Components
DESCRIPTION:
Dim overlay, global event filters, and drag/drop zones for markers and sidebar.
"""

from PySide6.QtCore import Qt, QTimer, QObject, QEvent, QRect, QPoint, QMimeData, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QSizePolicy, QLineEdit, QApplication
from PySide6.QtGui import QCursor, QPainter, QPen, QColor, QDrag

from gui.widgets.buttons import SidebarButton


class GlobalAppFilter(QObject):
    """Intercepts native QEvent.ToolTip globally and handles global input focus management."""
    def __init__(self, shared_tooltip):
        super().__init__()
        self.shared_tooltip = shared_tooltip
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._do_show)
        self.current_text = ""
        self.current_pos = None
        self.active_widget = None

    def eventFilter(self, obj, event):
        try:
            etype = event.type()
            # 1. Global Focus Management: clear focus from QLineEdit on click anywhere outside
            if etype == QEvent.Type.MouseButtonPress:
                focused = QApplication.focusWidget()
                if isinstance(focused, QLineEdit):
                    global_pos = QCursor.pos()
                    focused_global_rect = QRect(focused.mapToGlobal(QPoint(0, 0)), focused.size())
                    if not focused_global_rect.contains(global_pos):
                        focused.clearFocus()

            # 2. Enter/Return removes focus from QLineEdit
            if etype == QEvent.Type.KeyPress and isinstance(obj, QLineEdit) and obj.hasFocus():
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    obj.clearFocus()

            # 3. Tooltip handling via Enter/Leave for better reliability
            if etype == QEvent.Type.Enter:
                if isinstance(obj, QWidget):
                    text = obj.toolTip()
                    if text:
                        self.current_text = text
                        self.current_pos = QCursor.pos()
                        self.active_widget = obj
                        self.tooltip_timer.start(750)
            elif etype == QEvent.Type.MouseMove and self.active_widget == obj:
                self.current_pos = QCursor.pos()
            elif etype in (QEvent.Type.Leave, QEvent.Type.Hide,
                           QEvent.Type.MouseButtonPress, QEvent.Type.WindowDeactivate):
                if obj == self.active_widget or self.active_widget is None:
                    self.tooltip_timer.stop()
                    if hasattr(self, 'shared_tooltip'):
                        self.shared_tooltip.hide()
                    self.active_widget = None
                    self.current_text = ""
            elif etype == QEvent.Type.ToolTip and self.active_widget == obj:
                return True
        except RuntimeError:
            pass
        return False

    def _do_show(self):
        if self.current_text and self.active_widget:
            self.shared_tooltip.show_global(self.current_text, self.current_pos)


class SidebarDragZone(QFrame):
    """A drop-zone container for SidebarButtons."""
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(6)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText():
            return
            
        layout = self.layout()
        source_btn = event.source()
        
        target_idx = layout.count()
        last_vis_widget = None
        drop_y = 0
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_btn:
                continue
            
            last_vis_widget = w
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
            else:
                layout_margins = self.layout().contentsMargins()
                drop_y = layout_margins.top() if layout_margins else 0
                
        self._drop_line_y = drop_y
        self.update()
        event.accept()

    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        activity_id = event.mimeData().text()
        source_btn = event.source()
        if isinstance(source_btn, SidebarButton) and source_btn.activity_id == activity_id:
            layout = self.layout()
            
            target_idx = layout.count()
            last_vis_widget = None
            drop_y = 0
            
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if not w or w.isHidden() or w == source_btn:
                    continue
                
                last_vis_widget = w
                if event.position().y() < w.geometry().center().y():
                    target_idx = i
                    drop_y = w.geometry().top()
                    break
            else:
                if last_vis_widget:
                    drop_y = last_vis_widget.geometry().bottom()
                else:
                    layout_margins = self.layout().contentsMargins()
                    drop_y = layout_margins.top() if layout_margins else 0
                        
            layout.insertWidget(target_idx, source_btn)
            event.acceptProposedAction()
            
            main_window = self.window()
            is_right = (hasattr(main_window, "_sidebar_right") and self == main_window._drag_zone_right)
            source_btn.is_right_side = is_right
            source_btn.set_active(False)
            
            self._drop_line_y = -1
            self.update()

            if hasattr(main_window, '_save_sidebar_layout'):
                main_window._save_sidebar_layout()

            if getattr(source_btn, '_drag_was_active', False):
                source_btn.window()._toggle_activity(source_btn.activity_id)
                source_btn._drag_was_active = False


class MarkerDragZone(QFrame):
    """A drop-zone container for Custom Markers in the settings panel."""
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() == "m_drag":
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        layout = self.layout()
        source_widget = event.source()
        
        target_idx = layout.count() - 1 
        drop_y = 0
        last_vis_widget = None
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            
            if w.objectName() == "stretch_placeholder":
                continue
                
            last_vis_widget = w
            
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
                
        if drop_y != self._drop_line_y:
            self._drop_line_y = drop_y
            self.update()
            
        event.acceptProposedAction()
        
    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        self._drop_line_y = -1
        self.update()
        
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        source_widget = event.source()
        layout = self.layout()
        
        target_idx = layout.count() - 1
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            if w.objectName() == "stretch_placeholder":
                continue
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                break
                
        if hasattr(self.window(), "_on_markers_reordered"):
            self.window()._on_markers_reordered(source_widget.original_idx, target_idx)
            
        event.acceptProposedAction()


class MarkerRowWidget(QWidget):
    """Draggable marker row."""
    def __init__(self, marker_data, original_idx, parent=None):
        super().__init__(parent)
        self.marker_data = marker_data
        self.original_idx = original_idx
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText("m_drag")
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.MoveAction)


class AnimatedDimOverlay(QWidget):
    def __init__(self, parent_gui, opacity_target=0.55, duration=200):
        parent = getattr(parent_gui, 'centralWidget', lambda: None)() or parent_gui
        super().__init__(parent)
        self.opacity_target = opacity_target
        self.current_alpha = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self.anim_in = QVariantAnimation(self)
        self.anim_in.setDuration(duration)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(int(255 * opacity_target))
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_in.valueChanged.connect(self._on_alpha_changed)

    def _on_alpha_changed(self, val):
        self.current_alpha = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.current_alpha))

    def fade_in(self):
        p = self.parentWidget()
        if p:
            self.setGeometry(0, 0, p.width(), p.height())
        self.show()
        self.raise_()
        QApplication.processEvents()
        self.anim_in.start()

    def fade_out(self):
        self.anim_out = QVariantAnimation(self)
        self.anim_out.setDuration(160)
        self.anim_out.setStartValue(self.current_alpha)
        self.anim_out.setEndValue(0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.valueChanged.connect(self._on_alpha_changed)
        self.anim_out.finished.connect(self.deleteLater)
        self.anim_out.start()
