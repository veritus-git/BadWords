#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Tests for Point 3:
- Frameless window hit-testing (all 8 edges/corners, HTMAXBUTTON Snap Layouts, HTCAPTION)
- User normal-size memory (70% default + custom user size restored after maximize/rip)
- Zero Windows 11 startup micro-window flashes (no premature PanelHeaderWidget / SettingsDialog winId)
- CustomTitleBar neutral X hover (NEVER red), maximize icon sizing, and zero menu/source overlap
- SettingsDialog as an independent top-level window (Alt+Tab, min/max/close, responsive sidebar,
  AI-chat-style max content width, Wayland Always-on-Top hint, live icon refresh without restart)
- Multi-monitor negative-coordinate clamping & IDETooltip active-screen clamping
- Cross-OS VSync (QtCore.framework macOS lookup, QUnifiedTimer ABI binding, dynamic subscriber updates)
- Popup Always-on-Top inheritance without hardcoded WindowStaysOnTopHint
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QEvent, QObject, QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BADWORDS_DEV"] = "1"
app = QApplication.instance() or QApplication([])

import config
from gui.components.mixins import (
    HTBOTTOM,
    HTBOTTOMLEFT,
    HTBOTTOMRIGHT,
    HTCAPTION,
    HTCLIENT,
    HTLEFT,
    HTMAXBUTTON,
    HTRIGHT,
    HTTOP,
    HTTOPLEFT,
    HTTOPRIGHT,
    FramelessWindowMixin,
    compute_default_normal_geometry,
    compute_win_nchittest,
)
from gui.components.titlebar import AnimatedTitleButton, CustomTitleBar
from gui.dialogs.msgbox import CustomMsgBox
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.v4_migration_dialog import V4MigrationDialog
from gui.utils import clamp_rect_to_screen, apply_app_icon_everywhere
from gui.widgets.labels import IDETooltip
import gui.vsync as vsync


