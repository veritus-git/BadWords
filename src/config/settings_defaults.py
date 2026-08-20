#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: settings_defaults.py
ROLE: Configuration
DESCRIPTION:
Default values for user settings.
"""

import platform

from config.app_constants import VERSION, get_system_font_name

# ==========================================
# USER DATA DEFAULTS (user.json)
# Stores user identity and consent state only.
# ==========================================
DEFAULT_USER_DATA = {
    "uuid": None,               # Hashed machine UUID for telemetry (anonymous)
    "telemetry_opt_in": None,   # None = not yet asked, True/False = user decision
    "telemetry_geo": True,      # Whether to include country/city in telemetry ping
    "last_pinged_version": "",  # Version string of the last successful telemetry ping
}

# ==========================================
# APPLICATION SETTINGS DEFAULTS (settings.json)
# Stores persistent UI and engine preferences.
# DO NOT include track/timeline/model selections here — those belong to main UI state.
# ==========================================
DEFAULT_SETTINGS = {
    "settings_version":     VERSION,
    # ── Transcript / Editor ──────────────────────────────────────────────────
    "editor_font_family":   get_system_font_name(),
    "editor_font_size":     12,
    "editor_line_height":   7,
    "transcript_font_size":   12,       # legacy alias kept for compatibility
    "transcript_line_height": 12,       # legacy alias kept for compatibility
    "view_mode":            "segmented",
    "transcript_layout":    "segmented",
    "settings_view_mode":   "basic",
    # ── Chunking ────────────────────────────────────────────────────────────
    "chunk_punct_count":    1,
    "chunk_max_words":      15,
    "chunk_lookahead":      3,
    "chunk_min_chars":      7,
    "chunk_min_words":      7,
    "inaud_min_dur":        0.02,
    # ── Audio sync ──────────────────────────────────────────────────────────
    "offset":               0.133,
    "pad":                  0.0,
    "snap_max":             0.25,
    # ── Silence detection ───────────────────────────────────────────────────
    "silence_min_dur":      0.2,    # Minimum silence duration (seconds) for FFmpeg silencedetect
    "silence_threshold_db": -42.0,  # Silence threshold in dB (both standalone and post-transcript)
    "ui_spin_thresh":       -42.0,
    "ui_spin_pad":          0.1,
    "fs_cut_mode":          True,
    "fs_mark_mode":         False,
    "sync_davinci_chapter": True,
    # ── AI / Whisper ────────────────────────────────────────────────────────
    "compute_type":         "int8",
    "ai_compute_type":      "Auto",
    "device":               "auto",
    "ai_initial_prompt":    "",
    "ai_vad_filter":        False,
    "ai_beam_size":             1,
    "ai_temperature":           0.0,
    "ai_condition_on_prev":     False,
    "ai_logprob_threshold":     -0.8,
    "ai_no_speech_threshold":   0.7,
    "ai_patience":              1.0,
    "ai_compression_ratio_threshold": 2.4,
    "ai_no_repeat_ngram_size":  0,
    "ai_length_penalty":        1.0,
    "ai_repetition_penalty":    1.0,
    # ── App / UI ────────────────────────────────────────────────────────────
    "gui_lang":             "en",
    "always_on_top":        False,
    "hidden_panels":        [],
    "accent_color":         "green",
    "app_icon":             "default",
    # ── Algorithm tuning ────────────────────────────────────────────────────
    "algo_fuzzy_threshold":   75,
    "algo_retake_lookahead":  80,
    "algo_distance_penalty":  2.0,
    "algo_anchor_depth":      3,
    # ── Keyboard shortcuts ───────────────────────────────────────────────────
    "shortcuts": {
        "mark_red":        "1",
        "mark_blue":       "2",
        "mark_green":      "3",
        "mark_eraser":     "4",
        "jump_to_word":    "opt_ctrl_lmb",
        "play_stop":       "Space",
        "skip_backward":   "Left",
        "skip_forward":    "Right",
        "search":          "Ctrl+F",
        "open_settings":   "Escape",
    },
    # ── Custom markers ───────────────────────────────────────────────────────
    "custom_markers":       [],
    # ── Assembly / XML Pipeline ──────────────────────────────────────────────
    # False (default): audio tracks are re-mapped sequentially (A1, A2, A3...)
    # True: original source track indices are preserved in the output timeline
    "xml_preserve_track_order": False,
    # ── Transcript timestamps ───────────────────────────────────────────────
    # False (default): timestamps rounded to nearest second, e.g. [01:08]
    # True: full millisecond precision, e.g. [01:07.986]
    "timestamp_precise": False,
    # ── Auto Updates ─────────────────────────────────────────────────────────
    # True (default): check for new releases on GitHub/GitLab at every startup.
    "auto_check_updates": True,
    # True: silently download and apply updates BEFORE loading BadWords (blocking).
    "auto_update_on_start": False,
    # ── Model Run History ─────────────────────────────────────────────────────
    # Dict mapping model name → True if it was ever successfully run this install.
    # Used to show "first run" hints when loading a model for the first time.
    "models_run_history": {},
}


# Keys in DEFAULT_SETTINGS whose change requires an application restart.
RESTART_REQUIRED_KEYS = ["compute_type", "device", "gui_lang", "ai_compute_type", "app_icon"]

