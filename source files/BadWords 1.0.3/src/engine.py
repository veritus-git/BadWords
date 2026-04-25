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
"""

import os
import sys
import json
import time
import shutil
import subprocess
import urllib.request
import re
import traceback
import platform
import random # Added for ID generation

import config
import algorythms
from osdoc import log_info, log_error

class AudioEngine:
    def __init__(self, os_doctor, resolve_handler):
        self.os_doc = os_doctor
        self.resolve_handler = resolve_handler
        self.ffmpeg_cmd = self.os_doc.get_ffmpeg_cmd() or "ffmpeg"

    # ==========================================
    # 1. EXTERNAL PROCESS MANAGEMENT (WHISPER)
    # ==========================================

    def get_whisper_executable(self):
        """Finds Whisper executable in the system."""
        possible_paths = []
        
        if self.os_doc.is_win:
             possible_paths.append(shutil.which("whisper.exe"))
             possible_paths.append(shutil.which("whisper"))
             try:
                 import sysconfig
                 scripts = sysconfig.get_path("scripts")
                 possible_paths.append(os.path.join(scripts, "whisper.exe"))
             except: pass
        else:
             home = self.os_doc.home_dir
             possible_paths.append(os.path.join(home, ".local", "bin", "whisper"))
             possible_paths.append(os.path.join(home, ".local/share/pipx/venvs/openai-whisper/bin/whisper"))
             possible_paths.append("/usr/local/bin/whisper")
             possible_paths.append("/usr/bin/whisper")
             possible_paths.append(shutil.which("whisper"))

        for path in possible_paths:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                log_info(f"Found Whisper at: {path}")
                return path
        
        return "whisper" # Fallback to PATH command

    def _get_external_python_executable(self):
        """
        Locates the Python interpreter associated with the Whisper installation.
        RESTORED: Crucial for pipx environments on Linux.
        """
        # 1. Try to find the specific pipx python environment (Linux/Mac)
        if not self.os_doc.is_win:
            home = self.os_doc.home_dir
            pipx_python = os.path.join(home, ".local/share/pipx/venvs/openai-whisper/bin/python")
            if os.path.exists(pipx_python):
                return pipx_python
            
            # Check for generic 'python' in ~/.local/bin if mapped
            local_python = os.path.join(home, ".local/bin/python3")
            if os.path.exists(local_python):
                return local_python

        # 2. Try to derive python from the whisper executable path
        whisper_bin = self.get_whisper_executable()
        if whisper_bin and os.path.isabs(whisper_bin):
            bin_dir = os.path.dirname(whisper_bin)
            neighbor_python = os.path.join(bin_dir, "python")
            if self.os_doc.is_win: neighbor_python += ".exe"
            
            if os.path.exists(neighbor_python):
                return neighbor_python

        # 3. Fallback
        return "python3" if not self.os_doc.is_win else "python"

    def download_whisper_model_interactive(self, model_name, progress_callback=None):
        """
        Forces the download of a specific Whisper model by running a dummy python script.
        Uses external python to ensure access to the whisper library (pipx support).
        """
        log_info(f"Starting interactive download for model: {model_name}")
        
        # Python script to trigger download via library
        py_script = f"import whisper; whisper.load_model('{model_name}')"
        
        # Use the detected external python, NOT sys.executable (which is DaVinci's)
        python_exec = self._get_external_python_executable()
        log_info(f"Using Python for download: {python_exec}")
        
        cmd = [python_exec, "-c", py_script]
        
        startup_info = self.os_doc.get_startup_info()
        
        try:
            # We must use Popen to read output in real-time
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                startupinfo=startup_info,
                env=os.environ.copy() # Pass current env
            )
            
            # Whisper uses tqdm which prints to stderr
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    # Parse TQDM progress: " 20%|██      | 100M/500M"
                    match = re.search(r'(\d+)%', line)
                    if match and progress_callback:
                        try:
                            val = int(match.group(1))
                            progress_callback(val)
                        except: pass
            
            if process.returncode == 0:
                log_info(f"Model {model_name} ready.")
                if progress_callback: progress_callback(100)
                return True
            else:
                log_error(f"Model download process returned error code {process.returncode}")
                return False
                
        except Exception as e:
            log_error(f"Interactive download failed: {e}")
            return False

    def check_model_exists(self, tech_name):
        """
        Checks if the Whisper model exists in standard cache locations.
        Moves logic from GUI to Engine.
        """
        paths_to_check = []
        home = os.path.expanduser("~")
        
        # Standard .cache location (Linux/Mac/Generic)
        paths_to_check.append(os.path.join(home, ".cache", "whisper"))
        
        if platform.system() == "Windows":
             # Windows specific paths
             paths_to_check.append(os.path.join(os.environ.get("USERPROFILE", home), ".cache", "whisper"))
             paths_to_check.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "whisper"))
             
             # Additional fallback for Windows user home if environment vars differ
             if "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
                 home_drive = os.environ["HOMEDRIVE"] + os.environ["HOMEPATH"]
                 paths_to_check.append(os.path.join(home_drive, ".cache", "whisper"))

        candidates = [f"{tech_name}.pt"]
        if tech_name == "large":
            candidates.extend(["large-v3.pt", "large-v2.pt"])
            
        for path_dir in paths_to_check:
            if not os.path.exists(path_dir): continue
            
            for fname in candidates:
                if os.path.exists(os.path.join(path_dir, fname)):
                    return True
        return False

    def run_whisper(self, audio_path, model, lang, verbatim, device_mode, filler_words_list=None):
        """
        Runs Whisper transcription process.
        Returns path to generated JSON file.
        """
        unique_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = self.os_doc.get_temp_folder()
        whisper_exec = self.get_whisper_executable()

        # Environment configuration
        env = os.environ.copy()
        # Clean env to avoid conflicts
        for k in ["PYTHONHOME", "PYTHONPATH", "LD_LIBRARY_PATH", "LIBPATH", "LD_PRELOAD"]:
            if k in env: del env[k]
        
        env["OMP_NUM_THREADS"] = "1"
        local_bin = os.path.join(self.os_doc.home_dir, ".local", "bin")
        env["PATH"] = f"{local_bin}{os.pathsep}{env.get('PATH', '')}"

        def build_cmd(force_cpu=False):
            use_fp16 = "True" 
            
            # --- PROMPT V11.0: BALANCED & EXPLICIT ---
            base_verbatim_prompt = (
                "Umm, uh, yyy. Transcribe exactly. "
                "Repetitions: 'Tak tak tak', 'Yes yes yes'. "
                "Phrase restarts: 'I went to- I went to di- I went to the store', 'That means- that means'. "
                "Stutters: 't-t-today'. "
                "Do not merge sentences. Keep raw."
            )
            
            full_prompt = base_verbatim_prompt
            if verbatim and filler_words_list:
                user_fillers = ", ".join(filler_words_list)
                if user_fillers.strip():
                    full_prompt += f" {user_fillers}"

            cmd = [whisper_exec, audio_path, "--model", model, "--output_format", "json", 
                   "--output_dir", output_dir, "--word_timestamps", "True", "--fp16", use_fp16]
            
            # --- PARAMETERS V11.0: ORGANIC SENSITIVITY ---
            
            if verbatim:
                # 1. SAMPLING (CHAOTIC) MODE ACTIVATED
                # Beam search is too stable for disjointed repetitions.
                # Sampling with low temp allows "organic" errors (like repetitions).
                cmd.extend(["--temperature", "0.27"]) 
                
                # 2. BEST OF 7
                # Give it more attempts to catch the tricky repetition path.
                cmd.extend(["--best_of", "7"])
                
                # Note: No --beam_size here to force sampling.
            else:
                # Standard Mode
                cmd.extend(["--temperature", "0"]) 
                cmd.extend(["--beam_size", "5"])
            
            # 3. HYPER-SENSITIVITY (Catching faint cuts)
            # 0.35: Very aggressive. Forces speech detection.
            cmd.extend(["--no_speech_threshold", "0.36"])
            
            # 4. HALLUCINATION GUARD (PERMISSIVE)
            # -6.0: Allows very faint/low-confidence words. 
            # Essential for turning "Inaudible" into text.
            cmd.extend(["--logprob_threshold", "-6.2"])
            
            # 5. LOOP BREAKER (NEAR MAX)
            # 16.5: Allows ~10-15 repetitions. 
            # High enough for "tak tak tak tak...", low enough to stop infinite loops.
            cmd.extend(["--compression_ratio_threshold", "14.5"])

            if force_cpu or device_mode == "CPU":
                cmd.extend(["--device", "cpu"])
            elif device_mode == "GPU (cuda/rocm)":
                cmd.extend(["--device", "cuda"])
            
            if lang and lang != "Auto": 
                cmd.extend(["--language", lang])
            
            if verbatim:
                cmd.extend(["--initial_prompt", full_prompt])
            
            # ISOLATION
            cmd.extend(["--condition_on_previous_text", "False"])
            
            return cmd

        cmd = build_cmd()
        log_info(f"Running Whisper v11.0: {' '.join(cmd)}")
        
        try:
            startup_info = self.os_doc.get_startup_info()
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, startupinfo=startup_info)
            
            err_msg = result.stderr.lower()
            gpu_failure_keywords = ["cuda", "driver", "gpu", "kernel", "torch", "segmentation fault", "code -11"]
            
            if result.returncode != 0 and device_mode != "CPU":
                if result.returncode == -11 or any(k in err_msg for k in gpu_failure_keywords):
                    log_error("Whisper GPU Error (Crash/Segfault). Switching to CPU...")
                    cmd_cpu = build_cmd(force_cpu=True)
                    result = subprocess.run(cmd_cpu, capture_output=True, text=True, env=env, startupinfo=startup_info)

            if result.returncode != 0:
                log_error(f"Whisper Error (Code {result.returncode}): {result.stderr}")
                return None
            
            json_file = os.path.join(output_dir, unique_name + ".json")
            return json_file if os.path.exists(json_file) else None

        except Exception as e:
            log_error(f"Exception in run_whisper: {e}")
            return None

    # ==========================================
    # 2. AUDIO PROCESSING (FFMPEG)
    # ==========================================

    def normalize_audio(self, input_path):
        """
        [ENHANCED] Applies "Radio Voice" processing + NOISE INJECTION.
        Injecting -85dB noise prevents Whisper from hallucinating in digital silence
        when using high sensitivity settings.
        """
        norm_path = input_path.replace(".wav", "_norm.wav")
        
        # 1. Highpass: Clean rumble
        # 2. Compressor: Boost quiet parts
        # 3. Loudnorm: Normalize
        filter_chain = (
            "highpass=f=80, "
            "acompressor=threshold=-25dB:ratio=4:attack=5:release=25, "
            "loudnorm=I=-14:LRA=7:tp=-1.0"
        )
        
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_path, "-af", filter_chain, 
               "-ar", "48000", "-ac", "1", norm_path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           check=True, startupinfo=self.os_doc.get_startup_info())
            return norm_path
        except:
            return input_path
    
    def create_slow_motion_audio(self, input_path, speed_factor):
        """
        [NEW] Creates a slowed-down version of the audio using FFmpeg.
        Target: 0.42x (The "Uneven" Precision).
        """
        base, ext = os.path.splitext(input_path)
        slow_path = f"{base}_slow{ext}"
        
        # 0.42 = 0.6 * 0.7
        filters = ["atempo=0.6", "atempo=0.7"]
        filter_chain = ",".join(filters)
        
        cmd = [
            self.ffmpeg_cmd, "-y", "-i", input_path,
            "-filter:a", filter_chain, 
            "-vn", # No video
            slow_path
        ]
        
        log_info(f"Generating Balanced Slow-Mo (Factor {speed_factor}, Chain: {filter_chain})...")
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           check=True, startupinfo=self.os_doc.get_startup_info())
            return slow_path
        except Exception as e:
            log_error(f"Slow Motion Generation Failed: {e}")
            return input_path 

    def detect_silence(self, audio_path, threshold_db, min_dur):
        # [TUNED] BACK TO -40dB.
        # Restoring standard threshold to prevent noise from being treated as "Inaudible".
        # Now, background noise will be correctly identified as "Silence" (Gray),
        # cleaning up the transcript view.
        cmd = [self.ffmpeg_cmd, "-i", audio_path, "-af", 
               f"silencedetect=noise={threshold_db}dB:d={min_dur}", "-f", "null", "-"]
        try:
            res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, 
                                 startupinfo=self.os_doc.get_startup_info())
            output = res.stderr
            starts = [float(x) for x in re.findall(r'silence_start: (\d+\.?\d*)', output)]
            ends = [float(x) for x in re.findall(r'silence_end: (\d+\.?\d*)', output)]
            
            ranges = []
            count = min(len(starts), len(ends))
            for i in range(count): 
                ranges.append({'s': starts[i], 'e': ends[i]})
            if len(starts) > len(ends): 
                ranges.append({'s': starts[-1], 'e': 999999.0})
                
            return ranges
        except Exception as e:
            log_error(f"Silence Detection Error: {e}")
            return []

    # ==========================================
    # 3. MAIN ANALYSIS PIPELINE
    # ==========================================

    def run_analysis_pipeline(self, settings, callback_status=None, callback_progress=None):
        def update_status(msg):
            if callback_status: callback_status(msg)
        def update_progress(val):
            if callback_progress: callback_progress(val)

        trans_status = settings.get("trans_status", {})
        def get_status_msg(key, fallback="..."):
            return trans_status.get(key, fallback)

        try:
            lang = settings.get('lang')
            model = settings.get('model', 'medium').split()[0]
            device_mode = settings.get('device', 'Auto')
            filler_words = settings.get('filler_words', [])
            fps = self.resolve_handler.fps
            txt_inaudible = trans_status.get("txt_inaudible", "inaudible")
            
            # --- EXPERIMENTAL: ODD NUMBERS TUNING v11.0 ---
            # 0.42x Speed (0.6 * 0.7)
            USE_SLOW_MODE = True 
            SLOW_FACTOR = 0.42 
            
            unique_id = f"BW_{int(time.time())}"
            update_progress(5)

            update_status(get_status_msg("render", "Rendering..."))
            temp_dir = self.os_doc.get_temp_folder()
            os.makedirs(temp_dir, exist_ok=True)
            
            wav_path = self.resolve_handler.render_audio(unique_id, temp_dir)
            if not wav_path:
                log_error("Render failed.")
                return None, None
            
            update_progress(20)

            # 1. SLOW DOWN
            current_wav_path = wav_path
            time_scale_correction = 1.0
            
            if USE_SLOW_MODE:
                update_status("Slowing audio (0.42x Tuned)...")
                slow_wav = self.create_slow_motion_audio(wav_path, SLOW_FACTOR)
                if slow_wav != wav_path:
                    current_wav_path = slow_wav
                    time_scale_correction = SLOW_FACTOR
            
            update_progress(30)

            # 2. NORMALIZE
            update_status("Enhancing audio (Radio Voice)...")
            normalized_wav = self.normalize_audio(current_wav_path)
            target_wav = normalized_wav

            update_status(get_status_msg("check_model", f"Checking {model}..."))
            def dl_progress_cb(val): pass
            self.download_whisper_model_interactive(model, dl_progress_cb)
            
            update_status(get_status_msg("whisper_run", f"Whisper {model}..."))
            
            # --- START INDETERMINATE PROGRESS ---
            # Whisper execution time is unpredictable and blocking.
            # Setting progress to -1 triggers the 'marquee' animation in GUI.
            update_progress(-1) 
            
            json_path = self.run_whisper(target_wav, model, lang, True, device_mode, filler_words)
            
            # --- STOP INDETERMINATE PROGRESS ---
            # Jump to a concrete value to stop animation.
            update_progress(55)
            
            if not json_path:
                log_error("Whisper failed.")
                return None, None
            
            update_progress(60)

            update_status(get_status_msg("silence", "Silence detection..."))
            # Tuned to -40dB (standard) to clean up Inaudible spam
            silence_ranges = self.detect_silence(target_wav, -42, 0.2)
            
            # Cleanup
            for p in [wav_path, current_wav_path, normalized_wav]:
                if p and os.path.exists(p) and p != wav_path:
                     try: os.remove(p)
                     except: pass
            try: os.remove(wav_path)
            except: pass

            update_progress(80)

            update_status(get_status_msg("processing", "Processing..."))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            words_data, segments_data = self._build_data_structure(
                data, silence_ranges, filler_words, fps, 
                txt_inaudible, time_scale_correction
            )

            update_progress(95)
            
            if words_data:
                update_status(get_status_msg("init_analysis", "Analyzing..."))
                words_data, _ = algorythms.analyze_repeats(words_data)
                words_data = algorythms.absorb_inaudible_into_repeats(words_data)

            update_progress(100)
            return words_data, segments_data

        except Exception as e:
            log_error(f"Pipeline Critical Error: {traceback.format_exc()}")
            return None, None

    def _build_data_structure(self, json_data, silence_ranges, filler_words, fps, 
                              txt_inaudible="inaudible", time_scale_correction=1.0):
        temp_words = []
        dynamic_bad = [w.lower().strip() for w in filler_words]
        
        def fix_t(t): return t * time_scale_correction
        
        for seg in json_data.get('segments', []):
            seg_start = fix_t(seg.get('start', 0))
            seg_end = fix_t(seg.get('end', 0))
            is_first = True
            
            for w in seg.get('words', []):
                clean = re.sub(r'[^\w\s\'-]', '', w['word'].strip())
                if clean:
                    is_bad = clean.lower() in dynamic_bad
                    real_start = fix_t(w['start'])
                    real_end = fix_t(w['end'])
                    
                    w_obj = {
                        "text": clean,
                        "start": real_start, "end": real_end,
                        "selected": is_bad,
                        "status": "bad" if is_bad else None,
                        "seg_start": seg_start, "seg_end": seg_end,
                        "is_segment_start": is_first,
                        "type": "word",
                        "id": 0
                    }
                    if is_first: is_first = False
                    temp_words.append(w_obj)

        scaled_silence = []
        if silence_ranges:
            for s in silence_ranges:
                scaled_silence.append({'s': fix_t(s['s']), 'e': fix_t(s['e'])})
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
                    if (gap_end - gap_start) >= 0.5:
                        final_words.append({
                            "start": gap_start, "end": gap_end,
                            "text": txt_inaudible,
                            "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                            "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False
                        })
                else:
                    for s in relevant:
                        valid_start = max(current_pos, s['s'])
                        valid_end = min(s['e'], gap_end)
                        
                        if valid_start - current_pos > 0.3:
                             final_words.append({
                                "start": current_pos, "end": valid_start,
                                "text": txt_inaudible,
                                "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                                "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False
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
                    
                    if gap_end - current_pos > 0.3:
                        final_words.append({
                            "start": current_pos, "end": gap_end,
                            "text": txt_inaudible,
                            "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                            "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False
                        })

                final_words.append(curr_w)

        for i, w in enumerate(final_words): w['id'] = i

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
        """
        Generates EDL using BLOCK-BASED approach.
        Uses Chunking + Boundary Snapping + Overlay.
        Special Logic: Merges silence and inaudible into BAD clips if in Mark mode.
        """
        ops = []
        if not words_data: return ops

        offset_s = settings.get('offset', -0.05)
        pad_s = settings.get('pad', 0.05)
        snap_max_s = settings.get('snap_max', 0.25)
        
        do_silence_cut = settings.get('silence_cut', False)
        do_silence_mark = settings.get('silence_mark', False)
        do_show_inaudible = settings.get('show_inaudible', True)
        do_auto_del = settings.get('auto_del', False)

        def t2f(t): return int(round(t * fps))
        
        offset_f = int(round(offset_s * fps))
        pad_f = int(round(pad_s * fps))
        snap_f = int(round(snap_max_s * fps))

        silence_blocks = [w for w in words_data if w.get('type') == 'silence']
        
        chunks = []
        current_chunk = None
        
        processed_words = []
        for w in words_data:
            if w.get('type') == 'silence': continue
            
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            
            if is_inaudible:
                current_status = w.get('status')
                if (not current_status or current_status == 'inaudible') and not do_show_inaudible:
                    continue
            
            processed_words.append(w)

        if not processed_words: return []

        for w in processed_words:
            status = w.get('status', 'normal')
            if status is None: status = 'normal'
            
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
                raw_cut = next_chunk_start
                cut_f = t2f(raw_cut) + offset_f - pad_f
                
                for s in silence_blocks:
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
                block_end_f = t2f(chunk_end_w) + offset_f + pad_f + 100 
            
            ops_raw.append({
                's': block_start_f,
                'e': block_end_f,
                'type': chunk['status']
            })
            
            current_time_f = block_end_f

        if do_silence_cut or do_silence_mark:
            final_ops = []
            
            s_ranges = []
            for s in silence_blocks:
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
            
        final_result = []
        for op in merged_ops:
            if do_auto_del and op['type'] == 'bad': continue
            
            if op['e'] - op['s'] < 2: continue 
            final_result.append(op)
            
        return final_result

    # ==========================================
    # 5. PROJECT & DATA MANAGEMENT (Data Controller)
    # ==========================================

    def save_project_state(self, file_path, data_packet):
        """
        Saves the project state to a JSON file.
        data_packet contains: settings, words_data, filler_words, script_content, lang_code
        """
        try:
            # Optimize floats
            optimized_words = []
            for w in data_packet.get("words_data", []):
                w_clean = w.copy()
                w_clean['start'] = round(w['start'], 3)
                w_clean['end'] = round(w['end'], 3)
                if 'seg_start' in w_clean: w_clean['seg_start'] = round(w['seg_start'], 3)
                if 'seg_end' in w_clean: w_clean['seg_end'] = round(w['seg_end'], 3)
                optimized_words.append(w_clean)

            project_state = {
                "version": config.VERSION,
                "timestamp": time.time(),
                "lang_code": data_packet.get("lang_code", "en"),
                "settings": data_packet.get("settings", {}),
                "filler_words": data_packet.get("filler_words", []),
                "words_data": optimized_words,
                "script_content": data_packet.get("script_content", "")
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_state, f, separators=(',', ':'))
            return True
        except Exception as e:
            log_error(f"Save Project Error: {e}")
            raise e

    def load_project_state(self, file_path):
        """
        Loads project state from JSON.
        Returns the raw project_state dict and reconstructed segments.
        GUI is responsible for parsing settings back to vars.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_state = json.load(f)
            
            words = project_state.get("words_data", [])
            segments = self._reconstruct_segments(words)
            
            return project_state, segments
        except Exception as e:
            log_error(f"Load Project Error: {e}")
            raise e

    def _reconstruct_segments(self, words_data):
        segments = []
        current_seg = []
        for w in words_data:
            if w.get('is_segment_start') and current_seg:
                segments.append(current_seg)
                current_seg = []
            current_seg.append(w)
        if current_seg: segments.append(current_seg)
        return segments

    # ==========================================
    # 6. WRAPPERS (Logic Orchestration)
    # ==========================================

    def run_standalone_analysis(self, words_data, show_inaudible=True):
        """
        Wraps algorithms for standalone analysis.
        Decouples GUI from Algorithm implementation.
        """
        processed_words, count = algorythms.analyze_repeats(words_data, show_inaudible=show_inaudible)
        processed_words = algorythms.absorb_inaudible_into_repeats(processed_words)
        return processed_words, count

    def run_comparison_analysis(self, script_text, words_data):
        """
        Wraps algorithms for comparison analysis.
        """
        result_words = algorythms.compare_script_to_transcript(script_text, words_data)
        final_words = algorythms.absorb_inaudible_into_repeats(result_words)
        # Returns AnalysisResult which behaves like list but has .missing_indices
        return final_words

    # ==========================================
    # 7. ASSEMBLY ORCHESTRATION (THE COMPOUND FIX)
    # ==========================================

    def start_timeline_generation(self, words_data, settings, callbacks):
        """
        THREADED ENTRY POINT FOR ASSEMBLY.
        Allows GUI to just call this and forget.
        """
        import threading
        
        def runner():
            # Now returns tuple: (success, warning_code)
            result = self.assemble_timeline(
                words_data,
                settings,
                callback_status=callbacks.get('on_status'),
                callback_progress=callbacks.get('on_progress')
            )
            
            # Handle both old (bool) and new (tuple) return types for safety
            if isinstance(result, tuple):
                success, warning = result
            else:
                success, warning = result, None
            
            if success:
                if callbacks.get('on_success'):
                    # Safe call if on_success doesn't accept args
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
        The Master Function for creating the edited timeline.
        Handles the "Compound Clip Fix" logic internally.
        
        Args:
            words_data: The transcript data.
            settings: Dictionary of user settings from GUI.
            callback_status: Function to update status text.
            callback_progress: Function to update progress bar.
        
        Returns:
            (bool, warning_code) - Success status and optional warning code (e.g. 'unsynced')
        """
        unique_wrapper_id = None
        source_item = None
        warning_code = None
        
        # Safe callback wrappers
        def set_status(msg): 
            if callback_status: callback_status(msg)
            else: log_info(msg)
            
        def set_progress(val):
            if callback_progress: callback_progress(val)

        try:
            set_status("Initializing Assembly...")
            set_progress(10)
            
            # 1. Refresh Context
            self.resolve_handler.refresh_context()
            if not self.resolve_handler.timeline:
                log_error("No active timeline found.")
                return False, None
                
            original_tl_name = self.resolve_handler.timeline.GetName()
            
            # DETECT SOURCE TYPE & INTENT (NEW)
            _, context_type = self.resolve_handler.get_timeline_source_info()
            audio_only_mode = (context_type == 'audio')
            
            # DETECT UNSYNCED MEDIA (NEW INTELLIGENT FIX)
            is_unsynced = False
            if not audio_only_mode:
                is_unsynced = self.resolve_handler.detect_unsynced_video_items()
            
            # Determine if we should force compound mode
            user_wants_compound = settings.get("compound", False)
            should_use_compound = user_wants_compound or is_unsynced
            
            if is_unsynced and not user_wants_compound:
                log_info("Unsynced media detected. Forcing Compound Clip mode.")
                warning_code = "unsynced_warning"

            # 2. HANDLE SOURCE & COMPOUND LOGIC
            if should_use_compound:
                # Generate 6-digit ID: XXX-XXX
                part1 = random.randint(100, 999)
                part2 = random.randint(100, 999)
                unique_wrapper_id = f"{part1}-{part2}"
                
                set_status(f"Creating Wrapper {unique_wrapper_id}...")
                
                # API Call to create wrapper
                # Expects api.py to return (wrapper_tl, source_item)
                # where source_item is the item INSIDE the wrapper (the original timeline item)
                wrapper_tl, nested_source_item = self.resolve_handler.create_temporary_wrapper(original_tl_name, unique_wrapper_id)
                
                if not wrapper_tl or not nested_source_item:
                    log_error("Failed to create temporary wrapper timeline.")
                    return False, None
                
                # We use the nested source item (Original Timeline Item) to build the new timeline.
                # Because it's a Timeline Item, appending it nests the original timeline.
                source_item = nested_source_item
            else:
                # Standard Mode
                # Re-fetch item to be sure (though get_timeline_source_info already found it)
                found_item, found_type = self.resolve_handler.get_timeline_source_info()
                source_item = found_item
                
                if not source_item:
                    log_error("Could not find source clip (V1 or A1).")
                    return False, None
            
            set_progress(30)
            
            # 3. CALCULATE CUTS
            set_status("Calculating Cuts...")
            fps = self.resolve_handler.fps
            clean_ops = self.calculate_timeline_structure(words_data, fps, settings)
            
            set_progress(50)
            
            # 4. GENERATE TIMELINE
            set_status("Assembling in Resolve...")
            
            # Naming Logic: Always use original name, regardless of wrapper
            clean_name, next_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
            new_tl_name = f"{clean_name} BadWords Edit {next_idx}"
            
            success = self.resolve_handler.generate_timeline_from_ops(
                clean_ops, 
                source_item, 
                new_tl_name,
                audio_only_mode=audio_only_mode # Pass the flag
            )
            
            if not success:
                log_error("Failed to generate timeline via API.")
                return False, None
                
            set_progress(90)
            
            # 5. CLEANUP WRAPPER (If used)
            if unique_wrapper_id:
                set_status("Cleaning up wrapper...")
                self.resolve_handler.cleanup_wrapper(unique_wrapper_id)
                
            set_progress(100)
            return True, warning_code
            
        except Exception as e:
            log_error(f"Assembly Critical Error: {e}")
            traceback.print_exc()
            # Emergency cleanup attempt
            if unique_wrapper_id:
                try: self.resolve_handler.cleanup_wrapper(unique_wrapper_id)
                except: pass
            return False, None