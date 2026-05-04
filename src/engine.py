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

    def txt(self, key: str, **kwargs) -> str:
        import config
        prefs = self.load_preferences() or {}
        lang = prefs.get("gui_lang", "en")
        text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

    def save_preferences(self, settings_dict):
        """Delegates all preference saving to OSDoctor's smart router.
        Keys are automatically routed to user.json or settings.json.
        """
        self.os_doc.save_all_prefs(settings_dict)

    def load_preferences(self):
        """Delegates all preference loading to OSDoctor's smart router.
        Returns a merged dict of user data + settings.
        """
        return self.os_doc.get_all_prefs()

    # ==========================================
    # TELEMETRY (POSTHOG)
    # ==========================================

    def send_telemetry_ping(self, event_name="app_started"):
        """
        Asynchroniczne wysyłanie pingu telemetrycznego do PostHog.
        Wysyła tylko za zgodą użytkownika i tylko raz na daną wersję.
        """
        try:
            # 1. Sprawdzenie flagi - z uwzględnieniem parsowania stringów z JSON
            opt_in = self.os_doc.get_telemetry_pref("telemetry_opt_in")
            if opt_in not in [True, "True", "true", 1, "1"]:
                log_info("Telemetry: Oczekuje na zgode lub zgoda zostala odrzucona.")
                return 
            
            last_ping = self.os_doc.get_telemetry_pref("last_pinged_version")
            current_version = config.VERSION
            
            if last_ping == current_version:
                log_info(f"Telemetry: Ping for version {current_version} already sent. Skipping.")
                return 
                
            # Natychmiastowe nadpisanie zabezpieczające przed dublowaniem żądań z innych wątków/okien
            self.os_doc.set_telemetry_pref("last_pinged_version", current_version)
            
            install_type = "New Install" if not last_ping else "Update"
            uuid_str = self.os_doc.get_telemetry_pref("analytics_uuid") or "unknown"
            allow_geo = self.os_doc.get_telemetry_pref("telemetry_allow_geo")
            machine_id = self.os_doc.get_telemetry_pref("analytics_uuid") or ""
            
            def _ping_thread(previous_version):
                import ssl
                try:
                    # distinct_id dla bezpieczeństwa dublujemy w properties i na zewnątrz (wymogi PostHog API)
                    payload = {
                        "api_key": getattr(config, "POSTHOG_API_KEY", ""),
                        "event": event_name,
                        "distinct_id": uuid_str, 
                        "properties": {
                            "distinct_id": uuid_str,
                            "version": current_version,
                            "os": self.os_doc.os_type,
                            "install_type": install_type,
                            "$lib": "urllib_python"
                        }
                    }
                    if not allow_geo:
                        payload["properties"]["$geoip_disable"] = True
                    
                    if machine_id == "762c22f5-0dbe-8238-43d4-31c0d0d33d5a":
                        payload["properties"]["is_dev_env"] = True
                        log_info("Dev environment recognized. Telemetry ping flagged as is_dev_env.")
                    
                    if not payload["api_key"] or "TUTAJ_WKLEISZ" in payload["api_key"]:
                        log_info("Telemetry skip: Default/Empty API Key in config.")
                        self.os_doc.set_telemetry_pref("last_pinged_version", previous_version)
                        return

                    data = json.dumps(payload).encode('utf-8')
                    host = getattr(config, "POSTHOG_HOST", "https://eu.i.posthog.com")
                    url = f"{host.rstrip('/')}/capture/"
                    
                    # Usunąłem User-Agent, dodano Accept. Zapobiega to blokowaniu przez Cloudflare.
                    headers = {
                        'Content-Type': 'application/json',
                        'Accept': '*/*'
                    }
                    req = urllib.request.Request(url, data=data, headers=headers)
                    
                    # OMINIECIE PROBLEMU Z BRAKIEM CERTYFIKATOW SSL W PORTABLE PYTHON
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        if response.getcode() == 200:
                            log_info(f"Telemetry ping sent successfully ({install_type} - {current_version}).")
                        else:
                            self.os_doc.set_telemetry_pref("last_pinged_version", previous_version)
                            log_error(f"Telemetry ping failed with HTTP code {response.getcode()}")
                except Exception as e:
                    self.os_doc.set_telemetry_pref("last_pinged_version", previous_version)
                    log_error(f"Telemetry ping HTTP request failed: {e}")

            threading.Thread(target=_ping_thread, args=(last_ping,), daemon=True).start()

        except Exception as e:
            log_error(f"Telemetry initialization failed: {e}")

    # ==========================================
    # 0. SMART COMPUTE DETECTION
    # ==========================================

    def _get_optimal_compute_type(self, device="cpu"):
        """
        3-LEVEL SMART COMPUTE DETECTION:
          CPU (any):         → int8   (safest, universal)
          GPU cc < 7.0:      → int8_float32  (Pascal/Maxwell: GTX 9xx/10xx)
          GPU cc >= 7.0:     → int8_float16  (Volta/Turing/Ampere+: RTX 2xxx+)

        NOTE: This is only called when ai_compute_type == 'Auto'.
        If the user explicitly sets float16 or float32, that value is used
        directly without calling this function.
        """
        if device != "cuda":
            return "int8"
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=compute_cap', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                **self.os_doc.get_subprocess_kwargs()
            )
            output = result.stdout.strip()
            if not output:
                return "int8_float32"  # fallback for GPU with unknown cap

            first_gpu_cap = output.split('\n')[0].strip()
            if '.' in first_gpu_cap:
                major, _minor = first_gpu_cap.split('.', 1)
                major = int(major)
                if major >= 7:
                    return "int8_float16"   # RTX 2000+ (Volta/Turing/Ampere/Ada)
                else:
                    return "int8_float32"   # GTX 900/1000 (Maxwell/Pascal)
            return "int8_float32"
        except (FileNotFoundError, ValueError, Exception) as e:
            log_info(f"[ComputeDetect] nvidia-smi failed ({e}); falling back to int8")
            return "int8"

    def verify_hardware_compute(self, device_pref: str, compute_pref: str) -> bool:
        """
        Stage 6A v2: Validates that the chosen compute type is actually supported
        by the hardware, using ctranslate2 directly (no model load needed).
        Returns True if supported or if compute_pref is 'auto' (skips validation).
        """
        if compute_pref.lower() == "auto":
            return True

        # Determine the real target device
        if device_pref.lower() in ("gpu", "auto") and self.os_doc.has_nvidia_support():
            target_device = "cuda"
        else:
            target_device = "cpu"

        probe_script = (
            f"import ctranslate2; "
            f"types = list(ctranslate2.get_supported_compute_types('{target_device}')); "
            f"print(types)"
        )

        try:
            python_exe = self.os_doc.get_venv_python_path()
            kwargs = {}
            if hasattr(self.os_doc, 'get_subprocess_kwargs'):
                kwargs = self.os_doc.get_subprocess_kwargs()
            result = subprocess.run(
                [python_exe, "-c", probe_script],
                capture_output=True, text=True, timeout=15,
                **kwargs,
            )
            log_info(f"[VerifyCompute] target={target_device} probe stdout: {result.stdout.strip()}")
            return compute_pref in result.stdout
        except Exception as exc:
            log_info(f"[VerifyCompute] Probe failed ({exc}); defaulting to supported=True")
            return True  # Don't block the user if the probe itself errors

    # ==========================================
    # 1. EXTERNAL PROCESS MANAGEMENT (FASTER-WHISPER)
    # ==========================================

    def _get_python_executable(self):
        return self.os_doc.get_venv_python_path()

    def download_whisper_model_interactive(self, model_name, progress_callback=None, status_callback=None):
        log_info(f"Starting interactive download for Faster-Whisper model: {model_name}")
        if model_name == "large": model_name = "large-v3"
        
        script_content = f"""
import sys
import os
import re

# Force tqdm to render progress bar even if not in terminal
class FakeTTY:
    def __init__(self, stream):
        self.stream = stream
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
    def isatty(self):
        return True
    def write(self, *args, **kwargs):
        self.stream.write(*args, **kwargs)
        self.stream.flush()

sys.stderr = FakeTTY(sys.stderr)
sys.stdout = FakeTTY(sys.stdout)
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
os.environ["TQDM_DISABLE"] = "0"

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
    download_model("{model_name}", cache_dir={repr(self.models_dir)})
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
        env = os.environ.copy()
        env["HF_HOME"] = self.models_dir
        
        try:
            # Disable tqdm in huggingface_hub so it doesn't pollute stdout with \r
            env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
            
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
                env=env, **self.os_doc.get_subprocess_kwargs()
            )
            
            for line in process.stdout:
                line_s = line.strip()
                if line_s:
                    log_info(f"[FW-DL] {line_s}")


            process.wait()
            if process.returncode == 0:
                log_info(f"Model {model_name} ready.")
                return True
            else:
                log_error(f"Model download failed (return code {process.returncode})")
                return False
        except Exception as e:
            log_error(f"Download execution failed: {e}")
            return False
        finally:
            if os.path.exists(runner_path):
                try: os.remove(runner_path)
                except: pass



    def check_model_exists(self, model_name):
        if model_name == "large": model_name = "large-v3"
        model_folder = os.path.join(self.models_dir, f"models--Systran--faster-whisper-{model_name}")
        snapshots_dir = os.path.join(model_folder, "snapshots")
        return os.path.exists(snapshots_dir) and len(os.listdir(snapshots_dir)) > 0

    def run_whisper(self, audio_path, model, lang, verbatim, device_mode, compute_type,
                    filler_words_list=None, initial_prompt=None, progress_callback=None,
                    islands=None):
        """
        Modified v11.0: Uses stable-ts (stable_whisper) with faster-whisper backend.
        FIXED v11.2: Injects portable bin path to OS PATH for sub-dependencies.
        UPDATED v12.1: Replaced subprocess.run with Popen for real-time output streaming.
        STAGE 9: Enabled VAD filter (min_silence_duration_ms=400) + no_repeat_ngram_size=0 to kill hallucination loops.
        STAGE 6A: initial_prompt injected via repr() for safe quoting in generated script.
        UPDATED v13.0: initial_prompt is now per-language aware via config.get_whisper_prompt_for_lang().
        UPDATED v14.0: True In-Memory Chunking via islands list (NumPy slicing, zero disk I/O).
        """
        unique_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = self.os_doc.get_temp_folder()
        json_output_path = os.path.join(output_dir, unique_name + ".json")
        runner_script_path = os.path.join(output_dir, f"fw_runner_{unique_name}.py")

        if model == "large": model = "large-v3"
        fw_device = "cuda" if "GPU" in device_mode else "cpu"
        
        prefs = self.os_doc.get_all_prefs()

        initial_prompt_str = ""
        if verbatim:
            # Stage 6A: Use user's custom initial prompt if set, else fall back to DEFAULT_WHISPER_PROMPT
            base_prompt = initial_prompt if initial_prompt else config.DEFAULT_WHISPER_PROMPT
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

        # ── Chunked mode: in-memory NumPy slicing ────────────────────────────
        use_chunking = islands is not None and len(islands) > 1
        if use_chunking:
            log_info(f"[Chunked] {len(islands)} sound islands → in-memory NumPy slicing.")
            script_content = f"""
