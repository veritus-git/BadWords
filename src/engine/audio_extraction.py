#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: engine.py
ROLE: Logic Layer / Processing Engine
DESCRIPTION:
Coordinates heavy processes: running Whisper, FFmpeg operations (via subprocess),
detecting silence, and building data structures.
Acts as an orchestrator, delegating tasks to API and Algorithms.
Now also acts as a Data Controller for Project State and Model Management.
Refactored to use Faster-Whisper via Runner Script Isolation (VENV Aware).
FIXED v9.3: 
- Implemented smart Compute Type detection (NVIDIA Compute Capability check).
- Tuned Whisper parameters for VERBATIM transcription.
FIXED v9.5:
- Removed 'window_size_samples' from VadOptions.
- TUNED v9.6: Optimized VAD & Decoding parameters.
UPDATED v10.3:
- OPERATION "LOBOTOMY": Switched to GREEDY DECODING (beam_size=1).
- Disables linguistic smoothing to force raw acoustic capture.
- Removes temperature fallback strategies to prevent grammar correction.
- Raw Retake Logic retained.
UPDATED v11.0:
- INTEGRATED STABLE-TS: Now uses stable-ts wrapper for robust timestamp alignment.
FIXED v11.2:
- Added dynamic PATH injection for portable FFmpeg in runner script to fix FileNotFoundError.
NEW v12.0:
- SMART CHUNKING: Re-chunks stable-ts output into blocks respecting punctuation with lookahead (up to 33 words).
- ANTI-HALLUCINATION: Automatically squashes 10+ identical repetitive words into one red clip.
- RAW TEXT ENGINE: Pass 3 logic bleed removed (No more auto loop-detection on initial load).
"""

import os
import sys
import json
import time
import threading
import shutil
import subprocess
import urllib.request
import re
import traceback
import platform
import random
import difflib  # Essential for on-the-fly fuzzy matching

import config
import algorithms
from osdoc import log_info, log_error

class AudioExtractionMixin:
    def normalize_audio(self, input_path):
        """
        STAGE 9 FIX: Gentle processing only — preserves micro-pauses between stutters.
        Removed loudnorm (was raising noise floor and masking silence gaps).
        Using a very light compressor just to catch hard peaks, nothing more.
        """
        # FIX KR-04: use splitext instead of replace() — safe for .WAV and other extensions
        base, ext = os.path.splitext(input_path)
        norm_path = base + "_norm" + ext
        filter_chain = (
            "highpass=f=80, "
            "acompressor=threshold=-15dB:ratio=2:attack=10:release=50"
        )
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_path, "-af", filter_chain,
               "-ar", "48000", "-ac", "1", norm_path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, **self.os_doc.get_subprocess_kwargs())
            return norm_path
        except Exception as e:
            log_error(f"normalize_audio: FFmpeg failed, returning original: {e}")
            return input_path
    


    def _extract_audio_direct(self, source_info, output_wav_path, callback_status=None):
        """
        Extracts and concatenates audio directly from source file(s) using FFmpeg,
        bypassing DaVinci Resolve render. The source file is NEVER modified —
        we write to output_wav_path (a temp file).

        NOTE: Resolve clip effects (EQ, gain, normalisation) are intentionally
        NOT applied here. Raw source audio is better for Whisper transcription
        accuracy, as Resolve processing may introduce compression artefacts that
        confuse VAD and silence detection.

        Supports:
          single_uncut            → simple -ss / -t trim
          single_source_multicopy → filter_complex atrim+concat per clip

        Returns True on success, False on failure.
        """
        mode        = source_info.get("mode")
        source_file = source_info.get("source_file")
        clips       = source_info.get("clips", [])  # [{src_in_s, duration_s}, ...]

        if not source_file or not clips:
            log_error("_extract_audio_direct: missing source_file or clips.")
            return False

        if callback_status:
            callback_status(self.txt("status_direct_source"))

        try:
            if mode == "single_uncut":
                # ── Single uncut clip: direct trim ────────────────────────────
                c   = clips[0]
                in_s  = c["src_in_s"]
                dur_s = c["duration_s"]
                log_info(f"[DirectAudio] single_uncut: in={in_s:.3f}s dur={dur_s:.3f}s")

                cmd = [
                    self.ffmpeg_cmd, "-y",
                    "-i",  source_file,
                    "-ss", f"{in_s:.6f}",
                    "-t",  f"{dur_s:.6f}",
                    "-vn",
                    "-map", "0:a?",
                    "-ar", "48000",
                    "-ac", "1",
                    output_wav_path,
                ]

            else:
                # ── Multi-clip concat via filter_complex atrim ────────────────
                log_info(f"[DirectAudio] single_source_multicopy: {len(clips)} clips")

                # Build filter_complex:
                # [0:a]atrim=start=IN:end=END,asetpts=PTS-STARTPTS[s0];
                # [0:a]atrim=start=IN:end=END,asetpts=PTS-STARTPTS[s1];
                # [s0][s1]concat=n=N:v=0:a=1[out]
                filter_parts = []
                concat_inputs = ""
                for idx, c in enumerate(clips):
                    in_s  = c["src_in_s"]
                    end_s = in_s + c["duration_s"]
                    filter_parts.append(
                        f"[0:a]atrim=start={in_s:.6f}:end={end_s:.6f},"
                        f"asetpts=PTS-STARTPTS[s{idx}]"
                    )
                    concat_inputs += f"[s{idx}]"

                n = len(clips)
                filter_parts.append(f"{concat_inputs}concat=n={n}:v=0:a=1[out]")
                filter_complex = ";".join(filter_parts)

                cmd = [
                    self.ffmpeg_cmd, "-y",
                    "-i",  source_file,
                    "-filter_complex", filter_complex,
                    "-map", "[out]",
                    "-ar", "48000",
                    "-ac", "1",
                    output_wav_path,
                ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                **self.os_doc.get_subprocess_kwargs()
            )

            if result.returncode != 0:
                log_error(f"[DirectAudio] FFmpeg failed (rc={result.returncode}): {result.stderr[-400:]}")
                return False

            if not os.path.exists(output_wav_path) or os.path.getsize(output_wav_path) == 0:
                log_error("[DirectAudio] Output WAV is missing or empty.")
                return False

            log_info(f"[DirectAudio] Success → {output_wav_path}")
            return True

        except Exception as e:
            log_error(f"[DirectAudio] Exception: {e}")
            return False

    def detect_silence(self, audio_path, threshold_db, min_dur):
        cmd = [self.ffmpeg_cmd, "-i", audio_path, "-af", 
               f"silencedetect=noise={threshold_db}dB:d={min_dur}", "-f", "null", "-"]
        try:
            res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, 
                                 encoding='utf-8', errors='replace',
                                 **self.os_doc.get_subprocess_kwargs())
            output = res.stderr
            starts = [float(x) for x in re.findall(r'silence_start: (\d+\.?\d*)', output)]
            ends = [float(x) for x in re.findall(r'silence_end: (\d+\.?\d*)', output)]
            ranges = []
            count = min(len(starts), len(ends))
            for i in range(count): ranges.append({'s': starts[i], 'e': ends[i]})
            if len(starts) > len(ends): ranges.append({'s': starts[-1], 'e': 999999.0})
            return ranges
        except Exception as e:
            log_error(f"Silence Detection Error: {e}")
            return []

    def _get_audio_duration(self, wav_path):
        """Return audio duration in seconds via ffprobe."""
        try:
            # FIX KR-05: don't use replace("ffmpeg","ffprobe") — path may contain "ffmpeg" multiple times
            _ffmpeg_dir = os.path.dirname(self.ffmpeg_cmd)
            _ffprobe_name = "ffprobe" + (".exe" if self.os_doc.is_win else "")
            ffprobe = os.path.join(_ffmpeg_dir, _ffprobe_name) if _ffmpeg_dir else _ffprobe_name
            cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", wav_path]
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 **self.os_doc.get_subprocess_kwargs())
            return float(res.stdout.strip())
        except Exception:
            return 9999.0

    def _compute_sound_islands(self, silence_ranges, total_duration,
                               min_island_dur=0.3, pad_fixed=0.25, pad_threshold=0.5):
        """
        Convert silence_ranges into smart-padded sound islands for chunked transcription.

        Steps:
          1. Invert silences  →  raw islands [(start, end), ...]
          2. Merge islands shorter than min_island_dur with their nearest neighbour
          3. Smart Padding: eat into surrounding silence
               gap >= pad_threshold  →  each side += pad_fixed
               gap <  pad_threshold  →  each side += gap / 2  (never overlap!)
          4. Clip to [0, total_duration] and return list of (start, end) tuples.

        All timings are in the same time-domain as silence_ranges (slow-WAV time).
        """
        if not silence_ranges:
            return [(0.0, total_duration)]

        # Step 1: invert silences → raw islands
        raw = []
        prev_end = 0.0
        for s in sorted(silence_ranges, key=lambda x: x['s']):
            if s['s'] > prev_end:
                raw.append([prev_end, s['s']])
            prev_end = max(prev_end, s['e'])
        if prev_end < total_duration:
            raw.append([prev_end, total_duration])

        if not raw:
            return [(0.0, total_duration)]

        # Step 2: merge short islands
        changed = True
        while changed:
            changed = False
            out = []
            i = 0
            while i < len(raw):
                dur = raw[i][1] - raw[i][0]
                if dur < min_island_dur and len(raw) > 1:
                    if i + 1 < len(raw):
                        raw[i + 1][0] = raw[i][0]
                    elif out:
                        out[-1][1] = raw[i][1]
                        i += 1
                        changed = True
                        continue
                    i += 1
                    changed = True
                    continue
                out.append(raw[i])
                i += 1
            raw = out

        # Step 3: smart padding — compute amounts from ORIGINAL positions
        n = len(raw)
        start_pad = [0.0] * n
        end_pad   = [0.0] * n
        for i in range(n):
            gap_before = raw[i][0] if i == 0 else raw[i][0] - raw[i - 1][1]
            gap_after  = (total_duration - raw[i][1]) if i == n - 1 else raw[i + 1][0] - raw[i][1]
            start_pad[i] = pad_fixed if gap_before >= pad_threshold else gap_before / 2.0
            end_pad[i]   = pad_fixed if gap_after  >= pad_threshold else gap_after  / 2.0

        # Step 4: apply padding and clip
        result = []
        for i in range(n):
            s = max(0.0, raw[i][0] - start_pad[i])
            e = min(total_duration, raw[i][1] + end_pad[i])
            if e > s:
                result.append((s, e))

        return result if result else [(0.0, total_duration)]

    def prepare_preview_audio(self, settings=None, callback_status=None):
        """
        Extracts audio for preview directly from source clip files via FFmpeg first,
        or via Resolve render, ONLY IF the target timeline and source clips match the expected settings.
        Returns the output wav path on success, or None on failure.
        """
        if settings is None:
            settings = {}
        unique_id = f"BW_PREVIEW_{int(time.time())}"
        temp_dir = self.os_doc.get_temp_folder()
        os.makedirs(temp_dir, exist_ok=True)

        tl_name = settings.get('timeline_name') or ""
        track_indices = settings.get('track_indices') or None
        expected_source_files = settings.get('source_files') or []

        if not self.resolve_handler or not getattr(self.resolve_handler, 'project', None):
            log_error("[PreviewAudio] DaVinci Resolve is not connected.")
            return None

        # ── 1. VALIDATE TIMELINE EXISTENCE & MATCHING ────────────────────────
        matching_tl = None
        if tl_name and self.resolve_handler.project and hasattr(self.resolve_handler.project, "GetTimelineCount"):
            try:
                count = int(self.resolve_handler.project.GetTimelineCount())
                for i in range(1, count + 1):
                    t = self.resolve_handler.project.GetTimelineByIndex(i)
                    if t and t.GetName() == tl_name:
                        matching_tl = t
                        break
            except Exception as e:
                log_info(f"[PreviewAudio] Timeline lookup error: {e}")

        if not matching_tl:
            curr_tl = getattr(self.resolve_handler, 'timeline', None)
            if curr_tl and (not tl_name or curr_tl.GetName() == tl_name):
                matching_tl = curr_tl

        if not matching_tl:
            log_error(f"[PreviewAudio] Target timeline '{tl_name}' not found in DaVinci Resolve.")
            return None

        inspect_tl_name = matching_tl.GetName()

        # ── 2. VALIDATE SOURCE CLIPS MATCHING ──────────────────────────────
        direct_info = None
        try:
            direct_info = self.resolve_handler.get_direct_audio_info(
                inspect_tl_name, track_indices
            )
        except Exception as e:
            log_info(f"[PreviewAudio] get_direct_audio_info error: {e}")

        if expected_source_files:
            expected_basenames = {os.path.basename(f).lower() for f in expected_source_files if f}
            
            actual_basenames = set()
            if direct_info and direct_info.get('clips'):
                actual_basenames = {os.path.basename(c['file_path']).lower() for c in direct_info['clips'] if c.get('file_path')}
            else:
                try:
                    for i in range(1, matching_tl.GetTrackCount("audio") + 1):
                        items = matching_tl.GetItemListInTrack("audio", i) or []
                        for item in items:
                            pi = item.GetMediaPoolItem()
                            if pi:
                                fp = pi.GetClipProperty("File Path") or ""
                                if fp:
                                    actual_basenames.add(os.path.basename(fp).lower())
                except Exception:
                    pass

            if expected_basenames and actual_basenames:
                intersection = expected_basenames.intersection(actual_basenames)
                if not intersection:
                    log_error(
                        f"[PreviewAudio] Source clip mismatch on timeline '{inspect_tl_name}'. "
                        f"Expected: {expected_basenames}, Found: {actual_basenames}. Aborting preview audio recovery."
                    )
                    return None

        # ── 3. EXTRACT AUDIO (DIRECT OR RENDER) ─────────────────────────────
        if direct_info:
            _direct_wav = os.path.join(temp_dir, f"{unique_id}_direct.wav")
            ok_direct = self._extract_audio_direct(direct_info, _direct_wav, callback_status=callback_status)
            if ok_direct and os.path.exists(_direct_wav) and os.path.getsize(_direct_wav) > 0:
                log_info(f"[PreviewAudio] Direct source clip audio extraction successful → {_direct_wav}")
                return _direct_wav

        # Fallback to Resolve render
        end_frame_override = None
        if track_indices and self.resolve_handler:
            try:
                end_seconds = self.resolve_handler.get_selected_tracks_end_seconds(
                    inspect_tl_name, track_indices
                )
                if end_seconds:
                    fps = self.resolve_handler.fps or 60.0
                    end_frame_override = int(round(end_seconds * fps))
            except Exception as e:
                log_info(f"prepare_preview_audio: track end calculation error: {e}")

        try:
            wav_path = self.resolve_handler.render_audio(
                unique_id, temp_dir,
                timeline_name=inspect_tl_name,
                track_indices=track_indices,
                end_frame_override=end_frame_override,
            )
            if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                log_info(f"[PreviewAudio] Resolve audio render successful → {wav_path}")
                return wav_path
        except Exception as e:
            log_error(f"prepare_preview_audio render failed: {e}")

        return None

    def _convert_wav_to_flac(self, wav_path, flac_path):
        """Convert WAV to FLAC Vorbis using FFmpeg. Returns True on success."""
        try:
            cmd = [
                self.ffmpeg_cmd, "-y",
                "-i", wav_path,
                "-codec:a", "flac",
                "-compression_level", "5",
                flac_path
            ]
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=120,
                **self.os_doc.get_subprocess_kwargs()
            )
            if result.returncode == 0 and os.path.exists(flac_path):
                wav_size = os.path.getsize(wav_path)
                flac_size = os.path.getsize(flac_path)
                log_info(f"_convert_wav_to_flac: {wav_size} → {flac_size} bytes "
                         f"({flac_size/wav_size*100:.1f}%)")
                return True
            else:
                log_error(f"_convert_wav_to_flac failed: {result.stderr[:500]}")
                return False
        except Exception as e:
            log_error(f"_convert_wav_to_flac error: {e}")
            return False

