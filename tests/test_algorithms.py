#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Heuristic tests for algorithms.py.
Verifies retake detection, two-layer visual status priority (manual_status > algo_status),
and text processing / fuzzy comparison routines.
"""

import copy
import unittest
import algorithms


class TestAlgorithms(unittest.TestCase):
    def test_retake_detection(self):
        """Verify repeated phrases are detected and marked as repeat."""
        words = [
            {'id': 1, 'text': 'I', 'start': 1.0, 'end': 1.2, 'status': None},
            {'id': 2, 'text': 'think', 'start': 1.3, 'end': 1.6, 'status': None},
            {'id': 3, 'text': 'that', 'start': 1.7, 'end': 1.9, 'status': None},
            {'id': 4, 'text': 'I', 'start': 2.5, 'end': 2.7, 'status': None},
            {'id': 5, 'text': 'think', 'start': 2.8, 'end': 3.1, 'status': None},
            {'id': 6, 'text': 'that', 'start': 3.2, 'end': 3.4, 'status': None},
            {'id': 7, 'text': 'works', 'start': 3.5, 'end': 3.7, 'status': None},
        ]

        algorithms.analyze_repeats(words)

        # Repetition should mark words 1-6 as repeat
        statuses = [w.get('status') for w in words]
        self.assertEqual(statuses[0], 'repeat')
        self.assertEqual(statuses[1], 'repeat')
        self.assertEqual(statuses[2], 'repeat')
        self.assertNotEqual(statuses[6], 'repeat')

    def test_manual_status_priority_over_algo_status(self):
        """Verify that user manual overrides (manual_status) are never overwritten by analyze_repeats."""
        words = [
            {'id': 1, 'text': 'I', 'start': 1.0, 'end': 1.2, 'status': 'normal', 'manual_status': 'normal'},
            {'id': 2, 'text': 'think', 'start': 1.3, 'end': 1.6, 'status': None},
            {'id': 3, 'text': 'that', 'start': 1.7, 'end': 1.9, 'status': None},
            {'id': 4, 'text': 'I', 'start': 2.5, 'end': 2.7, 'status': None},
            {'id': 5, 'text': 'think', 'start': 2.8, 'end': 3.1, 'status': None},
            {'id': 6, 'text': 'that', 'start': 3.2, 'end': 3.4, 'status': None},
        ]

        algorithms.analyze_repeats(words)

        # Word 1 has manual_status='normal', so it MUST remain 'normal'
        self.assertEqual(words[0]['status'], 'normal')
        self.assertEqual(words[0]['manual_status'], 'normal')

    def test_propagate_status_change_standard_word(self):
        """Verify propagate_status_change sets base layer manual_status."""
        words = [
            {'id': 101, 'text': 'important', 'status': None, 'manual_status': None},
            {'id': 102, 'text': 'word', 'status': None, 'manual_status': None},
        ]

        updates = algorithms.propagate_status_change(words, 0, 'bad')

        self.assertEqual(updates, [(101, 'bad')])
        self.assertEqual(words[0]['status'], 'bad')
        self.assertEqual(words[0]['manual_status'], 'bad')
        self.assertTrue(words[0]['selected'])

    def test_propagate_status_change_inaudible_block(self):
        """Verify propagate_status_change expands to contiguous inaudible block."""
        words = [
            {'id': 1, 'text': 'start', 'status': None, 'is_inaudible': False},
            {'id': 2, 'text': '[inaudible1]', 'status': 'inaudible', 'is_inaudible': True},
            {'id': 3, 'text': '[inaudible2]', 'status': 'inaudible', 'is_inaudible': True},
            {'id': 4, 'text': 'end', 'status': None, 'is_inaudible': False},
        ]

        updates = algorithms.propagate_status_change(words, 1, 'bad')

        # Both inaudible words (id 2 and 3) should be updated
        self.assertEqual(len(updates), 2)
        updated_ids = [u[0] for u in updates]
        self.assertIn(2, updated_ids)
        self.assertIn(3, updated_ids)
        self.assertEqual(words[1]['manual_status'], 'bad')
        self.assertEqual(words[2]['manual_status'], 'bad')

    def test_text_helpers_fuzzy_matching(self):
        """Verify fuzzy match and super_clean string helpers."""
        self.assertEqual(algorithms.super_clean("  Hello, World! 123  "), "helloworld123")
        self.assertTrue(algorithms.check_fuzzy_match("resolve", "resolv"))
        self.assertFalse(algorithms.check_fuzzy_match("davinci", "premiere"))

    def test_auto_filler_preserves_manual_status(self):
        """Verify apply_auto_filler_logic respects manual_status two-layer priority invariant."""
        words = [
            {'id': 1, 'text': 'um', 'status': 'normal', 'manual_status': 'normal'},
            {'id': 2, 'text': 'uh', 'status': None, 'manual_status': None},
        ]
        algorithms.apply_auto_filler_logic(words, ['um', 'uh'], True)
        self.assertEqual(words[0]['status'], 'normal', "User manual_status was overwritten by filler pass")
        self.assertEqual(words[0]['manual_status'], 'normal')
        self.assertEqual(words[1]['status'], 'bad', "Filler word without manual override was not marked bad")


if __name__ == "__main__":
    unittest.main()

