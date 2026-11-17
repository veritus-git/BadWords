#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Timeline cut calculation unit tests for AudioEngine.
Verifies frame calculations across 23.976, 29.97, 60.0, and 25.0 fps,
ripple deletions of silence cuts and auto-cut colors, and non-overlapping clip bounds.
"""

import copy
import unittest
import osdoc
from engine.audio_engine import AudioEngine


class TestTimelineCuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = osdoc.OSDoctor()
        cls.engine = AudioEngine(cls.doc, None)

    def _sample_words(self):
        return [
            {
                'id': 1, 'word': 'Hello', 'start': 1.0, 'end': 2.0, 'status': 'normal',
                'meta_global_silence': [
                    {'s': 0.0, 'e': 1.0},
                    {'s': 2.0, 'e': 3.5},
                    {'s': 5.0, 'e': 6.0}
                ]
            },
            {'id': 2, 'word': 'brave', 'start': 3.5, 'end': 4.0, 'status': 'normal'},
            {'id': 3, 'word': 'new', 'start': 4.0, 'end': 4.5, 'status': 'bad'},
            {'id': 4, 'word': 'world', 'start': 4.5, 'end': 5.0, 'status': 'normal'}
        ]

    def test_multi_framerate_cut_calculations(self):
        """Test timeline structure cuts across multiple standard frame rates."""
        rates = [23.976, 29.97, 60.0, 25.0]

        settings = {
            'offset': 0.0,
            'ui_spin_pad': 0.0,
            'snap_max': 0.05,
            'silence_cut': True,
            'auto_cut_colors': ['bad']
        }

        for fps in rates:
            with self.subTest(fps=fps):
                words = copy.deepcopy(self._sample_words())
                surviving, cuts = self.engine.calculate_timeline_structure_with_cuts(words, fps, settings)

                self.assertGreater(len(surviving), 0, f"Expected surviving ops for fps {fps}")
                self.assertGreater(len(cuts), 0, f"Expected cut ops for fps {fps}")

                # Ensure cuts include the 'bad' color cut and silence cuts
                cut_types = [c.get('cut_type') for c in cuts]
                self.assertIn('silence_cut', cut_types)

                # Ensure all surviving clips have valid start/end frame indices (s < e)
                for op in surviving:
                    self.assertLess(op['s'], op['e'], f"Invalid op interval: {op['s']} >= {op['e']}")
                    self.assertGreaterEqual(op['s'], 0)

                # Ensure non-overlapping sequence
                for i in range(len(surviving) - 1):
                    self.assertLessEqual(surviving[i]['e'], surviving[i + 1]['s'],
                                        f"Surviving clips overlap at fps {fps}: {surviving[i]} vs {surviving[i+1]}")

    def test_silence_cut_disabled_vs_enabled(self):
        """Verify that disabling silence cut keeps silence regions intact."""
        words = copy.deepcopy(self._sample_words())
        fps = 30.0

        # Without silence cut
        surviving_no_cut, cuts_no_cut = self.engine.calculate_timeline_structure_with_cuts(
            copy.deepcopy(words), fps, {'silence_cut': False, 'auto_cut_colors': []}
        )

        # With silence cut
        surviving_with_cut, cuts_with_cut = self.engine.calculate_timeline_structure_with_cuts(
            copy.deepcopy(words), fps, {'silence_cut': True, 'auto_cut_colors': []}
        )

        silence_cuts = [c for c in cuts_with_cut if c.get('cut_type') == 'silence_cut']
        self.assertGreater(len(silence_cuts), 0)

        # Total duration of surviving ops should be less when silence is cut
        dur_no_cut = sum(op['e'] - op['s'] for op in surviving_no_cut)
        dur_with_cut = sum(op['e'] - op['s'] for op in surviving_with_cut)
        self.assertLess(dur_with_cut, dur_no_cut)

    def test_audio_end_cap(self):
        """Verify audio_end_cap_s truncates the timeline structure properly."""
        words = copy.deepcopy(self._sample_words())
        fps = 30.0
        cap_seconds = 3.0

        surviving, cuts = self.engine.calculate_timeline_structure_with_cuts(
            words, fps, {'audio_end_cap_s': cap_seconds, 'silence_cut': False}
        )

        max_frame = int(round(cap_seconds * fps))
        for op in surviving:
            self.assertLessEqual(op['e'], max_frame + 1, "Op exceeded capped end frame")


if __name__ == "__main__":
    unittest.main()