import sys, os, json, time
import numpy as np

os.environ["PATH"] = {repr(self.os_doc.bin_dir)} + os.pathsep + os.environ.get("PATH", "")
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HOME"] = {repr(self.models_dir)}
libs_dir = {repr(self.libs_dir)}
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)
try:
    import stable_whisper
    from faster_whisper.audio import decode_audio
    
    RAW_ISLANDS = {repr(islands)}
    MAX_CLUSTER_DUR = 22.0
    MIN_CLUSTER_DUR = 8.0
    MIN_SAFE_GAP = 0.5
    ISLANDS = []
    
    if RAW_ISLANDS:
        i = 0
        while i < len(RAW_ISLANDS):
            c_start = RAW_ISLANDS[i][0]
            
            J = []
            for j in range(i, len(RAW_ISLANDS)):
                if RAW_ISLANDS[j][1] - c_start <= MAX_CLUSTER_DUR:
                    J.append(j)
                else:
                    break
                    
            if not J:
                J = [i]
                
            if J[-1] == len(RAW_ISLANDS) - 1:
                best_j = J[-1]
            else:
                optimal = []
                safe = []
                for j in J:
                    gap = RAW_ISLANDS[j+1][0] - RAW_ISLANDS[j][1]
                    dur = RAW_ISLANDS[j][1] - c_start
                    if gap >= MIN_SAFE_GAP:
                        safe.append(j)
                        if dur >= MIN_CLUSTER_DUR:
                            optimal.append(j)
                            
                if optimal:
                    best_j = max(optimal, key=lambda j: RAW_ISLANDS[j+1][0] - RAW_ISLANDS[j][1])
                elif safe:
                    best_j = max(safe, key=lambda j: RAW_ISLANDS[j+1][0] - RAW_ISLANDS[j][1])
                else:
                    best_j = max(J, key=lambda j: RAW_ISLANDS[j+1][0] - RAW_ISLANDS[j][1])
                    
            c_end = RAW_ISLANDS[best_j][1]
            ISLANDS.append((c_start, c_end))
            i = best_j + 1
        
    model_size     = {repr(model)}
    target_device  = {repr(fw_device)}
    target_compute = {repr(compute_type)}
    print(f"[Chunked] Loading model {{model_size}} on {{target_device}} ({{target_compute}})...")
    model = stable_whisper.load_faster_whisper(
        model_size, device=target_device, compute_type=target_compute,
        download_root={repr(self.models_dir)}
    )
    print("[Chunked] Model loaded. Decoding audio array...")
    audio_array  = decode_audio({repr(audio_path)}, sampling_rate=16000)
    total_chunks = len(ISLANDS)
    print(f"[Chunked] {{total_chunks}} islands to process.")
    print("CHUNK_PROGRESS: 0")
    output_segments = []
    
    for chunk_idx, (island_start, island_end) in enumerate(ISLANDS):
        s_idx = int(island_start * 16000)
        e_idx = int(island_end   * 16000)
        chunk = audio_array[s_idx:e_idx]
        if len(chunk) == 0:
            print(f"CHUNK_PROGRESS: {{int((chunk_idx+1)/total_chunks*100)}}")
            continue
        print(f"[Chunked] Island {{chunk_idx+1}}/{{total_chunks}}: {{island_start:.2f}}s—{{island_end:.2f}}s")
        
        chunk_result = model.transcribe(
            chunk,
            beam_size={repr(prefs.get('ai_beam_size', 1))},
            patience={repr(prefs.get('ai_patience', 1.0))},
            language={repr(lang) if lang != 'Auto' else 'None'},
            initial_prompt={repr(initial_prompt_str)},
            condition_on_previous_text=False,
            vad_filter={repr(prefs.get('ai_vad_filter', False))},
            temperature={repr(prefs.get('ai_temperature', 0.0))},
            no_speech_threshold={0.6 if islands is not None else repr(prefs.get('ai_no_speech_threshold', 0.2))},
            log_prob_threshold={repr(prefs.get('ai_logprob_threshold', -1.0))},
            compression_ratio_threshold={2.4 if islands is not None else repr(prefs.get('ai_compression_ratio_threshold', 10.0))},
            no_repeat_ngram_size={repr(prefs.get('ai_no_repeat_ngram_size', 0))},
            regroup={repr(prefs.get('ai_regroup', False))},
            suppress_silence={repr(prefs.get('ai_suppress_silence', False))},
            q_levels={repr(prefs.get('ai_q_levels', 20))},
            k_size={repr(prefs.get('ai_k_size', 5))},
            verbose=False
        )
        if chunk_result.segments:
            for seg in chunk_result.segments:
                seg_obj = {{
                    "start": seg.start + island_start,
                    "end":   seg.end   + island_start,
                    "text":  seg.text,
                    "words": []
                }}
                if seg.words:
                    for w in seg.words:
                        seg_obj["words"].append({{
                            "word":        w.word,
                            "start":       w.start + island_start,
                            "end":         w.end   + island_start,
                            "probability": w.probability if hasattr(w, 'probability') else 1.0
                        }})
                output_segments.append(seg_obj)
                print(f"Segment processed: {{seg.start + island_start:.2f}}s")
                
        print(f"CHUNK_PROGRESS: {{int((chunk_idx+1)/total_chunks*100)}}")
    final_data = {{"segments": output_segments, "language": {repr(lang)}}}
    with open({repr(json_output_path)}, "w", encoding="utf-8") as f:
        json.dump(final_data, f)
    print("Transcription Done.")
