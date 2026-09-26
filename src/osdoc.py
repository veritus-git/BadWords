#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: osdoc.py
ROLE: Core Module
DESCRIPTION:
File management and project document structure system.
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
        self._buffer = ""
    
    def write(self, data):
        try:
            self._buffer += data
            if "\n" in self._buffer:
                lines = self._buffer.split("\n")
                self._buffer = lines.pop()
                for line in lines:
                    txt = line.rstrip("\r\n")
                    if txt and not txt.startswith("[INFO]") and not txt.startswith("[ERROR]") and "[STDOUT/ERR]" not in txt:
                        self.log_func(f"[STDOUT/ERR] {txt}")
            self.stream.write(data)
        except Exception:
            pass  # StreamProxy: celowe wyciszenie błędów logowania (nie możemy logować błędu loggera)
    
    def flush(self):
        try:
            if self._buffer:
                txt = self._buffer.rstrip("\r\n")
                if txt and not txt.startswith("[INFO]") and not txt.startswith("[ERROR]") and "[STDOUT/ERR]" not in txt:
                    self.log_func(f"[STDOUT/ERR] {txt}")
                self._buffer = ""
            if hasattr(self.stream, 'flush'): self.stream.flush()
        except Exception:
            pass  # StreamProxy: flush może nie być obsługiwany przez wszystkie streamy
    
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

def log_info(msg):
    logging.info(msg)
    try:
        print(f"[INFO] {msg}")
        sys.stdout.flush()
    except Exception:
        pass  # log_info: wyciszamy tylko błędy wypisywania na konsolę (logowanie do pliku już się udało)