class TestPoint3WindowsTitlebarVSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gui.dialogs.update_dialog import UpdateCheckThread
        UpdateCheckThread._checked = True
        UpdateCheckThread._cached_result = ("4.0.1", "https://github.com", "https://gitlab.com", "")

    def _create_mock_engine(self):
        engine = MagicMock()
        prefs = dict(config.DEFAULT_SETTINGS)
        prefs["gui_lang"] = "en"
        prefs["settings_view_mode"] = "basic"
        prefs["always_on_top"] = False
        prefs["app_icon"] = "default"
        engine.load_preferences.return_value = prefs
        engine.save_preferences = MagicMock()
        engine.current_lang = "en"
        mock_doc = MagicMock()
        mock_doc.is_win = False
        mock_doc.is_mac = False
        mock_doc.is_linux = True
        mock_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
        mock_doc.get_telemetry_pref.return_value = True
        mock_doc.set_always_on_top.return_value = False
        engine.os_doc = mock_doc
        mock_resolve = MagicMock()
        mock_resolve.is_free_21_1_or_newer.return_value = False
        engine.resolve_handler = mock_resolve
        return engine

    def test_win_nchittest_8_edges_snap_layouts_and_caption(self):
        w, h, b, tb = 1000, 700, 5, 32
        # All 8 resize edges/corners when windowed
        self.assertEqual(compute_win_nchittest(2, 2, w, h, b, False, False, tb), HTTOPLEFT)
        self.assertEqual(compute_win_nchittest(w - 2, 2, w, h, b, False, False, tb), HTTOPRIGHT)
        self.assertEqual(compute_win_nchittest(2, h - 2, w, h, b, False, False, tb), HTBOTTOMLEFT)
        self.assertEqual(compute_win_nchittest(w - 2, h - 2, w, h, b, False, False, tb), HTBOTTOMRIGHT)
        self.assertEqual(compute_win_nchittest(2, 200, w, h, b, False, False, tb), HTLEFT)
        self.assertEqual(compute_win_nchittest(w - 2, 200, w, h, b, False, False, tb), HTRIGHT)
        self.assertEqual(compute_win_nchittest(400, 2, w, h, b, False, False, tb), HTTOP)
        self.assertEqual(compute_win_nchittest(400, h - 2, w, h, b, False, False, tb), HTBOTTOM)

        # Titlebar empty space -> HTCAPTION; btn_max -> HTMAXBUTTON; other buttons -> HTCLIENT
        self.assertEqual(compute_win_nchittest(400, 16, w, h, b, False, False, tb), HTCAPTION)
        self.assertEqual(
            compute_win_nchittest(950, 16, w, h, b, False, False, tb, is_on_max_btn=True),
            HTMAXBUTTON,
        )
        self.assertEqual(
            compute_win_nchittest(980, 16, w, h, b, False, False, tb, is_on_interactive_child=True),
            HTCLIENT,
        )

        # When maximized, edge hit-test is disabled and top pixels hit titlebar
        self.assertEqual(compute_win_nchittest(400, 2, w, h, b, True, False, tb), HTCAPTION)
        self.assertEqual(
            compute_win_nchittest(950, 2, w, h, b, True, False, tb, is_on_max_btn=True),
            HTMAXBUTTON,
        )

    def test_70pct_default_and_user_normal_size_restore(self):
        screen_geo = QRect(0, 0, 1920, 1080)
        geo = compute_default_normal_geometry(screen_geo, ratio=0.70, min_w=640, min_h=460)
        self.assertEqual(geo.width(), 1344)
        self.assertEqual(geo.height(), 756)
        self.assertEqual(geo.x(), (1920 - 1344) // 2)
        self.assertEqual(geo.y(), (1080 - 756) // 2)

        # Simulated root window remembers user-resized normal size across maximize/restore & drag-detach
        from PySide6.QtWidgets import QMainWindow
        class _DummyWin(FramelessWindowMixin, QMainWindow):
            def __init__(self):
                super().__init__()
                self.frameless_init(is_popup=False)

        fake_screen = MagicMock()
        fake_screen.availableGeometry.return_value = screen_geo
        win = _DummyWin()
        win.init_normal_geometry(saved_w=1120, saved_h=680, screen=fake_screen, apply_geometry=True)
        self.assertEqual(win.get_user_normal_size(), QSize(1120, 680))

        # Simulate OS restoring window to ~100% screen before _restore_user_normal_size enforces user size
        with patch.object(win, "screen", return_value=fake_screen):
            win.resize(1920, 1080)
            win._restore_user_normal_size()
            self.assertEqual(win.size(), QSize(1120, 680))
        win.close()

    def test_titlebar_neutral_hover_icon_size_and_no_overlap(self):
        from PySide6.QtWidgets import QMainWindow
        win = QMainWindow()
        win._is_root = True
        tb = CustomTitleBar(win, "en", parent=win)
        win.setCentralWidget(tb)
        win.resize(520, 40)

        # Close button hover MUST stay neutral gray (never red)
        self.assertEqual(tb.btn_close._hover, config.COLOR_TITLEBAR_HOVER)
        self.assertNotEqual(QColor(tb.btn_close._hover).red(), 196)

        # Maximize icon updates to config.S(12)
        tb.update_maximize_icon(True)
        self.assertEqual(tb.btn_max.iconSize(), QSize(config.S(12), config.S(12)))

        # Render narrow & wide titlebar with long source info and verify zero overlap
        tb.activate_transcription_mode()
        tb.set_source_info("Very_Long_DaVinci_Project_Timeline_Name_For_Testing_Overlap", "A1, A2, A3, A4")
        win.show()
        app.processEvents()

        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        self.assertTrue(win.grab().save(os.path.join(art_dir, "point3_titlebar_narrow.png")))

        menu_right = tb._menu_container.x() + tb._menu_container.width()
        ctrl_left = tb._right_controls_left_edge()
        if tb._lbl_source_info.isVisible():
            self.assertGreaterEqual(tb._lbl_source_info.x(), menu_right)
            self.assertLessEqual(tb._lbl_source_info.x() + tb._lbl_source_info.width(), ctrl_left)

        win.resize(1100, 40)
        app.processEvents()
        self.assertTrue(win.grab().save(os.path.join(art_dir, "point3_titlebar_wide.png")))
        win.close()

    def test_zero_startup_micro_window_flashes(self):
        """Verify BadWordsGUI.__init__ and SettingsDialog.__init__ emit zero orphan Show/WinIdChange events."""
        import osdoc, api, engine, gui
        gui.BadWordsGUI.check_telemetry = lambda self: None
        gui.BadWordsGUI._start_update_check = lambda self: None

        flashes = []
        class _Spy(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() in (QEvent.Show, QEvent.WinIdChange):
                    if hasattr(obj, "isWindow") and obj.isWindow():
                        if obj.__class__.__name__ != "BadWordsGUI":
                            flashes.append((ev.type().name, obj.__class__.__name__, obj.objectName()))
                return False

        od = osdoc.OSDoctor()
        rh = api.ResolveHandler(od)
        eng = engine.AudioEngine(od, rh)
        spy = _Spy()
        app.installEventFilter(spy)
        try:
            mw = gui.BadWordsGUI(eng, rh)
            app.processEvents()
            mw._preload_settings()
            app.processEvents()
            self.assertEqual(flashes, [], f"Unexpected top-level flashes during boot/preload: {flashes}")
            mw.hide()
            mw.deleteLater()
        finally:
            app.removeEventFilter(spy)

    def test_settings_dialog_independent_window_responsive_and_renders(self):
        engine = self._create_mock_engine()
        from PySide6.QtWidgets import QMainWindow
        main_win = QMainWindow()
        main_win.setGeometry(100, 100, 1280, 720)
        main_win._always_on_top_active = False

        dlg = SettingsDialog(engine, main_win)
        # Independent top-level window (None Qt parent) with main window reference preserved
        self.assertIsNone(dlg.parent())
        self.assertIs(dlg._get_main_window(), main_win)
        wtype = dlg.windowFlags() & Qt.WindowType_Mask
        self.assertEqual(wtype, Qt.Window)
        self.assertNotEqual(wtype, Qt.Tool)
        self.assertNotEqual(wtype, Qt.Dialog)
        self.assertFalse(dlg._tb.btn_min.isHidden())
        self.assertFalse(dlg._tb.btn_max.isHidden())
        self.assertFalse(dlg._tb.btn_close.isHidden())

        # Verify changing app_icon or always_on_top does NOT flag restart_needed
        self.assertNotIn("app_icon", config.RESTART_REQUIRED_KEYS)
        self.assertNotIn("always_on_top", config.RESTART_REQUIRED_KEYS)

        # Render default Settings window
        dlg.show()
        app.processEvents()
        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        self.assertTrue(dlg.grab().save(os.path.join(art_dir, "point3_settings_default.png")))

        default_sidebar_w = dlg.left_panel.width()

        # Render maximized/wide Settings window -> wider sidebar + centered AI-chat-style content column
        dlg.resize(1360, 820)
        dlg._ensure_page_built(1)
        dlg.category_list.setCurrentRow(1)
        app.processEvents()
        self.assertGreaterEqual(dlg.left_panel.width(), default_sidebar_w)
        scroll = dlg.stack.widget(1)
        host = scroll.widget()
        self.assertLessEqual(host._content.width(), config.S(660))
        self.assertTrue(dlg.grab().save(os.path.join(art_dir, "point3_settings_maximized.png")))

        # Verify Linux CSD shadow margin collapses to 0 and effect disables when maximized, then restores
        with patch.object(dlg, "isMaximized", return_value=True):
            dlg._sync_csd_shadow_state()
            m_max = dlg.layout().contentsMargins()
            self.assertEqual((m_max.left(), m_max.top(), m_max.right(), m_max.bottom()), (0, 0, 0, 0))
            self.assertFalse(dlg.inner_frame.graphicsEffect().isEnabled())
        with patch.object(dlg, "isMaximized", return_value=False):
            dlg._sync_csd_shadow_state()
            m_win = dlg.layout().contentsMargins()
            self.assertEqual((m_win.left(), m_win.top(), m_win.right(), m_win.bottom()), (14, 14, 14, 14))
            self.assertTrue(dlg.inner_frame.graphicsEffect().isEnabled())

        # Verify Wayland Always on Top hint renders when Wayland is active
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            dlg_wl = SettingsDialog(engine, main_win)
            dlg_wl._ensure_page_built(1)
            dlg_wl.category_list.setCurrentRow(1)
            dlg_wl.show()
            app.processEvents()
            self.assertTrue(hasattr(dlg_wl, "lbl_always_on_top_wayland_hint"))
            self.assertTrue(dlg_wl.chk_ontop.isEnabled())
            self.assertTrue(dlg_wl.grab().save(os.path.join(art_dir, "point3_settings_appearance_wayland.png")))
            dlg_wl.close()

        dlg.close()
        main_win.close()

    def test_live_icon_refresh_everywhere(self):
        from PySide6.QtWidgets import QMainWindow
        win = QMainWindow()
        win._title_bar = CustomTitleBar(win, "en", parent=win)
        calls = []
        win._title_bar.update_titlebar_icon = lambda name=None: calls.append(name)
        apply_app_icon_everywhere("white")
        self.assertIn("white", calls)
        win.close()

    def test_multi_monitor_negative_coordinates_and_popup_aot_inheritance(self):
        # Secondary monitor placed to the LEFT (-1920, 0) and small screen clamping
        neg_screen = QRect(-1920, 0, 1920, 1080)
        ref = QRect(-1500, 150, 800, 600)
        x, y, cw, ch = clamp_rect_to_screen(750, 580, neg_screen, ref_geo=ref)
        self.assertLess(x, 0)
        self.assertGreaterEqual(x, neg_screen.left())
        self.assertLessEqual(x + cw - 1, neg_screen.right())
        self.assertEqual(cw, 750)

        small_screen = QRect(0, 0, 1024, 600)
        x2, y2, cw2, ch2 = clamp_rect_to_screen(750, 800, small_screen)
        self.assertLessEqual(ch2, 580)
        self.assertGreaterEqual(y2, 0)

        # Popups do NOT hardcode WindowStaysOnTopHint when main window has it OFF, and DO inherit when ON
        from PySide6.QtWidgets import QMainWindow
        parent_off = QMainWindow()
        parent_off._always_on_top_active = False
        parent_off.lang = "en"
        box_off = CustomMsgBox(parent_off, "T", "M", "OK")
        self.assertFalse(bool(box_off.windowFlags() & Qt.WindowStaysOnTopHint))
        box_off.close()

        parent_on = QMainWindow()
        parent_on._always_on_top_active = True
        parent_on.lang = "en"
        box_on = CustomMsgBox(parent_on, "T", "M", "OK")
        self.assertTrue(bool(box_on.windowFlags() & Qt.WindowStaysOnTopHint))
        box_on.close()

        mig = V4MigrationDialog(lang="en", parent=parent_off)
        self.assertIsInstance(mig, FramelessWindowMixin)
        self.assertFalse(bool(mig.windowFlags() & Qt.WindowStaysOnTopHint))
        mig.close()

        tip = IDETooltip()
        tip.prepare_content("Tooltip text")
        tip.show_global("Tooltip text", QPoint(-400, 200))
        tip.hide()
        tip.close()

    def test_vsync_macos_framework_lookup_and_dynamic_subscribers(self):
        # 1. Verify macOS QtCore.framework path discovery
        with patch("gui.vsync.platform.system", return_value="Darwin"), \
             patch("os.path.isfile", side_effect=lambda p: p.endswith("QtCore.framework/Versions/A/QtCore")):
            lib_p = vsync._find_qtcore_library()
            self.assertIsNotNone(lib_p)
            self.assertTrue(lib_p.endswith("QtCore.framework/Versions/A/QtCore"))

        # 2. Verify QUnifiedTimer binds on current Linux PySide6 Qt6Core
        vsync._init_unified_timer_hooks()
        self.assertTrue(vsync._UNIFIED_TIMER_AVAILABLE)

        # 3. Verify subscribed timers update dynamically when active monitor refresh rate changes
        t = QTimer()
        vsync.subscribe_timer(t)
        fake_144 = MagicMock()
        fake_144.refreshRate.return_value = 144.0
        fake_144.name.return_value = "DP-1"
        vsync.apply_screen_refresh_rate(fake_144)
        self.assertEqual(vsync.get_refresh_interval_ms(), 7)
        self.assertEqual(t.interval(), 7)

        fake_60 = MagicMock()
        fake_60.refreshRate.return_value = 60.0
        fake_60.name.return_value = "HDMI-1"
        vsync.apply_screen_refresh_rate(fake_60)
        self.assertEqual(vsync.get_refresh_interval_ms(), 17)
        self.assertEqual(t.interval(), 17)

        # Secondary monitor refreshRateChanged must NOT override active DP-1 screen!
        vsync.apply_screen_refresh_rate(fake_144)
        vsync._on_screen_rate_changed(fake_60)
        self.assertEqual(vsync.get_refresh_interval_ms(), 7)
        vsync.apply_screen_refresh_rate(fake_60)


if __name__ == "__main__":
    unittest.main()
