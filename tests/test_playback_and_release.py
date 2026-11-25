#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Regression tests for BadWords v4.1.0 pre-release fixes:
1. AudioPreviewWidget playback boundary clamping (trimmed DaVinci clips, Play rewind at end,
   skip_forward clamp, trailing skip_cuts stop, and trimmed-head Resolve safety).
2. Real FFmpeg audio muxing into silent DaVinci Resolve video-only 360p proxy MP4.
3. Hardened setupfiles/updater.py whitelist cleanup, .git repo guard, tag URL variants,
   and 4.x -> 4.x live PySide6 DLL-lock skip logic.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("_BW_AUTO_HEAL_ATTEMPTED", "1")
os.environ.setdefault("BADWORDS_DEV", "1")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
SETUPFILES_DIR = os.path.join(REPO_ROOT, "setupfiles")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if SETUPFILES_DIR not in sys.path:
    sys.path.insert(1, SETUPFILES_DIR)

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtMultimedia import QMediaPlayer

import osdoc
from engine.audio_engine import AudioEngine
from gui.components.audio_preview import AudioPreviewWidget
from gui.widgets.sliders import JumpSlider
from handlers.analysis_worker import ResolveTimelineProxyWorker
import updater


def _ensure_qapp():
    return QApplication.instance() or QApplication(["badwords-test"])


class _DummyEngine:
    def __init__(self, tmp_dir):
        self.os_doc = osdoc.OSDoctor()
        self.current_analysis_audio_path = None
        self.last_audio_path = None
        self.current_proxy_video_path = None
        self._prefs = {
            "show_timeline_preview": True,
            "show_video_preview": True,
            "resolve_render_timeline_proxy": False,
        }

    def load_preferences(self):
        return dict(self._prefs)

    def save_preferences(self, data):
        self._prefs.update(data)

    def calculate_timeline_structure_with_cuts(self, words, *args, **kwargs):
        return [], []


class _DummyCanvas:
    def __init__(self, words):
        self.words_data = words

    def update(self):
        pass


class _DummyMainWindow(QMainWindow):
    def __init__(self, tmp_dir, words):
        super().__init__()
        self.engine = _DummyEngine(tmp_dir)
        self.resolve_handler = None
        self.text_canvas = _DummyCanvas(words)
        self._transcription_source = {}
        self._current_clips_layout = []

    def txt(self, key, default=""):
        return default or key

    def _jump_playhead(self, t):
        pass


