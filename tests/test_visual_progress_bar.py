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

        # Test at 50%
        bar._value = 50.0
        pix_50 = bar.grab()
        img_50 = pix_50.toImage()
        out_50 = os.path.join(self.artifacts_dir, "liquid_progress_bar_50pct.png")
        img_50.save(out_50)
        self.assertTrue(os.path.isfile(out_50))

        # Corner (0,0) must NOT be filled with track (#2b2b2b) or progress green
        c_corner_50 = QColor(img_50.pixel(0, 0))
        c_prog_50 = QColor(img_50.pixel(50, h // 2))
        c_track_50 = QColor(img_50.pixel(150, h // 2))

        # Track color is #2b2b2b (43, 43, 43)
        self.assertAlmostEqual(c_track_50.red(), 43, delta=5)
        self.assertAlmostEqual(c_track_50.green(), 43, delta=5)
        self.assertAlmostEqual(c_track_50.blue(), 43, delta=5)

        # Progress color at (50, 8) must have strong green component
        self.assertGreater(c_prog_50.green(), c_prog_50.red())

        # Corner at (0, 0) must be clipped outside track & progress (i.e. background color, not track #2b2b2b or green)
        self.assertNotEqual((c_corner_50.red(), c_corner_50.green(), c_corner_50.blue()),
                            (c_track_50.red(), c_track_50.green(), c_track_50.blue()))

        # Test at 100%
        bar._value = 100.0
        pix_100 = bar.grab()
        img_100 = pix_100.toImage()
        out_100 = os.path.join(self.artifacts_dir, "liquid_progress_bar_100pct.png")
        img_100.save(out_100)
        self.assertTrue(os.path.isfile(out_100))

        c_corner_100 = QColor(img_100.pixel(0, 0))
        c_prog_100 = QColor(img_100.pixel(w - 20, h // 2))

        # Corner at 100% must NOT be painted with green progress fill (preventing setClipRect regression)
        self.assertNotEqual((c_corner_100.red(), c_corner_100.green()),
                            (c_prog_100.red(), c_prog_100.green()))

    def test_indeterminate_rendering(self):
        """Verify indeterminate pill renders smoothly within clipped bounds."""
        w, h = 200, 16
        bar = LiquidProgressBar()
        bar.setFixedSize(w, h)
        bar.show()

        bar._indeterminate = True
        bar._indet_offset = 0.5
        pix_indet = bar.grab()
        img_indet = pix_indet.toImage()
        out_indet = os.path.join(self.artifacts_dir, "liquid_progress_bar_indeterminate.png")
        img_indet.save(out_indet)
        self.assertTrue(os.path.isfile(out_indet))

        # Pill center should contain active color
        c_center = QColor(img_indet.pixel(w // 2, h // 2))
        self.assertGreater(c_center.green(), 40)


if __name__ == "__main__":
    unittest.main()
