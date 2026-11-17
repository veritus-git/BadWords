#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FCP7 XML validity and structure unit tests for assembler.py.
Verifies that generated Final Cut Pro 7 XML files (<xmeml version="5">)
are syntactically valid, frame-accurate, and contain all required tracks and metadata.
"""

import os
import unittest
import xml.etree.ElementTree as ET
import assembler


class TestAssemblerXML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(cls.artifacts_dir, exist_ok=True)
        cls.output_xml = os.path.join(cls.artifacts_dir, "test_fcp7_output.xml")

    def tearDown(self):
        if os.path.isfile(self.output_xml):
            try:
                os.remove(self.output_xml)
            except Exception:
                pass

    def test_build_fcp7_xml_validity_and_schema(self):
        """Verify XML generation produces well-formed, compliant FCP7 XML."""
        clips_info = [{
            'path': '/media/footage/interview_take1.mp4',
            'offset': 0.0,
            'duration': 20.0,
            'has_video': True,
            'audio_channels': 2
        }]

        # Two cut segments: 0..48 (48 frames) and 72..120 (48 frames) -> total 96 frames
        ops = [
            {'s': 0, 'e': 48, 'type': 'normal'},
            {'s': 72, 'e': 120, 'type': 'normal'},
        ]

        fps = 24.0
        success, msg = assembler.build_standalone_fcp7_xml(
            clips_info, ops, self.output_xml, fps=fps, width=1920, height=1080,
            timeline_name="Test BadWords Sequence"
        )

        self.assertTrue(success, f"FCP7 XML build failed: {msg}")
        self.assertTrue(os.path.isfile(self.output_xml))

        # Parse XML tree to verify syntax and structure
        tree = ET.parse(self.output_xml)
        root = tree.getroot()

        # Root element verification
        self.assertEqual(root.tag, "xmeml")
        self.assertEqual(root.attrib.get("version"), "5")

        # Sequence verification
        seq = root.find("sequence")
        self.assertIsNotNone(seq, "Missing <sequence> element")
        self.assertEqual(seq.find("name").text, "Test BadWords Sequence")
        self.assertEqual(seq.find("duration").text, "96")

        # Rate verification
        rate_el = seq.find("rate")
        self.assertIsNotNone(rate_el, "Missing <rate> element")
        self.assertEqual(rate_el.find("timebase").text, "24")

        # Video track and clip items
        media_el = seq.find("media")
        self.assertIsNotNone(media_el, "Missing <media> element")
        video_el = media_el.find("video")
        self.assertIsNotNone(video_el, "Missing <video> element")

        video_tracks = video_el.findall("track")
        self.assertGreaterEqual(len(video_tracks), 1, "Missing video track")

        v1_clips = video_tracks[0].findall("clipitem")
        self.assertEqual(len(v1_clips), 2, "Expected 2 video clipitems on V1")

        # Clip 1 bounds
        c1 = v1_clips[0]
        self.assertEqual(c1.find("start").text, "0")
        self.assertEqual(c1.find("end").text, "48")
        self.assertEqual(c1.find("in").text, "0")
        self.assertEqual(c1.find("out").text, "48")

        # Clip 2 bounds (ripple ripple destination time starts at 48)
        c2 = v1_clips[1]
        self.assertEqual(c2.find("start").text, "48")
        self.assertEqual(c2.find("end").text, "96")
        self.assertEqual(c2.find("in").text, "72")
        self.assertEqual(c2.find("out").text, "120")

        # Audio tracks verification
        audio_el = media_el.find("audio")
        self.assertIsNotNone(audio_el, "Missing <audio> element")
        audio_tracks = audio_el.findall("track")
        self.assertEqual(len(audio_tracks), 2, "Expected 2 audio tracks (stereo)")

    def test_build_fcp7_xml_empty_inputs(self):
        """Verify graceful error reporting when no operations or clips are provided."""
        success, msg = assembler.build_standalone_fcp7_xml([], [{'s': 0, 'e': 10}], self.output_xml)
        self.assertFalse(success)

        success, msg = assembler.build_standalone_fcp7_xml([{'path': 'a.mp4'}], [], self.output_xml)
        self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()