except Exception as e:
    print(f"FW_ERROR: {{e}}")
    import traceback; traceback.print_exc()
    sys.exit(1)
"""
        else:
            # ── Original single-file runner (unchanged) ──────────────────────
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
    
    # Parameters for strict VERBATIM output (STAGE 9: Unchain for phrasal retakes)
    result = model.transcribe(
        {repr(audio_path)}, 
        beam_size={repr(prefs.get('ai_beam_size', 1))},
        patience={repr(prefs.get('ai_patience', 1.0))},
        language={repr(lang) if lang != "Auto" else "None"},
        initial_prompt={repr(initial_prompt_str)},
        condition_on_previous_text={repr(prefs.get('ai_condition_on_prev', False))},
        vad_filter={repr(prefs.get('ai_vad_filter', False))},
        temperature={repr(prefs.get('ai_temperature', 0.0))},
        no_speech_threshold={repr(prefs.get('ai_no_speech_threshold', 0.2))},
        log_prob_threshold={repr(prefs.get('ai_logprob_threshold', -1.0))},
        compression_ratio_threshold={repr(prefs.get('ai_compression_ratio_threshold', 10.0))},
        no_repeat_ngram_size={repr(prefs.get('ai_no_repeat_ngram_size', 0))},
        # Stable-TS specific flags for alignment precision:
        regroup={repr(prefs.get('ai_regroup', False))},
        suppress_silence={repr(prefs.get('ai_suppress_silence', False))},
        q_levels={repr(prefs.get('ai_q_levels', 20))},
        k_size={repr(prefs.get('ai_k_size', 5))}
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
        
        log_info(f"Running Whisper Runner (Stable-TS). Script: {runner_script_path}")
        
        try:
            whisper_start = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True,
                env=env,
                **self.os_doc.get_subprocess_kwargs()
            )
            
            segments_count = 0
            # Lines that are filtered from [RUNNER] log but still parsed for progress signals
            spam_markers = [
                "Transcribe:", "Adjustment:", "Segment processed:",
                "CHUNK_PROGRESS:", "[Chunked]",
                "Transcribing with faster-whisper",
                "Detected language:", "Detected Language:",
            ]
            for line in iter(process.stdout.readline, ''):
                if any(marker in line for marker in spam_markers):
                    # Standard stable-ts % (only parse if not in chunked mode to prevent bouncing)
                    if not use_chunking:
                        match = re.search(r'Transcribe:\s*(\d+)%', line)
                        if match and progress_callback:
                            progress_callback(int(match.group(1)))
                    # Chunked mode % — checked unconditionally inside the filtered block
                    chunk_match = re.search(r'CHUNK_PROGRESS:\s*(\d+)', line)
                    if chunk_match and progress_callback:
                        progress_callback(int(chunk_match.group(1)))
                    if "Segment processed:" in line:
                        segments_count += 1
                else:
                    line_stripped = line.strip()
                    if line_stripped:
                        log_info(f"[RUNNER] {line_stripped}")
            
            process.wait()
            whisper_sec = int(time.time() - whisper_start)
            w_mins = whisper_sec // 60
            w_secs = whisper_sec % 60
            log_info(f"[RUNNER] Transcription complete in {w_mins}:{w_secs:02d} min. Total segments processed: {segments_count}")
            
            if process.returncode != 0:
                log_error(f"Subprocess Failed. Return Code: {process.returncode}")
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
        STAGE 9 FIX: Gentle processing only — preserves micro-pauses between stutters.
        Removed loudnorm (was raising noise floor and masking silence gaps).
        Using a very light compressor just to catch hard peaks, nothing more.
        """
        norm_path = input_path.replace(".wav", "_norm.wav")
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
        except:
            return input_path
    
    def create_slow_motion_audio(self, input_path, speed_factor):
        # STAGE 9 FIX: Single atempo filter (speed_factor driven by caller).
        # Multi-chained atempo was compounding distortion; one pass is cleaner.
        base, ext = os.path.splitext(input_path)
        slow_path = f"{base}_slow{ext}"
        filter_chain = f"atempo={speed_factor}"
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_path, "-filter:a", filter_chain, "-vn", slow_path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, **self.os_doc.get_subprocess_kwargs())
            return slow_path
        except Exception as e:
            log_error(f"Slow Motion Generation Failed: {e}")
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
                    "-ss", str(in_s),
                    "-t",  str(dur_s),
                    "-i",  source_file,
                    "-vn",
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
            ffprobe = self.ffmpeg_cmd.replace("ffmpeg", "ffprobe")
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
          4. Timestamps are scaled back by SLOW_FACTOR so meta_global_silence
             is always in real (source) time for calculate_timeline_structure.
        """
        def update_status(msg):
            if callback_status: callback_status(msg)
        def update_progress(val):
            if callback_progress: callback_progress(val)

        wav_path      = None
        slow_wav      = None
        normalized_wav = None

        # Mirror the same constants used in run_analysis_pipeline
        SLOW_FACTOR = 0.90

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

            # STEP 1: Slow motion — identical to run_analysis_pipeline.
            # Stretches silence windows so FFmpeg can detect them with the same
            # precision as the transcription path.
            update_status(self.txt("status_slow"))
            slow_wav = self.create_slow_motion_audio(wav_path, SLOW_FACTOR)
            analysis_wav = slow_wav if slow_wav != wav_path else wav_path

            update_progress(40)

            # STEP 2: Normalize — same filter chain as transcription path.
            normalized_wav = self.normalize_audio(analysis_wav)
            target_wav = normalized_wav

            update_progress(55)
            update_status(self.txt("status_silence"))

            # STEP 3: Detect silence using user-configured thresholds.
            # Both min_dur and threshold_db are now read from settings, so the user
            # can tune them from the GUI without touching engine code.
            min_silence_dur = settings.get('silence_min_dur', 0.2)
            raw_silences_slow = self.detect_silence(target_wav, threshold_db, min_silence_dur)

            # STEP 4: Scale timestamps back to real (source) time.
            # slow_wav stretches all timestamps by 1/SLOW_FACTOR; we must invert
            # this so that meta_global_silence is aligned with the original timeline.
            raw_silences = [
                {'s': s['s'] * SLOW_FACTOR, 'e': s['e'] * SLOW_FACTOR}
                for s in raw_silences_slow
            ]

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

            # Apply padding to each detected silence
            padded_silences = []
            for s in bridged:
                new_start = s['s'] + padding_s
                new_end   = s['e'] - padding_s
                if new_end > new_start:
                    padded_silences.append({'s': new_start, 'e': new_end})

            # --- Compute audio duration from Resolve timeline ---
            fps = self.resolve_handler.fps
            tl_start = self.resolve_handler.get_timeline_start_frame()
            tl_end = self.resolve_handler.timeline.GetEndFrame()
            duration_s = (tl_end - tl_start) / fps

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
            # Cleanup temp files safely (slow_wav is an extra file to clean up)
            for p in [normalized_wav, slow_wav, wav_path]:
                if p and p != wav_path and os.path.exists(p):
                    try: os.remove(p)
                    except: pass
            if wav_path and os.path.exists(wav_path):
                try: os.remove(wav_path)
                except: pass


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
            # Stage 6A: Prefer user-saved ai_compute_type from settings; auto-detect as fallback
            saved_prefs     = self.os_doc.get_all_prefs()
            saved_compute        = saved_prefs.get('ai_compute_type', '')
            user_custom_prompt   = saved_prefs.get('ai_initial_prompt', '').strip()
            # Per-language prompt selection: respects custom user prompt first,
            # then falls back to a language-specific verbatim prompt, then GOLDEN baseline.
            # lang is resolved above (None = auto-detect, str = specific language code)
            ai_initial_prompt = config.get_whisper_prompt_for_lang(lang, user_custom_prompt)
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
                    fw_compute = "int8"
                    log_info(f"[Compute] Auto (CPU): {fw_compute}")

            filler_words = settings.get('filler_words', [])
            fps = self.resolve_handler.fps
            txt_inaudible = "inaudible"
            
            USE_SLOW_MODE = True 
            SLOW_FACTOR = 0.90  # STAGE 9 FIX: 10% slowdown only; deep slow destroys phonetic transients
            
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

            # 1. SLOW DOWN
            current_wav_path = wav_path
            time_scale_correction = 1.0
            
            if USE_SLOW_MODE:
                update_status(self.txt("status_slow"))
                slow_wav = self.create_slow_motion_audio(wav_path, SLOW_FACTOR)
                if slow_wav != wav_path:
                    current_wav_path = slow_wav
                    time_scale_correction = SLOW_FACTOR
            
            update_progress(75)

            # 2. NORMALIZE
            # (Silently normalizes audio under the fast motion process without flashing screen)
            normalized_wav = self.normalize_audio(current_wav_path)
            target_wav = normalized_wav

            update_progress(100)
            time.sleep(0.3) # Let user see 100% completion of Phase 1

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
            # Chunked mode (Ultra Precise) activates only if requested and len(islands) > 1
            ultra_precise_mode = self.os_doc.get_all_prefs().get('ai_ultra_precise', config.DEFAULT_SETTINGS.get('ai_ultra_precise', False))
            if not ultra_precise_mode:
                islands = None
            
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
            for p in [wav_path, current_wav_path, normalized_wav]:
                if p and os.path.exists(p) and p != wav_path:
                     try: os.remove(p)
                     except: pass
            try: os.remove(wav_path)
            except: pass

            update_status(self.txt("status_process"))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            words_data, segments_data = self._build_data_structure(
                data, silence_ranges, filler_words, fps, 
                txt_inaudible, time_scale_correction
            )
            
            if words_data:
                update_status(self.txt("status_finalize"))
                # Wyrzuciliśmy automatyczne odpalanie algorytmów na start (pełen RAW text dla GUI)
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

            update_progress(100)
            return words_data, segments_data


        except Exception as e:
            log_error(f"Pipeline Critical Error: {traceback.format_exc()}")
            return None, None

    def _build_data_structure(self, json_data, silence_ranges, filler_words, fps, 
                              txt_inaudible="inaudible", time_scale_correction=1.0):
        prefs = self.os_doc.get_all_prefs()
        temp_words = []
        dynamic_bad = [w.lower().strip() for w in filler_words]
        
        def fix_t(t): return t * time_scale_correction
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
            for n in range(1, 16):
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

        # NOTE: Stretched-word inaudible detector removed (v14.1) — replaced by
        # gap-based inaudible detection below which has no false positives.

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
                # FIX #1 (DRIFT): The cut point is the start of the NEXT chunk.
                # offset_f shifts the cut earlier/later (global timing trim).
                # pad_f is a safety buffer added to the START of the next block,
                # NOT subtracted from the END of the current one.
                # Old code: `cut_f = t2f(raw_cut) + offset_f - pad_f`
                # This double-subtracted (offset is already negative) causing
                # ~2 frames of loss per cut boundary = 4-5 seconds over 55 clips.
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
                # If a track duration cap is active, clamp to it exactly (no pad_f
                # beyond the cap) so we don't produce silent tail frames.
                raw_block_end = max(audio_end_f, t2f(chunk_end_w)) + pad_f
                if audio_end_cap_s:
                    # Never exceed the hard cap — the tail silence IS the cap boundary
                    block_end_f = min(raw_block_end, audio_end_f)
                else:
                    block_end_f = raw_block_end

            
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
                "title_bar_text": data_packet.get("title_bar_text", ""),
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
        prefs = self.os_doc.get_all_prefs()
        algo_settings = {k: prefs[k] for k in ('algo_fuzzy_threshold', 'algo_retake_lookahead', 'algo_distance_penalty', 'algo_anchor_depth') if k in prefs}
        processed_words, count = algorithms.analyze_repeats(words_data, show_inaudible=show_inaudible, algo_settings=algo_settings)
        processed_words = algorithms.absorb_inaudible_into_repeats(processed_words)
        # FIX: Force hallucination status after manual re-analysis
        processed_words = self._enforce_hallucination_status(processed_words)
        return processed_words, count

    def run_comparison_analysis(self, script_text, words_data):
        prefs = self.os_doc.get_all_prefs()
        algo_settings = {k: prefs[k] for k in ('algo_fuzzy_threshold', 'algo_retake_lookahead', 'algo_distance_penalty', 'algo_anchor_depth') if k in prefs}
        
        result_words = algorithms.compare_script_to_transcript(script_text, words_data, algo_settings=algo_settings)
        final_words = algorithms.absorb_inaudible_into_repeats(result_words)
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
        """
        PRIMARY PATH: Builds a complete FCP7 XML in Python and imports it into
        Resolve in a single API call (ImportTimelineFromFile).

        ABSOLUTE EMERGENCY FALLBACK: If XML build or import fails, falls back to
        the old AppendToTimeline method (generate_timeline_from_ops). The fallback
        is logged clearly and should never be reached under normal operation.
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

            # ── NAME FOR NEW TIMELINE ─────────────────────────────────────────
            clean_name, next_idx = self.resolve_handler.get_next_badwords_edit_index(original_tl_name)
            new_tl_name = f"{clean_name} BadWords Edit {next_idx}"

            # ── LOAD PRESERVE TRACK ORDER + AUTO_DEL SETTINGS ────────────────
            import config
            prefs = self.os_doc.get_all_prefs()
            preserve_track_order = bool(prefs.get(
                "xml_preserve_track_order",
                config.DEFAULT_SETTINGS["xml_preserve_track_order"]
            ))
            # auto_del is already baked into clean_ops by calculate_timeline_structure().
            # No need to pass it further down the XML pipeline.

            # ──────────────────────────────────────────────────────────────────
            # PRIMARY PATH: XML BUILD + IMPORT
            # ──────────────────────────────────────────────────────────────────
            xml_success = False
            xml_tl_name = None

            try:
                temp_dir = self.os_doc.get_temp_folder()
                os.makedirs(temp_dir, exist_ok=True)
                safe_name = "".join(c for c in new_tl_name if c.isalnum() or c in '_-')
                xml_path  = os.path.join(temp_dir, f"bw_edit_{safe_name}.xml")

                set_status(self.txt("status_assembly_xml_build"))
                set_progress(-1)

                ok_build, color_schedule = self.resolve_handler.build_edit_xml_from_ops(
                    ops                  = clean_ops,
                    source_tl_name       = original_tl_name,
                    new_tl_name          = new_tl_name,
                    track_indices        = track_indices if not all_tracks_selected else [],
                    audio_only_mode      = audio_only_mode,
                    output_path          = xml_path,
                    preserve_track_order = preserve_track_order,
                )

                if ok_build:
                    set_status(self.txt("status_assembly_xml_import"))
                    set_progress(-1)

                    # ── SET FOLDER: Resources for source clips, Edits for the TL ─────
                    # Source clips from the XML import land in the CURRENT folder.
                    # We want source clips in BadWords/Resources, not Edits.
                    # After import, we move only the timeline's MediaPoolItem to Edits.
                    resources_bin = self.resolve_handler.get_badwords_resources_bin()
                    edits_bin     = self.resolve_handler.get_badwords_edits_bin()
                    if resources_bin:
                        try:
                            self.resolve_handler.media_pool.SetCurrentFolder(resources_bin)
                        except Exception:
                            pass

                    import_options = {
                        "timelineName":      new_tl_name,
                        "importSourceClips": True,
                    }
                    new_tl = self.resolve_handler.media_pool.ImportTimelineFromFile(
                        xml_path, import_options
                    )

                    if new_tl:
                        actual_name = new_tl.GetName()
                        log_info(f"assemble_timeline: XML import OK → '{actual_name}'")
                        xml_tl_name = actual_name

                        # Move the assembled timeline to Edits bin.
                        # Source clips stay in Resources (where they landed on import).
                        if edits_bin:
                            try:
                                tl_item = self.resolve_handler.find_timeline_item_recursive(
                                    self.resolve_handler.media_pool.GetRootFolder(), actual_name
                                )
                                if tl_item:
                                    self.resolve_handler.media_pool.MoveClips([tl_item], edits_bin)
                                    log_info(f"assemble_timeline: moved '{actual_name}' → BadWords/Edits")
                                else:
                                    log_error("assemble_timeline: could not locate timeline item in pool")
                            except Exception as move_err:
                                log_error(f"assemble_timeline: MoveClips error: {move_err}")

                        # ── Verify/correct clip colors (precise schedule) ──────────
                        set_status(self.txt("status_assembly_colors"))
                        self.resolve_handler.reapply_clip_colors(xml_tl_name, color_schedule)

                        xml_success = True
                    else:
                        log_error("assemble_timeline: ImportTimelineFromFile returned None.")
                else:
                    log_error("assemble_timeline: XML build failed.")

                # Cleanup temp XML regardless of success
                try:
                    if os.path.exists(xml_path):
                        os.remove(xml_path)
                except Exception:
                    pass

            except Exception as xml_err:
                log_error(f"assemble_timeline: XML path exception: {xml_err}")
                import traceback as _tb
                log_error(_tb.format_exc())

            # ──────────────────────────────────────────────────────────────────
            # ABSOLUTE EMERGENCY FALLBACK: AppendToTimeline
            # Triggered ONLY if XML path completely failed.
            # ──────────────────────────────────────────────────────────────────
            if not xml_success:
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
                                    filtered_xml, original_tl_name
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