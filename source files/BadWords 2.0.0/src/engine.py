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
FIXED v9.1: 
- Tuned Whisper parameters (VAD off, Temp strategy) for better accuracy.
- Suppressed HuggingFace token warnings.
- Robust Fallback strategy retained.
- Added HF_HUB_DISABLE_SYMLINKS_WARNING to suppress Windows symlink noise.
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
import random

import config
import algorythms
from osdoc import log_info, log_error

class AudioEngine:
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

    # ==========================================
    # 1. EXTERNAL PROCESS MANAGEMENT (FASTER-WHISPER)
    # ==========================================

    def _get_python_executable(self):
        """
        Returns the VENV python executable on Linux to ensure valid environment.
        On Windows, falls back to system/embedded python.
        """
        return self.os_doc.get_venv_python_path()

    def download_whisper_model_interactive(self, model_name, progress_callback=None):
        """
        Downloads the Faster-Whisper model via a subprocess script to handle I/O.
        Explicitly forces download to local 'models' folder.
        """
        log_info(f"Starting interactive download for Faster-Whisper model: {model_name}")
        
        if model_name == "large": model_name = "large-v3"
        
        script_content = f"""
import sys
import os

# SUPPRESS HF WARNINGS
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Fix for Windows Non-Admin/Non-DevMode

# FORCE CACHE DIR (Inside python script)
os.environ["HF_HOME"] = r"{self.models_dir}"
os.environ["XDG_CACHE_HOME"] = r"{self.models_dir}"

libs_dir = r"{self.libs_dir}"
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    print(f"DL-START: Target dir {self.models_dir}")
    from faster_whisper import download_model
    print(f"Downloading {model_name}...")
    download_model("{model_name}")
    print("Download Complete.")
except Exception as e:
    print(f"Error: {{e}}")
    sys.exit(1)
"""
        runner_path = os.path.join(self.os_doc.get_temp_folder(), "fw_downloader.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        python_exec = self._get_python_executable()
        cmd = [python_exec, runner_path]
        startup_info = self.os_doc.get_startup_info()
        env = os.environ.copy()
        env["HF_HOME"] = self.models_dir
        
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startup_info, env=env
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None: break
                if line: log_info(f"[FW-DL] {line.strip()}")
            
            if process.returncode == 0:
                log_info(f"Model {model_name} ready.")
                if progress_callback: progress_callback(100)
                return True
            else:
                err = process.stderr.read()
                log_error(f"Model download failed (STDERR): {err}")
                return False
        except Exception as e:
            log_error(f"Download execution failed: {e}")
            return False
        finally:
            if os.path.exists(runner_path): os.remove(runner_path)

    def check_model_exists(self, tech_name):
        return True

    def run_whisper(self, audio_path, model, lang, verbatim, device_mode, filler_words_list=None):
        """
        Runs Faster-Whisper with NVIDIA LIBRARY INJECTION.
        Uses float32 for GPU and int8 for CPU.
        """
        unique_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = self.os_doc.get_temp_folder()
        json_output_path = os.path.join(output_dir, unique_name + ".json")
        runner_script_path = os.path.join(output_dir, f"fw_runner_{unique_name}.py")

        if model == "large": model = "large-v3"
        
        # Device Logic (Resolved from Auto in pipeline)
        fw_device = "cuda" if "GPU" in device_mode else "cpu"
        
        # Compute Logic: Float32 for CUDA (compat), Int8 for CPU (speed)
        fw_compute = "float32" if fw_device == "cuda" else "int8"
        
        initial_prompt_str = ""
        if verbatim:
            base_prompt = "Umm, uh, yyy. Transcribe exactly. Repetitions: 'Tak tak tak', 'Yes yes yes'."
            initial_prompt_str = base_prompt
            if filler_words_list:
                initial_prompt_str += f" {', '.join(filler_words_list)}"
        
        safe_audio_path = audio_path.replace("\\", "\\\\")
        safe_json_path = json_output_path.replace("\\", "\\\\")
        safe_prompt = initial_prompt_str.replace("\"", "'")
        safe_models_dir = self.models_dir.replace("\\", "\\\\")

        # --- PREPARE ENVIRONMENT & INJECT NVIDIA LIBS ---
        env = os.environ.copy()
        env["HF_HOME"] = self.models_dir
        
        # Scan for nvidia libs in our local libs folder and add to LD_LIBRARY_PATH
        if self.os_doc.is_linux and fw_device == "cuda":
            nvidia_libs_paths = []
            nvidia_base = os.path.join(self.libs_dir, "nvidia")
            
            if os.path.exists(nvidia_base):
                log_info(f"Scanning for NVIDIA libs in: {nvidia_base}")
                for root, dirs, files in os.walk(nvidia_base):
                    if 'lib' in dirs:
                        lib_path = os.path.abspath(os.path.join(root, 'lib'))
                        if lib_path not in nvidia_libs_paths:
                            nvidia_libs_paths.append(lib_path)
            
            if nvidia_libs_paths:
                current_ld = env.get("LD_LIBRARY_PATH", "")
                new_ld_paths = ":".join(nvidia_libs_paths)
                env["LD_LIBRARY_PATH"] = f"{new_ld_paths}:{current_ld}"
                log_info(f"Injected LD_LIBRARY_PATH with: {new_ld_paths}")
            else:
                log_info("WARNING: No local NVIDIA libs found in venv. Relying on system libs.")

        # --- GENERATE RUNNER SCRIPT ---
        script_content = f"""
import sys
import os
import json
import time

# SUPPRESS HF WARNINGS
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Fix for Windows Non-Admin/Non-DevMode

# FORCE CACHE DIR
os.environ["HF_HOME"] = r"{safe_models_dir}"

libs_dir = r"{self.libs_dir}"
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    from faster_whisper import WhisperModel
    
    model_size = "{model}"
    target_device = "{fw_device}"
    target_compute = "{fw_compute}"
    
    print(f"Loading Model {{model_size}} on {{target_device}} ({{target_compute}})...")
    
    model = None
    
    def try_load(dev, comp):
        print(f"Attempting to load on {{dev}} ({{comp}})...")
        return WhisperModel(model_size, device=dev, compute_type=comp, download_root=r"{safe_models_dir}")

    # === ROBUST FALLBACK LOGIC ===
    try:
        # ATTEMPT 1: Target settings (CUDA float32 or CPU int8)
        model = try_load(target_device, target_compute)
        
    except Exception as e_pref:
        err_str = str(e_pref).lower()
        print(f"WARNING: Primary load failed: {{e_pref}}")
        
        # If we failed on CUDA, switch to CPU int8
        if target_device == "cuda":
             print("CRITICAL: CUDA acceleration failed. Switching to CPU (int8)...")
             try:
                 model = try_load("cpu", "int8")
             except Exception as e_cpu:
                 print(f"FW_ERROR: CPU Fallback also failed. System incompatible. Details: {{e_cpu}}")
                 sys.exit(1)
        else:
             print(f"FW_ERROR: CPU execution failed. Details: {{e_pref}}")
             sys.exit(1)

    print("Model Loaded Successfully. Starting Transcription...")
    
    segments, info = model.transcribe(
        r"{safe_audio_path}", 
        beam_size=5, 
        language="{lang}" if "{lang}" != "Auto" else None,
        word_timestamps=True,
        initial_prompt="{safe_prompt}",
        condition_on_previous_text=False,
        vad_filter=False,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        no_speech_threshold=0.36,
        log_prob_threshold=-6.2,
        compression_ratio_threshold=14.5
    )
    
    output_segments = []
    
    for segment in segments:
        seg_obj = {{
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": []
        }}
        
        if segment.words:
            for w in segment.words:
                seg_obj["words"].append({{
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability
                }})
        
        output_segments.append(seg_obj)
        print(f"Segment: {{segment.start:.2f}}s")

    final_data = {{
        "segments": output_segments,
        "language": info.language
    }}
    
    with open(r"{safe_json_path}", "w", encoding="utf-8") as f:
        json.dump(final_data, f)
        
    print("Transcription Done.")

except Exception as e:
    print(f"FW_ERROR: {{e}}")
    sys.exit(1)
"""
        with open(runner_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        python_exec = self._get_python_executable()
        cmd = [python_exec, runner_script_path]
        startup_info = self.os_doc.get_startup_info()
        
        log_info(f"Running Whisper Runner. Script: {runner_script_path}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env, 
                startupinfo=startup_info
            )
            
            if result.stdout: log_info(f"[RUNNER-OUT] {result.stdout[:500]} ...")
            if result.stderr: log_error(f"[RUNNER-ERR] {result.stderr}")

            if result.returncode != 0:
                log_error(f"Subprocess Failed. Return Code: {result.returncode}")
                return None
                
            if os.path.exists(json_output_path):
                return json_output_path
            else:
                log_error("JSON output missing after execution.")
                return None
                
        except Exception as e:
            log_error(f"Exception in run_whisper: {e}")
            return None
        finally:
            if os.path.exists(runner_script_path):
                try: os.remove(runner_script_path)
                except: pass

    # ==========================================
    # 2. AUDIO PROCESSING (FFMPEG)
    # ==========================================

    def normalize_audio(self, input_path):
        """
        [ENHANCED] Applies "Radio Voice" processing + NOISE INJECTION.
        """
        norm_path = input_path.replace(".wav", "_norm.wav")
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
        base, ext = os.path.splitext(input_path)
        slow_path = f"{base}_slow{ext}"
        filters = ["atempo=0.6", "atempo=0.7"]
        filter_chain = ",".join(filters)
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_path, "-filter:a", filter_chain, "-vn", slow_path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           check=True, startupinfo=self.os_doc.get_startup_info())
            return slow_path
        except Exception as e:
            log_error(f"Slow Motion Generation Failed: {e}")
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
            for i in range(count): ranges.append({'s': starts[i], 'e': ends[i]})
            if len(starts) > len(ends): ranges.append({'s': starts[-1], 'e': 999999.0})
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
            
            # --- AUTO DEVICE LOGIC ---
            raw_device = settings.get('device', 'Auto')
            
            if raw_device == "Auto":
                # Check for physical existence of NVIDIA libs in venv
                if self.os_doc.has_nvidia_support():
                    device_mode = "GPU" # Will map to cuda/float32
                    log_info("Auto Mode: Detected NVIDIA libs. Using GPU (float32).")
                else:
                    device_mode = "CPU" # Will map to cpu/int8
                    log_info("Auto Mode: No NVIDIA libs found. Using CPU (int8).")
            else:
                device_mode = raw_device

            filler_words = settings.get('filler_words', [])
            fps = self.resolve_handler.fps
            txt_inaudible = trans_status.get("txt_inaudible", "inaudible")
            
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
            
            # Check/Download logic for Faster-Whisper
            if self.os_doc.needs_manual_model_install():
                self.download_whisper_model_interactive(model, dl_progress_cb)
            
            # Changed: Update status right before execution
            update_status(get_status_msg("whisper_run", f"Faster-Whisper {model}..."))
            
            update_progress(-1) 
            
            # Execute Faster-Whisper via Runner with RESOLVED device mode
            json_path = self.run_whisper(target_wav, model, lang, True, device_mode, filler_words)
            
            update_progress(55)
            
            if not json_path:
                log_error("Whisper failed.")
                return None, None
            
            update_progress(60)

            update_status(get_status_msg("silence", "Silence detection..."))
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
        processed_words, count = algorythms.analyze_repeats(words_data, show_inaudible=show_inaudible)
        processed_words = algorythms.absorb_inaudible_into_repeats(processed_words)
        return processed_words, count

    def run_comparison_analysis(self, script_text, words_data):
        result_words = algorythms.compare_script_to_transcript(script_text, words_data)
        final_words = algorythms.absorb_inaudible_into_repeats(result_words)
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
        unique_wrapper_id = None
        source_item = None
        warning_code = None
        
        def set_status(msg): 
            if callback_status: callback_status(msg)
            else: log_info(msg)
            
        def set_progress(val):
            if callback_progress: callback_progress(val)

        try:
            set_status("Initializing Assembly...")
            set_progress(10)
            
            self.resolve_handler.refresh_context()
            if not self.resolve_handler.timeline:
                log_error("No active timeline found.")
                return False, None
                
            original_tl_name = self.resolve_handler.timeline.GetName()
            
            _, context_type = self.resolve_handler.get_timeline_source_info()
            audio_only_mode = (context_type == 'audio')
            
            is_unsynced = False
            if not audio_only_mode:
                is_unsynced = self.resolve_handler.detect_unsynced_video_items()
            
            user_wants_compound = settings.get("compound", False)
            should_use_compound = user_wants_compound or is_unsynced
            
            if is_unsynced and not user_wants_compound:
                log_info("Unsynced media detected. Forcing Compound Clip mode.")
                warning_code = "unsynced_warning"

            if should_use_compound:
                part1 = random.randint(100, 999)
                part2 = random.randint(100, 999)
                unique_wrapper_id = f"{part1}-{part2}"
                
                set_status(f"Creating Wrapper {unique_wrapper_id}...")
                
                wrapper_tl, nested_source_item = self.resolve_handler.create_temporary_wrapper(original_tl_name, unique_wrapper_id)
                
                if not wrapper_tl or not nested_source_item:
                    log_error("Failed to create temporary wrapper timeline.")
                    return False, None
                
                source_item = nested_source_item
            else:
                found_item, found_type = self.resolve_handler.get_timeline_source_info()
                source_item = found_item
                
                if not source_item:
                    log_error("Could not find source clip (V1 or A1).")
                    return False, None
            
            set_progress(30)
            
            set_status("Calculating Cuts...")
            fps = self.resolve_handler.fps
            clean_ops = self.calculate_timeline_structure(words_data, fps, settings)
            
            set_progress(50)
            
            set_status("Assembling in Resolve...")
            
            clean_name, next_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
            new_tl_name = f"{clean_name} BadWords Edit {next_idx}"
            
            success = self.resolve_handler.generate_timeline_from_ops(
                clean_ops, 
                source_item, 
                new_tl_name,
                audio_only_mode=audio_only_mode
            )
            
            if not success:
                log_error("Failed to generate timeline via API.")
                return False, None
                
            set_progress(90)
            
            if unique_wrapper_id:
                set_status("Cleaning up wrapper...")
                self.resolve_handler.cleanup_wrapper(unique_wrapper_id)
                
            set_progress(100)
            return True, warning_code
            
        except Exception as e:
            log_error(f"Assembly Critical Error: {e}")
            traceback.print_exc()
            if unique_wrapper_id:
                try: self.resolve_handler.cleanup_wrapper(unique_wrapper_id)
                except: pass
            return False, None