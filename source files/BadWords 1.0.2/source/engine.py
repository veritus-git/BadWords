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
                 scripts_path = sysconfig.get_path("scripts")
                 possible_paths.append(os.path.join(scripts_path, "whisper.exe"))
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

        # NOTE: LD_LIBRARY_PATH injection removed to prevent Segfaults on Linux AMD.
        # We rely on system/pipx paths and HSA_OVERRIDE from wrapper.

        def build_cmd(force_cpu=False):
            # CHANGED: Enable FP16 (True). 
            # Critical for AMD Radeon stability (prevents OOM/Hang/Crash).
            use_fp16 = "True" 
            
            # --- VERBATIM PROMPT ENGINEERING (MULTILINGUAL MEGA-PROMPT) ---
            # We construct a chaotic prompt to force Whisper into "verbatim mode".
            # This prompt mixes English, Polish, German and generic sounds to prime 
            # the model for capturing disfluencies in ANY language.
            # Designed to be around 140-160 tokens to leave safe buffer for user fillers.
            # This is NOT shown to the user in GUI.
            base_verbatim_prompt = (
                "Umm, uh, let me think... yyy, to znaczy, wiesz... like, hmm... okay. "
                "Ähm, also, so to speak. Yyy, eee, aaa, mhm, uh-huh. "
                "I mean, wait, no. Strictly verbatim, 1:1. Nie usuwaj, don't delete. "
                "Powtórzenia, repeats, uh... okay, so, basically... yyy... word for word. "
                "Err, erm, well, actually. No, w sumie, jakby. Czekaj, wait. "
                "Em, eh, este... alors, euh... donc. Yeah, exactly, like, kind of. "
                "I think so? Yyy, mhm. Transcribe everything, wszystkie słowa, alle Wörter. "
                "Don't clean up, bez czyszczenia. Uh, umm, err... just keep it raw, surowy tekst."
            )
            
            # Append user filler words to the technical prompt if they exist
            full_prompt = base_verbatim_prompt
            if verbatim and filler_words_list:
                user_fillers = ", ".join(filler_words_list)
                if user_fillers.strip():
                    full_prompt += f" {user_fillers}"

            cmd = [whisper_exec, audio_path, "--model", model, "--output_format", "json", 
                   "--output_dir", output_dir, "--word_timestamps", "True", "--fp16", use_fp16]
            
            # --- ACCURACY PARAMETERS ---
            # Force deterministic behavior and deeper search to catch every mutter
            cmd.extend(["--temperature", "0"])  # Deterministic output
            cmd.extend(["--beam_size", "5"])    # Deeper search for better accuracy
            
            if force_cpu or device_mode == "CPU":
                cmd.extend(["--device", "cpu"])
            elif device_mode == "GPU (cuda/rocm)":
                cmd.extend(["--device", "cuda"])
            
            if lang and lang != "Auto": 
                cmd.extend(["--language", lang])
            
            # Always inject the mega prompt if verbatim is requested (which is always True in pipeline)
            if verbatim:
                cmd.extend(["--initial_prompt", full_prompt])
            
            # Disable previous text conditioning to prevent hallucination loops in silence
            cmd.extend(["--condition_on_previous_text", "False"])
            
            return cmd

        cmd = build_cmd()
        log_info(f"Running Whisper: {' '.join(cmd)}")
        
        try:
            startup_info = self.os_doc.get_startup_info()
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, startupinfo=startup_info)
            
            err_msg = result.stderr.lower()
            gpu_failure_keywords = ["cuda", "driver", "gpu", "kernel", "torch", "segmentation fault", "code -11"]
            
            # Check for GPU failure and fallback
            if result.returncode != 0 and device_mode != "CPU":
                # If specifically a Segfault (-11) or GPU keywords found
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
        norm_path = input_path.replace(".wav", "_norm.wav")
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_path, "-af", "loudnorm=I=-23:LRA=7:tp=-2.0", 
               "-ar", "48000", "-ac", "1", norm_path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           check=True, startupinfo=self.os_doc.get_startup_info())
            return norm_path
        except:
            return input_path

    def detect_silence(self, audio_path, threshold_db, min_dur):
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
            is_compound = settings.get('compound', False)
            fps = self.resolve_handler.fps
            txt_inaudible = trans_status.get("txt_inaudible", "inaudible")

            if is_compound:
                update_status(get_status_msg("nesting", "Nesting..."))
                current_tl_name = self.resolve_handler.timeline.GetName()
                new_tl, source_item = self.resolve_handler.create_compound_clip_wrapper(current_tl_name)
                if not new_tl:
                    log_error("Failed to create compound wrapper.")
                    return None, None
            
            unique_id = f"BW_{int(time.time())}"
            update_progress(5)

            update_status(get_status_msg("render", "Rendering..."))
            temp_dir = self.os_doc.get_temp_folder()
            
            # Ensure temp dir exists before rendering
            os.makedirs(temp_dir, exist_ok=True)
            
            wav_path = self.resolve_handler.render_audio(unique_id, temp_dir)
            if not wav_path:
                log_error("Render failed.")
                return None, None
            
            update_progress(30)

            update_status(get_status_msg("check_model", f"Checking {model}..."))
            def dl_progress_cb(val): pass
            self.download_whisper_model_interactive(model, dl_progress_cb)
            
            update_status(get_status_msg("whisper_run", f"Whisper {model}..."))
            json_path = self.run_whisper(wav_path, model, lang, True, device_mode, filler_words)
            if not json_path:
                log_error("Whisper failed.")
                return None, None
            
            update_progress(60)

            update_status(get_status_msg("silence", "Silence detection..."))
            norm_wav = self.normalize_audio(wav_path)
            silence_ranges = self.detect_silence(norm_wav, -45, 0.3)
            if norm_wav != wav_path:
                try: os.remove(norm_wav)
                except: pass
            
            update_progress(80)

            update_status(get_status_msg("processing", "Processing..."))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            words_data, segments_data = self._build_data_structure(data, silence_ranges, filler_words, fps, txt_inaudible)

            try: os.remove(wav_path)
            except: pass

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

    def _build_data_structure(self, json_data, silence_ranges, filler_words, fps, txt_inaudible="inaudible"):
        temp_words = []
        dynamic_bad = [w.lower().strip() for w in filler_words]
        
        for seg in json_data.get('segments', []):
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)
            is_first = True
            
            for w in seg.get('words', []):
                clean = re.sub(r'[^\w\s\'-]', '', w['word'].strip())
                if clean:
                    is_bad = clean.lower() in dynamic_bad
                    w_obj = {
                        "text": clean,
                        "start": w['start'], "end": w['end'],
                        "selected": is_bad,
                        "status": "bad" if is_bad else None,
                        "seg_start": seg_start, "seg_end": seg_end,
                        "is_segment_start": is_first,
                        "type": "word",
                        "id": 0
                    }
                    if is_first: is_first = False
                    temp_words.append(w_obj)

        final_words = []
        
        if silence_ranges and temp_words and silence_ranges[0]['e'] < temp_words[0]['start']:
             s_start = silence_ranges[0]['s']
             s_end = silence_ranges[0]['e']
             # Only add initial silence if significant
             if s_end - s_start > 0.1:
                 final_words.append({
                     "start": s_start, "end": s_end, "text": "[SILENCE]",
                     "type": "silence", "status": "silence", "selected": False,
                     "seg_start": 0, "seg_end": 0, "is_segment_start": False
                 })

        if temp_words:
            final_words.append(temp_words[0])
            margin_sec = 0.1 # Reduced margin for precision
            
            for i in range(1, len(temp_words)):
                prev_w = temp_words[i-1]
                curr_w = temp_words[i]
                
                gap_start = prev_w['end']
                gap_end = curr_w['start']
                current_pos = gap_start
                
                # Check for silence in gap
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
                        # Only insert silence if it's substantial
                        valid_start = max(current_pos, s['s'])
                        valid_end = min(s['e'], gap_end)
                        
                        # Gap before silence? -> Inaudible
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

        # Settings
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

        # Separate Silence for Overlay
        silence_blocks = [w for w in words_data if w.get('type') == 'silence']
        
        # --- PHASE 1: CHUNKING (Group words into continuous blocks) ---
        chunks = []
        current_chunk = None
        
        processed_words = []
        for w in words_data:
            if w.get('type') == 'silence': continue
            
            # --- INAUDIBLE HANDLING START ---
            # If word is inaudible, check its status.
            # If user marked it manually (e.g. as bad, repeat), 'status' will be set.
            # If untouched, 'status' might be 'inaudible'.
            
            # If not showing inaudible, we skip it UNLESS user manually marked it
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            
            if is_inaudible:
                # If manually colored (status is bad/repeat/typo), we keep it regardless of 'show_inaudible'
                # If default status (inaudible) and 'show_inaudible' is False -> Skip
                current_status = w.get('status')
                if (not current_status or current_status == 'inaudible') and not do_show_inaudible:
                    continue
            # --- INAUDIBLE HANDLING END ---
            
            processed_words.append(w)

        if not processed_words: return []

        for w in processed_words:
            # Determine status for Chunking
            status = w.get('status', 'normal')
            if status is None: status = 'normal'
            
            # Note: If it's inaudible but user didn't change color, status is 'inaudible' -> Chocolate
            # If user changed it to 'bad', status is 'bad' -> Red
            
            # Start new chunk if status changes or no chunk exists
            if current_chunk is None:
                current_chunk = {'status': status, 'words': [w]}
            else:
                if current_chunk['status'] == status:
                    current_chunk['words'].append(w)
                else:
                    chunks.append(current_chunk)
                    current_chunk = {'status': status, 'words': [w]}
        
        if current_chunk: chunks.append(current_chunk)

        # --- PHASE 2: CALCULATE BOUNDARIES (The MPF Logic) ---
        # Instead of cutting every word, we cut only between chunks
        
        ops_raw = []
        current_time_f = 0
        
        for i, chunk in enumerate(chunks):
            chunk_end_w = chunk['words'][-1]['end']
            block_start_f = current_time_f
            
            if i < len(chunks) - 1:
                next_chunk_start = chunks[i+1]['words'][0]['start']
                raw_cut = next_chunk_start
                cut_f = t2f(raw_cut) + offset_f - pad_f
                
                # Snap to Silence Logic
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

        # --- PHASE 3: OVERLAY SILENCE (The Punch) ---
        if do_silence_cut or do_silence_mark:
            final_ops = []
            
            s_ranges = []
            for s in silence_blocks:
                if (s['end'] - s['start']) < 0.2: continue 
                s_ranges.append((t2f(s['start']), t2f(s['end'])))
            
            ops_raw.sort(key=lambda x: x['s'])
            
            for op in ops_raw:
                # SPECIAL MERGE LOGIC (Updated):
                # If op is BAD (Red) and we are only MARKING silence, skip this op (don't punch holes)
                # This keeps the BAD clip continuous, covering the silence.
                # Also applies if op is INAUDIBLE (Chocolate) and we mark silence.
                if (op['type'] == 'bad' or op['type'] == 'inaudible') and do_silence_mark and not do_silence_cut:
                    final_ops.append(op)
                    continue

                sub_segments = [op]
                
                for s_s, s_e in s_ranges:
                    new_sub = []
                    for sub in sub_segments:
                        # Case 1: Silence is outside
                        if s_e <= sub['s'] or s_s >= sub['e']:
                            new_sub.append(sub)
                        # Case 2: Silence covers completely
                        elif s_s <= sub['s'] and s_e >= sub['e']:
                            if do_silence_mark:
                                new_sub.append({'s': sub['s'], 'e': sub['e'], 'type': 'silence_mark'})
                        # Case 3: Overlap
                        else:
                            # Part before silence
                            if s_s > sub['s']:
                                new_sub.append({'s': sub['s'], 'e': s_s, 'type': sub['type']})
                            
                            # The silence part
                            if do_silence_mark:
                                overlap_s = max(sub['s'], s_s)
                                overlap_e = min(sub['e'], s_e)
                                new_sub.append({'s': overlap_s, 'e': overlap_e, 'type': 'silence_mark'})
                            
                            # Part after silence
                            if s_e < sub['e']:
                                new_sub.append({'s': s_e, 'e': sub['e'], 'type': sub['type']})
                                
                    sub_segments = new_sub
                
                final_ops.extend(sub_segments)
            
            ops_raw = final_ops

        # --- PHASE 4: FILTERING & CLEANUP ---
        # Sort and merge same adjacent types (to fix fragmentation from silence processing)
        ops_raw.sort(key=lambda x: x['s'])
        
        merged_ops = []
        if ops_raw:
            curr = ops_raw[0]
            for next_op in ops_raw[1:]:
                # Merge if same type and touching/overlapping
                if next_op['type'] == curr['type'] and next_op['s'] <= curr['e'] + 1:
                    curr['e'] = max(curr['e'], next_op['e'])
                else:
                    merged_ops.append(curr)
                    curr = next_op
            merged_ops.append(curr)
            
        final_result = []
        for op in merged_ops:
            # Auto-Delete Logic
            # Delete BAD clips?
            if do_auto_del and op['type'] == 'bad': continue
            # Delete Inaudible clips? Usually user wants to see them if they enabled 'Show Inaudible'
            # But if they manually marked it 'bad', it's handled above.
            # If it's still 'inaudible' type, we keep it (chocolate).
            
            if op['e'] - op['s'] < 2: continue 
            final_result.append(op)
            
        return final_result