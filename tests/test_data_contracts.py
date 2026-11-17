#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data contract and invariant tests for BadWords.
Verifies words_data[0] metadata preservation (meta_global_silence, session tags),
word item structural integrity, and edge case stability (empty lists, boundary values).
"""

import copy
import unittest
import osdoc
from engine.audio_engine import AudioEngine


class TestDataContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = osdoc.OSDoctor()
        cls.engine = AudioEngine(cls.doc, None)

    def test_words_data_zero_metadata_preservation(self):
        """Verify words_data[0] preserves metadata across timeline structure calculations."""
        meta_silence = [{'s': 0.0, 'e': 1.0}, {'s': 2.0, 'e': 3.0}]
        custom_meta = {'session_id': 'bw_test_123', 'timeline_track': 1}
        session_tags = ['take_1', 'cam_a', 'raw']

        words_data = [
            {
                'id': 1, 'word': 'First', 'text': 'First',
                'start': 1.0, 'end': 2.0, 'status': 'normal',
                'meta_global_silence': meta_silence,
                'custom_meta': custom_meta,
                'session_tags': session_tags
            },
            {
                'id': 2, 'word': 'Second', 'text': 'Second',
                'start': 3.0, 'end': 4.0, 'status': 'normal'
            }
        ]

        # Calculate structure with cuts
        surviving, cuts = self.engine.calculate_timeline_structure_with_cuts(
            words_data, 24.0, {'silence_cut': True}
        )

        # Invariant checks on words_data[0]
        self.assertIn('meta_global_silence', words_data[0], "words_data[0] lost meta_global_silence")
        self.assertEqual(words_data[0]['meta_global_silence'], meta_silence)
        self.assertEqual(words_data[0]['custom_meta'], custom_meta)
        self.assertEqual(words_data[0]['session_tags'], session_tags)

    def test_empty_words_data_safety(self):
        """Verify that empty words_data does not raise exceptions and returns empty structures."""
        surviving, cuts = self.engine.calculate_timeline_structure_with_cuts([], 24.0, {'silence_cut': True})
        self.assertEqual(surviving, [])
        self.assertEqual(cuts, [])

    def test_words_data_required_fields(self):
        """Verify that calculation annotates anchor positions without corrupting base keys."""
        words_data = [
            {'id': 1, 'word': 'Hello', 'text': 'Hello', 'start': 0.5, 'end': 1.0, 'status': 'normal'}
        ]

        surviving, cuts = self.engine.calculate_timeline_structure_with_cuts(words_data, 30.0, {})
        w = words_data[0]

        # Mandatory invariant keys
        self.assertEqual(w['id'], 1)
        self.assertEqual(w['word'], 'Hello')
        self.assertAlmostEqual(w['start'], 0.5)
        self.assertAlmostEqual(w['end'], 1.0)
        self.assertEqual(w['status'], 'normal')
        # Anchor start should have been set
        self.assertIn('anchor_start', w)


if __name__ == "__main__":
    unittest.main()

