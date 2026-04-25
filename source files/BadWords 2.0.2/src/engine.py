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
    # PREFERENCES MANAGEMENT
    # ==========================================

    def save_preferences(self, settings_dict):
        """
        Saves the configuration window settings to a JSON file.
        Uses os_doc.pref_file defined in OSDoctor.
        """
        try:
            pref_path = getattr(self.os_doc, 'pref_file', os.path.join(self.os_doc.install_dir, "pref.json"))
            
            # 1. Odczytaj istniejące dane (aby nie nadpisać np. telemetrii)
            existing_prefs = {}
            if os.path.exists(pref_path):
                try:
                    with open(pref_path, 'r', encoding='utf-8') as f:
                        existing_prefs = json.load(f)
                except Exception:
                    pass
            
            # 2. Zaktualizuj tylko przekazane klucze
            existing_prefs.update(settings_dict)

            # 3. Zapisz połączony słownik
            with open(pref_path, 'w', encoding='utf-8') as f:
                json.dump(existing_prefs, f, indent=4)
                
            log_info(f"Preferences saved to: {pref_path}")
            return True
        except Exception as e:
            log_error(f"Failed to save preferences: {e}")
            return False

    def load_preferences(self):
        """
        Loads settings from the JSON preference file.
        Returns a dict or None if missing/corrupt.
        """
        try:
            pref_path = getattr(self.os_doc, 'pref_file', os.path.join(self.os_doc.install_dir, "pref.json"))
            if not os.path.exists(pref_path):
                return None
            with open(pref_path, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
            log_info(f"Preferences loaded from: {pref_path}")
            return prefs
        except Exception as e:
            log_error(f"Failed to load preferences: {e}")
            return None

    # ==========================================
    # TELEMETRY (POSTHOG)
    # ==========================================

    def send_telemetry_ping(self, event_name="app_started"):
        """
        Asynchroniczne wysyłanie pingu telemetrycznego do PostHog.
        Wysyła tylko za zgodą użytkownika i tylko raz na daną wersję.
        """
        def _ping_thread():
            try:
                opt_in = self.os_doc.get_telemetry_pref("telemetry_opt_in")
                if not opt_in:
                    return # Brak zgody lub brak decyzji
                
                last_ping = self.os_doc.get_telemetry_pref("last_pinged_version")
                current_version = config.VERSION
                
                if last_ping == current_version:
                    return # Ping dla tej wersji już został wysłany
                    
                # Magia kategoryzacji (Nowy vs Update)
                install_type = "New Install" if not last_ping else "Update"
                uuid_str = self.os_doc.get_telemetry_pref("analytics_uuid") or "unknown"
                
                payload = {
                    "api_key": getattr(config, "POSTHOG_API_KEY", ""),
                    "event": event_name,
                    "distinct_id": uuid_str,
                    "properties": {
                        "version": current_version,
                        "os": self.os_doc.os_type,
                        "install_type": install_type,
                        "$lib": "urllib_python"
                    }
                }
                
                # Zabezpieczenie przed wysyłaniem, jeśli klucz nie został podany
                if not payload["api_key"] or "TUTAJ_WKLEISZ" in payload["api_key"]:
                    log_info("Telemetry skip: Default/Empty API Key in config.")
                    return

                data = json.dumps(payload).encode('utf-8')
                host = getattr(config, "POSTHOG_HOST", "https://eu.i.posthog.com")
                url = f"{host.rstrip('/')}/capture/"
                
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                
                # Używamy timeout=5s, żeby nie powiesić wątku, jeśli internet kuleje
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.getcode() == 200:
                        log_info(f"Telemetry ping sent successfully ({install_type}).")
                        # Sukces! Zapisujemy wersję, żeby więcej nie pingować przy kolejnym włączeniu
                        self.os_doc.set_telemetry_pref("last_pinged_version", current_version)
            except Exception as e:
                log_error(f"Telemetry ping failed: {e}")

        # Uruchamiamy w tle
        threading.Thread(target=_ping_thread, daemon=True).start()

    # ==========================================
    # 0. SMART COMPUTE DETECTION
    # ==========================================

    def _get_optimal_compute_type(self):
        """
        Sprawdza wersję Compute Capability karty NVIDIA bez użycia PyTorch.
        Zwraca: "float16", "float32" lub "int8"
        """
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=compute_cap', '--format=csv,noheader'],
                capture_output=True, 
                text=True
            )
            output = result.stdout.strip()
            if not output: return "int8"
                
            first_gpu_cap = output.split('\n')[0]
            if '.' in first_gpu_cap:
                major, minor = first_gpu_cap.split('.')
                major = int(major)
                # Generacja 7 (Volta/Turing - RTX 20xx) i nowsze -> float16
                if major >= 7: return "float16"
                else: return "float32"
            return "float32" 
        except (FileNotFoundError, ValueError, Exception):
            return "int8"

    # ==========================================
    # 1. EXTERNAL PROCESS MANAGEMENT (FASTER-WHISPER)
    # ==========================================

    def _get_python_executable(self):
        return self.os_doc.get_venv_python_path()

    def download_whisper_model_interactive(self, model_name, progress_callback=None):
        log_info(f"Starting interactive download for Faster-Whisper model: {model_name}")
        if model_name == "large": model_name = "large-v3"
        
        script_content = f"""
import sys
import os

# SUPPRESS HF WARNINGS
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Fix for Windows Non-Admin/Non-DevMode

# FORCE CACHE DIR (Inside python script)
os.environ["HF_HOME"] = {repr(self.models_dir)}
os.environ["XDG_CACHE_HOME"] = {repr(self.models_dir)}

libs_dir = {repr(self.libs_dir)}
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    print("DL-START: Target dir " + {repr(self.models_dir)})
    from faster_whisper import download_model
    print("Downloading {model_name}...")
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

    def run_whisper(self, audio_path, model, lang, verbatim, device_mode, compute_type, filler_words_list=None):
        """
        Modified v11.0: Uses stable-ts (stable_whisper) with faster-whisper backend.
        FIXED v11.2: Injects portable bin path to OS PATH for sub-dependencies.
        """
        unique_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = self.os_doc.get_temp_folder()
        json_output_path = os.path.join(output_dir, unique_name + ".json")
        runner_script_path = os.path.join(output_dir, f"fw_runner_{unique_name}.py")

        if model == "large": model = "large-v3"
        fw_device = "cuda" if "GPU" in device_mode else "cpu"
        
        initial_prompt_str = ""
        if verbatim:
            # USER REQUESTED PROMPT (v10.3) - Stutter/Filler injection
            base_prompt = "Umm, yyy, eh, mmm, tsk, h-h-hello, i... i will check, tak tak."
            initial_prompt_str = base_prompt
            if filler_words_list:
                initial_prompt_str += f" {', '.join(filler_words_list)}"

        env = os.environ.copy()
        env["HF_HOME"] = self.models_dir
        
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
        
        script_content = f"""
