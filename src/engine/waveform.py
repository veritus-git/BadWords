#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: waveform.py
ROLE: Audio Waveform & Peak Cache Engine
DESCRIPTION:
High-performance, vectorized audio waveform peak extraction and caching engine.
Generates lightweight min/max amplitude peaks from raw audio buffers or files
optimized for 60 FPS UI rendering with viewport culling.
"""

from __future__ import annotations

import os
import time
import hashlib
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from osdoc import log_info, log_error, get_subprocess_kwargs


@dataclass
class WaveformPeaks:
    """
    Compact container for precomputed waveform amplitude peaks.
    Memory footprint: ~480 KB for 10 minutes of audio at 100 points/sec.
    """
    peaks_min: np.ndarray      # Shape (N,), float32 in [-1.0, 0.0]
    peaks_max: np.ndarray      # Shape (N,), float32 in [0.0, 1.0]
    peaks_rms: np.ndarray      # Shape (N,), float32 in [0.0, 1.0]
    duration: float            # Total audio duration in seconds
    sample_rate: int = 16000   # Sampling rate of source audio
    points_per_second: int = 400  # Resolution density (points per second)

    @property
    def num_points(self) -> int:
        return len(self.peaks_min)

    def get_visible_peaks(
        self, t_start: float, t_end: float
    ) -> Tuple[np.ndarray, np.ndarray, int, int]:
        """
        Ultra-fast O(1) viewport culling. Returns slices of (min, max, start_idx, end_idx)
        corresponding to the visible time interval [t_start, t_end].
        """
        if self.num_points == 0 or t_end <= t_start or self.duration <= 0:
            empty = np.empty(0, dtype=np.float32)
            return empty, empty, 0, 0

        t_start = max(0.0, t_start)
        t_end = min(self.duration, max(t_start, t_end))

        idx_start = max(0, min(self.num_points, int(t_start * self.points_per_second)))
        idx_end = max(idx_start, min(self.num_points, int(np.ceil(t_end * self.points_per_second))))

        if idx_start >= idx_end and idx_start < self.num_points:
            idx_end = min(self.num_points, idx_start + 1)

        return (
            self.peaks_min[idx_start:idx_end],
            self.peaks_max[idx_start:idx_end],
            idx_start,
            idx_end,
        )

    def save(self, cache_path: str) -> None:
        """Persists peaks to compressed NumPy format (.npz)."""
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            np.savez_compressed(
                cache_path,
                min=self.peaks_min.astype(np.float32),
                max=self.peaks_max.astype(np.float32),
                rms=self.peaks_rms.astype(np.float32),
                duration=np.float32(self.duration),
                sample_rate=np.int32(self.sample_rate),
                pps=np.int32(self.points_per_second),
            )
        except Exception as e:
            log_error(f"WaveformPeaks: failed to save cache '{cache_path}': {e}")

    @classmethod
    def load(cls, cache_path: str) -> Optional[WaveformPeaks]:
        """Loads precomputed peaks from a compressed .npz cache file."""
        if not os.path.isfile(cache_path):
            return None
        try:
            with np.load(cache_path) as data:
                return cls(
                    peaks_min=data["min"],
                    peaks_max=data["max"],
                    peaks_rms=data.get("rms", np.zeros_like(data["min"])),
                    duration=float(data["duration"]),
                    sample_rate=int(data.get("sample_rate", 16000)),
                    points_per_second=int(data.get("pps", 100)),
                )
        except Exception as e:
            log_error(f"WaveformPeaks: failed to load cache '{cache_path}': {e}")
            return None


class WaveformExtractor:
    """
    Core vector processing engine to generate waveform peaks from raw buffers or media files.
    """

    @staticmethod
    def generate_peaks(
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        points_per_second: int = 400,
    ) -> WaveformPeaks:
        """
        Vectorized amplitude peak extraction using NumPy.
        Executes in < 30ms for 10 minutes of audio.
        """
        if audio_data is None or len(audio_data) == 0:
            empty = np.empty(0, dtype=np.float32)
            return WaveformPeaks(empty, empty, empty, 0.0, sample_rate, points_per_second)

        # Ensure float32 in [-1.0, 1.0] and single channel mono
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=-1)

        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Guard against NaNs / Infs and clip to valid audio range
        audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=1.0, neginf=-1.0)
        np.clip(audio_data, -1.0, 1.0, out=audio_data)

        total_samples = len(audio_data)
        duration = total_samples / float(sample_rate) if sample_rate > 0 else 0.0

        chunk_size = max(1, sample_rate // points_per_second)
        n_chunks = total_samples // chunk_size

        if n_chunks == 0:
            # Very short audio snippet (< 1 chunk)
            p_min = np.array([float(np.min(audio_data))], dtype=np.float32)
            p_max = np.array([float(np.max(audio_data))], dtype=np.float32)
            p_rms = np.array([float(np.sqrt(np.mean(audio_data**2)))], dtype=np.float32)
            return WaveformPeaks(p_min, p_max, p_rms, duration, sample_rate, points_per_second)

        # Vectorized reshape for bulk chunk processing
        full_chunks_len = n_chunks * chunk_size
        trimmed = audio_data[:full_chunks_len].reshape(n_chunks, chunk_size)

        peaks_min = trimmed.min(axis=1).astype(np.float32)
        peaks_max = trimmed.max(axis=1).astype(np.float32)
        peaks_rms = np.sqrt(np.mean(trimmed**2, axis=1)).astype(np.float32)

        # Process trailing remainder samples if any
        remainder_len = total_samples - full_chunks_len
        if remainder_len > 0:
            rem = audio_data[full_chunks_len:]
            rem_min = np.float32(np.min(rem))
            rem_max = np.float32(np.max(rem))
            rem_rms = np.float32(np.sqrt(np.mean(rem**2)))
            peaks_min = np.append(peaks_min, rem_min)
            peaks_max = np.append(peaks_max, rem_max)
            peaks_rms = np.append(peaks_rms, rem_rms)

        return WaveformPeaks(
            peaks_min=peaks_min,
            peaks_max=peaks_max,
            peaks_rms=peaks_rms,
            duration=duration,
            sample_rate=sample_rate,
            points_per_second=points_per_second,
        )

    @classmethod
    def get_cache_file_path(cls, file_path: str, points_per_second: int, cache_dir: str) -> str:
        """Computes a unique, deterministic cache file path based on file metadata."""
        try:
            st = os.stat(file_path)
            sig = f"{os.path.abspath(file_path)}_{st.st_size}_{st.st_mtime_ns}_{points_per_second}"
        except Exception:
            sig = f"{os.path.abspath(file_path)}_{points_per_second}"

        file_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_"))[:32]
        return os.path.join(cache_dir, f"wf_{safe_name}_{file_hash}.npz")

    @classmethod
    def extract_from_file(
        cls,
        file_path: str,
        points_per_second: int = 400,
        cache_dir: Optional[str] = None,
        ffmpeg_cmd: str = "ffmpeg",
    ) -> Optional[WaveformPeaks]:
        """
        Extracts waveform peaks from an audio/video file.
        Uses cache if available; otherwise falls back to scipy/wave or FFmpeg pipe decoding.
        """
        if not file_path or not os.path.isfile(file_path):
            log_error(f"WaveformExtractor: file not found '{file_path}'")
            return None

        # 1. Check cache
        cache_file = None
        if cache_dir:
            cache_file = cls.get_cache_file_path(file_path, points_per_second, cache_dir)
            if os.path.isfile(cache_file):
                cached = WaveformPeaks.load(cache_file)
                if cached is not None and cached.num_points > 0:
                    return cached

        # 2. Extract raw audio data
        audio_data = None
        sr = 16000

        # Fast path: standard 16-bit PCM WAV reading via python built-in wave module
        if file_path.lower().endswith(".wav"):
            try:
                import wave
                with wave.open(file_path, "rb") as wf:
                    if wf.getsampwidth() == 2 and wf.getcomptype() == "NONE":
                        sr = wf.getframerate()
                        n_ch = wf.getnchannels()
                        raw_bytes = wf.readframes(wf.getnframes())
                        raw_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        if n_ch > 1:
                            raw_data = raw_data.reshape(-1, n_ch).mean(axis=-1)
                        audio_data = raw_data
            except Exception:
                pass

        # Fallback path: universal FFmpeg pipe extraction (converts to 16kHz s16le mono)
        if audio_data is None:
            cmd = [
                ffmpeg_cmd,
                "-v", "error",
                "-y",
                "-i", file_path,
                "-vn",
                "-f", "s16le",
                "-ac", "1",
                "-ar", "16000",
                "pipe:1",
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=60,
                    **get_subprocess_kwargs()
                )
                if res.stdout:
                    audio_data = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0
                    sr = 16000
            except Exception as e:
                log_error(f"WaveformExtractor: FFmpeg pipe decode failed for '{file_path}': {e}")
                return None

        if audio_data is None or len(audio_data) == 0:
            log_error(f"WaveformExtractor: decoded zero audio samples from '{file_path}'")
            return None

        # 3. Generate peaks
        peaks = cls.generate_peaks(audio_data, sample_rate=sr, points_per_second=points_per_second)

        # 4. Save to cache
        if cache_file:
            peaks.save(cache_file)

        return peaks
