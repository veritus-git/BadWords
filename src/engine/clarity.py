#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: clarity.py
ROLE: Engine
DESCRIPTION:
A 0-100 clarity score for any stretch of the recording: how sure Whisper was of the words
(its per-word probability) and how strongly the speech came through compared with the rest of
the recording (an off-mic or mumbled passage scores lower). Used to steer the AI towards
clear sentences and shown on the story board.
"""

import bisect

import numpy as np

SR = 16000


def _speech_level(seg):
    """Loudness of the speech itself (dB): 90th percentile of 50 ms frame energies."""
    if seg is None or len(seg) < 800:
        return None
    fr = seg[:len(seg) // 800 * 800].reshape(-1, 800)
    e = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(np.quantile(e, 0.9))


def make_scorer(words_data, audio=None):
    """Returns score(t0, t1) -> int 0-100, or None when there is nothing to judge.
    words_data: transcript words (with 'prob' when the transcription kept it).
    audio: mono float32 at 16 kHz, or None (then only word confidence counts)."""
    spoken = [w for w in words_data or []
              if w.get('type') not in ('silence', 'inaudible') and not w.get('is_inaudible')]
    starts = [float(w.get('start', 0.0)) for w in spoken]
    ref = None
    if audio is not None and len(audio) > SR:
        # The recording's typical speech level: median over 3-second windows
        win = 3 * SR
        levels = [_speech_level(audio[i:i + win]) for i in range(0, len(audio) - win // 2, win)]
        levels = [lv for lv in levels if lv is not None and lv > -60]
        ref = float(np.median(levels)) if levels else None

    def score(t0, t1):
        i0, i1 = bisect.bisect_left(starts, t0 - 1e-3), bisect.bisect_right(starts, t1 + 1e-3)
        probs = [float(w['prob']) for w in spoken[i0:i1] if w.get('prob') is not None]
        p_factor = None
        if probs:
            p = float(np.mean(probs)) * 0.6 + float(np.min(probs)) * 0.4  # one garbled word costs something
            p_factor = min(1.0, max(0.0, (p - 0.35) / 0.55))
        loud = None
        if ref is not None:
            lv = _speech_level(audio[int(max(0.0, t0) * SR):int(t1 * SR)])
            if lv is not None:
                loud = min(1.0, max(0.0, (lv - ref + 18.0) / 15.0))  # 0 at 18 dB below typical, 1 at 3 dB below
        if p_factor is None and loud is None:
            return None
        if p_factor is None:
            return int(round(100 * loud))
        if loud is None:
            return int(round(100 * p_factor))
        return int(round(100 * (0.7 * p_factor + 0.3 * loud)))

    return score