import sys
import os
import json
import time

# FIXED v11.2: Force include portable bin in PATH for stable-ts subprocess calls
os.environ["PATH"] = {repr(self.os_doc.bin_dir)} + os.pathsep + os.environ.get("PATH", "")

os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HOME"] = {repr(self.models_dir)}

libs_dir = {repr(self.libs_dir)}
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    # --- STABLE-TS INTEGRATION v11.0 ---
    import stable_whisper
    
    model_size = {repr(model)}
    target_device = {repr(fw_device)}
    target_compute = {repr(compute_type)}
    
    print(f"Loading Stable-Whisper (Faster Backend): {{model_size}} on {{target_device}} ({{target_compute}})...")
    
    # Load using stable_whisper wrapper for faster-whisper
    model = stable_whisper.load_faster_whisper(
        model_size, 
        device=target_device, 
        compute_type=target_compute, 
        download_root={repr(self.models_dir)}
    )

    print("Model Loaded Successfully. Starting STABLE Transcription...")
    
    # Parameters optimized for VERBATIM & STABILITY
    result = model.transcribe(
        {repr(audio_path)}, 
        beam_size=1,            # GREEDY DECODING
        patience=1.0,
        language={repr(lang) if lang != "Auto" else "None"},
        initial_prompt={repr(initial_prompt_str)},
        condition_on_previous_text=False,
        vad_filter=False,
        temperature=0.0,
        no_speech_threshold=0.2,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        # Stable-TS specific flags for alignment precision:
        regroup=True,           # Regroup words for better timing
        suppress_silence=True,  # Suppress visual silence in timestamps
        q_levels=20,            # Quantization levels for alignment
        k_size=5                # Kernel size for alignment
    )
    
    output_segments = []
    
    # Iterate over stable-ts segments
    if result.segments:
        for segment in result.segments:
            seg_obj = {{
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": []
            }}
            
            # Stable-TS provides high quality word timestamps
            if segment.words:
                for w in segment.words:
                    # Stable-ts word object attributes
                    seg_obj["words"].append({{
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability if hasattr(w, 'probability') else 1.0
                    }})
            
            output_segments.append(seg_obj)
            print(f"Segment processed: {{segment.start:.2f}}s")

    final_data = {{
        "segments": output_segments,
        "language": getattr(result, 'language', {repr(lang)})
    }}
    
    with open({repr(json_output_path)}, "w", encoding="utf-8") as f:
        json.dump(final_data, f)
        
    print("Transcription Done.")

