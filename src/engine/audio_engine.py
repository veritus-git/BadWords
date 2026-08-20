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

from .preferences import PreferencesMixin
from .audio_extraction import AudioExtractionMixin
from .transcription import TranscriptionMixin

class AudioEngine(PreferencesMixin, AudioExtractionMixin, TranscriptionMixin):
    def __init__(self, os_doctor, resolve_handler):
        self.os_doc = os_doctor
        self.resolve_handler = resolve_handler
        self.ffmpeg_cmd = self.os_doc.get_ffmpeg_cmd() or "ffmpeg"
        
        # Determine path to local libs for subprocess injection
        self.libs_dir = os.path.join(os.path.dirname(__file__), "libs")
        
        # Define local models directory (in install folder)
        self.models_dir = os.path.join(self.os_doc.install_dir, "models")
        try:
            os.makedirs(self.models_dir, exist_ok=True)
        except Exception as e:
            log_error(f"Failed to create models dir: {e}")
            
        # FORCE OVERRIDE FIX FOR TIMESTAMPS
        # Migrate all legacy users to the new exact synchronization settings
        prefs = self.load_preferences() or {}
        if prefs.get('offset') != 0.133 or prefs.get('pad') != 0.0 or prefs.get('snap_max') != 0.25:
            self.save_preferences({'offset': 0.133, 'pad': 0.0, 'snap_max': 0.25})
            log_info("Forced offset/pad/snap override applied successfully.")

    # ==========================================

    # ==========================================
    # TELEMETRY (POSTHOG)
    # ==========================================

    # ==========================================
    # 0. SMART COMPUTE DETECTION
    # ==========================================

    # ==========================================
    # 1. EXTERNAL PROCESS MANAGEMENT (FASTER-WHISPER)
    # ==========================================

    # ==========================================
    # 2. AUDIO PROCESSING (FFMPEG)
    # ==========================================

    # ==========================================
    # 2.5 HELPER: ENFORCE HALLUCINATION STATUS
    # ==========================================
    
    def _enforce_hallucination_status(self, words_data):
        """
        Forces hallucination objects to remain 'bad' and 'selected'.
        Necessary because algorithms.analyze_repeats clears all initial statuses 
        to perform its own clean logic pass.
        """
        for w in words_data:
            if w.get('_is_hallucination'):
                w['status'] = 'bad'
                w['selected'] = True
                w['is_auto'] = True
                w['algo_status'] = 'bad'
                w['manual_status'] = 'bad'
        return words_data

    # ==========================================
    # 3. MAIN ANALYSIS PIPELINE
    # ==========================================

    def run_fast_silence_pipeline(self, settings, callback_status=None, callback_progress=None):
        """
        Fast Silence Cut: render audio, run FFmpeg silencedetect, build a minimal
        words_data list of 'silence' segments — no Whisper involved.

        PARITY FIX: Audio pipeline now mirrors run_analysis_pipeline exactly:
          1. Slow motion pass (atempo=0.90) — stretches silence windows,
             giving FFmpeg the same precision as the transcription path.
          2. normalize_audio() — identical filter chain.
          3. detect_silence(min_dur=0.2) — same threshold as transcription path,
             eliminates false positives from sub-100ms micro-pauses.

             is always in real (source) time for calculate_timeline_structure.
        """
        def update_status(msg):
            if callback_status: callback_status(msg)
        def update_progress(val):
            if callback_progress: callback_progress(val)

        wav_path      = None

        normalized_wav = None

        try:
            threshold_db = settings.get('threshold_db', -42.0)
            padding_s    = settings.get('padding_s', 0.05)

            unique_id = f"BW_FSC_{int(time.time())}"
            update_status(self.txt("status_render"))
            update_progress(10)

            temp_dir = self.os_doc.get_temp_folder()
            os.makedirs(temp_dir, exist_ok=True)

            # ── Pre-render: calculate track end frame to limit render range ───
            # If specific tracks are selected, we only need to render up to where
            # THOSE tracks end — no need to render silence from longer other tracks.
            track_indices_for_render = settings.get('track_indices') or None
            end_frame_override = None
            if track_indices_for_render:
                end_seconds = self.resolve_handler.get_selected_tracks_end_seconds(
                    settings.get('timeline_name') or self.resolve_handler.timeline.GetName(),
                    track_indices_for_render
                )
                if end_seconds:
                    fps = self.resolve_handler.fps or 60.0
                    end_frame_override = int(round(end_seconds * fps))
                    log_info(f"transcribe_audio: render end_frame_override={end_frame_override} ({end_seconds:.2f}s)")

            # ── Try Direct Audio first (skip Resolve render when possible) ───
            tl_name_for_direct = settings.get('timeline_name') or (
                self.resolve_handler.timeline.GetName() if self.resolve_handler.timeline else ""
            )
            direct_info = None
            if tl_name_for_direct:
                try:
                    direct_info = self.resolve_handler.get_direct_audio_info(
                        tl_name_for_direct, track_indices_for_render
                    )
                except Exception as _di_err:
                    log_info(f"[DirectAudio] Inspection error (harmless, using render): {_di_err}")

            wav_path = None
            if direct_info:
                # Build unique output path for the direct-extracted WAV
                _direct_wav = os.path.join(temp_dir, f"{unique_id}_direct.wav")
                ok_direct = self._extract_audio_direct(
                    direct_info, _direct_wav,
                    callback_status=update_status,
                )
                if ok_direct:
                    wav_path = _direct_wav
                    log_info(f"[DirectAudio] Using direct source audio ({direct_info['mode']})")
                else:
                    log_info("[DirectAudio] Direct extraction failed, falling back to Resolve render.")

            if not wav_path:
                update_status(self.txt("status_render"))
                update_progress(-1)  # Indeterminate infinite progress bar

                wav_path = self.resolve_handler.render_audio(
                    unique_id, temp_dir,
                    timeline_name=settings.get('timeline_name'),
                    track_indices=track_indices_for_render,
                    end_frame_override=end_frame_override,
                )
            if not wav_path:
                log_error("Fast Silence: render failed.")
                return None, None

            update_progress(25)

            # STEP 1: Normalize — prepare audio for silence detection
            normalized_wav = self.normalize_audio(wav_path)
            target_wav = normalized_wav

            update_progress(55)
            update_status(self.txt("status_silence"))

            # STEP 3: Detect silence using user-configured thresholds.
            # Both min_dur and threshold_db are now read from settings, so the user
            # can tune them from the GUI without touching engine code.
            min_silence_dur = settings.get('silence_min_dur', 0.2)
            raw_silences = self.detect_silence(target_wav, threshold_db, min_silence_dur)

            update_progress(75)
            update_status(self.txt("status_process"))

            # --- Gap Bridging (matches _build_data_structure logic) ---
            # Merge adjacent silence regions separated by less than 150ms.
            # Without bridging, very short speech islands create false positives.
            bridged = []
            if raw_silences:
                curr = dict(raw_silences[0])
                for next_s in raw_silences[1:]:
                    if next_s['s'] - curr['e'] < 0.15:
                        curr['e'] = next_s['e']
                    else:
                        bridged.append(curr)
                        curr = dict(next_s)
                bridged.append(curr)

            # --- Compute audio duration from the physical WAV file ---
            duration_s = self._get_audio_duration(wav_path)

            # Apply padding to each detected silence
            padded_silences = []
            for s in bridged:
                new_start = s['s'] if s['s'] < 0.01 else s['s'] + padding_s
                new_end   = s['e'] if s['e'] >= duration_s or abs(s['e'] - duration_s) < 0.01 else s['e'] - padding_s
                if new_end > new_start:
                    padded_silences.append({'s': new_start, 'e': new_end})

            # Single fake word that spans the entire audio;
            # calculate_timeline_structure will use meta_global_silence for precise cuts.
            words_data = [{
                'text':             '[FAST_SILENCE_TRACK]',
                'start':            0.0,
                'end':              duration_s,
                'type':             'word',
                'status':           'normal',
                'selected':         False,
                'seg_start':        0.0,
                'seg_end':          duration_s,
                'is_segment_start': True,
                'id':               0,
                'meta_global_silence': padded_silences,
            }]

            update_progress(100)
            update_status(self.txt("status_finalize"))
            return words_data, []

        except Exception as e:
            log_error(f"run_fast_silence_pipeline error: {traceback.format_exc()}")
            return None, None
        finally:
            # Cleanup temp files safely
            for p in [normalized_wav, wav_path]:
                if p and p != wav_path and os.path.exists(p):
                    try: os.remove(p)
                    except Exception as e:
                        log_error(f"run_fast_silence_pipeline cleanup: cannot remove {p}: {e}")
            if wav_path and os.path.exists(wav_path) and 'words_data' in locals() and words_data:
                words_data[0]['meta_audio_path'] = wav_path
                # Do not delete wav_path so it can be used for audio preview


    def run_analysis_pipeline(self, settings, callback_status=None, callback_progress=None):
        def update_status(msg):
            if callback_status: callback_status(msg)
        def update_progress(val):
            if callback_progress: callback_progress(val)

        try:
            lang = settings.get('lang')
            # Whisper expects None for auto-detection, not the string "auto"
            if isinstance(lang, str) and lang.lower() == "auto":
                lang = None
            _raw_model = settings.get('model', 'medium')
            if "Turbo" in _raw_model:
                model = "large-v3-turbo"
            else:
                model = _raw_model.split()[0].lower()
            
            # --- AUTO DEVICE LOGIC & COMPUTE TYPE ---
            raw_device = settings.get('device', 'Auto')
            
            if raw_device == "Auto":
                # Check for physical existence of NVIDIA libs in venv
                if self.os_doc.has_nvidia_support():
                    device_mode = "GPU"
                    log_info("Auto Mode: Detected NVIDIA libs. Using GPU.")
                else:
                    device_mode = "CPU"
                    log_info("Auto Mode: No NVIDIA libs found. Using CPU.")
            else:
                device_mode = raw_device

            # Determine Compute Type based on detected device
            # Stage 6A: Prefer user-saved ai_compute_type from settings; auto-detect as fallback
            saved_prefs     = self.os_doc.get_all_prefs()
            saved_compute        = saved_prefs.get('ai_compute_type', '')
            user_custom_prompt   = saved_prefs.get('ai_initial_prompt', '').strip()
            # Per-language prompt selection: respects custom user prompt first,
            # then falls back to a language-specific verbatim prompt, then GOLDEN baseline.
            # lang is resolved above (None = auto-detect, str = specific language code)
            ai_initial_prompt = config.get_whisper_prompt_for_lang(lang, user_custom_prompt)
            
            # --- HOTWORDS INJECTION ---
            expected_script = settings.get('expected_script', '').strip()
            if expected_script:
                hotwords_list = self._extract_hotwords(expected_script)
                if hotwords_list:
                    # Whisper token limit for initial prompt is ~224 tokens. 
                    # We limit the added hotwords string to ~500 chars to be safe.
                    # We prioritize longer words as they are usually more specific.
                    hotwords_list.sort(key=len, reverse=True)
                    injected_words = []
                    current_len = 0
                    for hw in hotwords_list:
                        if current_len + len(hw) + 2 > 500: # +2 for comma and space
                            break
                        injected_words.append(hw)
                        current_len += len(hw) + 2
                    
                    if injected_words:
                        hotwords_str = ", ".join(injected_words)
                        if ai_initial_prompt:
                            # Sandwich the hotwords BEFORE the verbatim prompt.
                            # Whisper's stylistic priming is strongly influenced by the END of the prompt.
                            # By putting the stuttering prompt at the end, we preserve the verbatim transcription quality
                            # while still injecting the technical vocabulary into the context.
                            ai_initial_prompt = f"{hotwords_str}... {ai_initial_prompt}"
                        else:
                            ai_initial_prompt = f"{hotwords_str}."
                        log_info(f"[Hotwords] Injected {len(injected_words)} hotwords into initial_prompt.")

            log_info(f"[Prompt] lang={lang!r} → using {'custom' if user_custom_prompt else 'per-lang/golden'} prompt.")
            algo_settings   = {k: saved_prefs[k] for k in (
                'algo_fuzzy_threshold', 'algo_retake_lookahead',
                'algo_distance_penalty', 'algo_anchor_depth',
            ) if k in saved_prefs}
            # Store so GUI-triggered compare calls can reuse them
            self._last_algo_settings = algo_settings

            fw_compute = "int8"  # universal CPU fallback
            if "GPU" in device_mode:
                fw_device_str = "cuda"
                if saved_compute and saved_compute.lower() not in ("auto", ""):
                    # User explicitly chose float16 or float32 — respect it unconditionally
                    fw_compute = saved_compute
                    log_info(f"[Compute] User override (GPU): {fw_compute}")
                else:
                    fw_compute = self._get_optimal_compute_type(device="cuda")
                    log_info(f"[Compute] Auto-detected (GPU cc-based): {fw_compute}")
            else:
                fw_device_str = "cpu"
                if saved_compute and saved_compute.lower() not in ("auto", ""):
                    fw_compute = saved_compute
                    log_info(f"[Compute] User override (CPU): {fw_compute}")
                else:
                    ram_gb = self._get_system_ram_gb()
                    if hasattr(self, 'os_doc') and getattr(self.os_doc, 'is_mac', False):
                        if ram_gb >= 14.0:
                            fw_compute = "float32"
                            log_info(f"[Compute] Auto (CPU/Mac): {fw_compute} (Plenty of RAM detected: {ram_gb:.1f}GB)")
                        else:
                            fw_compute = "int8"
                            log_info(f"[Compute] Auto (CPU/Mac): {fw_compute} (Conserving RAM on {ram_gb:.1f}GB system)")
                    else:
                        fw_compute = "int8"
                        log_info(f"[Compute] Auto (CPU): {fw_compute}")

            # --- OOM PROTECTION ---
            try:
                ram_gb = self._get_system_ram_gb()
                if ram_gb < 12.0 and fw_compute == "float32" and "large" in model.lower():
                    log_info(f"[OOM Protection] System has only {ram_gb:.1f}GB RAM. Downgrading {model} from float32 to prevent crash.")
                    fw_compute = "int8"
            except Exception:
                pass


            filler_words = settings.get('filler_words', [])
            fps = self.resolve_handler.fps
            txt_inaudible = "inaudible"
            

            
            unique_id = f"BW_{int(time.time())}"
            update_progress(10)

            update_status(self.txt("status_render"))
            temp_dir = self.os_doc.get_temp_folder()
            os.makedirs(temp_dir, exist_ok=True)
            
            # ── Pre-render: calculate track end frame to limit render range ───
            track_indices_for_render = settings.get('track_indices') or None
            end_frame_override_tx = None
            if track_indices_for_render:
                _end_s = self.resolve_handler.get_selected_tracks_end_seconds(
                    settings.get('timeline_name') or self.resolve_handler.timeline.GetName(),
                    track_indices_for_render
                )
                if _end_s:
                    _fps = self.resolve_handler.fps or 60.0
                    end_frame_override_tx = int(round(_end_s * _fps))
                    log_info(f"transcribe_audio: render end_frame_override={end_frame_override_tx} ({_end_s:.2f}s)")

            # ── Try Direct Audio first (skip Resolve render when possible) ───
            tl_name_for_direct = settings.get('timeline_name') or (
                self.resolve_handler.timeline.GetName() if self.resolve_handler.timeline else ""
            )
            direct_info = None
            if tl_name_for_direct:
                try:
                    direct_info = self.resolve_handler.get_direct_audio_info(
                        tl_name_for_direct, track_indices_for_render
                    )
                except Exception as _di_err:
                    log_info(f"[DirectAudio] Inspection error (harmless, using render): {_di_err}")

            wav_path = None
            if direct_info:
                _direct_wav = os.path.join(temp_dir, f"{unique_id}_direct.wav")
                ok_direct = self._extract_audio_direct(
                    direct_info, _direct_wav,
                    callback_status=update_status,
                )
                if ok_direct:
                    wav_path = _direct_wav
                    log_info(f"[DirectAudio] Using direct source audio ({direct_info['mode']})")
                    update_progress(40)
                else:
                    log_info("[DirectAudio] Direct extraction failed, falling back to Resolve render.")

            if not wav_path:
                update_status(self.txt("status_render"))
                update_progress(-1)  # Indeterminate infinite progress bar

                wav_path = self.resolve_handler.render_audio(
                    unique_id, temp_dir,
                    timeline_name=settings.get('timeline_name'),
                    track_indices=track_indices_for_render,
                    end_frame_override=end_frame_override_tx,
                )
            if not wav_path:
                log_error("Render failed.")
                return None, None

            
            update_progress(50)

            # 1. NO SLOW DOWN (Removed per user request)
            current_wav_path = wav_path
            
            update_progress(75)

            # 2. NORMALIZE
            # (Silently normalizes audio under the fast motion process without flashing screen)
            normalized_wav = self.normalize_audio(current_wav_path)
            target_wav = normalized_wav

            update_progress(100)
            # FIX OP-03: Removed time.sleep(0.3) — UI logic does not belong in the Engine layer

            update_status(self.txt("status_check_model"))
            
            # Switch to Indeterminate during model check phase
            update_progress(-1)

            # Check/Download logic for Faster-Whisper
            if not self.check_model_exists(model):
                update_status(self.txt("status_downloading_model"))
                dl_ok = self.download_whisper_model_interactive(
                    model,
                    progress_callback=update_progress,
                    status_callback=update_status,
                )
                if not dl_ok:
                    log_error("Model download/verification failed. Cannot proceed.")
                    return None, None
            
            update_status(self.txt("status_whisper_init"))
            update_progress(-1)  # Indeterminate bar during init

            def whisper_live_progress(pct):
                update_progress(int(pct))
                update_status(f"{self.txt('status_transcribing')} {pct}%")

            # ── Silence detection BEFORE Whisper ─────────────────────────────
            # Results are reused both for island computation and _build_data_structure
            # (single FFmpeg call, same quality as before).
            update_status(self.txt("status_silence"))
            _silence_prefs       = self.os_doc.get_all_prefs()
            silence_threshold_db = _silence_prefs.get('silence_threshold_db', -42.0)
            silence_min_dur      = _silence_prefs.get('silence_min_dur', 0.2)
            silence_ranges       = self.detect_silence(target_wav, silence_threshold_db, silence_min_dur)

            # ── Compute sound islands for chunked transcription ───────────────
            total_dur = self._get_audio_duration(target_wav)
            islands   = self._compute_sound_islands(silence_ranges, total_dur)
            log_info(f"[Chunked] {len(islands)} sound island(s) detected (total_dur={total_dur:.2f}s).")

            # Execute Faster-Whisper via Runner with RESOLVED parameters
            # Execute Faster-Whisper via Runner with RESOLVED parameters
            # Chunking is now always enabled by default if len(islands) > 1
            
            update_status(self.txt("status_whisper_init"))
            
            # Note: Bar remains indeterminate (from status_whisper_init above) until runner emits first progress
            json_path = self.run_whisper(
                target_wav, model, lang, True, device_mode, fw_compute,
                filler_words,
                initial_prompt=ai_initial_prompt,
                progress_callback=whisper_live_progress,
                islands=islands,
            )
            
            if not json_path:
                log_error("Whisper failed.")
                return None, None

            # silence_ranges already computed above — reused here for data structure
            
            # Cleanup
            final_audio = wav_path
            
            for p in [wav_path, current_wav_path, normalized_wav]:
                if p and os.path.exists(p) and p != final_audio:
                    try: os.remove(p)
                    except Exception as e:
                        log_error(f"run_analysis_pipeline cleanup: cannot remove {p}: {e}")
            update_status(self.txt("status_process"))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Compute real timeline duration from the original wav file
            duration_s = self._get_audio_duration(wav_path)

            words_data, segments_data = self._build_data_structure(
                data, silence_ranges, filler_words, fps, 
                txt_inaudible,
                expected_script=expected_script,
                audio_duration=duration_s
            )
            
            if final_audio and os.path.exists(final_audio) and words_data:
                words_data[0]['meta_audio_path'] = final_audio
                # Do not delete final_audio so it can be used for audio preview
            
            if words_data:
                update_status(self.txt("status_finalize"))
                
                # --- AUTO COMPARE PHASE ---
                import algorithms
                if expected_script:
                    log_info("Auto-running CompareEngine post-transcription with Phase G...")
                    update_progress(-1)
                    algo_settings_copy = dict(settings.get("algo_settings", {}))
                    algo_settings_copy['run_phase_g'] = True
                    compare_result = self.run_compare_in_subprocess(
                        expected_script, words_data, algo_settings=algo_settings_copy
                    )
                    words_data = compare_result
                    
                    # Generate SBS cache immediately
                    try:
                        sbs_rows = algorithms.build_side_by_side_alignment(expected_script, words_data)
                        curr_hash = " ".join(algorithms.super_clean(w) for w in expected_script.split() if algorithms.super_clean(w))
                        self.sbs_cache = {
                            "hash": curr_hash,
                            "rows": sbs_rows
                        }
                    except Exception as e:
                        log_error(f"Failed to pre-calculate SBS cache: {e}")
                        self.sbs_cache = None

                words_data = algorithms.absorb_inaudible_into_repeats(words_data)
                
                # Mark model as successfully used via a marker file
                try:
                    _hist_key = model if model != "large" else "large-v3"
                    model_folder_name = f"models--Systran--faster-whisper-{_hist_key}"
                    model_folder_path = os.path.join(self.models_dir, model_folder_name)
                    if os.path.exists(model_folder_path):
                        marker_path = os.path.join(model_folder_path, ".badwords_initialized")
                        with open(marker_path, "w") as mf:
                            mf.write("1")
                except Exception as e:
                    log_error(f"Failed to save model init marker: {e}")
                    
                # Re-index IDs and rebuild segments_data (since Phase G or absorb_inaudible might have shrunk the list)
                for i, w in enumerate(words_data):
                    w['id'] = i
                
                segments_data = []
                current_seg = []
                for w in words_data:
                    if w.get('is_segment_start') and current_seg:
                        segments_data.append(current_seg)
                        current_seg = []
                    current_seg.append(w)
                if current_seg:
                    segments_data.append(current_seg)

            update_progress(100)
            return words_data, segments_data


        except Exception as e:
            log_error(f"Pipeline Critical Error: {traceback.format_exc()}")
            return None, None
    def _extract_hotwords(self, text):
        """
        Silnik Regex (V14) do wyciagania hotwords.
        Skupia sie na twardych anomaliach strukturalnych.
        """
        import re
        hard_hotwords = set()
        
        # 1. Alfanumeryczne (np. 1080Ti, Mk8, P0300, enp3s0, i9-13900K, mRNA-1273)
        hard_hotwords.update(re.findall(r'\b(?:[A-Za-z]+[0-9]+[A-Za-z0-9-]*|[0-9]+[A-Za-z]+[A-Za-z0-9-]*)\b', text))
        
        # 2. System paths and URLs (e.g. /etc/netplan, /usr/share/doc)
        hard_hotwords.update(re.findall(r'(?<!\w)(?:/[a-zA-Z0-9_.-]+)+', text))
        
        # 3. Pliki, domeny, adresy (np. config.yaml, Node.js, example.com)
        hard_hotwords.update(re.findall(r'\b[\w-]+\.(?:yaml|yml|txt|conf|exe|sh|json|xml|csv|log|py|js|cjs|cpp|h|com|org|net|io|pl)\b', text))
        
        # 4. CamelCase (np. AliExpress, TailwindCSS, MacBook)
        hard_hotwords.update(re.findall(r'\b[A-Za-z]*[a-z][A-Z][A-Za-z]*\b', text))
        
        # 5. Special character clusters (e.g. 50-cloud-init, ctrl+k, C++, C#)
        hard_hotwords.update(re.findall(r'(?<![\w/])[a-zA-Z0-9_]+[-+*/#]+[a-zA-Z0-9_]*(?![\w/])', text))
        
        # 6. IPv4, IPv6 oraz adresy MAC
        hard_hotwords.update(re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)) # IPv4
        hard_hotwords.update(re.findall(r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b', text)) # IPv6
        hard_hotwords.update(re.findall(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b', text)) # MAC

        final_list = []
        for w in hard_hotwords:
            w_clean = w.strip('.,!?"\'()[]{}:;')
            if not w_clean.isnumeric() and len(w_clean) > 1:
                final_list.append(w_clean)
                
        return sorted(list(set(final_list)), key=str.casefold)


    def _build_data_structure(self, json_data, silence_ranges, filler_words, fps, 
                              txt_inaudible="inaudible",
                              expected_script=None, audio_duration=None):
        prefs = self.os_doc.get_all_prefs()
        temp_words = []
        dynamic_bad = [w.lower().strip() for w in filler_words]
        
        def clean_word(txt): return re.sub(r'[^\w\s\'-]', '', txt.strip()).lower()
        def clean_for_match(txt): return re.sub(r'[^\w\s\'-]', '', txt.strip()).lower()

        # --- PASS 1: N-GRAM HALLUCINATION COMPRESSOR ---
        # Detects and compresses perfectly repeating consecutive phrases (from 1 to 15 words)
        # into a single tile e.g. "I went to the store [x30]"
        all_raw_words = []
        for seg in json_data.get('segments', []):
            for w in seg.get('words', []):
                all_raw_words.append(w)

        if all_raw_words:
            # FIX OP-01: Reducing n-gram from 15 to 5 drastically reduces complexity
            for n in range(1, 6):
                i = 0
                while i <= len(all_raw_words) - n * 2:
                    ngram = [clean_for_match(w['word']) for w in all_raw_words[i:i+n]]
                    if not any(ngram): 
                        i += 1
                        continue
                    
                    repeats = 1
                    curr_idx = i + n
                    while curr_idx <= len(all_raw_words) - n:
                        next_ngram = [clean_for_match(w['word']) for w in all_raw_words[curr_idx:curr_idx+n]]
                        if next_ngram == ngram:
                            repeats += 1
                            curr_idx += n
                        else:
                            break
                            
                    threshold = 4 if n > 1 else 5
                    if repeats >= threshold:
                        merged_word_text = " ".join(w['word'].strip() for w in all_raw_words[i : i+n])
                        
                        merged = all_raw_words[i].copy()
                        merged['word'] = f"{merged_word_text} [x{repeats}]"
                        merged['end'] = all_raw_words[curr_idx - 1]['end']
                        merged['_is_hallucination'] = True
                        
                        # Replace the entire repeating sequence with the single compressed dictionary
                        all_raw_words[i : curr_idx] = [merged]
                    
                    i += 1

        compressed_words = all_raw_words

        # --- PASS 2: SMART CHUNKING (Z LOOKAHEAD) ---
        c_max = int(prefs.get('chunk_max_words', 30))
        c_look = int(prefs.get('chunk_lookahead', 3))
        # GOLDEN fix: use chunk_min_words (word count) not chunk_min_chars (char count)
        c_min = int(prefs.get('chunk_min_words', prefs.get('chunk_min_chars', 7)))
        c_punct_target = int(prefs.get('chunk_punct_count', 1))
        c_hard_limit = c_max + c_look

        chunks = []
        curr_chunk = []
        punct_seen = 0
        for i, w in enumerate(compressed_words):
            curr_chunk.append(w)
            
            last_word_text = w['word'].strip()
            has_punct = last_word_text.endswith(('.', '?', '!'))
            if has_punct:
                punct_seen += 1
            should_break = False
            
            # Absolute maximum hard limit to prevent infinite run-ons
            if len(curr_chunk) >= c_hard_limit:
                should_break = True
            elif len(curr_chunk) >= c_max:
                # GOLDEN fix: break if the CURRENT word has punctuation (not accumulated count).
                # In src_old: `if has_punct: should_break = True` — per-word check.
                if has_punct:
                    should_break = True  # Break immediately if current word has punctuation
                else:
                    # Look ahead up to remaining allowance (c_hard_limit - current_length)
                    allowance = c_hard_limit - len(curr_chunk)
                    lookahead_limit = min(allowance, len(compressed_words) - i - 1)
                    found_punct = False
                    
                    for j in range(1, lookahead_limit + 1):
                        next_w_text = compressed_words[i + j]['word'].strip()
                        if next_w_text.endswith(('.', '?', '!')):
                            found_punct = True
                            break
                    
                    # If we didn't find any punctuation in the upcoming allowed words, break now.
                    # If we DID find it, we keep going (should_break = False) until we hit it in next loops.
                    if not found_punct:
                        should_break = True
            # GOLDEN fix: normal soft break — require current word has punct (has_punct), not cumulative count.
            elif len(curr_chunk) >= c_min and has_punct:
                should_break = True  # Normal soft break mid-sentence
                
            if should_break:
                chunks.append(curr_chunk)
                curr_chunk = []
                punct_seen = 0
                
        if curr_chunk:
            chunks.append(curr_chunk)

        # --- PASS 3: RAW DATA & FILLER WORDS ONLY ---
        for chunk in chunks:
            if not chunk: continue
            
            seg_start = chunk[0].get('start', 0)
            seg_end = chunk[-1].get('end', 0)
            is_first = True
            
            for w in chunk:
                raw_txt = w['word'].strip()
                cleaned = clean_word(raw_txt)
                is_hallucination = w.get('_is_hallucination', False)
                
                if cleaned or is_hallucination:
                    is_bad = cleaned in dynamic_bad
                    real_start = w['start']
                    real_end = w['end']
                    
                    status = "bad" if is_bad else None
                    
                    if is_hallucination:
                        # Wymuszenie statusu bad przy skompresowanej halucynacji
                        status = "bad"
                        is_bad = True

                    w_obj = {
                        "text": raw_txt,
                        "start": real_start, "end": real_end,
                        "selected": is_bad,
                        "status": status,
                        "is_filler": is_bad,
                        "seg_start": seg_start, "seg_end": seg_end,
                        "is_segment_start": is_first,
                        "type": "word",
                        "id": 0
                    }
                    
                    if is_hallucination:
                        w_obj['_is_hallucination'] = True  # CRITICAL: Keep tag alive for Enforcer
                        w_obj['is_auto'] = True
                        w_obj['algo_status'] = 'bad'
                        w_obj['manual_status'] = 'bad'
                        
                    if is_first: is_first = False
                    temp_words.append(w_obj)

        # NOTE: Stretched-word inaudible detector removed (v14.1) — replaced by
        # gap-based inaudible detection below which has no false positives.

        # --- GAP BRIDGING & PADDING (SILENCE LOGIC) ---
        scaled_silence = []
        if silence_ranges:
            for s in silence_ranges:
                scaled_silence.append({'s': s['s'], 'e': s['e']})
        
        if scaled_silence:
            bridged = []
            curr = scaled_silence[0]
            for next_s in scaled_silence[1:]:
                if next_s['s'] - curr['e'] < 0.15:
                    curr['e'] = next_s['e'] 
                else:
                    bridged.append(curr)
                    curr = next_s
            bridged.append(curr)
            scaled_silence = bridged

        pad_s = prefs.get('ui_spin_pad', 0.05)
        if scaled_silence:
            padded = []
            for s in scaled_silence:
                new_start = s['s'] if s['s'] < 0.01 else s['s'] + pad_s
                
                new_end = s['e']
                if audio_duration is not None and (s['e'] >= audio_duration or abs(s['e'] - audio_duration) < 0.01):
                    pass # Touching absolute end, do not pad
                else:
                    new_end -= pad_s
                    
                if new_end > new_start:
                    padded.append({'s': new_start, 'e': new_end})
            scaled_silence = padded

        raw_global_silence = scaled_silence
        silence_ranges = scaled_silence
        
        final_words = []
        
        if silence_ranges and temp_words and silence_ranges[0]['e'] < temp_words[0]['start']:
             s_start = silence_ranges[0]['s']
             s_end = silence_ranges[0]['e']
             if s_end - s_start > 0.1:
                 final_words.append({
                     "start": s_start, "end": s_end, "text": "[SILENCE]",
                     "type": "silence", "status": "silence", "selected": False,
                     "seg_start": 0, "seg_end": 0, "is_segment_start": False
                 })

        if temp_words:
            final_words.append(temp_words[0])
            for i in range(1, len(temp_words)):
                prev_w = temp_words[i-1]
                curr_w = temp_words[i]
                
                gap_start = prev_w['end']
                gap_end = curr_w['start']
                current_pos = gap_start
                
                relevant = [s for s in silence_ranges if s['e'] > gap_start and s['s'] < gap_end]
                relevant.sort(key=lambda x: x['s'])

                if not relevant:
                    if (gap_end - gap_start) >= 0.5:  # v14.1: raised to 0.5s — gap must be significant
                        final_words.append({
                            "start": gap_start, "end": gap_end,
                            "text": txt_inaudible,
                            "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                            "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False,
                            "manual_status": None, "algo_status": "inaudible", "is_auto": True
                        })
                else:
                    for s in relevant:
                        valid_start = max(current_pos, s['s'])
                        valid_end = min(s['e'], gap_end)
                        
                        if valid_start - current_pos >= 0.5:  # v14.1: 0.5s minimum
                             final_words.append({
                                "start": current_pos, "end": valid_start,
                                "text": txt_inaudible,
                                "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                                "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False,
                                "manual_status": None, "algo_status": "inaudible", "is_auto": True
                            })
                             current_pos = valid_start

                        if valid_end - valid_start > 0.1:
                            final_words.append({
                                "start": valid_start, "end": valid_end,
                                "text": "[SILENCE]",
                                "type": "silence", "status": "silence", "selected": False,
                                "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False
                            })
                            current_pos = valid_end
                    
                    if gap_end - current_pos >= 0.5:
                        final_words.append({
                            "start": current_pos, "end": gap_end,
                            "text": txt_inaudible,
                            "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                            "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False,
                            "manual_status": None, "algo_status": "inaudible", "is_auto": True
                        })

                final_words.append(curr_w)

        # Identify start noise
        first_good_found = False
        for w in final_words:
            if w.get('type') == 'silence':
                continue
            if w.get('status') in ['bad', 'inaudible']:
                if not first_good_found:
                    w['is_hidden_start'] = True
            else:
                first_good_found = True

        for i, w in enumerate(final_words): w['id'] = i
        if final_words:
            final_words[0]['meta_global_silence'] = raw_global_silence
            if 'language' in json_data:
                final_words[0]['meta_language'] = json_data.get('language')

        segments = []
        current_seg = []
        for w in final_words:
            if w.get('is_segment_start') and current_seg:
                segments.append(current_seg)
                current_seg = []
            current_seg.append(w)
        if current_seg: segments.append(current_seg)

        return final_words, segments

    # ==========================================
    # 4. TIMELINE GENERATION LOGIC (BLOCK-BASED)
    # ==========================================

    def calculate_timeline_structure(self, words_data, fps, settings):
        ops = []
        if not words_data: return ops

        # Reverted to original logic, just changed default values according to user request
        offset_s = settings.get('offset', 0.133)
        pad_s = settings.get('ui_spin_pad', 0.0)
        snap_max_s = settings.get('snap_max', 0.25)
        
        do_silence_cut = settings.get('silence_cut', False)
        do_silence_mark = settings.get('silence_mark', False)
        do_show_inaudible = settings.get('show_inaudible', True)
        do_show_typos = settings.get('show_typos', True)
        auto_cut_colors = [c.lower() for c in settings.get('auto_cut_colors', [])]
        do_show_typos = settings.get('show_typos', True)

        def t2f(t): return int(round(t * fps))
        
        offset_f = int(round(offset_s * fps))
        pad_f = int(round(pad_s * fps))
        snap_f = int(round(snap_max_s * fps))

        # FIX #2 (TAIL SILENCE): Determine the true end of the source audio.
        # words_data[0] may carry a 'meta_global_silence' list whose last element
        # tells us where the detected audio actually ends. If that is absent, fall
        # back to the 'end' field of the last word (works for FAST_SILENCE_TRACK
        # which always spans the full timeline duration).
        raw_silence = words_data[0].get('meta_global_silence', None)
        _audio_end_s = words_data[-1].get('end', 0.0)
        if raw_silence:
            _audio_end_s = max(_audio_end_s, raw_silence[-1]['e'])
        audio_end_f = t2f(_audio_end_s)

        # ── CAP to selected track duration (prevents long tail from other tracks) ──
        audio_end_cap_s = settings.get("audio_end_cap_s")
        if audio_end_cap_s:
            cap_f = t2f(audio_end_cap_s)
            log_info(f"calculate_timeline_structure: audio_end_f={audio_end_f} cap_f={cap_f} audio_end_cap_s={audio_end_cap_s:.3f}s")
            if cap_f < audio_end_f:
                log_info(f"calculate_timeline_structure: capping audio_end_f {audio_end_f} → {cap_f}.")
                audio_end_f = cap_f
            else:
                log_info(f"calculate_timeline_structure: cap ({cap_f}) >= audio_end_f ({audio_end_f}) — cap has no effect, check offset calculation!")
            # Also trim raw_silence to not extend beyond cap
            if raw_silence:
                raw_silence = [s for s in raw_silence if s['s'] < audio_end_cap_s]
                # Clamp end of last partial silence block
                if raw_silence and raw_silence[-1]['e'] > audio_end_cap_s:
                    raw_silence[-1] = dict(raw_silence[-1])
                    raw_silence[-1]['e'] = audio_end_cap_s
            # Trim words_data entries whose start is beyond the cap
            words_data = [w for w in words_data if w.get('start', 0.0) < audio_end_cap_s]

        silence_blocks_for_snap = [w for w in words_data if w.get('type') == 'silence']
        
        chunks = []
        current_chunk = None
        
        processed_words = []
        for w in words_data:
            if w.get('type') == 'silence': continue
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            
            # Fully ignore inaudible segments during timeline assembly
            # if the first checkbox (show_inaudible) is disabled.
            if is_inaudible and not do_show_inaudible:
                continue
                
            processed_words.append(w)

        if not processed_words: return []

        for w in processed_words:
            status = w.get('status', 'normal')
            if status is None: status = 'normal'
            if status == 'typo' and w.get('is_auto') and not do_show_typos:
                status = 'normal'
            
            if current_chunk is None:
                current_chunk = {'status': status, 'words': [w]}
            else:
                if current_chunk['status'] == status:
                    current_chunk['words'].append(w)
                else:
                    chunks.append(current_chunk)
                    current_chunk = {'status': status, 'words': [w]}
        
        if current_chunk: chunks.append(current_chunk)

        ops_raw = []
        current_time_f = 0
        
        for i, chunk in enumerate(chunks):
            chunk_end_w = chunk['words'][-1]['end']
            block_start_f = current_time_f
            
            if i < len(chunks) - 1:
                next_chunk_start = chunks[i+1]['words'][0]['start']
                # We ADD offset_f because Whisper timestamps are typically early,
                # and a positive offset_f shifts the cut later to align with real speech.
                cut_f = t2f(next_chunk_start) + offset_f
                
                for s in silence_blocks_for_snap:
                    s_start_f = t2f(s['start'])
                    s_end_f = t2f(s['end'])
                    if abs(cut_f - s_start_f) <= snap_f:
                        cut_f = s_start_f
                        break
                    if abs(cut_f - s_end_f) <= snap_f:
                        cut_f = s_end_f
                        break
                
                if cut_f < block_start_f: cut_f = block_start_f + 1
                block_end_f = cut_f
            else:
                # FIX #2 (TAIL SILENCE): Last block must extend to the actual end
                # of the source audio, not just the last word's timestamp.
                # We NEVER exceed audio_end_f to avoid creating phantom fragments at the end.
                raw_block_end = max(audio_end_f, t2f(chunk_end_w)) + pad_f
                block_end_f = min(raw_block_end, audio_end_f)
            
            ops_raw.append({
                's': block_start_f,
                'e': block_end_f,
                'type': chunk['status']
            })
            current_time_f = block_end_f

        if do_silence_cut or do_silence_mark:
            final_ops = []
            s_ranges = []
            
            if raw_silence is not None:
                for s in raw_silence:
                    if (s['e'] - s['s']) < 0.2: continue
                    s_ranges.append((t2f(s['s']), t2f(s['e'])))
            else:
                for s in silence_blocks_for_snap:
                    if (s['end'] - s['start']) < 0.2: continue 
                    s_ranges.append((t2f(s['start']), t2f(s['end'])))
            
            ops_raw.sort(key=lambda x: x['s'])
            
            for op in ops_raw:
                if (op['type'] == 'bad' or op['type'] == 'inaudible') and do_silence_mark and not do_silence_cut:
                    final_ops.append(op)
                    continue

                sub_segments = [op]
                for s_s, s_e in s_ranges:
                    new_sub = []
                    for sub in sub_segments:
                        if s_e <= sub['s'] or s_s >= sub['e']:
                            new_sub.append(sub)
                        elif s_s <= sub['s'] and s_e >= sub['e']:
                            if do_silence_mark:
                                new_sub.append({'s': sub['s'], 'e': sub['e'], 'type': 'silence_mark'})
                        else:
                            if s_s > sub['s']:
                                new_sub.append({'s': sub['s'], 'e': s_s, 'type': sub['type']})
                            
                            if do_silence_mark:
                                overlap_s = max(sub['s'], s_s)
                                overlap_e = min(sub['e'], s_e)
                                new_sub.append({'s': overlap_s, 'e': overlap_e, 'type': 'silence_mark'})
                            
                            if s_e < sub['e']:
                                new_sub.append({'s': s_e, 'e': sub['e'], 'type': sub['type']})
                                
                    sub_segments = new_sub
                final_ops.extend(sub_segments)
            ops_raw = final_ops

        ops_raw.sort(key=lambda x: x['s'])
        
        merged_ops = []
        if ops_raw:
            curr = ops_raw[0]
            for next_op in ops_raw[1:]:
                if next_op['type'] == curr['type'] and next_op['s'] <= curr['e'] + 1:
                    curr['e'] = max(curr['e'], next_op['e'])
                else:
                    merged_ops.append(curr)
                    curr = next_op
            merged_ops.append(curr)
            
        # Write exact final anchors back into EVERY source word.
        # This allows the GUI to flawlessly jump to any word's start, even if it's in the middle of a clip,
        # by predicting exactly where the cut would be if that word was a block start.
        for w in processed_words:
            w_start_f = t2f(w.get('start', 0.0)) + offset_f
            
            for s in silence_blocks_for_snap:
                s_start_f = t2f(s['start'])
                s_end_f = t2f(s['end'])
                if abs(w_start_f - s_start_f) <= snap_f:
                    w_start_f = s_start_f
                    break
                if abs(w_start_f - s_end_f) <= snap_f:
                    w_start_f = s_end_f
                    break
                    
            if w_start_f < 0:
                w_start_f = 0
            w['anchor_start'] = w_start_f / fps
            
        def get_color_for_type(op_type):
            COLOR_MAP = {
                "bad":          "Violet",
                "repeat":       "Navy",
                "typo":         "Olive",
                "inaudible":    "Chocolate",
                "silence_mark": "Tan"
            }
            c = COLOR_MAP.get(op_type)
            if not c and str(op_type).startswith("custom_"):
                c = op_type.split("_")[1]
            return c.lower() if c else None

        final_result = []
        for op in merged_ops:
            op_c = get_color_for_type(op['type'])
            if op_c and op_c in auto_cut_colors:
                continue
            if op['e'] - op['s'] < 2: continue 
            final_result.append(op)
            
        return final_result

    # ==========================================
    # 5. PROJECT & DATA MANAGEMENT (Data Controller)
    # ==========================================

    def api_delete_clips_by_color(self, color_name, new_timeline=True):
        if self.resolve_handler:
            self.resolve_handler.delete_clips_by_color(color_name, new_timeline)

    # ==========================================
    # 5b. BWS PROJECT ARCHIVE (v2)
    # ==========================================

    def build_assembly_recipe(self, clean_ops, fps):
        """Build an assembly recipe dict from ops for storage in .bws."""
        if not clean_ops:
            return None
        return {
            "type": "wave_concat",
            "fps": fps,
            "source": "audio/source.flac",
            "ops": [{"s": op["s"], "e": op["e"], "type": op["type"]} for op in clean_ops]
        }

    def execute_assembly_recipe(self, recipe, source_audio_path, output_path):
        """
        Execute an assembly recipe against a source audio file (using exact wave slicing).
        Produces the assembled/cut audio at output_path.
        Returns True on success.
        """
        if not recipe or recipe.get("type") not in ("ffmpeg_concat", "wave_concat"):
            return False

        ops = recipe.get("ops", [])
        fps = recipe.get("fps", 24.0)
        if not ops or not source_audio_path or not os.path.exists(source_audio_path):
            return False

        try:
            import tempfile
            import wave
            import subprocess

            temp_wav_src = tempfile.mktemp(suffix=".wav")
            temp_wav_cut = tempfile.mktemp(suffix=".wav")

            # 1. Decode source (FLAC or other) to WAV
            decode_cmd = [
                self.ffmpeg_cmd, "-y", "-i", source_audio_path,
                "-acodec", "pcm_s16le", temp_wav_src
            ]
            subprocess.run(decode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **self.os_doc.get_subprocess_kwargs())

            if not os.path.exists(temp_wav_src):
                return False

            # 2. Slice EXACTLY using wave
            with wave.open(temp_wav_src, 'rb') as w_in:
                params = w_in.getparams()
                with wave.open(temp_wav_cut, 'wb') as w_out:
                    w_out.setparams(params)
                    sr = params.framerate

                    for op in ops:
                        start_s = op['s'] / fps
                        end_s = op['e'] / fps
                        
                        start_frame = int(start_s * sr)
                        end_frame = int(end_s * sr)
                        frames_to_read = max(0, end_frame - start_frame)
                        
                        if frames_to_read > 0:
                            w_in.setpos(start_frame)
                            data = w_in.readframes(frames_to_read)
                            w_out.writeframes(data)

            # 3. Encode cut WAV to FLAC (output format required by .bws structure)
            encode_cmd = [
                self.ffmpeg_cmd, "-y", "-i", temp_wav_cut,
                "-acodec", "flac", "-compression_level", "5", output_path
            ]
            subprocess.run(encode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **self.os_doc.get_subprocess_kwargs())

            # Cleanup
            try: os.remove(temp_wav_src)
            except: pass
            try: os.remove(temp_wav_cut)
            except: pass

            if os.path.exists(output_path):
                log_info(f"execute_assembly_recipe: wrote {output_path}")
                return True
            return False
            
        except Exception as e:
            log_error(f"execute_assembly_recipe error: {e}")
            return False

    def build_media_inventory(self, source_files):
        """
        Build a media inventory list from source file paths.
        Each entry stores basename, size, and a partial 4KB checksum for fast verification.
        """
        import hashlib
        inventory = []
        for fp in (source_files or []):
            if not fp:
                continue
            entry = {
                "path": fp,
                "basename": os.path.basename(fp),
                "size_bytes": 0,
                "checksum_sha256_4k": "",
                "last_modified": 0.0,
            }
            try:
                if os.path.exists(fp):
                    stat = os.stat(fp)
                    entry["size_bytes"] = stat.st_size
                    entry["last_modified"] = stat.st_mtime
                    # Hash first 4 KB for fast integrity check
                    with open(fp, 'rb') as f:
                        head = f.read(4096)
                    entry["checksum_sha256_4k"] = hashlib.sha256(head).hexdigest()
            except Exception as e:
                log_error(f"build_media_inventory: error reading {fp}: {e}")
            inventory.append(entry)
        return inventory

    def verify_media_inventory(self, inventory):
        """
        Verify that all media files from an inventory exist and match.
        Returns (missing: list, changed: list) of inventory entries.
        """
        missing = []
        changed = []
        import hashlib
        for entry in (inventory or []):
            path = entry.get("path", "")
            if not path or not os.path.exists(path):
                missing.append(entry)
                continue
            try:
                actual_size = os.path.getsize(path)
                if actual_size != entry.get("size_bytes", 0):
                    changed.append(entry)
                    continue
                # Verify partial checksum
                expected_hash = entry.get("checksum_sha256_4k", "")
                if expected_hash:
                    with open(path, 'rb') as f:
                        head = f.read(4096)
                    actual_hash = hashlib.sha256(head).hexdigest()
                    if actual_hash != expected_hash:
                        changed.append(entry)
            except Exception:
                changed.append(entry)
        return missing, changed

    def export_source_drt(self, timeline_name):
        """
        Export the source timeline as .drt for bundling into .bws.
        Returns the path to the exported .drt file, or None on failure.
        """
        if not self.resolve_handler:
            return None
        try:
            target_tl = None
            count = self.resolve_handler.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = self.resolve_handler.project.GetTimelineByIndex(i)
                if tl and tl.GetName() == timeline_name:
                    target_tl = tl
                    break

            if not target_tl:
                log_error(f"export_source_drt: timeline '{timeline_name}' not found.")
                return None

            export_type = getattr(self.resolve_handler.resolve, 'EXPORT_DRT', None)
            if export_type is None:
                log_info("export_source_drt: EXPORT_DRT not available in this Resolve version.")
                return None

            temp_dir = self.os_doc.get_temp_folder()
            os.makedirs(temp_dir, exist_ok=True)
            safe_name = "".join(c for c in timeline_name if c.isalnum() or c in '_- ')
            drt_path = os.path.join(temp_dir, f"bws_source_{safe_name.replace(' ', '_')}.drt")

            if os.path.exists(drt_path):
                try:
                    os.remove(drt_path)
                except Exception as e:
                    log_error(f"export_source_drt: could not remove existing file: {e}")

            export_ok = target_tl.Export(drt_path, export_type)
            if export_ok and os.path.exists(drt_path):
                log_info(f"export_source_drt: exported '{timeline_name}' → {drt_path} "
                         f"({os.path.getsize(drt_path)} bytes)")
                return drt_path
            else:
                log_error("export_source_drt: Export() failed.")
                return None

        except Exception as e:
            log_error(f"export_source_drt error: {e}")
            return None

    def _get_resolve_project_name(self):
        """Get the current DaVinci Resolve project name, or empty string."""
        try:
            if self.resolve_handler and self.resolve_handler.project:
                return self.resolve_handler.project.GetName() or ""
        except Exception:
            pass
        return ""

    def _optimize_words_floats(self, words):
        """Round float fields in words list for compact JSON."""
        optimized = []
        for w in words:
            w_clean = w.copy()
            if 'start' in w_clean: w_clean['start'] = round(w['start'], 3)
            if 'end' in w_clean: w_clean['end'] = round(w['end'], 3)
            if 'seg_start' in w_clean: w_clean['seg_start'] = round(w['seg_start'], 3)
            if 'seg_end' in w_clean: w_clean['seg_end'] = round(w['seg_end'], 3)
            optimized.append(w_clean)
        return optimized

    # ==========================================
    # 6. WRAPPERS (Logic Orchestration)
    # ==========================================

    def run_standalone_analysis(self, words_data, show_inaudible=True):
        prefs = self.os_doc.get_all_prefs()
        algo_settings = {k: prefs[k] for k in ('algo_fuzzy_threshold', 'algo_retake_lookahead', 'algo_distance_penalty', 'algo_anchor_depth') if k in prefs}
        processed_words, count = algorithms.analyze_repeats(words_data, show_inaudible=show_inaudible, algo_settings=algo_settings)
        processed_words = algorithms.absorb_inaudible_into_repeats(processed_words)
        processed_words = self._enforce_hallucination_status(processed_words)
        
        # Re-index IDs to prevent UI selection desync after word deletion
        for i, w in enumerate(processed_words):
            w['id'] = i
            
        return processed_words, count

    def run_compare_in_subprocess(self, script_text, words_data, algo_settings=None):
        import time
        import subprocess
        
        unique_name = f"compare_{int(time.time() * 1000)}"
        output_dir = self.os_doc.get_temp_folder()
        os.makedirs(output_dir, exist_ok=True)
        
        input_json_path = os.path.join(output_dir, f"{unique_name}_in.json")
        output_json_path = os.path.join(output_dir, f"{unique_name}_out.json")
        runner_script_path = os.path.join(output_dir, f"{unique_name}_runner.py")
        
        clean_words = []
        for w in words_data:
            clean_w = {}
            for k, v in w.items():
                if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                    clean_w[k] = v
            clean_words.append(clean_w)
            
        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "script_text": script_text,
                "words_data": clean_words,
                "algo_settings": algo_settings or {}
            }, f)
            
        script_content = f"""
import sys
import json
import os

src_dir = {repr(os.path.dirname(os.path.abspath(__file__)))}
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    import algorithms
    with open({repr(input_json_path)}, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    result_words = algorithms.compare_script_to_transcript(
        data.get('script_text', ''), 
        data.get('words_data', []), 
        algo_settings=data.get('algo_settings')
    )
    
    with open({repr(output_json_path)}, 'w', encoding='utf-8') as f:
        json.dump(result_words, f)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
        with open(runner_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
            
        python_exec = self._get_python_executable()
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        cmd = [python_exec, runner_script_path]
        
        log_info(f"Running CompareEngine in subprocess... Script: {runner_script_path}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True,
                env=env,
                **self.os_doc.get_subprocess_kwargs()
            )
            
            stdout, _ = process.communicate()
            
            if process.returncode != 0:
                log_error(f"Compare subprocess failed:\\n{stdout}")
                return words_data
                
            if not os.path.exists(output_json_path):
                log_error("Compare subprocess finished but output json not found.")
                return words_data
                
            with open(output_json_path, 'r', encoding='utf-8') as f:
                result_words = json.load(f)
                
            return result_words
        except Exception as e:
            log_error(f"Error launching compare subprocess: {e}")
            return words_data
        finally:
            try: os.remove(input_json_path)
            except: pass
            try: os.remove(output_json_path)
            except: pass
            try: os.remove(runner_script_path)
            except: pass

    def run_comparison_analysis(self, script_text, words_data):
        prefs = self.os_doc.get_all_prefs()
        algo_settings = {k: prefs[k] for k in ('algo_fuzzy_threshold', 'algo_retake_lookahead', 'algo_distance_penalty', 'algo_anchor_depth') if k in prefs}
        
        # v9.6 FORCE HYBRID FUSION ENGINE (V6)
        # which causes aggressive false positive "blue" retakes. We force V6 to ensure accurate results.
        
        # Multiprocessing in PyInstaller without freeze_support() causes a fatal crash.
        # However, blocking the GUI thread (GIL) during DP loop causes freezing.
        # We now offload it completely to a separate process via subprocess to guarantee fluid UI.
        result_words = self.run_compare_in_subprocess(script_text, words_data, algo_settings=algo_settings)
            
        final_words = algorithms.absorb_inaudible_into_repeats(result_words)
        # FIX: Force hallucination status after script comparison analysis
        final_words = self._enforce_hallucination_status(final_words)
        
        # Re-index IDs to prevent UI selection desync after word deletion
        for i, w in enumerate(final_words):
            w['id'] = i
            
        return final_words

    # ==========================================
    # 7. ASSEMBLY ORCHESTRATION (THE COMPOUND FIX)
    # ==========================================

    def start_timeline_generation(self, words_data, settings, callbacks):
        import threading
        
        def runner():
            result = self.assemble_timeline(
                words_data,
                settings,
                callback_status=callbacks.get('on_status'),
                callback_progress=callbacks.get('on_progress')
            )
            
            if isinstance(result, tuple):
                success, warning = result
            else:
                success, warning = result, None
            
            if success:
                if callbacks.get('on_success'):
                    try:
                        callbacks['on_success'](warning)
                    except TypeError:
                         callbacks['on_success']()
            else:
                if callbacks.get('on_error'): callbacks['on_error']("Assembly failed. Check logs.")

        t = threading.Thread(target=runner, daemon=True)
        t.start()

    def assemble_timeline(self, words_data, settings, callback_status=None, callback_progress=None):
        """
        3-TIER ASSEMBLY PIPELINE:

        TIER 1 — DRT (primary): Export source timeline as native .drt,
        modify SeqContainer XML (Start/Duration/In only), reimport.
        Preserves 100% of DaVinci-specific data.

        TIER 2 — FCP7 XML (fallback): Export as FCP7 XML, apply ops,
        reimport.  Handles most clip types but loses some DaVinci specifics.

        TIER 3 — AppendToTimeline (emergency): Legacy clip-by-clip method.
        Used only when both DRT and XML paths fail completely.
        """
        warning_code = None

        def set_status(msg):
            if callback_status: callback_status(msg)
            else: log_info(msg)

        def set_progress(val):
            if callback_progress: callback_progress(val)

        try:
            set_status(self.txt("status_assembly_init"))
            set_progress(-1)

            self.resolve_handler.refresh_context()
            if not self.resolve_handler.timeline:
                log_error("No active timeline found.")
                return False, None, None, None

            # ── SOURCE SNAPSHOT ───────────────────────────────────────────────
            source_snapshot   = settings.get("source_snapshot") or {}
            original_tl_name  = source_snapshot.get("timeline_name") or settings.get("original_timeline_name")
            if not original_tl_name:
                original_tl_name = self.resolve_handler.timeline.GetName()
                log_info(f"assemble_timeline: No source snapshot, using active: '{original_tl_name}'")
            else:
                log_info(f"assemble_timeline: Source snapshot → '{original_tl_name}'")

            track_indices = source_snapshot.get("track_indices") or []

            # ── SOURCE TIMELINE INSPECTION (single pass) ──────────────────────
            # Determine: audio_only_mode, a_track_count, for later use.
            context_type  = "video"  # default
            a_track_count = 0
            try:
                count = self.resolve_handler.project.GetTimelineCount()
                for i in range(1, count + 1):
                    tl = self.resolve_handler.project.GetTimelineByIndex(i)
                    if tl.GetName() == original_tl_name:
                        a_track_count = tl.GetTrackCount("audio")
                        v_count       = tl.GetTrackCount("video")
                        v_has_clips   = False
                        for vi in range(1, v_count + 1):
                            if tl.GetItemListInTrack("video", vi):
                                v_has_clips = True
                                break
                        if not v_has_clips:
                            context_type = "audio"
                        break
            except Exception:
                pass
            audio_only_mode = (context_type == "audio")

            # ── AUDIO CAP: determine true end of selected tracks ──────────────
            audio_end_cap_s = None

            all_tracks_selected = (not track_indices) or (
                a_track_count > 0 and len(track_indices) >= a_track_count
            )

            if track_indices and not all_tracks_selected:
                audio_end_cap_s = self.resolve_handler.get_selected_tracks_end_seconds(
                    original_tl_name, track_indices
                )
                if audio_end_cap_s:
                    log_info(f"assemble_timeline: audio cap at {audio_end_cap_s:.3f}s")

            # ── CALCULATE CUTS ────────────────────────────────────────────────
            set_status(self.txt("status_calc_cuts"))
            fps = self.resolve_handler.fps
            calc_settings = dict(settings)
            if audio_end_cap_s:
                calc_settings["audio_end_cap_s"] = audio_end_cap_s
            clean_ops = self.calculate_timeline_structure(words_data, fps, calc_settings)
            time.sleep(0.05)

            # ── NAME FOR NEW TIMELINE ─────────────────────────────────────────
            clean_name, next_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
            new_tl_name = f"{clean_name} BadWords Edit {next_idx}"

            # ── LOAD SETTINGS ─────────────────────────────────────────────────
            import config
            prefs = self.os_doc.get_all_prefs()
            preserve_track_order = bool(prefs.get(
                "xml_preserve_track_order",
                config.DEFAULT_SETTINGS["xml_preserve_track_order"]
            ))
            # auto_del is already baked into clean_ops by calculate_timeline_structure().
            # No need to pass it further down the XML pipeline.

            # ══════════════════════════════════════════════════════════════════
            # TIER 1 — PRIMARY: NATIVE .drt ASSEMBLY
            # Preserves 100% of DaVinci-specific data (adjustment clips,
            # generators, Fusion comps, color grading, all binary metadata).
            # ══════════════════════════════════════════════════════════════════
            drt_success = False
            drt_tl_name = None

            try:
                import assembler

                set_status(self.txt("status_assembly_xml_build"))
                set_progress(-1)

                temp_dir = self.os_doc.get_temp_folder()
                os.makedirs(temp_dir, exist_ok=True)
                
                audio_track_filter = None
                video_track_filter = None
                
                track_config = source_snapshot.get('assembly_track_config')
                if track_config:
                    amode = track_config.get('audio_mode', 'all')
                    if amode == 'tr':
                        audio_track_filter = track_indices if track_indices else None
                    elif amode == 'cust':
                        audio_track_filter = track_config.get('audio_custom', [])
                    
                    vmode = track_config.get('video_mode', 'all')
                    if vmode == 'none':
                        video_track_filter = []
                    elif vmode == 'cust':
                        video_track_filter = track_config.get('video_custom', [])

                log_info("assemble_timeline: TIER 1 — attempting DRT primary path...")
                drt_ok, drt_colors, drt_name = assembler.assemble_via_drt(
                    self.resolve_handler,
                    original_tl_name,
                    clean_ops,
                    new_tl_name,
                    audio_only_mode=audio_only_mode,
                    audio_track_filter=audio_track_filter,
                    video_track_filter=video_track_filter,
                    preserve_track_order=preserve_track_order,
                    temp_dir=temp_dir
                )

                if drt_ok and drt_name:
                    drt_success = True
                    drt_tl_name = drt_name
                    log_info(f"assemble_timeline: DRT path succeeded → '{drt_tl_name}'")

                    # Apply / verify clip colors
                    set_status(self.txt("status_assembly_colors"))
                    self.resolve_handler.reapply_clip_colors(drt_tl_name, drt_colors or {})
                    new_tl_name = drt_tl_name
                else:
                    log_error("assemble_timeline: DRT path failed, falling to TIER 2 (XML)...")

            except Exception as drt_err:
                log_error(f"assemble_timeline: DRT path exception: {drt_err}")
                import traceback as _tb
                log_error(_tb.format_exc())

            # ──────────────────────────────────────────────────────────────────
            # TIER 2 — FALLBACK #1: FCP7 XML EXPORT → CUT → IMPORT
            # Used when DRT path fails (e.g. EXPORT_DRT not available,
            # or .drt import returned None).
            # ──────────────────────────────────────────────────────────────────
            xml_success  = False
            xml_tl_name  = None
            src_xml_path = ""  # initialised before try so finally block can reference them
            cut_xml_path = ""

            if not drt_success:

                try:
                    temp_dir = self.os_doc.get_temp_folder()
                    os.makedirs(temp_dir, exist_ok=True)
                    safe_name = "".join(c for c in new_tl_name if c.isalnum() or c in '_-')
                    src_xml_path = os.path.join(temp_dir, f"bw_src_{safe_name}.xml")
                    cut_xml_path = os.path.join(temp_dir, f"bw_cut_{safe_name}.xml")

                    # Step 1: Export source timeline XML (Resolve native, all clip types)
                    set_status(self.txt("status_assembly_xml_build"))
                    set_progress(-1)
                    time.sleep(0.05)
                    log_info("assemble_timeline: TIER 2 — attempting FCP7 XML fallback...")
                    export_ok = self.resolve_handler.export_timeline_xml(
                        original_tl_name, src_xml_path
                    )
                    time.sleep(0.05)
                    if not export_ok:
                        log_error("assemble_timeline: source XML export failed.")
                    else:
                        # Step 2: Apply op-cuts to the exported XML
                        ok_cut, color_schedule = self.resolve_handler.apply_ops_cuts_to_timeline_xml(
                            src_xml_path, clean_ops, cut_xml_path, audio_only_mode=audio_only_mode
                        )
                        time.sleep(0.05)

                        if ok_cut:
                            set_status(self.txt("status_assembly_xml_import"))
                            set_progress(-1)

                            # CRITICAL: Reset current folder to Root before import.
                            root_folder = self.resolve_handler.media_pool.GetRootFolder()
                            if root_folder:
                                self.resolve_handler.media_pool.SetCurrentFolder(root_folder)

                            import_options = {
                                "timelineName": new_tl_name,
                                "importSourceClips": True
                            }

                            new_tl = self.resolve_handler.media_pool.ImportTimelineFromFile(
                                cut_xml_path,
                                import_options,
                            )
                            time.sleep(0.05)

                            if new_tl:
                                actual_name = new_tl.GetName()
                                log_info(f"assemble_timeline: XML import OK → '{actual_name}'")
                                xml_tl_name = actual_name

                                # Move timeline into BadWords/ root bin
                                bw_bin = self.resolve_handler.get_badwords_root_bin()
                                if bw_bin:
                                    try:
                                        tl_item = self.resolve_handler.find_timeline_item_recursive(
                                            self.resolve_handler.media_pool.GetRootFolder(), actual_name
                                        )
                                        if tl_item:
                                            self.resolve_handler.media_pool.MoveClips([tl_item], bw_bin)
                                            log_info(f"assemble_timeline: moved '{actual_name}' → BadWords/")
                                        else:
                                            log_error("assemble_timeline: timeline item not found in pool")
                                    except Exception as move_err:
                                        log_error(f"assemble_timeline: MoveClips error: {move_err}")

                                # Apply / verify clip colors
                                set_status(self.txt("status_assembly_colors"))
                                self.resolve_handler.reapply_clip_colors(xml_tl_name, color_schedule)

                                xml_success = True
                                new_tl_name = xml_tl_name
                            else:
                                log_error("assemble_timeline: ImportTimelineFromFile returned None.")
                        else:
                            log_error("assemble_timeline: apply_ops_cuts_to_timeline_xml failed.")

                except Exception as xml_err:
                    log_error(f"assemble_timeline: XML path exception: {xml_err}")
                    import traceback as _tb
                    log_error(_tb.format_exc())
                finally:
                    # Cleanup temp XMLs
                    for _p in (src_xml_path, cut_xml_path):
                        try:
                            if os.path.exists(_p):
                                os.remove(_p)
                        except Exception:
                            pass

            # ──────────────────────────────────────────────────────────────────
            # TIER 3 — EMERGENCY FALLBACK: AppendToTimeline
            # Triggered ONLY if both DRT and XML paths completely failed.
            # ──────────────────────────────────────────────────────────────────
            if not drt_success and not xml_success:
                log_error("assemble_timeline: !! EMERGENCY FALLBACK — AppendToTimeline !!")
                log_error("assemble_timeline: XML path failed. Using legacy method.")

                # For fallback we need a source_item (old logic)
                source_tl_for_fallback = original_tl_name
                if track_indices and not all_tracks_selected:
                    # Try to create filtered TL as before (old code reused)
                    try:
                        tmp_dir = self.os_doc.get_temp_folder()
                        os.makedirs(tmp_dir, exist_ok=True)
                        s_safe = "".join(c for c in original_tl_name
                                         if c.isalnum() or c in '_-')
                        raw_xml      = os.path.join(tmp_dir, f"bw_raw_{s_safe}.xml")
                        filtered_xml = os.path.join(tmp_dir, f"bw_filtered_{s_safe}.xml")
                        if self.resolve_handler.export_timeline_xml(original_tl_name, raw_xml):
                            if self.resolve_handler.filter_xml_tracks(raw_xml, filtered_xml, track_indices):
                                fl_name = self.resolve_handler.import_xml_as_timeline(
                                    filtered_xml, original_tl_name, audio_only_mode=audio_only_mode
                                )
                                if fl_name:
                                    source_tl_for_fallback = fl_name
                    except Exception as fb_xml_err:
                        log_error(f"assemble_timeline: Fallback XML pre-filter: {fb_xml_err}")

                set_status(self.txt("status_assembly_source"))
                source_item, fb_context = self.resolve_handler.get_optimal_source_item(
                    source_tl_for_fallback
                )
                if not source_item:
                    log_error("assemble_timeline: Fallback also failed — no source item.")
                    return False, None, None, None

                audio_only_mode = (fb_context == "audio")

                # Re-compute edit name (may have been taken if XML partially worked)
                fb_name, fb_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
                fb_tl_name = f"{fb_name} BadWords Edit {fb_idx}"

                def fb_progress(current, total):
                    set_progress(int((current / max(1, total)) * 100))
                    set_status(f"{self.txt('status_assembly_clips')} {current}/{total}...")

                set_status(self.txt("status_assembly_resolve"))
                fb_ok = self.resolve_handler.generate_timeline_from_ops(
                    clean_ops, source_item, fb_tl_name,
                    audio_only_mode=audio_only_mode,
                    progress_callback=fb_progress
                )
                if not fb_ok:
                    log_error("assemble_timeline: Emergency fallback also failed.")
                    return False, None, None, None

                new_tl_name = fb_tl_name
                log_info(f"assemble_timeline: Fallback succeeded → '{new_tl_name}'")

            # ── Return to Edit page & cleanup ─────────────────────────────────
            try:
                if self.resolve_handler.resolve:
                    self.resolve_handler.resolve.OpenPage("edit")
            except Exception:
                pass

            import gc
            gc.collect()

            set_progress(100)
            return True, warning_code, new_tl_name, clean_ops

        except Exception as e:
            log_error(f"Assembly Critical Error: {e}")
            traceback.print_exc()
            return False, None, None, None