#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: osdoc.py
ROLE: Tool Layer / System Abstraction
DESCRIPTION:
Modified to force SELF-CONTAINED mode (v9.0).
- Logs/Configs/Models in install dir.
- FFmpeg detection prioritizes local 'bin' folder (Portable mode).
- VENV detection for Python isolation.
- NEW: Nvidia library detection for Auto-GPU config.
"""

import os
import sys
import platform
import shutil
import logging
import subprocess
import tempfile
import uuid
import json
import hashlib
import ctypes

# ==========================================
# 1. LOGGING & STREAM PROXY
# ==========================================

class ResolveStreamProxy:
    """
    Captures stdout/stderr streams so error messages
    go both to the DaVinci console and the log file.
    """
    def __init__(self, stream, log_func):
        self.stream = stream
        self.log_func = log_func
    
    def write(self, data):
        try:
            txt = data.strip()
            if txt and not txt.startswith("[INFO]") and not txt.startswith("[ERROR]") and "[STDOUT/ERR]" not in txt: 
                self.log_func(f"[STDOUT/ERR] {txt}")
            self.stream.write(data)
        except: 
            pass 
    
    def flush(self):
        try:
            if hasattr(self.stream, 'flush'): self.stream.flush()
        except: pass 
    
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

def log_info(msg):
    logging.info(msg)
    try: print(f"[INFO] {msg}")
    except: pass

def log_error(msg):
    logging.error(msg)
    try: print(f"[ERROR] {msg}", file=sys.__stderr__)
    except: pass

# ==========================================
# 2. OS DOCTOR CLASS
# ==========================================

class OSDoctor:
    def __init__(self):
        """
        Initializes the system doctor.
        Now forces paths to be relative to the installation folder (Self-Contained).
        """
        self.os_type = platform.system()
        self.is_mac = (self.os_type == "Darwin")
        self.is_win = (self.os_type == "Windows")
        self.is_linux = (self.os_type == "Linux")
        
        self.home_dir = os.path.expanduser("~")
        
        # --- SELF-CONTAINED PATH LOGIC ---
        # Instead of using system APPDATA, we use the directory where this script resides.
        self.install_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Force AppData to be the Install Dir
        self.app_data_dir = self.install_dir
        
        # Define internal structure paths
        self.bin_dir = os.path.join(self.install_dir, "bin")
        self.log_file = os.path.join(self.app_data_dir, "badwords_debug.log")
        # Split config: user identity/consent → user.json, app prefs → settings.json
        self.user_file     = os.path.join(self.install_dir, 'user.json')
        self.settings_file = os.path.join(self.install_dir, 'settings.json')
        # Legacy path for one-time migration
        self.legacy_pref_file = os.path.join(self.install_dir, 'pref.json')
        self.saves_dir = os.path.join(self.app_data_dir, "saves")
        
        # Fallback check
        if not os.access(self.install_dir, os.W_OK):
            self.app_data_dir = os.path.join(tempfile.gettempdir(), "BadWords_Fallback")
            self.log_file = os.path.join(self.app_data_dir, "badwords.log")
            self.user_file     = os.path.join(self.app_data_dir, 'user.json')
            self.settings_file = os.path.join(self.app_data_dir, 'settings.json')
            self.legacy_pref_file = os.path.join(self.app_data_dir, 'pref.json')
            try: os.makedirs(self.app_data_dir, exist_ok=True)
            except: pass

        # Init Temp
        self.temp_dir = self._init_smart_temp_dir()
        
        # Init Logging
        self._setup_logging()
        self._log_system_info()
        
        # --- MIGRATE LEGACY CONFIG (pref.json → user.json + settings.json) ---
        self._migrate_legacy_config()
        
        # --- LOAD CONFIG INTO MEMORY (deep-merge with defaults) ---
        self.user_data = self.load_user_data()
        self.settings  = self.load_settings()
        
        # --- ENSURE TELEMETRY UUID IS GENERATED ---
        self._ensure_telemetry_prefs()

    def _get_machine_id(self):
        """Pobiera stabilny, niezmienny identyfikator instalacji systemu operacyjnego (Win/Lin/Mac)."""
        try:
            if self.is_win:
                # Windows: Pobieramy stały MachineGuid z Rejestru
                import winreg
                registry = winreg.HKEY_LOCAL_MACHINE
                address = r"SOFTWARE\Microsoft\Cryptography"
                key = winreg.OpenKey(registry, address, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                winreg.CloseKey(key)
                return str(value)
            
            elif self.is_linux:
                # Linux: Używamy uniwersalnego machine-id z systemd
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
            
            elif self.os_type == "Darwin": 
                # macOS: Natywny IOPlatformUUID z rejestru sprzętowego Apple (ioreg)
                # Nie wywołuje monitów o prywatność jak MAC adres
                result = subprocess.run(
                    ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'], 
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if 'IOPlatformUUID' in line:
                        parts = line.split('=')
                        if len(parts) == 2:
                            return parts[1].strip().strip('"')
                return "mac_fallback_" + str(uuid.getnode())
                
            else:
                return str(uuid.getnode())
        except Exception:
            return "unknown_" + str(uuid.getnode())

    # ==========================
    # CONFIG MIGRATION & LOADERS
    # ==========================

    def _migrate_legacy_config(self):
        """One-time migration: splits legacy pref.json into user.json + settings.json.
        Routes every key dynamically: user identity keys go to user.json, all others to settings.json.
        """
        if not os.path.exists(self.legacy_pref_file):
            return

        try:
            with open(self.legacy_pref_file, 'r', encoding='utf-8') as f:
                legacy = json.load(f)
        except Exception as e:
            log_error(f"Migration: could not read pref.json: {e}")
            return

        import config as _cfg

        user_data = dict(_cfg.DEFAULT_USER_DATA)
        settings  = dict(_cfg.DEFAULT_SETTINGS)

        # Map the one legacy key name that differs from the new schema
        legacy_key_alias = {
            "analytics_uuid":    "uuid",
            "telemetry_allow_geo": "telemetry_geo",
        }

        # Dynamically route every key from the old flat pref.json
        for key, value in legacy.items():
            resolved = legacy_key_alias.get(key, key)
            if resolved in _cfg.DEFAULT_USER_DATA:
                user_data[resolved] = value
            else:
                # Everything else (layout prefs, offsets, model choices, etc.) → settings
                settings[resolved] = value

        # --- Save both new files ---
        try:
            with open(self.user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            log_error(f"Migration: failed to write new config files: {e}")
            return

        # --- Safely delete the legacy file ---
        try:
            os.remove(self.legacy_pref_file)
        except Exception as e:
            log_error(f"Migration: could not remove pref.json: {e}")

        log_info("Config migrated: pref.json → user.json + settings.json")

    def load_user_data(self) -> dict:
        """Loads user.json with self-healing deep-merge against DEFAULT_USER_DATA."""
        import config as _cfg
        defaults = dict(_cfg.DEFAULT_USER_DATA)

        loaded = {}
        if os.path.exists(self.user_file):
            try:
                with open(self.user_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
            except json.JSONDecodeError as e:
                log_error(f"load_user_data: corrupt user.json, using defaults. ({e})")
                loaded = {}

        # Deep-merge: add any keys that were introduced in a new version
        needs_save = False
        for key, default_val in defaults.items():
            if key not in loaded:
                loaded[key] = default_val
                needs_save = True

        if needs_save:
            try:
                with open(self.user_file, 'w', encoding='utf-8') as f:
                    json.dump(loaded, f, indent=4)
                log_info("load_user_data: self-healed missing keys in user.json")
            except Exception as e:
                log_error(f"load_user_data: could not persist self-heal: {e}")

        return loaded

    def load_settings(self) -> dict:
        """Loads settings.json with self-healing deep-merge against DEFAULT_SETTINGS."""
        import config as _cfg
        defaults = dict(_cfg.DEFAULT_SETTINGS)

        loaded = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
            except json.JSONDecodeError as e:
                log_error(f"load_settings: corrupt settings.json, using defaults. ({e})")
                loaded = {}

        # Deep-merge: add any keys that were introduced in a new version
        needs_save = False
        for key, default_val in defaults.items():
            if key not in loaded:
                loaded[key] = default_val
                needs_save = True

        if needs_save:
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(loaded, f, indent=4)
                log_info("load_settings: self-healed missing keys in settings.json")
            except Exception as e:
                log_error(f"load_settings: could not persist self-heal: {e}")

        return loaded

    def _ensure_telemetry_prefs(self):
        """Ensures the anonymous tracking UUID exists in user.json.
        last_pinged_version is handled by the deep-merge loader automatically.
        """
        if not self.user_data.get("uuid"):
            machine_id = self._get_machine_id().encode('utf-8')
            hashed_node = hashlib.sha256(machine_id).hexdigest()
            stable_uuid = str(uuid.UUID(hashed_node[:32]))
            self.user_data["uuid"] = stable_uuid
            try:
                with open(self.user_file, 'w', encoding='utf-8') as f:
                    json.dump(self.user_data, f, indent=4)
            except Exception as e:
                log_error(f"_ensure_telemetry_prefs: cannot write user.json: {e}")

    def get_telemetry_pref(self, key):
        """Reads a telemetry/user preference from the in-memory user_data dict.
        Maps legacy key names used by engine.py to the new schema."""
        key_alias = {
            "analytics_uuid":    "uuid",
            "telemetry_allow_geo": "telemetry_geo",
        }
        resolved = key_alias.get(key, key)
        return self.user_data.get(resolved)

    def set_telemetry_pref(self, key, value):
        """Writes a telemetry/user preference to in-memory user_data and persists to user.json.
        Maps legacy key names used by engine.py to the new schema."""
        key_alias = {
            "analytics_uuid":    "uuid",
            "telemetry_allow_geo": "telemetry_geo",
        }
        resolved = key_alias.get(key, key)
        self.user_data[resolved] = value
        try:
            with open(self.user_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            log_error(f"set_telemetry_pref: cannot write user.json: {e}")

    def set_pref(self, key, value):
        """Universal preference router.
        User identity/consent keys → user.json.
        Everything else (app settings, UI prefs) → settings.json.
        Both in-memory dicts and the respective files are updated.
        """
        import config as _cfg
        if key in _cfg.DEFAULT_USER_DATA:
            self.user_data[key] = value
            try:
                with open(self.user_file, 'w', encoding='utf-8') as f:
                    json.dump(self.user_data, f, indent=4)
                log_info(f"set_pref: '{key}' saved to user.json")
            except Exception as e:
                log_error(f"set_pref: cannot write user.json ({key}): {e}")
        else:
            self.settings[key] = value
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4)
                log_info(f"set_pref: '{key}' saved to settings.json")
            except Exception as e:
                log_error(f"set_pref: cannot write settings.json ({key}): {e}")

    def get_all_prefs(self) -> dict:
        """Returns a merged view of all preferences (user data + settings).
        engine.py and gui.py should call this instead of reading JSON directly.
        Settings keys take precedence over user_data keys if names ever collide.
        """
        merged = {}
        merged.update(self.user_data)
        merged.update(self.settings)
        return merged

    def save_all_prefs(self, prefs_dict: dict):
        """Bulk preference router: routes each key to user.json or settings.json.
        engine.py and gui.py should call this instead of writing JSON directly.
        """
        import config as _cfg
        user_modified    = False
        settings_modified = False

        for key, value in prefs_dict.items():
            if not isinstance(key, str):
                log_error(f"save_all_prefs: Filtered out invalid non-string key: {type(key)}")
                continue

            if key in _cfg.DEFAULT_USER_DATA:
                self.user_data[key] = value
                user_modified = True
            else:
                self.settings[key] = value
                settings_modified = True

        if user_modified:
            try:
                with open(self.user_file, 'w', encoding='utf-8') as f:
                    json.dump(self.user_data, f, indent=4)
                log_info("save_all_prefs: user.json updated")
            except Exception as e:
                log_error(f"save_all_prefs: cannot write user.json: {e}")

        if settings_modified:
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4)
                log_info("save_all_prefs: settings.json updated")
            except Exception as e:
                log_error(f"save_all_prefs: cannot write settings.json: {e}")

    def _init_smart_temp_dir(self):
        """
        Determines the best location for heavy temporary files (Audio Renders).
        """
        # Linux Resolve visibility fix: Use Videos/Documents if possible
        if self.is_linux:
            home = os.path.expanduser("~")
            
            # Priority 1: ~/Videos/BadWords_Temp
            videos = os.path.join(home, "Videos")
            if os.path.exists(videos):
                path = os.path.join(videos, "BadWords_Temp")
            else:
                # Priority 2: In App Folder (Portable)
                path = os.path.join(self.app_data_dir, "temp")
            
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except:
                pass
        
        # Windows/Mac Default
        return os.path.join(self.app_data_dir, "temp")

    def _setup_logging(self):
        """Configures logging to file and stream redirection."""
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        try:
            logging.basicConfig(
                filename=self.log_file,
                filemode='a',
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        except PermissionError:
             print(f"CRITICAL: Cannot write to log file {self.log_file}. Logging disabled.")
        
        sys.stdout = ResolveStreamProxy(sys.__stdout__, logging.info)
        sys.stderr = ResolveStreamProxy(sys.__stderr__, logging.error)

    def _log_system_info(self):
        """Logs detailed system information for debugging."""
        log_info("="*30)
        log_info(f"BadWords Session Started (v9.0 Portable)")
        log_info(f"OS: {self.os_type} {platform.release()}")
        log_info(f"Install Dir: {self.install_dir}")
        log_info(f"Bin Dir (FFmpeg): {self.bin_dir}")
        log_info(f"VENV Python: {self.get_venv_python_path()}")
        log_info(f"NVIDIA Support Detected: {self.has_nvidia_support()}")
        log_info("="*30)

    # ==========================
    # PATHS & RESOLVE API
    # ==========================

    def get_resolve_api_path(self) -> str:
        """Returns the standard path for DaVinci Resolve Scripting API modules."""
        paths = []
        if self.is_mac:
            paths.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
        elif self.is_win:
            paths.append(os.path.join(
                os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                "Blackmagic Design", "DaVinci Resolve", "Support",
                "Developer", "Scripting", "Modules"
            ))
        elif self.is_linux:
            paths.append("/opt/resolve/Developer/Scripting/Modules")
            
        for p in paths:
            if os.path.exists(p):
                return p
                
        # Fallback to environment variables if paths don't exist
        env_paths = [
            os.environ.get("RESOLVE_SCRIPT_API"),
            os.environ.get("RESOLVE_SCRIPT_LIB")
        ]
        for p in env_paths:
            if p and os.path.exists(p):
                return os.path.dirname(p) if os.path.isfile(p) else p
                
        return paths[0] if paths else ""

    def get_ffmpeg_cmd(self):
        """
        Returns FFmpeg command.
        PRIORITY: Local 'bin' folder > System PATH.
        Now with explicit logging of source.
        """
        # 1. Check Portable Bin Folder (Created by Installer)
        portable_ffmpeg = os.path.join(self.bin_dir, "ffmpeg")
        if self.is_win: portable_ffmpeg += ".exe"
        
        if os.path.exists(portable_ffmpeg):
            # Verify execution permission on Linux
            if self.is_linux and not os.access(portable_ffmpeg, os.X_OK):
                try: os.chmod(portable_ffmpeg, 0o755)
                except: pass
            log_info(f"[FFMPEG] Using Portable Binary: {portable_ffmpeg}")
            return portable_ffmpeg
        
        # 2. Check Local User Bin (Legacy)
        if self.is_linux:
            local_bin = os.path.expanduser("~/.local/bin/ffmpeg")
            if os.path.exists(local_bin): 
                log_info(f"[FFMPEG] Using Legacy Local Binary: {local_bin}")
                return local_bin
            
        # 3. System PATH fallback
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            log_info(f"[FFMPEG] Using System Binary: {sys_ffmpeg}")
            return sys_ffmpeg
        
        log_error("[FFMPEG] Critical: FFmpeg not found anywhere.")
        return None

    def get_subprocess_kwargs(self) -> dict:
        """
        Returns cross-platform subprocess kwargs, abstracting Windows startupinfo.
        """
        if self.is_win:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            return {"startupinfo": si}
        return {}

    def force_dark_titlebar(self, window_id: int):
        """Forces the native Windows title bar to dark mode via DWM API."""
        if not self.is_win:
            return
        try:
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            # Try attribute 20 (Windows 10 20H1 and newer)
            res = set_window_attribute(window_id, 20, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int))
            if res != 0:
                # Try attribute 19 for older Windows 10 versions
                set_window_attribute(window_id, 19, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int))
        except Exception:
            pass

    # ==========================
    # FILE MANAGEMENT
    # ==========================

    def get_temp_folder(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        return self.temp_dir
        
    def get_saves_folder(self):
        os.makedirs(self.saves_dir, exist_ok=True)
        return self.saves_dir
        
    def get_icon_path(self):
        """
        Returns the path to the branding icon based on the OS.
        Windows uses .ico, Linux/Mac uses .png.
        """
        icon_file = "icon.ico" if self.is_win else "icon.png"
        icon_path = os.path.join(self.install_dir, icon_file)
        
        if os.path.exists(icon_path):
            return icon_path
        return None

    def cleanup_temp(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
        except: pass

    # ==========================
    # VENV & DEPENDENCY CHECKING
    # ==========================

    def get_venv_python_path(self):
        """
        Returns the path to the Isolated VENV Python executable.
        """
        # --- WINDOWS VENV FIX ---
        if self.is_win:
            # Check for standard venv structure on Windows: venv\Scripts\python.exe
            venv_python = os.path.join(self.install_dir, "venv", "Scripts", "python.exe")
            if os.path.exists(venv_python):
                return venv_python
            
            # Fallback (Should typically not be reached if installed correctly)
            return "python"
        
        # --- LINUX VENV FIX ---
        # In Self-Contained mode, VENV is inside install_dir
        venv_python = os.path.join(self.install_dir, "venv", "bin", "python3")
        
        if os.path.exists(venv_python): return venv_python
        
        # Fallback to system python
        return sys.executable

    def check_dependencies(self):
        """
        Checks dependencies via file existence (avoids import crashes).
        """
        missing = []
        
        # Check FFmpeg
        if not self.get_ffmpeg_cmd():
            missing.append("FFmpeg")
            
        # Check Faster-Whisper
        fw_found = False
        
        if self.is_win:
            try: import faster_whisper; fw_found = True # type: ignore
            except: pass
        else:
            # Check VENV content
            venv_lib = os.path.join(self.install_dir, "venv", "lib")
            if os.path.exists(venv_lib):
                py_dirs = [d for d in os.listdir(venv_lib) if d.startswith("python")]
                if py_dirs:
                    site_pkgs = os.path.join(venv_lib, py_dirs[0], "site-packages", "faster_whisper")
                    if os.path.exists(site_pkgs): fw_found = True
            
            # Fallback (libs symlink)
            if not fw_found:
                 libs_path = os.path.join(self.install_dir, "libs", "faster_whisper")
                 if os.path.exists(libs_path): fw_found = True

        if not fw_found:
            missing.append("faster-whisper (files missing in venv)")
            
        return missing

    def has_nvidia_support(self):
        """
        Checks if physical NVIDIA hardware is present AND libraries are installed.
        Used by GUI and Engine to determine if 'GPU' mode is safe.
        """
        # 1. Weryfikacja sprzętowa (Cross-platform z ukryciem konsoli na Win)
        has_hardware = False
        try:
            subprocess.run(
                ['nvidia-smi'], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True,
                **self.get_subprocess_kwargs()
            )
            has_hardware = True
        except Exception:
            has_hardware = False

        if not has_hardware:
            return False

        if self.is_win:
            return True # Na Windowsie polegamy na sterownikach systemowych, jeśli karta istnieje
            
        # 2. Weryfikacja bibliotek (Linux)
        libs_path = os.path.join(self.install_dir, "libs")
        cublas_path = os.path.join(libs_path, "nvidia", "cublas")
        
        return os.path.exists(cublas_path)

    def needs_manual_model_install(self):
        """
        Forces model verification/download step on all operating systems.
        HuggingFace hub will quickly skip the download if the model is already cached.
        """
        return True