class TestPlaybackBoundaryAndProxyMux(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_qapp()
        cls.ffmpeg = shutil.which("ffmpeg")
        cls.ffprobe = shutil.which("ffprobe")

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="bw_playback_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_media(self):
        """Generates a real 5.0s MP4 and 2.0s WAV (simulating tail-trimmed Resolve clip)."""
        self.assertIsNotNone(self.ffmpeg, "ffmpeg must be available on host for live media tests")
        mp4_5s = os.path.join(self.tmp_dir, "raw_5s.mp4")
        wav_2s = os.path.join(self.tmp_dir, "trimmed_2s.wav")
        subprocess.run(
            [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=5.0",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5.0",
                "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                mp4_5s,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2.0",
                wav_2s,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return mp4_5s, wav_2s

    def _build_preview(self, dur_s=2.0):
        words = [
            {"word": "Hello", "start": 0.1, "end": 0.6, "status": "keep"},
            {"word": "world", "start": 0.7, "end": min(dur_s, 1.9), "status": "keep"},
        ]
        mw = _DummyMainWindow(self.tmp_dir, words)
        ap = AudioPreviewWidget(mw, mw)
        slider = JumpSlider(mw)
        slider.setRange(0, 1000)
        ap.slider_seek = slider
        ap.waveform_timeline._duration = dur_s
        return mw, ap

    def test_playback_stops_at_trimmed_timeline_end(self):
        mp4_5s, wav_2s = self._make_media()
        mw, ap = self._build_preview(dur_s=2.0)
        try:
            mw._transcription_source = {
                "source_type": "resolve",
                "source_files": [mp4_5s],
                "is_complex_video": False,
            }
            mw.engine.current_analysis_audio_path = wav_2s
            ap.check_audio_availability()
            ap.waveform_timeline._duration = 2.0

            # Simulate active playback whose wall-clock reached 2.08s on a 5.0s raw clip
            ap._start_pos_s = 1.95
            ap._real_start_time = time.time() - 0.13
            with patch.object(ap.player, "playbackState", return_value=QMediaPlayer.PlayingState), \
                 patch.object(ap.player, "pause") as mock_pause, \
                 patch.object(ap.player, "setPosition") as mock_set_pos:
                ap.sync_playback()

            self.assertTrue(mock_pause.called, "Player must pause when audio_t >= timeline duration")
            self.assertLessEqual(ap._start_pos_s, 2.0)
            self.assertEqual(ap.slider_seek.value(), 1000)
            self.assertLessEqual(ap.waveform_timeline._playhead_time, 2.0)
            self.assertTrue(mock_set_pos.called)
            self.assertEqual(mock_set_pos.call_args[0][0], 2000)
        finally:
            if getattr(ap.waveform_timeline, "_worker", None) and ap.waveform_timeline._worker.isRunning():
                ap.waveform_timeline._worker.wait(3000)
            ap.close()
            mw.close()

    def test_toggle_play_at_end_rewinds_to_zero(self):
        _, ap = self._build_preview(dur_s=2.0)
        try:
            ap._start_pos_s = 2.0
            ap._at_timeline_end = True
            with patch.object(ap.player, "playbackState", return_value=QMediaPlayer.PausedState), \
                 patch.object(ap.player, "position", return_value=2000), \
                 patch.object(ap.player, "setPosition") as mock_set_pos, \
                 patch.object(ap.player, "play") as mock_play:
                ap.toggle_play()

            mock_set_pos.assert_called_with(0)
            self.assertEqual(ap._start_pos_s, 0.0)
            self.assertFalse(ap._at_timeline_end)
            mock_play.assert_called_once()
        finally:
            ap.close()

    def test_skip_cuts_at_timeline_end_stops_cleanly(self):
        _, ap = self._build_preview(dur_s=2.0)
        try:
            ap.skip_cuts = True
            ap.waveform_timeline._timeline_segments = [
                {"start_s": 0.0, "end_s": 1.5, "is_cut": False},
                {"start_s": 1.5, "end_s": 2.0, "is_cut": True},
            ]
            ap._start_pos_s = 1.55
            ap._real_start_time = time.time()
            with patch.object(ap.player, "playbackState", return_value=QMediaPlayer.PlayingState), \
                 patch.object(ap.player, "pause") as mock_pause, \
                 patch.object(ap.player, "setPosition") as mock_set_pos:
                ap.sync_playback()

            self.assertTrue(mock_pause.called)
            self.assertEqual(ap._start_pos_s, 2.0)
            self.assertEqual(mock_set_pos.call_args[0][0], 2000)
        finally:
            ap.close()

    def test_skip_forward_clamps_to_duration(self):
        _, ap = self._build_preview(dur_s=2.0)
        try:
            ap._start_pos_s = 1.0
            with patch.object(ap.player, "playbackState", return_value=QMediaPlayer.PausedState), \
                 patch.object(ap.player, "setPosition") as mock_set_pos:
                ap.skip_forward()

            self.assertEqual(ap._start_pos_s, 2.0)
            mock_set_pos.assert_called_with(2000)
        finally:
            ap.close()

    def test_trimmed_head_resolve_never_loads_raw_video(self):
        mp4_5s, wav_2s = self._make_media()
        mw, ap = self._build_preview(dur_s=2.0)
        try:
            # Single Resolve clip with left_offset > 0 (is_complex_video=True) and proxy disabled
            mw._transcription_source = {
                "source_type": "resolve",
                "source_files": [mp4_5s],
                "is_complex_video": True,
            }
            mw._current_clips_layout = [{"name": "Clip1", "start_s": 0.0, "end_s": 2.0}]
            mw.engine.current_analysis_audio_path = wav_2s
            ap.check_audio_availability()

            self.assertEqual(ap._source_audio_path, wav_2s)
            self.assertNotEqual(ap._source_audio_path, mp4_5s)
        finally:
            if getattr(ap.waveform_timeline, "_worker", None) and ap.waveform_timeline._worker.isRunning():
                ap.waveform_timeline._worker.wait(3000)
            ap.close()
            mw.close()

    def test_resolve_proxy_muxes_selected_audio_stream(self):
        self.assertIsNotNone(self.ffmpeg)
        self.assertIsNotNone(self.ffprobe)

        silent_mp4 = os.path.join(self.tmp_dir, "resolve_silent_proxy.mp4")
        wav_2s = os.path.join(self.tmp_dir, "selected_tracks.wav")

        subprocess.run(
            [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=24:d=2.0",
                "-c:v", "libx264", "-preset", "ultrafast", "-an",
                silent_mp4,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", "sine=frequency=523.25:sample_rate=48000:duration=2.0",
                wav_2s,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        engine = AudioEngine.__new__(AudioEngine)
        engine.os_doc = osdoc.OSDoctor()
        engine.ffmpeg_cmd = self.ffmpeg
        engine.current_analysis_audio_path = wav_2s
        engine.resolve_handler = MagicMock()
        engine.resolve_handler.render_timeline_video_proxy.return_value = silent_mp4

        worker = ResolveTimelineProxyWorker(engine, "Timeline 1", self.tmp_dir, "BW_proxy_test")
        emitted = []
        worker.proxy_ready.connect(emitted.append)
        worker.run()

        self.assertEqual(emitted, [silent_mp4])

        probe = subprocess.check_output(
            [self.ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", silent_mp4],
            text=True,
        )
        info = json.loads(probe)
        codec_types = [s.get("codec_type") for s in info.get("streams", [])]
        self.assertIn("video", codec_types)
        self.assertIn("audio", codec_types)
        dur = float(info["format"]["duration"])
        self.assertAlmostEqual(dur, 2.0, delta=0.25)


class TestUpdaterHardening(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="bw_updater_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_whitelist_preserves_launchers_temp_and_user_files(self):
        parent_sibling = os.path.join(self.tmp_dir, "important_user_file.txt")
        with open(parent_sibling, "w", encoding="utf-8") as f:
            f.write("keep me")

        inst = os.path.join(self.tmp_dir, "BW_custom_install")
        for sub in ("gui", "api", "models", "saves", "temp", "venv", "my_videos"):
            os.makedirs(os.path.join(inst, sub), exist_ok=True)

        # Obsolete BadWords code files (should be cleaned)
        for rel, content in [
            ("main.py", "# main"),
            ("osdoc.py", "# osdoc"),
            (".version", "4.0.1\n"),
            (os.path.join("gui", "stale_file.py"), "# stale"),
            (os.path.join("api", "old_module.py"), "# old"),
        ]:
            with open(os.path.join(inst, rel), "w", encoding="utf-8") as f:
                f.write(content)

        # Protected binaries, user configs, heavy folders, and unrelated personal files
        preserved = [
            "BadWords",
            "BadWords.exe",
            "badwords-installer",
            "settings.json",
            "user.json",
            os.path.join("models", "dummy"),
            os.path.join("saves", "dummy"),
            os.path.join("temp", "active.wav"),
            os.path.join("venv", "python"),
            os.path.join("my_videos", "clip.mp4"),
            "notes.txt",
        ]
        for rel in preserved:
            with open(os.path.join(inst, rel), "w", encoding="utf-8") as f:
                f.write("data")

        res = updater.clean_badwords_code_whitelist(inst, cur_script=os.path.join(inst, "updater.py"), allow_git_for_test=True)
        self.assertTrue(res["cleaned"])

        self.assertFalse(os.path.exists(os.path.join(inst, "gui")))
        self.assertFalse(os.path.exists(os.path.join(inst, "api")))
        self.assertFalse(os.path.exists(os.path.join(inst, "main.py")))
        self.assertFalse(os.path.exists(os.path.join(inst, "osdoc.py")))
        self.assertFalse(os.path.exists(os.path.join(inst, ".version")))

        for rel in preserved:
            self.assertTrue(os.path.isfile(os.path.join(inst, rel)), f"Must preserve {rel}")
        self.assertTrue(os.path.isfile(parent_sibling), "Parent directory sibling must never be touched")

    def test_updater_aborts_on_git_repo(self):
        git_dir = os.path.join(self.tmp_dir, "repo")
        os.makedirs(os.path.join(git_dir, ".git"), exist_ok=True)
        with open(os.path.join(git_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("# repo main")
        with open(os.path.join(git_dir, "osdoc.py"), "w", encoding="utf-8") as f:
            f.write("# repo osdoc")

        res = updater.clean_badwords_code_whitelist(git_dir, allow_git_for_test=False)
        self.assertFalse(res["cleaned"])
        self.assertEqual(res["reason"], "git_repo")
        self.assertTrue(os.path.isfile(os.path.join(git_dir, "main.py")))

        # CLI invocation against .git repo must also exit non-zero cleanly without modifying anything
        proc = subprocess.run(
            [sys.executable, os.path.join(SETUPFILES_DIR, "updater.py"), "--install-dir", git_dir],
            capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(git_dir, "main.py")))

    def test_candidate_tag_urls_handle_both_tag_formats(self):
        urls_bare = updater.build_candidate_tag_urls("4.1.0")
        urls_v = updater.build_candidate_tag_urls("v4.1.0")
        self.assertIn("https://github.com/veritus-git/BadWords/archive/refs/tags/4.1.0.zip", urls_bare)
        self.assertIn("https://github.com/veritus-git/BadWords/archive/refs/tags/v4.1.0.zip", urls_bare)
        self.assertIn("https://github.com/veritus-git/BadWords/archive/refs/tags/4.1.0.zip", urls_v)
        self.assertIn("https://github.com/veritus-git/BadWords/archive/refs/tags/v4.1.0.zip", urls_v)

    def test_updater_windows_exe_urls_and_linux_wrapper_fallback(self):
        exe_urls = updater.build_badwords_exe_candidate_urls("4.1.0")
        self.assertEqual(
            exe_urls,
            [
                "https://github.com/veritus-git/BadWords/releases/download/4.1.0/BadWords.exe",
                "https://github.com/veritus-git/BadWords/releases/download/v4.1.0/BadWords.exe",
                "https://github.com/veritus-git/BadWords/releases/latest/download/BadWords.exe",
            ],
        )

        if os.name == "posix":
            inst = os.path.join(self.tmp_dir, "inst")
            local_bin = os.path.join(self.tmp_dir, "local_bin")
            os.makedirs(os.path.join(inst, "venv", "bin"), exist_ok=True)
            os.makedirs(local_bin, exist_ok=True)
            with open(os.path.join(inst, "venv", "bin", "python3"), "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
            with open(os.path.join(inst, "main.py"), "w", encoding="utf-8") as f:
                f.write("print('ok')\n")

            bin_entry = os.path.join(local_bin, "badwords")
            os.symlink(os.path.join(inst, "MissingBadWords"), bin_entry)

            ok = updater.ensure_linux_local_bin_entry(inst, local_bin_dir=local_bin)
            self.assertTrue(ok)
            self.assertFalse(os.path.islink(bin_entry))
            with open(bin_entry, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue(content.startswith("#!/bin/sh\nexec "))
            self.assertIn("python3", content)
            self.assertIn("main.py", content)


if __name__ == "__main__":
    unittest.main()
