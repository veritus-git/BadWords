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
    compute_proportional_rip_rect,
    compute_win_nccalcsize_rect,
    compute_win_nchittest,
)
from gui.components.titlebar import AnimatedTitleButton, CustomTitleBar
from gui.dialogs.export_dialog import ExportDialog
from gui.dialogs.marker_dialog import MarkerDialog
from gui.dialogs.msgbox import CustomMsgBox
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.telemetry_popup import TelemetryPopup
from gui.dialogs.crash_report_dialog import CrashReportConsentDialog
from gui.dialogs.unsaved_changes_dialog import UnsavedChangesDialog
from gui.dialogs.update_dialog import UpdateNotifyDialog
from gui.dialogs.v4_migration_dialog import V4MigrationDialog
from gui.utils import clamp_rect_to_screen, apply_app_icon_everywhere
from gui.widgets.labels import IDETooltip
import gui.vsync as vsync
from startup.boot_splash import BootSplash


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

        # When maximized, ALL 8 resize edges are disabled: top-right corner (w-1, 0) hits close (HTCLIENT),
        # top edge (y=0) hits HTCAPTION for effortless ripping, and btn_max hits HTMAXBUTTON.
        self.assertEqual(compute_win_nchittest(400, 0, w, h, b, True, False, tb), HTCAPTION)
        self.assertEqual(
            compute_win_nchittest(w - 1, 0, w, h, b, True, False, tb, is_on_interactive_child=True),
            HTCLIENT,
        )
        self.assertEqual(
            compute_win_nchittest(950, 0, w, h, b, True, False, tb, is_on_max_btn=True),
            HTMAXBUTTON,
        )

        # Verify WM_NCCALCSIZE pure rect math (kills Windows 8px black bar & right/bottom clipping!)
        # 1. Windowed (IsZoomed=False): rect untouched -> 0px non-client area
        self.assertEqual(
            compute_win_nccalcsize_rect((100, 100, 1100, 800), is_zoomed=False, is_fullscreen=False,
                                        work_rect=(0, 0, 1920, 1040), monitor_rect=(0, 0, 1920, 1080)),
            (100, 100, 1100, 800),
        )
        # 2. Maximized (IsZoomed=True, overhanging -8px): snaps directly to monitor rcWork
        self.assertEqual(
            compute_win_nccalcsize_rect((-8, -8, 1928, 1048), is_zoomed=True, is_fullscreen=False,
                                        work_rect=(0, 0, 1920, 1040), monitor_rect=(0, 0, 1920, 1080)),
            (0, 0, 1920, 1040),
        )
        # 3. Maximized with auto-hide taskbar (rcWork == rcMonitor): reserves 1px bottom strip
        self.assertEqual(
            compute_win_nccalcsize_rect((-8, -8, 1928, 1088), is_zoomed=True, is_fullscreen=False,
                                        work_rect=(0, 0, 1920, 1080), monitor_rect=(0, 0, 1920, 1080)),
            (0, 0, 1920, 1079),
        )

    def test_70pct_rip_vs_button_restore_and_settings_1to1_parity(self):
        screen_geo = QRect(0, 0, 1920, 1080)
        geo = compute_default_normal_geometry(screen_geo, ratio=0.70, min_w=640, min_h=460)
        self.assertEqual(geo.width(), 1344)
        self.assertEqual(geo.height(), 756)
        self.assertEqual(geo.x(), (1920 - 1344) // 2)
        self.assertEqual(geo.y(), (1080 - 756) // 2)

        from PySide6.QtWidgets import QMainWindow
        class _DummyWin(FramelessWindowMixin, QMainWindow):
            def __init__(self):
                super().__init__()
                self.frameless_init(is_popup=False)

        fake_screen = MagicMock()
        fake_screen.availableGeometry.return_value = screen_geo
        win = _DummyWin()
        win.init_normal_geometry(screen=fake_screen, ratio=0.70, apply_geometry=True)

        with patch.object(win, "screen", return_value=fake_screen), \
             patch("gui.components.mixins.QGuiApplication.screenAt", return_value=fake_screen):
            # 1. Button restore with NO prior pre-maximize geometry -> 70% x 70% centered
            win.resize(1920, 1080)
            win._restore_after_unmaximize(via_button=True)
            self.assertEqual(win.size(), QSize(1344, 756))

            # 2. User places window at exact custom position/size, then maximizes -> snapshot captured
            win._restoring_from_max = False
            win._last_normal_geo = QRect(960, 0, 960, 1080)
            win._snapshot_pre_maximize_geometry()
            self.assertEqual(win._pre_maximize_geometry, QRect(960, 0, 960, 1080))

            # 3. Ripping out of maximize (via_button=False) ALWAYS uses 70% x 70%
            win.resize(1920, 1080)
            win._restore_after_unmaximize(via_button=False)
            self.assertEqual(win.size(), QSize(1344, 756))

            # 4. ONLY clicking Restore button (via_button=True) restores exact pre-max geometry + position
            win._restoring_from_max = False
            win.resize(1920, 1080)
            win._restore_after_unmaximize(via_button=True)
            self.assertEqual(win.geometry(), QRect(960, 0, 960, 1080))
        win.close()

    def test_button_restore_exact_premax_geometry_and_rip_ignores_stale_flag(self):
        screen_geo = QRect(0, 0, 1920, 1080)
        from PySide6.QtWidgets import QMainWindow
        class _DummyWin(FramelessWindowMixin, QMainWindow):
            def __init__(self):
                super().__init__()
                self.frameless_init(is_popup=False)
        fake_screen = MagicMock()
        fake_screen.availableGeometry.return_value = screen_geo
        win = _DummyWin()
        win.init_normal_geometry(screen=fake_screen, ratio=0.70, apply_geometry=True)
        with patch.object(win, "screen", return_value=fake_screen), \
             patch("gui.components.mixins.QGuiApplication.screenAt", return_value=fake_screen):
            win._last_normal_geo = QRect(137, 91, 1001, 703)
            win._snapshot_pre_maximize_geometry()
            win.resize(1920, 1080)
            win._restore_after_unmaximize(via_button=True)
            self.assertEqual(win.geometry(), QRect(137, 91, 1001, 703))
            # Stale button flag must never leak: ripping afterwards is ALWAYS 70% x 70%
            self.assertFalse(win._restore_via_button)
            win._restoring_from_max = False
            win.resize(1920, 1080)
            win._restore_after_unmaximize(via_button=False)
            self.assertEqual(win.size(), QSize(1344, 756))
        win.close()

    def test_maximized_grips_and_border_overlay_hidden_and_1to1_settings(self):
        engine = self._create_mock_engine()
        from PySide6.QtWidgets import QMainWindow
        main_win = QMainWindow()
        main_win._always_on_top_active = False

        dlg = SettingsDialog(engine, main_win)
        # 1:1 parity with BadWordsGUI: SettingsDialog is now a true QMainWindow (zero QDialog X11 shadow!)
        self.assertIsInstance(dlg, QMainWindow)
        self.assertIs(dlg._title_bar, dlg._tb)
        self.assertIs(dlg._root_frame, dlg.inner_frame)
        dlg.show()
        app.processEvents()

        # Windowed -> grips visible + 1px mouse-transparent border overlay visible
        dlg._update_border_overlay()
        dlg._update_grips()
        self.assertTrue(all(not g.isHidden() for g in dlg._grips))
        self.assertIsNotNone(dlg._border_overlay)
        self.assertFalse(dlg._border_overlay.isHidden())
        self.assertTrue(dlg._border_overlay.testAttribute(Qt.WA_TransparentForMouseEvents))

        # Maximized -> ALL 8 resize grips hidden AND border overlay hidden (0px obstruction at corner X & y=0!)
        with patch.object(dlg, "isMaximized", return_value=True):
            dlg._update_border_overlay()
            dlg._update_grips()
            self.assertTrue(all(g.isHidden() for g in dlg._grips))
            self.assertTrue(dlg._border_overlay.isHidden())
            # Titlebar sits at exact y=0 and btn_close reaches exact right edge w-1
            self.assertEqual(dlg._tb.y(), 0)
            self.assertEqual(dlg._tb.btn_close.x() + dlg._tb.btn_close.width(), dlg._tb.width())
        dlg._update_border_overlay()
        dlg._update_grips()

        # Render Polish 0.85-scaled SettingsDialog (1280x800 laptop/VM scenario) to verify zero right-edge clipping
        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        pl_engine = self._create_mock_engine()
        pl_engine.load_preferences.return_value["gui_lang"] = "pl"
        pl_engine.current_lang = "pl"
        old_scale = config.SCALE_FACTOR
        try:
            config.set_ui_scale(0.85)
            dlg_pl = SettingsDialog(pl_engine, main_win)
            dlg_pl.show()
            app.processEvents()
            # Ensure right edge of Widok Zaawansowany button fits cleanly inside its scroll viewport
            vp_w = dlg_pl.stack.widget(0).viewport().width()
            adv_right = dlg_pl.btn_view_advanced.mapTo(dlg_pl.stack.widget(0).viewport(), QPoint(dlg_pl.btn_view_advanced.width(), 0)).x()
            self.assertLessEqual(adv_right, vp_w + 2, f"Right-edge clipping detected: {adv_right} > {vp_w}")
            self.assertTrue(dlg_pl.grab().save(os.path.join(art_dir, "point3_settings_pl_scaled85.png")))
            dlg_pl.close()
        finally:
            config.set_ui_scale(old_scale)

        dlg.close()
        main_win.close()

    def test_main_window_close_guards_unsaved_settings(self):
        import osdoc, api, engine, gui
        gui.BadWordsGUI.check_telemetry = lambda self: None
        gui.BadWordsGUI._start_update_check = lambda self: None
        od = osdoc.OSDoctor()
        rh = api.ResolveHandler(od)
        eng = engine.AudioEngine(od, rh)
        mw = gui.BadWordsGUI(eng, rh)
        dlg = mw._get_settings_dialog()
        dlg.show()
        app.processEvents()

        # Simulate dirty/unsaved settings where user cancels the UnsavedChangesDialog -> dlg stays visible
        from PySide6.QtGui import QCloseEvent
        with patch.object(dlg, "has_unsaved_changes", return_value=True), \
             patch.object(dlg, "close", return_value=False) as mock_dlg_close:
            ev = QCloseEvent()
            mw.closeEvent(ev)
            mock_dlg_close.assert_called_once()
            self.assertFalse(ev.isAccepted(), "Main window must NOT close if Settings stayed open with unsaved changes!")
            self.assertTrue(dlg.isVisible())

        # Simulate Settings closing cleanly when user confirms Quit -> both close
        with patch.object(dlg, "has_unsaved_changes", return_value=False), \
             patch("gui.main_window.CustomMsgBox") as mock_msg:
            mock_msg.return_value.exec.return_value = 1  # QDialog.Accepted
            ev2 = QCloseEvent()
            mw.closeEvent(ev2)
            self.assertTrue(ev2.isAccepted())
            self.assertIsNone(mw._settings_dialog)

        mw.deleteLater()

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

        # App Icon requires restart (prevents Win32 WM_SETICON from painting Windows 7 Basic caption chrome)
        self.assertIn("app_icon", config.RESTART_REQUIRED_KEYS)
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

        # Settings mirrors the main window 1:1: QMainWindow, no CSD drop-shadow, flush frame + 1px overlay border
        self.assertFalse(dlg._use_linux_csd_shadow)
        self.assertIsNone(dlg.inner_frame.graphicsEffect())
        self.assertIsNotNone(dlg._border_overlay)
        self.assertFalse(dlg._border_overlay.isHidden())

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

    def test_settings_always_restores_default_size_and_proportional_rip_math(self):
        # 1. Exact proportional rip positioning (PO example: 1920px bar, click at 1500px -> 78.125%,
        # new width 1344px -> cursor stays at 1050px from left edge of restored window)
        sg = QRect(0, 0, 1920, 1080)
        r = compute_proportional_rip_rect(
            cursor_x=1500, cursor_y=20, click_x=1500, click_y=16,
            maximized_w=1920, target_w=1344, target_h=756, screen_geo=sg,
        )
        self.assertEqual(r.width(), 1344)
        self.assertEqual(r.height(), 756)
        self.assertEqual(r.x(), 450)  # 1500 - 450 == 1050 (78.125% of 1344)
        self.assertEqual(1500 - r.x(), 1050)
        self.assertEqual(r.y(), 4)

        # Extreme right-side grab (e.g. 92% of bar) must NOT be capped at 82%, and stays within screen
        r_right = compute_proportional_rip_rect(
            cursor_x=1766, cursor_y=18, click_x=1766, click_y=16,
            maximized_w=1920, target_w=750, target_h=580, screen_geo=sg,
        )
        self.assertGreater(r_right.x(), 1000)
        self.assertLessEqual(r_right.right(), sg.right())
        self.assertGreaterEqual(1766, r_right.left())
        self.assertLessEqual(1766, r_right.right())

        # Negative secondary monitor clamping
        neg_sg = QRect(-1920, 0, 1920, 1080)
        r_neg = compute_proportional_rip_rect(
            cursor_x=-200, cursor_y=16, click_x=1720, click_y=16,
            maximized_w=1920, target_w=750, target_h=580, screen_geo=neg_sg,
        )
        self.assertGreaterEqual(r_neg.left(), neg_sg.left())
        self.assertLessEqual(r_neg.right(), neg_sg.right())

        # 2. SettingsDialog ALWAYS restores to its small default size (both btn_max AND rip),
        # even after manual edge resize before maximizing!
        engine = self._create_mock_engine()
        from PySide6.QtWidgets import QMainWindow
        main_win = QMainWindow()
        main_win._always_on_top_active = False
        fake_screen = MagicMock()
        fake_screen.availableGeometry.return_value = sg

        dlg = SettingsDialog(engine, main_win)
        expected_w = min(config.SETTINGS_WINDOW_W, sg.width())
        expected_h = min(config.SETTINGS_WINDOW_H, sg.height())
        with patch.object(dlg, "screen", return_value=fake_screen), \
             patch("gui.components.mixins.QGuiApplication.screenAt", return_value=fake_screen):
            # Simulate user manually resizing Settings larger, then maximizing
            dlg._last_normal_geo = QRect(100, 80, 1200, 850)
            dlg._snapshot_pre_maximize_geometry()
            dlg.resize(1920, 1080)
            # Exiting via btn_max -> MUST return to original small default size (not 1200x850, not 70%)
            dlg._restore_after_unmaximize(via_button=True)
            self.assertEqual(dlg.size(), QSize(expected_w, expected_h))

            # Exiting via rip -> MUST also use small default size
            dlg._restoring_from_max = False
            dlg.resize(1920, 1080)
            dlg._restore_after_unmaximize(via_button=False)
            self.assertEqual(dlg.size(), QSize(expected_w, expected_h))
        dlg.close()
        main_win.close()

    def test_zero_custom_shadows_opaque_solid_borders_and_win11_native_event_safety(self):
        # 1. Verify nativeEvent never calls self.winId() (prevents Win11 CreateWindowEx stack overflow)
        import ast
        with open(os.path.join(os.path.dirname(__file__), "..", "src", "gui", "components", "mixins.py"), "r", encoding="utf-8") as f:
            mixins_src = f.read()
        tree = ast.parse(mixins_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "nativeEvent":
                src_seg = ast.get_source_segment(mixins_src, node) or ""
                has_winid_call = any(
                    isinstance(c, ast.Call)
                    and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "winId"
                    for c in ast.walk(node)
                )
                self.assertFalse(has_winid_call, "nativeEvent must never call self.winId()")
                self.assertIn("msg.hWnd", src_seg)

        # 2. Verify zero QGraphicsDropShadowEffect & zero WA_TranslucentBackground across all windows/dialogs/splash
        engine = self._create_mock_engine()
        from PySide6.QtWidgets import QMainWindow
        parent = QMainWindow()
        parent._always_on_top_active = False
        parent.lang = "en"
        parent.engine = engine

        splash = BootSplash()
        msg_box = CustomMsgBox(parent, "Notice", "Clean solid border test.", "OK", "Cancel")
        unsaved = UnsavedChangesDialog(parent, {"theme": ("dark", "light")}, {"theme": "Theme"})
        marker = MarkerDialog(parent, "en", "tool_custom_markers")
        export_dlg = ExportDialog(parent, engine, [], [])
        telem = TelemetryPopup(engine, parent=parent)
        consent = CrashReportConsentDialog(engine, parent=parent)
        upd = UpdateNotifyDialog(parent, "en", "4.0.1", "4.0.2", "https://github.com", "https://gitlab.com", False, False, ".", "- Fix")
        mig = V4MigrationDialog(lang="en", parent=parent)

        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        for name, w in (
            ("boot_splash_solid", splash),
            ("msgbox_solid", msg_box),
            ("unsaved_solid", unsaved),
            ("marker_solid", marker),
            ("export_solid", export_dlg),
            ("telemetry_solid", telem),
            ("consent_solid", consent),
            ("update_solid", upd),
            ("migration_solid", mig),
        ):
            self.assertFalse(w.testAttribute(Qt.WA_TranslucentBackground), f"{name} must be opaque")
            self.assertFalse(bool(w.windowFlags() & Qt.NoDropShadowWindowHint), f"{name} should allow native OS shadow")
            self.assertEqual(w.findChildren(QGraphicsDropShadowEffect), [], f"{name} must not have QGraphicsDropShadowEffect")
            inner = getattr(w, "inner_frame", None)
            if inner is not None:
                self.assertIsNone(inner.graphicsEffect())

        splash.show()
        msg_box.show()
        app.processEvents()
        self.assertTrue(splash.grab().save(os.path.join(art_dir, "point3_boot_splash_solid.png")))
        self.assertTrue(msg_box.grab().save(os.path.join(art_dir, "point3_msgbox_solid.png")))

        for w in (splash, msg_box, unsaved, marker, export_dlg, telem, consent, upd, mig, parent):
            w.close()

    def test_win11_sharp_corners_and_half_screen_getwindowrect_restore_contract(self):
        # 1. Verify DWMWCP_DONOTROUND (33 = 1) is enforced across showEvent, _dwm_uncloak, WinIdChange & nativeEvent
        from gui.components.mixins import FramelessWindowMixin, _WindowBorderOverlay
        import inspect

        mixins_src = inspect.getsource(FramelessWindowMixin)
        self.assertIn("_enforce_win_dwm_attributes", mixins_src)
        self.assertIn("SetWindowRgn", mixins_src)  # Clears Win11 uxtheme WS_POPUP|WS_CAPTION top-corner region
        self.assertIn("~0x80000000", mixins_src)  # Strips WS_POPUP so WS_OVERLAPPEDWINDOW has zero clipping region
        self.assertIn("WinIdChange", mixins_src)
        self.assertIn("0x007D", mixins_src)  # WM_STYLECHANGED
        self.assertIn("0x031E", mixins_src)  # WM_DWMCOMPOSITIONCHANGED
        self.assertIn("GetWindowRect", mixins_src)  # Half-screen Aero Snap capture (not frozen rcNormalPosition)
        self.assertIn("_verify_win_button_restore", mixins_src)

        # 2. Simulate _record_normal_geometry + _sync_win_normal_placement on Windows 11 half-screen Snap
        import ctypes
        from ctypes import wintypes

        class RECT_MATCH:
            def __init__(self, l, t, r, b):
                self.left, self.top, self.right, self.bottom = l, t, r, b

        recorded_wp = []

        class _FakeUser32:
            def IsIconic(self, hwnd):
                return 0

            def IsZoomed(self, hwnd):
                return int(self._zoomed)

            def GetWindowRect(self, hwnd, ptr):
                r = getattr(ptr, "_obj", None)
                if r is None:
                    r = ctypes.cast(ptr, ctypes.POINTER(wintypes.RECT))[0]
                r.left, r.top, r.right, r.bottom = 960, 0, 1920, 1032
                return 1

            def MonitorFromPoint(self, pt, flags):
                return 101

            def MonitorFromWindow(self, hwnd, flags):
                return 101

            def GetMonitorInfoW(self, hmon, ptr):
                mi = getattr(ptr, "_obj", None)
                if mi is None:
                    class _MI(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", wintypes.DWORD),
                            ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT),
                            ("dwFlags", wintypes.DWORD),
                        ]
                    mi = ctypes.cast(ptr, ctypes.POINTER(_MI))[0]
                mi.rcMonitor = wintypes.RECT(0, 0, 1920, 1080)
                mi.rcWork = wintypes.RECT(0, 0, 1920, 1032)
                return 1

            def GetWindowPlacement(self, hwnd, ptr):
                wp = getattr(ptr, "_obj", None)
                if wp is None:
                    class _WP(ctypes.Structure):
                        _fields_ = [
                            ("length", wintypes.UINT),
                            ("flags", wintypes.UINT),
                            ("showCmd", wintypes.UINT),
                            ("ptMinPosition", wintypes.POINT),
                            ("ptMaxPosition", wintypes.POINT),
                            ("rcNormalPosition", wintypes.RECT),
                        ]
                    wp = ctypes.cast(ptr, ctypes.POINTER(_WP))[0]
                # Windows leaves rcNormalPosition frozen at old 70% centered rect on Aero Snap
                wp.rcNormalPosition = wintypes.RECT(288, 154, 1632, 876)
                wp.showCmd = 3 if self._zoomed else 1
                return 1

            def SetWindowPlacement(self, hwnd, ptr):
                wp = getattr(ptr, "_obj", None)
                if wp is None:
                    class _WP(ctypes.Structure):
                        _fields_ = [
                            ("length", wintypes.UINT),
                            ("flags", wintypes.UINT),
                            ("showCmd", wintypes.UINT),
                            ("ptMinPosition", wintypes.POINT),
                            ("ptMaxPosition", wintypes.POINT),
                            ("rcNormalPosition", wintypes.RECT),
                        ]
                    wp = ctypes.cast(ptr, ctypes.POINTER(_WP))[0]
                r = wp.rcNormalPosition
                recorded_wp.append((r.left, r.top, r.right, r.bottom))
                return 1

        fake_u32 = _FakeUser32()
        fake_u32._zoomed = False
        fake_dwm_calls = []

        class _FakeDwm:
            def DwmSetWindowAttribute(self, hwnd, attr, ptr, sz):
                obj = getattr(ptr, "_obj", None)
                val = obj.value if obj is not None else ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint))[0]
                fake_dwm_calls.append((int(attr), int(val)))
                return 0

            def DwmExtendFrameIntoClientArea(self, hwnd, ptr):
                return 0

        from unittest.mock import patch

        class _FakeScreen:
            def availableGeometry(self):
                return QRect(0, 0, 1920, 1032)

        class _FakeWin(FramelessWindowMixin):
            def __init__(self):
                self._is_win = True
                self._is_root = True
                self._is_popup = False
                self._always_restore_default_size = False
                self._normal_ratio = 0.70
                self._last_normal_geo = None
                self._pre_maximize_geometry = None
                self._last_normal_win_rect = None
                self._pre_maximize_win_rect = None
                self._restoring_from_max = False

            def isVisible(self):
                return True

            def isMinimized(self):
                return False

            def _is_effectively_maximized(self):
                return bool(fake_u32._zoomed)

            def geometry(self):
                return QRect(960, 0, 960, 1032)

            def screen(self):
                return _FakeScreen()

            def testAttribute(self, attr):
                return True

            def winId(self):
                return 9999

            def devicePixelRatioF(self):
                return 1.0

        fw = _FakeWin()
        with (
            patch("gui.components.mixins._get_win32_apis", return_value=(fake_u32, None, _FakeDwm())),
            patch("gui.components.mixins.QGuiApplication.screenAt", return_value=_FakeScreen()),
        ):
            # Step 1: Window snapped to right half -> GetWindowRect must capture (960, 0, 1920, 1032)
            fw._record_normal_geometry()
            self.assertEqual(fw._last_normal_win_rect, (960, 0, 1920, 1032))

            # Step 2: Window maximizes -> snapshot right half, set rcNormalPosition to 70% for Aero rip
            fw._snapshot_pre_maximize_geometry()
            fake_u32._zoomed = True
            fw._sync_win_normal_placement(use_button_restore=False)
            self.assertEqual(recorded_wp[-1], (288, 155, 1632, 877))

            # Step 3: User clicks btn_max -> MUST restore exact right half (960, 0, 1920, 1032)!
            fw._sync_win_normal_placement(use_button_restore=True)
            self.assertEqual(recorded_wp[-1], (960, 0, 1920, 1032))

            # Step 4: DWM corner preference MUST enforce DWMWCP_DONOTROUND (33 -> 1)
            # and dark COLORREF border #101010 (34 -> 0x00101010) instead of white taskbar outline
            fw._enforce_win_dwm_attributes(9999, include_extend=True)
            self.assertIn((33, 1), fake_dwm_calls)
            self.assertIn((34, 0x00101010), fake_dwm_calls)


if __name__ == "__main__":
    unittest.main()