except Exception as e:
    print(f"FW_ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
        with open(runner_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        python_exec = self._get_python_executable()
        cmd = [python_exec, runner_script_path]
        startup_info = self.os_doc.get_startup_info()
        
        log_info(f"Running Whisper Runner (Stable-TS). Script: {runner_script_path}")
        
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
    # 2.5 HELPER: ENFORCE HALLUCINATION STATUS
    # ==========================================
    
    def _enforce_hallucination_status(self, words_data):
        """
        Forces hallucination objects to remain 'bad' and 'selected'.
        Necessary because algorythms.analyze_repeats clears all initial statuses 
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
            fw_compute = "int8"
            if "GPU" in device_mode:
                fw_compute = self._get_optimal_compute_type()
                log_info(f"Auto-Detected Compute Type: {fw_compute}")
            else:
                log_info(f"Using standard CPU compute: {fw_compute}")

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
            
            # Włączamy nieokreślony pasek ładowania przed weryfikacją (dla Windowsa i Linuxa)
            update_progress(-1) 
            
            def dl_progress_cb(val): pass
            
            # Check/Download logic for Faster-Whisper
            if self.os_doc.needs_manual_model_install():
                self.download_whisper_model_interactive(model, dl_progress_cb)
            
            update_status(get_status_msg("whisper_run", f"Faster-Whisper {model}..."))
            
            # Execute Faster-Whisper via Runner with RESOLVED parameters
            json_path = self.run_whisper(target_wav, model, lang, True, device_mode, fw_compute, filler_words)
            
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
                update_status(get_status_msg("init_analysis", "Finalizing data..."))
                # Wyrzuciliśmy automatyczne odpalanie algorytmów na start (pełen RAW text dla GUI)
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
        def clean_word(txt): return re.sub(r'[^\w\s\'-]', '', txt.strip()).lower()
        def clean_for_match(txt): return re.sub(r'[^\w\s\'-]', '', txt.strip()).lower()

        # --- PASS 1: EXTRACT & COMPRESS HALLUCINATIONS ---
        all_raw_words = []
        for seg in json_data.get('segments', []):
            for w in seg.get('words', []):
                all_raw_words.append(w)
                
        compressed_words = []
        if all_raw_words:
            current_group = [all_raw_words[0]]
            for i in range(1, len(all_raw_words)):
                w = all_raw_words[i]
                prev_w = current_group[-1]
                w_clean = clean_for_match(w['word'])
                prev_clean = clean_for_match(prev_w['word'])
                
                # Check if words are identical and not empty punctuation
                if w_clean and w_clean == prev_clean:
                    current_group.append(w)
                else:
                    if len(current_group) >= 5:
                        merged = current_group[0].copy()
                        merged['end'] = current_group[-1]['end']
                        merged['word'] = f"{merged['word'].strip()} [x{len(current_group)}]"
                        merged['_is_hallucination'] = True
                        compressed_words.append(merged)
                    else:
                        compressed_words.extend(current_group)
                    current_group = [w]
            
            # Process the last group left in memory
            if current_group:
                if len(current_group) >= 5:
                    merged = current_group[0].copy()
                    merged['end'] = current_group[-1]['end']
                    merged['word'] = f"{merged['word'].strip()} [x{len(current_group)}]"
                    merged['_is_hallucination'] = True
                    compressed_words.append(merged)
                else:
                    compressed_words.extend(current_group)

        # --- PASS 2: SMART CHUNKING (Z LOOKAHEAD) ---
        chunks = []
        curr_chunk = []
        for i, w in enumerate(compressed_words):
            curr_chunk.append(w)
            
            last_word_text = w['word'].strip()
            has_punct = last_word_text.endswith(('.', '?', '!'))
            should_break = False
            
            # Absolute maximum hard limit to prevent infinite run-ons
            if len(curr_chunk) >= 33:
                should_break = True
            elif len(curr_chunk) >= 30:
                if has_punct:
                    should_break = True # Break immediately if current word has punctuation
                else:
                    # Look ahead up to remaining allowance (33 - current_length)
                    allowance = 33 - len(curr_chunk)
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
            elif len(curr_chunk) >= 7 and has_punct:
                should_break = True # Normal soft break mid-sentence
                
            if should_break:
                chunks.append(curr_chunk)
                curr_chunk = []
                
        if curr_chunk:
            chunks.append(curr_chunk)

        # --- PASS 3: RAW DATA & FILLER WORDS ONLY ---
        for chunk in chunks:
            if not chunk: continue
            
            seg_start = fix_t(chunk[0].get('start', 0))
            seg_end = fix_t(chunk[-1].get('end', 0))
            is_first = True
            
            for w in chunk:
                raw_txt = w['word'].strip()
                cleaned = clean_word(raw_txt)
                is_hallucination = w.get('_is_hallucination', False)
                
                if cleaned or is_hallucination:
                    is_bad = cleaned in dynamic_bad
                    real_start = fix_t(w['start'])
                    real_end = fix_t(w['end'])
                    
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

        # --- GAP BRIDGING & PADDING (SILENCE LOGIC) ---
        scaled_silence = []
        if silence_ranges:
            for s in silence_ranges:
                scaled_silence.append({'s': fix_t(s['s']), 'e': fix_t(s['e'])})
        
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

        if scaled_silence:
            padded = []
            for s in scaled_silence:
                new_start = s['s'] + 0.05
                new_end = s['e'] - 0.05
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
                    if (gap_end - gap_start) >= 1.2: 
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
                        
                        if valid_start - current_pos > 1.2: 
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
                    
                    if gap_end - current_pos > 1.2: 
                        final_words.append({
                            "start": current_pos, "end": gap_end,
                            "text": txt_inaudible,
                            "type": "inaudible", "status": "inaudible", "selected": True, "is_inaudible": True,
                            "seg_start": curr_w['seg_start'], "seg_end": curr_w['seg_end'], "is_segment_start": False,
                            "manual_status": None, "algo_status": "inaudible", "is_auto": True
                        })

                final_words.append(curr_w)

        for i, w in enumerate(final_words): w['id'] = i
        if final_words:
            final_words[0]['_meta_global_silence'] = raw_global_silence

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
        do_show_typos = settings.get('show_typos', True)

        def t2f(t): return int(round(t * fps))
        
        offset_f = int(round(offset_s * fps))
        pad_f = int(round(pad_s * fps))
        snap_f = int(round(snap_max_s * fps))

        raw_silence = words_data[0].get('_meta_global_silence', None)
        silence_blocks_for_snap = [w for w in words_data if w.get('type') == 'silence']
        
        chunks = []
        current_chunk = None
        
        processed_words = []
        for w in words_data:
            if w.get('type') == 'silence': continue
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            
            # W pełni ignorujemy fragment inaudible podczas składania osi czasu,
            # jeśli pierwszy checkbox (show_inaudible) jest wyłączony.
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
                raw_cut = next_chunk_start
                cut_f = t2f(raw_cut) + offset_f - pad_f
                
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
        # FIX: Force hallucination status after manual re-analysis
        processed_words = self._enforce_hallucination_status(processed_words)
        return processed_words, count

    def run_comparison_analysis(self, script_text, words_data):
        result_words = algorythms.compare_script_to_transcript(script_text, words_data)
        final_words = algorythms.absorb_inaudible_into_repeats(result_words)
        # FIX: Force hallucination status after script comparison analysis
        final_words = self._enforce_hallucination_status(final_words)
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
                
            # AUTO-SOURCING: Zawsze używamy oryginalnego timeline'u z momentu analizy
            original_tl_name = settings.get("original_timeline_name")
            if not original_tl_name:
                original_tl_name = self.resolve_handler.timeline.GetName()
                
            set_status("Detecting optimal source...")
            source_item, context_type = self.resolve_handler.get_optimal_source_item(original_tl_name)
            
            if not source_item:
                log_error("Could not find optimal source clip or timeline.")
                return False, None
                
            audio_only_mode = (context_type == 'audio')
            
            set_progress(30)
            
            set_status("Calculating Cuts...")
            fps = self.resolve_handler.fps
            clean_ops = self.calculate_timeline_structure(words_data, fps, settings)
            
            set_progress(50)
            
            set_status("Assembling in Resolve...")
            
            clean_name, next_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
            new_tl_name = f"{clean_name} BadWords Edit {next_idx}"
            
            # --- ZMIANA: Przekazanie paczkowego callbacku do api.py ---
            def assembly_progress_cb(current, total):
                # Skalujemy postęp w przedziale od 50 do 90 (pozostałe procenty to cleanup i przygotowanie)
                perc = 50 + int((current / max(1, total)) * 40)
                set_progress(perc)
                # Dynamiczna zmiana tekstu w UI
                set_status(f"Assembling {current}/{total} clips...")

            success = self.resolve_handler.generate_timeline_from_ops(
                clean_ops, 
                source_item, 
                new_tl_name,
                audio_only_mode=audio_only_mode,
                progress_callback=assembly_progress_cb
            )
            # -----------------------------------------------------------
            
            if not success:
                log_error("Failed to generate timeline via API.")
                return False, None
                
            set_progress(100)
            return True, warning_code
            
        except Exception as e:
            log_error(f"Assembly Critical Error: {e}")
            traceback.print_exc()
            return False, None