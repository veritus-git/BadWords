#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visual regression tests for LiquidProgressBar.
Ensures rounded corners are preserved and clipping prevents squared-off corners.
Saves PNG artifacts to tests/artifacts/.
"""

import os
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QApplication.instance() or QApplication([])

from gui.widgets.progress_bar import LiquidProgressBar


class TestLiquidProgressBarVisual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(cls.artifacts_dir, exist_ok=True)

    def test_determinate_rounded_corners_and_clipping(self):
        """Verify that corners are rounded and not squared off at 50% and 100% progress."""
        w, h = 200, 16
        bar = LiquidProgressBar()
        bar.setFixedSize(w, h)
        bar.show()

        # Test at 1% (tiny fill should smoothly stay within track caps without pinching or clipping)
        bar._value = 1.0
        pix_1 = bar.grab()
        img_1 = pix_1.toImage()
        out_1 = os.path.join(self.artifacts_dir, "liquid_progress_bar_1pct.png")
        img_1.save(out_1)
        self.assertTrue(os.path.isfile(out_1))
        for cx, cy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            c = QColor(img_1.pixel(cx, cy))
            c_mid_right = QColor(img_1.pixel(w - 20, h // 2))
            self.assertNotEqual(
                (c.red(), c.green(), c.blue()),
                (c_mid_right.red(), c_mid_right.green(), c_mid_right.blue()),
                f"Corner ({cx}, {cy}) squared off at 1%",
            )

        # Test at 50%
        bar._value = 50.0
        pix_50 = bar.grab()
        img_50 = pix_50.toImage()
        out_50 = os.path.join(self.artifacts_dir, "liquid_progress_bar_50pct.png")
        img_50.save(out_50)
        self.assertTrue(os.path.isfile(out_50))

        # Corner pixels to test: (0, 0), (w-1, 0), (0, h-1), (w-1, h-1)
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]

        # Corner (0,0) must NOT be filled with track (#2b2b2b) or progress green
        c_prog_50 = QColor(img_50.pixel(50, h // 2))
        c_track_50 = QColor(img_50.pixel(150, h // 2))

        # Track color is #2b2b2b (43, 43, 43)
        self.assertAlmostEqual(c_track_50.red(), 43, delta=5)
        self.assertAlmostEqual(c_track_50.green(), 43, delta=5)
        self.assertAlmostEqual(c_track_50.blue(), 43, delta=5)

        # Progress color at (50, 8) must have strong green component
        self.assertGreater(c_prog_50.green(), c_prog_50.red())

        # All 4 corners at 50% must be clipped outside track & progress (i.e. background color)
        for cx, cy in corners:
            c = QColor(img_50.pixel(cx, cy))
            self.assertNotEqual((c.red(), c.green(), c.blue()),
                                (c_track_50.red(), c_track_50.green(), c_track_50.blue()),
                                f"Corner ({cx}, {cy}) painted with track color at 50%")

        # Test at 100%
        bar._value = 100.0
        pix_100 = bar.grab()
        img_100 = pix_100.toImage()
        out_100 = os.path.join(self.artifacts_dir, "liquid_progress_bar_100pct.png")
        img_100.save(out_100)
        self.assertTrue(os.path.isfile(out_100))

        c_prog_100 = QColor(img_100.pixel(w - 20, h // 2))

        # All 4 corners at 100% must NOT be painted with green progress fill (preventing setClipRect regression)
        for cx, cy in corners:
            c = QColor(img_100.pixel(cx, cy))
            self.assertNotEqual((c.red(), c.green()),
                                (c_prog_100.red(), c_prog_100.green()),
                                f"Corner ({cx}, {cy}) painted with green fill at 100%")

    def test_indeterminate_rendering(self):
        """Verify indeterminate pill renders smoothly within clipped bounds without squaring off corners."""
        w, h = 200, 16
        bar = LiquidProgressBar()
        bar.setFixedSize(w, h)
        bar.show()

        bar._indeterminate = True

        # Phase 1: Pill entering on left (offset=0.05). Left corners must NOT be squared-off green!
        bar._indet_offset = 0.05
        img_entering = bar.grab().toImage()
        c_entering_pill = QColor(img_entering.pixel(5, h // 2))
        self.assertGreater(c_entering_pill.green(), c_entering_pill.red(), "Entering pill should be green at x=5")
        c_top_left = QColor(img_entering.pixel(0, 0))
        c_bot_left = QColor(img_entering.pixel(0, h - 1))
        self.assertNotEqual((c_top_left.red(), c_top_left.green()),
                            (c_entering_pill.red(), c_entering_pill.green()),
                            "Top-left corner squared off during indeterminate entry (setClipRect regression)")
        self.assertNotEqual((c_bot_left.red(), c_bot_left.green()),
                            (c_entering_pill.red(), c_entering_pill.green()),
                            "Bottom-left corner squared off during indeterminate entry (setClipRect regression)")

        # Phase 2: Pill centered (offset=0.5)
        bar._indet_offset = 0.5
        pix_indet = bar.grab()
        img_indet = pix_indet.toImage()
        out_indet = os.path.join(self.artifacts_dir, "liquid_progress_bar_indeterminate.png")
        img_indet.save(out_indet)
        self.assertTrue(os.path.isfile(out_indet))

        # Pill center should contain active color
        c_center = QColor(img_indet.pixel(w // 2, h // 2))
        self.assertGreater(c_center.green(), 40)

        # Phase 3: Pill exiting on right (offset=0.95). Right corners must NOT be squared-off green!
        bar._indet_offset = 0.95
        img_exiting = bar.grab().toImage()
        c_exiting_pill = QColor(img_exiting.pixel(w - 6, h // 2))
        self.assertGreater(c_exiting_pill.green(), c_exiting_pill.red(), "Exiting pill should be green near right edge")
        c_top_right = QColor(img_exiting.pixel(w - 1, 0))
        c_bot_right = QColor(img_exiting.pixel(w - 1, h - 1))
        self.assertNotEqual((c_top_right.red(), c_top_right.green()),
                            (c_exiting_pill.red(), c_exiting_pill.green()),
                            "Top-right corner squared off during indeterminate exit (setClipRect regression)")
        self.assertNotEqual((c_bot_right.red(), c_bot_right.green()),
                            (c_exiting_pill.red(), c_exiting_pill.green()),
                            "Bottom-right corner squared off during indeterminate exit (setClipRect regression)")


if __name__ == "__main__":
    unittest.main()