def log_error(msg):
    logging.error(msg)
    try:
        print(f"[ERROR] {msg}", file=sys.__stderr__)
        sys.__stderr__.flush()
    except Exception:
        pass  # log_error: wyciszamy tylko błędy wypisywania na konsolę (logowanie do pliku już się udało)

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
            except Exception as e:
                log_error(f"OSDoctor: nie można utworzyć katalogu fallback AppData: {e}")

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

    def is_legacy_updater_migration(self) -> bool:
        """Check if this is an upgrade that occurred via legacy 3.x updater.py,
        meaning native launchers, desktop integration, or the new installer are missing.
        Returns False if installed via the new installer or marker exists."""
        dirs_to_check = [self.install_dir, os.path.dirname(self.install_dir)]
        for d in dirs_to_check:
            marker = os.path.join(d, '.v4_migration_notified')
            if os.path.isfile(marker):
                return False

        # Check if the new installer or native desktop launchers exist
        for d in dirs_to_check:
            if self.is_win:
                has_launcher = os.path.isfile(os.path.join(d, 'BadWords.exe'))
                has_installer = os.path.isfile(os.path.join(d, 'uninstall.exe'))
            elif getattr(self, 'is_mac', False) or self.os_type == 'Darwin':
                has_launcher = os.path.isdir(os.path.join(d, 'BadWords.app'))
                has_installer = os.path.isfile(os.path.join(d, 'badwords-installer'))
            else:
                has_launcher = os.path.isfile(os.path.join(d, 'BadWords'))
                has_installer = os.path.isfile(os.path.join(d, 'badwords-installer'))

            if has_launcher or has_installer:
                return False

        return True

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

        # Upgrading from 3.x requires a one-time milestone notice ONLY if updated via legacy updater
        if self.is_legacy_updater_migration():
            settings['v4_migration_notified'] = False
        else:
            settings['v4_migration_notified'] = True

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

        # Force migration for AI parameters for versions < 3.1.0
        current_version = getattr(_cfg, "VERSION", "3.1.0")
        saved_version = loaded.get("settings_version", "0.0.0")
        
        def version_tuple(v):
            try:
                clean_v = ''.join(c if c.isdigit() or c == '.' else '' for c in v)
                return tuple(map(int, (clean_v.split(".") + ["0", "0"])[:3]))
            except Exception:
                return (0, 0, 0)
                
        needs_save = False
        
        if loaded and version_tuple(saved_version) < version_tuple("3.1.0"):
            log_info(f"Migrating AI settings from {saved_version} to {current_version} (forcing new optimized defaults)")
            loaded["ai_compression_ratio_threshold"] = 2.4
            loaded["ai_no_speech_threshold"] = 0.7
            loaded["ai_logprob_threshold"] = -0.8
            loaded["ai_initial_prompt"] = ""
            loaded["settings_version"] = current_version
            needs_save = True

        # Force migration for default system fonts and milestone notice when upgrading from v3.x
        if loaded and version_tuple(saved_version) < version_tuple("4.0.0"):
            old_font = loaded.get("editor_font_family", "")
            legacy_default_fonts = {"Segoe UI", "Segoe UI Variable", "Segoe UI Variable Display", "Noto Sans", "Ubuntu", "Helvetica Neue", "Arial", "sans-serif", "Sans"}
            if old_font in legacy_default_fonts or not old_font:
                new_font = _cfg.DEFAULT_SETTINGS.get("editor_font_family", "Ubuntu Sans")
                if old_font != new_font:
                    log_info(f"Migrating default editor_font_family from '{old_font}' to '{new_font}' (v3 -> v4 upgrade)")
                    loaded["editor_font_family"] = new_font
                    needs_save = True

            if self.is_legacy_updater_migration():
                loaded["v4_migration_notified"] = False
                needs_save = True
            else:
                loaded["v4_migration_notified"] = True
            
        if loaded.get("settings_version") != current_version:
            loaded["settings_version"] = current_version
            needs_save = True

        # Remove lingering telemetry keys from settings if present (they belong exclusively in user.json)
        for key_to_remove in ("telemetry_opt_in", "telemetry_geo"):
            if key_to_remove in loaded:
                loaded.pop(key_to_remove, None)
                needs_save = True

        # Deep-merge: add any keys that were introduced in a new version
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
            except Exception as e:
                log_error(f"_init_smart_temp_dir: nie można utworzyć katalogu temp {path}: {e}")
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
        log_info(f"BadWords Session Started")
        log_info(f"OS: {self.os_type} {platform.release()}")
        log_info(f"Install Dir: {self.install_dir}")
        log_info(f"Bin Dir (FFmpeg): {self.bin_dir}")
        log_info(f"VENV Python: {self.get_venv_python_path()}")
        log_info(f"NVIDIA Support Detected: {self.has_nvidia_support()}")
        try:
            topo = self.get_cpu_topology()
            if topo.get("is_apple_silicon"):
                log_info(f"CPU Topology: {topo.get('chip_name', 'Apple Silicon')} (P-cores: {topo.get('p_cores')}, E-cores: {topo.get('e_cores')}, Rosetta: {topo.get('is_rosetta')})")
            else:
                log_info(f"CPU Topology: {topo.get('chip_name', platform.machine())} (Physical: {topo.get('physical_cores')}, Logical: {topo.get('logical_cores')})")
        except Exception:
            pass
        log_info("="*30)

    # ==========================
    # PATHS & RESOLVE API
    # ==========================

    def get_resolve_api_path(self) -> str:
        """Returns the standard path for DaVinci Resolve Scripting API modules and exports env vars."""
        paths = []
        if self.is_mac:
            paths.extend([
                "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
                "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/Modules",
                "/Applications/DaVinci Resolve Studio/DaVinci Resolve.app/Contents/Libraries/Fusion/Modules",
                "/Applications/DaVinci Resolve Studio/DaVinci Resolve Studio.app/Contents/Libraries/Fusion/Modules",
            ])
            if "RESOLVE_SCRIPT_LIB" not in os.environ:
                candidates = [
                    "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
                    "/Applications/DaVinci Resolve Studio/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
                    "/Applications/DaVinci Resolve Studio/DaVinci Resolve Studio.app/Contents/Libraries/Fusion/fusionscript.so",
                    "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Libraries/fusionscript.so",
                ]
                for c in candidates:
                    if os.path.exists(c):
                        os.environ["RESOLVE_SCRIPT_LIB"] = c
                        break
            if "RESOLVE_SCRIPT_API" not in os.environ:
                api_dir = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
                if os.path.isdir(api_dir):
                    os.environ["RESOLVE_SCRIPT_API"] = api_dir

        elif self.is_win:
            paths.append(os.path.join(
                os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                "Blackmagic Design", "DaVinci Resolve", "Support",
                "Developer", "Scripting", "Modules"
            ))
            if "RESOLVE_SCRIPT_LIB" not in os.environ:
                c = "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll"
                if os.path.exists(c):
                    os.environ["RESOLVE_SCRIPT_LIB"] = c

        elif self.is_linux:
            paths.extend([
                "/opt/resolve/Developer/Scripting/Modules",
                "/opt/resolve/libs/Fusion/Modules",
            ])
            if "RESOLVE_SCRIPT_LIB" not in os.environ:
                c = "/opt/resolve/libs/Fusion/fusionscript.so"
                if os.path.exists(c):
                    os.environ["RESOLVE_SCRIPT_LIB"] = c
            if "RESOLVE_SCRIPT_API" not in os.environ:
                api_dir = "/opt/resolve/Developer/Scripting"
                if os.path.isdir(api_dir):
                    os.environ["RESOLVE_SCRIPT_API"] = api_dir
            
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

    def get_resolve_installation_info(self) -> dict:
        """
        Detects installed DaVinci Resolve edition (Studio vs Free) and version.
        Returns:
            dict with keys:
                installed (bool)
                edition ('Studio' | 'Free' | 'Unknown')
                version (str, e.g. '21.1.0')
                version_tuple (tuple, e.g. (21, 1, 0))
                is_21_1_or_newer (bool)
        """
        if hasattr(self, '_resolve_installation_info') and self._resolve_installation_info is not None:
            return dict(self._resolve_installation_info)

        info = {
            "installed": False,
            "edition": "Unknown",
            "version": "",
            "version_tuple": (0, 0, 0),
            "is_21_1_or_newer": False,
        }

        if self.is_win:
            try:
                import winreg
                for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    for subkey in (
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                    ):
                        try:
                            key = winreg.OpenKey(hkey, subkey)
                        except OSError:
                            continue
                        try:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    sub_name = winreg.EnumKey(key, i)
                                    sub_key = winreg.OpenKey(key, sub_name)
                                    disp_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                    if "DaVinci Resolve" in disp_name:
                                        info["installed"] = True
                                        info["edition"] = "Studio" if "Studio" in disp_name else "Free"
                                        try:
                                            ver, _ = winreg.QueryValueEx(sub_key, "DisplayVersion")
                                            info["version"] = ver
                                        except OSError:
                                            pass
                                        winreg.CloseKey(sub_key)
                                        break
                                    winreg.CloseKey(sub_key)
                                except (OSError, ValueError):
                                    continue
                        finally:
                            winreg.CloseKey(key)
                        if info["installed"]:
                            break
                    if info["installed"]:
                        break
            except Exception as e:
                log_warn(f"get_resolve_installation_info registry error: {e}")

            exe_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
            if os.path.isfile(exe_path):
                info["installed"] = True
                if not info["version"]:
                    try:
                        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                               f"(Get-Item -LiteralPath '{exe_path}').VersionInfo.ProductVersion"]
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, **self.get_subprocess_kwargs())
                        if res.returncode == 0 and res.stdout.strip():
                            info["version"] = res.stdout.strip()
                    except Exception:
                        pass
                if info["edition"] == "Unknown":
                    try:
                        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                               f"(Get-Item -LiteralPath '{exe_path}').VersionInfo.ProductName"]
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, **self.get_subprocess_kwargs())
                        if res.returncode == 0 and res.stdout.strip():
                            prod_name = res.stdout.strip()
                            info["edition"] = "Studio" if "Studio" in prod_name else "Free"
                    except Exception:
                        pass

        elif self.is_mac:
            candidate_apps = [
                ("/Applications/DaVinci Resolve Studio/DaVinci Resolve Studio.app", "Studio"),
                ("/Applications/DaVinci Resolve Studio.app", "Studio"),
                ("/Applications/DaVinci Resolve/DaVinci Resolve.app", "Free"),
                ("/Applications/DaVinci Resolve.app", "Free"),
            ]
            chosen_app = None
            for app_path, ed in candidate_apps:
                if os.path.isdir(app_path):
                    info["installed"] = True
                    info["edition"] = ed
                    chosen_app = app_path
                    break

            if chosen_app:
                plist_path = os.path.join(chosen_app, "Contents", "Info.plist")
                if os.path.isfile(plist_path):
                    try:
                        import plistlib
                        with open(plist_path, "rb") as f:
                            pl = plistlib.load(f)
                            info["version"] = str(pl.get("CFBundleShortVersionString") or pl.get("CFBundleVersion") or "")
                            bid = str(pl.get("CFBundleIdentifier") or "").lower()
                            dname = str(pl.get("CFBundleDisplayName") or pl.get("CFBundleName") or "").lower()
                            if "studio" in bid or "studio" in dname:
                                info["edition"] = "Studio"
                            elif "resolve" in bid or "resolve" in dname:
                                info["edition"] = "Free"
                    except Exception as e:
                        log_warn(f"Failed to read Info.plist: {e}")

        elif self.is_linux:
            resolve_bin = "/opt/resolve/bin/resolve"
            if os.path.isfile(resolve_bin):
                info["installed"] = True

                # 1. Check documentation files in /opt/resolve/docs/
                for doc_name in ("ReadMe.html", "Welcome.txt", "License.html"):
                    doc_path = os.path.join("/opt/resolve/docs", doc_name)
                    if os.path.isfile(doc_path):
                        try:
                            with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
                                doc_content = f.read(65536)
                            import re
                            if re.search(r"DaVinci\s+Resolve\s+Studio", doc_content, re.IGNORECASE):
                                info["edition"] = "Studio"
                            elif info["edition"] == "Unknown" and re.search(r"DaVinci\s+Resolve", doc_content, re.IGNORECASE):
                                info["edition"] = "Free"

                            if not info["version"]:
                                vm = re.search(r"DaVinci\s+Resolve(?:\s+Studio)?\s+(?:Version\s+)?(\d+(?:\.\d+)+)", doc_content, re.IGNORECASE)
                                if vm:
                                    info["version"] = vm.group(1)
                        except Exception:
                            pass
                        if info["edition"] == "Studio" and info["version"]:
                            break

                # 2. Check desktop application files (.desktop)
                if info["edition"] != "Studio":
                    desktop_dirs = [
                        "/usr/share/applications",
                        "/usr/local/share/applications",
                        os.path.expanduser("~/.local/share/applications"),
                    ]
                    for d_dir in desktop_dirs:
                        if not os.path.isdir(d_dir):
                            continue
                        try:
                            for fname in os.listdir(d_dir):
                                if "resolve" in fname.lower() or "davinci" in fname.lower():
                                    fpath = os.path.join(d_dir, fname)
                                    if os.path.isfile(fpath):
                                        try:
                                            with open(fpath, "r", encoding="utf-8", errors="ignore") as df:
                                                df_content = df.read(16384)
                                            import re
                                            if re.search(r"Name=.*DaVinci\s+Resolve\s+Studio", df_content, re.IGNORECASE) or "resolve-studio" in fname.lower() or "studio" in fname.lower():
                                                info["edition"] = "Studio"
                                                break
                                        except Exception:
                                            pass
                        except Exception:
                            pass
                        if info["edition"] == "Studio":
                            break

                # 3. Check native Linux package managers (RPM on Fedora/RHEL/openSUSE, Pacman on Arch, DPKG on Debian/Ubuntu)
                if info["edition"] != "Studio":
                    if shutil.which("rpm"):
                        try:
                            res = subprocess.run(["rpm", "-qa", "*resolve*", "*davinci*"], capture_output=True, text=True, timeout=2, **self.get_subprocess_kwargs())
                            if "studio" in (res.stdout or "").lower():
                                info["edition"] = "Studio"
                        except Exception:
                            pass

                    if info["edition"] != "Studio" and shutil.which("pacman"):
                        try:
                            res = subprocess.run(["pacman", "-Qs", "resolve"], capture_output=True, text=True, timeout=2, **self.get_subprocess_kwargs())
                            if res.returncode == 0 and "studio" in (res.stdout or "").lower():
                                info["edition"] = "Studio"
                        except Exception:
                            pass

                    if info["edition"] != "Studio" and shutil.which("dpkg"):
                        try:
                            res = subprocess.run(["dpkg", "-l", "*resolve*", "*davinci*"], capture_output=True, text=True, timeout=2, **self.get_subprocess_kwargs())
                            if res.returncode == 0 and "studio" in (res.stdout or "").lower():
                                info["edition"] = "Studio"
                        except Exception:
                            pass

                # 4. Check resolve -v output (definitive CLI inspection)
                if info["edition"] != "Studio" or not info["version"]:
                    try:
                        res = subprocess.run([resolve_bin, "-v"], capture_output=True, text=True, timeout=2, **self.get_subprocess_kwargs())
                        out = (res.stdout or "") + " " + (res.stderr or "")
                        if "studio" in out.lower():
                            info["edition"] = "Studio"
                        elif info["edition"] == "Unknown" and "davinci resolve" in out.lower():
                            info["edition"] = "Free"

                        if not info["version"]:
                            import re
                            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", out)
                            if m:
                                info["version"] = m.group(1)
                    except Exception:
                        pass

                # 5. Check license directory (.license with files)
                if info["edition"] != "Studio":
                    lic_dir = "/opt/resolve/.license"
                    if os.path.isdir(lic_dir):
                        try:
                            if any(not f.startswith('.') for f in os.listdir(lic_dir)):
                                info["edition"] = "Studio"
                        except Exception:
                            pass

        # Default unknown edition to "Free" if Resolve is installed or utility dirs exist
        if info["edition"] == "Unknown":
            if info["installed"]:
                info["edition"] = "Free"
            else:
                util_dirs = self.get_resolve_script_utility_dirs()
                if any(os.path.isdir(d) for d in util_dirs):
                    info["edition"] = "Free"

        # Parse version tuple
        if info["version"]:
            import re
            nums = re.findall(r"\d+", info["version"])
            if nums:
                t = tuple(int(x) for x in nums[:3])
                while len(t) < 3:
                    t = t + (0,)
                info["version_tuple"] = t
                info["is_21_1_or_newer"] = t >= (21, 1, 0)

        self._resolve_installation_info = dict(info)
        return info

    def get_resolve_script_utility_dirs(self) -> list:
        """Returns candidate Fusion/Scripts/Utility directories on this machine."""
        dirs = []
        if self.is_win:
            for env_var in ("APPDATA", "PROGRAMDATA"):
                base = os.environ.get(env_var)
                if base:
                    dirs.append(os.path.join(base, "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion", "Scripts", "Utility"))
                    dirs.append(os.path.join(base, "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
        elif self.is_mac:
            dirs.append(os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
            dirs.append(os.path.join("/Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
        elif self.is_linux:
            dirs.append(os.path.join(os.path.expanduser("~"), ".local", "share", "DaVinciResolve", "Fusion", "Scripts", "Utility"))
            dirs.append(os.path.join("/opt", "resolve", "libs", "Fusion", "Scripts", "Utility"))
            dirs.append(os.path.join("/opt", "resolve", "Fusion", "Scripts", "Utility"))

        unique = []
        for d in dirs:
            if d not in unique:
                unique.append(d)
        return unique

    def generate_davinci_wrapper_content(self) -> str:
        """Generates cross-platform BadWords.py wrapper script for DaVinci Resolve."""
        install_str = self.install_dir.replace('\\', '/')
        libs_str = os.path.join(self.install_dir, 'libs').replace('\\', '/')
        main_script = os.path.join(self.install_dir, 'main.py').replace('\\', '/')
        return f'''\
import sys, os, traceback

INSTALL_DIR = r'{install_str}'
MAIN_SCRIPT = r'{main_script}'

# 1. Discover all site-packages candidates (venv direct paths + libs symlink/junction)
_candidates = [
    r'{libs_str}',
    os.path.join(INSTALL_DIR, "libs"),
    os.path.join(INSTALL_DIR, "venv", "Lib", "site-packages"),
]

_v_lib = os.path.join(INSTALL_DIR, "venv", "lib")
if os.path.isdir(_v_lib):
    try:
        for _entry in os.listdir(_v_lib):
            _sp = os.path.join(_v_lib, _entry, "site-packages")
            if os.path.isdir(_sp) and _sp not in _candidates:
                _candidates.append(_sp)
    except Exception:
        pass

for _sp_dir in _candidates:
    if os.path.isdir(_sp_dir):
        if _sp_dir in sys.path:
            sys.path.remove(_sp_dir)
        sys.path.insert(0, _sp_dir)

if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

# 2. Windows: register DLL search paths for PySide6 and shiboken6
if sys.platform.startswith('win') and hasattr(os, 'add_dll_directory'):
    for _sp_dir in _candidates:
        if os.path.isdir(_sp_dir):
            for _pkg in ['PySide6', 'shiboken6']:
                _p = os.path.join(_sp_dir, _pkg)
                if os.path.isdir(_p):
                    try: os.add_dll_directory(_p)
                    except Exception: pass

# 3. Linux: Preload Qt6 shared libraries if needed
if sys.platform.startswith('linux'):
    import ctypes
    for _sp_dir in _candidates:
        _qt_lib_dir = os.path.join(_sp_dir, "PySide6", "Qt", "lib")
        if os.path.isdir(_qt_lib_dir):
            _qt_preload = [
                'libQt6Core.so.6','libQt6Network.so.6','libQt6DBus.so.6',
                'libQt6Gui.so.6','libQt6Widgets.so.6','libQt6OpenGL.so.6','libQt6XcbQpa.so.6',
            ]
            for _lib in _qt_preload:
                _p = os.path.join(_qt_lib_dir, _lib)
                if os.path.exists(_p):
                    try: ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                    except OSError: pass
            break

# 4. Launch main script in-process (preserves DaVinci Resolve Free API connection)
if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, encoding='utf-8') as f: code = f.read()
        gv = globals().copy()
        gv['__file__'] = MAIN_SCRIPT
        exec(code, gv)
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
else:
    print("CRITICAL: script not found at", MAIN_SCRIPT)
'''

    def sync_resolve_scripts(self, force: bool = False) -> None:
        """
        Auto-healing: ensures the correct scripts are installed in DaVinci Resolve.
        - DaVinci Resolve Studio:
            * BadWords.py MUST be installed (uses native external scripting).
            * BadWords Bridge.lua MUST NOT be installed (removed if present).
        - DaVinci Resolve Free:
            * BadWords Bridge.lua MUST ALWAYS be installed!
            * If Free >= 21.1: BadWords.py MUST BE REMOVED (Blackmagic blocked external API).
            * If Free < 21.1: BadWords.py CAN / SHOULD be installed.
        """
        try:
            info = self.get_resolve_installation_info()
            util_dirs = self.get_resolve_script_utility_dirs()
            if not util_dirs:
                return

            is_studio = (info["edition"] == "Studio")
            is_free_21_1 = (not is_studio and info["is_21_1_or_newer"])

            # Robustly locate BadWords Bridge.lua source across all layouts
            lua_src = None
            for cand in [
                os.path.join(self.install_dir, "setupfiles", "BadWords Bridge.lua"),
                os.path.join(self.install_dir, "BadWords Bridge.lua"),
                os.path.join(os.path.dirname(self.install_dir), "setupfiles", "BadWords Bridge.lua"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setupfiles", "BadWords Bridge.lua"),
                getattr(self, 'resources_dir', '') and os.path.join(getattr(self, 'resources_dir', ''), "setupfiles", "BadWords Bridge.lua"),
            ]:
                if cand and os.path.isfile(cand):
                    lua_src = cand
                    break

            wrapper_content = self.generate_davinci_wrapper_content()

            if is_studio:
                # ── STUDIO EDITION ─────────────────────────────────────────────────────────────
                # 1. BadWords Bridge.lua is NOT needed and MUST NOT be installed. Remove if present.
                # 2. BadWords.py MUST be installed for native scripting.
                log_info(f"[Resolve Sync] Detected Studio edition (v{info.get('version', 'unknown')}). Removing Bridge.lua, ensuring BadWords.py.")
                for ud in util_dirs:
                    if not os.path.isdir(ud):
                        continue
                    lua_file = os.path.join(ud, "BadWords Bridge.lua")
                    if os.path.isfile(lua_file):
                        try:
                            os.remove(lua_file)
                            log_info(f"[Resolve Sync] Removed BadWords Bridge.lua from Studio setup: {lua_file}")
                        except Exception as e:
                            log_warn(f"[Resolve Sync] Could not remove {lua_file}: {e}")

                py_deployed = False
                for ud in util_dirs:
                    if not os.path.isdir(ud):
                        try: os.makedirs(ud, exist_ok=True)
                        except Exception: continue
                    py_file = os.path.join(ud, "BadWords.py")
                    if not py_deployed:
                        try:
                            should_write = force or not os.path.isfile(py_file)
                            if should_write:
                                with open(py_file, "w", encoding="utf-8") as f:
                                    f.write(wrapper_content)
                                try: os.chmod(py_file, 0o755)
                                except Exception: pass
                                log_info(f"[Resolve Sync] Installed BadWords.py for Studio at: {py_file}")
                            py_deployed = True
                        except Exception as e:
                            log_warn(f"[Resolve Sync] Could not write BadWords.py to {ud}: {e}")

            else:
                # ── FREE EDITION (or Unknown) ──────────────────────────────────────────────────
                # 1. BadWords Bridge.lua MUST ALWAYS be installed!
                # 2. BadWords.py:
                #    - If Free >= 21.1: REMOVE BadWords.py (API blocked).
                #    - If Free < 21.1: Ensure BadWords.py is installed.
                log_info(f"[Resolve Sync] Detected Free edition (v{info.get('version', 'unknown')}, is_21_1+={is_free_21_1}). Ensuring Bridge.lua.")

                # Handle BadWords.py
                if is_free_21_1:
                    for ud in util_dirs:
                        if not os.path.isdir(ud):
                            continue
                        py_file = os.path.join(ud, "BadWords.py")
                        if os.path.isfile(py_file):
                            try:
                                os.remove(py_file)
                                log_info(f"[Resolve Sync] Removed BadWords.py for Resolve Free 21.1+: {py_file}")
                            except Exception as e:
                                log_warn(f"[Resolve Sync] Could not remove {py_file}: {e}")
                else:
                    py_deployed = False
                    for ud in util_dirs:
                        if not os.path.isdir(ud):
                            try: os.makedirs(ud, exist_ok=True)
                            except Exception: continue
                        py_file = os.path.join(ud, "BadWords.py")
                        if not py_deployed:
                            try:
                                should_write = force or not os.path.isfile(py_file)
                                if should_write:
                                    with open(py_file, "w", encoding="utf-8") as f:
                                        f.write(wrapper_content)
                                    try: os.chmod(py_file, 0o755)
                                    except Exception: pass
                                    log_info(f"[Resolve Sync] Installed BadWords.py for Free <21.1 at: {py_file}")
                                py_deployed = True
                            except Exception as e:
                                log_warn(f"[Resolve Sync] Could not write BadWords.py to {ud}: {e}")

                # Handle BadWords Bridge.lua (ALWAYS for Free)
                primary_installed = False
                for ud in util_dirs:
                    if not os.path.isdir(ud):
                        try: os.makedirs(ud, exist_ok=True)
                        except Exception: continue

                    lua_file = os.path.join(ud, "BadWords Bridge.lua")
                    if lua_src and os.path.isfile(lua_src):
                        if not primary_installed:
                            try:
                                should_copy = force or not os.path.isfile(lua_file)
                                if not should_copy and os.path.isfile(lua_file):
                                    if os.path.getmtime(lua_src) > os.path.getmtime(lua_file):
                                        should_copy = True
                                if should_copy:
                                    shutil.copy2(lua_src, lua_file)
                                    try: os.chmod(lua_file, 0o755)
                                    except Exception: pass
                                    log_info(f"[Resolve Sync] Installed BadWords Bridge.lua for Free at: {lua_file}")
                                primary_installed = True
                            except Exception as e:
                                log_warn(f"[Resolve Sync] Failed to sync BadWords Bridge.lua to {ud}: {e}")
                        else:
                            # Secondary directory: remove duplicate so only 1 entry appears in Resolve menus
                            if os.path.isfile(lua_file):
                                try:
                                    os.remove(lua_file)
                                    log_info(f"[Resolve Sync] Removed duplicate BadWords Bridge.lua from secondary dir: {lua_file}")
                                except Exception: pass
        except Exception as e:
            log_warn(f"sync_resolve_scripts error: {e}")

    def _test_executable(self, cmd_path):
        try:
            # -version exits cleanly if the binary is valid
            subprocess.run([cmd_path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, **self.get_subprocess_kwargs())
            return True
        except Exception:
            return False

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
            # Verify execution permission on Linux and macOS
            if (self.is_linux or self.is_mac) and not os.access(portable_ffmpeg, os.X_OK):
                try: os.chmod(portable_ffmpeg, 0o755)
                except Exception as e:
                    log_error(f"get_ffmpeg_cmd: chmod failed on {portable_ffmpeg}: {e}")
            if self._test_executable(portable_ffmpeg):
                log_info(f"[FFMPEG] Using Portable Binary: {portable_ffmpeg}")
                return portable_ffmpeg
            else:
                log_error(f"[FFMPEG] Portable Binary {portable_ffmpeg} is corrupted or incompatible. Falling back...")
        
        # 2. Check Local User Bin (Legacy)
        if self.is_linux or self.is_mac:
            local_bin = os.path.expanduser("~/.local/bin/ffmpeg")
            if os.path.exists(local_bin) and self._test_executable(local_bin): 
                log_info(f"[FFMPEG] Using Legacy Local Binary: {local_bin}")
                return local_bin
            
        # 3. System PATH fallback
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg and self._test_executable(sys_ffmpeg):
            log_info(f"[FFMPEG] Using System Binary: {sys_ffmpeg}")
            return sys_ffmpeg
        
        log_error("[FFMPEG] Critical: FFmpeg not found anywhere.")
        return None

    def get_subprocess_kwargs(self) -> dict:
        """
        Returns cross-platform subprocess kwargs, abstracting Windows startupinfo.
        Strictly suppresses console window creation on Windows (CREATE_NO_WINDOW + SW_HIDE).
        """
        if self.is_win or os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0x00000001)
            si.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
            cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            return {"startupinfo": si, "creationflags": cf}
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

    def set_always_on_top(self, window_id: int, top: bool) -> bool:
        """
        Sets the window to always on top using native OS API without recreating the Qt window.
        - Windows: SetWindowPos with HWND_TOPMOST / HWND_NOTOPMOST
        - macOS: NSWindow setLevel: NSFloatingWindowLevel (3) & collection behavior
        - Linux (X11): _NET_WM_STATE_ABOVE via XClientMessageEvent
        """
        if self.is_win:
            try:
                import ctypes
                # HWND_TOPMOST = -1, HWND_NOTOPMOST = -2
                # SWP_NOSIZE(1) | SWP_NOMOVE(2) | SWP_NOACTIVATE(0x10) | SWP_FRAMECHANGED(0x20) = 0x0033
                hwnd_insert_after = -1 if top else -2
                flags = 0x0001 | 0x0002 | 0x0010 | 0x0020
                ctypes.windll.user32.SetWindowPos(window_id, hwnd_insert_after, 0, 0, 0, 0, flags)
                return True
            except Exception:
                return False

        elif self.is_mac:
            try:
                import ctypes, ctypes.util
                objc_path = ctypes.util.find_library('objc')
                if not objc_path:
                    return False
                objc = ctypes.cdll.LoadLibrary(objc_path)
                objc.objc_getClass.restype = ctypes.c_void_p
                objc.objc_getClass.argtypes = [ctypes.c_char_p]
                objc.sel_registerName.restype = ctypes.c_void_p
                objc.sel_registerName.argtypes = [ctypes.c_char_p]

                # In Qt on macOS, window_id is an NSView pointer.
                view = ctypes.c_void_p(window_id)
                sel_window = objc.sel_registerName(b"window")
                msgSend_window = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
                nswindow = msgSend_window(view, sel_window)
                if not nswindow:
                    nswindow = view

                # NSNormalWindowLevel = 0, NSFloatingWindowLevel = 3
                sel_setLevel = objc.sel_registerName(b"setLevel:")
                msgSend_setLevel = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long))
                level = ctypes.c_long(3 if top else 0)
                msgSend_setLevel(nswindow, sel_setLevel, level)

                # Ensure collection behavior allows floating across desktop spaces
                sel_setBehavior = objc.sel_registerName(b"setCollectionBehavior:")
                msgSend_setBehavior = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong))
                # NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0, NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8
                behavior = ctypes.c_ulong((1 << 0) | (1 << 8) if top else 0)
                msgSend_setBehavior(nswindow, sel_setBehavior, behavior)
                return True
            except Exception:
                return False

        elif self.is_linux:
            # 1. Try wmctrl if available (works 100% reliably in Mutter/Cinnamon/KWin/XFCE)
            try:
                import subprocess, shutil
                if shutil.which('wmctrl'):
                    action = "add" if top else "remove"
                    res = subprocess.run(
                        ['wmctrl', '-i', '-r', hex(window_id), '-b', f'{action},above'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    if res.returncode == 0:
                        return True
            except Exception:
                pass

            # 2. Direct X11 ClientMessage fallback via XSendEvent
            try:
                from PySide6.QtGui import QGuiApplication
                if QGuiApplication.platformName() == 'wayland':
                    return False

                import ctypes, ctypes.util
                x11_path = ctypes.util.find_library('X11')
                if not x11_path:
                    return False
                x11 = ctypes.cdll.LoadLibrary(x11_path)
                x11.XOpenDisplay.restype = ctypes.c_void_p
                x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
                display = x11.XOpenDisplay(None)
                if not display:
                    return False

                x11.XDefaultRootWindow.restype = ctypes.c_ulong
                x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
                x11.XInternAtom.restype = ctypes.c_ulong
                x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
                x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
                x11.XFlush.argtypes = [ctypes.c_void_p]
                x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]

                atom_state = x11.XInternAtom(display, b'_NET_WM_STATE', False)
                atom_above = x11.XInternAtom(display, b'_NET_WM_STATE_ABOVE', False)
                root = x11.XDefaultRootWindow(display)

                class XClientMessageEvent(ctypes.Structure):
                    _fields_ = [
                        ('type', ctypes.c_int),
                        ('serial', ctypes.c_ulong),
                        ('send_event', ctypes.c_int),
                        ('display', ctypes.c_void_p),
                        ('window', ctypes.c_ulong),
                        ('message_type', ctypes.c_ulong),
                        ('format', ctypes.c_int),
                        ('data', ctypes.c_long * 5)
                    ]

                class XEvent(ctypes.Union):
                    _fields_ = [
                        ('type', ctypes.c_int),
                        ('xclient', XClientMessageEvent),
                        ('pad', ctypes.c_long * 24)
                    ]

                event = XEvent()
                event.type = 33  # ClientMessage
                event.xclient.type = 33
                event.xclient.serial = 0
                event.xclient.send_event = 1
                event.xclient.display = display
                event.xclient.window = window_id
                event.xclient.message_type = atom_state
                event.xclient.format = 32
                event.xclient.data[0] = 1 if top else 0  # 1 = _NET_WM_STATE_ADD, 0 = _NET_WM_STATE_REMOVE
                event.xclient.data[1] = atom_above
                event.xclient.data[2] = 0
                event.xclient.data[3] = 1
                event.xclient.data[4] = 0

                mask = 0x00180000  # SubstructureRedirectMask | SubstructureNotifyMask
                x11.XSendEvent(display, root, False, mask, ctypes.byref(event))
                x11.XFlush(display)
                x11.XCloseDisplay(display)
                return True
            except Exception:
                return False

        return False

    # ==========================
    # FILE MANAGEMENT
    # ==========================

    def get_temp_folder(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        return self.temp_dir
        
    def get_saves_folder(self):
        os.makedirs(self.saves_dir, exist_ok=True)
        return self.saves_dir

    def get_autosave_dir(self):
        """Returns (and creates) the autosave directory for crash recovery."""
        path = os.path.join(self.saves_dir, "autosave")
        os.makedirs(path, exist_ok=True)
        return path
        
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
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            log_error(f"cleanup_temp: failed to clear temp directory {self.temp_dir}: {e}")

    # ==========================
    # VENV & DEPENDENCY CHECKING
    # ==========================

    def get_venv_python_path(self, prefer_windowless: bool = True):
        """
        Returns the path to the Isolated VENV Python executable.
        On Windows, prefers pythonw.exe (windowless GUI subsystem) when prefer_windowless is True
        to guarantee zero console windows or flashes.
        """
        # --- WINDOWS VENV FIX ---
        if self.is_win:
            venv_scripts = os.path.join(self.install_dir, "venv", "Scripts")
            venv_pythonw = os.path.join(venv_scripts, "pythonw.exe")
            venv_python = os.path.join(venv_scripts, "python.exe")

            if prefer_windowless and os.path.exists(venv_pythonw):
                return venv_pythonw
            if os.path.exists(venv_python):
                return venv_python
            if os.path.exists(venv_pythonw):
                return venv_pythonw
            
            # Fallback (Should typically not be reached if installed correctly)
            if prefer_windowless and shutil.which("pythonw"):
                return "pythonw"
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
            except Exception as e:
                log_error(f"check_dependencies: błąd importu faster_whisper: {e}")
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
        if os.path.exists(cublas_path):
            return True

        try:
            import importlib.util
            if importlib.util.find_spec("nvidia.cublas") is not None:
                return True
        except Exception:
            pass

        return os.path.exists("/usr/local/cuda") or shutil.which("nvcc") is not None

    def needs_manual_model_install(self):
        """
        Forces model verification/download step on all operating systems.
        HuggingFace hub will quickly skip the download if the model is already cached.
        """
        return True

    def get_cpu_topology(self) -> dict:
        """
        Detects CPU topology, specifically handling Apple Silicon asymmetric cores
        (Performance P-cores vs Efficiency E-cores across M1, M2, M3, M4, M5, Pro/Max/Ultra),
        legacy Intel Macs (x86_64), Linux, and Windows.
        """
        import multiprocessing
        logical = multiprocessing.cpu_count() or 1
        topo = {
            "logical_cores": logical,
            "physical_cores": logical,
            "p_cores": logical,
            "e_cores": 0,
            "is_apple_silicon": False,
            "is_rosetta": False,
            "chip_name": platform.processor() or platform.machine(),
        }

        if self.is_mac:
            import subprocess
            def _sysctl_int(param):
                try:
                    out = subprocess.check_output(["sysctl", "-n", param], stderr=subprocess.DEVNULL, text=True).strip()
                    return int(out) if out.isdigit() else 0
                except Exception:
                    return 0

            # Rosetta 2 check
            topo["is_rosetta"] = (_sysctl_int("sysctl.proc_translated") == 1)

            # Query Apple Silicon Performance vs Efficiency cores
            # hw.perflevel0 = High Performance cores (P-cores)
            # hw.perflevel1 = Power Efficiency cores (E-cores)
            p_cores = _sysctl_int("hw.perflevel0.physicalcpu")
            if p_cores == 0:
                p_cores = _sysctl_int("hw.perflevel0.logicalcpu")
            e_cores = _sysctl_int("hw.perflevel1.physicalcpu")
            if e_cores == 0:
                e_cores = _sysctl_int("hw.perflevel1.logicalcpu")

            phys = _sysctl_int("hw.physicalcpu")

            # Brand string (e.g. "Apple M4", "Apple M3 Pro", "Intel(R) Core(TM) i9...")
            try:
                brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], stderr=subprocess.DEVNULL, text=True).strip()
                if brand:
                    topo["chip_name"] = brand
            except Exception:
                pass

            if p_cores > 0:
                topo["is_apple_silicon"] = True
                topo["p_cores"] = p_cores
                topo["e_cores"] = e_cores
                topo["physical_cores"] = phys if phys > 0 else (p_cores + e_cores)
            elif platform.machine() == "arm64" or topo["is_rosetta"]:
                topo["is_apple_silicon"] = True
                topo["physical_cores"] = phys if phys > 0 else logical
                # Fallback: base Apple Silicon chips typically feature 3-4 P-cores
                topo["p_cores"] = max(2, min(4, logical // 2))
                topo["e_cores"] = max(0, logical - topo["p_cores"])
            else:
                # Intel Mac (x86_64)
                topo["is_apple_silicon"] = False
                topo["physical_cores"] = phys if phys > 0 else max(1, logical // 2)
                topo["p_cores"] = topo["physical_cores"]
                topo["e_cores"] = 0
        else:
            # Linux / Windows
            try:
                import psutil
                phys = psutil.cpu_count(logical=False)
                if phys and phys > 0:
                    topo["physical_cores"] = phys
                    topo["p_cores"] = phys
            except Exception:
                topo["physical_cores"] = max(1, logical // 2 if logical > 2 else logical)
                topo["p_cores"] = topo["physical_cores"]

        return topo

    def get_optimal_whisper_threading(self, device: str = "cpu") -> dict:
        """
        Computes optimal thread count and worker count for Faster-Whisper / CTranslate2.
        Prevents thread thrashing, barrier stalls on asymmetric Apple Silicon cores (M1-M5),
        and leaves enough headroom for the OS, DaVinci Resolve, and BadWords GUI.
        """
        topo = self.get_cpu_topology()

        # 1. GPU (CUDA on Linux / Windows)
        if "cuda" in device.lower() or "gpu" in device.lower():
            return {
                "cpu_threads": 2,
                "workers": 2,
                "env_threads": "2",
                "reason": "GPU mode (CUDA saturated; 2 CPU helper threads optimal)"
            }

        # 2. Apple Silicon macOS (M1, M2, M3, M4, M5, Pro, Max, Ultra)
        if topo.get("is_apple_silicon"):
            p_cores = max(1, topo.get("p_cores", 4))
            e_cores = topo.get("e_cores", 4)
            # CRITICAL ARCHITECTURAL RULE FOR APPLE SILICON (M1-M5):
            # In matrix multiplication (CTranslate2/OpenMP), if thread count exceeds P-cores,
            # threads spill onto E-cores. Fast P-cores finish in 1.5ms and wait on slow E-cores (barrier stall).
            # Restricting threads exclusively to P-cores yields up to 2-3x faster transcription!
            # All E-cores stay 100% free for macOS WindowServer, DaVinci Resolve & BadWords GUI.
            # Parallel chunk workers:
            # 2 parallel workers is the proven sweet spot across all Apple Silicon chips (M1-M5).
            # It processes two audio chunks simultaneously in thread pool without serial bottleneck.
            workers = 2
            threads = 4 if p_cores >= 4 else p_cores

            return {
                "cpu_threads": threads,
                "workers": workers,
                "env_threads": str(threads),
                "reason": f"Apple Silicon ({topo.get('chip_name', 'ARM64')}): {workers} parallel chunk workers with {threads} threads; {e_cores} E-cores reserved for OS/UI"
            }

        # 3. Intel Mac (x86_64)
        if self.is_mac:
            phys = max(1, topo.get("physical_cores", 4))
            threads = max(1, phys - 1)
            workers = 1 if phys <= 4 else 2
            return {
                "cpu_threads": threads,
                "workers": workers,
                "env_threads": str(threads),
                "reason": f"Intel Mac: {threads} physical cores, leaving 1 core for OS/UI"
            }

        # 4. Linux / Windows on CPU
        logical = topo.get("logical_cores", 4)
        phys = topo.get("physical_cores", logical)
        threads = max(1, min(phys, logical - 2))
        workers = max(1, (logical - 2) // 2) if logical > 4 else 1
        return {
            "cpu_threads": threads,
            "workers": workers,
            "env_threads": str(threads),
            "reason": f"CPU Mode: {threads} threads, {workers} workers, leaving 2 cores for UI/OS"
        }

