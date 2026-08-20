#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: transcription.py
ROLE: Core Engine
DESCRIPTION:
Interface for external transcription models (e.g., Whisper).
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

class TranscriptionMixin:
    def _get_system_ram_gb(self):
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            pass
        
        try:
            import platform, subprocess
            if platform.system() == "Darwin":
                res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
                return int(res.stdout.strip()) / (1024**3)
            elif platform.system() == "Windows":
                res = subprocess.run(["wmic", "computersystem", "get", "TotalPhysicalMemory"], capture_output=True, text=True)
                lines = res.stdout.strip().split('\n')
                if len(lines) > 1:
                    return int(lines[1].strip()) / (1024**3)
            elif platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            return int(line.split()[1]) / (1024**2)
        except Exception:
            pass
        return 8.0 # fallback

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
            ram_gb = self._get_system_ram_gb()
            if hasattr(self, 'os_doc') and getattr(self.os_doc, 'is_mac', False):
                return "float32" if ram_gb >= 14.0 else "int8"
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
{'''
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
''' if self.os_doc.is_mac else ""}
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
                except Exception as e:
                    log_error(f"download_whisper_model_interactive: cleanup failed: {e}")



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

        kwargs_str = ""
        if prefs.get('ai_length_penalty', 1.0) != 1.0:
            kwargs_str += f", length_penalty={repr(prefs.get('ai_length_penalty', 1.0))}"
        if prefs.get('ai_repetition_penalty', 1.0) != 1.0:
            kwargs_str += f", repetition_penalty={repr(prefs.get('ai_repetition_penalty', 1.0))}"

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
{'''
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
''' if self.os_doc.is_mac else ""}
libs_dir = {repr(self.libs_dir)}
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)
try:
    from faster_whisper import WhisperModel
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
        
    import concurrent.futures
    import multiprocessing
    
    model_size     = {repr(model)}
    target_device  = {repr(fw_device)}
    target_compute = {repr(compute_type)}
    
    # Decide how many parallel workers to use
    cpu_threads_val = 4
    if target_device == "cpu":
        # CPU Optimization: Prevent thread thrashing. 
        # CTranslate2 uses 'cpu_threads' per worker. If we have 12 cores, 
        # 3 workers * 4 threads = 12 concurrent threads. This is highly optimal.
        cpu_cores = multiprocessing.cpu_count()
        workers = max(1, int(cpu_cores / cpu_threads_val))
    else:
        # GPU (CUDA/MPS): 2 workers empirically proven to yield ~20% faster times 
        # (0:35 vs 0:42) by saturating CUDA cores while keeping VRAM usage safe for 'base' model.
        workers = 2

    print(f"[Chunked] Loading model {{model_size}} on {{target_device}} ({{target_compute}}) with {{workers}} workers...")
    model = WhisperModel(
        model_size, device=target_device, compute_type=target_compute,
        cpu_threads=cpu_threads_val, num_workers=workers,
        download_root={repr(self.models_dir)}
    )
    print("[Chunked] Model loaded. Decoding audio array...")
    audio_array  = decode_audio({repr(audio_path)}, sampling_rate=16000)
    total_chunks = len(ISLANDS)
    print(f"[Chunked] {{total_chunks}} islands to process.")
    print("CHUNK_PROGRESS: 0", flush=True)
    
    results_dict = {{}}
    completed = 0
    import threading
    progress_lock = threading.Lock()
    chunk_progress = {{i: 0.0 for i in range(total_chunks)}}
    total_audio_duration = sum(e - s for s, e in ISLANDS) if total_chunks > 0 else 1.0
    
    def process_chunk(idx, start_t, end_t):
        s_idx = int(start_t * 16000)
        e_idx = int(end_t   * 16000)
        chunk_audio = audio_array[s_idx:e_idx]
        if len(chunk_audio) == 0:
            return idx, []
            
        print(f"[Chunked] Island {{idx+1}}/{{total_chunks}}: {{start_t:.2f}}s—{{end_t:.2f}}s")
        segments_gen, info = model.transcribe(
            chunk_audio,
            beam_size={repr(prefs.get('ai_beam_size', 1))},
            patience={repr(prefs.get('ai_patience', 1.0))},
            language={repr(lang) if lang != 'Auto' else 'None'},
            initial_prompt={repr(initial_prompt_str)},
            condition_on_previous_text={repr(prefs.get('ai_condition_on_prev', False))},
            vad_filter={repr(prefs.get('ai_vad_filter', False))},
            temperature={repr(prefs.get('ai_temperature', 0.0))},
            no_speech_threshold={repr(prefs.get('ai_no_speech_threshold', 0.6))},
            log_prob_threshold={repr(prefs.get('ai_logprob_threshold', -1.0))},
            compression_ratio_threshold={repr(prefs.get('ai_compression_ratio_threshold', 2.4))},
            no_repeat_ngram_size={repr(prefs.get('ai_no_repeat_ngram_size', 0))},
            word_timestamps=True{kwargs_str}
        )
        
        segs = []
        for seg in segments_gen:
            with progress_lock:
                chunk_progress[idx] = seg.end
                current_total = sum(chunk_progress.values())
                percent = int((current_total / total_audio_duration) * 100)
                print(f"CHUNK_PROGRESS: {{percent}}", flush=True)

            seg_obj = {{
                "start": seg.start + start_t,
                "end":   seg.end   + start_t,
                "text":  seg.text,
                "words": []
            }}
            if seg.words:
                for w in seg.words:
                    seg_obj["words"].append({{
                        "word":        w.word,
                        "start":       w.start + start_t,
                        "end":         w.end   + start_t,
                        "probability": getattr(w, 'probability', 1.0)
                    }})
            segs.append(seg_obj)
        
        with progress_lock:
            chunk_progress[idx] = end_t - start_t
            current_total = sum(chunk_progress.values())
            percent = int((current_total / total_audio_duration) * 100)
            print(f"CHUNK_PROGRESS: {{percent}}", flush=True)
            
        return idx, segs

    # GPU processes sequentially (fastest due to zero threading overhead, yields 0:35)
    # CPU processes in parallel (scales with cores, yields 3:27 or better)
    if workers == 1 or target_device != "cpu":
        for i, (s, e) in enumerate(ISLANDS):
            c_idx, c_segs = process_chunk(i, s, e)
            results_dict[c_idx] = c_segs
            completed += 1
            print(f"CHUNK_PROGRESS: {{int((completed)/total_chunks*100)}}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {{executor.submit(process_chunk, i, s, e): i for i, (s, e) in enumerate(ISLANDS)}}
            for future in concurrent.futures.as_completed(futures):
                c_idx, c_segs = future.result()
                results_dict[c_idx] = c_segs
                completed += 1
                print(f"CHUNK_PROGRESS: {{int((completed)/total_chunks*100)}}")
            print(f"CHUNK_PROGRESS: {{int(completed/total_chunks*100)}}")

    # Assemble in order
    output_segments = []
    for i in range(total_chunks):
        if i in results_dict and results_dict[i]:
            output_segments.extend(results_dict[i])

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
{'''
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
''' if self.os_doc.is_mac else ""}

libs_dir = {repr(self.libs_dir)}
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

try:
    # --- FASTER-WHISPER NATIVE INTEGRATION ---
    from faster_whisper import WhisperModel
    
    model_size = {repr(model)}
    target_device = {repr(fw_device)}
    target_compute = {repr(compute_type)}
    
    print(f"Loading Faster-Whisper: {{model_size}} on {{target_device}} ({{target_compute}})...")
    
    model = WhisperModel(
        model_size, 
        device=target_device, 
        compute_type=target_compute, 
        {'cpu_threads=4,' if self.os_doc.is_mac else ''}
        num_workers=1,
        download_root={repr(self.models_dir)}
    )

    print("Model Loaded Successfully. Starting STABLE Transcription...")
    
    # Parameters for strict VERBATIM output (STAGE 9: Unchain for phrasal retakes)
    segments_gen, info = model.transcribe(
        {repr(audio_path)}, 
        beam_size={repr(prefs.get('ai_beam_size', 1))},
        patience={repr(prefs.get('ai_patience', 1.0))},
        language={repr(lang) if lang != "Auto" else "None"},
        initial_prompt={repr(initial_prompt_str)},
        condition_on_previous_text={repr(prefs.get('ai_condition_on_prev', False))},
        vad_filter={repr(prefs.get('ai_vad_filter', False))},
        temperature={repr(prefs.get('ai_temperature', 0.0))},
        no_speech_threshold={repr(prefs.get('ai_no_speech_threshold', 0.6))},
        log_prob_threshold={repr(prefs.get('ai_logprob_threshold', -1.0))},
        compression_ratio_threshold={repr(prefs.get('ai_compression_ratio_threshold', 2.4))},
        no_repeat_ngram_size={repr(prefs.get('ai_no_repeat_ngram_size', 0))},
        word_timestamps=True{kwargs_str}
    )
    
    output_segments = []
    total_duration = info.duration
    
    # Iterate over faster-whisper segments generator
    for segment in segments_gen:
        # Calculate percentage based on segment end and total duration
        progress_percent = int((segment.end / total_duration) * 100) if total_duration > 0 else 0
        print(f"CHUNK_PROGRESS: {{progress_percent}}", flush=True)
        
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
                    "probability": getattr(w, 'probability', 1.0)
                }})
        
        output_segments.append(seg_obj)
        print(f"Segment processed: {{segment.start:.2f}}s")

    final_data = {{
        "segments": output_segments,
        "language": getattr(info, 'language', {repr(lang)})
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
        
        log_info(f"Running Whisper Runner (Faster-Whisper). Script: {runner_script_path}")
        
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
                except Exception as e:
                    log_error(f"run_whisper: runner script cleanup failed: {e}")

